import sys
import os
import re
import json
import traceback
from datetime import datetime

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QDateEdit, QTableWidget,
                             QTableWidgetItem, QHeaderView, QMessageBox, QTextEdit,
                             QGroupBox, QSplitter, QDialog, QCheckBox, QListWidget,
                             QListWidgetItem, QMenu, QAction, QAbstractItemView)
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QFont

from .. import config
from ..config import get_app_data_dir, MAX_UP_COUNT, CONFIG_FILE, TIMEZONE_CN
from ..storage import save_daily_video_data
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
        self.setGeometry(100, 100, 1400, 880)
        self.setStyleSheet(MAIN_STYLE)
        mw = QWidget()
        self.setCentralWidget(mw)
        ml = QVBoxLayout(mw)
        ml.setSpacing(15)
        ml.setContentsMargins(15, 15, 15, 15)

        cg = QGroupBox("统计配置")
        cvl = QVBoxLayout(cg)
        cvl.setSpacing(10)
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("开始日期："))
        self.sd = QDateEdit(QDate.currentDate().addDays(-7))
        self.sd.setDisplayFormat("yyyy-MM-dd")
        self.sd.setCalendarPopup(True)
        self.sd.setFixedWidth(130)
        row1.addWidget(self.sd)
        row1.addWidget(QLabel("结束日期："))
        self.ed = QDateEdit(QDate.currentDate())
        self.ed.setDisplayFormat("yyyy-MM-dd")
        self.ed.setCalendarPopup(True)
        self.ed.setFixedWidth(130)
        row1.addWidget(self.ed)

        self.stb = QPushButton("开始统计")
        self.stb.setFixedSize(120, 38)
        self.stb.clicked.connect(self.start_stat)
        row1.addWidget(self.stb)

        self.spb = QPushButton("停止统计")
        self.spb.setFixedSize(120, 38)
        self.spb.setProperty("cssClass", "danger")
        self.spb.setStyleSheet(self.spb.styleSheet())
        self.spb.clicked.connect(self.stop_stat)
        self.spb.setEnabled(False)
        row1.addWidget(self.spb)
        row1.addStretch()
        cvl.addLayout(row1)

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
        upl.addWidget(QLabel("已添加UP主（右键删除）："))
        self.ult = QListWidget()
        self.ult.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ult.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ult.customContextMenuRequested.connect(self.on_up_list_context_menu)
        self.ult.itemDoubleClicked.connect(self.on_up_item_double_clicked)
        upl.addWidget(self.ult)
        upw.setFixedWidth(380)
        sp.addWidget(upw)

        daw = QWidget()
        dal = QVBoxLayout(daw)
        dal.setContentsMargins(0, 0, 0, 0)
        dal.setSpacing(8)

        ttl = QHBoxLayout()
        ttl.addWidget(QLabel("视频7天播放量统计详情："))
        ttl.addStretch()
        self.exb = QPushButton("导出Excel")
        self.exb.setFixedSize(120, 34)
        self.exb.clicked.connect(self.export_excel)
        self.exb.setEnabled(False)
        ttl.addWidget(self.exb)
        self.fib = QPushButton("筛选作品")
        self.fib.setFixedSize(120, 34)
        self.fib.clicked.connect(self.open_filter_dialog)
        self.fib.setEnabled(False)
        ttl.addWidget(self.fib)
        dal.addLayout(ttl)

        self.vt = QTableWidget()
        self.vt.setColumnCount(8)
        self.vt.setHorizontalHeaderLabels(["UP主昵称", "视频标题", "BV号", "发布时间", "7天播放量", "统计天数", "状态", "共创角色"])
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

        sbl = QHBoxLayout()
        sbl.addStretch()
        self.seb = QPushButton("Cookie设置")
        self.seb.setFixedSize(110, 32)
        self.seb.setProperty("cssClass", "secondary")
        self.seb.clicked.connect(self.open_settings)
        sbl.addWidget(self.seb)
        self.heb = QPushButton("使用帮助")
        self.heb.setFixedSize(110, 32)
        self.heb.setProperty("cssClass", "secondary")
        self.heb.clicked.connect(self.open_help)
        sbl.addWidget(self.heb)
        dal.addLayout(sbl)
        sp.addWidget(daw)
        ml.addWidget(sp)

    def open_settings(self):
        CookieSettingsDialog(self).exec_()

    def open_help(self):
        QMessageBox.about(self, "使用帮助",
                          "1.添加UP主UID和昵称\n2.设置时间(默认是7天前)\n3.每日点击【开始统计】\n4.已结算视频自动锁定\n5.导出Excel\n\n⚠️ 重要提示：请务必在Cookie设置中填写完整的SESSDATA、bili_jct和buvid3！")

    def closeEvent(self, e):
        if self.stat_thread and self.stat_thread.isRunning():
            save_daily_video_data(self.stat_thread.daily_data)
            self.stat_thread.requestInterruption()
            self.stat_thread.wait(3000)
        e.accept()

    def load_up_list(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.up_list = json.load(f)
                self.up_list = [u for u in self.up_list if u.get("uid") and u.get("nickname")]
                for u in self.up_list:
                    if "enabled" not in u:
                        u["enabled"] = True
                self.refresh_up_list_text()
            except Exception:
                self.up_list = []

    def save_up_list(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.up_list, f, ensure_ascii=False, indent=2)

    def on_up_item_changed(self, item):
        idx = item.data(Qt.UserRole)
        if idx is None or idx >= len(self.up_list):
            return
        self.up_list[idx]["enabled"] = (item.checkState() == Qt.Checked)
        self.save_up_list()

    def on_up_item_double_clicked(self, item):
        new_state = item.checkState() != Qt.Checked
        item.setCheckState(Qt.Checked if new_state else Qt.Unchecked)

    def refresh_up_list_text(self):
        try:
            self.ult.itemChanged.disconnect()
        except:
            pass
        self.ult.clear()
        for i, u in enumerate(self.up_list, 1):
            item = QListWidgetItem(f"{i}. {u['nickname']}（UID:{u['uid']}）")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if u.get("enabled", True) else Qt.Unchecked)
            item.setData(Qt.UserRole, i - 1)
            self.ult.addItem(item)
        self.ult.itemChanged.connect(self.on_up_item_changed)

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
        self.up_list.append({"uid": u, "nickname": n, "enabled": True})
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
            self.up_list.append({"uid": uid, "nickname": name, "enabled": True})
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

    def on_up_list_context_menu(self, pos):
        item = self.ult.itemAt(pos)
        if item is None:
            return
        idx = item.data(Qt.UserRole)
        if idx is None or idx >= len(self.up_list):
            return
        menu = QMenu(self)
        del_action = QAction(f"删除 {self.up_list[idx]['nickname']}", self)
        del_action.triggered.connect(lambda: self.remove_up_by_index(idx))
        menu.addAction(del_action)
        menu.exec_(self.ult.viewport().mapToGlobal(pos))

    def remove_up_by_index(self, idx):
        if 0 <= idx < len(self.up_list):
            name = self.up_list[idx]["nickname"]
            self.up_list.pop(idx)
            self.save_up_list()
            self.refresh_up_list_text()
            self.log(f"已删除：{name}")

    def start_stat(self):
        if not self.up_list:
            QMessageBox.warning(self, "提示", "请添加UP主")
            return
        enabled_up_list = [u for u in self.up_list if u.get("enabled", True)]
        if not enabled_up_list:
            QMessageBox.warning(self, "提示", "没有启用的UP主，请在左侧列表中勾选")
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

        if self.stat_thread:
            if self.stat_thread.isRunning():
                self.stat_thread.requestInterruption()
                self.stat_thread.wait(3000)
            try:
                self.stat_thread.log_signal.disconnect()
                self.stat_thread.table_signal.disconnect()
                self.stat_thread.finish_signal.disconnect()
                self.stat_thread.error_signal.disconnect()
            except:
                pass

        self.stat_thread = StatThread(enabled_up_list, sdt_full, edt_full,
                                      config.SESSDATA, config.BILI_JCT, config.BUVID3,
                                      config.DEDEUSERID, config.AC_TIME_VALUE)
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
        if self.raw_video_data_backup:
            self.exb.setEnabled(True)
            self.fib.setEnabled(True)

    def refresh_table(self, data):
        self.vt.setRowCount(len(data))
        keys = ["nickname", "title", "bvid", "pub_time", "current_play", "stat_days", "play_tag", "collab_role"]
        for row, item in enumerate(data):
            for col, key in enumerate(keys):
                val = str(item.get(key, ""))
                table_item = QTableWidgetItem(val)
                self.vt.setItem(row, col, table_item)
                if col != 1:
                    table_item.setTextAlignment(Qt.AlignCenter)
        self.vt.scrollToBottom()

    def stat_finish(self, rank_data, result_data):
        self.final_rank_data = rank_data
        self.raw_video_data_backup = result_data

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
            filtered = dialog.result_data

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
                except (ValueError, TypeError):
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
    try:
        log_dir = os.path.join(get_app_data_dir(), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"crash_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("".join(traceback.format_exception(t, v, tb)))
        try:
            QMessageBox.critical(None, "程序异常", f"错误已保存至：\n{log_file}")
        except Exception:
            pass
    except Exception:
        sys.__excepthook__(t, v, tb)


def main():
    sys.excepthook = except_hook
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 9))
    window = BiliStatTool()
    window.show()
    sys.exit(app.exec_())
