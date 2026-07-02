# MacauLottery V4PRO - 项目结构

## 目录结构

`
macau_lottery/
├── shared/                    共享核心代码
│   ├── engine.py              预测引擎（1984行）
│   ├── macaujc_api.py         API接口
│   └── macaujc_data.json      历史数据（915条）
│
├── desktop/                   桌面端（tkinter）
│   ├── main.py                入口（984行）
│   └── build.bat              PyInstaller打包脚本
│
├── android/                   安卓端（Flet）
│   └── main.py                入口（665行）
│
├── tools/                     回测/调试工具
│   ├── backtest.py ~ v4.py    回测框架
│   └── _*.py                  调试脚本
│
└── .github/workflows/
    └── build-apk.yml          GitHub Actions云端APK编译
`

## 运行方式

### 桌面版
`ash
cd desktop
python main.py
# 或打包：
build.bat
`

### 安卓版
`ash
cd android
python main.py
# APK构建：推送代码到GitHub自动触发，或手动在Actions页面触发
`

## 共享机制
- desktop 和 android 都通过 sys.path 导入 ../shared/engine
- engine.py 是唯一的预测模型代码源
- 数据文件 macaujc_data.json 由 shared/ 统一管理

## 打包

| 平台 | 方式 | 命令 |
|------|------|------|
| Windows EXE | PyInstaller | cd desktop && build.bat |
| Android APK | GitHub Actions | git push → 自动构建 |
