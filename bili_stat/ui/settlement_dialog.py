import copy
from datetime import datetime

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QGroupBox, QDateEdit, QCheckBox,
                             QTabWidget, QWidget, QMessageBox, QAbstractItemView)
from PyQt5.QtCore import QDate, Qt

from ..settlement import (load_settlement_config, save_settlement_config,
                          load_settlement_result, save_settlement_result,
                          calculate_settlement, aggregate_up_views,
                          _default_config)
from ..storage import load_daily_video_data
from ..config import TIMEZONE_CN
from .styles import MAIN_STYLE


class SettlementDialog(QDialog):
    def __init__(self, raw_video_data_backup, default_start_date, default_end_date, parent=None):
        super().__init__(parent)
        self.raw_video_data_backup = raw_video_data_backup or []
        self.tier_config = load_settlement_config()
        self.settlement_result = None

        self.setWindowTitle("奖池结算")
        self.setMinimumSize(1100, 750)
        self.setStyleSheet(MAIN_STYLE)
        self._setup_ui(default_start_date, default_end_date)

    def _setup_ui(self, default_start_date, default_end_date):
        ml = QVBoxLayout(self)
        ml.setSpacing(12)
        ml.setContentsMargins(15, 15, 15, 15)

        # ── 数据筛选 ──
        filter_group = QGroupBox("数据筛选")
        fl = QHBoxLayout(filter_group)
        fl.addWidget(QLabel("视频发布时间："))
        self.filter_start = QDateEdit()
        self.filter_start.setDisplayFormat("yyyy-MM-dd")
        self.filter_start.setCalendarPopup(True)
        self.filter_start.setFixedWidth(130)
        fl.addWidget(self.filter_start)
        fl.addWidget(QLabel("至"))
        self.filter_end = QDateEdit()
        self.filter_end.setDisplayFormat("yyyy-MM-dd")
        self.filter_end.setCalendarPopup(True)
        self.filter_end.setFixedWidth(130)
        fl.addWidget(self.filter_end)
        self.include_ongoing_cb = QCheckBox("包含统计中视频")
        self.include_ongoing_cb.setChecked(True)
        fl.addWidget(self.include_ongoing_cb)
        fl.addStretch()
        ml.addWidget(filter_group)

        # 设置默认日期
        if default_start_date:
            if hasattr(default_start_date, 'month'):
                self.filter_start.setDate(QDate(default_start_date.year, default_start_date.month, default_start_date.day))
            else:
                self.filter_start.setDate(QDate.currentDate().addDays(-7))
        else:
            self.filter_start.setDate(QDate.currentDate().addDays(-7))

        if default_end_date:
            if hasattr(default_end_date, 'month'):
                self.filter_end.setDate(QDate(default_end_date.year, default_end_date.month, default_end_date.day))
            else:
                self.filter_end.setDate(QDate.currentDate())
        else:
            self.filter_end.setDate(QDate.currentDate())

        # ── TabWidget ──
        self.tab_widget = QTabWidget()
        self._setup_config_tab()
        self._setup_preview_tab()
        ml.addWidget(self.tab_widget)

        # ── 校验提示 ──
        self.validation_label = QLabel("")
        self.validation_label.setStyleSheet("color: #d94444; font-weight: bold; padding: 4px;")
        self.validation_label.setWordWrap(True)
        ml.addWidget(self.validation_label)

        # ── 底部按钮 ──
        bl = QHBoxLayout()
        bl.addStretch()
        save_btn = QPushButton("保存配置")
        save_btn.setFixedSize(110, 36)
        save_btn.clicked.connect(self.on_save_config)
        bl.addWidget(save_btn)
        preview_btn = QPushButton("预览结算")
        preview_btn.setFixedSize(110, 36)
        preview_btn.clicked.connect(self.on_preview)
        bl.addWidget(preview_btn)
        apply_btn = QPushButton("应用结算")
        apply_btn.setFixedSize(110, 36)
        apply_btn.clicked.connect(self.on_apply)
        bl.addWidget(apply_btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(110, 36)
        cancel_btn.setProperty("cssClass", "secondary")
        cancel_btn.setStyleSheet(cancel_btn.styleSheet())
        cancel_btn.clicked.connect(self.reject)
        bl.addWidget(cancel_btn)
        ml.addLayout(bl)

        self._populate_config_table()

    # ═══════════ 档位配置 Tab ═══════════
    def _setup_config_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(5, 10, 5, 5)
        l.setSpacing(10)

        self.config_table = QTableWidget()
        self.config_table.setColumnCount(4)
        self.config_table.setHorizontalHeaderLabels(["档位名称", "累计播放量(门槛)", "瓜分金额(元)", "单人最高瓜分(元)"])
        self.config_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.config_table.setAlternatingRowColors(True)
        self.config_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        l.addWidget(self.config_table)

        bl = QHBoxLayout()
        add_btn = QPushButton("添加档位")
        add_btn.clicked.connect(self.add_tier)
        bl.addWidget(add_btn)
        del_btn = QPushButton("删除选中")
        del_btn.clicked.connect(self.delete_tier)
        bl.addWidget(del_btn)
        up_btn = QPushButton("▲上移")
        up_btn.clicked.connect(self.move_tier_up)
        bl.addWidget(up_btn)
        down_btn = QPushButton("▼下移")
        down_btn.clicked.connect(self.move_tier_down)
        bl.addWidget(down_btn)
        reset_btn = QPushButton("恢复默认")
        reset_btn.setProperty("cssClass", "secondary")
        reset_btn.setStyleSheet(reset_btn.styleSheet())
        reset_btn.clicked.connect(self.reset_tiers)
        bl.addWidget(reset_btn)
        bl.addStretch()
        l.addLayout(bl)

        self.tab_widget.addTab(w, "档位配置")

    def _populate_config_table(self):
        self.config_table.setRowCount(len(self.tier_config))
        for row, t in enumerate(self.tier_config):
            for col, key in enumerate(["name", "threshold", "pool", "max_per_person"]):
                val = str(t.get(key, ""))
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                self.config_table.setItem(row, col, item)

    def _read_tier_from_table(self):
        tiers = []
        for row in range(self.config_table.rowCount()):
            name = self.config_table.item(row, 0)
            threshold = self.config_table.item(row, 1)
            pool = self.config_table.item(row, 2)
            max_p = self.config_table.item(row, 3)
            try:
                t_val = int(threshold.text().strip()) if threshold else 0
            except ValueError:
                t_val = 0
            try:
                p_val = float(pool.text().strip()) if pool else 0.0
            except ValueError:
                p_val = 0.0
            try:
                m_val = float(max_p.text().strip()) if max_p else 0.0
            except ValueError:
                m_val = 0.0
            tiers.append({
                "name": name.text().strip() if name else f"第{row + 1}档",
                "threshold": t_val,
                "pool": p_val,
                "max_per_person": m_val,
                "sort_order": row,
            })
        return tiers

    def _validate(self, tiers):
        errors = []
        for i, t in enumerate(tiers):
            label = t["name"] or f"第{i + 1}档"
            if t["threshold"] < 0:
                errors.append(f"{label}：累计播放量门槛不能为负数")
            if t["pool"] < 0:
                errors.append(f"{label}：瓜分金额不能为负数")
            if t["max_per_person"] < 0:
                errors.append(f"{label}：单人最高瓜分不能为负数")
            if t["max_per_person"] > t["pool"] and t["pool"] > 0:
                errors.append(f"{label}：单人最高瓜分（{t['max_per_person']}）不能大于瓜分奖池总额（{t['pool']}）")
        return errors

    def add_tier(self):
        tiers = self._read_tier_from_table()
        idx = 1
        new_name = f"新增档位{idx}"
        existing = {t["name"] for t in tiers}
        while new_name in existing:
            idx += 1
            new_name = f"新增档位{idx}"
        tiers.append({"name": new_name, "threshold": 0, "pool": 0, "max_per_person": 0, "sort_order": len(tiers)})
        self.tier_config = tiers
        self._populate_config_table()

    def delete_tier(self):
        rows = set(idx.row() for idx in self.config_table.selectedIndexes())
        if not rows:
            QMessageBox.warning(self, "提示", "请先选择一个档位")
            return
        if self.config_table.rowCount() <= 1:
            QMessageBox.warning(self, "提示", "至少保留一个档位")
            return
        for row in sorted(rows, reverse=True):
            self.config_table.removeRow(row)
        self.tier_config = self._read_tier_from_table()

    def move_tier_up(self):
        rows = set(idx.row() for idx in self.config_table.selectedIndexes())
        if not rows:
            QMessageBox.warning(self, "提示", "请先选择一个档位")
            return
        row = min(rows)
        if row <= 0:
            return
        tiers = self._read_tier_from_table()
        tiers[row], tiers[row - 1] = tiers[row - 1], tiers[row]
        self.tier_config = tiers
        self._populate_config_table()
        self.config_table.selectRow(row - 1)

    def move_tier_down(self):
        rows = set(idx.row() for idx in self.config_table.selectedIndexes())
        if not rows:
            QMessageBox.warning(self, "提示", "请先选择一个档位")
            return
        row = max(rows)
        if row >= self.config_table.rowCount() - 1:
            return
        tiers = self._read_tier_from_table()
        tiers[row], tiers[row + 1] = tiers[row + 1], tiers[row]
        self.tier_config = tiers
        self._populate_config_table()
        self.config_table.selectRow(row + 1)

    def reset_tiers(self):
        if QMessageBox.question(self, "确认", "恢复为默认7档配置？当前修改将丢失。") == QMessageBox.Yes:
            self.tier_config = _default_config()
            self._populate_config_table()
            self._clear_preview()

    # ═══════════ 结算预览 Tab ═══════════
    def _setup_preview_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(5, 10, 5, 5)
        l.setSpacing(10)

        l.addWidget(QLabel("档位汇总"))
        self.summary_table = QTableWidget()
        self.summary_table.setColumnCount(5)
        self.summary_table.setHorizontalHeaderLabels(["档位", "累计播放量(门槛)", "瓜分金额(元)", "单人最高瓜分(元)", "奖池人数"])
        self.summary_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.summary_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.summary_table.setAlternatingRowColors(True)
        l.addWidget(self.summary_table)

        l.addWidget(QLabel("UP主结算明细"))
        self.detail_table = QTableWidget()
        self.detail_table.setColumnCount(8)
        self.detail_table.setHorizontalHeaderLabels(
            ["档位", "UP主", "UID", "对应播放量", "占比", "预估收益(元)", "实际收益(元)", "是否封顶"])
        self.detail_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.detail_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.detail_table.setAlternatingRowColors(True)
        l.addWidget(self.detail_table)

        self.tab_widget.addTab(w, "结算预览")

    def _clear_preview(self):
        self.summary_table.setRowCount(0)
        self.detail_table.setRowCount(0)

    def _populate_preview(self, result):
        tier_results = result.get("tier_results", [])

        # 档位汇总表
        self.summary_table.setRowCount(len(tier_results))
        for row, tr in enumerate(tier_results):
            values = [tr["tier_name"], str(tr["threshold"]), str(tr["pool"]),
                      str(tr["max_per_person"]), str(tr["qualified_count"])]
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                self.summary_table.setItem(row, col, item)

        # UP主结算明细表
        total_rows = sum(len(tr["members"]) for tr in tier_results)
        self.detail_table.setRowCount(total_rows)
        row = 0
        for tr in tier_results:
            for m in tr["members"]:
                ratio_str = f"{m['ratio'] * 100:.1f}%" if m["ratio"] else "0.0%"
                values = [
                    tr["tier_name"], m["nickname"], str(m["uid"]),
                    str(m["individual_views"]), ratio_str,
                    str(m["estimated"]), str(m["actual"]),
                    "是" if m["capped"] else "否"
                ]
                for col, val in enumerate(values):
                    item = QTableWidgetItem(val)
                    item.setTextAlignment(Qt.AlignCenter)
                    self.detail_table.setItem(row, col, item)
                row += 1

    # ═══════════ 视频数据获取 ═══════════
    def _get_video_data_for_settlement(self):
        fs = self.filter_start.date().toPyDate()
        fe = self.filter_end.date().toPyDate()
        start_dt = datetime.combine(fs, datetime.min.time(), tzinfo=TIMEZONE_CN)
        end_dt = datetime.combine(fe, datetime.max.time(), tzinfo=TIMEZONE_CN)

        daily_data = load_daily_video_data()
        merged = []
        seen = set()

        # 先加入历史已结算数据
        for bvid, v in daily_data.items():
            if v.get("excluded", False):
                continue
            if v.get("status") == "已结算":
                merged.append({
                    "uid": v.get("uid", 0),
                    "nickname": v.get("nickname", ""),
                    "current_play": v.get("final_play", 0),
                    "pub_time": v.get("pub_time", ""),
                    "excluded": False,
                })
                seen.add(bvid)

        # 加入当前统计中的数据（优先级高于 daily_data 中的统计中快照）
        if self.include_ongoing_cb.isChecked():
            for v in self.raw_video_data_backup:
                if v.get("excluded", False):
                    continue
                bvid = v.get("bvid", "")
                if bvid and bvid in seen:
                    continue
                if bvid:
                    seen.add(bvid)
                merged.append({
                    "uid": v.get("uid", 0),
                    "nickname": v.get("nickname", ""),
                    "current_play": v.get("current_play", 0),
                    "pub_time": v.get("pub_time", ""),
                    "excluded": False,
                })

            # 补充：daily_data 中的"统计中"视频（本次未统计到的UP主，使用最近一次快照数据）
            for bvid, v in daily_data.items():
                if v.get("excluded", False):
                    continue
                if bvid in seen:
                    continue
                if v.get("status") == "统计中":
                    merged.append({
                        "uid": v.get("uid", 0),
                        "nickname": v.get("nickname", ""),
                        "current_play": v.get("final_play", 0),
                        "pub_time": v.get("pub_time", ""),
                        "excluded": False,
                    })
                    seen.add(bvid)

        return aggregate_up_views(merged, start_dt, end_dt)

    # ═══════════ 操作按钮 ═══════════
    def on_save_config(self):
        tiers = self._read_tier_from_table()
        errors = self._validate(tiers)
        if errors:
            self.validation_label.setText("\n".join(errors))
            return
        self.tier_config = tiers
        save_settlement_config(tiers)
        self.validation_label.setText("")
        QMessageBox.information(self, "提示", "档位配置已保存")

    def on_preview(self):
        tiers = self._read_tier_from_table()
        errors = self._validate(tiers)
        if errors:
            self.validation_label.setText("\n".join(errors))
            return
        self.validation_label.setText("")
        self.tier_config = tiers

        up_data = self._get_video_data_for_settlement()
        if not up_data:
            QMessageBox.warning(self, "提示", "所选日期范围内无有效视频数据")
            self._clear_preview()
            return

        result = calculate_settlement(tiers, up_data)
        self._populate_preview(result)
        self.tab_widget.setCurrentIndex(1)

        # 检查是否有达标UP主
        total_members = sum(tr["qualified_count"] for tr in result["tier_results"])
        if total_members == 0:
            QMessageBox.information(self, "提示", "预览完成，但当前无UP主达到任何档位门槛")

    def on_apply(self):
        tiers = self._read_tier_from_table()
        errors = self._validate(tiers)
        if errors:
            self.validation_label.setText("\n".join(errors))
            return
        self.validation_label.setText("")
        self.tier_config = tiers

        up_data = self._get_video_data_for_settlement()
        if not up_data:
            QMessageBox.warning(self, "提示", "所选日期范围内无有效视频数据，无法应用结算")
            return

        result = calculate_settlement(tiers, up_data)
        save_settlement_config(tiers)
        save_settlement_result(result)
        self.settlement_result = result
        QMessageBox.information(self, "提示", "奖池结算已应用生效！\n配置和结果已保存，可导出Excel查看明细。")
        self.accept()
