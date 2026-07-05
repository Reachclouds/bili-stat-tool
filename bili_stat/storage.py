import os
import json
import shutil
import time
from datetime import datetime

from .config import get_app_data_dir


# ====================== 7天统计数据 本地存储+自动备份 ======================
def get_daily_data_path():
    return os.path.join(get_app_data_dir(), "video_7day_data.json")


def get_backup_dir():
    return os.path.join(get_app_data_dir(), "backups")


def clean_old_backups(retention_days=30):
    backup_dir = get_backup_dir()
    if not os.path.exists(backup_dir):
        return
    now = time.time()
    max_age = retention_days * 86400
    for f in os.listdir(backup_dir):
        path = os.path.join(backup_dir, f)
        try:
            if os.path.isfile(path) and (now - os.path.getmtime(path)) > max_age:
                os.remove(path)
        except:
            continue


def save_daily_video_data(data):
    data_path = get_daily_data_path()
    backup_dir = get_backup_dir()
    os.makedirs(backup_dir, exist_ok=True)

    temp_path = data_path + ".tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if os.path.exists(data_path):
            os.replace(temp_path, data_path)
        else:
            os.rename(temp_path, data_path)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise e

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"video_7day_backup_{timestamp}.json")
    try:
        shutil.copy2(data_path, backup_path)
    except:
        pass

    clean_old_backups(30)


def load_daily_video_data():
    path = get_daily_data_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                migrated = {}
                needs_migration = False
                for key, v in data.items():
                    if "excluded" not in v:
                        v["excluded"] = False
                    if "is_collaborative" not in v:
                        v["is_collaborative"] = False
                    if "collab_role" not in v:
                        v["collab_role"] = ""
                    # 向后兼容：旧格式 key 为纯 bvid，迁移为 uid_bvid
                    uid = v.get("uid", 0)
                    bvid = v.get("bvid", key)
                    new_key = f"{uid}_{bvid}"
                    if new_key != key:
                        needs_migration = True
                    migrated[new_key] = v
                if needs_migration:
                    save_daily_video_data(migrated)
                return migrated
        except:
            return {}
    return {}


# ====================== 统计进度 断点续传 ======================
def get_progress_path():
    return os.path.join(get_app_data_dir(), "stat_progress.json")


def save_stat_progress(completed_uids, start_date, end_date):
    path = get_progress_path()
    data = {
        "completed_uids": list(completed_uids),
        "start_date": start_date.date().isoformat() if hasattr(start_date, 'date') else str(start_date),
        "end_date": end_date.date().isoformat() if hasattr(end_date, 'date') else str(end_date),
        "timestamp": datetime.now().isoformat(),
    }
    temp_path = path + ".tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if os.path.exists(path):
            os.replace(temp_path, path)
        else:
            os.rename(temp_path, path)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def load_stat_progress():
    path = get_progress_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None


def clear_stat_progress():
    path = get_progress_path()
    if os.path.exists(path):
        try:
            os.remove(path)
        except:
            pass
