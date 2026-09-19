"""统计看板数据结构。"""

from pydantic import BaseModel, Field

from app.schemas.inspection import InspectionOut
from app.schemas.issue import IssueOut


class NameValue(BaseModel):
    name: str
    value: float


class PeriodInfo(BaseModel):
    """实际生效的统计区间，回传给前端用于明细链接与标题展示。"""

    start: str
    end: str
    compare_start: str
    compare_end: str
    compare_mode: str = Field(description="mom=环比 / yoy=同比")
    compare_label: str
    days: int


class CompareOverview(BaseModel):
    """对比区间（环比/同比）的区间内指标，口径与本期完全一致。"""

    inspection_total: int = 0
    issue_total: int = 0
    avg_score: float | None = None
    rectification_rate: float | None = None
    has_data: bool = False


class OverviewStats(BaseModel):
    # —— 与时间无关的存量快照 ——
    restroom_total: int = 0
    restroom_open: int = 0
    restroom_maintenance: int = 0
    issue_open: int = 0
    issue_overdue: int = 0

    # —— 本期区间内口径（与趋势、明细同一区间）——
    inspection_total: int = 0
    issue_total: int = 0
    avg_score: float | None = Field(default=None, description="区间内巡查均分，无数据为 null")
    rectification_rate: float | None = Field(
        default=None, description="区间内上报问题的闭环率，无数据为 null"
    )
    issue_closed: int = Field(default=0, description="区间内上报且已闭环（已完成/已关闭）数量")

    # —— 兼容旧字段（保留，避免历史调用方取空）——
    inspection_today: int = 0
    inspection_week: int = 0
    avg_score_week: float = 0.0
    issue_done_this_month: int = 0


class TrendPoint(BaseModel):
    date: str
    inspections: int = 0
    issues: int = 0
    avg_score: float | None = None


class CategoryStat(BaseModel):
    category: str
    total: int = 0
    open: int = 0
    closed: int = 0


class RestroomRankItem(BaseModel):
    restroom_id: int
    code: str
    name: str
    district: str
    inspection_count: int = 0
    avg_score: float | None = None
    open_issues: int = 0


class DistrictStat(BaseModel):
    district: str
    restroom_count: int = 0
    issue_total: int = 0
    issue_open: int = 0
    inspection_count: int = 0
    avg_score: float | None = None


class DashboardStats(BaseModel):
    """看板一次拉取所需的全部指标。同一区间口径，一次返回、整屏一致。"""

    period: PeriodInfo
    compare: CompareOverview
    has_data: bool = Field(description="本期区间是否存在任何巡查或问题数据")
    overview: OverviewStats
    issue_by_status: list[NameValue] = Field(default_factory=list)
    issue_by_category: list[CategoryStat] = Field(default_factory=list)
    issue_by_severity: list[NameValue] = Field(default_factory=list)
    inspection_trend: list[TrendPoint] = Field(default_factory=list)
    districts: list[DistrictStat] = Field(default_factory=list)
    top_restrooms: list[RestroomRankItem] = Field(default_factory=list)
    recent_issues: list[IssueOut] = Field(default_factory=list)
    recent_inspections: list[InspectionOut] = Field(default_factory=list)
