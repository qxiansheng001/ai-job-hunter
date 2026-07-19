"""中英文岗位名称模糊匹配模块。

提供岗位关键词的同义扩展能力，实现中英文模糊匹配。
"""

JOB_ALIAS_MAP = {
    "prompt engineer": [
        "提示词工程师", "prompt工程师", "AI提示词工程师",
        "提示工程工程师", "prompt工程",
    ],
    "nlp engineer": [
        "NLP工程师", "自然语言处理工程师",
        "NLP算法工程师", "nlp算法工程师",
    ],
    "大模型算法工程师": [
        "大模型算法工程师", "LLM工程师", "大型语言模型工程师",
        "大模型工程师", "大模型应用工程师",
    ],
    "深度学习工程师": [
        "深度学习工程师", "deep learning工程师",
        "DL工程师", "深度神经网络工程师",
    ],
    "AI产品经理": [
        "AI产品经理", "人工智能产品经理",
    ],
    "算法工程师": [
        "算法工程师", "AI算法工程师", "AI工程师",
    ],
    "机器学习工程师": [
        "机器学习工程师", "ML工程师", "machine learning工程师",
        "MLOps工程师", "机器学习平台工程师",
    ],
    "数据工程师": [
        "数据工程师", "大数据工程师", "数据开发工程师",
        "ETL工程师",
    ],
    "计算机视觉工程师": [
        "计算机视觉工程师", "CV工程师", "computer vision工程师",
        "视觉算法工程师",
    ],
    "推荐系统工程师": [
        "推荐系统工程师", "推荐算法工程师", "推荐工程师",
        "广告算法工程师",
    ],
}


def expand_keywords(keyword):
    """扩展岗位关键词为同义中英文列表。

    输入用户选择的岗位名称，返回所有相关搜索关键词。
    原始关键词始终在第一位。
    未匹配到映射时返回 [keyword] 自身。

    Args:
        keyword: 用户选择的岗位名称字符串

    Returns:
        去重后的关键词列表
    """
    kw = keyword.lower().strip()
    if not kw:
        return [keyword]

    result = [keyword]

    # 直接匹配 canonical key
    if kw in JOB_ALIAS_MAP:
        for alias in JOB_ALIAS_MAP[kw]:
            if alias.lower() != kw:
                result.append(alias)

    # 匹配 alias value（用户输入可能是别名）
    else:
        for canonical, aliases in JOB_ALIAS_MAP.items():
            for alias in aliases:
                if kw == alias.lower():
                    if canonical.lower() != kw:
                        result.append(canonical)
                    for a in aliases:
                        if a.lower() != kw:
                            result.append(a)
                    break
            else:
                continue
            break
        else:
            return [keyword]

    # dict.fromkeys() 去重保留顺序
    return list(dict.fromkeys(result))
