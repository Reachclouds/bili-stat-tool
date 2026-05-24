# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

B站（Bilibili）UP主7天播放量统计工具。PyQt5 桌面应用，批量统计UP主视频播放量，支持历史数据持久化、视频筛选、Excel导出。用户自用工具，无测试套件。

## Running

```bash
python main.py
```

Requires: Python 3.12+, PyQt5, openpyxl, bilibili-api

## Architecture

`bili_stat/` 包，按职责分层：

- **config.py** — 全局常量、Cookie配置读写、Excel样式变量。`update_cookie()` 是修改全局 Cookie 状态的唯一入口。
- **storage.py** — `video_7day_data.json` 的原子写入、自动备份（30天保留）、数据迁移（旧数据自动补 `excluded` 字段）。
- **api.py** — `StatThread(QThread)` 封装全部B站API调用，含防412风控策略（随机延时、Referer伪装、游客模式降级）。
- **excel_export.py** — `export_excel()` 纯函数，接收数据参数，生成双sheet Excel。
- **ui/styles.py** — QSS样式字符串。
- **ui/dialogs.py** — `CookieSettingsDialog`（修改Cookie）、`VideoSelectionDialog`（筛选/排除视频）。
- **ui/main_window.py** — `BiliStatTool` 主窗口，`main()` 函数包含启动逻辑和全局异常钩子。

原文件 `B站统计工具.py` 是重构前的备份，不参与运行。

## Key Data Flow

1. 用户配置UP主列表 → 保存到 `~/.BiliStatTool/up_list.json`
2. `StatThread` 遍历UP主，调用B站API获取视频列表 → 写入 `daily_data`（内存）
3. 统计完成 → `save_daily_video_data()` 原子写入 `~/.BiliStatTool/video_7day_data.json`
4. 视频分两类：已结算（≥7天，播放量锁定）和统计中（<7天，次日更新）
5. `VideoSelectionDialog` 可排除特定视频，排除状态持久化到 `daily_data[bvid]["excluded"]`
6. `export_excel()` 合并历史已结算 + 本次统计中数据，生成Excel

## Important Patterns

- 所有B站请求在子线程（`StatThread`），通过 Qt 信号回传 UI 更新
- 数据文件路径统一通过 `config.get_app_data_dir()` 定位（`~/.BiliStatTool/`）
- `daily_data` 以 `bvid` 为 key，跨会话累积，已结算视频数据永不更新
