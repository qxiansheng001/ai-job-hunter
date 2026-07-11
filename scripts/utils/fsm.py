"""路由状态机：检测用户进度状态，路由到对应子技能。"""

from enum import Enum


class JobState(str, Enum):
    """用户求职进度状态枚举。"""
    NO_STATE = "no_state"           # 无 .skill-state.json 或 profile 为空
    PROFILE_DONE = "profile_done"   # job-init 完成，可以开始扫岗
    SCAN_DONE = "scan_done"         # job-scan 完成，有岗位数据但未分析
    ANALYZE_DONE = "analyze_done"   # JD 分析完成，但学习计划未生成
    PLAN_DONE = "plan_done"         # 学习计划已生成，进入陪跑
    ACTIVE = "active"               # 陪跑中（兼容旧状态）


def detect_state(state_data: dict) -> JobState:
    """根据状态文件内容确定当前 JobState。"""
    if not state_data:
        return JobState.NO_STATE

    profile = state_data.get("profile", {})
    if not profile or not profile.get("tech_stack"):
        return JobState.NO_STATE

    # 检查 job_search
    job_search = state_data.get("job_search", {})
    if job_search.get("status") != "done":
        return JobState.PROFILE_DONE

    # 检查分析
    analysis = state_data.get("analysis", {})
    if not analysis.get("report_file"):
        return JobState.SCAN_DONE

    # 检查学习计划
    learning_plan = state_data.get("learning_plan", {})
    if not learning_plan.get("target_role") or not learning_plan.get("plan_file"):
        return JobState.ANALYZE_DONE

    return JobState.PLAN_DONE


STATE_TO_SKILL = {
    JobState.NO_STATE: "job-init",
    JobState.PROFILE_DONE: "job-scan",
    JobState.SCAN_DONE: "job-analyze",
    JobState.ANALYZE_DONE: "job-analyze",
    JobState.PLAN_DONE: "job-status",
    JobState.ACTIVE: "job-status",
}

STATE_DESCRIPTIONS = {
    JobState.NO_STATE: "尚未创建画像，需要先进行初始化。",
    JobState.PROFILE_DONE: "画像已就绪，可以开始搜索岗位。",
    JobState.SCAN_DONE: "岗位数据已就绪，等待分析。",
    JobState.ANALYZE_DONE: "JD 分析已完成，等待生成学习计划。",
    JobState.PLAN_DONE: "学习计划已就绪，进入陪跑模式。",
    JobState.ACTIVE: "学习计划已就绪，进入陪跑模式。",
}
