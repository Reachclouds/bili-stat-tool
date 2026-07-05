import os
import json
import copy
from datetime import datetime

from .config import get_app_data_dir, TIMEZONE_CN

SETTLEMENT_CONFIG_FILE = os.path.join(get_app_data_dir(), "settlement_config.json")
SETTLEMENT_RESULT_FILE = os.path.join(get_app_data_dir(), "settlement_result.json")

DEFAULT_TIERS = [
    {"name": "第一档", "threshold": 100000, "pool": 10000.0, "max_per_person": 5000.0, "sort_order": 1},
    {"name": "第二档", "threshold": 50000,  "pool": 8000.0,  "max_per_person": 3000.0, "sort_order": 2},
    {"name": "第三档", "threshold": 30000,  "pool": 6000.0,  "max_per_person": 2000.0, "sort_order": 3},
    {"name": "第四档", "threshold": 10000,  "pool": 4000.0,  "max_per_person": 1000.0, "sort_order": 4},
    {"name": "第五档", "threshold": 5000,   "pool": 2500.0,  "max_per_person": 500.0,  "sort_order": 5},
    {"name": "第六档", "threshold": 2000,   "pool": 1500.0,  "max_per_person": 300.0,  "sort_order": 6},
    {"name": "第七档", "threshold": 1000,   "pool": 800.0,   "max_per_person": 150.0,  "sort_order": 7},
]


def _default_config():
    return copy.deepcopy(DEFAULT_TIERS)


def load_settlement_config():
    if os.path.exists(SETTLEMENT_CONFIG_FILE):
        try:
            with open(SETTLEMENT_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    for t in data:
                        t.setdefault("sort_order", 0)
                    return data
        except:
            pass
    return _default_config()


def save_settlement_config(config):
    temp_path = SETTLEMENT_CONFIG_FILE + ".tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        if os.path.exists(SETTLEMENT_CONFIG_FILE):
            os.replace(temp_path, SETTLEMENT_CONFIG_FILE)
        else:
            os.rename(temp_path, SETTLEMENT_CONFIG_FILE)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def load_settlement_result():
    if os.path.exists(SETTLEMENT_RESULT_FILE):
        try:
            with open(SETTLEMENT_RESULT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return None


def save_settlement_result(result):
    temp_path = SETTLEMENT_RESULT_FILE + ".tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        if os.path.exists(SETTLEMENT_RESULT_FILE):
            os.replace(temp_path, SETTLEMENT_RESULT_FILE)
        else:
            os.rename(temp_path, SETTLEMENT_RESULT_FILE)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def aggregate_up_views(video_data, start_date=None, end_date=None):
    """按UID聚合UP主7日有效播放量。

    video_data: list[dict], 每条记录含 uid, nickname, current_play, excluded, pub_time 等
    start_date / end_date: datetime (timezone-aware) 过滤视频发布时间范围
    返回: {uid: {"nickname": str, "total_views": int}}
    """
    result = {}
    for v in video_data:
        if v.get("excluded", False):
            continue
        pub_str = v.get("pub_time", "")
        if start_date or end_date:
            try:
                if len(pub_str) == 10:
                    pub_dt = datetime.strptime(pub_str, "%Y-%m-%d").replace(tzinfo=TIMEZONE_CN)
                elif len(pub_str) >= 16:
                    pub_dt = datetime.strptime(pub_str[:16], "%Y-%m-%d %H:%M").replace(tzinfo=TIMEZONE_CN)
                else:
                    continue
                if start_date and pub_dt < start_date:
                    continue
                if end_date and pub_dt > end_date:
                    continue
            except ValueError:
                continue
        uid = v.get("uid", 0)
        if not uid:
            continue
        play = v.get("current_play", 0) or v.get("final_play", 0)
        try:
            play = int(play)
        except (ValueError, TypeError):
            play = 0
        if uid not in result:
            result[uid] = {"nickname": v.get("nickname", ""), "total_views": 0}
        result[uid]["total_views"] += play
    return result


def calculate_settlement(tiers, up_play_data):
    """执行4步结算算法。

    tiers: list[dict], 每个含 name/threshold/pool/max_per_person/sort_order
    up_play_data: dict, {uid: {"nickname": str, "total_views": int}}
    返回: dict 结算结果
    """
    # 档位按门槛降序（最高档在前）
    sorted_tiers = sorted(tiers, key=lambda t: (-t["threshold"], t.get("sort_order", 0)))

    # UP主按播放量降序排列
    up_list = sorted(up_play_data.items(), key=lambda x: -x[1]["total_views"])

    # 档位分配：每UP主归属到最高达标档位
    tier_members = {t["name"]: [] for t in sorted_tiers}
    assigned = set()
    for uid, info in up_list:
        views = info["total_views"]
        for t in sorted_tiers:
            if views >= t["threshold"]:
                tier_members[t["name"]].append({
                    "uid": uid,
                    "nickname": info["nickname"],
                    "individual_views": views,
                })
                assigned.add(uid)
                break

    # 逐档位执行4步结算
    tier_results = []
    for t in sorted_tiers:
        members = tier_members[t["name"]]
        qualified_count = len(members)
        total_qualified_views = sum(m["individual_views"] for m in members)

        pool = t["pool"]
        max_per = t["max_per_person"]
        distributed = 0.0
        overflow = 0.0

        for m in members:
            if total_qualified_views > 0:
                ratio = m["individual_views"] / total_qualified_views
                estimated = pool * ratio
            else:
                ratio = 0.0
                estimated = 0.0

            if estimated > max_per:
                actual = max_per
                m["capped"] = True
                overflow += (estimated - actual)
            else:
                actual = estimated
                m["capped"] = False

            m["ratio"] = ratio
            m["estimated"] = round(estimated, 2)
            m["actual"] = round(actual, 2)
            distributed += actual

        remaining_pool = round(pool - distributed - overflow, 2)
        overflow = round(overflow, 2)

        tier_results.append({
            "tier_name": t["name"],
            "threshold": t["threshold"],
            "pool": pool,
            "max_per_person": max_per,
            "qualified_count": qualified_count,
            "total_qualified_views": total_qualified_views,
            "members": members,
            "overflow": overflow,
            "remaining_pool": remaining_pool,
            "total_distributed": round(distributed, 2),
        })

    unassigned = []
    for uid, info in up_list:
        if uid not in assigned:
            unassigned.append({
                "uid": uid,
                "nickname": info["nickname"],
                "individual_views": info["total_views"],
            })

    return {
        "tier_results": tier_results,
        "unassigned": unassigned,
        "settlement_time": datetime.now(TIMEZONE_CN).strftime("%Y-%m-%d %H:%M:%S"),
    }


def calculate_equal_settlement(tiers, up_play_data):
    """执行平分奖池结算算法。

    档位归属与 calculate_settlement 相同，但每个档位内均分奖池：
    per_person = min(pool / qualified_count, max_per_person)
    """
    sorted_tiers = sorted(tiers, key=lambda t: (-t["threshold"], t.get("sort_order", 0)))
    up_list = sorted(up_play_data.items(), key=lambda x: -x[1]["total_views"])

    tier_members = {t["name"]: [] for t in sorted_tiers}
    assigned = set()
    for uid, info in up_list:
        views = info["total_views"]
        for t in sorted_tiers:
            if views >= t["threshold"]:
                tier_members[t["name"]].append({
                    "uid": uid,
                    "nickname": info["nickname"],
                    "individual_views": views,
                })
                assigned.add(uid)
                break

    tier_results = []
    for t in sorted_tiers:
        members = tier_members[t["name"]]
        qualified_count = len(members)
        total_qualified_views = sum(m["individual_views"] for m in members)

        pool = t["pool"]
        max_per = t["max_per_person"]
        distributed = 0.0
        overflow = 0.0

        equal_share = pool / qualified_count if qualified_count > 0 else 0.0

        for m in members:
            if equal_share > max_per:
                actual = max_per
                m["capped"] = True
                overflow += (equal_share - actual)
            else:
                actual = equal_share
                m["capped"] = False

            m["ratio"] = 1.0 / qualified_count if qualified_count > 0 else 0.0
            m["estimated"] = round(equal_share, 2)
            m["actual"] = round(actual, 2)
            distributed += actual

        remaining_pool = round(pool - distributed - overflow, 2)
        overflow = round(overflow, 2)

        tier_results.append({
            "tier_name": t["name"],
            "threshold": t["threshold"],
            "pool": pool,
            "max_per_person": max_per,
            "qualified_count": qualified_count,
            "total_qualified_views": total_qualified_views,
            "members": members,
            "overflow": overflow,
            "remaining_pool": remaining_pool,
            "total_distributed": round(distributed, 2),
        })

    unassigned = []
    for uid, info in up_list:
        if uid not in assigned:
            unassigned.append({
                "uid": uid,
                "nickname": info["nickname"],
                "individual_views": info["total_views"],
            })

    return {
        "tier_results": tier_results,
        "unassigned": unassigned,
        "settlement_time": datetime.now(TIMEZONE_CN).strftime("%Y-%m-%d %H:%M:%S"),
        "settlement_mode": "equal",
    }


# ====================== 平分奖池结算结果 持久化 ======================
EQUAL_SETTLEMENT_RESULT_FILE = os.path.join(get_app_data_dir(), "equal_settlement_result.json")


def load_equal_settlement_result():
    if os.path.exists(EQUAL_SETTLEMENT_RESULT_FILE):
        try:
            with open(EQUAL_SETTLEMENT_RESULT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return None


def save_equal_settlement_result(result):
    temp_path = EQUAL_SETTLEMENT_RESULT_FILE + ".tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        if os.path.exists(EQUAL_SETTLEMENT_RESULT_FILE):
            os.replace(temp_path, EQUAL_SETTLEMENT_RESULT_FILE)
        else:
            os.rename(temp_path, EQUAL_SETTLEMENT_RESULT_FILE)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise
