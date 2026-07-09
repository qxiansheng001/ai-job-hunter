"""文件读写工具函数"""

import json
import re


def load_profile(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_report(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    data = {}
    m = re.search(r'\*\*样本总量\*\*[：:]\s*(\d+)', text)
    if m: data["total_jobs"] = int(m.group(1))
    m = re.search(r'\*\*涉及公司\*\*[：:]\s*(\d+)', text)
    if m: data["total_companies"] = int(m.group(1))

    mention_rows = re.findall(r'\|\s*\d+\s*\|\s*(\S+)\s*\|\s*([\d.]+)%\s*\|\s*(\d+)', text)
    if mention_rows:
        data["mention_rates"] = {s: float(r) for s, r, c in mention_rows}
        data["top_skills"] = [(s, int(c)) for s, r, c in mention_rows]
        all_by_rate = sorted(data["mention_rates"].items(), key=lambda x: -x[1])
        data["essential_skills"] = [(s, r) for s, r in all_by_rate if r >= 30.0]
        data["bonus_skills"] = [(s, r) for s, r in all_by_rate if 10.0 <= r < 30.0]
    else:
        skills = re.findall(r'\|\s*\d+\s*\|\s*(\S+)\s*\|\s*(\d+)\s*次', text)
        data["top_skills"] = [(s, int(c)) for s, c in skills]

    edu = re.findall(r'\|\s*(本科|硕士|博士|大专|学历不限)\s*\|\s*(\d+)', text)
    data["education"] = [(e, int(c)) for e, c in edu]
    return data
