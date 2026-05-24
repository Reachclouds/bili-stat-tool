# B站UP主7天播放量统计工具

批量统计B站UP主视频的7天播放量，支持历史数据持久化、视频筛选、Excel导出的桌面应用。

## 功能

- 批量添加UP主（UID+昵称），最多80个
- 按日期范围统计视频播放量，区分"已结算"和"统计中"状态
- 历史数据本地持久化，自动备份（保留30天）
- 视频筛选：可排除特定视频，排除状态跨会话生效
- 导出Excel：含视频明细 + UP主整体排名两个工作表
- 防风控：随机延时、浏览器伪装、412自动降级游客模式

## 安装

```bash
pip install PyQt5 openpyxl bilibili-api
```

## 运行

```bash
python main.py
```

## 使用流程

1. 点击「Cookie设置」，填写B站Cookie（SESSDATA、bili_jct、buvid3等）
2. 添加UP主：单个输入UID+昵称，或批量导入（格式：`UID,昵称`，每行一个）
3. 设置统计日期范围（默认最近7天）
4. 点击「开始统计」，等待完成
5. 可选：点击「筛选作品」排除不需要的视频
6. 点击「导出Excel」保存结果

## Cookie获取方式

在浏览器中登录B站，按F12打开开发者工具 → Application → Cookies，找到以下字段：

| 字段 | 说明 |
|------|------|
| SESSDATA | 会话数据 |
| bili_jct | CSRF Token |
| buvid3 | 浏览器标识 |
| DedeUserID | 用户ID |
| ac_time_value | 时间校验值 |

## 数据存储

所有数据保存在用户目录下：

```
~/.BiliStatTool/
├── cookie.json           # Cookie配置
├── up_list.json          # UP主列表
├── video_7day_data.json  # 视频统计数据
├── backups/              # 自动备份（30天）
└── logs/                 # 崩溃日志
```

## 项目结构

```
├── main.py                 # 入口
└── bili_stat/
    ├── config.py           # 全局配置 + Cookie管理
    ├── storage.py          # 数据持久化 + 备份
    ├── api.py              # B站API调用（StatThread）
    ├── excel_export.py     # Excel导出
    └── ui/
        ├── styles.py       # 界面样式
        ├── dialogs.py      # 对话框（Cookie设置、视频筛选）
        └── main_window.py  # 主窗口
```
