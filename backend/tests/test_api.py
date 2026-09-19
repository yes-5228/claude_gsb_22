"""接口级测试：覆盖台账、巡查、问题整改与统计看板。"""

from datetime import datetime, timedelta

from tests.conftest import full_items


def test_health_and_dictionaries(client):
    assert client.get("/health").json()["status"] == "ok"
    payload = client.get("/api/v1/meta/dictionaries").json()
    assert "待整改" in payload["issue_status"]
    assert len(payload["inspection_check_items"]) == 8
    assert payload["issue_transitions"]["待整改"] == ["整改中", "已关闭"]


def test_restroom_crud_and_delete_guard(client, restroom):
    assert restroom["code"].startswith("WC-")

    listed = client.get("/api/v1/restrooms", params={"district": "测试区"}).json()
    assert listed["meta"]["total"] >= 1

    detail = client.get(f"/api/v1/restrooms/{restroom['id']}").json()
    assert detail["inspection_count"] == 0
    assert detail["open_issue_count"] == 0

    updated = client.patch(
        f"/api/v1/restrooms/{restroom['id']}", json={"status": "维修中", "manager": "新责任人"}
    ).json()
    assert updated["status"] == "维修中"
    assert updated["manager"] == "新责任人"

    # 存在关联数据时不允许直接删除
    client.post(
        "/api/v1/inspections",
        json={
            "restroom_id": restroom["id"],
            "inspector": "测试巡查员",
            "shift": "早班",
            "items": full_items(9),
        },
    )
    blocked = client.delete(f"/api/v1/restrooms/{restroom['id']}")
    assert blocked.status_code == 409

    ok = client.delete(f"/api/v1/restrooms/{restroom['id']}", params={"force": "true"})
    assert ok.status_code == 200
    assert client.get(f"/api/v1/restrooms/{restroom['id']}").status_code == 404


def test_inspection_scoring_and_filter(client, restroom):
    good = client.post(
        "/api/v1/inspections",
        json={
            "restroom_id": restroom["id"],
            "inspector": "李巡查",
            "shift": "中班",
            "items": full_items(9),
            "remark": "整体良好",
        },
    ).json()
    assert good["score"] == 90.0
    assert good["grade"] == "优秀"
    assert good["result"] == "正常"

    bad_items = full_items(9)
    bad_items[0]["score"] = 3
    bad_items[0]["remark"] = "地面污渍"
    bad = client.post(
        "/api/v1/inspections",
        json={
            "restroom_id": restroom["id"],
            "inspector": "李巡查",
            "shift": "晚班",
            "items": bad_items,
        },
    ).json()
    assert bad["result"] == "发现问题"
    assert bad["score"] < 90

    filtered = client.get(
        "/api/v1/inspections", params={"result": "发现问题", "restroom_id": restroom["id"]}
    ).json()
    assert filtered["meta"]["total"] == 1
    assert filtered["items"][0]["id"] == bad["id"]
    assert filtered["items"][0]["restroom"]["name"] == restroom["name"]

    today = datetime.now().date().isoformat()
    ranged = client.get(
        "/api/v1/inspections", params={"date_from": today, "date_to": today}
    ).json()
    assert ranged["meta"]["total"] == 2

    duplicate = full_items(5) + [{"name": "地面与台阶清洁", "score": 4}]
    rejected = client.post(
        "/api/v1/inspections",
        json={"restroom_id": restroom["id"], "inspector": "李巡查", "items": duplicate},
    )
    assert rejected.status_code == 400

    empty = client.post(
        "/api/v1/inspections",
        json={"restroom_id": restroom["id"], "inspector": "李巡查", "items": []},
    )
    assert empty.status_code == 422


def test_issue_lifecycle(client, restroom):
    inspection = client.post(
        "/api/v1/inspections",
        json={
            "restroom_id": restroom["id"],
            "inspector": "王巡查",
            "items": full_items(4),
        },
    ).json()

    issue = client.post(
        "/api/v1/issues",
        json={
            "restroom_id": restroom["id"],
            "inspection_id": inspection["id"],
            "title": "地面污渍未清理",
            "description": "巡查发现地面有明显污渍",
            "category": "保洁不到位",
            "severity": "严重",
            "reporter": "王巡查",
            "assignee": "保洁班组",
            "deadline": (datetime.now() - timedelta(days=1)).isoformat(),
        },
    ).json()
    assert issue["status"] == "待整改"
    assert len(issue["records"]) == 1
    assert issue["records"][0]["action"] == "上报问题"

    # 越级流转被拒绝：待整改 -> 已完成
    invalid = client.post(
        f"/api/v1/issues/{issue['id']}/transitions",
        json={"to_status": "已完成", "operator": "值班长"},
    )
    assert invalid.status_code == 400
    assert "不允许流转" in invalid.json()["detail"]

    options = client.get(f"/api/v1/issues/{issue['id']}/transitions").json()
    assert {option["status"] for option in options} == {"整改中", "已关闭"}

    processing = client.post(
        f"/api/v1/issues/{issue['id']}/transitions",
        json={"to_status": "整改中", "operator": "保洁班组张伟", "remark": "已安排清洗"},
    ).json()
    assert processing["status"] == "整改中"
    assert processing["assignee"] == "保洁班组"

    reviewing = client.post(
        f"/api/v1/issues/{issue['id']}/transitions",
        json={"to_status": "待验收", "operator": "保洁班组张伟", "remark": "整改完成待验收"},
    ).json()
    assert reviewing["status"] == "待验收"

    # 验收驳回回到整改中
    rejected = client.post(
        f"/api/v1/issues/{issue['id']}/transitions",
        json={"to_status": "整改中", "operator": "王巡查", "remark": "角落仍有残留"},
    ).json()
    assert rejected["status"] == "整改中"
    assert rejected["records"][-1]["action"] == "验收驳回"

    for target in ("待验收", "已完成", "已关闭"):
        payload = {"to_status": target, "operator": "值班长", "remark": f"流转到{target}"}
        response = client.post(f"/api/v1/issues/{issue['id']}/transitions", json=payload)
        assert response.status_code == 200, response.text
    final = response.json()
    assert final["status"] == "已关闭"
    assert final["closed_at"] is not None
    assert [record["to_status"] for record in final["records"]][-1] == "已关闭"

    closed_record = client.post(
        f"/api/v1/issues/{issue['id']}/records",
        json={"action": "整改进度", "operator": "值班长", "remark": "补充说明"},
    )
    assert closed_record.status_code == 400

    overdue = client.get("/api/v1/issues", params={"overdue": "true"}).json()
    assert overdue["meta"]["total"] == 0

    # 巡查记录可反查关联问题数量
    detail = client.get(f"/api/v1/inspections/{inspection['id']}").json()
    assert detail["issue_count"] == 1


def test_issue_requires_matching_restroom(client, restroom):
    other = client.post(
        "/api/v1/restrooms",
        json={"name": "另一座公厕", "district": "测试区", "address": "测试路 2 号"},
    ).json()
    inspection = client.post(
        "/api/v1/inspections",
        json={"restroom_id": other["id"], "inspector": "周巡查", "items": full_items(9)},
    ).json()
    mismatch = client.post(
        "/api/v1/issues",
        json={
            "restroom_id": restroom["id"],
            "inspection_id": inspection["id"],
            "title": "关联错误",
        },
    )
    assert mismatch.status_code == 400
    assert "不一致" in mismatch.json()["detail"]


def test_dashboard_stats(client, restroom):
    payload = client.get("/api/v1/stats/dashboard", params={"days": 7, "mode": "current"}).json()
    range_meta = payload["range"]
    assert range_meta["mode"] == "current"
    assert range_meta["days"] == 7
    assert range_meta["date_from"] <= range_meta["date_to"]

    overview = payload["overview"]
    assert overview["restroom_total"] >= 1
    assert overview["inspection_total"] >= 1
    assert len(payload["inspection_trend"]) == 7
    assert {item["name"] for item in payload["issue_by_status"]} == {
        "待整改",
        "整改中",
        "待验收",
        "已完成",
        "已关闭",
    }
    assert payload["top_restrooms"]
    assert "rectification_rate" in overview


def _create_issue(client, restroom_id, *, category="保洁不到位", severity="一般", days_ago=0):
    return client.post(
        "/api/v1/issues",
        json={
            "restroom_id": restroom_id,
            "title": f"{category}-{days_ago}天前",
            "category": category,
            "severity": severity,
            "reporter": "测试巡查员",
            "report_time": (datetime.now() - timedelta(days=days_ago)).isoformat(),
        },
    ).json()


def test_dashboard_range_consistency_and_detail_reconciliation(client, restroom):
    """指标卡 / 趋势 / 明细三处合计必须一致：看板区间与明细列表同口径过滤。"""
    # 测试库为会话级共享，先记录基线，再用增量断言区间口径
    before = client.get(
        "/api/v1/stats/dashboard", params={"days": 7, "mode": "current"}
    ).json()
    base_insp = before["overview"]["inspection_total"]
    base_issue = before["overview"]["issue_total"]

    # 区间内新增 2 条巡查、区间外 1 条
    for days_ago in (0, 2):
        client.post(
            "/api/v1/inspections",
            json={
                "restroom_id": restroom["id"],
                "inspector": "区间巡查员",
                "shift": "早班",
                "items": full_items(9),
                "inspect_time": (datetime.now() - timedelta(days=days_ago)).isoformat(),
            },
        )
    client.post(
        "/api/v1/inspections",
        json={
            "restroom_id": restroom["id"],
            "inspector": "区间外巡查员",
            "shift": "早班",
            "items": full_items(9),
            "inspect_time": (datetime.now() - timedelta(days=10)).isoformat(),
        },
    )
    _create_issue(client, restroom["id"], days_ago=1)
    _create_issue(client, restroom["id"], category="设施损坏", severity="严重", days_ago=3)
    _create_issue(client, restroom["id"], days_ago=9)

    payload = client.get(
        "/api/v1/stats/dashboard", params={"days": 7, "mode": "current"}
    ).json()
    meta = payload["range"]

    # 区间内恰好新增 2 条巡查、2 个问题，区间外的不计入
    assert payload["overview"]["inspection_total"] == base_insp + 2
    assert payload["overview"]["issue_total"] == base_issue + 2

    # 趋势按天合计 == 指标卡合计
    assert sum(p["inspections"] for p in payload["inspection_trend"]) == payload["overview"][
        "inspection_total"
    ]
    assert sum(p["issues"] for p in payload["inspection_trend"]) == payload["overview"][
        "issue_total"
    ]
    # 分布合计 == 指标卡合计
    assert sum(i["value"] for i in payload["issue_by_status"]) == payload["overview"][
        "issue_total"
    ]
    assert sum(i["value"] for i in payload["issue_by_severity"]) == payload["overview"][
        "issue_total"
    ]
    assert sum(i["total"] for i in payload["issue_by_category"]) == payload["overview"][
        "issue_total"
    ]

    # 明细列表用看板返回的 date_from/date_to 过滤，合计必须与看板完全一致
    issues = client.get(
        "/api/v1/issues",
        params={"date_from": meta["date_from"], "date_to": meta["date_to"]},
    ).json()
    assert issues["meta"]["total"] == payload["overview"]["issue_total"]
    inspections = client.get(
        "/api/v1/inspections",
        params={"date_from": meta["date_from"], "date_to": meta["date_to"]},
    ).json()
    assert inspections["meta"]["total"] == payload["overview"]["inspection_total"]

    # 区间外的记录确实只出现在更宽的明细查询里
    wide = client.get(
        "/api/v1/inspections",
        params={
            "date_from": (datetime.now().date() - timedelta(days=12)).isoformat(),
            "date_to": meta["date_to"],
        },
    ).json()
    assert wide["meta"]["total"] >= inspections["meta"]["total"] + 1

    # 分类下钻：看板分类数 == 带分类+区间条件的明细数
    cleaning = next(i for i in payload["issue_by_category"] if i["category"] == "保洁不到位")
    drilling = client.get(
        "/api/v1/issues",
        params={
            "date_from": meta["date_from"],
            "date_to": meta["date_to"],
            "category": "保洁不到位",
        },
    ).json()
    assert drilling["meta"]["total"] == cleaning["total"]

    # 区域下钻：看板区域问题数 == 带区域+区间条件的明细数
    district_row = next(row for row in payload["districts"] if row["district"] == "测试区")
    by_district = client.get(
        "/api/v1/issues",
        params={
            "date_from": meta["date_from"],
            "date_to": meta["date_to"],
            "district": "测试区",
        },
    ).json()
    assert by_district["meta"]["total"] == district_row["issue_count"]


def test_dashboard_compare_periods_are_disjoint_and_equal_length(client, restroom):
    """环比为紧邻的上一等长区间，同比为去年同期，二者与本期互不重叠。"""
    current = client.get(
        "/api/v1/stats/dashboard", params={"days": 7, "mode": "current"}
    ).json()["range"]
    mom = client.get("/api/v1/stats/dashboard", params={"days": 7, "mode": "mom"}).json()[
        "range"
    ]
    yoy = client.get(
        "/api/v1/stats/dashboard", params={"days": 7, "mode": "yoy"}
    ).json()["range"]

    assert mom["days"] == yoy["days"] == current["days"] == 7
    # 环比区间紧接本期之前、等长且不重叠
    from datetime import date as date_cls

    cur_from = date_cls.fromisoformat(current["date_from"])
    mom_to = date_cls.fromisoformat(mom["date_to"])
    mom_from = date_cls.fromisoformat(mom["date_from"])
    assert (cur_from - mom_to).days == 1
    assert (mom_to - mom_from).days == 6
    # 同比恰好在一年前
    yoy_from = date_cls.fromisoformat(yoy["date_from"])
    assert (cur_from - yoy_from).days in (365, 366)
    assert yoy["date_from"] < mom["date_from"]


def test_dashboard_empty_period_is_marked_not_zero(client, restroom):
    """去年同期没有任何业务数据时，要明确返回无数据标记，均分/闭环率为 null 而非 0。"""
    payload = client.get(
        "/api/v1/stats/dashboard", params={"days": 30, "mode": "yoy"}
    ).json()
    assert payload["has_inspections"] is False
    assert payload["has_issues"] is False
    overview = payload["overview"]
    assert overview["inspection_total"] == 0
    assert overview["issue_total"] == 0
    assert overview["avg_score"] is None
    assert overview["rectification_rate"] is None
    # 趋势仍给出完整日期骨架，但每日均分也是 null
    assert len(payload["inspection_trend"]) == 30
    assert all(point["avg_score"] is None for point in payload["inspection_trend"])

    # 有巡查无问题：巡查均分有值，问题闭环率仍须为 null
    # 把巡查写到去年同期窗口，该窗口在整个测试会话中没有问题数据
    client.post(
        "/api/v1/inspections",
        json={
            "restroom_id": restroom["id"],
            "inspector": "去年巡查员",
            "items": full_items(8),
            "inspect_time": (datetime.now() - timedelta(days=365)).isoformat(),
        },
    )
    yoy_again = client.get(
        "/api/v1/stats/dashboard", params={"days": 7, "mode": "yoy"}
    ).json()
    assert yoy_again["has_inspections"] is True
    assert yoy_again["has_issues"] is False
    assert yoy_again["overview"]["avg_score"] == 80.0
    assert yoy_again["overview"]["rectification_rate"] is None


def test_dashboard_invalid_mode_rejected(client):
    bad = client.get("/api/v1/stats/dashboard", params={"mode": "half_year"})
    assert bad.status_code == 422
