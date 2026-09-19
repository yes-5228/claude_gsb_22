"""统计看板业务逻辑。

所有看板面板（指标卡 / 趋势 / 分类 / 区域 / 排行 / 明细）都基于同一个
``DateRange`` 过滤：巡查按 ``inspect_time``、问题按 ``report_time``，
区间边界统一为 ``start 00:00 ~ end 23:59:59.999999``，与明细列表接口一致，
因此三处合计在结构上必然对得上。环比 / 同比区间由 :mod:`app.services.periods`
按等长、同边界的口径计算。
"""

from datetime import date, datetime, time, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.constants import (
    OPEN_ISSUE_STATUSES,
    IssueCategory,
    IssueSeverity,
    IssueStatus,
    RestroomStatus,
)
from app.models import Inspection, Issue, Restroom
from app.schemas.stats import (
    CategoryStat,
    CompareOverview,
    DashboardStats,
    DistrictStat,
    NameValue,
    OverviewStats,
    PeriodInfo,
    RestroomRankItem,
    TrendPoint,
)
from app.services import inspection_service, issue_service, periods
from app.services.periods import CompareMode, DateRange

CLOSED_ISSUE_STATUSES = (IssueStatus.DONE.value, IssueStatus.CLOSED.value)


def _count(db: Session, model, *conditions) -> int:
    stmt = select(func.count()).select_from(model)
    if conditions:
        stmt = stmt.where(*conditions)
    return db.scalar(stmt) or 0


def _period_inspection_stats(db: Session, span: DateRange) -> tuple[int, float | None]:
    """区间内巡查条数与均分（无巡查时均分为 None，区分"无数据"与 0 分）。"""
    total, avg = db.execute(
        select(func.count(Inspection.id), func.avg(Inspection.score)).where(
            Inspection.inspect_time >= span.start_dt,
            Inspection.inspect_time <= span.end_dt,
        )
    ).one()
    total = int(total or 0)
    return total, (round(float(avg), 1) if total else None)


def _period_issue_stats(db: Session, span: DateRange) -> tuple[int, int, int]:
    """区间内上报问题的 (总数, 未闭环, 已闭环)，状态取当前实时状态。"""
    total, open_count = db.execute(
        select(
            func.count(Issue.id),
            func.coalesce(
                func.sum(case((Issue.status.in_(OPEN_ISSUE_STATUSES), 1), else_=0)), 0
            ),
        ).where(Issue.report_time >= span.start_dt, Issue.report_time <= span.end_dt)
    ).one()
    total = int(total or 0)
    open_count = int(open_count or 0)
    return total, open_count, total - open_count


def overview(db: Session, span: DateRange | None = None) -> OverviewStats:
    now = datetime.now()
    today_start = datetime.combine(now.date(), time.min)
    week_start = today_start - timedelta(days=6)
    month_start = datetime.combine(date(now.year, now.month, 1), time.min)

    # —— 存量快照（与区间无关）——
    restroom_total = _count(db, Restroom)
    restroom_open = _count(db, Restroom, Restroom.status == RestroomStatus.NORMAL.value)
    restroom_maintenance = _count(
        db, Restroom, Restroom.status == RestroomStatus.MAINTENANCE.value
    )
    issue_open = _count(db, Issue, Issue.status.in_(OPEN_ISSUE_STATUSES))
    issue_overdue = _count(
        db,
        Issue,
        Issue.deadline.is_not(None),
        Issue.deadline < now,
        Issue.status.in_(OPEN_ISSUE_STATUSES),
    )

    # —— 区间内指标 ——
    if span is None:
        span, _ = periods.resolve_ranges(periods.DEFAULT_DAYS)
    insp_total, avg_score = _period_inspection_stats(db, span)
    issue_total, open_in_period, closed_in_period = _period_issue_stats(db, span)
    rate = round(closed_in_period / issue_total * 100, 1) if issue_total else None

    return OverviewStats(
        restroom_total=restroom_total,
        restroom_open=restroom_open,
        restroom_maintenance=restroom_maintenance,
        issue_open=issue_open,
        issue_overdue=issue_overdue,
        inspection_total=insp_total,
        issue_total=issue_total,
        avg_score=avg_score,
        rectification_rate=rate,
        issue_closed=closed_in_period,
        # 兼容字段
        inspection_today=_count(db, Inspection, Inspection.inspect_time >= today_start),
        inspection_week=_count(db, Inspection, Inspection.inspect_time >= week_start),
        avg_score_week=round(
            float(
                db.scalar(
                    select(func.avg(Inspection.score)).where(Inspection.inspect_time >= week_start)
                )
                or 0.0
            ),
            1,
        ),
        issue_done_this_month=_count(
            db, Issue, Issue.status == IssueStatus.DONE.value, Issue.updated_at >= month_start
        ),
    )


def compare_overview(db: Session, span: DateRange) -> CompareOverview:
    insp_total, avg_score = _period_inspection_stats(db, span)
    issue_total, _, closed_total = _period_issue_stats(db, span)
    return CompareOverview(
        inspection_total=insp_total,
        issue_total=issue_total,
        avg_score=avg_score,
        rectification_rate=round(closed_total / issue_total * 100, 1) if issue_total else None,
        has_data=bool(insp_total or issue_total),
    )


def issue_by_status(db: Session, span: DateRange) -> list[NameValue]:
    rows = dict(
        db.execute(
            select(Issue.status, func.count())
            .where(Issue.report_time >= span.start_dt, Issue.report_time <= span.end_dt)
            .group_by(Issue.status)
        ).all()
    )
    return [
        NameValue(name=status.value, value=float(rows.get(status.value, 0)))
        for status in IssueStatus
    ]


def issue_by_severity(db: Session, span: DateRange) -> list[NameValue]:
    rows = dict(
        db.execute(
            select(Issue.severity, func.count())
            .where(Issue.report_time >= span.start_dt, Issue.report_time <= span.end_dt)
            .group_by(Issue.severity)
        ).all()
    )
    return [
        NameValue(name=severity.value, value=float(rows.get(severity.value, 0)))
        for severity in IssueSeverity
    ]


def issue_by_category(db: Session, span: DateRange) -> list[CategoryStat]:
    rows = db.execute(
        select(Issue.category, func.count())
        .where(Issue.report_time >= span.start_dt, Issue.report_time <= span.end_dt)
        .group_by(Issue.category)
    ).all()
    totals = {category: int(count) for category, count in rows}
    open_rows = db.execute(
        select(Issue.category, func.count())
        .where(
            Issue.report_time >= span.start_dt,
            Issue.report_time <= span.end_dt,
            Issue.status.in_(OPEN_ISSUE_STATUSES),
        )
        .group_by(Issue.category)
    ).all()
    opens = {category: int(count) for category, count in open_rows}
    return [
        CategoryStat(
            category=category.value,
            total=totals.get(category.value, 0),
            open=opens.get(category.value, 0),
            closed=totals.get(category.value, 0) - opens.get(category.value, 0),
        )
        for category in IssueCategory
    ]


def inspection_trend(db: Session, span: DateRange) -> list[TrendPoint]:
    """把区间逐天落桶，桶的并集就是本期（合计与指标卡、明细一致）。"""
    days = (span.end - span.start).days + 1
    inspection_rows = db.execute(
        select(Inspection.inspect_time, Inspection.score).where(
            Inspection.inspect_time >= span.start_dt,
            Inspection.inspect_time <= span.end_dt,
        )
    ).all()
    issue_rows = db.execute(
        select(Issue.report_time).where(
            Issue.report_time >= span.start_dt, Issue.report_time <= span.end_dt
        )
    ).all()

    buckets: dict[str, dict[str, float]] = {
        (span.start + timedelta(days=offset)).isoformat(): {
            "inspections": 0,
            "issues": 0,
            "score_sum": 0.0,
        }
        for offset in range(days)
    }
    for inspect_time, score in inspection_rows:
        key = inspect_time.date().isoformat()
        if key in buckets:
            buckets[key]["inspections"] += 1
            buckets[key]["score_sum"] += float(score or 0)
    for (report_time,) in issue_rows:
        key = report_time.date().isoformat()
        if key in buckets:
            buckets[key]["issues"] += 1

    points: list[TrendPoint] = []
    for key, bucket in buckets.items():
        count = int(bucket["inspections"])
        points.append(
            TrendPoint(
                date=key,
                inspections=count,
                issues=int(bucket["issues"]),
                avg_score=round(bucket["score_sum"] / count, 1) if count else None,
            )
        )
    return points


def district_stats(db: Session, span: DateRange) -> list[DistrictStat]:
    restroom_rows = db.execute(
        select(Restroom.district, func.count()).group_by(Restroom.district)
    ).all()
    counts = {district: int(count) for district, count in restroom_rows}

    issue_rows = db.execute(
        select(
            Restroom.district,
            func.count(Issue.id),
            func.coalesce(
                func.sum(case((Issue.status.in_(OPEN_ISSUE_STATUSES), 1), else_=0)), 0
            ),
        )
        .join(Issue, Issue.restroom_id == Restroom.id)
        .where(Issue.report_time >= span.start_dt, Issue.report_time <= span.end_dt)
        .group_by(Restroom.district)
    ).all()
    issues = {district: (int(total), int(opened)) for district, total, opened in issue_rows}

    score_rows = db.execute(
        select(Restroom.district, func.count(Inspection.id), func.avg(Inspection.score))
        .join(Inspection, Inspection.restroom_id == Restroom.id)
        .where(
            Inspection.inspect_time >= span.start_dt,
            Inspection.inspect_time <= span.end_dt,
        )
        .group_by(Restroom.district)
    ).all()
    inspections = {
        district: (int(count), round(float(avg), 1) if count else None)
        for district, count, avg in score_rows
    }

    result = [
        DistrictStat(
            district=district,
            restroom_count=count,
            issue_total=issues.get(district, (0, 0))[0],
            issue_open=issues.get(district, (0, 0))[1],
            inspection_count=inspections.get(district, (0, None))[0],
            avg_score=inspections.get(district, (0, None))[1],
        )
        for district, count in counts.items()
    ]
    result.sort(key=lambda item: (item.issue_total, item.inspection_count), reverse=True)
    return result


def restroom_ranking(db: Session, span: DateRange, limit: int = 8) -> list[RestroomRankItem]:
    """区间内有巡查或问题活动的公厕重点排行。"""
    inspections = db.execute(
        select(
            Inspection.restroom_id,
            func.count(Inspection.id),
            func.avg(Inspection.score),
        )
        .where(
            Inspection.inspect_time >= span.start_dt,
            Inspection.inspect_time <= span.end_dt,
        )
        .group_by(Inspection.restroom_id)
    ).all()
    insp_stats = {
        rid: {"count": int(count), "avg": round(float(avg), 1) if count else None}
        for rid, count, avg in inspections
    }
    open_rows = db.execute(
        select(Issue.restroom_id, func.count())
        .where(
            Issue.report_time >= span.start_dt,
            Issue.report_time <= span.end_dt,
            Issue.status.in_(OPEN_ISSUE_STATUSES),
        )
        .group_by(Issue.restroom_id)
    ).all()
    opens = {rid: int(count) for rid, count in open_rows}

    active_ids = set(insp_stats) | {rid for rid, count in opens.items() if count > 0}
    restrooms = {
        room.id: room for room in db.scalars(select(Restroom).where(Restroom.id.in_(active_ids)))
    } if active_ids else {}

    ranking = [
        RestroomRankItem(
            restroom_id=rid,
            code=room.code,
            name=room.name,
            district=room.district,
            inspection_count=insp_stats.get(rid, {}).get("count", 0),
            avg_score=insp_stats.get(rid, {}).get("avg"),
            open_issues=opens.get(rid, 0),
        )
        for rid, room in restrooms.items()
    ]
    ranking.sort(key=lambda item: (-item.open_issues, item.avg_score is None, item.avg_score or 0))
    return ranking[:limit]


def dashboard(db: Session, days: int = 14, compare: CompareMode = CompareMode.MOM) -> DashboardStats:
    current, comparison = periods.resolve_ranges(days, compare=compare)

    recent_issues, _ = issue_service.list_issues(
        db,
        page=1,
        page_size=5,
        sort_by="report_time",
        date_from=current.start,
        date_to=current.end,
    )
    recent_inspections, _ = inspection_service.list_inspections(
        db,
        page=1,
        page_size=5,
        sort_by="inspect_time",
        date_from=current.start,
        date_to=current.end,
    )

    ov = overview(db, current)
    has_data = bool(ov.inspection_total or ov.issue_total)

    return DashboardStats(
        period=PeriodInfo(
            start=current.start.isoformat(),
            end=current.end.isoformat(),
            compare_start=comparison.start.isoformat(),
            compare_end=comparison.end.isoformat(),
            compare_mode=compare.value,
            compare_label=comparison.label,
            days=periods.clamp_days(days),
        ),
        compare=compare_overview(db, comparison),
        has_data=has_data,
        overview=ov,
        issue_by_status=issue_by_status(db, current),
        issue_by_category=issue_by_category(db, current),
        issue_by_severity=issue_by_severity(db, current),
        inspection_trend=inspection_trend(db, current),
        districts=district_stats(db, current),
        top_restrooms=restroom_ranking(db, current),
        recent_issues=[issue_service.to_out(issue) for issue in recent_issues],
        recent_inspections=[inspection_service.to_out(item) for item in recent_inspections],
    )
