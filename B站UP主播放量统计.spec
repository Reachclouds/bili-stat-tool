# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# bilibili_api 使用 importlib 动态导入所有子模块，PyInstaller 无法自动追踪
bilibili_hidden = collect_submodules('bilibili_api')
# 同时收集 bilibili_api/data 下的 JSON 配置文件
bilibili_datas = collect_data_files('bilibili_api')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=bilibili_datas,
    hiddenimports=bilibili_hidden + [
        'curl_cffi',
        'curl_cffi.requests',
        'aiohttp',
        'httpx',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='B站UP主播放量统计',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['bili_stat/resources/图标.ico'],
)
