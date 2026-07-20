"""学习计划构建器：连续知识单元，弹性编排 + 均匀穿插"""

from analysis.skill_map import (
    resolve_skill_to_theme, WEEK_PHASE_MAP, THEME_PREREQUISITES, PROJECT_SCALE,
    SUPPLEMENT_POOL,
)
from analysis.content_generator import generate_plan_content
from analysis.gap_analyzer.core import _merge_into_calendar_days, _generate_filler_blocks
from utils.time import _parse_hours_float, _parse_hours, _compute_time_coefficient, get_day_target

# 开源实践：递进式任务（按序循环使用）
_OS_DAYS = [
    ("代码整理与文档化", "把项目代码和文档整理干净，开源的第一步",
     "清理代码 → 加函数注释 → 整理文件结构 → 添加 .gitignore", "2.5h"),
    ("README 编写与开源发布", "好 README 是项目的脸面，决定别人是否会继续看你的代码",
     "写 README（背景/架构/用法）→ 选 LICENSE → 创建 GitHub 仓库并推送", "2.5h"),
    ("技术文章写作", "写一篇技术文章介绍项目，让更多人了解你的工作",
     "撰写技术文章 → 配截图/架构图 → 发布到掘金/知乎/博客", "2.5h"),
    ("项目展示优化", "优化项目展示页，添加徽章和演示截图",
     "添加项目徽章 → 补充演示截图/GIF → 配置项目主页或 GitHub Pages", "2.5h"),
    ("社区分享与维护", "将项目分享到开发者社区，收集反馈持续改进",
     "分享到 V2EX/Reddit/HackerNews → 收集 issue → 规划下个版本", "2.5h"),
]


# ══════════════════════════════════════════════
# 工具函数
# ══════════════════════════════════════════════

def determine_skill_depth(mention_rate, priority):
    """根据提及率和优先级决定技能学习深度。

    L3: 深入掌握 (6-8h)，含项目实践
    L2: 核心掌握 (3-5h)，含实践任务
    L1: 概念了解 (1-2h)，概述为主
    """
    if mention_rate >= 60 and priority in ("必修", "核心"):
        return "L3"
    if mention_rate >= 30 or priority in ("必修",):
        return "L2"
    return "L1"


def _get_prerequisites_for_theme(theme):
    if theme in THEME_PREREQUISITES:
        return THEME_PREREQUISITES[theme]
    return []


def _resolve_prerequisites(kus):
    """Kahn 算法拓扑排序。"""
    theme_to_index = {}
    for i, ku in enumerate(kus):
        if ku.get("theme"):
            theme_to_index[ku["theme"]] = i

    in_degree = [0] * len(kus)
    adjacency = [[] for _ in range(len(kus))]

    for i, ku in enumerate(kus):
        if not ku.get("theme"):
            continue
        for prereq_theme in _get_prerequisites_for_theme(ku["theme"]):
            if prereq_theme in theme_to_index:
                j = theme_to_index[prereq_theme]
                adjacency[j].append(i)
                in_degree[i] += 1

    queue = [i for i in range(len(kus)) if in_degree[i] == 0]
    queue.sort(key=lambda i: (kus[i].get("phase_num", 2), i))

    sorted_kus = []
    visited = set()
    while queue:
        i = queue.pop(0)
        sorted_kus.append(kus[i])
        visited.add(i)
        for j in adjacency[i]:
            in_degree[j] -= 1
            if in_degree[j] == 0:
                queue.append(j)
        queue.sort(key=lambda i: (kus[i].get("phase_num", 2), i))

    remaining = [kus[i] for i in range(len(kus)) if i not in visited]
    remaining.sort(key=lambda ku: (ku.get("phase_num", 2), kus.index(ku)))
    sorted_kus.extend(remaining)

    return sorted_kus


# ══════════════════════════════════════════════
# 市场驱动周计划（保留，用于非连续模式）
# ══════════════════════════════════════════════

def build_market_driven_plan(market_skills, supplement_candidates, duration, profile, gap_data, title=""):
    to_learn = [ms for ms in market_skills if not ms["user_has"]]
    to_learn.sort(key=lambda x: -x["mention_rate"])

    plan_entries = []
    used_themes = set()
    for ms in to_learn:
        theme = resolve_skill_to_theme(ms["name"])
        if theme and theme not in used_themes:
            plan_entries.append({"theme": theme, "mention_rate": ms["mention_rate"], "source": ms["source"]})
            used_themes.add(theme)

    # 用 LLM 生成每个主题的学习内容
    skills_with_depth = []
    for e in plan_entries:
        ms = next((x for x in market_skills if x.get("name", "").lower() in e["theme"].lower()), None)
        priority = "必修" if e["source"] == "essential" else "加分"
        depth = determine_skill_depth(e["mention_rate"], priority)
        skills_with_depth.append({
            "theme": e["theme"], "depth": depth,
            "mention_rate": e["mention_rate"], "source": e["source"],
        })

    content = generate_plan_content(skills_with_depth, profile)

    # 按阶段分组
    phase_groups = {1: [], 2: [], 3: []}
    for entry in plan_entries:
        ph = WEEK_PHASE_MAP.get(entry["theme"], 2)
        phase_groups[ph].append(entry)

    selected_phases = []
    applied_phase_num = 1
    phase_names = {1: "基础夯实期", 2: "深度专精期", 3: "实战输出期"}

    # 从 content 构建 week_data
    content_theme_map = {t["theme"]: t for t in content.get("themes", [])}

    for ph in sorted(phase_groups.keys()):
        entries = phase_groups[ph]
        if not entries:
            continue
        phase_name = phase_names.get(ph, f"阶段{ph}")

        weeks = []
        week_num = 1
        for entry in entries:
            theme = entry["theme"]
            theme_content = content_theme_map.get(theme)
            if not theme_content:
                continue
            days = []
            for item in theme_content.get("items", []):
                h = item.get("base_hours", 2)
                days.append(("", item["title"], item.get("feynman_hint", ""),
                             item.get("practice_task", ""), f"{h}h"))
            if not days:
                continue
            week_data = {
                "week": week_num, "theme": theme, "goal": theme_content.get("goal", ""),
                "days": days,
                "_market_mention_rate": entry["mention_rate"],
                "_market_source": entry["source"],
            }
            weeks.append(week_data)
            week_num += 1

        if weeks:
            selected_phases.append({
                "phase": applied_phase_num, "phase_name": phase_name,
                "weeks": weeks, "phase_checklist": [],
            })
            applied_phase_num += 1

    active_supplements = []
    for supp in supplement_candidates:
        week_data = {
            "week": supp["week"], "theme": supp["theme"], "goal": supp["goal"],
            "days": supp["days"], "_is_supplement": True,
            "_supplement_label": supp.get("label", ""), "_supplement_hours": supp.get("hours", 0),
        }
        active_supplements.append(week_data)

    if active_supplements:
        if selected_phases:
            s_phase = selected_phases[-1]
            last_week_num = max((w["week"] for w in s_phase["weeks"]), default=0)
            for i, ws in enumerate(active_supplements):
                ws["week"] = last_week_num + i + 1
            s_phase["weeks"].extend(active_supplements)
        else:
            selected_phases.append({
                "phase": 1, "phase_name": "拓展与输出期",
                "weeks": active_supplements, "phase_checklist": [],
            })

    return selected_phases


# ═══════════════════════════════════════════════════════════════
# 新：连续知识单元计划 — 弹性编排 + 均匀穿插
# ═══════════════════════════════════════════════════════════════

def _theme_total_hours(theme, content_theme_map):
    """从 LLM 生成的内容中获取 theme 的总小时数。"""
    tc = content_theme_map.get(theme)
    if tc:
        return sum(it.get("base_hours", 0) for it in tc.get("items", []))
    return 6


def _build_phase_map(themes_in_order):
    """将主题按阶段分组，保留原始顺序。"""
    grouped = {1: [], 2: [], 3: []}
    for t in themes_in_order:
        ph = WEEK_PHASE_MAP.get(t, 2)
        grouped[ph].append(t)
    return grouped


def build_continuous_plan(market_skills, supplement_candidates, duration, profile, gap_data):
    """
    连续知识单元计划 — 弹性编排 + 均匀穿插。
    """
    to_learn = [ms for ms in market_skills if not ms["user_has"]]
    to_learn.sort(key=lambda x: (-x["mention_rate"], 0 if x["source"] == "essential" else 1))

    # 1. 收集主题
    theme_capacity = max(1, int(duration * 0.7 / 5.5))
    essential_only = [ms for ms in to_learn if ms["source"] == "essential"]
    bonus_only = [ms for ms in to_learn if ms["source"] == "bonus"]
    if len(essential_only) >= theme_capacity:
        selected_ms = essential_only[:theme_capacity]
    else:
        remaining = theme_capacity - len(essential_only)
        selected_ms = essential_only + bonus_only[:remaining]

    themes_in_order = []
    theme_map = {}
    for ms in selected_ms:
        theme = resolve_skill_to_theme(ms["name"])
        if theme and theme not in themes_in_order:
            themes_in_order.append(theme)
            theme_map[theme] = ms

    # 2. 用 LLM 生成学习内容
    skills_with_depth = []
    for theme in themes_in_order:
        ms = theme_map[theme]
        depth = determine_skill_depth(ms.get("mention_rate", 0), "必修" if ms["source"] == "essential" else "加分")
        skills_with_depth.append({
            "theme": theme, "depth": depth,
            "mention_rate": ms.get("mention_rate", 0), "source": ms["source"],
        })

    content = generate_plan_content(skills_with_depth, profile)
    content_theme_map = {t["theme"]: t for t in content.get("themes", [])}

    all_study_items = []
    for theme in themes_in_order:
        theme_content = content_theme_map.get(theme)
        if not theme_content:
            continue
        phase_num = WEEK_PHASE_MAP.get(theme, 2)
        phase_name = {1: "基础夯实期", 2: "深度专精期", 3: "实战输出期"}.get(phase_num, f"阶段{phase_num}")
        for item in theme_content.get("items", []):
            bh = item.get("base_hours", 1)
            if bh < 0.01:
                continue
            all_study_items.append({
                "item_type": "study",
                "title": item["title"],
                "theme": theme,
                "phase_num": phase_num,
                "phase_name": phase_name,
                "source_skill": theme_map[theme]["name"],
                "mention_rate": theme_map[theme].get("mention_rate", 0),
                "base_hours": bh,
                "feynman_hint": item.get("feynman_hint", ""),
                "practice_task": item.get("practice_task", ""),
                "goal": theme_content.get("goal", ""),
            })

    # 3. 添加补充内容
    for supp in supplement_candidates:
        for d in supp["days"]:
            bh = _parse_hours_float(d[4])
            if bh < 0.01:
                continue
            all_study_items.append({
                "item_type": "supplement",
                "title": d[1],
                "theme": supp.get("theme", ""),
                "phase_num": supp.get("phase", 2),
                "phase_name": {1: "基础夯实期", 2: "深度专精期", 3: "实战输出期"}.get(supp.get("phase", 2), ""),
                "source_skill": supp["name"],
                "mention_rate": 0,
                "base_hours": bh,
                "feynman_hint": d[2],
                "practice_task": d[3],
                "goal": supp["goal"],
                "supplement_label": supp.get("label", ""),
            })

    # 4. 按主题依赖排序（以 theme 为单位）
    theme_kus = [{"theme": t, "phase_num": WEEK_PHASE_MAP.get(t, 2)} for t in themes_in_order]
    sorted_theme_kus = _resolve_prerequisites(theme_kus)
    sorted_themes = [ku["theme"] for ku in sorted_theme_kus]

    # 按排序后的主题重排 study items
    theme_order_map = {t: i for i, t in enumerate(sorted_themes)}
    all_study_items.sort(key=lambda x: (theme_order_map.get(x["theme"], 999),
                                         x.get("phase_num", 2)))

    # 5. 确定项目/开源数量
    daily_h = gap_data.get("daily_hours", 3.0)
    time_coeff = _compute_time_coefficient(daily_h)
    project_count, os_count = PROJECT_SCALE.get(duration, (4, 2))

    # 6. 构建穿插序列
    phase_themes = _build_phase_map(sorted_themes)
    sequence = []
    consecutive_study = 0
    project_counter = 0
    total_study_base = sum(it["base_hours"] for it in all_study_items)

    # 各阶段的项目模板（{theme} 会被替换为刚学完的主题名）
    phase_project_templates = {
        1: [{"name": "基础实战项目", "days": [
            ("", "{theme} 应用：需求分析与方案设计", "用工程思维规划基于 {theme} 的应用", "明确项目目标，设计 {theme} 的技术方案", "3h"),
            ("", "{theme} 核心功能开发", "聚焦 {theme} 的应用难点", "实现基于 {theme} 的核心功能", "3h"),
            ("", "{theme} 项目测试与复盘", "验证 {theme} 学习成果", "添加测试，完成项目文档并上传 GitHub", "2h"),
        ]}],
        2: [{"name": "进阶实战项目", "days": [
            ("", "{theme} 系统设计与接口定义", "先画图再写代码，理清模块间关系", "画出 {theme} 架构图并定义核心接口", "3h"),
            ("", "{theme} 核心逻辑实现", "重点攻克 {theme} 的技术难点", "实现 {theme} 的核心业务逻辑", "3h"),
            ("", "{theme} 集成测试与优化", "系统的瓶颈往往在集成阶段暴露", "添加集成测试并优化关键路径", "3h"),
            ("", "{theme} 技术复盘与文档", "写出你的设计思路和关键决策", "完成 {theme} 技术文档和复盘笔记", "2h"),
        ]}],
        3: [{"name": "综合实战项目", "days": [
            ("", "{theme} 需求分析与架构设计", "理解从需求到架构的转化过程", "输出 {theme} 需求文档和架构设计图", "3h"),
            ("", "{theme} 核心开发与联调", "独立完成有挑战的开发任务", "实现 {theme} 核心功能并完成集成联调", "3h"),
            ("", "{theme} 部署上线与演示", "让项目可被访问和展示", "部署到云端并准备演示材料", "3h"),
            ("", "{theme} 完整复盘", "系统性总结项目经验", "输出完整技术文档和复盘笔记", "2h"),
        ]}],
    }
    # 按阶段分配项目
    phase_themes_list = sorted(phase_themes.keys()) if phase_themes else [1]
    projects_per_phase = {}
    remaining = project_count
    for i, ph in enumerate(phase_themes_list):
        if i == len(phase_themes_list) - 1:
            projects_per_phase[ph] = remaining
        else:
            n = max(1, project_count // len(phase_themes_list))
            projects_per_phase[ph] = min(n, remaining)
            remaining -= n

    # 7. 构建穿插序列
    for theme in sorted_themes:
        phase = WEEK_PHASE_MAP.get(theme, 2)
        theme_items = [it for it in all_study_items if it["theme"] == theme]

        for item in theme_items:
            sequence.append(item)
            consecutive_study += 1

        # 学完本阶段主题 → 插入项目
        is_last_theme_of_phase = not any(
            WEEK_PHASE_MAP.get(t, 2) == phase
            for t in sorted_themes[sorted_themes.index(theme) + 1:]
            if t != theme
        )
        if is_last_theme_of_phase and projects_per_phase.get(phase, 0) > 0:
            for _ in range(projects_per_phase[phase]):
                project_counter += 1
                # 从该主题的学习条目中提取具体内容，动态生成项目描述
                theme_study_items = [it for it in all_study_items if it["theme"] == theme]
                proj_fmt = phase_project_templates.get(phase, phase_project_templates[1])[0]
                phase_labels = {1: "基础夯实期", 2: "深度专精期", 3: "实战输出期"}
                pn = f"{theme} 实战项目 #{project_counter}"
                day_roles = ["方案设计", "核心开发", "测试集成", "文档复盘"]

                for i, pd in enumerate(proj_fmt["days"]):
                    bh = _parse_hours_float(pd[4])
                    if bh < 0.01:
                        continue
                    ref = theme_study_items[i % len(theme_study_items)] if theme_study_items else None
                    role = day_roles[i] if i < len(day_roles) else f"第{i+1}天"
                    if ref:
                        day_title = f"{theme} 实战：{ref['title']}——{role}"
                        day_hint = f"将刚学的「{ref['title']}」应用到实战中——{ref['feynman_hint']}"
                        day_task = f"综合运用「{ref['title']}」相关知识（{ref['practice_task']}），完成项目{role}"
                    else:
                        day_title = pd[1].format(theme=theme)
                        day_hint = pd[2].format(theme=theme)
                        day_task = pd[3].format(theme=theme)
                    sequence.append({
                        "item_type": "project",
                        "title": day_title,
                        "theme": f"实战项目 #{project_counter}",
                        "phase_num": phase,
                        "phase_name": phase_labels.get(phase, f"阶段{phase}"),
                        "source_skill": "", "mention_rate": 0,
                        "base_hours": bh,
                        "feynman_hint": day_hint,
                        "practice_task": day_task,
                        "goal": pn,
                        "project_name": pn,
                        "project_num": project_counter,
                    })

        # 主题边界插入复盘
        if consecutive_study >= 5:
            theme_study_items = [it for it in all_study_items if it["theme"] == theme]
            topic_names = ", ".join(it["title"] for it in theme_study_items[:3])
            sequence.append({
                "item_type": "review", "title": f"{theme} — 阶段性巩固",
                "theme": "", "phase_num": phase, "phase_name": "阶段复盘",
                "source_skill": "", "mention_rate": 0, "base_hours": 2.0,
                "feynman_hint": f"回顾刚学的 {theme} 内容（{topic_names}），哪些能流畅讲清楚，哪些还模糊？",
                "practice_task": f"逐一检视 {theme} 各知识点掌握度：对 {topic_names} 分别标记置信度（绿/黄/红），列出待回炉清单",
                "goal": "查漏补缺，巩固记忆", "review_type": "light",
            })
            consecutive_study = 0

    # 插入开源贡献
    if os_count > 0:
        # 从 sequence 提取真实项目名
        os_project_refs = [it.get("project_name", "") for it in sequence if it["item_type"] == "project" and it.get("project_name")]
        os_project_names = list(dict.fromkeys(os_project_refs))
        project_ref = "、".join(os_project_names[-2:]) if os_project_names else "你刚完成的项目"

        estimated_seq_len = len(sequence) + os_count
        os_positions = []
        for i in range(1, os_count + 1):
            pos = int(estimated_seq_len * (i / (os_count + 1)))
            os_positions.append(pos)
        os_items_added = 0
        for pos in sorted(os_positions, reverse=True):
            pos = min(pos, len(sequence))
            os_idx = os_items_added % len(_OS_DAYS)
            day_def = _OS_DAYS[os_idx]
            os_items_added += 1
            sequence.insert(pos, {
                "item_type": "os_contribution",
                "title": f"开源实践：{day_def[0]}",
                "theme": "", "phase_num": 3, "phase_name": "开源与社区贡献",
                "source_skill": "", "mention_rate": 0, "base_hours": 2.5,
                "feynman_hint": day_def[1],
                "practice_task": f"基于「{project_ref}」项目，{day_def[2]}",
                "goal": f"将「{project_ref}」项目完善为开源作品", "os_num": os_items_added,
            })

    # 8. 弹性打包（节奏感知）：将 sequence 分配到日历天
    pace_config = gap_data.get("learning_pace", {"mode": "daily"})
    is_flexible = pace_config.get("mode") == "flexible"

    target_h = daily_h  # 用于后续 _batch_to_calendar_day()，flexible 模式下也使用日均值
    if is_flexible:
        # 灵活模式：不按天打包，每个 item 独立为一个"段"
        calendar_days = [[item] for item in sequence]
        total_calendar_days = len(calendar_days)
    else:
        calendar_days = []
        day_batch = []
        day_hours = 0.0
        day_index = 1  # 用于 weekend 模式计算周几

        for item in sequence:
            item_h = item["base_hours"]
            if pace_config.get("mode") == "weekend":
                target_h = get_day_target(pace_config, day_index)
            min_h = target_h * 0.75
            max_h = target_h * 1.25

            if not day_batch:
                day_batch = [item]
                day_hours = item_h
            elif day_hours + item_h <= max_h:
                day_batch.append(item)
                day_hours += item_h
                if day_hours >= min_h:
                    calendar_days.append(day_batch)
                    day_batch = []
                    day_hours = 0.0
                    day_index += 1
            else:
                calendar_days.append(day_batch)
                day_batch = [item]
                day_hours = item_h
                day_index += 1

        if day_batch:
            calendar_days.append(day_batch)

        total_calendar_days = len(calendar_days)

    # 9. 与 duration 对齐，用温和的填补防止计划过短
    #   条件：核心技能覆盖 ≥80% 且内容天数不足 55% 目标时，插入适量填充
    all_to_learn = [ms for ms in market_skills if not ms["user_has"]]
    all_essential = [ms for ms in all_to_learn if ms["source"] == "essential"]
    covered_essential_names = set()
    for item in sequence:
        for ms in all_essential:
            if ms["name"].lower() in item.get("title", "").lower():
                covered_essential_names.add(ms["name"])
    essential_covered_ratio = len(covered_essential_names) / max(1, len(all_essential))

    target_min_days = int(duration * 0.60)  # 软阈值：内容不足60%时填补
    max_filler = int(duration * 0.20)       # 硬上限：填补不超过20%总天数
    if total_calendar_days < target_min_days and essential_covered_ratio >= 0.8:
        gap = min(target_min_days - total_calendar_days, max_filler)
        last_phase = sequence[-1]["phase_num"] if sequence else 3
        # 按 1:1:1 插入实战深化:深度复盘:综合输出
        theme_list = "、".join(sorted_themes[:3])
        extras = []
        for i in range(gap):
            choice = i % 3
            if choice == 0:
                extras.append([{
                    "item_type": "project",
                    "title": "综合实践：技能串联与 Demo 构建",
                    "theme": "", "phase_num": last_phase,
                    "phase_name": "实战输出期",
                    "source_skill": "", "mention_rate": 0,
                    "base_hours": 3.0,
                    "feynman_hint": f"将 {theme_list} 的技术用在一个小型综合项目中检验理解",
                    "practice_task": f"从 {theme_list} 中选择 2-3 个技术，搭建一个小型综合 Demo",
                    "goal": "巩固已学技能的综合应用能力",
                    "project_name": f"项目深耕 #{i//3 + 1}",
                    "project_num": project_counter + i//3 + 1,
                }])
            elif choice == 1:
                extras.append([{
                    "item_type": "review",
                    "title": "知识串联：绘制已学概念关系图",
                    "theme": "", "phase_num": last_phase,
                    "phase_name": "综合复盘",
                    "source_skill": "", "mention_rate": 0,
                    "base_hours": 2.5,
                    "feynman_hint": f"把 {theme_list} 中的概念编成一个「从问题到解决」的技术故事",
                    "practice_task": f"围绕 {theme_list} 绘制知识图谱，将已学概念用因果关系串联",
                    "goal": "系统巩固，查漏补缺",
                    "review_type": "deep",
                }])
            else:
                extras.append([{
                    "item_type": "review",
                    "title": "内容产出：学习成果转化为教程",
                    "theme": "", "phase_num": last_phase,
                    "phase_name": "综合复盘",
                    "source_skill": "", "mention_rate": 0,
                    "base_hours": 3.0,
                    "feynman_hint": f"假设你要教会零基础的人 {theme_list} 中的一个技术点，你会怎么组织内容",
                    "practice_task": f"从 {theme_list} 中选择一个技术点，写一篇面向初学者的技术教程",
                    "goal": "将知识沉淀为可展示的作品",
                    "review_type": "synthesis",
                }])
        # 均匀散布到日历中
        for idx, ins in enumerate(extras):
            pos = min(len(calendar_days), 3 + idx * max(1, len(calendar_days) // max(1, len(extras))))
            calendar_days.insert(pos, ins)
            total_calendar_days += 1

    actual_total_days = total_calendar_days

    # 10. 组装 knowledge_units（按 phase 分组）
    #     每个 phase 是一个 knowledge_unit，包含 _merged_days
    phase_groups_seq = {}
    for day_idx, batch in enumerate(calendar_days[:actual_total_days]):
        phase_num = batch[0].get("phase_num", 2) if batch else 2
        phase_name = batch[0].get("phase_name", "") if batch else ""
        if phase_num not in phase_groups_seq:
            phase_groups_seq[phase_num] = {
                "phase_num": phase_num,
                "phase_name": phase_name,
                "day_batches": [],
            }
        phase_groups_seq[phase_num]["day_batches"].append(batch)

    final_kus = []
    current_day = 1
    for pn in sorted(phase_groups_seq.keys()):
        pg = phase_groups_seq[pn]
        merged_days = []
        for batch in pg["day_batches"]:
            # 构建一个合并天
            cal = _batch_to_calendar_day(batch, target_h, time_coeff)
            merged_days.append(cal)

        day_count = len(merged_days)
        pu = {
            "unit_type": "study",
            "title": pg.get("phase_name", f"阶段{pn}"),
            "theme": "",
            "days": [],  # 学习内容来自 _merged_days
            "phase_num": pn,
            "phase_name": pg.get("phase_name", f"阶段{pn}"),
            "day_start": current_day,
            "day_end": current_day + day_count - 1,
            "_merged_days": merged_days,
            "_day_count": day_count,
            "total_hours": sum(cd["scaled_hours"] + cd.get("filler_hours", 0) for cd in merged_days),
            "source_skill": "",
            "mention_rate": 0,
        }
        final_kus.append(pu)
        current_day += day_count

    # 11. 提取项目/复盘信息
    all_proj_days = [batch for batch in calendar_days[:actual_total_days]
                     if any(it["item_type"] == "project" for it in batch)]
    project_kus = []
    seen_proj_names = set()
    for batch in all_proj_days:
        for it in batch:
            if it["item_type"] == "project" and it.get("project_name") and it["project_name"] not in seen_proj_names:
                seen_proj_names.add(it["project_name"])
                pname = it["project_name"]
                pnum = it.get("project_num", 1)
                # Find all days for this project
                proj_batches = [b for b in calendar_days[:actual_total_days]
                                if any(x["item_type"] == "project" and x.get("project_name") == pname for x in b)]
                if proj_batches:
                    pstart = sum(len(prev) for prev in calendar_days[:calendar_days.index(proj_batches[0])]) + 1 if calendar_days.index(proj_batches[0]) > 0 else 1
                    pend = pstart + len(proj_batches) - 1
                    ph = proj_batches[0][0].get("phase_num", 2)
                    project_kus.append({
                        "unit_type": "project",
                        "title": pname,
                        "day_start": pstart,
                        "day_end": pend,
                        "total_hours": sum(
                            _parse_hours_float(x["base_hours"]) * time_coeff
                            for b in proj_batches for x in b if x.get("project_name") == pname
                        ),
                        "phase_num": ph,
                    })

    all_review_days = _build_review_days_from_calendar(calendar_days[:actual_total_days])
    all_os_contributions = _build_os_list_from_calendar(calendar_days[:actual_total_days], os_count)

    # 12. 计算技能覆盖率
    covered_themes = set()
    for ku in final_kus:
        md = ku.get("_merged_days", [])
        for cd in md:
            for topic in cd.get("topics", []):
                for ms in market_skills:
                    if ms["name"].lower() in topic.lower() and not ms.get("user_has"):
                        covered_themes.add(ms["name"])

    all_to_learn = [ms for ms in market_skills if not ms["user_has"]]
    all_essential = [ms for ms in all_to_learn if ms["source"] == "essential"]
    all_bonus = [ms for ms in all_to_learn if ms["source"] == "bonus"]
    essential_covered = sum(1 for ms in all_essential if ms["name"] in covered_themes)
    bonus_covered = sum(1 for ms in all_bonus if ms["name"] in covered_themes)

    total_all_hours = sum(ku["total_hours"] for ku in final_kus)
    total_actual_days = max(current_day - 1, 1)

    # 概览
    learning_overview = []
    for ku in final_kus:
        dr = f"Day {ku['day_start']}" if ku["day_start"] == ku["day_end"] else f"Day {ku['day_start']}-{ku['day_end']}"
        learning_overview.append({
            "day_range": dr,
            "title": ku["title"],
            "type": "弹性学习",
            "estimated_hours": ku["total_hours"],
        })

    return {
        "knowledge_units": final_kus,
        "total_days": total_actual_days,
        "total_hours": total_all_hours,
        "time_coefficient": time_coeff,
        "learning_overview": learning_overview,
        "projects": project_kus,
        "os_contributions": all_os_contributions,
        "review_days": all_review_days,
        "essential_count": len(all_essential),
        "essential_covered": essential_covered,
        "bonus_count": len(all_bonus),
        "bonus_covered": bonus_covered,
        "is_flexible": is_flexible,
    }


def _batch_to_calendar_day(batch, daily_target, time_coeff):
    """将一批 item 转换为日历天格式。
    按 base_hours 比例将 daily_target 分配到各 item 作为 scaled 时长。
    """
    total_base = sum(it["base_hours"] for it in batch)
    total_scaled = round(min(total_base, daily_target), 1)

    blocks = []
    for item in batch:
        ratio = item["base_hours"] / total_base if total_base > 0 else 1.0
        item_scaled = total_scaled * ratio
        blocks.append({"type": "核心", "topic": item["title"],
                       "hours": round(item_scaled * 0.50, 1)})
        if item.get("practice_task"):
            blocks.append({"type": "实践", "topic": item["practice_task"],
                           "hours": round(item_scaled * 0.25, 1)})
        blocks.append({"type": "费曼", "topic": item["title"],
                       "hours": round(max(0.25, item_scaled * 0.20), 1)})

    # 构建 tags
    tags = []
    for item in batch:
        if item["item_type"] == "project":
            pn = item.get("project_num", "")
            tags.append(f"【实战项目#{pn}】")
        elif item["item_type"] == "os_contribution":
            on = item.get("os_num", "")
            tags.append(f"【开源贡献#{on}】")
        elif item["item_type"] == "review":
            tags.append("【复盘整理】")

    filler = round(max(0, daily_target - total_scaled), 1)
    if filler > 0.3 and batch:
        fblocks = _generate_filler_blocks("study", filler, batch[-1]["title"])
        blocks.extend(fblocks)
    else:
        filler = 0

    return {
        "topics": [it["title"] for it in batch],
        "feynman_hints": [it.get("feynman_hint", "") for it in batch],
        "practice_tasks": [it.get("practice_task", "") for it in batch],
        "goals": [it.get("goal", "") for it in batch],
        "base_hours": round(total_base, 1),
        "scaled_hours": total_scaled,
        "filler_hours": filler,
        "blocks": blocks,
        "tags": list(set(tags)),
        "item_types": [it["item_type"] for it in batch],
    }


def _build_review_days_from_calendar(calendar_days):
    """从日历天中提取复盘日信息。"""
    reviews = []
    for day_idx, batch in enumerate(calendar_days, 1):
        if any(it["item_type"] == "review" for it in batch):
            reviews.append({
                "day_start": day_idx,
                "title": "阶段性知识巩固",
                "type": "light",
            })
    return reviews


def _build_os_list_from_calendar(calendar_days, max_os):
    """从日历天中提取开源贡献信息。"""
    os_list = []
    for day_idx, batch in enumerate(calendar_days, 1):
        if any(it["item_type"] == "os_contribution" for it in batch):
            os_list.append({
                "day_start": day_idx,
                "title": f"开源贡献实践 #{len(os_list) + 1}",
            })
    return os_list
