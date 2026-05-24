import sys
import os
import re
import json
import shutil
import traceback
from datetime import datetime

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QDateEdit, QTableWidget,
                             QTableWidgetItem, QHeaderView, QMessageBox, QTextEdit,
                             QGroupBox, QSplitter, QDialog)
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QFont

from ..config import (get_app_data_dir, SESSDATA, BILI_JCT, BUVID3, DEDEUSERID,
                      AC_TIME_VALUE, MAX_UP_COUNT, CONFIG_FILE, TIMEZONE_CN)
from ..storage import save_daily_video_data, load_daily_video_data, get_daily_data_path
from ..api import StatThread
from ..excel_export import export_excel
from .styles import MAIN_STYLE
from .dialogs import CookieSettingsDialog, VideoSelectionDialog


class BiliStatTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.up_list = []
        self.stat_thread = None
        self.final_rank_data = []
        self.raw_video_data_backup = []
        self.init_ui()
        self.load_up_list()

    def init_ui(self):
        self.setWindowTitle("B站UP主7天播放量统计工具")
        self.setGeometry(100, 100, 1500, 850)
        self.setStyleSheet(MAIN_STYLE)
        mw = QWidget()
        self.setCentralWidget(mw)
        ml = QVBoxLayout(mw)
        ml.setSpacing(15)
        ml.setContentsMargins(15, 15, 15, 15)

        cg = QGroupBox("统计配置")
        cl = QHBoxLayout(cg)
        cl.addWidget(QLabel("开始日期："))
        self.sd = QDateEdit(QDate.currentDate().addDays(-7))
        self.sd.setDisplayFormat("yyyy-MM-dd")
        self.sd.setCalendarPopup(True)
        cl.addWidget(self.sd)
        cl.addWidget(QLabel("结束日期："))
        self.ed = QDateEdit(QDate.currentDate())
        self.ed.setDisplayFormat("yyyy-MM-dd")
        self.ed.setCalendarPopup(True)
        cl.addWidget(self.ed)

        self.stb = QPushButton("开始统计")
        self.stb.setFixedSize(120, 38)
        self.stb.clicked.connect(self.start_stat)
        cl.addWidget(self.stb)

        self.spb = QPushButton("停止统计")
        self.spb.setFixedSize(120, 38)
        self.spb.setProperty("cssClass", "danger")
        self.spb.setStyleSheet(self.spb.styleSheet())
        self.spb.clicked.connect(self.stop_stat)
        self.spb.setEnabled(False)
        cl.addWidget(self.spb)

        self.exb = QPushButton("导出Excel")
        self.exb.setFixedSize(120, 38)
        self.exb.clicked.connect(self.export_excel)
        self.exb.setEnabled(False)
        cl.addWidget(self.exb)

        self.fib = QPushButton("筛选作品")
        self.fib.setFixedSize(120, 38)
        self.fib.clicked.connect(self.open_filter_dialog)
        self.fib.setEnabled(False)
        cl.addWidget(self.fib)

        self.seb = QPushButton("Cookie设置")
        self.seb.setFixedSize(120, 38)
        self.seb.setProperty("cssClass", "secondary")
        self.seb.clicked.connect(self.open_settings)
        cl.addWidget(self.seb)

        self.heb = QPushButton("使用帮助")
        self.heb.setFixedSize(120, 38)
        self.heb.setProperty("cssClass", "secondary")
        self.heb.clicked.connect(self.open_help)
        cl.addWidget(self.heb)
        cl.addStretch()
        ml.addWidget(cg)

        sp = QSplitter(Qt.Horizontal)
        sp.setStretchFactor(0, 3)
        sp.setStretchFactor(1, 7)
        upw = QWidget()
        upl = QVBoxLayout(upw)
        upl.setContentsMargins(0, 0, 0, 0)
        upl.addWidget(QLabel(f"UP主管理（最多{MAX_UP_COUNT}个）"))
        aul = QHBoxLayout()
        aul.addWidget(QLabel("UID："))
        self.uid = QLineEdit()
        self.uid.setPlaceholderText("纯数字UID")
        aul.addWidget(self.uid)
        aul.addWidget(QLabel("昵称："))
        self.nk = QLineEdit()
        self.nk.setPlaceholderText("UP主昵称")
        aul.addWidget(self.nk)
        self.ab = QPushButton("添加")
        self.ab.clicked.connect(self.add_up)
        aul.addWidget(self.ab)
        upl.addLayout(aul)

        bal = QHBoxLayout()
        self.bt = QTextEdit()
        self.bt.setPlaceholderText("批量导入：\nUID,昵称")
        self.bt.setFixedHeight(100)
        bal.addWidget(self.bt)
        bbl = QVBoxLayout()
        self.ba = QPushButton("批量添加")
        self.ba.clicked.connect(self.batch_add_up)
        bbl.addWidget(self.ba)
        self.cb = QPushButton("清空列表")
        self.cb.clicked.connect(self.clear_up_list)
        bbl.addWidget(self.cb)
        bal.addLayout(bbl)
        upl.addLayout(bal)
        upl.addWidget(QLabel("已添加UP主："))
        self.ult = QTextEdit()
        self.ult.setReadOnly(True)
        upl.addWidget(self.ult)
        upw.setFixedWidth(420)
        sp.addWidget(upw)

        daw = QWidget()
        dal = QVBoxLayout(daw)
        dal.setContentsMargins(0, 0, 0, 0)
        dal.addWidget(QLabel("视频7天播放量统计详情："))
        self.vt = QTableWidget()
        self.vt.setColumnCount(7)
        self.vt.setHorizontalHeaderLabels(["UP主昵称", "视频标题", "BV号", "发布时间", "7天播放量", "统计天数", "状态"])
        self.vt.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.vt.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.vt.setEditTriggers(QTableWidget.NoEditTriggers)
        self.vt.setAlternatingRowColors(True)
        dal.addWidget(self.vt)
        dal.addWidget(QLabel("运行日志："))
        self.logt = QTextEdit()
        self.logt.setReadOnly(True)
        self.logt.setFixedHeight(150)
        dal.addWidget(self.logt)
        sp.addWidget(daw)
        ml.addWidget(sp)

    def open_settings(self):
        CookieSettingsDialog(self).exec_()

    def open_help(self):
        QMessageBox.about(self, "使用帮助",
                          "1.添加UP主UID和昵称\n2.设置时间(默认是7天前)\n3.每日点击【开始统计】\n4.已结算视频自动锁定\n5.导出Excel\n\n⚠️ 重要提示：请务必在Cookie设置中填写完整的SESSDATA、bili_jct和buvid3！")

    def closeEvent(self, e):
        if self.stat_thread and self.stat_thread.isRunning():
            self.stat_thread.requestInterruption()
            self.stat_thread.wait(3000)
        e.accept()

    def load_up_list(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.up_list = json.load(f)
                self.up_list = [u for u in self.up_list if u.get("uid") and u.get("nickname")]
                self.refresh_up_list_text()
            except:
                self.up_list = []

    def save_up_list(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.up_list, f, ensure_ascii=False, indent=2)

    def refresh_up_list_text(self):
        t = ""
        for i, u in enumerate(self.up_list, 1):
            t += f"{i}.{u['nickname']}（UID:{u['uid']}）\n"
        self.ult.setText(t)

    def add_up(self):
        u = self.uid.text().strip()
        n = self.nk.text().strip()
        if not u or not n:
            QMessageBox.warning(self, "提示", "UID和昵称不能为空")
            return
        if not re.match(r'^\d+$', u):
            QMessageBox.warning(self, "提示", "UID必须纯数字")
            return
        if len(self.up_list) >= MAX_UP_COUNT:
            QMessageBox.warning(self, "提示", f"最多{MAX_UP_COUNT}个")
            return
        if any(str(x["uid"]) == str(u) for x in self.up_list):
            QMessageBox.warning(self, "提示", "已存在")
            return
        self.up_list.append({"uid": u, "nickname": n})
        self.save_up_list()
        self.refresh_up_list_text()
        self.uid.clear()
        self.nk.clear()
        self.log(f"已添加：{n}")

    def batch_add_up(self):
        t = self.bt.toPlainText().strip().replace("，", ",")
        if not t:
            QMessageBox.warning(self, "提示", "请输入内容")
            return
        c = 0
        for line in t.split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) != 2:
                continue
            uid, name = parts[0].strip(), parts[1].strip()
            if not re.match(r'^\d+$', uid) or not name:
                continue
            if len(self.up_list) >= MAX_UP_COUNT:
                break
            if any(str(x["uid"]) == str(uid) for x in self.up_list):
                continue
            self.up_list.append({"uid": uid, "nickname": name})
            c += 1
        if c > 0:
            self.save_up_list()
            self.refresh_up_list_text()
            self.bt.clear()
            self.log(f"批量添加{c}个")
        else:
            QMessageBox.warning(self, "提示", "无有效数据")

    def clear_up_list(self):
        if QMessageBox.question(self, "确认", "清空所有？") == QMessageBox.Yes:
            self.up_list = []
            self.save_up_list()
            self.refresh_up_list_text()
            self.log("已清空")

    def start_stat(self):
        if not self.up_list:
            QMessageBox.warning(self, "提示", "请添加UP主")
            return
        sdt = self.sd.date().toPyDate()
        edt = self.ed.date().toPyDate()
        if sdt > edt:
            QMessageBox.warning(self, "提示", "开始日期不能晚于结束日期")
            return
        sdt_full = datetime.combine(sdt, datetime.min.time(), tzinfo=TIMEZONE_CN)
        edt_full = datetime.combine(edt, datetime.max.time(), tzinfo=TIMEZONE_CN)
        now = datetime.now(tz=TIMEZONE_CN)
        if edt_full > now:
            edt_full = now
        self.vt.setRowCount(0)
        self.logt.clear()
        self.exb.setEnabled(False)
        self.fib.setEnabled(False)
        self.stb.setEnabled(False)
        self.spb.setEnabled(True)

        self.stat_thread = StatThread(self.up_list, sdt_full, edt_full, SESSDATA, BILI_JCT, BUVID3, DEDEUSERID,
                                      AC_TIME_VALUE)
        self.stat_thread.log_signal.connect(self.log)
        self.stat_thread.table_signal.connect(self.refresh_table)
        self.stat_thread.finish_signal.connect(self.stat_finish)
        self.stat_thread.error_signal.connect(self.log)
        self.stat_thread.start()

    def stop_stat(self):
        if self.stat_thread and self.stat_thread.isRunning():
            self.stat_thread.requestInterruption()
            self.stat_thread.wait(2000)
            self.log("已停止")
        self.stb.setEnabled(True)
        self.spb.setEnabled(False)

    def refresh_table(self, data):
        self.vt.setRowCount(len(data))
        keys = ["nickname", "title", "bvid", "pub_time", "current_play", "stat_days", "play_tag"]
        for row, item in enumerate(data):
            for col, key in enumerate(keys):
                val = str(item.get(key, ""))
                table_item = QTableWidgetItem(val)
                self.vt.setItem(row, col, table_item)
                if col != 1:
                    table_item.setTextAlignment(Qt.AlignCenter)
        self.vt.scrollToBottom()

    def stat_finish(self, rank_data):
        self.final_rank_data = rank_data
        self.raw_video_data_backup = []
        for row in range(self.vt.rowCount()):
            data = {}
            keys = ["nickname", "title", "bvid", "pub_time", "current_play", "stat_days", "play_tag"]
            for col, key in enumerate(keys):
                item = self.vt.item(row, col)
                data[key] = item.text() if item else ""
            try:
                for up in self.up_list:
                    if up["nickname"] == data["nickname"]:
                        data["uid"] = int(up["uid"])
                        break
                else:
                    data["uid"] = 0
            except:
                data["uid"] = 0
            try:
                data["current_play"] = int(data["current_play"])
                data["stat_days"] = int(data["stat_days"])
            except:
                data["current_play"] = 0
                data["stat_days"] = 0
            self.raw_video_data_backup.append(data)

        self.log("\n===== 统计完成 =====")
        self.log("✅ 已结算视频：数据永久锁定")
        self.log("🔄 统计中视频：次日将自动更新")
        for item in rank_data:
            self.log(f"{item['rank']}. {item['nickname']}：{item['total_play']}")
        self.stb.setEnabled(True)
        self.spb.setEnabled(False)
        self.exb.setEnabled(True)
        self.fib.setEnabled(True)
        QMessageBox.information(self, "完成", "统计完成！\n已结算视频锁定，统计中视频次日更新")
        backup_dir = os.path.join(get_app_data_dir(), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        backup_file = os.path.join(backup_dir, f"video_7day_data_{datetime.now().strftime('%Y%m%d')}.json")
        try:
            shutil.copy(get_daily_data_path(), backup_file)
            self.log(f"✅ 数据已备份至：{backup_file}")
        except Exception as e:
            self.log(f"⚠️ 备份失败：{str(e)}")

    def export_excel(self):
        fp = export_excel(self, self.raw_video_data_backup, self.final_rank_data)
        if fp:
            self.log(f"✅ 导出完整历史数据成功：{fp}")

    def open_filter_dialog(self):
        if not self.raw_video_data_backup:
            QMessageBox.warning(self, "提示", "暂无视频数据")
            return
        dialog = VideoSelectionDialog(self.raw_video_data_backup, self)
        if dialog.exec_() == QDialog.Accepted:
            if hasattr(dialog, 'result_data'):
                filtered = dialog.result_data
            else:
                filtered = [it["data"] for it in dialog.data_list if it["selected"]]

            if not filtered:
                QMessageBox.warning(self, "提示", "筛选结果为空，无法更新")
                return

            self.raw_video_data_backup = filtered
            self.refresh_table(filtered)

            total_map = {}
            for video in filtered:
                uid = video.get("uid", 0)
                nick = video.get("nickname", "")
                try:
                    play = int(video.get("current_play", 0))
                except:
                    play = 0
                if uid not in total_map:
                    total_map[uid] = {"uid": uid, "nickname": nick, "total_play": 0}
                total_map[uid]["total_play"] += play

            ranked = sorted(total_map.values(), key=lambda x: (-x["total_play"], x["nickname"]))
            for i, item in enumerate(ranked, 1):
                item["rank"] = i
            self.final_rank_data = ranked

            self.log(f"\n===== 筛选完成 =====")
            self.log(f"已保留 {len(filtered)} 个视频")
            for item in ranked[:10]:
                self.log(f"{item['rank']}. {item['nickname']}：{item['total_play']}")
            QMessageBox.information(self, "完成", f"筛选完成！\n当前显示 {len(filtered)} 个视频")

    def log(self, text):
        self.logt.append(f"[{datetime.now().strftime('%H:%M:%S')}] {text}")
        self.logt.verticalScrollBar().setValue(self.logt.verticalScrollBar().maximum())


def except_hook(t, v, tb):
    if issubclass(t, KeyboardInterrupt):
        sys.__excepthook__(t, v, tb)
        return
    log_dir = os.path.join(get_app_data_dir(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"crash_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write("".join(traceback.format_exception(t, v, tb)))
    try:
        QMessageBox.critical(None, "程序异常", f"错误已保存至：\n{log_file}")
    except:
        pass


def main():
    sys.excepthook = except_hook
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 9))
    window = BiliStatTool()
    window.show()
    sys.exit(app.exec_())
