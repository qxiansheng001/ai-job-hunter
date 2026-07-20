"""Claude API 调用封装 — 统一处理环境变量检查 + API 调用 + JSON 解析。"""

import json
import os
import sys

from utils.protocol import emit

_MODEL = "claude-sonnet-5-20251001"


def claude_available():
    """检查 ANTHROPIC_API_KEY 环境变量是否已设置。"""
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    return bool(key)


def call_claude(system_prompt, user_prompt, response_schema=None):
    """调用 Claude API，返回解析后的 JSON。

    参数:
        system_prompt: 系统提示词
        user_prompt: 用户提示词（含数据）
        response_schema: 期望的 JSON Schema 描述（不传则回原始文本）

    返回:
        解析后的 dict（响应 JSON），或 None（调用失败/无 key）
    """
    if not claude_available():
        emit("claude.skip", "ANTHROPIC_API_KEY 未设置，跳过 Claude 调用",
             status="warn")
        return None

    try:
        import anthropic
    except ImportError:
        emit("claude.dep_missing", "缺少 anthropic 库，请执行: pip install anthropic",
             status="error")
        return None

    api_key = os.environ["ANTHROPIC_API_KEY"]
    client = anthropic.Anthropic(api_key=api_key)

    # 构建 messages
    messages = [{"role": "user", "content": user_prompt}]

    # 如果指定了 JSON schema，要求返回 JSON
    extra_body = {}
    suffix = ""
    if response_schema:
        suffix = (
            "\n\n你必须只返回一个合法的 JSON 对象，不要包含其他文字说明。"
            "JSON 结构必须严格符合以下 schema：\n"
            f"{json.dumps(response_schema, ensure_ascii=False, indent=2)}"
        )

    emit("claude.call", f"正在调用 Claude API（模型: {_MODEL}）...")

    try:
        resp = client.messages.create(
            model=_MODEL,
            max_tokens=4096,
            system=system_prompt + suffix,
            messages=messages,
        )
    except Exception as e:
        emit("claude.error", f"Claude API 调用失败: {e}", status="error",
             error={"code": "CLAUDE_API_ERROR", "traceback": str(e)})
        return None

    content = resp.content[0].text if resp.content else ""

    if response_schema:
        # 尝试从返回中提取 JSON
        content = content.strip()
        # 移除可能的 markdown 代码块包装
        if content.startswith("```"):
            lines = content.split("\n")
            # 移除第一行 ```json 或 ``` 和最后一行 ```
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        try:
            parsed = json.loads(content)
            emit("claude.ok", "Claude API 调用成功",
                 data={"tokens": getattr(resp, 'usage', None)})
            return parsed
        except json.JSONDecodeError as e:
            emit("claude.parse_error", f"Claude 返回非 JSON 内容: {e}",
                 status="error",
                 error={"code": "CLAUDE_PARSE_ERROR", "traceback": content[:500]})
            return None

    emit("claude.ok", "Claude API 调用成功",
         data={"tokens": getattr(resp, 'usage', None)})
    return content
