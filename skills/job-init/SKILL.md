---
name: job-init
description: AI 岗位求职画像初始化。按 cheat-on-skill 风格一次性开放提问，判定起点档位，写入 .skill-state.json。
argument-hint: ""
allowed-tools: Bash(*), Read, Write, Edit, Glob
---

# /job-init — 画像初始化（cheat-on-skill 风格）

## Phase 0：状态检测

```bash
# === 自动发现 skill 根目录（适配项目级/全局级安装） ===
SKILL_DIR="${AI_JOB_HUNTER_DIR:-}"
[ -n "$SKILL_DIR" ] && SKILL_DIR="${SKILL_DIR//\\//}"
if [ -z "$SKILL_DIR" ]; then
  [ -d ".claude/skills/ai-job-hunter" ] && SKILL_DIR=".claude/skills/ai-job-hunter"
  [ -z "$SKILL_DIR" ] && [ -d "$HOME/.claude/skills/ai-job-hunter" ] && SKILL_DIR="$HOME/.claude/skills/ai-job-hunter"
fi
DATA_DIR="${AI_JOB_HUNTER_DATA:-$(dirname "$SKILL_DIR")/ai-job-hunter-data}"
test -f "$DATA_DIR/.skill-state.json" && echo EXISTS || echo MISSING
```

- **EXISTS**：读取 `$DATA_DIR/.skill-state.json`，展示当前画像摘要，询问用户是否更新
  - 更新 → 进入 Phase 2（保留已有字段，只问需要改的），跳过已填字段
  - 不更新 → 提示用户下一步可以说"帮我找岗位"（→ job-scan）
- **MISSING**：进入 Phase 1

## Phase 1：期望管理（原样表达，语气直白）

> 这工具不会给你一份"AI 高薪岗位 Top10"那种水文清单——那些利益不中立，多是卖课/培训机构的获客漏斗。
>
> 我会做四件别人不做的事：
> ① 按你的真实底子匹配岗位，不给通用清单
> ② 用 BOSS 直聘真实招聘数据看哪些 AI 岗在招、给多少
> ③ 分析高频要求，做出可执行的学习路线
> ④ 遇到带有"培训贷/包就业/付费内推"的，直接劝退
>
> 转型通常需要几个月的真实投入，不是"30 天速成"。认同我们再往下。

## Phase 2：能力盘点（一次性抛出，开放回答）

**一次性抛所有问题**，用户自然语言回答，agent 解析提取。允许"不确定"，对应字段记 null 或空串。

> 我先了解一下你的情况，下面几个问题一起回答就行，不确定的直接说不确定：
>
> **① 你现在掌握了哪些技术/技能？学历专业是什么？**
> 编程语言、框架、工具……哪怕只学过一点也算。学历说清楚是什么学位、什么专业，在读的说年级。
> 例如：Python, LangChain, Docker；本科计算机科学大三
>
> **② AI 相关的经验到什么程度了？**
> 完全零基础 / 懂基本概念但没做过项目 / 独立做过项目 / 资深从业者。不确定就说不确定。
>
> **③ 每周能稳定投入几小时学习？能坚持多久？**
> 按**过去 3 个月真实情况**估，别往多了算。
> 例如：每周大概 10-15 小时，能坚持 3 个月。
>
> **④ 自驱力自评（1-5 分）？**
> 这会决定学习计划里的监督提醒密度。
> 1 分=需要强监督；3 分=能按计划但会拖延；5 分=极强自驱力。
>
> **⑤ 你的核心优势是什么？**
> 比如数学好、编程强、有项目经验、有管理经验、沟通表达强……多擅长就多写。
>
> **⑥ 目标城市在哪？现在是什么状态？**
> 状态选项：在读 / 找实习 / 求职中 / 在职想转。不确定也直说。
>
> **⑦ 你习惯什么学习节奏？**
> - **日常模式**（推荐）: 每天固定学 X 小时，保持节奏感
> - **周末攻坚**: 周中每天抽 1-2h 轻量学习，周末集中 4-6h 攻坚实践
> - **灵活模式**: 不排日期，只给任务清单，自己安排时间
> 直接告诉我就行，不用选数字。

用户回答后，agent 解析提取到以下字段：

| 问题 | state 字段 |
|------|-----------|
| ① 技能+学历 | `tech_stack`(array), `education`(object) |
| ② AI 经验 | `ai_experience_level`(string) |
| ③ 每周时长+周期 | `weekly_hours`(string range), `commitment_period`(string) |
| ④ 自驱力 | `self_drive_score`(int), `learning_self_rating`(string) |
| ⑤ 核心优势 | `strength_tags`(array), `advantage_tags`(array) |
| ⑥ 城市+状态 | `target_city`/`target_cities`(array), `status`(string) |
| ⑦ 学习节奏 | `learning_pace`(string) — "daily" / "weekend" / "flexible" |

**解析规则**：
- `ai_experience_level`：从回答中匹配"零基础/无经验"→"无经验"，"懂概念/基础"→"有AI基础"，"独立做过项目"→"有AI项目经验"，"资深"→"AI领域资深从业者"，"有编程"→"有编程基础但AI零经验"。匹配不到或"不确定"→记空串
- `weekly_hours`：从回答中提取数字范围，格式如 "10-15h"。匹配不到→null
- `commitment_period`：匹配"1个月/2个月/3个月/6个月/不设限"。匹配不到或"不确定"→空串
- `self_drive_score`：提取数字 1-5。匹配不到→null。同步 `learning_self_rating`（1→"需要外部强监督"，2→"偶尔需要提醒"，3→"能按计划但有拖延"，4→"自律性强"，5→"极强自驱力"）
- `strength_tags`：分割逗号/顿号，与预定义标签匹配。未匹配到的归入"其他（自定义）"。同步到 `advantage_tags`
- `target_cities`：解析城市名，单值同时写 `target_city`
- `learning_pace`：匹配"日常/每天/均匀"→"daily"，"周末/攻坚/集中"→"weekend"，"灵活/自由/不排"→"flexible"。匹配不到→"daily"

## Phase 2.5：起点档位判定

读 SKILL_DIR 下的 `shared-references/role-tiers.md`，结合 `tech_stack`、`ai_experience_level`、`self_drive_score` 判定 S0-S3。

规则：
- AI 领域资深从业者 / 自驱力 5 分 / 有项目经验 → 倾向于 S3
- 有 AI 基础 / 有编程基础 + 自驱力 3-4 → S2
- 无经验 + 自驱力 1-2 → S0
- 其他组合 → 居中判断

> 我判断你的起点档位是 **S2**（有技术底子）。
> 你比我更懂自己——可以自己修正。

## Phase 2.6：画像总览确认

生成以下预览让用户确认：

```
┌──── 我的职业画像总览 ─────────────────────────────────────┐
│                                                              │
│  档位         S2 · 有技术底子                                │
│  技能         Python, LangChain, LangGraph                    │
│  学历         本科 · 交通工程（大一）                         │
│  AI 经验      [等级] · [简述]                                 │
│  每周投入     [X]h → 日均约 [Y]h                              │
│  坚持周期     [X]                                              │
│  学习节奏     [日常/周末攻坚/灵活]                              │
│  自驱力       [X]分 — [描述]                                  │
│  核心优势     [A、B、C]                                       │
│  目标城市     [城市]                                          │
│  状态         [状态]                                          │
│                                                              │
│  [1] 确认无误  [2] 修改某项  [3] 重新填写                     │
└──────────────────────────────────────────────────────────────┘
```

如果选择修改 → 问"想修改哪一项？新值是什么？" → 更新后重新展示预览。
如果确认 → 进入 Phase 3。

## Phase 3：写入状态文件

读取 SKILL_DIR 下的 `templates/state.template.json` 填充数据。

```bash
date '+%Y-%m-%d %H:%M %Z %z'
```

写入 `$DATA_DIR/.skill-state.json`，设置 `create_time` 和 `update_time` 为当前时间。

## Phase 4：下一步

> 画像已保存。接下来你可以说：
> - **"帮我找岗位"** — 开始扫描匹配的 AI 岗位
> - **"分析 XX 岗位，做学习计划"** — 直接进入学习计划
> - **"修改我的画像"** — 更新任意字段
