"""看板统计区间：环比 / 同比按同一口径划分。

口径约定（任何指标都只认这一套边界）：

- 本期：截止今天、长度为 ``days`` 的连续区间 ``[today - (days-1), today]``，含首尾。
- 环比：紧邻本期之前的等长区间，即整体向前平移 ``days`` 天。
- 同比：去年同期的等长区间，即整体向前平移约一年；2/29 会自动收敛到 2/28，
  保证两个区间长度仍然相等。

两个对比区间与本期使用完全相同的长度与时间边界，巡查按 ``inspect_time``、
问题按 ``report_time`` 落桶，确保指标卡、趋势、明细三处合计可对齐。
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import StrEnum

MIN_DAYS = 3
MAX_DAYS = 60
DEFAULT_DAYS = 14


class CompareMode(StrEnum):
    """对比口径。"""

    MOM = "mom"  # 环比：上一等长周期
    YOY = "yoy"  # 同比：去年同期


@dataclass(frozen=True)
class DateRange:
    """一个统计区间，日期与对应的 datetime 边界成对提供。"""

    start: date
    end: date
    label: str = ""

    @property
    def start_dt(self) -> datetime:
        return datetime.combine(self.start, time.min)

    @property
    def end_dt(self) -> datetime:
        # 列表筛选用的是 end 当天 23:59:59.999999，保持同一口径
        return datetime.combine(self.end, time.max)

    def contains(self, value: datetime) -> bool:
        return self.start_dt <= value <= self.end_dt


def clamp_days(days: int | None) -> int:
    try:
        days = int(days or DEFAULT_DAYS)
    except (TypeError, ValueError):
        days = DEFAULT_DAYS
    return max(MIN_DAYS, min(days, MAX_DAYS))


def _shift_one_year(day: date) -> date:
    """把日期平移到去年同日；闰年 2/29 收敛为 2/28。"""
    try:
        return day.replace(year=day.year - 1)
    except ValueError:
        return day.replace(year=day.year - 1, day=28)


def resolve_ranges(
    days: int, *, compare: CompareMode = CompareMode.MOM, today: date | None = None
) -> tuple[DateRange, DateRange]:
    """返回 (本期, 对比区间)，两者长度严格相等。"""
    days = clamp_days(days)
    today = today or datetime.now().date()
    current = DateRange(start=today - timedelta(days=days - 1), end=today, label="本期")
    if compare == CompareMode.YOY:
        comparison = DateRange(
            start=_shift_one_year(current.start),
            end=_shift_one_year(current.end),
            label="去年同期",
        )
    else:
        comparison = DateRange(
            start=current.start - timedelta(days=days),
            end=current.end - timedelta(days=days),
            label="环比上期",
        )
    return current, comparison
