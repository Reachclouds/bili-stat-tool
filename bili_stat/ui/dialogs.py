from PyQt5.QtWidgets import (QDialog, QFormLayout, QLineEdit, QPushButton,
                             QHBoxLayout, QMessageBox, QVBoxLayout, QLabel,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QCheckBox, QComboBox)
from PyQt5.QtCore import Qt

from ..config import load_cookie_config, update_cookie, load_role_filter_settings, save_role_filter_settings
from ..storage import load_daily_video_data, save_daily_video_data
from .styles import MAIN_STYLE


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
        self.setStyleSheet(MAIN_STYLE)
        self.resize(1200, 750)
        self.current_data = current_data
        self.data_list = []
        self.role_filter_enabled, self.excluded_roles = load_role_filter_settings()

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

        self.role_layout = QHBoxLayout()
        self.role_filter_cb = QCheckBox("排除指定共创角色：")
        self.role_filter_cb.setChecked(self.role_filter_enabled)
        self.role_filter_cb.stateChanged.connect(self.on_role_filter_changed)
        self.role_layout.addWidget(self.role_filter_cb)
        self.role_placeholder = QLabel("（无共创角色）")
        self.role_placeholder.setStyleSheet("color: #999;")
        self.role_placeholder.setVisible(False)
        self.role_layout.addWidget(self.role_placeholder)
        self.role_checkboxes = []
        self.role_layout.addStretch()
        layout.addLayout(self.role_layout)

        action_layout = QHBoxLayout()
        self.toggle_select_btn = QPushButton("全选/全不选")
        self.toggle_select_btn.clicked.connect(self.toggle_current_visible)
        action_layout.addWidget(self.toggle_select_btn)
        action_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        action_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton("确认筛选并永久排除")
        confirm_btn.setProperty("cssClass", "danger")
        confirm_btn.clicked.connect(self.confirm_selection)
        action_layout.addWidget(confirm_btn)
        layout.addLayout(action_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(["选择", "UP主昵称", "视频标题", "BV号", "发布时间", "7天播放量", "统计天数", "状态", "共创角色"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.resizeSection(0, 50)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.resizeSection(1, 110)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.resizeSection(3, 105)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.resizeSection(4, 90)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        header.resizeSection(5, 80)
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        header.resizeSection(6, 75)
        header.setSectionResizeMode(7, QHeaderView.Fixed)
        header.resizeSection(7, 70)
        header.setSectionResizeMode(8, QHeaderView.Fixed)
        header.resizeSection(8, 75)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.cellDoubleClicked.connect(self.on_row_double_clicked)
        layout.addWidget(self.table)


    def on_role_filter_changed(self):
        self.role_filter_enabled = self.role_filter_cb.isChecked()
        for cb in self.role_checkboxes:
            cb.setEnabled(self.role_filter_enabled)
        self.load_and_refresh()

    def _rebuild_role_checkboxes(self, roles):
        for cb in self.role_checkboxes:
            cb.setParent(None)
            cb.deleteLater()
        self.role_checkboxes = []

        if not roles:
            self.role_placeholder.setVisible(True)
            return

        self.role_placeholder.setVisible(False)
        sorted_roles = sorted(roles)
        for role in sorted_roles:
            cb = QCheckBox(role)
            cb.blockSignals(True)
            cb.setChecked(role in self.excluded_roles)
            cb.setEnabled(self.role_filter_enabled)
            cb.blockSignals(False)
            cb.stateChanged.connect(self.on_role_checkbox_changed)
            self.role_checkboxes.append(cb)
            self.role_layout.insertWidget(self.role_layout.count() - 1, cb)

    def on_role_checkbox_changed(self):
        self.excluded_roles = [cb.text() for cb in self.role_checkboxes if cb.isChecked()]
        self.load_and_refresh()

    def load_and_refresh(self):
        self.data_list = self._get_full_data_internal()

        all_roles = set()
        for item in self.data_list:
            role = item.get("data", {}).get("collab_role", "")
            if role:
                all_roles.add(role)
        self._rebuild_role_checkboxes(all_roles)

        if self.role_filter_enabled and self.excluded_roles:
            for item in self.data_list:
                role = item.get("data", {}).get("collab_role", "")
                if role and role in self.excluded_roles:
                    item["selected"] = False

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
                    count = sum(1 for item in self.data_list if item.get("data", {}).get("uid", 0) == uid)
                    self.up_combo.addItem(f"{nick}（UID:{uid}）- {count}个视频", key)

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
                pass  # 在新数据中出现的已排除视频 → 强制显示，selected=False
            elif not show_excluded and is_excluded:
                continue  # 不在新数据中的已排除视频 → 按原逻辑隐藏

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
                    "is_collaborative": v.get("is_collaborative", False),
                    "collab_role": v.get("collab_role", ""),
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
                d.get("play_tag", ""),
                d.get("collab_role", ""),
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

    def on_row_double_clicked(self, row, col):
        if col == 0:
            return
        chk_item = self.table.item(row, 0)
        if chk_item is None:
            return
        original_idx = chk_item.data(Qt.UserRole)
        if original_idx is None or not (0 <= original_idx < len(self.data_list)):
            return
        new_state = not self.data_list[original_idx].get("selected", True)
        self.data_list[original_idx]["selected"] = new_state
        chk_item.setCheckState(Qt.Checked if new_state else Qt.Unchecked)
        self.table.clearFocus()

    def toggle_current_visible(self):
        current_up = self.up_combo.currentData()
        all_selected = True
        for item in self.data_list:
            d = item.get("data", {})
            if current_up is not None:
                target_uid, _ = current_up
                if d.get("uid", 0) != target_uid:
                    continue
            if not item.get("selected", True):
                all_selected = False
                break

        new_state = not all_selected
        for item in self.data_list:
            d = item.get("data", {})
            if current_up is not None:
                target_uid, _ = current_up
                if d.get("uid", 0) != target_uid:
                    continue
            item["selected"] = new_state
        self.refresh_table_view()

    def confirm_selection(self):
        save_role_filter_settings(self.role_filter_enabled, self.excluded_roles)
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
