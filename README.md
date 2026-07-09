# AI Job Hunter

AI 行业求职助手 — 基于 [Claude Code Skill](https://claude.ai/claude-code) 系统，从画像初始化、岗位扫描到能力差距分析，生成可执行的学习计划。

## 工作流程

```
job-init → job-scan → job-analyze
```

1. **画像初始化** — 采集技术栈、学历、经验等级、每周可投入时间等，判定起点档位
2. **岗位扫描** — 推荐匹配岗位 → 通过 Chrome DevTools Protocol 抓取 BOSS 直聘真实数据 → 清洗导出
3. **分析学习** — JD 市场需求分析 → 能力差距分析 → 生成定制化每日学习计划（含费曼学习法和第一性原理）

## 前置要求

- Python 3.10+
- Google Chrome（用于 BOSS 直聘数据抓取）
- [Claude Code](https://claude.ai/claude-code)

## 安装

```bash
# 克隆到 Claude Code skills 目录
git clone https://github.com/你的用户名/ai-job-hunter.git /path/to/claude-code/skills/ai-job-hunter

# 安装依赖
pip install -r requirements.txt
```

## 使用方法

在 Claude Code 中触发：

> "开始求职" / "帮我找 AI 工作" / "分析 AI 岗位" / "job-hunter"

Claude Code 自动检测进度并路由到对应子 skill。

## 配置

数据目录可通过环境变量配置：

```bash
export AI_JOB_HUNTER_DATA=/path/to/data/dir
```

默认为 skill 目录外的 `../ai-job-hunter-data/`。该目录存放 `.skill-state.json`（个人画像与进度）和 `subjects/`（岗位分析结果）。

## 项目结构

```
scripts/
  scraper/boss_scraper.py       BOSS直聘 CDP 爬虫
  export/clean_and_export.py    数据清洗 → Excel
  analysis/jd_analyzer.py       JD 文本分析 → 报告
  analysis/gap_analyzer/        能力差距分析 → 学习计划
contents/themes.yaml            学习主题数据源（YAML）
shared-references/              参考文件（档位判定、城市编码等）
templates/                      状态文件模板
skills/                         子 skill 定义
```

## Python 依赖

- websockets — Chrome DevTools Protocol 通信
- httpx — HTTP 请求
- pandas + openpyxl — 数据清洗与导出
- jieba — 中文分词
- pyyaml — YAML 配置加载

## License

MIT
