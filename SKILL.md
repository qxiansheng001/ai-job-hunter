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

数据目录可通过 `AI_JOB_HUNTER_DATA` 环境变量配置，默认为 skill 目录同级的 `ai-job-hunter-data/`。
所有路径引用已自动适配 — 无论 skill 安装在项目级还是全局级均可正常工作。
状态文件 `$AI_JOB_HUNTER_DATA/.skill-state.json` 保存所有进度状态。

## 自动设置

首次进入自动安装依赖：

```bash
# === 自动发现 skill 根目录（适配项目级/全局级安装） ===
SKILL_DIR="${AI_JOB_HUNTER_DIR:-}"
[ -n "$SKILL_DIR" ] && SKILL_DIR="${SKILL_DIR//\\//}"
if [ -z "$SKILL_DIR" ]; then
  [ -d ".claude/skills/ai-job-hunter" ] && SKILL_DIR=".claude/skills/ai-job-hunter"
  [ -z "$SKILL_DIR" ] && [ -d "$HOME/.claude/skills/ai-job-hunter" ] && SKILL_DIR="$HOME/.claude/skills/ai-job-hunter"
fi
DATA_DIR="${AI_JOB_HUNTER_DATA:-$(dirname "$SKILL_DIR")/ai-job-hunter-data}"
mkdir -p "$DATA_DIR/subjects"
pip install -q -r "$SKILL_DIR/requirements.txt" 2>/dev/null || pip install -r "$SKILL_DIR/requirements.txt"
```

## 子技能路由

### 状态检测（FSM 路由）

```bash
# === 自动发现 skill 根目录（适配项目级/全局级安装） ===
SKILL_DIR="${AI_JOB_HUNTER_DIR:-}"
[ -n "$SKILL_DIR" ] && SKILL_DIR="${SKILL_DIR//\\//}"
if [ -z "$SKILL_DIR" ]; then
  [ -d ".claude/skills/ai-job-hunter" ] && SKILL_DIR=".claude/skills/ai-job-hunter"
  [ -z "$SKILL_DIR" ] && [ -d "$HOME/.claude/skills/ai-job-hunter" ] && SKILL_DIR="$HOME/.claude/skills/ai-job-hunter"
fi
DATA_DIR="${AI_JOB_HUNTER_DATA:-$(dirname "$SKILL_DIR")/ai-job-hunter-data}"
python -c "
import sys; sys.path.insert(0, '$SKILL_DIR/scripts')
from utils.fsm import detect_state
import json
try:
    with open('$DATA_DIR/.skill-state.json') as f:
        state = detect_state(json.load(f))
except FileNotFoundError:
    state = None
print(f'STATE={state.value if state else \"no_state\"}')
"
```

根据 STATE 输出路由：

| STATE | 路由 |
|-------|------|
| `no_state` | 调用 `Skill` 执行 `job-init` |
| `profile_done` | 调用 `Skill` 执行 `job-scan` |
| `scan_done` | 调用 `Skill` 执行 `job-analyze`（生成 JD 分析） |
| `analyze_done` | 调用 `Skill` 执行 `job-analyze`（生成学习计划） |
| `plan_done` | 提示用户学习计划已就绪，调用 `Skill` 执行 `job-status` |

### 子技能列表

| 子技能 | 触发词 | 功能 |
|--------|--------|------|
| `job-init` | "初始化画像"、"填写资料" | 用户画像采集 |
| `job-scan` | "找岗位"、"帮我搜索"、"推荐岗位" | 岗位推荐+抓取+清洗 |
| `job-analyze` | "分析岗位"、"做学习计划"、"分析JD" | JD分析+学习计划 |

## 触发方式

"开始求职" / "AI岗位猎手" / "帮我找AI工作" / "job-hunter" / "分析AI岗位" / "看看AI岗位要求" / "找工作"
