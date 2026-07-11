"""内容包加载器：从 YAML 文件加载技能映射/学习内容/项目模板"""

import os
import sys

CONTENT_PACK_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "contents",
)


def get_content_pack(pack_dir=None):
    """Load content pack from YAML files in pack_dir.

    Search priority:
    1. pack_dir parameter (from CLI --content-pack)
    2. CONTENT_PACK_DIR environment variable
    3. Default contents/ directory at skill root

    Returns merged dict of all .yaml/.yml files, or empty dict on failure.
    """
    if pack_dir is None:
        pack_dir = os.environ.get("CONTENT_PACK_DIR", CONTENT_PACK_DIR)

    if not pack_dir or not os.path.isdir(pack_dir):
        return {}

    try:
        import yaml
    except ImportError:
        from utils.protocol import emit
        emit("content.load", "缺少 PyYAML 库，内容包将不可用",
             status="warn", stream=sys.stderr)
        return {}

    data = {}
    try:
        for fname in sorted(os.listdir(pack_dir)):
            if not fname.endswith((".yaml", ".yml")):
                continue
            fpath = os.path.join(pack_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if loaded and isinstance(loaded, dict):
                    data.update(loaded)
    except Exception as e:
        from utils.protocol import emit
        emit("content.load", f"内容包加载失败: {e}",
             status="warn", warnings=[str(e)], stream=sys.stderr)
        return {}

    return data
