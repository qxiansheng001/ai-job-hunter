---
name: job-status
description: 学习进度陪跑。跟踪学习计划执行、每日打卡、卡点处理、进度调整。
  需要先有 .skill-state.json 且 learning_plan 已生成。可路由到 job-analyze。
argument-hint: ""
allowed-tools: Bash(*), Read, Write, Edit, Glob, Skill
---

# /job-status — 学习进度陪跑

## Step 0：上下文检查

```bash
DATA_DIR="${AI_JOB_HUNTER_DATA:-../ai-job-hunter-data}"
test -f "$DATA_DIR/.skill-state.json" && echo EXISTS || echo MISSING
```

- **MISSING** → 调用 `Skill` 执行 `job-init`

读取 `$DATA_DIR/.skill-state.json` 的 `learning_plan` 和 `progress`。
- `learning_plan.plan_file` 为空 → 调用 `Skill` 执行 `job-analyze`
- `progress` 为空 → 初始化进度

## Step 1：接住上下文

用 2-4 句话体现连续记忆：

> 你现在是第 **{current_phase}** 阶段第 **{current_week}** 周第 **{current_day}** 天。
> 目标岗位：{target_role}
> 上次完成：{最后一个 completed_tasks 的 artifact}
> 卡点：{blocked_on}

## Step 2：当天任务安排

最多 3 件任务，每件有明确的完成标准。

**进度把控：**
- `behind` → 压缩任务到最小可执行
- `ahead` → 增加扩展任务
- `blocked` → 诊断卡点类别（工具/选择/输入/质量/代码/动力），给最小修复动作

**偏离检测：** 如果用户在学无关内容 → 拉回到"先完成作品集"

## Step 3：打卡处理

判断用户完成度，更新 `$DATA_DIR/.skill-state.json`：

- 追加 `completed_tasks[]`：`{ day, task, artifact: "workspace/day-NN/xxx", at: now }`
- 推进 `current_day` / `current_week` / `current_phase`
- 写 `retro_log[]`：`{ event, summary, next_action }`

**产出落盘：** 用户产出不停在聊天里，存到 `workspace/day-NN/` 目录。

```bash
mkdir -p workspace/day-{current_week}-{current_day}
```

## Step 4：卡住处理

| 卡点类型 | 诊断 | 最小修复动作 |
|----------|------|------------|
| 工具 | 环境/安装问题 | 给出精确命令 |
| 选择 | 不知道学什么 | 缩小到下一个具体任务 |
| 输入 | 缺少资料 | WebSearch 找当前主题最佳教程 |
| 质量 | 产出达不到预期 | 降低标准，先完成再完善 |
| 代码 | 写不出来 | 给代码骨架，让用户填空 |
| 动力 | 不想学 | 缩小到 15 分钟可完成的任务 |

## Step 5：连续 3 天无交付

```bash
test -d workspace/day-{prev_week}-{prev_day} && echo HAS_OUTPUT || echo NO_OUTPUT
```

连续 3 天无产出 → 询问用户是否需要调整计划或暂停。

## Step 6：触发反诈

如果用户提到"付费内推"、"包就业"、"培训贷"等 → 停止并警告。更新 `retro_log[]`。
