"""统计看板数据结构。"""

from pydantic import BaseModel, Field

from app.schemas.inspection import InspectionOut
from app.schemas.issue import IssueOut


class NameValue(BaseModel):
    name: str
    value: float


class RangeMeta(BaseModel):
    """本次看板统计使用的统一区间，指标卡 / 趋势 / 明细跳转共用此口径。"""

    mode: str = Field(description="current=本期，mom=环比，yoy=同比")
    mode_label: str = Field(description="区间口径中文名")
    days: int
    date_from: str
    date_to: str


class OverviewStats(BaseModel):
    # —— 存量指标：取当前时点，不随统计区间变化 ——
    restroom_total: int = 0
    restroom_open: int = 0
    restroom_maintenance: int = 0
    issue_open: int = 0
    issue_overdue: int = 0

    # —— 区间流量指标：全部限定在 RangeMeta 描述的同一区间内 ——
    inspection_total: int = Field(default=0, description="区间内巡查记录数")
    issue_total: int = Field(default=0, description="区间内新增问题数")
    avg_score: float | None = Field(default=None, description="区间巡查均分，无巡查时为 null")
    issue_closed: int = Field(default=0, description="区间内上报且已闭环（已完成/已关闭）的问题数")
    rectification_rate: float | None = Field(
        default=None, description="区间问题闭环率（百分比），无问题时为 null"
    )

    # —— 仅 /stats/overview（全量口径）使用，看板区间口径下留空 ——
    inspection_today: int = 0
    inspection_week: int = 0
    avg_score_week: float | None = None
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
    inspection_count: int = 0
    issue_count: int = 0
    issue_open: int = 0
    avg_score: float | None = None


class DashboardStats(BaseModel):
    """看板一次拉取所需的全部指标，所有分块共用 range 描述的同一区间。"""

    range: RangeMeta
    has_inspections: bool = Field(description="区间内是否存在巡查记录")
    has_issues: bool = Field(description="区间内是否存在问题上报")
    overview: OverviewStats
    issue_by_status: list[NameValue] = Field(default_factory=list)
    issue_by_category: list[CategoryStat] = Field(default_factory=list)
    issue_by_severity: list[NameValue] = Field(default_factory=list)
    inspection_trend: list[TrendPoint] = Field(default_factory=list)
    districts: list[DistrictStat] = Field(default_factory=list)
    top_restrooms: list[RestroomRankItem] = Field(default_factory=list)
    recent_issues: list[IssueOut] = Field(default_factory=list)
    recent_inspections: list[InspectionOut] = Field(default_factory=list)
