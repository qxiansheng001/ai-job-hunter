"""统一的 JSON-Line 输出协议。

所有 Python 脚本必须通过 emit() 输出结构化 JSON 行到 stdout，
通过 emit_progress() 输出进度信息到 stderr。
每行一个独立 JSON 对象，\n 分隔，ensure_ascii=False。
"""

import json
import sys


def emit(step, message, status="ok", data=None, warnings=None, error=None, stream=None):
    """输出标准 JSON 行。

    参数:
        step: 点分隔步骤标识符，如 "scraper.list.done"
        message: 人类可读描述，不能为空
        status: "ok" | "warn" | "error"
        data: 结构化数据 dict（可选）
        warnings: 非致命问题字符串列表（可选）
        error: 致命错误 dict {"code": str, "traceback": str}（可选）
        stream: 输出流，默认 stdout
    """
    if stream is None:
        stream = sys.stdout
    obj = {"step": step, "status": status, "message": message}
    if data is not None:
        obj["data"] = data
    if warnings is not None:
        obj["warnings"] = warnings
    if error is not None:
        obj["error"] = error
    print(json.dumps(obj, ensure_ascii=False), file=stream)


def emit_progress(step, current, total, message, stream=None):
    """输出进度 JSON 行到 stderr（与结构化结果严格分离）。

    参数:
        step: 步骤标识符
        current: 当前进度数值
        total: 总量数值
        message: 人类可读描述
        stream: 输出流，默认 stderr
    """
    if stream is None:
        stream = sys.stderr
    pct = round(current / total * 100, 1) if total > 0 else 0
    obj = {
        "step": step, "status": "ok",
        "progress": {"current": current, "total": total, "pct": pct},
        "message": message,
    }
    print(json.dumps(obj, ensure_ascii=False), file=stream)


def emit_fatal(code, message, traceback=None):
    """输出致命错误 JSON 行到 stdout 后退出。

    参数:
        code: 错误代码字符串
        message: 错误描述
        traceback: 可选的 traceback 字符串
    """
    emit("fatal", message, status="error",
         error={"code": code, "traceback": traceback or ""})
    sys.exit(1)
