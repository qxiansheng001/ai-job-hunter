"""学习计划渲染器：Markdown 生成 + 预览 + CLI 入口"""

import json
import re
import sys
import os
import argparse
from datetime import datetime

from analysis.skill_map import SKILL_RESOURCES, PLATFORM_INFO, PROJECT_WEEK
from analysis.gap_analyzer.core import (
    analyze_gap, _get_market_annotation,
    build_content_calendar, build_monetization_plan, recommend_platforms,
)
from analysis.gap_analyzer.plan_builder import (
    build_continuous_plan, build_market_driven_plan,
)
from utils.time import (
    _parse_hours_float, _parse_hours, _format_hours_display,
    _compute_time_coefficient, _compute_task_intensity, _self_drive_label,
)
from utils.io import load_profile, load_report


# ══════════════════════════════════════════════
# 辅助
# ══════════════════════════════════════════════

def _phases_from_kus(kus):
    """从 KU 重建 phases 结构供 build_content_calendar/build_monetization_plan 使用。
    兼容新旧两种 KU 格式：旧格式 theme 在 KU 级别，新格式在 _merged_days 内。"""
    phase_map = {}
    for ku in kus:
        pn = ku.get("phase_num", 1)
        if pn not in phase_map:
            phase_map[pn] = set()
        # 新格式：从 _merged_days 的 blocks 中提取主题
        for cd in ku.get("_merged_days", []):
            for b in cd.get("blocks", []):
                if b.get("type") == "核心" and b.get("topic"):
                    phase_map[pn].add(b["topic"])
        # 旧格式：直接从 KU theme 字段获取
        if ku.get("theme"):
            phase_map[pn].add(ku["theme"])

    from analysis.skill_map import THEME_TO_SKILL
    phases = []
    for pn in sorted(phase_map.keys()):
        phase_name = {1: "基础夯实期", 2: "深度专精期", 3: "实战输出期"}.get(pn, f"阶段{pn}")
        # 提取第一个 topic 作为 summary（取较长的作为有意义的主题名称）
        all_topics = list(phase_map[pn])
        # 尝试匹配已知 theme
        weeks = []
        seen = set()
        theme_index = 1
        for topic in all_topics:
            matched = False
            for known_theme in THEME_TO_SKILL:
                if known_theme[:4].lower() in topic.lower() or topic[:4].lower() in known_theme.lower():
                    if known_theme not in seen:
                        weeks.append({"week": theme_index, "theme": known_theme})
                        seen.add(known_theme)
                        theme_index += 1
                        matched = True
                        break
            if not matched and topic not in seen:
                weeks.append({"week": theme_index, "theme": topic[:20]})
                seen.add(topic)
                theme_index += 1
        if not weeks:
            weeks = [{"week": 1, "theme": phase_name}]
        phases.append({"phase": pn, "phase_name": phase_name, "weeks": weeks})
    return phases


# ══════════════════════════════════════════════
# 预览 JSON
# ══════════════════════════════════════════════

def generate_preview_json(profile_data, report_data, gap_data, title, duration, business):
    """Generate preview data dict for --preview mode."""
    p = profile_data.get("profile", profile_data)
    market_skills = gap_data.get("market_skills", [])
    supp_candidates = gap_data.get("supplement_candidates", [])
    total_jobs = report_data.get("total_jobs", 0)
    supp_hours = gap_data.get("supplement_hours_total", 0)
    total_hours = max(gap_data.get("total_available_hours", 1), 1)

    n_essential = len([ms for ms in market_skills if ms.get("source") == "essential"])
    n_bonus = len([ms for ms in market_skills if ms.get("source") == "bonus"])
    start_config = gap_data.get("start_config", {})
    strengths = p.get("strength_tags", []) or p.get("advantage_tags", [])
    essential_list = [{"name": ms["name"], "mention_rate": ms.get("mention_rate", 0), "user_has": ms.get("user_has", False)} for ms in market_skills if ms.get("source") == "essential"]
    bonus_list = [{"name": ms["name"], "mention_rate": ms.get("mention_rate", 0), "user_has": ms.get("user_has", False)} for ms in market_skills if ms.get("source") == "bonus"]

    use_continuous = bool(market_skills) and duration >= 30
    plan_model = "continuous" if use_continuous else "week-based"
    total_days = duration
    project_count = 0
    os_contribution_count = 0
    review_day_count = 0
    essential_covered = 0
    bonus_covered = 0

    if use_continuous:
        ps = build_continuous_plan(market_skills, supp_candidates, duration, p, gap_data)
        total_days = ps["total_days"]
        project_count = len(ps["projects"])
        os_contribution_count = len(ps["os_contributions"])
        review_day_count = len(ps["review_days"])
        essential_covered = ps.get("essential_covered", 0)
        bonus_covered = ps.get("bonus_covered", 0)

    return {
        "title": title, "plan_model": plan_model, "total_jobs": total_jobs,
        "duration": duration, "total_days": total_days,
        "weekly_hours": p.get("weekly_hours", ""),
        "intensity": gap_data.get("hours_tier", "标准"),
        "daily_hours": round(gap_data.get("daily_hours", 0), 1),
        "daily_hours_display": _format_hours_display(round(gap_data.get("daily_hours", 0), 1)),
        "ai_experience_level": p.get("ai_experience_level", "未知"),
        "start_point": start_config.get("desc", "标准起点"),
        "self_drive_score": p.get("self_drive_score"),
        "supervision": gap_data.get("sd_label", "正常"),
        "core_strengths": strengths,
        "essential_count": n_essential, "bonus_count": n_bonus,
        "essential_skills": essential_list, "bonus_skills": bonus_list,
        "essential_coverage": f"{essential_covered}/{n_essential}" if n_essential > 0 else "N/A",
        "bonus_coverage": f"{bonus_covered}/{n_bonus}" if n_bonus > 0 else "N/A",
        "supplement_count": len(supp_candidates),
        "supplement_percent": round(supp_hours / total_hours * 100),
        "supplements": [{"name": s["name"], "label": s.get("label", ""), "hours": s.get("hours", 0)} for s in supp_candidates],
        "business_module": business == "y",
        "project_count": project_count, "os_contribution_count": os_contribution_count,
        "review_day_count": review_day_count,
    }


# ══════════════════════════════════════════════
# 每日计划渲染
# ══════════════════════════════════════════════

def generate_daily_plan(profile, gap_data, title, duration=60, business=False, commitment_period="", report_data=None):
    """生成含每日任务的详细学习计划"""
    lines = []
    p = profile.get("profile", profile)
    if report_data is None:
        report_data = {}

    lines.append(f"# {title} — 能力差距分析与学习计划")
    lines.append("")
    lines.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"> 基于个人画像与 BOSS直聘招聘数据分析")
    lines.append(f"> 学习策略：费曼学习法 + 第一性原理 + 项目驱动")
    lines.append("")

    market_skills = gap_data.get("market_skills", [])
    supp_candidates = gap_data.get("supplement_candidates", [])
    supp_explanations = gap_data.get("supplement_explanations", [])
    total_jobs = report_data.get("total_jobs", 0)
    hours_tier = gap_data.get("hours_tier", "标准")
    daily_h = gap_data.get("daily_hours", 0)
    time_coeff = _compute_time_coefficient(daily_h)

    exp_level = p.get("ai_experience_level", "未填写")
    wh_range = p.get("weekly_hours", "")
    intensity, daily_actual = _compute_task_intensity(p)
    sd_score = p.get("self_drive_score")
    sd_label, sd_flag = _self_drive_label(sd_score)
    strengths = p.get("strength_tags", []) or p.get("advantage_tags", [])

    lines.append("## 计划生成依据")
    lines.append("")
    lines.append("### 数据来源")
    lines.append(f"- **市场数据**：BOSS直聘 共 {total_jobs} 个 {title} 岗位")
    lines.append(f"- **个人画像**：{exp_level}，每周 {wh_range}，自驱力 {sd_score}/5")
    lines.append(f"- **分析方法**：词频统计 + TF-IDF + 技能提及率（必备 >= 30%，加分 10%-30%）")
    lines.append("")
    lines.append("### 权重分配")
    lines.append("| 维度 | 权重 | 说明 |")
    lines.append("|------|------|------|")
    n_essential = len([ms for ms in market_skills if ms.get("source") == "essential"])
    n_bonus = len([ms for ms in market_skills if ms.get("source") == "bonus"])
    lines.append(f"| 市场需求 | 60% | 必备技能 {n_essential}项 + 加分技能 {n_bonus}项，按提及率排序 |")
    lines.append(f"| 个人画像 | 30% | 经验等级→起点，每周投入→强度，自驱力→监督密度，优势标签→侧重点 |")
    supp_pct = gap_data.get("supplement_hours_total", 0) / max(gap_data.get("total_available_hours", 1), 1) * 100
    lines.append(f"| 合理补充 | 10% | {len(supp_candidates)}项拓展模块，占比约 {supp_pct:.0f}%，非强制 |")
    lines.append("")
    lines.append("### 市场必备技能（核心学习内容）")
    lines.append("| 技能 | 提及率 | 优先级 | 当前状态 |")
    lines.append("|------|--------|--------|---------|")
    for ms in market_skills:
        status = "已掌握，继续深化" if ms.get("user_has") else "待系统学习"
        lines.append(f"| {ms['name']} | {ms.get('mention_rate', 0):.1f}% | {ms.get('priority', '必修')} | {status} |")
    lines.append("")

    lines.append("### 画像摘要")
    lines.append("")
    lines.append(f"> 本计划基于以下画像定制生成：")
    lines.append(f"> - **目标岗位**: {title}")
    lines.append(f"> - **AI 经验等级**: {exp_level} → 学习起点：{gap_data.get('experience_start_point', 'Phase 1 Week 1')}")
    if wh_range:
        lines.append(f"> - **每周投入**: {wh_range} → 日均约 {daily_actual:.1f}h → 任务强度：{intensity}")
    if sd_score is not None:
        lines.append(f"> - **自驱力评分**: {sd_score}/5 → 监督提醒：{sd_label}")
    if strengths:
        lines.append(f"> - **核心优势**: {'、'.join(strengths)}")
    if commitment_period:
        if commitment_period == "不设限":
            lines.append(f"> - **坚持周期**: 不设限 → 长期主义是成为专家的唯一路径，加油！")
        else:
            lines.append(f"> - **坚持周期**: {commitment_period}")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## 一、当前能力盘点")
    lines.append("")
    lines.append(f"- **身份**：{p.get('identity', '未知')} · {p.get('education', {}).get('major', '未知专业')}")
    lines.append(f"- **已有技能**：{'、'.join(p.get('tech_stack', ['无']))}")
    lines.append(f"- **AI 经验等级**：{exp_level}")
    if p.get("ai_projects"):
        lines.append(f"- **AI 项目经验**：{p['ai_projects']}")
    lines.append(f"- **可投入时间**：{p.get('daily_hours', '未知')}/天（{wh_range}）")
    if strengths:
        lines.append(f"- **核心优势**：{'、'.join(strengths)}")
    lines.append("")

    lines.append("## 二、技能差距分析")
    lines.append("")
    lines.append(f"### 已掌握（{len(gap_data['has_skills'])} 项）")
    lines.append("")
    for s in gap_data["has_skills"]:
        lines.append(f"- **{s}** — 已具备基础，继续深化")
    lines.append("")
    lines.append(f"### 待补充（{len(gap_data['missing_skills'])} 项）")
    lines.append("")
    lines.append("| 技能 | 类型 | 优先级 | 您的起点 | 建议资源 |")
    lines.append("|------|------|--------|---------|----------|")
    for g in gap_data["gap_analysis"]:
        resources = g["resources"][0] if g["resources"] else ""
        start = g.get("start_point", "从零开始")
        lines.append(f"| **{g['skill']}** | {g['type']} | {g['priority']} | {start} | {resources} |")
    lines.append("")

    leverage = gap_data.get("leverage_skills", [])
    if leverage:
        lines.append("---")
        lines.append("")
        lines.append("### 杠杆策略：发挥优势，补齐短板")
        lines.append("")
        lines.append("| 您的优势 | 市场需求匹配 | 策略 |")
        lines.append("|---------|------------|------|")
        for item in leverage:
            lines.append(f"| {item['tag']} | {item['market_match']} | → **重点放大**，目标顶尖水平 |")
        all_strength_names = set(s.lower() for s in strengths)
        weakness_skills = [g["skill"] for g in gap_data["gap_analysis"]
                          if g["skill"].lower() not in all_strength_names]
        for ws in weakness_skills:
            lines.append(f"| {ws} | 市场要求 | → **够用即可**，目标达市场门槛 |")
        lines.append("")
        lines.append(f"> 根据你的核心优势，计划将重点放大优势技能，短板技能只需达到市场门槛水平。")
        lines.append("")

    # ── 3. 核心学习方法论 ──
    lines.append("## 三、核心学习方法论")
    lines.append("")
    lines.append("本学习计划深度融合两种顶级学习方法——**费曼学习法**和**第一性原理**，")
    lines.append("贯穿每一天的学习。下面说明它们是什么、为什么要用、以及怎么用。")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("### 3.1 费曼学习法：通过教来检验真懂")
    lines.append("")
    lines.append("**核心理念**：如果你不能简单地讲清楚，说明你还没有真正理解。")
    lines.append("")
    lines.append("**为什么有效**：")
    lines.append("- 「教别人」迫使你从「听过/看过」的模糊状态进入「清晰表达」状态")
    lines.append("- 讲不清楚的地方，就是理解盲区，精准暴露问题")
    lines.append("- 要用大白话 + 类比，你必须先建立自己的理解框架，而非复述原文")
    lines.append("")
    lines.append("**在本计划中的用法**：")
    lines.append("")
    lines.append("#### 每日费曼输出（每节课的收尾动作）")
    lines.append("1. 学完知识点 X 后，合上资料")
    lines.append("2. 用最简单的大白话，向一个完全没有技术背景的小白讲清楚 X")
    lines.append("   - ❌ 禁止使用专业术语。如果必须用，先用自己的话定义清楚")
    lines.append("   - ✅ 必须打比方、举例子、画类比")
    lines.append("3. 如果能流畅讲完 → 说明你真的理解了")
    lines.append("4. 如果讲不清楚、卡住了 → 这里就是你的理解盲区")
    lines.append("   - → 标记为「待回炉」，第二天优先复习")
    lines.append("")
    lines.append("#### 每周费曼串联（周末复盘）")
    lines.append("- 把本周所有核心概念用一段连贯的大白话串联")
    lines.append("- 从「用户遇到了什么问题」开始，到「技术是怎么解决的」结束")
    lines.append("- 能流畅讲完 = 本周内容真正消化 / 卡住 = 标记补强")
    lines.append("")
    lines.append("#### 产出建议")
    lines.append("- 录制语音或写文字笔记，作为你的「理解资产」")
    lines.append("- 每次完成费曼输出后，在计划中打勾标记")
    lines.append("- 未通过的（卡住的地方）必须记录原因")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("### 3.2 第一性原理：回归本质的深度思考")
    lines.append("")
    lines.append("**核心理念**：抛开既有结论和类比，回归事物最基本的原理，从本质出发重构理解。")
    lines.append("")
    lines.append("**为什么有效**：")
    lines.append("- 学框架 API 只是「知其然」，追问本质才能「知其所以然」")
    lines.append("- 知道什么时候不用某个技术，比知道怎么用它更重要")
    lines.append("- 能从零设计替代方案，才是最高阶的掌握")
    lines.append("")
    lines.append("**在本计划中的用法**：")
    lines.append("")
    lines.append("#### 阶段里程碑追问（每个阶段末）")
    lines.append("针对本阶段的核心技术，层层追问直至本质：")
    lines.append("1. **问题本质** — 这个技术解决了什么本质问题？")
    lines.append("2. **需求溯源** — 为什么需要它？如果没有它，我们怎么做？")
    lines.append("3. **核心原理** — 抛开所有封装和语法糖，最底层在做什么？")
    lines.append("4. **边界认知** — 它的局限性和边界在哪？什么场景不适用？")
    lines.append("5. **重构思考** — 如果从零开始设计替代方案，你会怎么做？")
    lines.append("")
    lines.append("#### 最终拆解任务（结业冲刺）")
    lines.append("针对学习过程中最核心的技术点，写出完整的拆解文档：")
    lines.append("问题本质 → 核心原理 → 最小实现 → 设计取舍")
    lines.append("")
    lines.append("#### 示例：学 LangChain 时的第一性原理追问")
    lines.append("")
    lines.append("> 不要停留在「会用」层面——追问：")
    lines.append("> LangChain 的本质是什么？—— 一套封装了 Prompt 模板、Chain 串联、")
    lines.append("> Tool 调用、Memory 管理的框架。去掉 LangChain，原生 Python 照样能实现。")
    lines.append("> LangChain 的价值是标准化和减少重复代码，代价是增加了一层抽象和调试难度。")
    lines.append("> 所以学 LangChain 的核心不是学 API，而是学它背后的设计模式。")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"> 根据你选择的 {duration} 天计划，以上方法会以不同深度嵌入每日学习。")

    # ── 4. 详细每日计划 ──
    lines.append("## 四、详细学习计划")
    lines.append("")

    use_continuous = bool(market_skills) and duration >= 30
    simple_mode = (duration <= 30)
    is_market_driven = bool(market_skills)
    selected_phases = []
    covered_skill_names = set()
    plan_structure = None

    if use_continuous:
        plan_structure = build_continuous_plan(market_skills, supp_candidates, duration, profile, gap_data)
        kus = plan_structure["knowledge_units"]

        lines.append("### 学习概览")
        lines.append("")
        lines.append(f"本计划共 {plan_structure['total_days']} 天（日均{_format_hours_display(daily_h)}，"
                     f"每日可在 {_format_hours_display(daily_h*0.75)}~{_format_hours_display(daily_h*1.25)} 之间弹性浮动），"
                     f"含 {len(plan_structure.get('projects', []))} 个实战项目")
        lines.append("")
        lines.append("| 时间段 | 内容 | 类型 | 预计投入 |")
        lines.append("|--------|------|------|---------|")
        for item in plan_structure["learning_overview"]:
            lines.append(f"| {item['day_range']} | {item['title']} | {item['type']} | {item['estimated_hours']}h |")
        lines.append("")

        if plan_structure["projects"]:
            lines.append("### 实战项目清单")
            lines.append("")
            for proj in plan_structure["projects"]:
                dr = f"Day {proj['day_start']}-{proj['day_end']}" if proj['day_start'] != proj['day_end'] else f"Day {proj['day_start']}"
                lines.append(f"- **{proj['title']}**（{dr}，约{proj['total_hours']}h）")
            lines.append("")

        if plan_structure["review_days"]:
            lines.append("### 复盘日计划")
            lines.append("")
            for rd in plan_structure["review_days"]:
                lines.append(f"- Day {rd['day_start']}：{rd['title']}")
            lines.append("")

        last_phase_num = None
        for ku_idx, ku in enumerate(kus):
            merged = ku.get("_merged_days", [])
            n_days = len(merged)
            if n_days == 0:
                continue
            dr = f"Day {ku['day_start']}" if n_days <= 1 else f"Day {ku['day_start']}-{ku['day_end']}"

            unit_type_label = {
                "study": "核心学习", "project": "项目实战", "review": "阶段复盘",
                "supplement": "拓展选修", "os_contribution": "开源贡献",
            }.get(ku["unit_type"], "学习")

            phase_num = ku.get("phase_num")
            if phase_num is not None and last_phase_num is not None and phase_num != last_phase_num:
                lines.append("---")
                lines.append("")
                lines.append(f"**第一性原理追问（{ku.get('phase_name', '')}）**")
                lines.append("")
                if simple_mode:
                    lines.append("思考以下 3 个问题（记录到笔记）：")
                    lines.append("")
                    lines.append("1. 这个技术解决了什么本质问题？")
                    lines.append("2. 它的核心原理是什么？（一句话说清）")
                    lines.append("3. 如果从零设计替代方案，你会怎么做？")
                else:
                    lines.append("回答并记录以下 5 层追问：")
                    lines.append("")
                    lines.append("1. **问题本质**：这个技术解决了什么本质问题？")
                    lines.append("2. **需求溯源**：为什么需要它？没有它行不行？")
                    lines.append("3. **核心原理**：抛开所有封装和语法糖，最底层在做什么？")
                    lines.append("4. **边界认知**：它的局限性和边界在哪？什么场景不适用？")
                    lines.append("5. **重构思考**：如果从零开始设计替代方案，你会怎么做？")
                    if duration > 60:
                        lines.append("")
                        lines.append("（90天版额外要求：画出原理推导图）")
                lines.append("")

            lines.append(f"### 《{unit_type_label}》{ku['title']}（{dr}）")
            lines.append("")

            if ku["unit_type"] in ("study", "supplement"):
                ann = _get_market_annotation(ku.get("theme", ""), market_skills, week_theme=ku.get("theme"))
                if ann:
                    lines.append(f"> 此单元对应市场「{ann['source_label']}」— {ann['name']}（提及率 {ann['mention_rate']}%）")
                    lines.append("")
                    covered_skill_names.add(ann["name"])

            if ku.get("goal"):
                lines.append(f"**目标**：{ku['goal']}")
                lines.append("")

            if "_merged_days" in ku:
                for day_idx, cal_day in enumerate(ku["_merged_days"]):
                    abs_day = ku["day_start"] + day_idx
                    total_dur = cal_day["scaled_hours"] + cal_day.get("filler_hours", 0)
                    topics_str = " + ".join(cal_day["topics"][:2])
                    if len(cal_day["topics"]) > 2:
                        topics_str += f" + ...（共{len(cal_day['topics'])}个知识点）"

                    tags_str = " ".join(cal_day.get("tags", []))
                    n_topics = len(cal_day["topics"])
                    topic_label = f"（{n_topics}个知识模块）" if n_topics >= 2 else ""

                    lines.append("---")
                    lines.append("")
                    header = f"##### Day {abs_day}：{topics_str} {tags_str} {topic_label}".strip()
                    lines.append(header)
                    lines.append("")
                    lines.append(f"- **今日学习时长**：{_format_hours_display(total_dur)}（平均值：{_format_hours_display(daily_h)}，弹性范围：{_format_hours_display(daily_h*0.75)}~{_format_hours_display(daily_h*1.25)}）")
                    lines.append("- **时间分配**：")
                    for blk in cal_day["blocks"]:
                        lines.append(f"  - [{blk['type']}] {blk['topic']}（{_format_hours_display(blk['hours'])}）")
                    if cal_day.get("filler_hours", 0) > 0.3:
                        lines.append(f"  - [灵活] 剩余时间自主安排（{_format_hours_display(cal_day['filler_hours'])}）")
                    lines.append("")

                    for t, tp in zip(cal_day["topics"], cal_day["practice_tasks"]):
                        if tp:
                            lines.append(f"- **实践任务**：{tp}")
                    lines.append("")

                    lines.append("**费曼输出任务**")
                    lines.append("")
                    for t, h in zip(cal_day["topics"], cal_day["feynman_hints"]):
                        lines.append(f"用大白话向小白讲清楚「{t}」")
                        if h:
                            lines.append(f"- 提示启发：{h}")
                        lines.append("- 禁止使用专业术语，必须打比方/举例子")
                        lines.append("- 卡住的地方 = 盲区，标记为「待回炉」")
                        lines.append("")

                    filtered_tags = [t for t in cal_day.get("tags", []) if "复盘整理" not in t and "实战项目" not in t]
                    if filtered_tags:
                        lines.append(f"**{' '.join(filtered_tags)}**")
                        lines.append("")

                    lines.append("**今日检验**")
                    lines.append("")
                    for t, tp in zip(cal_day["topics"], cal_day["practice_tasks"]):
                        if tp:
                            lines.append(f"- [ ] 实践任务完成：{tp}")
                    for t in cal_day["topics"]:
                        lines.append(f"- [ ] 费曼输出完成：能流畅讲清 {t}")
                    lines.append("")


                    if sd_flag == "daily_checkin":
                        lines.append("**今日签到**")
                        lines.append("")
                        lines.append("- [ ] 今日任务全部完成")
                        lines.append("- [ ] 费曼输出已记录")
                        lines.append("- [ ] 理解盲区已标记")
                        lines.append("")
                    if sd_flag == "challenge_task" and any(p for p in cal_day["practice_tasks"]) and not any(t in ("review", "os_contribution") for t in cal_day.get("item_types", [])):
                        lines.append("**挑战任务（提速可选）**")
                        lines.append("")
                        topic = cal_day["topics"][0] if cal_day["topics"] else ""
                        ptask = next((p for p in cal_day["practice_tasks"] if p), "")
                        if topic:
                            lines.append(f"- {topic}：尝试更复杂的实际场景应用或与已学知识结合")
                        if ptask:
                            lines.append(f"- 在「{ptask}」的基础上，增加异常处理/性能优化/边界测试")
                        lines.append("")
            else:
                for i, (day_name, topic, feynman, check, dur) in enumerate(ku["days"], 1):
                    if _parse_hours_float(dur) < 0.01:
                        continue
                    abs_day = ku["day_start"] + i - 1
                    sdur = (ku.get("_scaled_dur_list") or [dur] * len(ku["days"]))[i-1]
                    scaled_hours = _parse_hours_float(sdur)

                    lines.append("---")
                    lines.append("")
                    lines.append(f"##### Day {abs_day}：{topic}")
                    lines.append("")
                    lines.append(f"- **今日总学习时长**：{_format_hours_display(scaled_hours)}")
                    lines.append("- **时间分配**：")
                    core_h = round(scaled_hours * 0.50, 1)
                    practice_h = round(scaled_hours * 0.25, 1) if check else 0
                    feynman_h = round(max(0.3, scaled_hours * 0.15), 1)
                    check_h = round(max(0.2, scaled_hours * 0.10), 1)
                    lines.append(f"  - [核心] {topic}（{_format_hours_display(core_h)}）")
                    if check:
                        lines.append(f"  - [实践] {check}（{_format_hours_display(practice_h)}）")
                    lines.append(f"  - [费曼] 大白话讲清「{topic}」（{_format_hours_display(feynman_h)}）")
                    lines.append(f"  - [检验] 自测题+代码复现（{_format_hours_display(check_h)}）")
                    remaining = round(scaled_hours - core_h - practice_h - feynman_h - check_h, 1)
                    if remaining > 0.3:
                        lines.append(f"  - [拓展] 自主拓展与深化（{_format_hours_display(remaining)}）")
                    lines.append("")

                    if simple_mode:
                        lines.append("**费曼输出任务（今日核心）**")
                        lines.append("")
                        lines.append(f"用大白话向小白讲清楚「{topic}」")
                        lines.append(f"- 提示：{feynman}")
                        lines.append("- 卡住的地方 = 盲区，标记为「待回炉」")
                    else:
                        lines.append("**费曼输出任务（今日核心）**")
                        lines.append("")
                        lines.append(f"用大白话向小白讲清楚「{topic}」")
                        lines.append(f"- 提示启发：{feynman}")
                        lines.append("- 禁止使用专业术语，必须打比方/举例子")
                        lines.append("- 卡住的地方 = 盲区，标记为「待回炉」")
                    lines.append("")

                    lines.append("**今日检验**")
                    lines.append("")
                    if check:
                        lines.append(f"- [ ] 实践任务完成：{check}")
                    lines.append(f"- [ ] 费曼输出完成：能流畅讲清 {topic}")
                    lines.append("")

                    if simple_mode:
                        lines.append(f"- **今日产出**：费曼笔记（3-5句话录音或文字）")
                    elif duration > 60:
                        out = f"费曼笔记（300字以上白话解释）"
                        if check:
                            out = f"{check} 实现代码 + " + out
                        lines.append(f"- **今日产出**：{out}")
                    else:
                        out = "费曼笔记（完整白话解释）"
                        if check:
                            out = f"{check} 实现代码 + " + out
                        lines.append(f"- **今日产出**：{out}")
                    lines.append("")

                    if sd_flag == "daily_checkin":
                        lines.append("**今日签到**")
                        lines.append("")
                        lines.append("- [ ] 今日任务全部完成")
                        lines.append("- [ ] 费曼输出已记录")
                        lines.append("- [ ] 理解盲区已标记")
                        lines.append("")
                    if sd_flag == "challenge_task" and check:
                        lines.append("**挑战任务（提速可选）**")
                        lines.append("")
                        lines.append(f"- 进阶：{check} 的基础上，尝试优化/扩展功能")
                        lines.append("- 如已完成当日任务且有余力，建议挑战")
                        lines.append("")

            if ku_idx + 1 < len(kus):
                next_ku = kus[ku_idx + 1]
                if next_ku["unit_type"] == "study" and next_ku.get("theme") and ku.get("theme") and ku["theme"] != next_ku["theme"]:
                    lines.append("---")
                    lines.append("")
                    lines.append(f"**→ 下一单元**：完成「{ku['theme']}」后，进入「{next_ku['theme']}」")
                    lines.append("")
                elif next_ku["unit_type"] == "project":
                    lines.append("---")
                    lines.append("")
                    lines.append(f"**→ 下一单元**：进入实战项目阶段")
                    lines.append("")
                elif next_ku["unit_type"] == "review":
                    lines.append("---")
                    lines.append("")
                    lines.append(f"**→ 下一单元**：阶段复盘日")
                    lines.append("")

            last_phase_num = phase_num

        to_learn_set = set(ms["name"] for ms in market_skills if not ms["user_has"])
        covered_market = covered_skill_names & to_learn_set
        if covered_market:
            essential_set = set(ms["name"] for ms in market_skills if not ms["user_has"] and ms.get("source") == "essential")
            lines.append("---")
            lines.append("")
            lines.append("### 市场技能覆盖进度")
            lines.append("")
            lines.append(f"> 已完成市场要求技能 [ {len(covered_market)}/{len(to_learn_set)} ] "
                         f"（必备技能覆盖 {len(covered_market & essential_set)}/{len(essential_set)}）")
            lines.append("")

        selected_phases = _phases_from_kus(kus)

    else:
        if market_skills:
            selected_phases = build_market_driven_plan(market_skills, supp_candidates, duration, profile, gap_data, title)
        else:
            # 无市场数据时使用最小占位
            selected_phases = [{
                "phase": 1, "phase_name": "基础学习",
                "weeks": [{"week": 1, "theme": "技能学习", "goal": title,
                           "days": [("Day 1", "开始学习", "", "规划学习路线", "1h")]}],
                "phase_checklist": [],
            }]

        for phase_data in selected_phases:
            phase_num = phase_data["phase"]
            phase_name = phase_data["phase_name"]
            weeks = phase_data["weeks"]

            first_wk = weeks[0]["week"]
            last_wk = weeks[-1]["week"]
            lines.append(f"---")
            lines.append(f"")
            lines.append(f"## 阶段 {phase_num}：{phase_name}（第 {first_wk}-{last_wk} 周）")
            lines.append("")

            for w in weeks:
                if w.get("_is_supplement"):
                    label = w.get("_supplement_label", "补充")
                    supp_hours = w.get("_supplement_hours", 0)
                    total_h = max(gap_data.get("total_available_hours", 1), 1)
                    supp_pct = supp_hours / total_h * 100
                    lines.append(f"#### 第 {w['week']} 周（补充）：{label} {w['theme']}")
                    lines.append("")
                    lines.append(f"> 补充内容占比 {supp_pct:.0f}%（{supp_hours}h / {total_h:.0f}h），未超过 10% 上限")
                else:
                    lines.append(f"#### 第 {w['week']} 周：{w['theme']}")
                lines.append("")
                lines.append(f"**周目标**：{w['goal']}")
                lines.append("")

                for i, (day_name, topic, feynman, check, dur) in enumerate(w["days"], 1):
                    lines.append("---")
                    lines.append("")
                    lines.append(f"##### 第 {i} 天：{topic}")
                    lines.append("")
                    scaled_dur = _parse_hours_float(dur) * time_coeff
                    lines.append(f"- **今日总学习时长**：{_format_hours_display(scaled_dur)}")
                    lines.append("- **时间分配**：")
                    core_h = round(scaled_dur * 0.50, 1)
                    practice_h = round(scaled_dur * 0.25, 1) if check else 0
                    feynman_h = round(max(0.3, scaled_dur * 0.15), 1)
                    lines.append(f"  - [核心] {topic}（{_format_hours_display(core_h)}）")
                    if check:
                        lines.append(f"  - [实践] {check}（{_format_hours_display(practice_h)}）")
                    lines.append(f"  - [费曼] 大白话讲清「{topic}」（{_format_hours_display(feynman_h)}）")
                    lines.append(f"- **学习内容**：{topic}")
                    if check:
                        lines.append(f"- **实践任务**：{check}")
                    lines.append("")

                    if simple_mode:
                        lines.append("**费曼输出任务（今日核心）**")
                        lines.append("")
                        lines.append(f"用大白话向小白讲清楚「{topic}」")
                        lines.append(f"- 提示：{feynman}")
                        lines.append("- 卡住的地方 = 盲区，标记为「待回炉」")
                    else:
                        lines.append("**费曼输出任务（今日核心）**")
                        lines.append("")
                        lines.append(f"用大白话向小白讲清楚「{topic}」")
                        lines.append(f"- 提示启发：{feynman}")
                        lines.append("- 禁止使用专业术语，必须打比方/举例子")
                        lines.append("- 卡住的地方 = 盲区，标记为「待回炉」")
                    lines.append("")

                    lines.append("**今日检验**")
                    lines.append("")
                    if check:
                        lines.append(f"- [ ] 实践任务完成：{check}")
                    lines.append(f"- [ ] 费曼输出完成：能流畅讲清 {topic}")
                    lines.append("")

                    if is_market_driven:
                        ann = _get_market_annotation(topic, market_skills, week_theme=w["theme"])
                        if ann:
                            lines.append(f"> 此部分对应报告中「{ann['source_label']}TOP: {ann['name']}（提及率 {ann['mention_rate']}%）")
                            lines.append("")
                        if ann:
                            covered_skill_names.add(ann["name"])

                    if simple_mode:
                        lines.append(f"- **今日产出**：费曼笔记（3-5句话录音或文字）")
                    elif duration > 60:
                        out = f"费曼笔记（300字以上白话解释）"
                        if check:
                            out = f"{check} 实现代码 + " + out
                        lines.append(f"- **今日产出**：{out}")
                    else:
                        out = "费曼笔记（完整白话解释）"
                        if check:
                            out = f"{check} 实现代码 + " + out
                        lines.append(f"- **今日产出**：{out}")
                    lines.append("")

                    if sd_flag == "daily_checkin":
                        lines.append("**今日签到**")
                        lines.append("")
                        lines.append("- [ ] 今日任务全部完成")
                        lines.append("- [ ] 费曼输出已记录")
                        lines.append("- [ ] 理解盲区已标记")
                        lines.append("")
                    if sd_flag == "challenge_task" and check:
                        lines.append("**挑战任务（提速可选）**")
                        lines.append("")
                        lines.append(f"- 进阶：{check} 的基础上，尝试优化/扩展功能")
                        lines.append("- 如已完成当日任务且有余力，建议挑战")
                        lines.append("")

                if simple_mode:
                    lines.append("---")
                    lines.append("")
                    lines.append("**本周费曼串联（简化）**")
                    lines.append("")
                    lines.append("花 5 分钟口头串联本周概念，卡住的地方 = 下次复习重点。")
                    lines.append("")
                else:
                    week_topics = "、".join(t for _, t, _, _, _ in w["days"] if t)
                    lines.append("---")
                    lines.append("")
                    lines.append("**本周费曼串联任务**")
                    lines.append("")
                    lines.append(f"将本周学的概念（{week_topics}）用大白话串联成一个完整的技术故事，")
                    lines.append("从用户需求开始到技术实现结束。")
                    lines.append("")
                    lines.append("- 能流畅讲完 → 本周内容真正消化")
                    lines.append("- 讲着讲着卡住 → 该部分理解不足，标记并补强")
                    if duration > 60:
                        lines.append("- （90天版额外要求：以写作形式输出，300字以上，同步作为内容素材）")
                    lines.append("")

                if is_market_driven and covered_skill_names:
                    total_market_count = len([ms for ms in market_skills if not ms.get("user_has")])
                    match_count = len(covered_skill_names)
                    if total_market_count > 0:
                        match_pct = match_count / total_market_count * 100
                        lines.append(f"> **本周技能与市场匹配度**：已完成市场要求技能的 [{match_count}/{total_market_count}]（约 {match_pct:.0f}%）")
                        lines.append("")

                if sd_flag == "daily_checkin":
                    lines.append("---")
                    lines.append("")
                    lines.append("**本周进度自我诊断（自驱力强化）**")
                    lines.append("")
                    lines.append("| 检查项 | 完成情况 |")
                    lines.append("|--------|---------|")
                    lines.append("| 本周所有任务完成？ | [ ] 是 [ ] 否 — 未完成请周日补上 |")
                    lines.append("| 费曼输出全部记录？ | [ ] 是 [ ] 否 |")
                    lines.append("| 理解盲区已标记？ | [ ] 是 [ ] 否 |")
                    lines.append("| 是否跟上计划进度？ | [ ] 是 [ ] 否 — 落后超过2天建议重新评估 |")
                    lines.append("")
                    lines.append("> ⚠️ 如果本周任务未完成，请在周日补完，否则建议重新评估自驱力等级。")
                    lines.append("")

            lines.append("### 阶段自查清单")
            lines.append("")
            if simple_mode:
                for item in phase_data["phase_checklist"][:3]:
                    lines.append(f"- [ ] {item}")
            else:
                for item in phase_data["phase_checklist"]:
                    lines.append(f"- [ ] {item}")
            lines.append("")

            if simple_mode:
                lines.append("---")
                lines.append("")
                lines.append(f"**阶段 {phase_num} 第一性原理追问（简化版）**")
                lines.append("")
                lines.append("针对本阶段核心技术，思考以下 3 个问题（记录到笔记）：")
                lines.append("")
                lines.append("1. 这个技术解决了什么本质问题？")
                lines.append("2. 它的核心原理是什么？（一句话说清）")
                lines.append("3. 如果从零设计替代方案，你会怎么做？")
                lines.append("")
            else:
                lines.append("---")
                lines.append("")
                lines.append(f"**阶段 {phase_num} 第一性原理追问**")
                lines.append("")
                lines.append("针对本阶段核心技术，回答并记录以下 5 层追问：")
                lines.append("")
                lines.append("1. **问题本质**：这个技术解决了什么本质问题？")
                lines.append("2. **需求溯源**：为什么需要它？没有它行不行？")
                lines.append("3. **核心原理**：抛开所有封装和语法糖，最底层在做什么？")
                lines.append("4. **边界认知**：它的局限性和边界在哪？什么场景不适用？")
                lines.append("5. **重构思考**：如果从零开始设计替代方案，你会怎么做？")
                if duration > 60:
                    lines.append("")
                    lines.append("（90天版额外要求：画出原理推导图）")
                lines.append("")

                if sd_flag == "challenge_task":
                    lines.append("> 💡 如果您已经熟练掌握本阶段内容，可跳过本模块，直接进入下一阶段。")
                    lines.append("")
                elif sd_flag == "milestone_reminder":
                    lines.append("> 💡 建议加入学习社群或找学习伙伴互相督促，提升学习效果。")
                    lines.append("")

    if not is_market_driven and not use_continuous:
        ew = PROJECT_WEEK["extra_week"]
        lines.append(f"#### 第 {ew['week']} 周（附加）：{ew['theme']}")
        lines.append("")
        lines.append(f"**周目标**：{ew['goal']}")
        lines.append("")
        for i, (day_name, topic, feynman, check, dur) in enumerate(ew["days"], 1):
            lines.append("---")
            lines.append("")
            lines.append(f"##### 第 {i} 天：{topic}")
            lines.append("")
            scaled_dur_pw = _parse_hours_float(dur) * time_coeff
            lines.append(f"- **今日总学习时长**：{_format_hours_display(scaled_dur_pw)}")
            lines.append("- **时间分配**：")
            lines.append(f"  - [核心] {topic}（{_format_hours_display(round(scaled_dur_pw*0.5,1))}）")
            if check:
                lines.append(f"  - [实践] {check}（{_format_hours_display(round(scaled_dur_pw*0.3,1))}）")
            lines.append(f"  - [费曼] 大白话讲清「{topic}」（{_format_hours_display(round(max(0.3,scaled_dur_pw*0.2),1))}）")
            lines.append(f"- **学习内容**：{topic}")
            if check:
                lines.append(f"- **实践任务**：{check}")
            lines.append("")
            lines.append("**费曼输出任务（今日核心）**")
            lines.append("")
            lines.append(f"用大白话向小白讲清楚「{topic}」")
            lines.append(f"- 提示启发：{feynman}")
            if not simple_mode:
                lines.append("- 禁止使用专业术语，必须打比方/举例子")
            lines.append("- 卡住的地方 = 盲区，标记为「待回炉」")
            lines.append("")
            lines.append("**今日检验**")
            lines.append("")
            if check:
                lines.append(f"- [ ] 实践任务完成：{check}")
            lines.append(f"- [ ] 费曼输出完成：能流畅讲清 {topic}")
            lines.append("")
            out = "费曼笔记"
            if check:
                out = f"{check} 实现代码 + " + out
            lines.append(f"- **今日产出**：{out}")
            lines.append("")

    lines.append("## 五、项目实战建议")
    lines.append("")
    lines.append("| 项目 | 难度 | 涉及技能 | 说明 |")
    lines.append("|------|------|----------|------|")
    projects = [
        ("AI 知识库问答助手", "入门", "LangChain / RAG / Prompt", "基于 RAG 的个人知识库问答系统"),
        ("多Agent 调研助手", "进阶", "LangGraph / Multi-Agent", "多个 Agent 协作完成搜索→分析→总结→报告"),
        ("AI 编程助手", "进阶", "Agent / LLM / Tool Use", "类似 Claude Code 的 AI 编程助手"),
        ("智能客服系统", "高阶", "RAG / 对话系统 / Agent", "结合 RAG 和 Agent 的智能客服"),
    ]
    for name, diff, skills, desc in projects:
        lines.append(f"| **{name}** | {diff} | {skills} | {desc} |")
    lines.append("")

    lines.append("## 六、总时间线与关键建议")
    lines.append("")
    total_days_actual = plan_structure["total_days"] if use_continuous and plan_structure else duration
    lines.append(f"- **总时长**：约 {total_days_actual} 天" + ("（含综合项目周）" if not use_continuous else "（含实战项目与复盘日）"))
    lines.append(f"- **每日投入**：{p.get('daily_hours', '3-4h')}")
    if use_continuous and plan_structure:
        plan_projects = plan_structure.get("projects", [])
        if len(plan_projects) >= 1:
            p1 = plan_projects[0]
            lines.append(f"- **里程碑 1**（Day {p1['day_start']}）：{p1['title']}")
        if len(plan_projects) >= 2:
            p2 = plan_projects[1]
            lines.append(f"- **里程碑 2**（Day {p2['day_start']}）：{p2['title']}")
        if len(plan_projects) >= 3:
            p3 = plan_projects[2]
            lines.append(f"- **里程碑 3**（Day {p3['day_start']}）：{p3['title']}")
    elif duration <= 30:
        lines.append("- **里程碑 1**（第 4 周）：完成 RAG 知识库问答系统")
        lines.append("- **里程碑 2**（第 5 周）：作品集就绪，可投实习")
    elif duration <= 60:
        lines.append("- **里程碑 1**（第 4-5 周）：完成 RAG 知识库问答系统")
        lines.append("- **里程碑 2**（第 8-9 周）：完成多Agent 协作项目")
        lines.append("- **里程碑 3**（第 9 周）：作品集就绪，可投实习")
    else:
        lines.append("- **里程碑 1**（第 4-5 周）：完成 RAG 知识库问答系统")
        lines.append("- **里程碑 2**（第 8-9 周）：完成多Agent 协作项目")
        lines.append("- **里程碑 3**（第 12 周）：作品集就绪，可投实习")
    lines.append("")
    lines.append("### 每日学习流程建议")
    lines.append("")
    lines.append("1. **复习（15min）** — 回顾昨天费曼笔记，检查「待回炉」标记")
    lines.append("2. **学习新内容（1-2h）** — 阅读/看教程，理解核心概念")
    lines.append("3. **实践任务（1h）** — 动手实现，在代码中验证理解")
    lines.append("4. **费曼输出（核心环节，20min）** — 用大白话讲给小白听，录制或写下来")
    lines.append("5. **自查与标记（10min）** — 完成检验清单，标记盲区为「待回炉」")
    lines.append("")

    lines.append("## 七、最终综合大检验：第一性原理拆解")
    lines.append("")
    lines.append("> 这是本学习计划的终极考核。能拆解清楚，才算真正掌握。")
    lines.append("")
    lines.append("要求针对核心技术点，分别写出第一性原理拆解文档。每个文档包含：")
    lines.append("**问题本质 → 核心原理 → 最小实现 → 设计取舍**。")
    lines.append("")
    if simple_mode:
        lines.append("- [ ] **RAG（检索增强生成）** — 第一性原理拆解文档")
    elif duration <= 60:
        lines.append("- [ ] **RAG（检索增强生成）** — 第一性原理拆解文档")
        lines.append("- [ ] **Agent（智能体）** — 第一性原理拆解文档")
    else:
        lines.append("- [ ] **RAG（检索增强生成）** — 第一性原理拆解文档")
        lines.append("- [ ] **Agent（智能体）** — 第一性原理拆解文档")
        lines.append("- [ ] **Prompt Engineering（提示工程）** — 第一性原理拆解文档")
        lines.append("")
        lines.append("> 90天版额外要求：包含推导过程、完整代码实现、设计权衡分析。")
    lines.append("")
    lines.append("### 拆解文档模板")
    lines.append("")
    lines.append("| 部分 | 内容要求 |")
    lines.append("|------|---------|")
    lines.append("| **问题本质** | 这个技术解决了什么本质问题？100字以内 |")
    lines.append("| **核心原理** | 一句话说清最底层原理（抛开所有框架封装） |")
    lines.append("| **最小实现** | 不依赖任何框架，用最简代码实现核心逻辑 |")
    lines.append("| **设计取舍** | 为什么这样设计？有哪些权衡？什么场景不适用？ |")
    lines.append("")
    lines.append("拆解文档的质量将作为结业考核的重要标准之一。")
    lines.append("")

    if market_skills:
        lines.append("---")
        lines.append("")
        lines.append("## 技能与市场对照总表")
        lines.append("")
        lines.append("| 技能 | 市场提及率 | 优先级 | 来源 |")
        lines.append("|------|-----------|--------|------|")
        for ms in market_skills:
            source = "必备技能TOP榜" if ms.get("source") == "essential" else "加分技能TOP榜"
            priority = "核心必修" if ms.get("source") == "essential" else "加分必修"
            lines.append(f"| {ms['name']} | {ms.get('mention_rate', 0):.1f}% | {priority} | {source} |")
        for supp in supp_candidates:
            lines.append(f"| {supp['name']} | - | 拓展选修 | {supp.get('label', '补充')} |")
        lines.append("")
        n_learned = sum(1 for ms in market_skills if ms.get("user_has"))
        n_total = len(market_skills)
        lines.append(f"> 市场技能覆盖：已掌握 {n_learned}/{n_total}，待学习 {n_total - n_learned} 项")
        lines.append("")

    if supp_explanations:
        lines.append("---")
        lines.append("")
        lines.append("## 补充模块说明")
        lines.append("")
        lines.append("以下为根据你个人画像和市场趋势筛选的拓展模块，非强制学习：")
        lines.append("")
        lines.append("| 模块 | 类型 | 纳入原因 | 建议投入 | 替代方案 |")
        lines.append("|------|------|---------|---------|---------|")
        for se in supp_explanations:
            lines.append(f"| {se['name']} | {se['label']} | {se['reason']} | {se['hours']}h | 时间紧张可跳过 |")
        lines.append("")
        lines.append("> 这些模块旨在拓宽技术视野和增强竞争力，如果时间紧张建议优先完成核心内容。")
        lines.append("")

    if business:
        lines.append("---")
        lines.append("")
        lines.append("## 八、商业赋能：技术内容创作与技能变现")
        lines.append("")
        lines.append("> 以下内容基于你的学习计划中的具体技术栈生成，学什么就输出什么、变现什么。")
        lines.append("> 流量和兼职属于锦上添花，不会挤占核心技能学习时间。")
        lines.append("")

        lines.append("### 与费曼输出的联动（内容素材自动生成）")
        lines.append("")
        lines.append("每天产出的费曼输出和第一性原理记录，可直接作为内容创作素材：")
        lines.append("")
        lines.append("| 素材类型 | 加工方向 |")
        lines.append("|----------|---------|")
        lines.append("| 大白话解释（每日费曼输出） | 小红书图文笔记 / 知乎回答 |")
        lines.append("| 打比方/举例子 | 抖音/B站短视频脚本 |")
        lines.append("| 完整技术故事串联（周串联） | 博客系列文章 |")
        lines.append("| 第一性原理追问记录 | 掘金深度文章 / B站原理讲解视频 |")
        lines.append("")
        lines.append("> 这意味着：每天的费曼产出就是未来的内容作品，无需额外构思选题。")
        lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("### 技术内容创作与个人品牌建设")
        lines.append("")
        lines.append("每学完一项技术，下一周就输出对应的技术内容到适配平台：")
        lines.append("")

        calendar = build_content_calendar(selected_phases, simple_mode, duration, profile=p)
        platforms, primary_platforms = recommend_platforms(p, simple_mode, duration)

        lines.append(f"**推荐主攻平台**：{'、'.join(primary_platforms)}")
        if simple_mode or duration <= 30:
            lines.append(f"（30天版建议集中精力做{len(platforms)}个平台，确保内容深度）")
        lines.append("")

        if not simple_mode:
            lines.append("| 平台 | 内容调性 |")
            lines.append("|------|---------|")
            for pl in platforms:
                lines.append(f"| **{pl}** | {PLATFORM_INFO[pl]} |")
            lines.append("")

        pf_headers = " | ".join(f"**{p}**" for p in platforms)
        lines.append(f"| 输出周 | 学习主题 | {pf_headers} |")
        sep = "|--------|---------" + "".join(f"|{'-'*8}" for _ in platforms)
        lines.append(sep)

        for c in calendar:
            if "platforms" in c:
                cells = " | ".join(c["platforms"].get(p, "") for p in platforms)
            else:
                cells = " | ".join([""] * len(platforms))
            lines.append(f"| 第{c['output_week']}周 | {c['title']} | {cells} |")
        lines.append("")

        lines.append("**平台说明：**")
        tag_source = p.get("strength_tags", []) or p.get("advantage_tags", [])
        lines.append(f"- 根据你的个人优势标签（{'、'.join(tag_source)}），建议主攻：{'、'.join(primary_platforms)}")
        lines.append("- 每个平台的内容标题已根据其调性定制，确保风格匹配")
        lines.append("- 每日费曼产出可直接加工为对应平台的内容素材")
        if simple_mode:
            lines.append(f"- {len(platforms)}个平台足以建立早期影响力，后续可拓展到更多平台")
        lines.append("")

        if not simple_mode:
            lines.append("**附加建议：**")
            lines.append("- 将完成的学习项目开源，作为 GitHub 作品集展示")
            if duration > 60:
                lines.append("- 将核心项目打包为开源工具，提升技术影响力")
                lines.append("- 将费曼输出系列化，形成系统教程，可发布到知识星球/小鹅通")
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("### 技能变现与副业路径")
        lines.append("")
        lines.append("根据你的技能组合，匹配以下变现路径：")
        lines.append("")

        monetization = build_monetization_plan(selected_phases, simple_mode, duration)
        for m in monetization:
            lines.append(f"- **{m['title']}**")
            lines.append(f"  - 接单渠道：{m['channels']}")
            lines.append(f"  - 参考报价：{m['price']}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*计划由 ai-job-hunter 根据个人画像与 BOSS直聘招聘数据自动生成*")
    lines.append("*学习策略：费曼学习法（通过教来检验真懂）+ 第一性原理（回归本质的深度思考）*")

    return "\n".join(lines)


# ══════════════════════════════════════════════
# CLI 入口
# ══════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="能力差距分析与学习计划生成")
    parser.add_argument("--profile", default="profile.json", help="用户画像文件路径")
    parser.add_argument("--report", required=True, help="JD 分析报告 Markdown 路径")
    parser.add_argument("--title", default="", help="岗位名称（默认从报告文件名推断）")
    parser.add_argument("--output", default="", help="输出路径（默认自动生成）")
    parser.add_argument("--duration", type=int, default=60, choices=[30, 60, 90], help="学习周期天数")
    parser.add_argument("--business", default="n", choices=["y", "n"], help="是否包含商业模块")
    parser.add_argument("--commitment", default="", help="坚持周期（如 '3个月'、'不设限'）")
    parser.add_argument("--preview", action="store_true", help="预览模式：打印配置摘要JSON后退出")
    parser.add_argument("--content-pack", default="", help="自定义内容包目录路径（YAML 文件）")
    parser.add_argument("--data-dir", default="", help="数据目录（默认从 AI_JOB_HUNTER_DATA 环境变量读取）")
    args = parser.parse_args()

    data_dir = args.data_dir or os.environ.get("AI_JOB_HUNTER_DATA", "")

    if args.content_pack:
        os.environ["CONTENT_PACK_DIR"] = args.content_pack

    profile = load_profile(args.profile)
    report_data = load_report(args.report)

    title = args.title
    if not title:
        basename = os.path.basename(args.report)
        title = basename.replace("_JD_Analysis_Report.md", "").strip()

    gap_data = analyze_gap(profile, report_data, duration=args.duration)

    gap_data["title"] = title

    if args.preview:
        preview = generate_preview_json(profile, report_data, gap_data, title, args.duration, args.business)
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        return

    print(json.dumps({"step": "profile", "message": "正在读取用户画像..."}, ensure_ascii=False))
    print(json.dumps({"step": "report", "message": "正在读取 JD 分析报告..."}, ensure_ascii=False))
    print(json.dumps({"step": "gap", "message": "正在进行差距分析..."}, ensure_ascii=False))
    print(json.dumps({"step": "gap_done", "has": len(gap_data["has_skills"]),
                       "missing": len(gap_data["missing_skills"])}, ensure_ascii=False))
    print(json.dumps({"step": "plan", "message": "正在生成详细学习计划..."}, ensure_ascii=False))
    commitment = args.commitment or profile.get("profile", {}).get("commitment_period", "")
    plan = generate_daily_plan(profile, gap_data, title, duration=args.duration,
                               business=(args.business == "y"), commitment_period=commitment,
                               report_data=report_data)

    suffix = f"_{args.duration}days_定制版"
    if args.business == "y":
        suffix += "_with_business"
    if data_dir:
        output = args.output or os.path.join(data_dir, f"subjects/{title}/Learning_Plan{suffix}.md")
    else:
        output = args.output or f"subjects/{title}/Learning_Plan{suffix}.md"

    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        f.write(plan)

    print(json.dumps({"step": "done", "message": f"学习计划已生成: {output}", "output": output},
                     ensure_ascii=False))

    print(f"\n{'='*60}", file=sys.stderr)
    print(f"  {title} — 能力差距分析与学习计划", file=sys.stderr)
    print(f"  已掌握: {len(gap_data['has_skills'])} 项", file=sys.stderr)
    print(f"  待补充: {len(gap_data['missing_skills'])} 项", file=sys.stderr)
    print(f"  学习周期: 约{args.duration}天", file=sys.stderr)
    print(f"  输出文件: {output}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)


if __name__ == "__main__":
    main()
