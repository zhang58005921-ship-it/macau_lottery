# MacauLottery V4PRO — 开发日志

> **最后更新**：2026-07-03  
> **构建状态**：🟢 APK 构建成功 (Run #33)  
> **项目仓库**：[zhang58005921-ship-it/macau_lottery](https://github.com/zhang58005921-ship-it/macau_lottery)

---

## 1. 项目概述

**MacauLottery V4PRO** 是澳门六合彩分析预测工具，支持桌面端（Windows EXE）和安卓端（APK），
两端共享同一套预测引擎核心。

| 维度 | 说明 |
|------|------|
| **平台** | Windows 桌面 + Android |
| **桌面框架** | tkinter（Python 标准库） |
| **安卓框架** | Flet（基于 Flutter） |
| **预测引擎** | 自研 LotteryAnalyzer + AdversarialPredictor + EnsemblePredictor |
| **数据量** | 915 条历史开奖记录 (≈530KB JSON) |
| **打包** | PyInstaller（桌面）/ GitHub Actions + Flet -> APK（安卓） |
| **代码行数** | engine.py ≈1984 行, desktop/main.py ≈984 行, android/main.py ≈665 行 |

---

## 2. 目录结构

```
macau_lottery/
├── shared/                        共享核心（绝不重复）
│   ├── engine.py                  预测引擎（唯一代码源）
│   ├── macaujc_api.py             数据 API 接口
│   └── macaujc_data.json          历史数据（915条）
│
├── desktop/                       桌面端
│   ├── main.py                    tkinter GUI 入口
│   ├── build.bat                  PyInstaller 打包脚本
│   ├── _launch.html               启动页模板
│   └── _rebuild.bat               快速重编译脚本
│
├── android/                       安卓端
│   ├── main.py                    Flet 应用入口
│   └── buildozer.spec             Buildozer 配置（备用）
│
├── tools/                         开发辅助工具
│   ├── backtest.py ~ v4.py        回测框架（多版本迭代）
│   ├── fix_zodiac.py/v2.py        生肖数据修复
│   ├── clean_code.py              代码清理
│   ├── audit_data.py              数据审计
│   └── _*.py                      调试/实验脚本
│
├── .github/workflows/
│   └── build-apk.yml              CI/CD：云端 APK 编译
│
├── AGENTS.md                      项目结构说明（给 AI Agent）
├── DEVELOPMENT_LOG.md             本文件：开发日志
└── .gitignore
```

---

## 3. 架构设计决策

### 3.1 核心原则：单一代码源（Single Source of Truth）

```
┌──────────────┐     ┌──────────────┐
│  desktop/    │     │  android/    │
│  main.py     │     │  main.py     │
│  tkinter UI  │     │  Flet UI     │
└──────┬───────┘     └──────┬───────┘
       │   sys.path.insert   │
       │   ../shared         │
       ▼                     ▼
┌─────────────────────────────────────┐
│          shared/                     │
│  engine.py   <- 唯一预测引擎          │
│  macaujc_api.py                     │
│  macaujc_data.json                  │
└─────────────────────────────────────┘
```

- **两端绝不各自复制引擎代码**，只共享 shared/ 目录
- android/main.py 在开发环境和打包环境分别寻找 ../shared 和 ./shared
- 修改预测逻辑只需改 shared/engine.py 一处

### 3.2 项目演进

```
Phase 1 --- 单文件原型（根目录 main.py + engine.py）
Phase 2 --- 安卓适配（新增 apk_build/ 目录） 
Phase 3 --- 结构重构（分离 shared/desktop/android/tools）
Phase 4 --- CI/CD 自动化（GitHub Actions 云端编译 APK）
```

**Phase 3 重构要点**（2026-07-02）：
- 旧根目录文件（main.py, engine.py, app_android.py, macaujc_* 等）-> 移至对应子目录
- apk_build/ 目录废弃，源码统一由 android/ 使用 shared/
- GitHub Actions 工作流适配新结构（cp shared -> android/shared）

### 3.3 打包策略

| 目标 | 工具 | 触发 |
|------|------|------|
| Windows .exe | PyInstaller (desktop/build.bat) | 手动本地执行 |
| Android .apk | Flutter + Flet (GitHub Actions) | push 或手动触发 |

APK 在 GitHub Actions **Ubuntu 云端**编译，无需本地 Android SDK。

---

## 4. CI/CD 构建流水线

### 4.1 工作流文件

**位置**：.github/workflows/build-apk.yml

```
触发条件:
├── push (main/master, 路径: android/**, shared/**, .github/**)
└── workflow_dispatch (手动)

构建步骤:
1. checkout 代码
2. Python 3.12
3. Flutter SDK 3.27.0
4. Android SDK (platforms;android-35)
5. pip install flet
6. cp -r shared android/shared     <- 关键：复制共享引擎
7. flet build apk                  <- 编译 APK
8. upload-artifact                 <- 上传产物
```

### 4.2 Flet APK 构建参数

| 参数 | 值 |
|------|-----|
| --org | com.macau.lottery |
| --project | macau_lottery_v4pro |
| --artifact / --product | MacauLotteryV4PRO |
| --build-version | 4.0.3 |
| --android-permissions INTERNET | true |
| minSdkVersion | 33 (Android 13) |
| targetSdkVersion | 35 (Android 15) |

---

## 5. 构建运行历史

### 5.1 运行总结（33 次运行）

| 状态 | 数量 | 说明 |
|------|------|------|
| 🟢 成功 | 8 | #11, #12, #13, #30, #31, #32, #33 |
| 🔴 失败 | 14 | #14-#16, #19-#23, #27-#29 |
| ⚪ 取消 | 11 | #1-#10, #17, #18, #24-#26 |

### 5.2 关键里程碑

| 日期 | Run # | 事件 | 结果 |
|------|-------|------|------|
| 07-02 23:33 | #11 | 首次成功 APK 构建（apk_build/ 目录，手动触发） | ✅ |
| 07-02 23:48 | #12 | 重构项目结构 | ✅ |
| 07-02 23:49 | #13 | 结构重构后续 | ✅ |
| 07-02 23:56 | #14-#16 | 工作流适配失败（路径问题） | ❌ |
| 07-03 00:56 | #17-#18 | 修复 module-name（被取消） | ⚪ |
| 07-03 00:58 | #19-#26 | 清理旧结构文件（因文件缺失失败） | ❌/⚪ |
| 07-03 01:04 | #27-#29 | 推送新结构（逐文件推送，前几个因文件不全失败） | ❌ |
| 07-03 01:05 | #30-#33 | 补全共享文件 + 手动触发 -> 最终成功 | ✅ |

### 5.3 最新成功构建 (#33)

| 项目 | 详情 |
|------|------|
| Run URL | https://github.com/zhang58005921-ship-it/macau_lottery/actions/runs/28607838458 |
| 触发方式 | workflow_dispatch（手动） |
| 总耗时 | ≈10分39秒 |
| APK 大小 | 65.59 MB |
| 产物名称 | MacauLotteryV4PRO-APK |
| 下载 | Actions -> Run #33 -> Artifacts |
| 有效期 | 至 2026-09-30 |

---

## 6. 当前状态

| 项目 | 状态 |
|------|------|
| 本地桌面版 | ✅ 正常运行 |
| 本地安卓版 | ✅ 开发模式正常 |
| 桌面 EXE 打包 | ✅ PyInstaller 成功 (74MB) |
| APK 云端编译 | ✅ GitHub Actions 成功 |
| 代码结构 | ✅ shared/desktop/android 分离完成 |
| GitHub 仓库 | ✅ 12个文件同步完成 |

---

## 7. 经验教训

### 7.1 构建失败原因分析

| 失败类型 | 原因 | 解决 |
|----------|------|------|
| cp shared 失败 | 旧工作流在 android/ 目录执行但 shared 在根目录 | 改为 cp -r ../shared shared 或从根目录 cp -r shared android/shared |
| main.py not found | entry point 文件名是 app_android.py 但配置写 main | 统一使用 main.py |
| 文件不全触发构建 | 逐文件 push 时，先 push 的文件触发构建但缺少依赖文件 | 批量 push 后手动触发 |

### 7.2 关键教训

1. 修改工作流后必须手动触发一次验证，不要依赖 push 自动触发
2. 逐文件 push 会触发多次构建，应使用批量 push 或 push 后取消多余 runs
3. cp 命令在 CI 中的路径基准是 $GITHUB_WORKSPACE 或 working-directory
4. 大文件 JSON（>500KB）通过 GitHub API 推送正常，API limit 100MB

---

## 8. 下一步计划

| 优先级 | 任务 | 说明 |
|--------|------|------|
| 🔴 P0 | 下载验证 APK | 安装到 Android 设备测试 |
| 🟡 P1 | 预测模型迭代 | 根据回测结果优化 engine.py |
| 🟡 P1 | 安卓 UI 优化 | 响应式布局调试 |
| 🟢 P2 | 自动更新机制 | 桌面端数据自动同步 |
| 🟢 P2 | 单元测试 | 核心预测函数测试覆盖 |
| ⚪ P3 | 多语言支持 | 简体中文/繁体中文 |

---

## 9. 开发协作规则

> **以下规则用于指导 AI Agent 辅助开发，禁止幻觉，遇到不确定的问题必须询问用户。**

### 9.1 AI Agent 行为准则

1. **禁止幻觉**：不确定的事必须查证或询问，不得编造
2. **单一代码源**：预测模型修改只改 shared/engine.py，不要在两端的 main.py 里复制逻辑
3. **操作前确认**：修改文件前先列计划，涉及 git 操作、删除文件、API 调用等必须确认
4. **构建验证**：推送代码后检查 GitHub Actions 运行状态，失败时分析日志找原因
5. **日志更新**：每次重大操作后更新本 DEVELOPMENT_LOG.md

### 9.2 用户可调用的 Skills

用户在开发中可通过 $SkillName 调用 skills 辅助工作，包括但不限于：

- ecc:codebase-onboarding — 代码库概览
- ecc:code-tour — 代码结构讲解
- ecc:blueprint — 架构设计
- ecc:git-workflow — Git 操作
- superpowers:* — 代码审查、测试等

---

> 📝 本日志随着项目迭代持续更新。每次重大变更后请追加条目。
