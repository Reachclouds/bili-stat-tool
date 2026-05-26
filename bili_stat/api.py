import re
import random
import time
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal
from bilibili_api import user, sync, Credential, request_settings
from bilibili_api.video import Video

from .config import TIMEZONE_CN
from .storage import save_daily_video_data, load_daily_video_data


class StatThread(QThread):
    log_signal = pyqtSignal(str)
    table_signal = pyqtSignal(list)
    finish_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)

    def __init__(self, up_list, start_date, end_date,
                 sessdata, bili_jct, buvid3, dedeuserid, ac_time_value,
                 proxy=None):
        super().__init__()
        self.up_list = up_list
        self.start_date = start_date
        self.end_date = end_date
        self.sessdata = sessdata
        self.bili_jct = bili_jct
        self.buvid3 = buvid3
        self.dedeuserid = dedeuserid
        self.ac_time_value = ac_time_value
        self.proxy = proxy
        self.current_page = 0
        self.daily_data = load_daily_video_data()

    # def _human_like_delay(self, delay_type="page"):
    #     if delay_type == "up":
    #         if random.random() < 0.3:
    #             delay = random.uniform(120, 300)
    #             self.log_signal.emit(f"  ☕ 模拟真人休息 {delay:.1f} 秒...")
    #         else:
    #             delay = random.uniform(30, 60)
    #             self.log_signal.emit(f"  ↳ 切换UP主，等待 {delay:.1f} 秒...")
    #     elif delay_type == "page":
    #         delay = random.uniform(120, 300)
    #         self.log_signal.emit(f"  ↳ 第 {self.current_page} 页完成，等待 {delay:.1f} 秒...")
    #     elif delay_type == "retry":
    #         delay = random.uniform(300, 600)
    #         self.log_signal.emit(f"  🚨 触发风控，强制冷却 {delay:.1f} 秒后重试...")
    #     elif delay_type == "video_info":
    #         delay = random.uniform(5, 15)
    #         self.log_signal.emit(f"  ↳ 获取共创信息，等待 {delay:.1f} 秒...")
    #     time.sleep(delay)
    def _human_like_delay(self, delay_type="page"):
        if delay_type == "up":
            if random.random() < 0.3:
                delay = random.uniform(5, 30)
                self.log_signal.emit(f"  ☕ 模拟真人休息 {delay:.1f} 秒...")
            else:
                delay = random.uniform(3, 20)
                self.log_signal.emit(f"  ↳ 切换UP主，等待 {delay:.1f} 秒...")
        elif delay_type == "page":
            delay = random.uniform(10, 30)
            self.log_signal.emit(f"  ↳ 第 {self.current_page} 页完成，等待 {delay:.1f} 秒...")
        elif delay_type == "retry":
            delay = random.uniform(300, 600)
            self.log_signal.emit(f"  🚨 触发风控，强制冷却 {delay:.1f} 秒后重试...")
        elif delay_type == "video_info":
            delay = random.uniform(5, 15)
            self.log_signal.emit(f"  ↳ 获取共创信息，等待 {delay:.1f} 秒...")
        time.sleep(delay)

    def _process_video(self, video, uid, nickname, now):
        pub_time = datetime.fromtimestamp(video["created"], tz=TIMEZONE_CN)
        if pub_time < self.start_date or pub_time > self.end_date:
            return None

        bvid = video["bvid"]
        title = re.sub(r'[\r\n\t]+', ' ', video["title"]).strip()
        days_diff = (now - pub_time).days

        excluded = self.daily_data.get(bvid, {}).get("excluded", False)

        attr = video.get("attribute", 0)
        is_collaborative = (attr >> 24) & 1 == 1
        collab_role = ""
        if is_collaborative:
            staff_list = video.get("staff", [])
            if not staff_list:
                try:
                    info = sync(Video(bvid).get_info())
                    staff_list = info.get("staff", [])
                    self._human_like_delay(delay_type="video_info")
                except Exception:
                    staff_list = []
            for s in staff_list:
                if s.get("mid") == uid:
                    collab_role = s.get("title", "")
                    break

        if days_diff >= 7:
            if bvid in self.daily_data:
                current_play = self.daily_data[bvid]["final_play"]
                play_tag = "已结算"
                stat_days = 7
            else:
                play_raw = video.get("play", 0)
                current_play = int(play_raw) if str(play_raw).isdigit() else 0
                play_tag = "已结算"
                stat_days = 7
                self.daily_data[bvid] = {
                    "uid": uid, "nickname": nickname, "title": title,
                    "pub_time": pub_time.strftime("%Y-%m-%d %H:%M"),
                    "bvid": bvid, "final_play": current_play,
                    "stat_days": stat_days, "status": play_tag,
                    "excluded": excluded,
                    "is_collaborative": is_collaborative,
                    "collab_role": collab_role,
                }
        else:
            play_raw = video.get("play", 0)
            current_play = int(play_raw) if str(play_raw).isdigit() else 0
            play_tag = "统计中"
            stat_days = days_diff + 1
            self.daily_data[bvid] = {
                "uid": uid, "nickname": nickname, "title": title,
                "pub_time": pub_time.strftime("%Y-%m-%d %H:%M"),
                "bvid": bvid, "final_play": current_play,
                "stat_days": stat_days, "status": play_tag,
                "excluded": excluded,
                "is_collaborative": is_collaborative,
                "collab_role": collab_role,
            }

        return {
            "uid": uid, "nickname": nickname, "title": title, "bvid": bvid,
            "pub_time": pub_time.strftime("%Y-%m-%d %H:%M"),
            "current_play": current_play, "stat_days": stat_days,
            "play_tag": play_tag,
            "is_collaborative": is_collaborative,
            "collab_role": collab_role,
        }

    def run(self):
        try:
            if self.proxy:
                request_settings.set_proxy(self.proxy)
                self.log_signal.emit(f"✅ 已启用代理：{self.proxy}")
            else:
                request_settings.set_proxy(None)

            request_settings.set("impersonate", "chrome131")
            request_settings.set("http2", True)
            self.log_signal.emit("✅ 已启用浏览器伪装（chrome131）")
        except Exception as e:
            self.log_signal.emit(f"⚠️ 代理/伪装设置失败：{e}")

        cred = None
        if self.sessdata and self.bili_jct and self.buvid3:
            try:
                cred = Credential(
                    sessdata=self.sessdata,
                    bili_jct=self.bili_jct,
                    buvid3=self.buvid3,
                    dedeuserid=self.dedeuserid,
                    ac_time_value=self.ac_time_value
                )
            except Exception as e:
                self.log_signal.emit(f"⚠️ Credential 创建失败：{e}")
        else:
            self.log_signal.emit("⚠️ Cookie 不完整，将使用游客模式")

        result_data = []
        up_total_list = []
        now = datetime.now(tz=TIMEZONE_CN)

        up_list_copy = self.up_list[:]
        random.shuffle(up_list_copy)
        for up in up_list_copy:
            if self.isInterruptionRequested():
                self.log_signal.emit("统计已被用户中断")
                save_daily_video_data(self.daily_data)
                return

            uid = int(up["uid"])
            nickname = up["nickname"]
            self.log_signal.emit(f"正在统计：{nickname}（UID:{uid}）")
            self.current_page = 0

            self._human_like_delay(delay_type="up")

            up_video_list = []
            up_total_play = 0
            page = 1
            has_more = True

            try:
                u = user.User(uid, credential=cred) if cred else user.User(uid)

                request_settings.set("headers", {
                    "Referer": f"https://space.bilibili.com/{uid}/video",
                    "Origin": "https://space.bilibili.com",
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache"
                })

                while has_more:
                    if self.isInterruptionRequested():
                        save_daily_video_data(self.daily_data)
                        return

                    res = sync(u.get_videos(pn=page, ps=30))
                    video_list = res.get("list", {}).get("vlist", [])
                    if not video_list:
                        has_more = False
                        break

                    earliest_time = datetime.fromtimestamp(video_list[-1]["created"], tz=TIMEZONE_CN)
                    if earliest_time < self.start_date:
                        has_more = False
                        for video in video_list:
                            processed = self._process_video(video, uid, nickname, now)
                            if processed:
                                up_video_list.append(processed)
                                up_total_play += processed["current_play"]
                        break

                    for video in video_list:
                        processed = self._process_video(video, uid, nickname, now)
                        if processed:
                            up_video_list.append(processed)
                            up_total_play += processed["current_play"]

                    if len(video_list) < 30:
                        has_more = False
                    page += 1
                    self.current_page = page

                    self._human_like_delay(delay_type="page")

            except Exception as e:
                err_str = str(e)
                if "412" in err_str or "Precondition Failed" in err_str:
                    self.log_signal.emit(f"❌ {nickname} 触发风控（412），先强制冷却...")
                    self._human_like_delay(delay_type="retry")
                    self.log_signal.emit(f"🔄 尝试游客模式获取 {nickname} 的投稿...")
                else:
                    self.error_signal.emit(f"获取 {nickname} 投稿失败：{err_str}")
                    continue

                try:
                    u = user.User(uid)
                    page = 1
                    has_more = True
                    temp_videos = []
                    while has_more:
                        if self.isInterruptionRequested():
                            self.log_signal.emit("统计已被用户中断")
                            save_daily_video_data(self.daily_data)
                            return

                        res = sync(u.get_videos(pn=page, ps=30))
                        video_list = res.get("list", {}).get("vlist", [])
                        if not video_list:
                            break

                        earliest_time = datetime.fromtimestamp(video_list[-1]["created"], tz=TIMEZONE_CN)
                        if earliest_time < self.start_date:
                            has_more = False
                            for video in video_list:
                                processed = self._process_video(video, uid, nickname, now)
                                if processed:
                                    temp_videos.append(processed)
                            break

                        for video in video_list:
                            processed = self._process_video(video, uid, nickname, now)
                            if processed:
                                temp_videos.append(processed)

                        if len(video_list) < 30:
                            has_more = False
                        page += 1
                        self.current_page = page
                        self._human_like_delay(delay_type="page")

                    up_video_list = temp_videos
                    up_total_play = sum(v["current_play"] for v in temp_videos)
                    self.log_signal.emit(f"✅ {nickname} 游客模式获取成功")
                except Exception as e2:
                    self.error_signal.emit(f"游客模式也失败：{str(e2)}")
                    continue

            result_data.extend(up_video_list)
            up_total_list.append({
                "nickname": nickname, "uid": uid, "total_play": up_total_play
            })
            self.table_signal.emit(result_data)

        save_daily_video_data(self.daily_data)
        up_total_list_sorted = sorted(up_total_list, key=lambda x: (-x["total_play"], x["nickname"]))
        for idx, item in enumerate(up_total_list_sorted, 1):
            item["rank"] = idx
        self.finish_signal.emit(up_total_list_sorted)
