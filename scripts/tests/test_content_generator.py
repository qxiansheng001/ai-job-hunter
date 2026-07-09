"""测试内容生成器核心函数"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
from analysis.content_generator import _select_items_for_user


class TestSelectItemsForUser(unittest.TestCase):
    """_select_items_for_user: 基于用户画像从条目池中筛选最合适的条目"""

    def setUp(self):
        # (title, hint, task, hours, tags_dict)
        self.items = [
            ("入门概念", "hint", "task", 1.0, {"level": "L1", "style": "writing", "prereq": "none"}),
            ("核心实践", "hint", "task", 2.0, {"level": "L2", "style": "technical", "prereq": "basic"}),
            ("高级专题", "hint", "task", 3.0, {"level": "L3", "style": "analytical", "prereq": "advanced"}),
            ("实战项目", "hint", "task", 4.0, {"level": "L2", "style": "practical", "prereq": "intermediate"}),
        ]

    def test_level_match_preferred(self):
        """深度匹配的条目应优先"""
        profile = {"ai_experience_level": "无经验", "education": "本科", "strength_tags": [], "self_drive_score": 2}
        result = _select_items_for_user(self.items, profile, "L2")
        # L2 条目应排在 L1/L3 之前
        self.assertEqual(result[0][0], "核心实践")

    def test_no_experience_prefers_none_prereq(self):
        """无经验用户应优先选择 prereq=none 的条目"""
        profile = {"ai_experience_level": "无经验", "education": "本科", "strength_tags": [], "self_drive_score": 2}
        items = [
            ("有前置要求", "hint", "task", 1.0, {"level": "L1", "style": "writing", "prereq": "basic"}),
            ("无需前置", "hint", "task", 1.0, {"level": "L1", "style": "writing", "prereq": "none"}),
        ]
        result = _select_items_for_user(items, profile, "L1")
        # 两条目同级，但 "无需前置" 应排前面
        self.assertEqual(result[0][0], "无需前置")

    def test_experienced_prefers_basic_prereq(self):
        """有经验的用户应优先选择 basic/intermediate 的条目"""
        profile = {"ai_experience_level": "有AI项目经验", "education": "本科", "strength_tags": [], "self_drive_score": 2}
        items = [
            ("无需前置", "hint", "task", 1.0, {"level": "L1", "style": "writing", "prereq": "none"}),
            ("有前置要求", "hint", "task", 1.0, {"level": "L1", "style": "writing", "prereq": "basic"}),
        ]
        result = _select_items_for_user(items, profile, "L1")
        self.assertEqual(result[0][0], "有前置要求")

    def test_self_drive_bonus(self):
        """高自驱力 (>=4) 给 practical 和 technical 风格加分"""
        profile = {"ai_experience_level": "无经验", "education": "本科", "strength_tags": [], "self_drive_score": 4.5}
        items = [
            ("写作任务", "hint", "task", 1.0, {"level": "L2", "style": "writing", "prereq": "none"}),
            ("实践任务", "hint", "task", 1.0, {"level": "L2", "style": "practical", "prereq": "none"}),
        ]
        result = _select_items_for_user(items, profile, "L2")
        # 实践任务应排前面（自驱力加分 +2）
        self.assertEqual(result[0][0], "实践任务")

    def test_strength_tag_communication(self):
        """沟通标签 → writing 风格加分"""
        profile = {"ai_experience_level": "无经验", "education": "本科",
                   "strength_tags": ["沟通"], "self_drive_score": 2}
        items = [
            ("技术任务", "hint", "task", 1.0, {"level": "L2", "style": "technical", "prereq": "none"}),
            ("写作任务", "hint", "task", 1.0, {"level": "L2", "style": "writing", "prereq": "none"}),
        ]
        result = _select_items_for_user(items, profile, "L2")
        self.assertEqual(result[0][0], "写作任务")

    def test_senior_experience(self):
        """资深从业者 → intermediate/advanced prereq 加分"""
        profile = {"ai_experience_level": "AI领域资深从业者", "education": "本科",
                   "strength_tags": [], "self_drive_score": 2}
        items = [
            ("入门内容", "hint", "task", 1.0, {"level": "L3", "style": "technical", "prereq": "none"}),
            ("进阶内容", "hint", "task", 1.0, {"level": "L3", "style": "technical", "prereq": "advanced"}),
        ]
        result = _select_items_for_user(items, profile, "L3")
        self.assertEqual(result[0][0], "进阶内容")


if __name__ == "__main__":
    unittest.main()
