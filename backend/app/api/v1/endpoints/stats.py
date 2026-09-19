"""统计看板接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.stats import DashboardStats, OverviewStats
from app.services import stats_service

router = APIRouter(prefix="/stats", tags=["统计看板"])


@router.get("/overview", response_model=OverviewStats, summary="核心指标（全量口径）")
def get_overview(db: Annotated[Session, Depends(get_db)]) -> OverviewStats:
    return stats_service.overview(db)


@router.get("/dashboard", response_model=DashboardStats, summary="看板聚合数据（统一区间口径）")
def get_dashboard(
    db: Annotated[Session, Depends(get_db)],
    days: Annotated[int, Query(ge=3, le=60, description="区间天数（环比/同比为等长区间）")] = 14,
    mode: Annotated[
        str, Query(pattern="^(current|mom|yoy)$", description="口径：current=本期 mom=环比 yoy=同比")
    ] = "current",
) -> DashboardStats:
    period = stats_service.resolve_period(mode=mode, days=days)
    return stats_service.dashboard(db, period)
