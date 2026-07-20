#!/usr/bin/env python3
"""
JD 数据分析与报告生成
读取清洗后的岗位数据（Excel/CSV/TXT），自动分析市场需求并生成结构化 Markdown 报告。

用法:
  python jd_analyzer.py --input jobs_clean.xlsx --title "AI Agent开发工程师"

输出:
  {岗位名称}_JD_Analysis_Report.md
"""

import json
import re
import sys
import os
import argparse
from collections import Counter
from datetime import datetime

import pandas as pd

from utils.claude_helper import claude_available, call_claude

try:
    import jieba
    import jieba.analyse
except ImportError:
    msg = {"error": "缺少 jieba 库，请执行: pip install jieba", "step": "dep"}
    print(json.dumps(msg, ensure_ascii=False))
    sys.exit(1)


# ── 岗位名称 → 种子词库 ──

POSITION_SEED_MAP = [
    # 格式: (关键词, [种子词列表])
    ("算法", ["算法", "模型", "训练", "推理", "深度学习", "机器学习", "PyTorch", "TensorFlow"]),
    ("大模型", ["大模型", "LLM", "GPT", "Transformer", "训练", "SFT", "RLHF", "推理"]),
    ("Agent", ["Agent", "LangChain", "LangGraph", "工具调用", "RAG", "记忆", "规划"]),
    ("开发", ["开发", "Python", "Java", "Go", "C++", "工程", "API", "架构", "后端"]),
    ("NLP", ["NLP", "自然语言", "文本", "语义", "BERT", "GPT", "分词", "NER"]),
    ("AIGC", ["AIGC", "生成", "扩散", "Stable Diffusion", "图像", "视频", "多模态"]),
    ("运维", ["运维", "Kubernetes", "Docker", "部署", "监控", "CI/CD", "DevOps"]),
    ("数据", ["数据", "ETL", "Spark", "Flink", "Kafka", "数据仓库", "Hadoop"]),
    ("产品", ["产品", "需求", "PRD", "用户", "体验", "交互", "原型", "Axure"]),
    ("前端", ["前端", "React", "Vue", "TypeScript", "HTML", "CSS", "Web"]),
    ("测试", ["测试", "自动化", "CI/CD", "单元测试", "集成测试", "Selenium"]),
    ("实习", ["实习", "学习", "基础", "培养", "指导", "在校"]),
    ("AI", ["AI", "人工智能", "大模型", "LLM", "深度学习", "机器学习"]),
    ("研发", ["研发", "开发", "工程", "架构", "设计", "实现", "优化"]),
    ("工程", ["工程", "开发", "架构", "系统", "平台", "部署", "性能"]),
]


def build_seed_keywords(title):
    """根据岗位名称自动构建关键词种子库"""
    title_lower = title.lower()
    seeds = set()

    for keyword, word_list in POSITION_SEED_MAP:
        if keyword.lower() in title_lower:
            seeds.update(word_list)

    # 从标题本身提取词汇
    title_cut = jieba.lcut(title)
    seeds.update(w for w in title_cut if len(w) > 1 and not re.match(r'^[\d\W]+$', w))

    # 添加通用技术词
    seeds.update([
        "Python", "开发", "工程", "系统", "平台", "技术", "设计", "实现",
        "优化", "架构", "服务", "数据", "模型", "算法", "团队", "项目",
    ])

    return list(seeds)


# ── 分类词典 ──

HARD_SKILL_DICT = {
    "编程语言": ["Python", "Java", "Go", "C++", "C#", "Rust", "JavaScript", "TypeScript", "Scala", "Shell"],
    "AI/ML框架": ["PyTorch", "TensorFlow", "Keras", "MXNet", "PaddlePaddle", "JAX", "ONNX"],
    "大模型/LLM": ["GPT", "LLM", "大模型", "Transformer", "BERT", "ChatGPT", "GLM", "Qwen", "Baichuan", "Llama", "ChatGLM", "LangChain", "LangGraph", "RAG", "Agent", "Prompt", "SFT", "RLHF", "LoRA", "微调"],
    "云原生/DevOps": ["Kubernetes", "K8s", "Docker", "Jenkins", "CI/CD", "Git", "GitHub", "GitLab"],
    "数据库/中间件": ["MySQL", "Redis", "MongoDB", "PostgreSQL", "Elasticsearch", "Kafka", "RabbitMQ", "RocketMQ"],
    "大数据": ["Spark", "Flink", "Hadoop", "Hive", "HBase", "Flume"],
    "视觉/CV": ["OpenCV", "图像", "视频", "目标检测", "OCR", "人脸", "YOLO"],
    "NLP": ["NLP", "分词", "NER", "情感", "语义", "文本", "对话", "意图"],
}

SOFT_SKILL_SET = {
    "沟通", "协作", "团队合作", "团队精神", "责任心", "自驱", "自我驱动",
    "学习能力", "快速学习", "逻辑思维", "解决问题", "问题分析", "抗压",
    "主动", "积极", "耐心", "细心", "执行力", "推动力", "表达",
    "英语", "英文", "阅读", "文档", "方案",
}

EXPERIENCE_PATTERNS = [
    (r'(\d+)[-~]\d+\s*年', lambda m: f'{m.group(1)}+年'),
    (r'(\d+)\s*年以上', lambda m: f'{m.group(1)}+年'),
    (r'经验不限', '经验不限'),
    (r'应届生', '应届生'),
]

EDUCATION_PATTERNS = {
    '博士': r'博士',
    '硕士': r'硕士|研究生',
    '本科': r'本科',
    '大专': r'大专|专科',
    '学历不限': r'学历不限|不限学历',
}


# ── 核心分析 ──

def load_data(path):
    """读取数据文件，支持 xlsx/csv/txt"""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".xlsx":
        return pd.read_excel(path, engine="openpyxl")
    elif ext == ".csv":
        return pd.read_csv(path)
    elif ext == ".txt":
        with open(path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        return pd.DataFrame({"JD摘要": lines})
    else:
        raise ValueError(f"不支持的文件格式: {ext}")


def find_jd_column(df):
    """自动识别 JD 文本列"""
    candidates = ["JD摘要", "JD", "jd", "jd_text", "职位描述", "岗位职责", "岗位描述",
                  "职位要求", "任职要求", "description", "正文"]
    for col in df.columns:
        if col in candidates:
            return col
    # 找文本最长的列
    text_cols = [c for c in df.columns if df[c].dtype == object]
    if text_cols:
        return max(text_cols, key=lambda c: df[c].astype(str).str.len().sum())
    return df.columns[0]


def analyze_jds(df, title, seed_keywords):
    """分析 JD 数据，返回统计信息"""
    jd_col = find_jd_column(df)
    jd_texts = df[jd_col].astype(str).tolist()

    # 合并所有 JD 文本
    all_text = " ".join(jd_texts)

    # ── 词频统计（用 jieba 分词）──
    words = jieba.lcut(all_text)
    # 过滤：长度 >= 2，非纯数字/符号
    filtered_words = [
        w for w in words
        if len(w) >= 2 and not re.match(r'^[\d\s\W_]+$', w)
    ]
    word_freq = Counter(filtered_words)

    # TF-IDF 提取关键词（种子词加权）
    tfidf_keywords = jieba.analyse.extract_tags(all_text, topK=100, withWeight=True)
    tfidf_dict = {k: w for k, w in tfidf_keywords}

    # ── 硬技能统计 ──
    skill_stats = {}
    for category, skills in HARD_SKILL_DICT.items():
        counts = {}
        for skill in skills:
            count = len(re.findall(re.escape(skill), all_text, re.IGNORECASE))
            if count > 0:
                counts[skill] = count
        if counts:
            skill_stats[category] = dict(sorted(counts.items(), key=lambda x: -x[1]))

    # ── 按 JD 粒度的提及率计算 ──
    mention_rates = {}
    for category, skills in HARD_SKILL_DICT.items():
        for skill in skills:
            jd_count = sum(1 for t in jd_texts if re.search(re.escape(skill), t, re.IGNORECASE))
            if jd_count > 0:
                mention_rates[skill] = round(jd_count / len(jd_texts) * 100, 1)

    all_skills_by_rate = sorted(mention_rates.items(), key=lambda x: -x[1])
    essential_skills = [(s, r) for s, r in all_skills_by_rate if r >= 30.0]
    bonus_skills = [(s, r) for s, r in all_skills_by_rate if 10.0 <= r < 30.0]

    # ── 软技能统计 ──
    soft_skills = {}
    for skill in SOFT_SKILL_SET:
        count = len(re.findall(re.escape(skill), all_text))
        if count > 0:
            soft_skills[skill] = count
    soft_skills = dict(sorted(soft_skills.items(), key=lambda x: -x[1]))

    # ── 学历要求统计 ──
    edu_stats = {}
    for level, pattern in EDUCATION_PATTERNS.items():
        count = sum(1 for t in jd_texts if re.search(pattern, t))
        if count > 0:
            edu_stats[level] = count

    # ── 经验要求统计（仅取每个 JD 中第一个匹配）──
    exp_stats = {}
    for t in jd_texts:
        for pat_regex, label_or_fn in EXPERIENCE_PATTERNS:
            m = re.search(pat_regex, t)
            if m:
                if callable(label_or_fn):
                    tag = label_or_fn(m)
                else:
                    tag = label_or_fn
                exp_stats[tag] = exp_stats.get(tag, 0) + 1
                break

    # ── 数据概览 ──
    overview = {
        "total_jobs": len(df),
        "total_companies": df["公司名称"].nunique() if "公司名称" in df.columns else 0,
        "job_column": jd_col,
    }

    if "岗位名称" in df.columns:
        titles = df["岗位名称"].astype(str)
        overview["intern_count"] = int(titles.str.contains("实习", na=False).sum())
        overview["formal_count"] = overview["total_jobs"] - overview["intern_count"]

    if "工作地点" in df.columns:
        location_counts = df["工作地点"].value_counts().head(10).to_dict()
        overview["top_locations"] = {str(k): int(v) for k, v in location_counts.items()}

    # ── 公司分析 ──
    if "公司名称" in df.columns:
        companies = df["公司名称"].dropna().astype(str)
        company_counts = Counter(companies).most_common(15)
        overview["top_companies"] = [(str(c), int(n)) for c, n in company_counts]

    return {
        "overview": overview,
        "word_freq_top": dict(word_freq.most_common(50)),
        "tfidf_top": {k: round(v, 4) for k, v in tfidf_keywords[:30]},
        "skill_stats": skill_stats,
        "soft_skills": soft_skills,
        "edu_stats": edu_stats,
        "exp_stats": exp_stats,
        "total_jd_chars": len(all_text),
        "mention_rates": mention_rates,
        "essential_skills": essential_skills,
        "bonus_skills": bonus_skills,
    }


def generate_report(stats, title):
    """生成结构化 Markdown 报告"""
    o = stats["overview"]
    lines = []

    # 标题 & 元信息
    lines.append(f"# {title} — JD 市场需求分析报告")
    lines.append(f"")
    lines.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"> 数据来源：BOSS直聘")
    lines.append(f"")
    lines.append("---")
    lines.append("")

    # ── 1. 数据概览 ──
    lines.append("## 一、数据概览")
    lines.append("")
    lines.append(f"- **样本总量**：{o['total_jobs']} 个岗位")
    lines.append(f"- **涉及公司**：{o['total_companies']} 家")
    if "intern_count" in o:
        lines.append(f"- **正式/实习**：{o['formal_count']} 个正式岗位 / {o['intern_count']} 个实习岗位")
    if "top_locations" in o:
        locs = o["top_locations"]
        loc_str = "、".join([f"{k}（{v}个）" for k, v in list(locs.items())[:5]])
        lines.append(f"- **主要城市**：{loc_str}")
    if "top_companies" in o:
        companies = o["top_companies"]
        lines.append(f"- **主要招聘方**：{', '.join([c for c, n in companies[:8]])}")
    lines.append(f"- **JD 文本总长度**：{stats['total_jd_chars']:,} 字符")
    lines.append("")

    # ── 2. 硬技能需求TOP榜 ──
    lines.append("## 二、硬技能需求TOP榜")
    lines.append("")
    lines.append("基于词频统计，以下为各技术类别中需求最高的技能：")
    lines.append("")

    # 整体 TOP 技能（不分词类别）
    lines.append("### TOP 20 核心技术关键词")
    lines.append("")
    lines.append("| 排名 | 关键词 | 提及率 | 出现次数 |")
    lines.append("|------|--------|--------|----------|")
    # 从 skill_stats 中取出所有技能打平排
    flat_skills = []
    for cat, skills in stats["skill_stats"].items():
        for skill, count in skills.items():
            flat_skills.append((skill, count, cat))
    flat_skills.sort(key=lambda x: -x[1])
    mention_rates = stats.get("mention_rates", {})
    for i, (skill, count, cat) in enumerate(flat_skills[:20], 1):
        rate = mention_rates.get(skill, 0)
        rate_str = f"{rate}%" if rate else "-"
        lines.append(f"| {i} | {skill} | {rate_str} | {count} 次 |")
    lines.append("")

    # ── 必备技能 TOP榜 ──
    essential = stats.get("essential_skills", [])
    if essential:
        lines.append("### 2.1 必备技能 TOP榜（提及率 >= 30%）")
        lines.append("")
        lines.append("| 排名 | 技能 | 提及率 | 出现次数 | 类别 |")
        lines.append("|------|------|--------|----------|------|")
        # Build a skill→category lookup
        skill_cat = {}
        for cat, skills in stats["skill_stats"].items():
            for sk, _ in skills.items():
                skill_cat[sk] = cat
        for i, (skill, rate) in enumerate(essential, 1):
            cat = skill_cat.get(skill, "其他")
            # Find total occurrence count from flat_skills
            occ = next((c for s, c, _ in flat_skills if s == skill), 0)
            lines.append(f"| {i} | {skill} | {rate}% | {occ}次 | {cat} |")
        lines.append("")

    # ── 加分技能 TOP榜 ──
    bonus = stats.get("bonus_skills", [])
    if bonus:
        lines.append("### 2.2 加分技能 TOP榜（10% <= 提及率 < 30%）")
        lines.append("")
        lines.append("| 排名 | 技能 | 提及率 | 出现次数 | 类别 |")
        lines.append("|------|------|--------|----------|------|")
        skill_cat = {}
        for cat, skills in stats["skill_stats"].items():
            for sk, _ in skills.items():
                skill_cat[sk] = cat
        for i, (skill, rate) in enumerate(bonus, 1):
            cat = skill_cat.get(skill, "其他")
            occ = next((c for s, c, _ in flat_skills if s == skill), 0)
            lines.append(f"| {i} | {skill} | {rate}% | {occ}次 | {cat} |")
        lines.append("")

    # 分技能展示
    for category, skills in stats["skill_stats"].items():
        if not skills:
            continue
        lines.append(f"### {category}")
        lines.append("")
        lines.append("| 技能/工具 | 提及率 | 出现次数 |")
        lines.append("|-----------|--------|----------|")
        for skill, count in list(skills.items())[:10]:
            rate = mention_rates.get(skill, 0)
            rate_str = f"{rate}%" if rate else "-"
            lines.append(f"| {skill} | {rate_str} | {count} |")
        lines.append("")

    # ── 3. 软技能与经验门槛 ──
    lines.append("## 三、软技能与经验门槛")
    lines.append("")

    # 学历要求
    lines.append("### 学历要求分布")
    lines.append("")
    edu = stats["edu_stats"]
    total_edu = sum(edu.values()) if edu else 1
    if edu:
        lines.append("| 学历 | 提及次数 | 占比 |")
        lines.append("|------|----------|------|")
        for level in ["博士", "硕士", "本科", "大专", "学历不限"]:
            cnt = edu.get(level, 0)
            if cnt > 0:
                pct = cnt / total_edu * 100
                lines.append(f"| {level} | {cnt} | {pct:.0f}% |")
    else:
        lines.append("（未从 JD 中提取到明确的学历要求）")
    lines.append("")

    # 经验要求
    lines.append("### 经验要求分布")
    lines.append("")
    exp = stats["exp_stats"]
    total_exp = sum(exp.values()) if exp else 1
    if exp:
        lines.append("| 经验 | 提及次数 | 占比 |")
        lines.append("|------|----------|------|")
        for exp_label in sorted(exp.keys(), key=lambda x: (isinstance(x, str), x)):
            cnt = exp[exp_label]
            pct = cnt / total_exp * 100
            lines.append(f"| {exp_label} | {cnt} | {pct:.0f}% |")
    else:
        lines.append("（未从 JD 中提取到明确的经验要求）")
    lines.append("")

    # 软技能
    lines.append("### 软技能关键词")
    lines.append("")
    soft = stats["soft_skills"]
    if soft:
        lines.append("| 软技能 | 出现次数 |")
        lines.append("|--------|----------|")
        for skill, count in list(soft.items())[:15]:
            lines.append(f"| {skill} | {count} |")
    else:
        lines.append("（未从 JD 中提取到明确的软技能要求）")
    lines.append("")

    # ── 4. 行业赛道分析 ──
    lines.append("## 四、行业赛道分析")
    lines.append("")

    # 公司类别分析
    if "top_companies" in o:
        companies = o["top_companies"]
        lines.append("### 主要招聘公司")
        lines.append("")
        lines.append("| 公司 | 岗位数 |")
        lines.append("|------|--------|")
        for c, n in companies:
            lines.append(f"| {c} | {n} |")
        lines.append("")

        # 判断赛道
        big_tech = {"字节跳动", "阿里巴巴集团", "京东集团", "阿里巴巴", "腾讯", "百度", "美团", "小米", "快手"}
        ai_companies = [c for c, _ in companies if any(k in c for k in ["AI", "智能", "科技", "数智", "数据"])]
        num_big_tech = sum(1 for c, _ in companies if c in big_tech)
        lines.append("### 赛道特征")
        lines.append("")
        lines.append(f"- **大厂参与度**：{num_big_tech} 家知名互联网/科技大厂在招")
        lines.append(f"- **AI/科创公司**：{len(ai_companies)} 家 AI 方向公司（{', '.join(ai_companies[:6])}）")
        if len(companies) > 10:
            lines.append(f"- **传统行业转型**：多家传统/垂直行业公司也在招募该岗位，说明 {title} 需求正在泛化")
        lines.append("")

    # ── 5. 核心洞察总结 ──
    lines.append("## 五、核心洞察总结")
    lines.append("")

    # 动态生成洞察

    # 1. 技术栈判定
    top_skills = [s for s, c, _ in flat_skills[:8]]
    lines.append(f"**① 核心技术栈**")
    lines.append(f"")
    lines.append(f"该岗位最核心的技术栈集中在 **{'、'.join(top_skills[:5])}** 等方向。")
    lines.append(f"")

    # 2. 经验判断
    if edu:
        top_edu = max(edu, key=edu.get)
        lines.append(f"**② 学历门槛**")
        lines.append(f"")
        lines.append(f"最低学历要求以 **{top_edu}** 为主" + (f"（{edu.get(top_edu, 0)}个岗位提及）" if edu.get(top_edu) else "") + "。")
        lines.append(f"")

    # 3. 实习 vs 正式
    if "intern_count" in o and o["intern_count"] > 0:
        intern_pct = o["intern_count"] / o["total_jobs"] * 100
        if intern_pct > 30:
            lines.append(f"**③ 入门友好度**")
            lines.append(f"")
            lines.append(f"实习岗位占比 {intern_pct:.0f}%，说明该领域对新人友好，是切入的好时机。")
            lines.append(f"")
        else:
            lines.append(f"**③ 岗位结构**")
            lines.append(f"")
            lines.append(f"正式岗位占主导（{o['formal_count']}/{o['total_jobs']}），实习坑位有限，说明该岗位更看重实际项目经验。")
            lines.append(f"")

    # 4. TF-IDF 最独特关键词
    tfidf_uniq = [k for k in stats["tfidf_top"] if k not in [s for s, _, _ in flat_skills[:5]]][:5]
    if tfidf_uniq:
        lines.append(f"**④ 差异化关键词**")
        lines.append(f"")
        lines.append(f"TF-IDF 分析显示，以下关键词在 JD 中具有较高区分度：{'、'.join(tfidf_uniq)}。这些可能是面试中的关键区分点。")
        lines.append(f"")

    # 5. 综合建议
    lines.append(f"**⑤ 综合建议**")
    lines.append(f"")
    if o.get("formal_count", 0) > o.get("intern_count", 0) * 2:
        lines.append(f"当前市场对 {title} 的需求以**有经验者**为主。建议在投递前准备 1-2 个完整的 Agent 项目案例，重点展示 {top_skills[0] if top_skills else '核心'} 相关能力。")
    else:
        lines.append(f"当前市场对 {title} 的需求对**新人/实习生**有一定空间。建议通过实习或项目积累经验，重点关注 {'、'.join(top_skills[:3])} 技能栈。")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*报告由 ai-job-hunter 自动生成*")

    return "\n".join(lines)


# ── Claude 分析模式 ──

_CLAUDE_JD_SYSTEM = """你是一位中文招聘数据分析专家。分析岗位描述(JD)数据，提取结构化市场洞察。

你的输出必须严格遵循 JSON 格式。"""


def _build_jd_analysis_prompt(title, jd_texts):
    """构造 Claude JD 分析 prompt。"""
    total = len(jd_texts)
    # 截断长文本以防超 token 限制
    truncated = []
    for i, t in enumerate(jd_texts):
        if len(t) > 3000:
            t = t[:3000] + f"\n...（原文共{len(t)}字符，已截断）"
        truncated.append(t)

    texts_json = json.dumps(
        [{"id": i + 1, "text": t} for i, t in enumerate(truncated)],
        ensure_ascii=False,
    )

    return f"""以下是 {total} 条「{title}」岗位的 JD 文本数据，请分析并返回 JSON。

返回 JSON 结构必须严格遵循以下格式：

```json
{{
  "hard_skills": [
    {{"name": "技能名称", "count": 出现次数, "mention_rate": 百分比(0-100)}}
  ],
  "skill_categories": {{
    "编程语言": ["Python", "Java", ...],
    "AI/ML框架": ["PyTorch", "TensorFlow", ...],
    "大模型/LLM": ["大模型", "GPT", "LangChain", ...],
    "云原生/DevOps": ["Docker", "Kubernetes", ...],
    "数据库/中间件": ["MySQL", "Redis", ...],
    "大数据": ["Spark", "Flink", ...],
    "视觉/CV": ["OpenCV", "YOLO", ...],
    "NLP": ["NLP", "分词", ...]
  }},
  "education_stats": {{"博士": N, "硕士": N, "本科": N, "大专": N, "学历不限": N}},
  "experience_stats": {{"经验要求描述": 出现次数}},
  "soft_skills": [{{"name": "软技能名", "count": 出现次数}}],
  "top_companies": [{{"name": "公司名", "count": 招聘数量}}],
  "industry_insight": "2-3句行业观察（中文）"
}}
```

关键规则：
1. hard_skills 中每个技能只出现一次，count 为在多少条 JD 中提到
2. mention_rate = round(count / {total} * 100, 1)
3. 语义归类：\"熟悉GPT/Claude/文心一言\" → 归为\"大模型\"；\"了解Agent/Function Calling\" → 归为\"Agent\"
4. education_stats 数量加起来应 ≤ {total}（不是所有 JD 都写学历要求）
5. 所有文本用中文
6. 只返回 JSON，不要额外说明

JD 数据：
{texts_json}"""


def _claude_output_to_stats(claude_result, df, title):
    """将 Claude 返回的 JSON 转换为与 analyze_jds() 兼容的 stats dict。"""
    total_jobs = len(df)

    # 构建 skill_stats（分类字典）
    skill_cats = claude_result.get("skill_categories", {})
    hard_skills = claude_result.get("hard_skills", [])
    skill_name_to_rate = {s["name"]: s.get("mention_rate", 0) for s in hard_skills}
    skill_name_to_count = {s["name"]: s.get("count", 0) for s in hard_skills}

    skill_stats = {}
    for cat, skills in skill_cats.items():
        cat_dict = {}
        for sk in skills:
            cnt = skill_name_to_count.get(sk, 0)
            if cnt > 0:
                cat_dict[sk] = cnt
        if cat_dict:
            skill_stats[cat] = dict(
                sorted(cat_dict.items(), key=lambda x: -x[1])
            )

    # mention_rates
    mention_rates = {}
    for s in hard_skills:
        mention_rates[s["name"]] = s.get("mention_rate", 0)

    # essential / bonus
    essential = [(s["name"], s.get("mention_rate", 0))
                 for s in hard_skills if s.get("mention_rate", 0) >= 30.0]
    bonus = [(s["name"], s.get("mention_rate", 0))
             for s in hard_skills if 10.0 <= s.get("mention_rate", 0) < 30.0]

    # soft skills
    soft_skills = {}
    for s in claude_result.get("soft_skills", []):
        soft_skills[s["name"]] = s.get("count", 0)

    # education
    edu_stats = claude_result.get("education_stats", {})
    exp_stats = claude_result.get("experience_stats", {})

    # company stats
    companies = claude_result.get("top_companies", [])

    # overview
    overview = {
        "total_jobs": total_jobs,
        "total_companies": len(companies),
        "job_column": "JD摘要",
    }
    if "岗位名称" in df.columns:
        titles = df["岗位名称"].astype(str)
        overview["intern_count"] = int(
            titles.str.contains("实习", na=False).sum()
        )
        overview["formal_count"] = total_jobs - overview["intern_count"]
    if "工作地点" in df.columns:
        location_counts = (
            df["工作地点"].value_counts().head(10).to_dict()
        )
        overview["top_locations"] = {
            str(k): int(v) for k, v in location_counts.items()
        }
    if "公司名称" in df.columns:
        from collections import Counter as C2
        real_companies = df["公司名称"].dropna().astype(str)
        cc = C2(real_companies).most_common(15)
        overview["top_companies"] = [(str(c), int(n)) for c, n in cc]

    total_jd_chars = int(df.astype(str).sum(axis=1).str.len().sum())

    return {
        "overview": overview,
        "word_freq_top": {},
        "tfidf_top": {},
        "skill_stats": skill_stats,
        "soft_skills": soft_skills,
        "edu_stats": edu_stats,
        "exp_stats": exp_stats,
        "total_jd_chars": total_jd_chars,
        "mention_rates": mention_rates,
        "essential_skills": essential,
        "bonus_skills": bonus,
    }


def analyze_jds_with_claude(df, title):
    """使用 Claude 分析 JD 数据，返回与 analyze_jds() 兼容的 stats dict。"""
    jd_col = find_jd_column(df)
    jd_texts = df[jd_col].astype(str).tolist()

    # 过滤太短的文本
    jd_texts = [t for t in jd_texts if len(t.strip()) > 20]

    prompt = _build_jd_analysis_prompt(title, jd_texts)

    result = call_claude(
        system_prompt=_CLAUDE_JD_SYSTEM,
        user_prompt=prompt,
        response_schema={
            "type": "object",
            "properties": {
                "hard_skills": {"type": "array"},
                "skill_categories": {"type": "object"},
                "education_stats": {"type": "object"},
                "experience_stats": {"type": "object"},
                "soft_skills": {"type": "array"},
                "top_companies": {"type": "array"},
                "industry_insight": {"type": "string"},
            },
        },
    )

    if result is None:
        return None

    return _claude_output_to_stats(result, df, title)


def main():
    parser = argparse.ArgumentParser(description="JD 数据分析与报告生成")
    parser.add_argument("--input", required=True, help="输入文件路径（xlsx/csv/txt）")
    parser.add_argument("--title", default="", help="岗位名称（默认从文件名推断）")
    parser.add_argument("--output", default="", help="输出报告路径（默认自动生成）")
    parser.add_argument("--data-dir", default="", help="数据目录（默认从 AI_JOB_HUNTER_DATA 环境变量读取）")
    parser.add_argument("--use-claude", action="store_true", help="使用 Claude API 进行语义分析（需设置 ANTHROPIC_API_KEY）")
    args = parser.parse_args()

    data_dir = args.data_dir or os.environ.get("AI_JOB_HUNTER_DATA", "")

    # 读取数据
    print(json.dumps({"step": "load", "message": f"正在读取数据: {args.input}"}, ensure_ascii=False))
    df = load_data(args.input)
    print(json.dumps({"step": "loaded", "rows": len(df), "cols": list(df.columns)}, ensure_ascii=False))

    # 岗位名称
    title = args.title
    if not title:
        basename = os.path.splitext(os.path.basename(args.input))[0]
        title = basename.replace("jobs_clean", "").replace("_", "").strip()
        if not title:
            title = "未知岗位"
    print(json.dumps({"step": "title", "title": title}, ensure_ascii=False))

    # 分析
    use_claude = args.use_claude and claude_available()

    if use_claude:
        print(json.dumps({"step": "analyze", "message": "正在调用 Claude 进行 JD 语义分析..."}, ensure_ascii=False))
        stats = analyze_jds_with_claude(df, title)
        if stats is None:
            print(json.dumps({"step": "analyze_fallback", "message": "Claude 分析失败，回退到 jieba 模式..."}, ensure_ascii=False))
            seeds = build_seed_keywords(title)
            stats = analyze_jds(df, title, seeds)
    else:
        if args.use_claude and not claude_available():
            print(json.dumps({"step": "claude_unavailable", "message": "ANTHROPIC_API_KEY 未设置，使用 jieba 模式"}, ensure_ascii=False))
        print(json.dumps({"step": "analyze", "message": "正在使用 jieba 分析 JD 文本..."}, ensure_ascii=False))
        seeds = build_seed_keywords(title)
        stats = analyze_jds(df, title, seeds)

    # 生成报告
    print(json.dumps({"step": "report", "message": "正在生成报告..."}, ensure_ascii=False))
    report = generate_report(stats, title)

    # 保存
    if data_dir:
        output = args.output or os.path.join(data_dir, f"subjects/{title}/JD_Analysis_Report.md")
        os.makedirs(os.path.dirname(output), exist_ok=True)
    else:
        output_dir = f"subjects/{title}"
        os.makedirs(output_dir, exist_ok=True)
        output = args.output or f"{output_dir}/JD_Analysis_Report.md"
    with open(output, "w", encoding="utf-8") as f:
        f.write(report)

    from utils.protocol import emit
    emit("done", f"报告已生成: {output}",
         data={"output": output, "total_jobs": stats["overview"]["total_jobs"],
               "top_skills": list(stats["skill_stats"].keys())[:5],
               "edu_summary": list(stats["edu_stats"].keys()) if stats["edu_stats"] else []})


if __name__ == "__main__":
    main()
