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


# ── 学习节奏模式 ──

def _parse_weekly_total(weekly_hours_str):
    """'15-20h' -> 17.5, '30h以上' -> 30, '15h' -> 15, None -> 17.5"""
    if not weekly_hours_str:
        return 17.5
    s = str(weekly_hours_str).replace("h", "").strip()
    if "-" in s:
        parts = s.split("-")
        try:
            return (float(parts[0]) + float(parts[1])) / 2
        except (ValueError, IndexError):
            return 17.5
    if "以上" in s:
        try:
            return float(s.replace("以上", ""))
        except ValueError:
            return 17.5
    try:
        return float(s)
    except ValueError:
        return 17.5


def compute_pace_hours(pace, weekly_hours_str):
    """根据学习节奏模式计算每日学习小时数分配。

    pace: "daily" | "weekend" | "flexible"
    weekly_hours_str: e.g. "15-20h", "30h以上"

    Returns dict:
        mode: 模式名
        daily_hours: 日均小时数（用于总量计算）
        weekday_hours: 周中每天小时数
        weekend_hours: 周末每天小时数
    """
    weekly = _parse_weekly_total(weekly_hours_str)
    daily_avg = weekly / 7

    if pace == "weekend":
        # 周中轻量(2h/天)，周末集中(剩余/2)
        weekday_h = 2.0
        remaining = weekly - 5 * weekday_h
        if remaining <= 0:
            weekday_h = daily_avg
            weekend_h = daily_avg
        else:
            weekend_h = remaining / 2
        return {
            "mode": "weekend",
            "daily_hours": round(daily_avg, 1),
            "weekday_hours": round(max(weekday_h, 0.5), 1),
            "weekend_hours": round(max(weekend_h, 0.5), 1),
        }
    elif pace == "flexible":
        return {
            "mode": "flexible",
            "daily_hours": round(daily_avg, 1),
            "weekday_hours": 0,
            "weekend_hours": 0,
        }
    else:  # daily (default)
        return {
            "mode": "daily",
            "daily_hours": round(daily_avg, 1),
            "weekday_hours": round(daily_avg, 1),
            "weekend_hours": round(daily_avg, 1),
        }


def get_day_target(pace_config, day_index):
    """根据节奏模式和天索引获取该天目标学习小时数。

    pace_config: compute_pace_hours() 返回的 dict
    day_index: 从 1 开始的第 N 天
    """
    mode = pace_config.get("mode", "daily")
    if mode == "flexible":
        return pace_config["daily_hours"]
    if mode == "weekend":
        # day 1=周一 ... day 6=周六 day 7=周日
        wd = ((day_index - 1) % 7) + 1
        if wd >= 6:  # 周六日
            return pace_config["weekend_hours"]
        return pace_config["weekday_hours"]
    return pace_config["daily_hours"]
