"""测试计划构建器核心函数"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
from analysis.gap_analyzer.plan_builder import determine_skill_depth
from analysis.gap_analyzer.models import PlanOutput


class TestDetermineSkillDepth(unittest.TestCase):
    """determine_skill_depth: 根据提及率和优先级决定技能学习深度"""

    def test_l3_high_mention_essential(self):
        """提及率 >= 60 且必修 → L3"""
        self.assertEqual(determine_skill_depth(80, "必修"), "L3")
        self.assertEqual(determine_skill_depth(60, "必修"), "L3")
        self.assertEqual(determine_skill_depth(60, "核心"), "L3")

    def test_l2_high_mention_bonus(self):
        """提及率 >= 60 但非必修 → L2"""
        self.assertEqual(determine_skill_depth(80, "加分"), "L2")
        self.assertEqual(determine_skill_depth(70, ""), "L2")

    def test_l2_medium_mention(self):
        """提及率 >= 30 → L2"""
        self.assertEqual(determine_skill_depth(45, "必修"), "L2")
        self.assertEqual(determine_skill_depth(30, "加分"), "L2")

    def test_l2_low_mention_essential(self):
        """提及率 < 30 但必修 → L2"""
        self.assertEqual(determine_skill_depth(15, "必修"), "L2")

    def test_l1_low_mention_bonus(self):
        """提及率 < 30 且非必修 → L1"""
        self.assertEqual(determine_skill_depth(15, "加分"), "L1")
        self.assertEqual(determine_skill_depth(0, "加分"), "L1")

    def test_edge_threshold_60(self):
        """边界：提及率 59 必修 → L2, 60 必修 → L3"""
        self.assertEqual(determine_skill_depth(59, "必修"), "L2")
        self.assertEqual(determine_skill_depth(60, "必修"), "L3")

    def test_edge_threshold_30(self):
        """边界：提及率 29 加分 → L1, 30 加分 → L2"""
        self.assertEqual(determine_skill_depth(29, "加分"), "L1")
        self.assertEqual(determine_skill_depth(30, "加分"), "L2")

    def test_empty_priority(self):
        """空字符串优先级 → 按提及率判定"""
        self.assertEqual(determine_skill_depth(80, ""), "L2")
        self.assertEqual(determine_skill_depth(10, ""), "L1")


class TestPlanOutput(unittest.TestCase):
    """PlanOutput dataclass"""

    def test_from_dict(self):
        """from_dict 正确转换所有字段"""
        d = {
            "total_days": 60,
            "total_hours": 120.5,
            "knowledge_units": [{"theme": "test"}],
            "projects": [{"name": "p1"}],
            "essential_count": 5,
            "essential_covered": 3,
        }
        po = PlanOutput.from_dict(d)
        self.assertEqual(po.total_days, 60)
        self.assertEqual(po.total_hours, 120.5)
        self.assertEqual(po.knowledge_units, [{"theme": "test"}])
        self.assertEqual(po.projects, [{"name": "p1"}])
        self.assertEqual(po.essential_count, 5)
        self.assertEqual(po.essential_covered, 3)

    def test_from_dict_missing_keys(self):
        """缺失 key → 使用默认值"""
        po = PlanOutput.from_dict({})
        self.assertEqual(po.total_days, 0)
        self.assertEqual(po.projects, [])
        self.assertEqual(po.knowledge_units, [])

    def test_attribute_access(self):
        """支持 . 属性访问"""
        po = PlanOutput(total_days=90, total_hours=200.0)
        self.assertEqual(po.total_days, 90)
        self.assertEqual(po.total_hours, 200.0)


if __name__ == "__main__":
    unittest.main()
