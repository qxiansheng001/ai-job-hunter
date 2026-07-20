---
name: job-analyze
description: JD 市场需求分析 + 能力差距分析 + 学习计划。需要先有 .skill-state.json
  且 job_search 已完成。可路由到 job-scan。
argument-hint: ""
allowed-tools: Bash(*), Read, Write, Edit, Glob, Skill, WebSearch, WebFetch
---

# /job-analyze — 岗位分析与学习计划

## Step 0：上下文检查

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

- **MISSING** → 调用 `Skill` 执行 `job-init`

读取 `$DATA_DIR/.skill-state.json`，检查 `job_search.status == "done"`。
- 未完成 → 告知用户"请先完成岗位扫描"，调用 `Skill` 执行 `job-scan`

读 SKILL_DIR 下的 `shared-references/analysis-rubric.md` 参考分析方法论。

### 画像完整性检查

读取 `$DATA_DIR/.skill-state.json` 的 `profile`，检查以下字段是否缺失：
- `ai_experience_level`
- `self_drive_score`
- `strength_tags`

如果任一缺失：

> 你的画像信息不完整（缺少 AI 经验等级、自驱力评分或核心优势标签），
> 建议先更新画像再生成计划，否则计划将使用默认值。
> 
> 是否现在更新？[y/n]
> - y → 调用 `Skill` 执行 `job-init`（仅补充缺失字段）
> - n → 继续使用默认值生成

## Step 1：JD 分析

```bash
python "$SKILL_DIR/scripts/analysis/jd_analyzer.py" \
  --input {clean_file} \
  --title "{keyword}" \
  --use-claude
```

其中 `{clean_file}` 和 `{keyword}` 从 `$DATA_DIR/.skill-state.json` 的 `job_search` 读取。

## Step 2：报告输出

> 报告已保存到本地：`$DATA_DIR/subjects/{keyword}/JD_Analysis_Report.md`

更新 `$DATA_DIR/.skill-state.json`：`analysis.report_title=keyword`、`analysis.report_file=$DATA_DIR/subjects/{keyword}/JD_Analysis_Report.md`、`analysis.generated_at=now`。

## Step 3a：选择学习周期

询问用户：

> 你希望学习计划周期多长？
> **1. 30天速成** — 核心技能速通，适合有基础/全职学习者
> **2. 60天标准** — 稳扎稳打，含项目实战，面试就绪（默认）
> **3. 90天深入** — 完整体系，含架构/源码/优化，适合零基础或在职

用户选择后存入变量 `{duration}`（30 / 60 / 90）。

### 坚持周期 × 时长联动检查

读取 `$DATA_DIR/.skill-state.json` 中 `profile.commitment_period`：

- **"不设限"** → 自动推荐 90 天：
  > 你的坚持周期为「不设限」——长期主义是成为专家的唯一路径。推荐 90 天深度版。
  > 是否接受推荐？[y/n]
  > - y → 设 `{duration}=90`
  > - n → 保持已选的 `{duration}`

- **"1个月" 且 `{duration}` > 30**：
  > 你的坚持周期为 1 个月，但你选择了 `{duration}` 天计划。
  > 建议调整为 30 天速成版，或延长坚持周期。
  > 是否调整？[1] 改为 30 天 [2] 保持当前 [3] 先修改画像

- **其他情况**（2个月/3个月/6个月）：如果坚持周期（月数）* 30 < `{duration}`：
  > 你的坚持周期为 `{period}`，建议计划不超过该周期。当前选择了 `{duration}` 天，确认继续？[y/n]

## Step 3b：商业模块询问

询问用户：

> 是否需要包含「技术内容创作与技能变现」模块？（y/n）
> 该模块为技能驱动型——根据你学习的**具体技术栈**，规划对应的内容输出和变现路径，
> 学什么就输出什么、变现什么，不会出现与你技能无关的通用建议。
>
> 内容分发支持 6 大平台（抖音/B站/小红书/知乎/博客/掘金），根据你的画像标签
> 推荐主攻平台，按学习进度生成多平台分发日历，每个平台有专属标题和内容调性。
> 
> 注意：流量和兼职属于锦上添花，不会挤占核心技能学习时间，所有输出内容都建立在已学知识之上。

如果 Step 3a 选了 30 天且 Step 3b 选了 y：

> 注意：30天速成计划已经非常紧凑，加入商业模块可能会影响核心学习进度。
> 确认继续？（y/n）
> - y → 生成含商业模块的 30 天计划
> - n → 生成不含商业模块的 30 天计划

用户选择后存入变量 `{business}`（y / n）。

## Step 3c：学习理念确认

在生成计划前，向用户说明：

> 你的学习计划将深度融合两种顶级学习方法：
> 
> **费曼学习法** — 通过教别人来检验真懂。每天都有「费曼输出任务」，
> 要求你用大白话向小白讲清楚当天的核心概念，卡住的地方就是盲区。
> 
> **第一性原理** — 回归本质的深度思考。每个阶段末有 5 层追问，
> 最终还有核心技术的拆解任务（问题本质→核心原理→最小实现→设计取舍）。
> 
> 这两种方法贯穿每一天的学习，帮你不仅学会技能，更能理解底层原理。

如果 `{business}` 为 y，追加说明：

> 你的计划还包含**技术内容创作与技能变现**模块。请注意：该模块属于锦上添花，
> 不会挤占核心技能学习时间。所有输出内容都建立在已学知识之上，学什么就输出什么、变现什么。
> (如果觉得时间紧张，可随时回到 Step 3b 关闭该模块)

> 确认继续？（y/n）
> - y → 进入配置确认
> - n → 询问用户需要什么调整

## Step 3c-bis：计划配置确认

在生成完整计划前，先调用预览模式展示配置摘要：

```bash
python "$SKILL_DIR/scripts/analysis/gap_analyzer/__main__.py" \
  --profile "$DATA_DIR/.skill-state.json" \
  --report "$DATA_DIR/subjects/{keyword}/JD_Analysis_Report.md" \
  --title "{keyword}" \
  --duration {duration} \
  --business {business} \
  --commitment "{commitment_period}" \
  --preview 2>/dev/null > "$DATA_DIR/_preview_config.json"

python -c "
import json, os
DATA_DIR = '$DATA_DIR'
with open(os.path.join(DATA_DIR, '_preview_config.json')) as f:
    d = json.load(f)

print('========== 计划生成配置确认 ==========')
print()
print(f'目标岗位: {d[\"title\"]}')
print(f'数据来源: BOSS直聘 ({d[\"total_jobs\"]}个岗位样本)')
print(f'学习周期: {d[\"duration\"]}天 | 每周投入: {d[\"weekly_hours\"]} | 强度: {d[\"intensity\"]}')
print(f'AI经验等级: {d[\"ai_experience_level\"]} → 起点: {d[\"start_point\"]}')
	lp = d.get('learning_pace', '日常模式')
	print(f'学习节奏: {lp}')
ed = d.get('self_drive_score', '?')
print(f'自驱力: {ed}/5 → 监督: {d[\"supervision\"]}')
strengths = '、'.join(d['core_strengths']) if d.get('core_strengths') else '无'
print(f'核心优势: {strengths}')
print()
print('权重分配:')
print(f'  [60%] 市场驱动 — 必备技能 {d[\"essential_count\"]}项 + 加分技能 {d[\"bonus_count\"]}项')
print(f'  [30%] 画像匹配 — 起点: {d[\"start_point\"]}')
sup_count = d.get('supplement_count', 0)
sup_pct = d.get('supplement_percent', 0)
print(f'  [10%] 合理补充 — {sup_count}项 ({sup_pct}%)')
print()
print(f'商业模块: {\"包含\" if d.get(\"business_module\", False) else \"不包含\"}')
print()
print('计划详情:')
print(f'  计划模型: {\"连续知识单元\" if d.get(\"plan_model\") == \"continuous\" else \"按周切割\"}')
print(f'  总天数: {d.get(\"total_days\", d[\"duration\"])} 天（含 {d.get(\"review_day_count\", 0)} 个复盘日）')
total_h = d.get('total_days', d['duration']) * d.get('daily_hours', 0)
dh_display = d.get('daily_hours_display', '')
print(f'  预计总学习小时数: ~{int(total_h)}h（日均{dh_display}）')
print(f'  实战项目: {d.get(\"project_count\", 0)} 个 | 开源贡献: {d.get(\"os_contribution_count\", 0)} 次')
print(f'  技能覆盖: 必备技能 {d.get(\"essential_coverage\", \"N/A\")} | 加分技能 {d.get(\"bonus_coverage\", \"N/A\")}')
print()
print('（提示：如需调整每日学习量，可退出后使用 --adjust 0.8~1.2 参数重新生成）')
print('请确认: 输入 Y 继续生成，输入 N 调整参数。')
print('==========================================')
"

rm -f "$DATA_DIR/_preview_config.json"
```

展示配置摘要后，询问用户：

> 请确认是否按以上配置生成学习计划？（y/n）
> - y → 进入 Step 3d 生成完整计划
> - n → 询问调整项：
>   - **1** — 重新选择学习周期（返回 Step 3a）
>   - **2** — 切换商业模块开关（返回 Step 3b）
>   - **3** — 生成 30 天精简版（自动关闭补充模块）
>   - **其他** — 请描述你想调整的内容

## Step 3d：生成学习计划

```bash
python "$SKILL_DIR/scripts/analysis/gap_analyzer/__main__.py" \
  --profile "$DATA_DIR/.skill-state.json" \
  --report "$DATA_DIR/subjects/{keyword}/JD_Analysis_Report.md" \
  --title "{keyword}" \
  --duration {duration} \
  --business {business} \
  --commitment "{commitment_period}"
```

其中 `{commitment_period}` 从 `$DATA_DIR/.skill-state.json` 的 `profile.commitment_period` 读取。

## Step 4：学习计划输出

> 学习计划已保存到本地：`$DATA_DIR/subjects/{keyword}/Learning_Plan_{duration}days_定制版[_with_business].md`

更新 `$DATA_DIR/.skill-state.json`：`learning_plan.target_role=keyword`、`plan_file=$DATA_DIR/subjects/{keyword}/Learning_Plan_{duration}days_定制版[_with_business].md`、`progress.status=in_progress`。

## Step 5：下一步

> 学习计划已就绪，所有文件已保存到本地。你可以随时再次运行 /job-analyze 生成新的岗位分析。
