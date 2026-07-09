"""计划模型数据类 — PlanInput / PlanOutput 定义计划构建器的接口契约。"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlanInput:
    """构建计划所需的所有输入。"""
    market_skills: list
    supplements: list
    duration: int
    profile: dict
    gap_data: dict


@dataclass
class PlanOutput:
    """计划构建器的标准输出。renderer 依赖此结构进行渲染。"""
    knowledge_units: list = field(default_factory=list)
    total_days: int = 0
    total_hours: float = 0.0
    time_coefficient: float = 1.0
    learning_overview: list = field(default_factory=list)
    projects: list = field(default_factory=list)
    os_contributions: list = field(default_factory=list)
    review_days: list = field(default_factory=list)
    essential_count: int = 0
    essential_covered: int = 0
    bonus_count: int = 0
    bonus_covered: int = 0

    @classmethod
    def from_dict(cls, d: dict) -> "PlanOutput":
        """从 build_continuous_plan 返回的 dict 创建实例。"""
        return cls(
            knowledge_units=d.get("knowledge_units", []),
            total_days=d.get("total_days", 0),
            total_hours=d.get("total_hours", 0.0),
            time_coefficient=d.get("time_coefficient", 1.0),
            learning_overview=d.get("learning_overview", []),
            projects=d.get("projects", []),
            os_contributions=d.get("os_contributions", []),
            review_days=d.get("review_days", []),
            essential_count=d.get("essential_count", 0),
            essential_covered=d.get("essential_covered", 0),
            bonus_count=d.get("bonus_count", 0),
            bonus_covered=d.get("bonus_covered", 0),
        )
