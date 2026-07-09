"""技能映射/学习内容/项目模板常量 — 支持 YAML 内容包覆盖"""
from analysis.content_loader import get_content_pack

_content = get_content_pack()

# ── 技能映射 ──

SKILL_RESOURCES = _content.get("SKILL_RESOURCES") or {
    "Python": {"type": "语言", "priority": "必修", "resources": [
        "Python官方教程 docs.python.org",
        "《Python编程从入门到实践》",
    ]},
    "LangChain": {"type": "框架", "priority": "必修", "resources": [
        "LangChain 官方文档 python.langchain.com",
    ]},
    "LangGraph": {"type": "框架", "priority": "必修", "resources": [
        "LangGraph 官方文档 langchain-ai.github.io/langgraph",
    ]},
    "RAG": {"type": "技术", "priority": "必修", "resources": [
        "LangChain RAG 官方教程",
        "向量数据库（ChromaDB / FAISS）入门",
    ]},
    "Prompt": {"type": "技术", "priority": "必修", "resources": [
        "Prompt Engineering Guide (promptingguide.ai)",
    ]},
    "Agent": {"type": "方向", "priority": "核心", "resources": [
        "AutoGPT / MetaGPT 源码阅读",
        "工具调用（Function Calling）实战",
    ]},
    "大模型": {"type": "基础", "priority": "必修", "resources": [
        "《大规模语言模型》复旦大学出版社",
        "HuggingFace NLP Course",
    ]},
    "LLM": {"type": "基础", "priority": "必修", "resources": ["同上（大模型）"]},
    "GPT": {"type": "基础", "priority": "必修", "resources": ["OpenAI API 官方文档"]},
    "Llama": {"type": "基础", "priority": "必修", "resources": [
        "Ollama 官方文档", "llama.cpp GitHub 仓库"]},
    "微调": {"type": "技术", "priority": "进阶", "resources": [
        "HuggingFace PEFT 库", "LoRA / QLoRA 微调教程"]},
    "Java": {"type": "语言", "priority": "选学", "resources": ["《Java核心技术》卷I"]},
    "Go": {"type": "语言", "priority": "选学", "resources": ["Go Tour (go.dev/tour)"]},
    "Kubernetes": {"type": "工具", "priority": "了解", "resources": ["K8s 官方入门教程"]},
    "Docker": {"type": "工具", "priority": "选学", "resources": ["Docker 官方 Get Started"]},
    "对话": {"type": "技术", "priority": "必修", "resources": [
        "Rasa 官方文档", "对话系统设计模式"]},
    "GitHub": {"type": "工具", "priority": "了解", "resources": [
        "GitHub 官方文档", "GitHub Flow 指南"]},
    "Python基础": {"type": "语言", "priority": "必修", "resources": [
        "《Python编程从入门到实践》", "Python官方Tutorial docs.python.org"]},
    "数据结构": {"type": "基础", "priority": "必修", "resources": [
        "《剑指Offer》", "LeetCode 热题100"]},
    "算法": {"type": "基础", "priority": "必修", "resources": ["LeetCode", "《算法导论》精选章节"]},
    "SQL": {"type": "技术", "priority": "必修", "resources": [
        "SQLZoo 在线练习", "《SQL必知必会》"]},
    "数据库": {"type": "技术", "priority": "必修", "resources": ["同上 SQL"]},
    "PyTorch": {"type": "框架", "priority": "必修", "resources": [
        "PyTorch 官方教程 pytorch.org/tutorials", "d2l.ai 李沐动手学深度学习"]},
    "AI基础": {"type": "基础", "priority": "必修", "resources": [
        "吴恩达《AI For Everyone》", "李开复《AI·未来》"]},
    "数据分析": {"type": "技术", "priority": "必修", "resources": [
        "《利用Python进行数据分析》", "Kaggle Learn 数据分析微课程"]},
    "Linux": {"type": "工具", "priority": "选学", "resources": [
        "《鸟哥的Linux私房菜》基础篇", "missing.csail.mit.edu"]},
    "NLP": {"type": "方向", "priority": "核心", "resources": [
        "HuggingFace NLP Course", "《Speech and Language Processing》Jurafsky"],
        },
    "BERT": {"type": "模型", "priority": "必修", "resources": [
        "BERT 原论文", "HuggingFace 文本分类教程"]},
    "Transformer": {"type": "模型", "priority": "必修", "resources": [
        "《Attention Is All You Need》", "The Annotated Transformer"]},
    "计算机视觉": {"type": "方向", "priority": "核心", "resources": [
        "CS231n 斯坦福课程", "d2l.ai 计算机视觉章节"]},
    "YOLO": {"type": "模型", "priority": "必修", "resources": [
        "Ultralytics YOLOv8 文档", "YOLO 原论文"]},
    "OpenCV": {"type": "库", "priority": "必修", "resources": [
        "OpenCV 官方教程 docs.opencv.org"]},
    "语音识别": {"type": "技术", "priority": "必修", "resources": [
        "OpenAI Whisper GitHub", "HuggingFace 语音教程"]},
    "TTS": {"type": "技术", "priority": "必修", "resources": [
        "Coqui TTS GitHub", "VITS 论文"]},
    "多模态": {"type": "方向", "priority": "核心", "resources": [
        "CLIP 原论文", "LLaVA 论文与代码", "HuggingFace 多模态教程"]},
    "MLOps": {"type": "方向", "priority": "核心", "resources": [
        "MLflow 官方文档", "Kubeflow 入门教程"]},
    "推荐系统": {"type": "方向", "priority": "核心", "resources": [
        "《推荐系统实践》项亮", "d2l.ai 推荐系统章节"]},
}

# 技能名称 → WEEKLY_PLANS 中对应 theme 的映射
SKILL_TO_THEME = _content.get("SKILL_TO_THEME") or {
    "Python": "Python 高级特性",
    "LangChain": "LangChain 核心组件",
    "Prompt": "Prompt 工程",
    "RAG": "RAG 与向量数据库",
    "LangGraph": "LangGraph 基础",
    "Agent": "Agent 全流程实战",
    "Function Calling": "Function Calling 与工具调用",
    "Memory": "Agent 记忆与长期记忆",
    "微调": "微调",
    "Kubernetes": "Kubernetes",
    "对话": "对话系统",
    "NLP": "NLP",
    "Git": "Git 与版本控制",
    "GitHub": "Git 与版本控制",
    "Go": "Go",
    "Java": "Java",
    "大模型": "LLM 与大模型基础",
    "LLM": "LLM 与大模型基础",
    "GPT": "LLM 与大模型基础",
    "Llama": "LLM 与大模型基础",
    "Docker": "生产级部署",
    "TypeScript": "TypeScript",
    "C++": "C++ 基础",
    "微服务": "微服务架构",
    "Python基础": "Python 基础编程",
    "编程基础": "Python 基础编程",
    "Python入门": "Python 基础编程",
    "数据结构": "数据结构与算法",
    "算法": "数据结构与算法",
    "LeetCode": "数据结构与算法",
    "SQL": "数据库与 SQL",
    "MySQL": "数据库与 SQL",
    "数据库": "数据库与 SQL",
    "PostgreSQL": "数据库与 SQL",
    "PyTorch": "PyTorch 框架实战",
    "PyTorch框架": "PyTorch 框架实战",
    "AI基础": "AI 通识入门",
    "人工智能基础": "AI 通识入门",
    "AI概念": "AI 通识入门",
    "数据分析": "数据分析与可视化",
    "数据可视化": "数据分析与可视化",
    "pandas": "数据分析与可视化",
    "Linux": "Linux 与命令行",
    "Shell": "Linux 与命令行",
    "命令行": "Linux 与命令行",
    # ── NLP 方向 ──
    "NLP基础": "NLP",
    "文本分类": "NLP",
    "NER": "NLP",
    "命名实体识别": "NLP",
    "词向量": "NLP",
    "Word2Vec": "NLP",
    "文本生成": "NLP",
    "文本摘要": "NLP",
    "情感分析": "NLP",
    "BERT": "NLP",
    "Transformer": "NLP",
    "LSTM": "NLP",
    "机器翻译": "NLP",
    "jieba": "NLP",
    "spaCy": "NLP",
    # ── 计算机视觉方向 ──
    "计算机视觉": "计算机视觉",
    "CV": "计算机视觉",
    "图像分类": "计算机视觉",
    "目标检测": "计算机视觉",
    "YOLO": "计算机视觉",
    "图像分割": "计算机视觉",
    "OpenCV": "计算机视觉",
    "图像处理": "计算机视觉",
    "CNN": "计算机视觉",
    "ResNet": "计算机视觉",
    "图像生成": "计算机视觉",
    "扩散模型": "计算机视觉",
    "视频理解": "计算机视觉",
    "行为识别": "计算机视觉",
    "ONNX": "计算机视觉",
    "TensorRT": "计算机视觉",
    # ── 语音技术方向 ──
    "语音识别": "语音技术",
    "ASR": "语音技术",
    "TTS": "语音技术",
    "语音合成": "语音技术",
    "语音": "语音技术",
    "Whisper": "语音技术",
    "声纹识别": "语音技术",
    "说话人分离": "语音技术",
    "语音增强": "语音技术",
    "语音情感": "语音技术",
    # ── 多模态方向 ──
    "多模态": "多模态大模型",
    "CLIP": "多模态大模型",
    "VLM": "多模态大模型",
    "视觉问答": "多模态大模型",
    "文生图": "多模态大模型",
    "文生视频": "多模态大模型",
    "Stable Diffusion": "多模态大模型",
    "LLaVA": "多模态大模型",
    # ── MLOps 方向 ──
    "MLOps": "MLOps 与模型运维",
    "模型部署": "MLOps 与模型运维",
    "模型监控": "MLOps 与模型运维",
    "MLflow": "MLOps 与模型运维",
    "Airflow": "MLOps 与模型运维",
    "Kubeflow": "MLOps 与模型运维",
    "模型漂移": "MLOps 与模型运维",
    "Triton": "MLOps 与模型运维",
    # ── 推荐系统方向 ──
    "推荐系统": "推荐系统",
    "协同过滤": "推荐系统",
    "DeepFM": "推荐系统",
    "召回": "推荐系统",
    "排序": "推荐系统",
    "多目标": "推荐系统",
    "冷启动": "推荐系统",
    "序列推荐": "推荐系统",
}

THEME_TO_SKILL = _content.get("THEME_TO_SKILL") or {v: k for k, v in SKILL_TO_THEME.items()}

# 周计划 → 阶段映射
WEEK_PHASE_MAP = _content.get("WEEK_PHASE_MAP") or {
    "Python 高级特性": 1, "LangChain 核心组件": 1, "Prompt 工程": 1, "RAG 与向量数据库": 1,
    "LLM 与大模型基础": 1, "Git 与版本控制": 1,
    "LangGraph 基础": 2, "Function Calling 与工具调用": 2, "Agent 记忆与长期记忆": 2,
    "Multi-Agent 协作": 2, "微调": 2, "对话系统": 2, "NLP": 2,
    "Kubernetes": 2, "微服务架构": 2,
    "Agent 系统架构设计": 3, "生产级部署": 3, "项目打磨与作品集": 3,
    "Agent 全流程实战": 2,
    "Python 基础编程": 1,
    "数据结构与算法": 2,
    "数据库与 SQL": 1,
    "PyTorch 框架实战": 2,
    "AI 通识入门": 1,
    "数据分析与可视化": 2,
    "Linux 与命令行": 1,
    "计算机视觉": 2,
    "语音技术": 2,
    "多模态大模型": 2,
    "MLOps 与模型运维": 2,
    "推荐系统": 2,
}

# 技能 → 难度等级映射
SKILL_DIFFICULTY = {
    "Python": "fundamental", "LangChain": "fundamental", "Prompt": "fundamental",
    "RAG": "fundamental", "LLM": "fundamental", "大模型": "fundamental",
    "微调": "advanced", "LangGraph": "advanced", "Agent": "advanced",
    "对话": "fundamental", "NLP": "fundamental",
    "Function Calling": "advanced", "Memory": "advanced",
    "Kubernetes": "advanced", "Docker": "fundamental",
    "Git": "fundamental", "Java": "fundamental", "Go": "fundamental",
    "GPT": "fundamental", "Llama": "fundamental",
    "GitHub": "fundamental", "TypeScript": "fundamental", "C++": "advanced",
    "微服务": "advanced",
    "Python基础": "fundamental",
    "数据结构": "fundamental",
    "算法": "advanced",
    "SQL": "fundamental",
    "数据库": "fundamental",
    "PyTorch": "advanced",
    "AI基础": "fundamental",
    "数据分析": "fundamental",
    "Linux": "fundamental",
    "BERT": "advanced",
    "Transformer": "advanced",
    "情感分析": "fundamental",
    "文本生成": "advanced",
    "NER": "advanced",
    "YOLO": "advanced",
    "ResNet": "advanced",
    "图像分割": "advanced",
    "OpenCV": "fundamental",
    "ASR": "advanced",
    "TTS": "advanced",
    "Whisper": "advanced",
    "CLIP": "advanced",
    "VLM": "advanced",
    "多模态": "advanced",
    "MLOps": "advanced",
    "MLflow": "fundamental",
    "协同过滤": "fundamental",
    "DeepFM": "advanced",
}

# ── 前置依赖映射 ──
THEME_PREREQUISITES = _content.get("THEME_PREREQUISITES") or {
    "LangChain 核心组件": ["Python 高级特性"],
    "Prompt 工程": ["Python 高级特性"],
    "RAG 与向量数据库": ["LangChain 核心组件", "Prompt 工程"],
    "LangGraph 基础": ["LangChain 核心组件"],
    "Function Calling 与工具调用": ["LangChain 核心组件"],
    "Agent 记忆与长期记忆": ["LangChain 核心组件", "LangGraph 基础"],
    "Multi-Agent 协作": ["LangGraph 基础", "Function Calling 与工具调用"],
    "Agent 全流程实战": ["LangChain 核心组件", "LangGraph 基础"],
    "Agent 系统架构设计": ["Multi-Agent 协作", "Agent 记忆与长期记忆"],
    "生产级部署": ["RAG 与向量数据库", "Agent 全流程实战"],
    "项目打磨与作品集": ["Agent 系统架构设计", "生产级部署"],
    "微调": ["RAG 与向量数据库"],
    "Kubernetes": ["Docker"],
    "对话系统": ["NLP"],
    "LLM 与大模型基础": [],
    "Git 与版本控制": [],
    "微服务架构": ["生产级部署"],
    "Python 基础编程": [],
    "数据结构与算法": ["Python 基础编程"],
    "数据库与 SQL": [],
    "PyTorch 框架实战": ["Python 高级特性", "LLM 与大模型基础"],
    "AI 通识入门": [],
    "数据分析与可视化": ["Python 基础编程"],
    "Linux 与命令行": [],
    "NLP": ["LLM 与大模型基础"],
    "计算机视觉": ["LLM 与大模型基础"],
    "语音技术": ["LLM 与大模型基础"],
    "多模态大模型": ["LLM 与大模型基础", "计算机视觉"],
    "MLOps 与模型运维": ["生产级部署"],
    "推荐系统": ["LLM 与大模型基础"],
}

# ── 持续时间内置项目/开源数量映射 ──
PROJECT_SCALE = _content.get("PROJECT_SCALE") or {30: (2, 1), 60: (4, 2), 90: (6, 5)}

# ── 项目模板 ──






# ── 补充模块池 ──
SUPPLEMENT_POOL = [
    {
        "id": "multi_agent",
        "name": "Multi-Agent 协作",
        "label": "【拓展选修 - 行业趋势】",
        "market_category": "大模型/LLM",
        "condition_type": "B",
        "condition_fn": lambda report_data: any("multi" in s.lower() for s, _ in report_data.get("top_skills", [])),
        "goal": "掌握多 Agent 通信、任务分配、结果聚合",
        "hours": 23,
        "phase": 2,
        "week": 8,
        "theme": "Multi-Agent 协作",
        "days": [
            ("Day 1", "Multi-Agent 架构模式", "用「一个项目组：PM + 开发 + 测试」类比多 Agent 架构", "阅读 AutoGPT / MetaGPT 架构，对比不同模式", "3h"),
            ("Day 2", "Agent 间通信机制", "解释「Agent 之间怎么传递消息」", "实现两个 Agent 的简单对话通信", "3h"),
            ("Day 3", "任务分解与分配", "类比「项目经理拆解任务给组员」", "实现 Supervisor Agent 分配任务给 Worker Agent", "4h"),
            ("Day 4", "结果聚合与冲突解决", "解释「多个 Agent 结果冲突怎么办」", "实现投票/加权/择优三种聚合策略", "3h"),
            ("Day 5", "多 Agent 调试与监控", "说明「多 Agent = 多线程调试难题」", "给 Agent 流程添加日志和可视化", "3h"),
            ("Day 6", "项目实战：多Agent 调研助手", "费曼：向同学解释这种架构为什么更适合复杂任务", "搭建一个「搜索→分析→总结→报告」的多 Agent 系统", "4h"),
            ("Day 7", "休息", "", "", "0h"),
        ]
    },
    {
        "id": "system_arch",
        "name": "Agent 系统架构设计",
        "label": "【优势深化 - 画像匹配】",
        "market_category": "大模型/LLM",
        "condition_type": "C",
        "condition_fn": lambda profile: any(k in (tag or "") for tag in profile.get("strength_tags", []) for k in ["学习", "探索", "架构", "设计"]),
        "goal": "从代码走向架构，理解生产级 Agent 系统设计",
        "hours": 20,
        "phase": 3,
        "week": 9,
        "theme": "Agent 系统架构设计",
        "days": [
            ("Day 1", "系统架构设计原则", "解释「好的架构不是为了炫技，而是为了少改代码」", "画出 Agent 系统架构图（模块/接口/数据流）", "3h"),
            ("Day 2", "可扩展 Agent 框架设计", "类比「乐高积木」解释可插拔架构", "设计一个支持动态添加工具的 Agent 框架", "4h"),
            ("Day 3", "性能优化策略", "解释「哪三步可以让 Agent 响应速度翻倍」", "对现有 Agent 做性能分析 + 优化", "3h"),
            ("Day 4", "错误处理与降级策略", "类比「飞机引擎故障还有备用方案」的容错设计", "给 Agent 添加完整错误处理 + 降级逻辑", "3h"),
            ("Day 5", "安全与权限设计", "解释「为什么 Agent 不能直接执行 shell 命令」", "实现 Agent 安全沙箱 / 权限分级", "3h"),
            ("Day 6", "架构评审（费曼输出）", "费曼：向技术面试官介绍你的 Agent 架构设计", "写一篇 Agent 系统架构设计文档", "4h"),
            ("Day 7", "休息", "", "", "0h"),
        ]
    },
    {
        "id": "production_deploy",
        "name": "生产级部署",
        "label": "【拓展选修 - 行业趋势】",
        "market_category": "云原生/DevOps",
        "condition_type": "B",
        "condition_fn": lambda report_data: any(k in " ".join(s for s, _ in report_data.get("top_skills", [])) for k in ["Docker", "Kubernetes", "部署"]),
        "goal": "掌握 Docker + 简单后端部署，让 Agent 项目可访问",
        "hours": 18,
        "phase": 3,
        "week": 10,
        "theme": "生产级部署",
        "days": [
            ("Day 1", "Docker 基础", "用「打包行李」类比 Docker 镜像和容器", "写 Dockerfile 打包一个 Python Agent 应用", "3h"),
            ("Day 2", "Docker Compose", "类比「一套乐高说明」解释 Compose 多容器编排", "用 Compose 编排 Agent + Redis + API 三个服务", "3h"),
            ("Day 3", "API 服务搭建（FastAPI）", "解释 API 就像「餐厅菜单」告诉别人你能提供什么", "用 FastAPI 为 Agent 搭建 REST API", "3h"),
            ("Day 4", "部署到云服务", "对比几种部署方式：云服务器 vs Serverless", "将 Agent 部署到 Render / Railway 等免费平台", "4h"),
            ("Day 5", "日志与监控", "解释「没有日志 = 闭着眼睛开车」", "为 Agent 添加结构化日志输出", "2h"),
            ("Day 6", "部署文档", "费曼：写一份部署指南，假设读者没做过 DevOps", "完成项目的 README + 部署文档", "3h"),
            ("Day 7", "休息", "", "", "0h"),
        ]
    },
    {
        "id": "portfolio",
        "name": "项目打磨与作品集",
        "label": "【优势深化 - 画像匹配】",
        "market_category": "综合",
        "condition_type": "C",
        "condition_fn": lambda profile: any(tag in (profile.get("strength_tags") or []) for tag in ["学习速度快", "喜欢探索未知"]) or profile.get("ai_experience_level") in ("有AI项目经验", "AI领域资深从业者"),
        "goal": "将之前项目完善为可展示的作品集",
        "hours": 21,
        "phase": 3,
        "week": 11,
        "theme": "项目打磨与作品集",
        "days": [
            ("Day 1", "项目复盘：RAG 问答系统", "如果重构一次，哪里可以做得更好？", "重构 RAG 项目，添加缓存 + 批处理", "4h"),
            ("Day 2", "项目复盘：多Agent 系统", "这个项目的技术亮点是什么？怎么在面试中讲清楚", "优化多 Agent 通信效率，添加进度展示", "4h"),
            ("Day 3", "项目三选一：新功能开发", "想清楚这个新功能解决什么真实问题", "为选定项目添加 1 个核心新功能", "4h"),
            ("Day 4", "编写项目 README", "README 就是项目的「第一印象」", "写完整的 README：背景/架构/用法/演示截图", "3h"),
            ("Day 5", "制作演示 Demo", "录屏 Demo 展示要比文字有力得多", "录制 3-5 分钟项目演示视频/prepare 截图", "3h"),
            ("Day 6", "作品集整合", "准备一份「项目亮点清单」——每个项目 3 句话", "整理 2-3 个项目到简历/作品集", "3h"),
            ("Day 7", "休息", "", "", "0h"),
        ]
    },
]

# ── 技术内容与技能变现映射 ──

CONTENT_MAPPING = _content.get("CONTENT_MAPPING") or {
    "Python 高级特性": {"title": "Python 进阶实战：async/await 与装饰器模式", "type": "实操指南"},
    "LangChain 核心组件": {"title": "LangChain 入门：四大核心组件（Chain/Memory/Retriever/Agent）详解", "type": "技术教程"},
    "Prompt 工程": {"title": "Prompt Engineering 完全指南：从 Few-shot 到 CoT", "type": "技术教程"},
    "RAG 与向量数据库": {"title": "从0到1搭建 RAG 知识库问答系统（含完整代码）", "type": "技术教程"},
    "LangGraph 基础": {"title": "LangGraph 入门：用状态图构建 Agent 工作流", "type": "技术教程"},
    "Function Calling 与工具调用": {"title": "Function Calling 深度解析：Tool Use 的底层原理与实践", "type": "深度分析"},
    "Agent 记忆与长期记忆": {"title": "Agent 记忆机制全解：4种记忆模式的实现与选型对比", "type": "技术教程"},
    "Multi-Agent 协作": {"title": "Multi-Agent 协作实战：设计一个多智能体调研助手系统", "type": "技术教程"},
    "Agent 系统架构设计": {"title": "生产级 Agent 系统架构设计：模块/接口/数据流", "type": "深度分析"},
    "生产级部署": {"title": "Docker + FastAPI：AI Agent 项目部署实战指南", "type": "实操指南"},
    "项目打磨与作品集": {"title": "AI 开发者作品集建设：如何让项目脱颖而出", "type": "学习笔记"},
    "LLM 与大模型基础": {"title": "LLM 与大模型基础：从原理到实践", "type": "深度分析"},
    "对话系统": {"title": "对话系统设计：意图识别与状态管理", "type": "技术教程"},
    "Git 与版本控制": {"title": "Git 与 GitHub 协作实践指南", "type": "实操指南"},
    "微服务架构": {"title": "微服务架构：从单体到服务拆分", "type": "深度分析"},
    "Python 基础编程": {"title": "Python 零基础入门：从安装到写第一个脚本", "type": "实操指南"},
    "数据结构与算法": {"title": "面试必备：数据结构与算法核心 20 讲", "type": "学习笔记"},
    "数据库与 SQL": {"title": "SQL 从入门到进阶：数据库查询与设计实战", "type": "技术教程"},
    "PyTorch 框架实战": {"title": "PyTorch 实战：从张量到模型部署完整教程", "type": "技术教程"},
    "AI 通识入门": {"title": "AI 通识课：零基础读懂人工智能", "type": "学习笔记"},
    "数据分析与可视化": {"title": "数据分析师入门：Python 数据分析完整工作流", "type": "技术教程"},
    "Linux 与命令行": {"title": "Linux 命令行实战：开发者必会的 20 个命令", "type": "实操指南"},
    "NLP": {"title": "NLP 入门到进阶：从词向量到预训练模型", "type": "技术教程"},
    "计算机视觉": {"title": "计算机视觉实战：从图像分类到目标检测", "type": "技术教程"},
    "语音技术": {"title": "语音技术入门：ASR/TTS/声纹识别实战指南", "type": "技术教程"},
    "多模态大模型": {"title": "多模态大模型：CLIP/VLM/文生图原理与实践", "type": "深度分析"},
    "MLOps 与模型运维": {"title": "MLOps 实战：从模型训练到生产部署的完整工作流", "type": "技术教程"},
    "推荐系统": {"title": "推荐系统核心算法与工程实战", "type": "技术教程"},
}

PROJECT_CONTENT = _content.get("PROJECT_CONTENT") or {
    "title": "RAG 知识库从设计到部署：完整项目复盘与技术拆解",
    "type": "技术教程",
}

PLATFORM_INFO = _content.get("PLATFORM_INFO") or {
    "抖音": "60s竖屏短视频",
    "哔哩哔哩": "5-15min中长视频",
    "小红书": "图文笔记",
    "知乎": "深度长文",
    "博客": "完整教程（自主阵地）",
    "掘金": "技术实战",
}

PLATFORM_TEMPLATES = _content.get("PLATFORM_TEMPLATES") or {
    "技术教程": {
        "抖音": "60s速通：{}核心知识点",
        "哔哩哔哩": "从0到1手把手：{}完整教程",
        "小红书": "{}入门必备清单｜附学习路线",
        "知乎": "{}完全指南：从入门到进阶",
        "博客": "{}保姆级教程：原理+代码+实战",
        "掘金": "{}实战教程：手把手带你实现核心功能",
    },
    "实操指南": {
        "抖音": "{}实操演示｜看完就能动手",
        "哔哩哔哩": "{}实操跟做：一步步搭建你的第一个项目",
        "小红书": "{}实操笔记｜5步搞定核心功能",
        "知乎": "{}实操全记录：踩坑与解决方案",
        "博客": "{}完整实操指南：从环境搭建到部署上线",
        "掘金": "{}踩坑实录：生产环境实战经验总结",
    },
    "深度分析": {
        "抖音": "1分钟讲透{}核心原理",
        "哔哩哔哩": "{}深度解析：原理、架构与最佳实践",
        "小红书": "{}深度科普｜看完秒懂核心逻辑",
        "知乎": "{}深度拆解：从底层原理到上层应用",
        "博客": "{}完全拆解：问题本质→核心原理→设计取舍",
        "掘金": "{}源码级分析：深入理解内部机制",
    },
    "学习笔记": {
        "抖音": "{}学习路线｜30天从零入门",
        "哔哩哔哩": "我的{}学习笔记：完整知识体系梳理",
        "小红书": "{}学习笔记｜核心知识点一张图总结",
        "知乎": "{}学习心得：从入门到实践的全过程记录",
        "博客": "{}学习笔记与项目复盘：理解、实践与思考",
        "掘金": "{}知识体系总结：核心概念与项目实战梳理",
    },
}

MONETIZATION_PATHS = _content.get("MONETIZATION_PATHS") or [
    {
        "match": ["LangChain", "RAG"],
        "title": "企业 RAG 知识库问答系统定制",
        "channels": "Upwork / 程序员客栈 / 行业技术外包群",
        "price_30": "基础版搭建 3000-8000元",
        "price_60": "完整系统 8000-20000元",
        "price_90": "企业级方案 15000-50000元",
    },
    {
        "match": ["LangGraph", "Agent"],
        "title": "Agent 智能体工作流开发",
        "channels": "Fiverr / 技术社区 / AI 创业团队合作",
        "price_60": "5000-15000元（单个 Agent 工作流）",
        "price_90": "15000-40000元（多 Agent 协作系统）",
    },
    {
        "match": ["Function Calling"],
        "title": "工具调用与 API 集成开发",
        "channels": "Upwork / 自由开发者平台",
        "price_60": "3000-10000元（工具定义+集成）",
        "price_90": "8000-20000元（复杂工具链编排）",
    },
    {
        "match": ["Memory"],
        "title": "对话系统与记忆方案设计",
        "channels": "知乎付费咨询 / 知识星球 / 行业顾问",
        "price_60": "3000-8000元（单系统记忆方案）",
        "price_90": "8000-20000元（完整记忆架构）",
    },
    {
        "match": ["Prompt"],
        "title": "Prompt Engineering 优化咨询",
        "channels": "在行 / 知乎付费咨询 / 技术培训",
        "price_30": "2000-5000元（Prompt 模板设计）",
        "price_60": "5000-10000元（完整 Prompt 体系搭建）",
        "price_90": "10000-25000元（企业级 Prompt 工程培训）",
    },
    {
        "match": ["架构", "部署"],
        "title": "AI 系统架构设计与技术顾问",
        "channels": "在行 / 技术顾问平台 / 创业公司合作",
        "price_90": "20000-80000元（系统架构设计+技术选型）",
    },
    {
        "match": ["Python", "部署"],
        "title": "Python + FastAPI 后端 API 开发",
        "channels": "程序员客栈 / 码市 / Upwork",
        "price_60": "5000-15000元（API 开发+部署）",
        "price_90": "10000-30000元（完整后端系统）",
    },
]

# ── 每周学习模板（13周 + 综合项目周） ──



PROJECT_WEEK = _content.get("PROJECT_WEEK") or {
    "phase": 1, "phase_name": "基础夯实期",
    "extra_week": {
        "week": 5, "theme": "综合项目：RAG 知识库问答系统",
        "goal": "独立完成一个完整项目，综合运用前 4 周所学",
        "days": [
            ("Day 1", "需求分析与架构设计", "用「盖房子要先画图纸」解释设计阶段的重要性",
             "画出项目架构图，列出技术选型清单", "3h"),
            ("Day 2", "数据采集与处理", "解释数据质量对 RAG 效果的影响",
             "实现文档加载 → 分割 → 清洗管线", "4h"),
            ("Day 3", "向量库构建与检索", "对比不同分块策略对检索效果的影响",
             "实现向量库构建 + 检索效果对比实验", "4h"),
            ("Day 4", "LLM 生成集成", "解释「检索到的内容怎么变成答案」",
             "实现 RAG 问答接口 + Prompt 模板", "3h"),
            ("Day 5", "UI / API 包装", "API 接口就像自动售货机的按键面板",
             "用 Gradio / FastAPI 搭建交互界面", "3h"),
            ("Day 6", "测试与优化", "解释「没有测试的代码=没有安全带的车」",
             "写单元测试 + 端到端测试 + 优化", "4h"),
            ("Day 7", "项目复盘", "费曼：完整讲解一遍项目架构和实现",
             "完成项目文档，上传 GitHub", "3h"),
        ]
    }
}

# ── 市场技能对应周模板 ──



# ── 填充内容库：当合并后天数仍有剩余时间时使用 ──

_FILLER_BLOCKS = _content.get("_FILLER_BLOCKS") or {
    "study": [
        ("复习", "回顾昨日费曼笔记和「待回炉」标记", 0.3),
        ("深入", "官方文档/源码指定章节：「{topic}」", 0.5),
        ("实践", "不参考笔记重新实现核心代码路径", 0.5),
        ("检验", "闭卷回答3个关于「{topic}」的核心问题", 0.3),
        ("拓展", "社区最佳实践/相关论文/关联技术对比", 0.5),
    ],
    "project": [
        ("复习", "浏览已完成模块确认进展", 0.3),
        ("优化", "重构/性能调优/增加注释", 0.5),
        ("实践", "添加1个辅助功能", 0.5),
        ("检验", "运行所有测试记录失败项", 0.3),
        ("文档", "更新README/架构图/使用说明", 0.5),
    ],
    "review": [
        ("串联", "用一段大白话串联本阶段所有核心概念", 0.3),
        ("图谱", "画出当前阶段的知识点关系图", 0.5),
        ("检验", "逐一检查所有「待回炉」标记", 0.5),
        ("笔记", "归档费曼输出标记理解置信度", 0.3),
    ],
    "os_contribution": [
        ("探索", "浏览项目issue区了解社区动态", 0.3),
        ("学习", "阅读贡献指南和代码规范", 0.5),
        ("实践", "在本地环境复现目标issue", 0.5),
    ],
    "supplement": [
        ("复习", "回顾与本模块相关的已学知识", 0.3),
        ("深化", "对比本模块与核心技能的异同", 0.5),
        ("产出", "写一段话总结本模块的价值和局限", 0.3),
    ],
}
