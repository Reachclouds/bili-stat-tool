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
                for bvid, v in data.items():
                    if "excluded" not in v:
                        v["excluded"] = False
                    if "is_collaborative" not in v:
                        v["is_collaborative"] = False
                    if "collab_role" not in v:
                        v["collab_role"] = ""
                return data
        except:
            return {}
    return {}
