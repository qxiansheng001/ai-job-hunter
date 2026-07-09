"""测试时间工具函数"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
from utils.time import _format_hours_display, _compute_daily_hours, _parse_hours_float


class TestFormatHoursDisplay(unittest.TestCase):
    """_format_hours_display: hours → 人类可读字符串"""

    def test_zero(self):
        self.assertEqual(_format_hours_display(0), "0h")

    def test_whole_hours(self):
        self.assertEqual(_format_hours_display(3), "3h")

    def test_hours_and_minutes(self):
        self.assertEqual(_format_hours_display(5.714), "5h43min")

    def test_only_minutes(self):
        self.assertEqual(_format_hours_display(0.3), "18min")

    def test_edge_round_up(self):
        """浮点精度：接近整数的值应正确四舍五入"""
        result = _format_hours_display(1.9999999)
        self.assertEqual(result, "2h")  # 之前出过 bug 的地方

    def test_edge_exact_60min(self):
        """59.5min 应进位为 1h"""
        result = _format_hours_display(0.9917)  # 59.5 min
        self.assertEqual(result, "1h")

    def test_negative_small(self):
        self.assertEqual(_format_hours_display(-0.1), "0h")


class TestParseHoursFloat(unittest.TestCase):
    def test_none(self):
        self.assertEqual(_parse_hours_float(None), 0.0)

    def test_numeric(self):
        self.assertEqual(_parse_hours_float(3), 3.0)
        self.assertEqual(_parse_hours_float(2.5), 2.5)

    def test_string_with_h(self):
        self.assertEqual(_parse_hours_float("3h"), 3.0)
        self.assertEqual(_parse_hours_float("2.5h"), 2.5)

    def test_string_without_h(self):
        self.assertEqual(_parse_hours_float("3"), 3.0)

    def test_empty_string(self):
        self.assertEqual(_parse_hours_float(""), 0.0)


class TestComputeDailyHours(unittest.TestCase):
    def test_range(self):
        self.assertAlmostEqual(_compute_daily_hours("15-20h"), 2.5)

    def test_above(self):
        self.assertAlmostEqual(_compute_daily_hours("30h以上"), 30 / 7)

    def test_fixed(self):
        self.assertAlmostEqual(_compute_daily_hours("21h"), 3.0)

    def test_none(self):
        self.assertAlmostEqual(_compute_daily_hours(None), 2.5)

    def test_empty(self):
        self.assertAlmostEqual(_compute_daily_hours(""), 2.5)


if __name__ == "__main__":
    unittest.main()
