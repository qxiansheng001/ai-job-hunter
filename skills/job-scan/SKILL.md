---
name: job-scan
description: AI 岗位扫描。推荐岗位 → 用户选择 → BOSS 直聘抓取 → 数据清洗。
  需要先有状态文件（$AI_JOB_HUNTER_DATA/.skill-state.json）且 profile 已就绪。可在 allowed-tools 中调用 job-init。
argument-hint: ""
allowed-tools: Bash(*), Read, Write, Edit, Glob, Skill
---

# /job-scan — 岗位扫描

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

- **MISSING** → 告知用户"请先完成画像初始化"，调用 `Skill` 工具执行 `job-init`

读取 `$DATA_DIR/.skill-state.json`，提取 profile（tech_stack、education、target_city 等）。

读取 SKILL_DIR 下的 `shared-references/role-tiers.md` 参考档位信息。

## Step 1：推荐岗位

根据画像推荐 **6 个**最匹配的 AI 岗位。使用以下格式：

```
┌──── 推荐岗位列表 ──────────────────────────────────────────┐
│                                                              │
│  1. 大模型算法工程师         匹配度: 92%                    │
│     → 你的PyTorch经验+硕士学历高度匹配，大模型方向需求爆发   │
│  ...                                                         │
└────────────────────────────────────────────────────────────┘
```

推荐原则：
- 岗位名称必须是真实市场上存在的
- 匹配度基于：技术栈重合度、学历门槛、经验要求
- 推荐理由要具体，诚实指出局限
- 排除"实习/实习生"类岗位，只推荐正式/校招岗位

## Step 2：用户选择

等待用户回复编号或岗位名称。确认后：

1. 向用户确认搜索参数：岗位名称、城市（来自画像）、抓取数量（建议 50 条）
2. 将 `keyword` 和 `city` 写入 `$DATA_DIR/.skill-state.json` 的 `job_search` 字段

## Step 3A：关键词扩展（模糊匹配）

使用 `job_aliases.py` 将用户选择的岗位名称扩展为中英文同义词，提高搜索结果覆盖率。

```bash
python -c "
import sys
sys.path.insert(0, '$SKILL_DIR/scripts')
from utils.job_aliases import expand_keywords
result = expand_keywords('{用户选择的岗位名称}')
for kw in result:
    print(kw)
"
```

将输出结果收集为逗号分隔的关键词列表。向用户展示即将搜索的所有相关岗位名称。

例如：
> 将搜索以下相关岗位名称：
> - prompt engineer
> - 提示词工程师
> - prompt工程师
> - AI提示词工程师

## Step 3B：BOSS直聘抓取（多关键词）

### 前置检查

检测 Chrome 调试端口：

```bash
python -c "
import urllib.request, json
try:
    r = urllib.request.urlopen('http://127.0.0.1:9222/json/version', timeout=3)
    print('READY')
except: print('NOT_READY')
"
```

**未就绪**则自动启动 Chrome：

```bash
python -c "
import subprocess, os, time, urllib.request, json, sys
import platform
_chrome_paths = {
    'Windows': r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    'Darwin': '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
}
chrome = _chrome_paths.get(platform.system(), 'google-chrome')
profile = os.path.expanduser(r'~\.ai-job-hunter-chrome')
os.makedirs(profile, exist_ok=True)
subprocess.Popen([chrome,
    '--remote-debugging-port=9222',
    f'--user-data-dir={profile}',
    '--no-first-run', '--no-default-browser-check',
    '--new-window', 'https://www.zhipin.com'],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for i in range(20):
    time.sleep(1)
    try:
        urllib.request.urlopen('http://127.0.0.1:9222/json/version', timeout=2)
        print('READY')
        sys.exit(0)
    except: pass
print('TIMEOUT')
"
```

**启动后立即停下来告知用户：**

> 请在打开的 Chrome 窗口中登录 BOSS直聘（zhipin.com）。
> **登录后告诉我"已登录"，我再开始抓取。Claude 必须等待用户明确回复。**

### 执行抓取

使用扩展后的关键词列表，通过 `--keywords` 参数传入（逗号分隔，无需空格）：

```bash
python "$SKILL_DIR/scripts/scraper/boss_scraper.py" \
  --keywords "{关键词1},{关键词2},{关键词3}" \
  --city "{城市编码（全国 100010000，北京 101010100）}" \
  --max-items 50
```

城市编码参考 SKILL_DIR 下的 `shared-references/city_codes.md`。

### 抓取结果

完成后告知用户抓取数量，更新 `$DATA_DIR/.skill-state.json` 的 `job_search` 字段。

## Step 4A：数据清洗 + 条数检查

```bash
python "$SKILL_DIR/scripts/export/clean_and_export.py" \
  --output "$DATA_DIR/subjects/{keyword}/jobs_clean.xlsx" \
  --min-count 25
```

记录命令的 exit code（`$?`）：
- **exit code 0** → 清洗后的数据 ≥ 25 条，跳到 Step 5
- **exit code 2** → 清洗后的数据 < 25 条，继续 Step 4B 跨省份扩展
- **其他 exit code** → 报错退出

更新 `$DATA_DIR/.skill-state.json`：`job_search.status=done`、`clean_file=$DATA_DIR/subjects/{keyword}/jobs_clean.xlsx`。

## Step 4B：跨省份扩展搜索

**仅在 Step 4A exit code 为 2 时执行。**

### 4B-1：分析当前省份和计划扩展省份

```bash
python -c "
import sys, json
sys.path.insert(0, '$SKILL_DIR/scripts')
from utils.province_map import get_province_name, get_expansion_provinces
cur = get_province_name('{城市编码}')
provinces = get_expansion_provinces('{城市编码}', 3)
print(json.dumps({'current_province': cur, 'expansion': provinces}, ensure_ascii=False))
"
```

### 4B-2：向用户展示并确认

根据上一步输出，向用户展示：

> 当前省份「{省份名}」仅找到 {数量} 条岗位信息（目标 25 条）。
> 计划扩展搜索以下省份：{省份1}、{省份2}、{省份3}
> 是否继续跨省搜索？（是/否）

等待用户明确回复。如果用户拒绝，则告知用户数据不足，流程结束。

### 4B-3：逐省搜索

用户确认后，对每个扩展省份：

1. 使用该省份的代表城市编码
2. 使用相同的多关键词（`--keywords`）
3. 设置 `--max-items 30`（每省少抓些）
4. 将原始数据保存到不同临时文件

```bash
python "$SKILL_DIR/scripts/scraper/boss_scraper.py" \
  --keywords "{关键词1},{关键词2},{关键词3}" \
  --city "{省份代表城市编码}" \
  --max-items 30 \
  --output "{临时目录}/{省份名}_raw.json"
```

### 4B-4：合并数据

将各省份的原始数据与最初的原始数据合并为一个 JSON 文件：

- 合并 `list_items` 数组
- 合并 `detail_items` 数组
- 对 `link` 进行全局去重
- 写入合并后的 `raw_data.json`

### 4B-5：重新清洗

```bash
python "$SKILL_DIR/scripts/export/clean_and_export.py" \
  --output "$DATA_DIR/subjects/{keyword}/jobs_clean.xlsx" \
  --min-count 25
```

如果仍然不足 25 条，告知用户实际数量，流程继续（不强求达到 25 条）。
如果已足够或有更多省份待搜索，可继续扩展。

## Step 5：下一步

告知用户下一步可以说"分析这些岗位"（→ job-analyze）。
