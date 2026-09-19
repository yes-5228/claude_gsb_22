"""统计看板业务逻辑。

看板所有分块（指标卡、趋势、分布、区域、明细链接）共用同一套区间口径：

- ``current`` 本期：``[今天-days+1, 今天]``
- ``mom`` 环比：紧邻本期的上一个等长区间
- ``yoy`` 同比：去年同一日历区间（2 月 29 日自动回退到 28 日）

区间内的巡查 / 问题数据只查询一次，指标卡合计、按天趋势与各分布的合计
因此必然一致；明细页按返回的 ``date_from / date_to`` 过滤即可对账。
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constants import (
    CLOSED_ISSUE_STATUSES,
    OPEN_ISSUE_STATUSES,
    IssueCategory,
    IssueSeverity,
    IssueStatus,
    RestroomStatus,
)
from app.models import Inspection, Issue, Restroom
from app.schemas.stats import (
    CategoryStat,
    DashboardStats,
    DistrictStat,
    NameValue,
    OverviewStats,
    RangeMeta,
    RestroomRankItem,
    TrendPoint,
)
from app.services import inspection_service, issue_service

MODE_LABELS = {"current": "本期", "mom": "环比区间", "yoy": "同比区间"}


@dataclass(frozen=True)
class Period:
    """一次看板统计使用的统一区间（含端点，按自然日划分）。"""

    mode: str
    days: int
    start: date
    end: date

    @property
    def start_dt(self) -> datetime:
        return datetime.combine(self.start, time.min)

    @property
    def end_dt(self) -> datetime:
        return datetime.combine(self.end, time.max)

    def meta(self) -> RangeMeta:
        return RangeMeta(
            mode=self.mode,
            mode_label=MODE_LABELS.get(self.mode, self.mode),
            days=self.days,
            date_from=self.start.isoformat(),
            date_to=self.end.isoformat(),
        )


def resolve_period(mode: str, days: int, today: date | None = None) -> Period:
    """按口径解析区间。环比与同比区间长度与本期完全一致。"""
    days = max(3, min(days, 60))
    today = today or date.today()
    if mode == "current":
        start, end = today - timedelta(days=days - 1), today
    elif mode == "mom":
        end = today - timedelta(days=days)
        start = end - timedelta(days=days - 1)
    elif mode == "yoy":
        end = _same_day_last_year(today)
        start = _same_day_last_year(today - timedelta(days=days - 1))
    else:
        raise ValueError(f"不支持的统计口径：{mode}")
    return Period(mode=mode, days=days, start=start, end=end)


def _same_day_last_year(day: date) -> date:
    """取去年同一日历日；去年不是闰年且遇到 2 月 29 日时回退到 2 月 28 日。"""
    try:
        return day.replace(year=day.year - 1)
    except ValueError:
        return day.replace(year=day.year - 1, day=28)


def _count(db: Session, model, *conditions) -> int:
    stmt = select(func.count()).select_from(model)
    if conditions:
        stmt = stmt.where(*conditions)
    return db.scalar(stmt) or 0


def overview(db: Session) -> OverviewStats:
    """全量口径核心指标（供 /stats/overview 使用，不带统计区间）。"""
    now = datetime.now()
    today_start = datetime.combine(now.date(), time.min)
    week_start = today_start - timedelta(days=6)
    month_start = datetime.combine(date(now.year, now.month, 1), time.min)

    issue_total = _count(db, Issue)
    issue_open = _count(db, Issue, Issue.status.in_(OPEN_ISSUE_STATUSES))
    issue_overdue = _count(
        db,
        Issue,
        Issue.deadline.is_not(None),
        Issue.deadline < now,
        Issue.status.in_(OPEN_ISSUE_STATUSES),
    )
    done_count = _count(db, Issue, Issue.status == IssueStatus.DONE.value)
    closed_count = _count(db, Issue, Issue.status == IssueStatus.CLOSED.value)
    finished = done_count + closed_count

    return OverviewStats(
        restroom_total=_count(db, Restroom),
        restroom_open=_count(db, Restroom, Restroom.status == RestroomStatus.NORMAL.value),
        restroom_maintenance=_count(db, Restroom, Restroom.status == RestroomStatus.MAINTENANCE.value),
        issue_open=issue_open,
        issue_overdue=issue_overdue,
        inspection_total=_count(db, Inspection),
        issue_total=issue_total,
        avg_score=round(float(db.scalar(select(func.avg(Inspection.score))) or 0.0), 1),
        issue_closed=finished,
        rectification_rate=round(finished / issue_total * 100, 1) if issue_total else None,
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


# --------------------------------------------------------------------------- #
# 区间口径：以下函数全部基于同一个 Period，且优先复用一次性查出的区间数据集
# --------------------------------------------------------------------------- #


def _range_inspections(db: Session, period: Period) -> list[Inspection]:
    return list(
        db.scalars(
            select(Inspection).where(
                Inspection.inspect_time >= period.start_dt,
                Inspection.inspect_time <= period.end_dt,
            )
        )
    )


def _range_issues(db: Session, period: Period) -> list[Issue]:
    return list(
        db.scalars(
            select(Issue).where(
                Issue.report_time >= period.start_dt,
                Issue.report_time <= period.end_dt,
            )
        )
    )


def _restroom_index(db: Session) -> dict[int, Restroom]:
    return {item.id: item for item in db.scalars(select(Restroom))}


def _range_overview(
    db: Session, issues: list[Issue], inspections: list[Inspection]
) -> OverviewStats:
    now = datetime.now()
    issue_total = len(issues)
    closed_total = sum(1 for issue in issues if issue.status in CLOSED_ISSUE_STATUSES)
    avg_score = (
        round(sum(float(item.score or 0) for item in inspections) / len(inspections), 1)
        if inspections
        else None
    )
    return OverviewStats(
        # 存量指标始终取当前时点
        restroom_total=_count(db, Restroom),
        restroom_open=_count(db, Restroom, Restroom.status == RestroomStatus.NORMAL.value),
        restroom_maintenance=_count(db, Restroom, Restroom.status == RestroomStatus.MAINTENANCE.value),
        issue_open=_count(db, Issue, Issue.status.in_(OPEN_ISSUE_STATUSES)),
        issue_overdue=_count(
            db,
            Issue,
            Issue.deadline.is_not(None),
            Issue.deadline < now,
            Issue.status.in_(OPEN_ISSUE_STATUSES),
        ),
        # 区间流量指标
        inspection_total=len(inspections),
        issue_total=issue_total,
        avg_score=avg_score,
        issue_closed=closed_total,
        rectification_rate=round(closed_total / issue_total * 100, 1) if issue_total else None,
    )


def _issue_by_status(issues: list[Issue]) -> list[NameValue]:
    counts = {status.value: 0 for status in IssueStatus}
    for issue in issues:
        counts[issue.status] = counts.get(issue.status, 0) + 1
    return [NameValue(name=status.value, value=float(counts[status.value])) for status in IssueStatus]


def _issue_by_severity(issues: list[Issue]) -> list[NameValue]:
    counts = {severity.value: 0 for severity in IssueSeverity}
    for issue in issues:
        counts[issue.severity] = counts.get(issue.severity, 0) + 1
    return [
        NameValue(name=severity.value, value=float(counts[severity.value]))
        for severity in IssueSeverity
    ]


def _issue_by_category(issues: list[Issue]) -> list[CategoryStat]:
    totals = {category.value: 0 for category in IssueCategory}
    opens = {category.value: 0 for category in IssueCategory}
    for issue in issues:
        totals[issue.category] = totals.get(issue.category, 0) + 1
        if issue.status in OPEN_ISSUE_STATUSES:
            opens[issue.category] = opens.get(issue.category, 0) + 1
    return [
        CategoryStat(
            category=category.value,
            total=totals[category.value],
            open=opens[category.value],
            closed=totals[category.value] - opens[category.value],
        )
        for category in IssueCategory
    ]


def _inspection_trend(
    period: Period, inspections: list[Inspection], issues: list[Issue]
) -> list[TrendPoint]:
    buckets: dict[str, dict[str, float]] = {}
    for offset in range(period.days):
        buckets[(period.start + timedelta(days=offset)).isoformat()] = {
            "inspections": 0,
            "issues": 0,
            "score_sum": 0.0,
        }
    for inspection in inspections:
        bucket = buckets.get(inspection.inspect_time.date().isoformat())
        if bucket is not None:
            bucket["inspections"] += 1
            bucket["score_sum"] += float(inspection.score or 0)
    for issue in issues:
        bucket = buckets.get(issue.report_time.date().isoformat())
        if bucket is not None:
            bucket["issues"] += 1

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


def _district_stats(
    issues: list[Issue],
    inspections: list[Inspection],
    restrooms: dict[int, Restroom],
) -> list[DistrictStat]:
    counts: dict[str, int] = {}
    for restroom in restrooms.values():
        counts[restroom.district] = counts.get(restroom.district, 0) + 1

    insp_counts: dict[str, int] = {}
    score_sums: dict[str, float] = {}
    for inspection in inspections:
        restroom = restrooms.get(inspection.restroom_id)
        district = restroom.district if restroom else "未知区域"
        insp_counts[district] = insp_counts.get(district, 0) + 1
        score_sums[district] = score_sums.get(district, 0.0) + float(inspection.score or 0)

    issue_counts: dict[str, int] = {}
    open_counts: dict[str, int] = {}
    for issue in issues:
        restroom = restrooms.get(issue.restroom_id)
        district = restroom.district if restroom else "未知区域"
        issue_counts[district] = issue_counts.get(district, 0) + 1
        if issue.status in OPEN_ISSUE_STATUSES:
            open_counts[district] = open_counts.get(district, 0) + 1

    rows: list[DistrictStat] = []
    for district, count in counts.items():
        insp_count = insp_counts.get(district, 0)
        rows.append(
            DistrictStat(
                district=district,
                restroom_count=count,
                inspection_count=insp_count,
                issue_count=issue_counts.get(district, 0),
                issue_open=open_counts.get(district, 0),
                avg_score=round(score_sums[district] / insp_count, 1) if insp_count else None,
            )
        )
    rows.sort(key=lambda item: (item.issue_open, item.issue_count), reverse=True)
    return rows


def _restroom_ranking(
    issues: list[Issue], inspections: list[Inspection], restrooms: dict[int, Restroom], limit: int = 8
) -> list[RestroomRankItem]:
    insp_counts: dict[int, int] = {}
    score_sums: dict[int, float] = {}
    for inspection in inspections:
        insp_counts[inspection.restroom_id] = insp_counts.get(inspection.restroom_id, 0) + 1
        score_sums[inspection.restroom_id] = score_sums.get(inspection.restroom_id, 0.0) + float(
            inspection.score or 0
        )
    open_counts: dict[int, int] = {}
    for issue in issues:
        if issue.status in OPEN_ISSUE_STATUSES:
            open_counts[issue.restroom_id] = open_counts.get(issue.restroom_id, 0) + 1

    ranking: list[RestroomRankItem] = []
    for restroom in restrooms.values():
        count = insp_counts.get(restroom.id, 0)
        ranking.append(
            RestroomRankItem(
                restroom_id=restroom.id,
                code=restroom.code,
                name=restroom.name,
                district=restroom.district,
                inspection_count=count,
                avg_score=round(score_sums[restroom.id] / count, 1) if count else None,
                open_issues=open_counts.get(restroom.id, 0),
            )
        )
    # 区间内有未闭环问题 / 巡查异常的优先，其次按巡查量
    ranking.sort(
        key=lambda item: (
            -item.open_issues,
            item.avg_score if item.avg_score is not None else 101,
            -item.inspection_count,
        )
    )
    return ranking[:limit]


def dashboard(db: Session, period: Period) -> DashboardStats:
    inspections = _range_inspections(db, period)
    issues = _range_issues(db, period)
    restrooms = _restroom_index(db)

    recent_issues, _ = issue_service.list_issues(
        db,
        page=1,
        page_size=5,
        sort_by="report_time",
        date_from=period.start,
        date_to=period.end,
    )
    recent_inspections, _ = inspection_service.list_inspections(
        db,
        page=1,
        page_size=5,
        sort_by="inspect_time",
        date_from=period.start,
        date_to=period.end,
    )

    return DashboardStats(
        range=period.meta(),
        has_inspections=bool(inspections),
        has_issues=bool(issues),
        overview=_range_overview(db, issues, inspections),
        issue_by_status=_issue_by_status(issues),
        issue_by_category=_issue_by_category(issues),
        issue_by_severity=_issue_by_severity(issues),
        inspection_trend=_inspection_trend(period, inspections, issues),
        districts=_district_stats(issues, inspections, restrooms),
        top_restrooms=_restroom_ranking(issues, inspections, restrooms),
        # 列表服务同样按 period 的 date_from/date_to 过滤，与看板合计天然对得上
        recent_issues=[issue_service.to_out(issue) for issue in recent_issues],
        recent_inspections=[inspection_service.to_out(item) for item in recent_inspections],
    )
