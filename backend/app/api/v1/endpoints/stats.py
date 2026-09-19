"""统计看板接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.stats import DashboardStats, OverviewStats
from app.services import stats_service
from app.services.periods import DEFAULT_DAYS, CompareMode

router = APIRouter(prefix="/stats", tags=["统计看板"])


@router.get("/overview", response_model=OverviewStats, summary="核心指标")
def get_overview(db: Annotated[Session, Depends(get_db)]) -> OverviewStats:
    # 默认近 7 天口径，与看板区间内字段保持可解释
    return stats_service.overview(db)


@router.get("/dashboard", response_model=DashboardStats, summary="看板聚合数据")
def get_dashboard(
    db: Annotated[Session, Depends(get_db)],
    trend_days: Annotated[int, Query(ge=3, le=60, description="本期区间天数")] = DEFAULT_DAYS,
    compare: Annotated[CompareMode, Query(description="对比口径：mom=环比，yoy=同比")] = CompareMode.MOM,
) -> DashboardStats:
    return stats_service.dashboard(db, days=trend_days, compare=compare)
