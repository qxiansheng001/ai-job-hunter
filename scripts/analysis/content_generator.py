"""学习计划内容生成器：基于用户画像和主题映射输出个性化结构化内容。"""

import json

from analysis.content_loader import get_content_pack
from utils.claude_helper import claude_available, call_claude


# ── 深度 → 学习量映射 ──

DEPTH_CONFIG = {
    "L3": {"label": "深入掌握", "item_count": (4, 6), "total_hours": (6, 8)},
    "L2": {"label": "核心掌握", "item_count": (2, 4), "total_hours": (3, 5)},
    "L1": {"label": "概念了解", "item_count": (1, 2), "total_hours": (1, 2)},
}


# ── Claude 个性化内容生成 ──

_CLAUDE_CONTENT_SYSTEM = """你是一位 AI 学习导师。根据用户背景和市场需求，为每个技能生成个性化学习条目。

要求：
1. 每个条目包含：标题、大白话类比（费曼提示）、实践任务、预计时长
2. 深度级别 L1=概念了解(1-2h), L2=核心掌握(3-5h), L3=深入掌握(6-8h)
3. 利用用户已有技能做类比，不要从零开始讲
4. 内容必须贴合实际技术，不能泛泛而谈
5. 返回 JSON。"""


def _build_content_prompt(skills_with_depth, profile):
    """构造内容生成 prompt。"""
    tech_stack = profile.get("tech_stack", [])
    ai_exp = profile.get("ai_experience_level", "无经验")
    ai_projects = profile.get("ai_projects", "")
    strength_tags = profile.get("strength_tags", []) or profile.get("advantage_tags", [])

    skills_json = json.dumps(skills_with_depth, ensure_ascii=False, indent=2)

    return f"""用户画像：
- 技术栈：{json.dumps(tech_stack, ensure_ascii=True)}
- AI 经验等级：{ai_exp}
- AI 项目经验：{ai_projects or "无"}
- 核心优势标签：{json.dumps(strength_tags, ensure_ascii=True)}

需要学习以下技能（含深度要求）：
{skills_json}

请为每个技能生成 2-4 个学习条目。返回 JSON 数组：

```json
[
  {{
    "theme": "技能主题（与输入 theme 字段一致）",
    "goal": "这个技能的学习目标（一句话）",
    "items": [
      {{
        "title": "学习条目标题",
        "feynman_hint": "大白话解释或类比",
        "practice_task": "具体实践任务",
        "base_hours": 预计小时数（浮点数）
      }}
    ]
  }}
]
```

个性化规则（必须遵守）：
1. 用户已有技能必须在类比和起点中被利用（如会 Flask → LangChain 类比 Flask 路由）
2. AI 经验低 → 从基础概念讲起，多用类比
3. AI 经验高 → 直接深入原理和最佳实践
4. L1 深度 → 1-2 条概念性条目，每个 1-2h
5. L2 深度 → 2-3 条含实践，每个 2-3h
6. L3 深度 → 3-4 条含深度实践，每个 2-3h"""


def _generate_with_claude(skills_with_depth, profile):
    """调用 Claude 生成个性化学习内容。"""
    prompt = _build_content_prompt(skills_with_depth, profile)

    result = call_claude(
        system_prompt=_CLAUDE_CONTENT_SYSTEM,
        user_prompt=prompt,
        response_schema={
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "theme": {"type": "string"},
                    "goal": {"type": "string"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "feynman_hint": {"type": "string"},
                                "practice_task": {"type": "string"},
                                "base_hours": {"type": "number"},
                            },
                            "required": ["title", "feynman_hint", "practice_task", "base_hours"],
                        },
                    },
                },
                "required": ["theme", "goal", "items"],
            },
        },
    )

    if result is None:
        return None

    return {"themes": result}


# ═══════════════════════════════════════════════
# 条目池 — 从 YAML 内容包加载，不再维护硬编码副本
# ═══════════════════════════════════════════════

_content = get_content_pack()
THEME_POOL = _content.get("THEME_POOL", {})
if not isinstance(THEME_POOL, dict):
    THEME_POOL = {}


# ═══════════════════════════════════════════════════════════════
# 核心函数
# ═══════════════════════════════════════════════════════════════

def generate_plan_content(skills_with_depth, profile):
    """生成学习计划内容。

    skills_with_depth: [{"theme": ..., "depth": "L1/L2/L3",
                          "mention_rate": ..., "source": ...}, ...]
    profile: 用户画像字典
    返回: {"themes": [{"theme": ..., "goal": ..., "items": [...]}]}
    """
    # 当 Claude 可用时使用语义生成
    if claude_available():
        claude_result = _generate_with_claude(skills_with_depth, profile)
        if claude_result is not None:
            return claude_result

    # 回退：使用 YAML 内容池
    return _generate_outline_v2(skills_with_depth, profile)


def _select_items_for_user(all_items, profile, depth):
    """基于用户画像从条目池中筛选最适合的条目。

    评分维度：
      - level 匹配目标深度（核心权重）
      - prereq 匹配用户经验水平
      - style 匹配用户优势标签/学历/自驱力

    返回按评分降序排列的条目列表。
    """
    exp = profile.get("ai_experience_level", "无经验")
    edu = profile.get("education", "")
    strength_tags = [s.lower() for s in profile.get("strength_tags", [])]
    self_drive = profile.get("self_drive_score", 0)

    scored = []
    for item in all_items:
        title, hint, task, hours, tags = item
        score = 0

        # 1. Level 匹配（核心）
        item_level = tags.get("level", "L2")
        if item_level == depth:
            score += 10
        elif (depth == "L1" and item_level == "L2") or \
             (depth == "L3" and item_level == "L2"):
            score += 5
        elif (depth == "L2" and item_level in ("L1", "L3")):
            score += 3

        # 2. 前置经验匹配
        prereq = tags.get("prereq", "none")
        if exp == "无经验" and prereq == "none":
            score += 5
        elif exp == "有AI项目经验" and prereq in ("basic", "intermediate"):
            score += 4
        elif exp in ("AI领域资深从业者",) and prereq in ("intermediate", "advanced"):
            score += 5
        elif exp != "无经验" and prereq == "none":
            score += 1  # 有经验的人学入门内容，给点分但不高

        # 3. 风格/优势匹配
        style = tags.get("style", "")
        if any("沟通" in s for s in strength_tags) and style == "writing":
            score += 3
        if any("分析" in s or "架构" in s for s in strength_tags) and style == "analytical":
            score += 3
        if any("学习" in s for s in strength_tags) and style == "technical":
            score += 2
        if edu in ("硕士", "博士") and style == "analytical":
            score += 2
        if self_drive >= 4 and style == "practical":
            score += 2
        if self_drive >= 4 and style == "technical":
            score += 1

        scored.append((score, item))

    scored.sort(key=lambda x: -x[0])
    return [item for _, item in scored]


def _generate_outline_v2(skills_with_depth, profile):
    """基于 THEME_POOL 和用户画像生成个性化学习内容。"""
    themes = []
    for s in skills_with_depth:
        cfg = DEPTH_CONFIG.get(s["depth"], DEPTH_CONFIG["L2"])
        pool_entry = THEME_POOL.get(s["theme"])

        goal = ""
        items = []

        if pool_entry:
            all_items = pool_entry["items"]
            goal = pool_entry["goal"]
            # 筛选：按 item_count 上限取前 N 条
            selected = _select_items_for_user(all_items, profile, s["depth"])
            count = max(1, sum(cfg["item_count"]) // 2)
            for i in range(min(count, len(selected))):
                title, hint, task, hours, _tags = selected[i]
                items.append({
                    "title": title,
                    "feynman_hint": hint,
                    "practice_task": task,
                    "base_hours": hours,
                })
        else:
            # Fallback：主题不在池中，生成通用条目
            total = sum(cfg["total_hours"]) / 2
            n = sum(cfg["item_count"]) // 2
            goal = f"掌握 {s['theme']} 的核心概念与实践（{cfg['label']}）"
            for i in range(max(1, n)):
                items.append({
                    "title": f"{s['theme']} — 核心要点 {i + 1}",
                    "feynman_hint": "用大白话向小白讲清楚这个概念",
                    "practice_task": "阅读相关资料后整理学习笔记",
                    "base_hours": round(total / max(1, n), 1),
                })

        themes.append({"theme": s["theme"], "goal": goal, "items": items})

    return {"themes": themes}
