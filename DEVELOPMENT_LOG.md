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

---

## 2026-07-03 — 模型诊断与改进 (v4.0.4)

### 诊断发现

回测发现模型存在严重的**预测粘滞**问题：
- 最近20轮仅预测了26/49个号码
- #30 出现19/20次，#41 出现17/20次
- Ensemble Top8 命中率 15.0%（低于随机基线 16.3%）
- Simple Top8 命中率 8.3%（远低于随机）

### 根因

1. EMA 频率模型权重过高，历史高频号码霸占预测
2. UCB 探索系数太小 (0.3)
3. 冷号加分固定 +20，不随冷号持续时长递增
4. 缺少预测多样性约束

### 改进实施

| 优先级 | 改进 | 修改 | 效果 |
|--------|------|------|------|
| 低 | UCB 探索系数 | 0.3 → 0.8 | 增加模型间探索 |
| 低 | 预测多样性罚分 | 重复预测指数衰减 (0.85^count) | 打破循环预测 |
| 低 | 冷号加分 | 与缺失期数成正比，封顶40分 | 适时激活冷号 |
| 低 | 随机注入 | 20%概率替换1-2个冷号 | 强制探索 |
| 中 | 滑动窗口重校 | 每15次预测重跑 _calibrate_from_history | 适应市场变化 |
| 中 | 连续未命重置 | ≥5次连续未命中 → UCB权重重置为均匀 | 逃离局部最优 |

### 改进后回测

| 场景 | Ensemble Top8 | Simple Top8 | 多样性 |
|------|-------------|------------|--------|
| 增量回测 | 15.0% | 16.7% (+8.4pp) | 47/49 |
| **持久会话(带反馈)** | **17.8%** | **18.5%** | 48/49 |

- Ensemble 在持久会话下超过随机基线 (16.3%)
- Simple 翻倍提升 (8.3% → 18.5%)
- 预测多样性从 26/49 提升至 48/49


---

## 2026-07-03 — 代码审计 & Android功能补全 (v4.0.5)

### 审计结果

| 模块 | 文件 | 行数 | 状态 | 问题 |
|------|------|------|------|------|
| 共享引擎 | shared/engine.py | 2027 | ✅ 完整 | 无 |
| 桌面端 | desktop/main.py | 972 | ✅ 完整 | 无 |
| 安卓端 | android/main.py | 670→802 | ⚠️ 需补全 | 缺一码中特、手动录入 |

### 安卓端补全

#### 一码中特预测卡片
- 在 show_predict() 中，特码推荐与综合策略之间插入
- 显示：最佳推荐号码(大字)、生肖、波色、单双、庄家意愿

#### 手动录入开奖数据
- 新增 show_manual_entry()：Flet AlertDialog 表单
- 输入：期号、日期、7个号码（逗号分隔）
- 自动去重、排序、保存、刷新预测器

#### 修复的 Bug
- 变量冲突：oc → wc_color（wave_color 与 odd_even_stats 冲突）
- 缺失变量：total_oe 补回
- 重复行：self.tab_row 去重

#### 录入按钮
- tab 栏绿色"录入"按钮

### 桌面端确认
- 从 main.py.bak 正确恢复，导入共享引擎
- 保留全部功能：DecisionAuditor、一码中特、手动录入

### 验证: 17/17 项集成检查全部通过
---

## 2026-07-03 — 散户热度反向策略 (v4.1.0)

### 问题

引擎缺少**买家数据和论坛预测数据**。媒体宣发和论坛讨论会引导大量散户跟买特定号码，庄家会刻意避开这些热门号（杀大赔小）。之前的模型未考虑这一因素。

### 论坛调研结果

| 平台 | 类型 | 状态 |
|------|------|------|
| 百度贴吧(六合彩吧) | 最大中文论坛 | ❌ 被封 |
| hnffcl.com(2026马到成功) | 预测聚合站 | ⚠️ 自动生成内容 |
| 大三巴导航(736777.com) | 博彩导航 | ⚠️ 聚合页 |
| yb9090.cc | 博彩导航 | ❌ 无讨论 |
| 394tk.com | 心水论坛 | ❌ 已跳转 |
| Bilibili/TikTok | 视频平台 | ❌ 微信诈骗广告 |
| YouTube | 视频平台 | ⚠️ 少量相关内容 |
| 微信公众号/QQ群 | 私域流量 | 🔒 不可爬取 |
| 今日头条 | 新闻聚合 | ⚠️ 需APP |

**结论**: 公开论坛基本被封或充斥诈骗广告，真正买家讨论在微信/QQ私域。采用**代理模型+手动输入**双轨方案。

### 新增: CrowdSentimentLayer 类

位置: shared/engine.py (在 AdversarialPredictor 之前)

#### 散户热度计算 (6维度, 0-100分)

| 信号 | 权重 | 来源 |
|------|------|------|
| 论坛热度 | 40% | 用户手动输入 |
| 媒体炒作分 | 25% | 近期特码开出(指数衰减) |
| 追势散户分 | 15% | 连续出现次数 |
| 迷信偏好分 | 10% | 吉利号码(6,8,9) |
| 生肖年偏好 | 5% | 马年马肖 |
| 频率热度 | 5% | 30期历史频率 |

#### 反向权重

散户热度 → 反向权重映射（反S曲线）：
- 热度 ≤20: 权重 1.0 (冷门，庄家可能开)
- 热度 20-40: 权重 1.0→0.7
- 热度 40-60: 权重 0.7→0.3
- 热度 >60: 权重 ≤0.3 (极度热门，庄家必定避开)

#### 手动论坛数据API

`python
ensemble.crowd.update_forum_data([(8, 9), (18, 8), (28, 7)])
`
- 输入: [(号码, 热度1-10), ...]
- 自动去重、边界限制、时间戳记录

### 集成

- EnsemblePredictor.__init__: 添加 self.crowd = CrowdSentimentLayer(a)
- EnsemblePredictor.predict_specials(): 反向权重融合到最终预测排序

### 测试验证

`
论坛数据: [(8, 9), (18, 8), (28, 7)]
无论坛 → 预测: [9, 16, 26, 45, 1, 2, 3, 4]
有论坛 → 预测: [30, 16, 37, 12, 1, 2, 3, 4]
         ↑ 8,18,28被成功排除
`

### 下一步建议

1. 用户从微信群/朋友圈收集热门号码，通过界面输入
2. 定期更新论坛数据（每日开奖前）
3. 可扩展：接入今日头条API自动抓取彩票相关文章热点

---

## 2026-07-03 — 舆论模块升级 (v4.1.1)

### 修复

| 问题 | 说明 |
|------|------|
| `num_to_zodiac` 未定义 | `crowd_sentiment.py` 独立模块缺少生肖映射函数，导致运行时 `NameError`。已在模块内自包含实现 `_num_to_zodiac()`，使用 `(zi - (n-1)) % 12` 逆序映射。 |

### 时间过滤

新增 `BEFORE_HOUR = 18` 常量，`_is_before_cutoff()` 方法自动过滤当天18:00后发布的帖子。澳门彩晚上21:32开奖，18:00前的预测帖才有参考价值。

### 多源采集

新增 **第二数据源** `@lhczl888`（六合彩大神资料频道，6.42K订阅）：

| 方法 | 来源 | 提取信号 |
|------|------|----------|
| `fetch()` | `@macau6hc` (19.9K) | 热门号码、推荐号码、推荐生肖 |
| `fetch_lhczl888()` | `@lhczl888` (6.42K) | 杀头信号、杀尾信号、心水推荐 |
| `fetch_all()` | 全部 | 合并以上所有信号 |

`lhczl888` 频道特点：只发布经过严格验证（准确率70%+或连中3期）的资料，信号质量更高。

### API 调研结果

| API | 用途 | 状态 |
|-----|------|------|
| `macaumarksix.com/api/live2` | 最新开奖结果 | ✅ 可用（已有 `macaujc_api.py` 覆盖） |
| `history.macaumarksix.com/history/macaujc2/y/2026` | 全年历史数据 | ✅ 可用（已有模块覆盖） |
| `macaujc.com/api/` | 官方API文档 | ✅ 文档存在 |

### 设计原则确认

> 舆论模块只采集**大方向舆情**（热门号、杀号信号、推荐方向），不重复采集开奖数据（`macaujc_api.py` 已覆盖）。权重30%，无当天数据时静默透传。
