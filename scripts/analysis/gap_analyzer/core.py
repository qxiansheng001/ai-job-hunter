"""核心分析引擎：差距分析 + 日历合并 + 内容推荐"""

import json

from analysis.skill_map import (
    SKILL_RESOURCES, SUPPLEMENT_POOL, CONTENT_MAPPING, PROJECT_CONTENT,
    PLATFORM_INFO, PLATFORM_TEMPLATES, MONETIZATION_PATHS, _FILLER_BLOCKS,
    THEME_TO_SKILL, SKILL_TO_THEME,
)
from utils.protocol import emit
from utils.io import normalize_profile
from utils.time import (
    _parse_hours_float, _compute_daily_hours, _format_hours_display, _self_drive_label,
    compute_pace_hours,
)
from utils.claude_helper import claude_available, call_claude


# ══════════════════════════════════════════════
# 差距分析
# ══════════════════════════════════════════════

# Claude 语义技能匹配

_SEMANTIC_SKILL_SYSTEM = """你是一位 AI 求职顾问。分析用户的技能背景与市场岗位需求之间的匹配关系。

对于每个市场需要的技能，判断用户是否掌握、部分掌握或未掌握，并给出个性化的学习起点建议。

返回 JSON 格式。"""


def _build_semantic_match_prompt(user_skills, ai_projects, ai_exp_level, market_skills):
    """构造语义技能匹配 prompt。"""
    skills_json = json.dumps(
        [{"skill": s["name"], "mention_rate": s.get("mention_rate", 0),
          "priority": s.get("priority", "必修")} for s in market_skills],
        ensure_ascii=False,
    )
    return f"""用户技能背景：
- 技术栈：{json.dumps(user_skills, ensure_ascii=False)}
- AI 项目经验：{ai_projects or "无"}
- AI 经验等级：{ai_exp_level}

市场需求技能（含提及率）：
{skills_json}

请判断用户对每个市场技能的掌握情况。返回 JSON 数组，每个元素：
{{
  "skill": "技能名称",
  "user_has": true/false,        # true=已掌握，false=未掌握
  "status": "mastered/partial/missing",
  "start_point": "个性化的学习起点建议，如「有 Python + Flask 基础，类比 Flask 路由理解 Chain 概念」",
  "reason": "一句简短理由"
}}

注意：如果用户有相关可迁移技能（如会 Flask → 易于学 LangChain），请在 start_point 中体现。"""


def _semantic_skill_match(user_skills, ai_projects, ai_exp_level, market_skills):
    """调用 Claude 进行语义技能匹配。

    返回 dict: {skill_name: {"user_has": bool, "status": str, "start_point": str}}
    或 None（调用失败时）。
    """
    if not market_skills:
        return None

    prompt = _build_semantic_match_prompt(user_skills, ai_projects, ai_exp_level, market_skills)

    result = call_claude(
        system_prompt=_SEMANTIC_SKILL_SYSTEM,
        user_prompt=prompt,
        response_schema={
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "skill": {"type": "string"},
                    "user_has": {"type": "boolean"},
                    "status": {"type": "string", "enum": ["mastered", "partial", "missing"]},
                    "start_point": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["skill", "user_has", "status", "start_point"],
            },
        },
    )

    if result is None:
        return None

    return {item["skill"]: item for item in result}


def analyze_gap(profile_data, report_data, duration=90):
    """市场驱动型差距分析：60% 市场 + 30% 画像 + 10% 补充"""
    profile = normalize_profile(profile_data)
    user_skills_raw = [s.lower() for s in profile.get("tech_stack", [])]
    ai_projects = (profile.get("ai_projects") or "").lower()
    strength_tags = profile.get("strength_tags", []) or profile.get("advantage_tags", [])
    ai_exp_level = profile.get("ai_experience_level", "")

    # ── 语义技能匹配（可用时）──
    semantic_result = None
    if claude_available():
        all_market_skills_raw = []
        seen = set()
        for skill_name, mention_rate in report_data.get("essential_skills", []):
            if skill_name.lower() not in seen:
                all_market_skills_raw.append({"name": skill_name, "mention_rate": mention_rate, "priority": "核心必修"})
                seen.add(skill_name.lower())
        for skill_name, mention_rate in report_data.get("bonus_skills", []):
            if skill_name.lower() not in seen:
                all_market_skills_raw.append({"name": skill_name, "mention_rate": mention_rate, "priority": "加分必修"})
                seen.add(skill_name.lower())
        if all_market_skills_raw:
            semantic_result = _semantic_skill_match(
                profile.get("tech_stack", []),
                profile.get("ai_projects", ""),
                ai_exp_level,
                all_market_skills_raw,
            )

    def _user_has_skill(key):
        """模糊匹配：user_skills 中任一技能包含 key 或被 key 包含"""
        if not key:
            return False
        # 语义结果优先
        if semantic_result and key in semantic_result:
            return semantic_result[key].get("user_has", False)
        return any(key in us or us in key for us in user_skills_raw) or key in ai_projects

    def _get_start_point(key):
        """获取语义起点建议（仅 Claude 模式有）。"""
        if semantic_result and key in semantic_result:
            return semantic_result[key].get("start_point", "")
        return ""

    report_top_skill_names = [s for s, _ in report_data.get("top_skills", [])]
    essential = report_data.get("essential_skills", []) or []
    bonus = report_data.get("bonus_skills", []) or []

    # STEP 1: Market-driven skill selection (60% weight)
    market_skills = []
    seen = set()

    for skill_name, mention_rate in essential:
        key = skill_name.lower()
        if key not in seen:
            user_has = _user_has_skill(key)
            start_pt = _get_start_point(key)
            entry = {
                "name": skill_name, "mention_rate": mention_rate,
                "source": "essential", "priority": "核心必修", "user_has": user_has,
            }
            if start_pt:
                entry["start_point"] = start_pt
            market_skills.append(entry)
            seen.add(key)

    for skill_name, mention_rate in bonus:
        key = skill_name.lower()
        if key not in seen:
            user_has = _user_has_skill(key)
            start_pt = _get_start_point(key)
            entry = {
                "name": skill_name, "mention_rate": mention_rate,
                "source": "bonus", "priority": "加分必修", "user_has": user_has,
            }
            if start_pt:
                entry["start_point"] = start_pt
            market_skills.append(entry)
            seen.add(key)

    # STEP 2: User profile adjustment (30% weight)
    exp_start_map = {
        "无经验": {"offset": 0, "desc": "从AI基础概念预热开始", "skip_mastered": False},
        "有编程基础但AI零经验": {"offset": 1, "desc": "从Python高级特性开始", "skip_mastered": False},
        "有AI基础": {"offset": 2, "desc": "从LangChain核心组件开始", "skip_mastered": True},
        "有AI项目经验": {"offset": 2, "desc": "从LangChain开始，跳过已掌握", "skip_mastered": True},
        "AI领域资深从业者": {"offset": 4, "desc": "直接进入深度专精期", "skip_mastered": True},
    }
    start_config = exp_start_map.get(ai_exp_level, {"offset": 1, "desc": "标准起点", "skip_mastered": False})
    experience_start_point = start_config["desc"]

    wh = profile.get("weekly_hours", "15-20h")
    daily = _compute_daily_hours(wh)
    if daily <= 1.5:
        hours_tier = "轻量"
    elif daily >= 4:
        hours_tier = "饱满"
    else:
        hours_tier = "标准"

    # 学习节奏模式
    pace_raw = profile.get("learning_pace", "daily")
    learning_pace = compute_pace_hours(pace_raw, wh)

    sd_score = profile.get("self_drive_score", 3)
    sd_label, sd_flag = _self_drive_label(sd_score)

    # STEP 3: Supplement selection (10% weight)
    total_days = duration
    total_available_hours = daily * total_days
    max_supplement_hours = total_available_hours * 0.10

    supplement_candidates = []
    supp_hours_total = 0

    if total_days > 30 and daily >= 1.5:
        for supp in SUPPLEMENT_POOL:
            if supp_hours_total + supp["hours"] > max_supplement_hours:
                continue
            check_profile = profile if supp["condition_type"] == "C" else None
            check_report = report_data if supp["condition_type"] != "C" else None
            try:
                if supp["condition_type"] == "C":
                    passes = supp["condition_fn"](profile)
                else:
                    passes = supp["condition_fn"](report_data)
                if passes:
                    supplement_candidates.append({**supp, "actual_hours": supp["hours"]})
                    supp_hours_total += supp["hours"]
            except Exception as e:
                emit("gap.supplement.skip", f"跳过补充模块 {supp.get('name', '?')}: {e}",
                     status="warn", warnings=[str(e)], stream=sys.stderr)
                continue

    # Gap analysis (backward compatible)
    has_skills = []
    missing_skills = []
    gap_analysis = []

    for skill, info in SKILL_RESOURCES.items():
        skill_lower = skill.lower()
        # 语义匹配优先
        if semantic_result and skill in semantic_result:
            user_has = semantic_result[skill].get("user_has", False)
            semantic_status = semantic_result[skill].get("status", "missing")
            semantic_start = semantic_result[skill].get("start_point", "")
        else:
            user_has = skill_lower in user_skills_raw or skill_lower in ai_projects
            semantic_status = "mastered" if user_has else "missing"
            semantic_start = ""

        if user_has:
            has_skills.append(skill)
        else:
            market_need = any(skill_lower in s for s in report_top_skill_names)
            if market_need or info["priority"] in ("必修", "核心"):
                missing_skills.append(skill)
                if semantic_start:
                    sp = semantic_start
                elif ai_exp_level in ("有AI项目经验", "AI领域资深从业者"):
                    sp = "有基础，建议快速浏览"
                elif ai_exp_level in ("有AI基础",):
                    sp = "了解概念，需系统学习"
                else:
                    sp = "从零开始"
                gap_analysis.append({
                    "skill": skill, "priority": info["priority"],
                    "type": info["type"], "status": "缺失",
                    "start_point": sp, "resources": info["resources"],
                })

    leverage_skills = []
    for tag in strength_tags:
        for ms in report_top_skill_names:
            if tag[:2].lower() in ms.lower() or ms.lower() in tag.lower():
                leverage_skills.append({"tag": tag, "market_match": ms})
                break

    supp_explanations = []
    for supp in supplement_candidates:
        reason_map = {"A": "行业底层基础", "B": "行业趋势验证", "C": "优势标签深化"}
        supp_explanations.append({
            "name": supp["name"], "label": supp["label"],
            "reason": reason_map.get(supp["condition_type"], "合理补充"),
            "hours": supp["actual_hours"], "goal": supp["goal"],
        })

    return {
        "has_skills": has_skills, "missing_skills": missing_skills,
        "gap_analysis": gap_analysis, "leverage_skills": leverage_skills,
        "experience_start_point": experience_start_point,
        "market_skills": market_skills, "start_config": start_config,
        "hours_tier": hours_tier, "daily_hours": daily,
        "sd_label": sd_label, "sd_flag": sd_flag,
        "supplement_candidates": supplement_candidates,
        "supplement_explanations": supp_explanations,
        "supplement_hours_total": supp_hours_total,
        "total_available_hours": total_available_hours,
        "learning_pace": learning_pace,
    }


# ══════════════════════════════════════════════
# 内容推荐与变现
# ══════════════════════════════════════════════

def recommend_platforms(profile, simple_mode, duration):
    """Recommend platforms based on profile advantage tags and duration."""
    preferred = profile.get("preferred_platforms", None)
    if preferred:
        valid = [p for p in preferred if p in PLATFORM_INFO]
        return valid, valid[:min(2, len(valid))]

    if simple_mode or duration <= 30:
        platform_count = 2
    elif duration <= 60:
        platform_count = 4
    else:
        platform_count = 6

    adv_tags = [t.lower() for t in profile.get("advantage_tags", [])]
    str_tags = [t.lower() for t in profile.get("strength_tags", [])]
    all_tags = list(set(adv_tags + str_tags))
    tags_str = " ".join(all_tags)

    scores = {p: 0 for p in PLATFORM_INFO}

    if "开源" in tags_str:
        scores["博客"] += 3; scores["掘金"] += 2
    if "表达" in tags_str or "表达力" in tags_str or "沟通表达" in tags_str:
        scores["哔哩哔哩"] += 3; scores["抖音"] += 2
    if "文字" in tags_str or "写作" in tags_str or "数学" in tags_str:
        scores["知乎"] += 3; scores["博客"] += 2
    if "设计" in tags_str or "审美" in tags_str:
        scores["小红书"] += 2; scores["抖音"] += 1
    if "编程" in tags_str or "工程化" in tags_str:
        scores["掘金"] += 2; scores["博客"] += 2

    platform_order = ["哔哩哔哩", "掘金", "知乎", "博客", "小红书", "抖音"]
    sorted_platforms = sorted(
        PLATFORM_INFO.keys(),
        key=lambda p: (-scores[p], platform_order.index(p) if p in platform_order else 99)
    )

    selected = sorted_platforms[:platform_count]
    primary = selected[:min(2, len(selected))]
    return selected, primary


def get_skill_weeks(phases):
    """Extract (week_num, theme) list from selected phases."""
    result = []
    for phase_data in phases:
        for w in phase_data["weeks"]:
            result.append((w["week"], w["theme"]))
    return result


def build_content_calendar(phases, simple_mode, duration, profile=None):
    """Build content calendar synchronized with learning schedule."""
    skill_weeks = get_skill_weeks(phases)
    max_items = 3 if simple_mode else (8 if duration <= 60 else len(skill_weeks) + 1)
    calendar = []

    for week_num, theme in skill_weeks:
        if len(calendar) >= max_items:
            break
        if theme in CONTENT_MAPPING:
            entry = CONTENT_MAPPING[theme]
            calendar.append({
                "output_week": week_num + 1,
                "title": entry["title"], "type": entry["type"],
            })

    if len(calendar) < max_items:
        project_week = (calendar[-1]["output_week"] + 1 if calendar else
                       max(w["week"] for p in phases for w in p["weeks"]) + 1)
        calendar.append({
            "output_week": project_week,
            "title": PROJECT_CONTENT["title"], "type": PROJECT_CONTENT["type"],
        })

    if profile:
        platforms, _ = recommend_platforms(profile, simple_mode, duration)
        for entry in calendar:
            content_type = entry.get("type", "技术教程")
            templates = PLATFORM_TEMPLATES.get(content_type, PLATFORM_TEMPLATES["技术教程"])
            topic_short = entry["title"].split("：")[0] if "：" in entry["title"] else entry["title"]
            entry["platforms"] = {p: templates[p].format(topic_short) for p in platforms}

    return calendar


def build_monetization_plan(phases, simple_mode, duration):
    """Build skill-based freelancing recommendations."""
    skill_weeks = get_skill_weeks(phases)
    all_themes = " ".join(t for _, t in skill_weeks)
    max_items = 2 if simple_mode else (4 if duration <= 60 else len(MONETIZATION_PATHS))

    paths = []
    for m in MONETIZATION_PATHS:
        if len(paths) >= max_items:
            break
        if any(s.lower() in all_themes.lower() for s in m["match"]):
            price_key = "price_30" if simple_mode else ("price_60" if duration <= 60 else "price_90")
            price = m.get(price_key, m.get("price_90", ""))
            paths.append({"title": m["title"], "channels": m["channels"], "price": price})

    return paths


# ══════════════════════════════════════════════
# 填充块生成
# ══════════════════════════════════════════════

def _generate_filler_blocks(unit_type, delta_hours, topic=""):
    """按剩余时间依次选取填充块。delta_hours: 剩余小时数(>0)。"""
    pool = _FILLER_BLOCKS.get(unit_type, _FILLER_BLOCKS["study"])
    blocks = []
    rem = delta_hours
    for blk_type, blk_label_tmpl, max_dur in pool:
        if rem <= 0.15:
            break
        dur = min(round(rem, 1), max_dur)
        if dur >= 0.2:
            blocks.append({"type": blk_type, "topic": blk_label_tmpl.format(topic=topic), "hours": dur})
            rem -= dur
    return blocks


# ══════════════════════════════════════════════
# 日合并引擎
# ══════════════════════════════════════════════

def _build_blocks_for_group(template_group, coeff):
    """一个模板天拆为 [核心50%, 实践30%(if has task), 费曼20%] 块。"""
    blocks = []
    for d in template_group:
        dur = _parse_hours_float(d[4]) * coeff
        blocks.append({"type": "核心", "topic": d[1], "hours": round(dur * 0.50, 1)})
        if d[3]:
            blocks.append({"type": "实践", "topic": d[3], "hours": round(dur * 0.30, 1)})
        blocks.append({"type": "费曼", "topic": d[2], "hours": round(max(0.3, dur * 0.20), 1)})
    return blocks


def _merge_into_calendar_days(template_days, daily_budget, coeff=1.0):
    """
    动态弹性编排：将多个模板天打包为日历天，允许每日时长在 ±25% 内浮动。
    每天可含 1~3+ 个知识点，由知识点预估耗时自然决定。
    """
    active = [d for d in template_days if _parse_hours_float(d[4]) >= 0.01]
    if not active:
        return []

    coeff = max(0.4, coeff)
    target = daily_budget
    min_h = target * 0.75
    max_h = target * 1.25

    items = []
    for d in active:
        items.append({
            "title": d[1], "feynman": d[2], "practice": d[3],
            "base_hours": _parse_hours_float(d[4]),
            "scaled_hours": round(_parse_hours_float(d[4]) * coeff, 1),
        })

    result = []
    i = 0
    while i < len(items):
        batch_items = [items[i]]
        batch_hours = items[i]["scaled_hours"]
        i += 1

        while i < len(items):
            nxt = items[i]
            if batch_hours + nxt["scaled_hours"] <= max_h:
                batch_items.append(nxt)
                batch_hours += nxt["scaled_hours"]
                i += 1
                if batch_hours >= min_h:
                    break
            else:
                break

        blocks = []
        for item in batch_items:
            blocks.append({"type": "核心", "topic": item["title"],
                           "hours": round(item["scaled_hours"] * 0.50, 1)})
            if item["practice"]:
                blocks.append({"type": "实践", "topic": item["practice"],
                               "hours": round(item["scaled_hours"] * 0.25, 1)})
            blocks.append({"type": "费曼", "topic": item["title"],
                           "hours": round(max(0.25, item["scaled_hours"] * 0.20), 1)})

        filler = round(max(0, target - batch_hours), 1)
        if filler > 0.3 and batch_items:
            fblocks = _generate_filler_blocks("study", filler, batch_items[-1]["title"])
            blocks.extend(fblocks)
        else:
            filler = 0

        result.append({
            "topics": [it["title"] for it in batch_items],
            "feynman_hints": [it["feynman"] for it in batch_items],
            "practice_tasks": [it["practice"] for it in batch_items],
            "base_hours": round(sum(it["base_hours"] for it in batch_items), 1),
            "scaled_hours": round(batch_hours, 1),
            "filler_hours": filler,
            "blocks": blocks,
            "tags": [],
        })

    return result


def _cap_blocks_hours(blocks, target_total):
    """等比缩放 blocks 中的 hours 使其总和不超过 target_total。"""
    current = sum(b["hours"] for b in blocks)
    if current <= target_total:
        return blocks
    ratio = target_total / current
    for b in blocks:
        b["hours"] = round(b["hours"] * ratio, 1)
    return blocks


# ══════════════════════════════════════════════
# 查询工具
# ══════════════════════════════════════════════

def _get_market_annotation(topic, market_skills, week_theme=None):
    """Find which market skill a study topic maps to."""
    for ms in market_skills:
        mn = ms["name"].lower()
        if mn in topic.lower():
            source_label = "必备技能" if ms.get("source") == "essential" else "加分技能"
            return {"name": ms["name"], "mention_rate": ms.get("mention_rate", 0), "source_label": source_label}
    if week_theme:
        skill_name = THEME_TO_SKILL.get(week_theme)
        if skill_name:
            for ms in market_skills:
                if ms["name"].lower() == skill_name.lower():
                    source_label = "必备技能" if ms.get("source") == "essential" else "加分技能"
                    return {"name": ms["name"], "mention_rate": ms.get("mention_rate", 0), "source_label": source_label}
    return None
