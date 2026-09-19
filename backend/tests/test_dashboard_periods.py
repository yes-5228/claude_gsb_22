"""看板区间口径测试：环比/同比等长同边界，指标卡/趋势/分类/区域/明细合计对齐。"""

from datetime import date, datetime, timedelta

from tests.conftest import full_items


def _create_inspection(client, restroom, *, day, score=9.0):
    return client.post(
        "/api/v1/inspections",
        json={
            "restroom_id": restroom["id"],
            "inspector": "区间巡查员",
            "shift": "早班",
            "inspect_time": datetime.combine(day, datetime.min.time()).isoformat(),
            "items": full_items(score),
        },
    ).json()


def test_ranges_are_equal_length_for_mom_and_yoy(client):
    for mode in ("mom", "yoy"):
        payload = client.get(
            "/api/v1/stats/dashboard", params={"trend_days": 14, "compare": mode}
        ).json()
        period = payload["period"]
        cur_len = (date.fromisoformat(period["end"]) - date.fromisoformat(period["start"])).days
        cmp_len = (
            date.fromisoformat(period["compare_end"]) - date.fromisoformat(period["compare_start"])
        ).days
        assert cur_len == cmp_len == 13  # 14 天 -> 跨度 13
        assert period["compare_mode"] == mode


def test_yoy_compare_is_exactly_one_year_earlier(client):
    payload = client.get(
        "/api/v1/stats/dashboard", params={"trend_days": 7, "compare": "yoy"}
    ).json()
    period = payload["period"]
    start = date.fromisoformat(period["start"])
    cmp_start = date.fromisoformat(period["compare_start"])
    assert (start - cmp_start).days in (365, 366)


def test_dashboard_totals_match_trend_distributions_and_detail_list(client, restroom):
    today = date.today()
    # 在本期（近 7 天）内造 3 条巡查、其中 1 条转问题
    bad = None
    for offset, score in ((1, 9.0), (2, 8.0), (4, 5.0)):
        inspection = _create_inspection(client, restroom, day=today - timedelta(days=offset), score=score)
        if score < 6:
            bad = inspection
    assert bad is not None and bad["result"] == "发现问题"
    client.post(
        "/api/v1/issues",
        json={
            "restroom_id": restroom["id"],
            "inspection_id": bad["id"],
            "title": "区间口径校验问题",
            "category": "保洁不到位",
            "severity": "严重",
            "reporter": "王巡查",
        },
    )
    payload = client.get(
        "/api/v1/stats/dashboard", params={"trend_days": 7, "compare": "mom"}
    ).json()
    p, ov = payload["period"], payload["overview"]

    # 指标卡 = 趋势合计
    trend_insp = sum(point["inspections"] for point in payload["inspection_trend"])
    trend_iss = sum(point["issues"] for point in payload["inspection_trend"])
    assert trend_insp == ov["inspection_total"] >= 3
    assert trend_iss == ov["issue_total"] >= 1

    # 指标卡 = 各分布合计
    assert sum(item["total"] for item in payload["issue_by_category"]) == ov["issue_total"]
    assert sum(item["value"] for item in payload["issue_by_severity"]) == ov["issue_total"]
    assert sum(item["value"] for item in payload["issue_by_status"]) == ov["issue_total"]
    assert sum(item["issue_total"] for item in payload["districts"]) == ov["issue_total"]

    # 指标卡 = 明细列表（同一 date_from/date_to 口径）
    issue_list = client.get(
        "/api/v1/issues", params={"date_from": p["start"], "date_to": p["end"]}
    ).json()
    insp_list = client.get(
        "/api/v1/inspections", params={"date_from": p["start"], "date_to": p["end"]}
    ).json()
    assert issue_list["meta"]["total"] == ov["issue_total"]
    assert insp_list["meta"]["total"] == ov["inspection_total"]

    # 分类/区域过滤后明细数与分布值一致（共享库，只比结构相等，不写死绝对值）
    for cat_row in payload["issue_by_category"]:
        count = client.get(
            "/api/v1/issues",
            params={"date_from": p["start"], "date_to": p["end"], "category": cat_row["category"]},
        ).json()["meta"]["total"]
        assert count == cat_row["total"]
    cleaning = next(item for item in payload["issue_by_category"] if item["category"] == "保洁不到位")
    assert cleaning["total"] >= 1


def test_empty_comparison_period_is_flagged_not_zero(client, restroom):
    # 演示库为空且仅在本期造数据：环比/同比对比区间都应无数据
    today = date.today()
    _create_inspection(client, restroom, day=today)
    payload = client.get(
        "/api/v1/stats/dashboard", params={"trend_days": 7, "compare": "mom"}
    ).json()
    assert payload["has_data"] is True
    compare = payload["compare"]
    assert compare["has_data"] is False
    assert compare["inspection_total"] == 0
    assert compare["issue_total"] == 0
    assert compare["avg_score"] is None
    assert compare["rectification_rate"] is None


def test_invalid_compare_rejected(client):
    response = client.get("/api/v1/stats/dashboard", params={"compare": "wow"})
    assert response.status_code == 422
