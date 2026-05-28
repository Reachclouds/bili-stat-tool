from PyQt5.QtWidgets import (QDialog, QFormLayout, QLineEdit, QPushButton,
                             QHBoxLayout, QMessageBox, QVBoxLayout, QLabel,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QCheckBox, QComboBox)
from PyQt5.QtCore import Qt

from ..config import load_cookie_config, update_cookie
from ..storage import load_daily_video_data, save_daily_video_data


class CookieSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cookie 设置")
        self.setModal(True)
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)
        cc = load_cookie_config()
        self.sess = QLineEdit(cc.get("SESSDATA", ""))
        self.bili = QLineEdit(cc.get("BILI_JCT", ""))
        self.buvid = QLineEdit(cc.get("BUVID3", ""))
        self.dede = QLineEdit(cc.get("DEDEUSERID", ""))
        self.ac_time = QLineEdit(cc.get("AC_TIME_VALUE", "1000"))
        layout.addRow("DedeUserID:", self.dede)
        layout.addRow("ac_time_value:", self.ac_time)
        layout.addRow("SESSDATA:", self.sess)
        layout.addRow("bili_jct:", self.bili)
        layout.addRow("buvid3:", self.buvid)
        bl = QHBoxLayout()
        sav = QPushButton("保存")
        sav.clicked.connect(self.save_and_close)
        can = QPushButton("取消")
        can.clicked.connect(self.reject)
        bl.addStretch()
        bl.addWidget(sav)
        bl.addWidget(can)
        layout.addRow(bl)

    def save_and_close(self):
        update_cookie(
            self.sess.text().strip(),
            self.bili.text().strip(),
            self.buvid.text().strip(),
            self.dede.text().strip(),
            self.ac_time.text().strip()
        )
        QMessageBox.information(self, "成功", "Cookie已保存")
        self.accept()


class VideoSelectionDialog(QDialog):
    def __init__(self, current_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("筛选统计作品")
        self.setModal(True)
        self.resize(1200, 750)
        self.current_data = current_data
        self.data_list = []

        self.init_ui()
        self.load_and_refresh()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        tip = QLabel("提示：取消勾选的视频将从排行榜和明细表中永久排除（历史数据也会生效）")
        tip.setStyleSheet("color: #D32F2F; font-weight:bold;")
        layout.addWidget(tip)

        ctrl_layout = QHBoxLayout()

        self.history_check = QCheckBox("包含全部历史数据一起筛选（推荐）")
        self.history_check.setChecked(True)
        self.history_check.stateChanged.connect(self.load_and_refresh)
        ctrl_layout.addWidget(self.history_check)

        self.show_excluded_check = QCheckBox("显示已排除的视频（用于恢复）")
        self.show_excluded_check.setChecked(False)
        self.show_excluded_check.stateChanged.connect(self.load_and_refresh)
        ctrl_layout.addWidget(self.show_excluded_check)

        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)

        up_layout = QHBoxLayout()
        up_layout.addWidget(QLabel("UP主专属视图："))
        self.up_combo = QComboBox()
        self.up_combo.setMinimumWidth(320)
        self.up_combo.currentIndexChanged.connect(self.refresh_table_view)
        up_layout.addWidget(self.up_combo)
        up_layout.addStretch()
        layout.addLayout(up_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["选择", "UP主昵称", "视频标题", "BV号", "发布时间", "7天播放量", "统计天数", "状态"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("全选当前显示")
        self.select_all_btn.clicked.connect(self.select_current_visible)
        btn_layout.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton("全不选当前显示")
        self.deselect_all_btn.clicked.connect(self.deselect_current_visible)
        btn_layout.addWidget(self.deselect_all_btn)
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton("确认筛选并永久排除")
        confirm_btn.setProperty("cssClass", "danger")
        confirm_btn.clicked.connect(self.confirm_selection)
        btn_layout.addWidget(confirm_btn)
        layout.addLayout(btn_layout)

    def load_and_refresh(self):
        self.data_list = self._get_full_data_internal()

        self.up_combo.blockSignals(True)
        self.up_combo.clear()
        self.up_combo.addItem("全部UP主", None)

        up_set = set()
        for item in self.data_list:
            d = item.get("data", {})
            uid = d.get("uid", 0)
            nick = d.get("nickname", "")
            if uid and nick:
                key = (uid, nick)
                if key not in up_set:
                    up_set.add(key)
                    self.up_combo.addItem(f"{nick}（UID:{uid}）", key)

        self.up_combo.blockSignals(False)
        self.refresh_table_view()

    def _get_full_data_internal(self):
        if not self.history_check.isChecked():
            result = []
            show_excluded = self.show_excluded_check.isChecked()
            for item in self.current_data:
                is_excluded = item.get("excluded", False)
                if not show_excluded and is_excluded:
                    continue
                result.append({
                    "data": item,
                    "selected": not is_excluded,
                    "source_bvid": item.get("bvid", "")
                })
            return result

        daily = load_daily_video_data()
        full = []
        seen_bvids = set()
        show_excluded = self.show_excluded_check.isChecked()
        current_bvids = {item.get("bvid", "") for item in self.current_data if item.get("bvid")}

        for v in daily.values():
            bvid = v.get("bvid", "")
            if not bvid or bvid in seen_bvids:
                continue

            is_excluded = v.get("excluded", False)
            if is_excluded and bvid in current_bvids:
                pass
            elif not show_excluded and is_excluded:
                continue

            seen_bvids.add(bvid)
            full.append({
                "data": {
                    "uid": v.get("uid", 0),
                    "nickname": v.get("nickname", ""),
                    "title": v.get("title", ""),
                    "bvid": bvid,
                    "pub_time": v.get("pub_time", ""),
                    "current_play": v.get("final_play", 0),
                    "stat_days": v.get("stat_days", 7),
                    "play_tag": v.get("status", "已结算"),
                },
                "selected": not is_excluded,
                "source_bvid": bvid
            })

        for item in self.current_data:
            bvid = item.get("bvid", "")
            if not bvid or bvid in seen_bvids:
                continue

            is_excluded = item.get("excluded", False)
            if not show_excluded and is_excluded:
                continue

            seen_bvids.add(bvid)
            full.append({
                "data": item,
                "selected": not is_excluded,
                "source_bvid": bvid
            })
        return full

    def refresh_table_view(self):
        try:
            self.table.itemChanged.disconnect()
        except:
            pass

        current_up = self.up_combo.currentData()

        self.table.setRowCount(0)
        row_pos = 0

        for idx, item in enumerate(self.data_list):
            d = item.get("data", {})

            if current_up is not None:
                target_uid, _ = current_up
                if d.get("uid", 0) != target_uid:
                    continue

            self.table.insertRow(row_pos)

            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk_item.setCheckState(Qt.Checked if item.get("selected", True) else Qt.Unchecked)
            chk_item.setData(Qt.UserRole, idx)
            self.table.setItem(row_pos, 0, chk_item)

            cols = [
                d.get("nickname", ""),
                d.get("title", ""),
                d.get("bvid", ""),
                d.get("pub_time", ""),
                str(d.get("current_play", 0)),
                str(d.get("stat_days", 0)),
                d.get("play_tag", "")
            ]
            for c, text in enumerate(cols):
                ti = QTableWidgetItem(text)
                self.table.setItem(row_pos, c + 1, ti)
                if c + 1 != 2:
                    ti.setTextAlignment(Qt.AlignCenter)

            row_pos += 1

        self.table.itemChanged.connect(self.on_item_check_changed)

    def on_item_check_changed(self, item):
        if item.column() != 0:
            return
        try:
            original_idx = item.data(Qt.UserRole)
            if original_idx is not None and 0 <= original_idx < len(self.data_list):
                self.data_list[original_idx]["selected"] = (item.checkState() == Qt.Checked)
        except Exception as e:
            pass

    def select_current_visible(self):
        current_up = self.up_combo.currentData()
        for item in self.data_list:
            d = item.get("data", {})
            if current_up is not None:
                target_uid, _ = current_up
                if d.get("uid", 0) != target_uid:
                    continue
            item["selected"] = True
        self.refresh_table_view()

    def deselect_current_visible(self):
        current_up = self.up_combo.currentData()
        for item in self.data_list:
            d = item.get("data", {})
            if current_up is not None:
                target_uid, _ = current_up
                if d.get("uid", 0) != target_uid:
                    continue
            item["selected"] = False
        self.refresh_table_view()

    def confirm_selection(self):
        daily = load_daily_video_data()
        for item in self.data_list:
            bvid = item.get("source_bvid", "") or item.get("data", {}).get("bvid", "")
            if bvid and bvid in daily:
                daily[bvid]["excluded"] = not item.get("selected", True)
        save_daily_video_data(daily)

        self.result_data = [it["data"] for it in self.data_list if it.get("selected", True)]

        if not self.result_data:
            QMessageBox.warning(self, "提示", "至少保留一个视频！")
            return

        self.accept()
