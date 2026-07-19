"""时间计算工具函数"""

import re


def _parse_hours_float(hours_str):
    """'3h' -> 3.0, '2.5h' -> 2.5, 5.7 -> 5.7, None -> 0.0"""
    if hours_str is None:
        return 0.0
    if isinstance(hours_str, (int, float)):
        return float(hours_str)
    m = re.match(r'([\d.]+)', hours_str.strip())
    return float(m.group(1)) if m else 0.0


def _parse_hours(hours_str):
    """'3h' -> 3, '2.5h' -> 2"""
    return int(_parse_hours_float(hours_str))


def _format_hours_display(hours):
    """5.714 -> '5h43min', 3.0 -> '3h', 0.3 -> '18min', 0.0 -> '0h'"""
    if hours < 0.01:
        return "0h"
    total_minutes = int(round(hours * 60))
    h = total_minutes // 60
    m = total_minutes % 60
    if h > 0 and m > 0:
        return f"{h}h{m}min"
    elif h > 0:
        return f"{h}h"
    else:
        return f"{m}min"


def _compute_daily_hours(weekly_hours_str):
    """Parse weekly_hours string (e.g. '15-20h', '30h以上') to daily float."""
    if not weekly_hours_str:
        return 2.5
    s = str(weekly_hours_str).replace("h", "").strip()
    if "-" in s:
        parts = s.split("-")
        try:
            return (int(parts[0]) + int(parts[1])) / 2 / 7
        except (ValueError, IndexError):
            return 2.5
    if "以上" in s:
        try:
            return int(s.replace("以上", "")) / 7
        except ValueError:
            return 2.5
    try:
        return int(s) / 7
    except ValueError:
        return 2.5


def _compute_task_intensity(profile):
    """Estimate daily task volume from profile."""
    wh = profile.get("weekly_hours", "15-20h")
    daily = _compute_daily_hours(wh)
    if daily <= 1.5:
        return "轻量", daily
    elif daily >= 4:
        return "饱满", daily
    return "标准", daily


def _self_drive_label(score):
    if score is None:
        return "正常", ""
    s = int(score)
    if s <= 2:
        return "高频", "daily_checkin"
    elif s <= 4:
        return "正常", "milestone_reminder"
    else:
        return "低频", "challenge_task"


def _compute_time_coefficient(daily_hours):
    """日均时长 / 基线3h，不设上限。3h/day=1.0, 5.7h/day=1.90"""
    if daily_hours <= 0:
        return 1.0
    return round(daily_hours / 3.0, 2)
