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
DATA_DIR="${AI_JOB_HUNTER_DATA:-../ai-job-hunter-data}"
test -f "$DATA_DIR/.skill-state.json" && echo EXISTS || echo MISSING
```

- **MISSING** → 告知用户"请先完成画像初始化"，调用 `Skill` 工具执行 `job-init`

读取 `$DATA_DIR/.skill-state.json`，提取 profile（tech_stack、education、target_city 等）。

读取 `../../shared-references/role-tiers.md` 参考档位信息。

## Step 1a：方向判定（仅无垂直方向积累的用户）

从 `tech_stack` 和 `ai_projects` 判断用户是否有垂直方向积累。关键词匹配规则：

| 方向 | 匹配关键词 |
|------|-----------|
| NLP | jieba, spaCy, BERT, 文本分类, NLP, 情感分析, NER, Word2Vec, 文本生成 |
| CV | OpenCV, YOLO, 目标检测, 图像分类, 图像分割, CNN, ResNet, 人脸识别 |
| 语音 | Whisper, librosa, torchaudio, ASR, 语音识别, TTS, 语音合成 |
| 多模态 | CLIP, VLM, Stable Diffusion, 多模态, 文生图, 视觉问答 |
| MLOps | MLflow, Docker, K8s, Kubeflow, 模型部署, 监控 |
| 推荐系统 | 协同过滤, DeepFM, 召回, CTR, 推荐系统 |

**有匹配** → 直接跳到 Step 1b，推荐该方向岗位

**无匹配** → 展示方向选择菜单：

```
┌──── 选择你想深入的方向 ─────────────────────────────────────┐
│                                                              │
│  你没有明确的 AI 方向积累，下面是几个主流方向：               │
│                                                              │
│  1. NLP 方向    需要基础：Python + Transformer/BERT          │
│  2. CV 方向     需要基础：Python + OpenCV + CNN              │
│  3. 语音方向    需要基础：Python + 信号处理基础               │
│  4. 多模态方向  需要基础：Python + CLIP/VLM 概念             │
│  5. MLOps 方向  需要基础：Python + Docker/K8s 基础           │
│  6. 推荐系统    需要基础：Python + 数据分析基础               │
│  7. 通用方向    (默认) LLM应用开发、RAG、Agent              │
│                                                              │
│  选一个方向后，我会基于你的选择推荐对应岗位并抓取数据。       │
│  方向也可以后期在画像中修改。                                 │
└────────────────────────────────────────────────────────────┘
```

用户选择后，将方向写入状态文件：

```bash
DATA_DIR="${AI_JOB_HUNTER_DATA:-../ai-job-hunter-data}"
python -c "
import json
with open('$DATA_DIR/.skill-state.json') as f: state = json.load(f)
state.setdefault('profile', {})['vertical_direction'] = '用户选择的编号'
with open('$DATA_DIR/.skill-state.json', 'w') as f: json.dump(state, f, ensure_ascii=False, indent=2)
print('OK')
"
```

## Step 1b：推荐岗位

根据用户画像和方向推荐 **6 个**最匹配的 AI 岗位。方向→岗位关键词映射：

| 方向 | 推荐岗位关键词 |
|------|--------------|
| nlp | NLP算法工程师, 文本挖掘, 对话系统, 自然语言处理 |
| cv | 计算机视觉工程师, 图像算法, 感知算法 |
| speech | 语音算法工程师, ASR, 语音识别, 语音合成 |
| multimodal | 多模态算法, VLM, AIGC算法 |
| mlops | MLOps工程师, 模型部署, AI infra |
| recsys | 推荐算法工程师, 搜索推荐, 广告算法 |
| general | AI应用开发, LLM工程, RAG工程师, Agent开发 |

使用以下格式：

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

## Step 2：用户选择

等待用户回复编号或岗位名称。确认后：

1. 向用户确认搜索参数：岗位名称、城市（来自画像）、抓取数量（建议 50 条）
2. 将 `keyword` 和 `city` 写入 `$DATA_DIR/.skill-state.json` 的 `job_search` 字段

## Step 3：BOSS 直聘抓取

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

```bash
python scripts/scraper/boss_scraper.py \
  --keyword "{岗位名称}" \
  --city "{城市编码（全国 100010000，北京 101010100）}" \
  --max-items 50
```

城市编码参考 `../../shared-references/city_codes.md`（如果存在）或使用常用编码。

### 抓取结果

完成后告知用户抓取数量，更新 `$DATA_DIR/.skill-state.json` 的 `job_search` 字段。

## Step 4：数据清洗

```bash
DATA_DIR="${AI_JOB_HUNTER_DATA:-../ai-job-hunter-data}"
python scripts/export/clean_and_export.py \
  --output "$DATA_DIR/subjects/{keyword}/jobs_clean.xlsx"
```

更新 `$DATA_DIR/.skill-state.json`：`job_search.status=done`、`clean_file=$DATA_DIR/subjects/{keyword}/jobs_clean.xlsx`。

## Step 5：下一步

告知用户下一步可以说"分析这些岗位"（→ job-analyze）。
