---
name: ai-job-hunter
description: >-
  AI行业岗位猎手。当用户说"开始求职"、"AI岗位猎手"、"帮我找AI工作"、"job-hunter"、
  "分析AI岗位"或类似找AI行业工作的意图时触发。
  自动检测进度状态，路由到对应子 skill 执行。
  包含：画像初始化(job-init) → 岗位扫描(job-scan) → 分析学习(job-analyze)
allowed-tools: Bash(*), Read, Write, Edit, Glob, Skill
---

# ai-job-hunter — AI行业岗位猎手

## 工作流

```
job-init → job-scan → job-analyze
```

各步骤作为独立子 skill 实现，支持自动路由和状态检测。

## 脚本路径

所有 Python 脚本位于 `scripts/` 目录：
- `scripts/scraper/boss_scraper.py` — BOSS直聘 CDP 爬虫
- `scripts/export/clean_and_export.py` — 数据清洗 → Excel
- `scripts/analysis/jd_analyzer.py` — JD 文本分析 → Markdown 报告
- `scripts/analysis/gap_analyzer/` — 能力差距分析 → 学习计划

## 状态文件

数据目录可通过 `AI_JOB_HUNTER_DATA` 环境变量配置，默认为 `../ai-job-hunter-data/`（skill 目录外）。
状态文件 `$AI_JOB_HUNTER_DATA/.skill-state.json` 保存所有进度状态。

## 自动设置

首次进入自动安装依赖：

```bash
DATA_DIR="${AI_JOB_HUNTER_DATA:-../ai-job-hunter-data}"
mkdir -p "$DATA_DIR/subjects"
pip install -q -r requirements.txt 2>/dev/null || pip install -r requirements.txt
```

## 子技能路由

### 检测入口

```bash
DATA_DIR="${AI_JOB_HUNTER_DATA:-../ai-job-hunter-data}"
test -f "$DATA_DIR/.skill-state.json" && echo EXISTS || echo MISSING
```

- **MISSING** → 调用 `Skill` 执行 `job-init`
- **EXISTS** → 读取 `$DATA_DIR/.skill-state.json` 判断进度，路由到对应子 skill：
  - `job_search.status != "done"` → `job-scan`
  - `analysis.report_file == ""` → `job-analyze`
  - `learning_plan.target_role == ""` → `job-analyze`
  - 其他 → 提示用户学习计划已就绪

### 子技能列表

| 子技能 | 触发词 | 功能 |
|--------|--------|------|
| `job-init` | "初始化画像"、"填写资料" | 用户画像采集 |
| `job-scan` | "找岗位"、"帮我搜索"、"推荐岗位" | 岗位推荐+抓取+清洗 |
| `job-analyze` | "分析岗位"、"做学习计划"、"分析JD" | JD分析+学习计划 |

## 触发方式

"开始求职" / "AI岗位猎手" / "帮我找AI工作" / "job-hunter" / "分析AI岗位" / "看看AI岗位要求" / "找工作"
