"""
Claude Agent SDK Python Demo
读取本地 .env 文件中的 ANTHROPIC_BASE_URL 和 ANTHROPIC_AUTH_TOKEN，
支持加载用户目录下的 MCP 服务器配置和 Skill。

使用方式:
1. 创建 .env 文件，配置 ANTHROPIC_BASE_URL 和 ANTHROPIC_AUTH_TOKEN
2. pip install claude-agent-sdk python-dotenv
3. python claude_agent_demo.py
"""

import asyncio
import json
import os
from pathlib import Path
from dotenv import load_dotenv

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ResultMessage,
)

# 加载 .env 文件
load_dotenv()

ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "")
ANTHROPIC_AUTH_TOKEN = os.getenv("ANTHROPIC_AUTH_TOKEN", "")
CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC = os.getenv("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC", "1")

print(f"[Claude] 使用环境变量: ANTHROPIC_BASE_URL={ANTHROPIC_BASE_URL}, ANTHROPIC_AUTH_TOKEN={ANTHROPIC_AUTH_TOKEN}")

# 用户目录 ~/.claude 路径
USER_CLAUDE_DIR = Path.home() / ".claude"


def load_user_mcp_servers() -> dict:
    """
    从用户目录加载 MCP 服务器配置。
    查找路径（按优先级）:
    1. ~/.claude/.mcp.json
    2. 当前项目 .mcp.json
    """
    mcp_servers = {}

    # 用户级 MCP 配置
    user_mcp_file = USER_CLAUDE_DIR / ".mcp.json"
    if user_mcp_file.exists():
        try:
            data = json.loads(user_mcp_file.read_text())
            servers = data.get("mcpServers", {})
            mcp_servers.update(servers)
            print(f"[MCP] 已加载用户级配置: {user_mcp_file} ({len(servers)} 个服务器)")
        except (json.JSONDecodeError, OSError) as e:
            print(f"[MCP] 解析用户级配置失败: {e}")

    # 项目级 MCP 配置
    project_mcp_file = Path.cwd() / ".mcp.json"
    if project_mcp_file.exists():
        try:
            data = json.loads(project_mcp_file.read_text())
            servers = data.get("mcpServers", {})
            mcp_servers.update(servers)
            print(f"[MCP] 已加载项目级配置: {project_mcp_file} ({len(servers)} 个服务器)")
        except (json.JSONDecodeError, OSError) as e:
            print(f"[MCP] 解析项目级配置失败: {e}")

    return mcp_servers


def load_user_settings() -> dict:
    """
    加载用户 ~/.claude/settings.json 中的配置（含启用的 plugin/skill 信息）。
    """
    settings_file = USER_CLAUDE_DIR / "settings.json"
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text())
            plugins = settings.get("enabledPlugins", {})
            enabled = [k for k, v in plugins.items() if v]
            print(f"[Settings] 已加载用户设置，启用的 Skills/Plugins: {enabled}")
            return settings
        except (json.JSONDecodeError, OSError) as e:
            print(f"[Settings] 解析设置文件失败: {e}")
    return {}


def build_options(mcp_servers: dict, user_settings: dict) -> ClaudeAgentOptions:
    """
    构建 ClaudeAgentOptions，注入环境变量和 MCP 配置。
    """
    env = {}
    if ANTHROPIC_BASE_URL:
        env["ANTHROPIC_BASE_URL"] = ANTHROPIC_BASE_URL
    if ANTHROPIC_AUTH_TOKEN:
        env["ANTHROPIC_AUTH_TOKEN"] = ANTHROPIC_AUTH_TOKEN
        # 某些代理场景下 AUTH_TOKEN 同时用作 API_KEY
        env["ANTHROPIC_API_KEY"] = ANTHROPIC_AUTH_TOKEN
    if CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC:
        env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC

    options = ClaudeAgentOptions(
        env=env,
        # 合并从配置文件中发现的 MCP 服务器
        mcp_servers=mcp_servers if mcp_servers else {},
        # 权限模式：acceptEdits 自动批准文件编辑
        permission_mode="acceptEdits",
        # 限制最大对话轮次，防止无限循环
        max_turns=10,
        thinking={"type": "disabled"}  # 0.1.44的版本需要这个参数，否则会报错，之前的版本不需要
    )
    return options


async def demo_oneshot():
    """
    演示 1: 单次查询模式 (query)
    适合无状态的一次性问答。
    """
    print(" " + "=" * 60)
    print("Demo 1: 单次查询模式 (query)")
    print("=" * 60)

    mcp_servers = load_user_mcp_servers()
    user_settings = load_user_settings()
    options = build_options(mcp_servers, user_settings)

    prompt = "你好，请简要介绍一下你自己，以及你当前可以使用哪些工具。"
    print(f" [Prompt] {prompt} ")

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(f"[Claude] {block.text}")
                elif isinstance(block, ToolUseBlock):
                    print(f"[Tool Call] {block.name}({json.dumps(block.input, ensure_ascii=False)})")
        elif isinstance(message, ResultMessage):
            if message.subtype == "success":
                print(f" [Result] 查询成功完成")
            else:
                print(f" [Result] 查询结束: {message.subtype}")


async def demo_interactive():
    """
    演示 2: 交互式会话模式 (ClaudeSDKClient)
    支持多轮对话，保持上下文。
    """
    print(" " + "=" * 60)
    print("Demo 2: 交互式会话模式 (ClaudeSDKClient)")
    print("=" * 60)

    mcp_servers = load_user_mcp_servers()
    user_settings = load_user_settings()
    options = build_options(mcp_servers, user_settings)

    async with ClaudeSDKClient(options=options) as client:
        queries = [
            "请列出当前目录下的文件。",
            "用一句话总结你刚才看到了什么。",
        ]
        for prompt in queries:
            print(f" [Prompt] {prompt}")
            await client.query(prompt)

            async for msg in client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            print(f"[Claude] {block.text}")
                        elif isinstance(block, ToolUseBlock):
                            print(f"[Tool Call] {block.name}")


async def demo_repl():
    """
    演示 3: REPL 交互式终端
    用户输入问题，Claude 回答，输入 'quit' 退出。
    """
    print(" " + "=" * 60)
    print("Demo 3: REPL 交互模式")
    print("输入 'quit' 或 'exit' 退出")
    print("=" * 60)

    mcp_servers = load_user_mcp_servers()
    user_settings = load_user_settings()
    options = build_options(mcp_servers, user_settings)

    async with ClaudeSDKClient(options=options) as client:
        while True:
            try:
                user_input = input(" [You] > ").strip()
            except (EOFError, KeyboardInterrupt):
                print(" 退出")
                break

            if user_input.lower() in ("quit", "exit", "q"):
                print("退出")
                break
            if not user_input:
                continue

            await client.query(user_input)

            async for msg in client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            print(f"[Claude] {block.text}")
                        elif isinstance(block, ToolUseBlock):
                            print(f"[Tool Call] {block.name}")


async def main():
    print("Claude Agent SDK Demo")
    print(f" ANTHROPIC_BASE_URL: {ANTHROPIC_BASE_URL or '(未设置，使用默认)'}")
    print(f" ANTHROPIC_AUTH_TOKEN: {'***' + ANTHROPIC_AUTH_TOKEN[-4:] if ANTHROPIC_AUTH_TOKEN else '(未设置)'}")
    print(f" 用户目录: {USER_CLAUDE_DIR}")

    # 选择运行哪个 demo
    print(" 请选择运行模式:")
    print(" 1 - 单次查询 (query)")
    print(" 2 - 多轮对话 (ClaudeSDKClient)")
    print(" 3 - REPL 交互终端")

    try:
        choice = input(" 选择 [1/2/3]: ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    if choice == "1":
        await demo_oneshot()
    elif choice == "2":
        await demo_interactive()
    elif choice == "3":
        await demo_repl()
    else:
        print(f"未知选项: {choice}")


if __name__ == "__main__":
    asyncio.run(main())
