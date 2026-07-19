"""省份-城市编码映射模块。

用于跨省搜索时确定代表城市和编码。
BOSS直聘城市编码格式: 101 + XX + XXXX，XX=省级代码
"""

import sys

# 省份 → 城市编码列表（取省会/主要城市）
PROVINCE_CITIES = {
    "北京": ["101010100"],
    "上海": ["101020100"],
    "天津": ["101030100"],
    "重庆": ["101040100"],
    "广东": ["101280100", "101280600"],
    "浙江": ["101210100"],
    "江苏": ["101190100", "101190400"],
    "四川": ["101270100"],
    "湖北": ["101200100"],
    "陕西": ["101110100"],
    "湖南": ["101250100"],
    "福建": ["101230200"],
    "安徽": ["101220100"],
    "河南": ["101180100"],
    "山东": ["101120100", "101120200"],
    "辽宁": ["101130200"],
}

# 反向查找：city_code → province_name
_CITY_TO_PROVINCE = {}
for prov, cities in PROVINCE_CITIES.items():
    for c in cities:
        _CITY_TO_PROVINCE[c] = prov


def get_province_name(city_code):
    """根据城市编码返回省份名称。

    Args:
        city_code: BOSS直聘城市编码，如 "101010100"

    Returns:
        省份名称字符串，未找到时返回 None
    """
    if not city_code or len(city_code) < 5:
        print(f"[province_map] 无效城市编码: {city_code}", file=sys.stderr)
        return None

    name = _CITY_TO_PROVINCE.get(city_code)
    if not name:
        print(f"[province_map] 未识别的城市编码: {city_code}", file=sys.stderr)
    return name


def get_expansion_provinces(target_city, max_provinces=3):
    """返回待扩展的省份列表（排除目标省份）。

    按地理邻近粗略排序：华北 → 华东 → 华南 → 其他。

    Args:
        target_city: 当前搜索的城市编码
        max_provinces: 最多返回几个省份，默认 3

    Returns:
        list[dict]，每个元素 {"name": str, "cities": list[str]}
    """
    current = get_province_name(target_city)
    if not current:
        return []

    # 固定优先级顺序（非目标省份出现越早越好）
    priority = [
        "上海", "北京", "广东", "浙江", "江苏",
        "四川", "湖北", "陕西", "湖南", "山东",
        "福建", "安徽", "河南", "辽宁", "天津", "重庆",
    ]

    result = []
    for prov in priority:
        if prov == current:
            continue
        if prov in PROVINCE_CITIES:
            result.append({
                "name": prov,
                "cities": PROVINCE_CITIES[prov],
            })
            if len(result) >= max_provinces:
                break

    return result
