"""
临时诊断脚本
"""

# 检查 MCP 服务器和工具注册
import os
import sys
from pathlib import Path

# 添加 backend 到路径
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))
os.chdir(str(backend_path))

# 检查 mcp_server.py
print("=== 诊断：检查 MCP 服务器工具注册 ===")

mcp_server_file = backend_path / "agents/mcp_server.py"
if mcp_server_file.exists():
    print(f"✅ MCP服务器文件存在: {mcp_server_file}")
    content = mcp_server_file.read_text()

    # 检查 @tool 装饰器使用
    import_count = content.count("@tool(")
    print(f"发现 {import_count} 个 @tool 装 使用")

    # 检查 create_sdk_mcp_server 调用
    create_count = content.count("create_sdk_mcp_server")
    print(f"发现 {create_count} 个 create_sdk_mcp_server 调用")

    # 检查工具列表
    if "all_tools = [" in content:
        start = content.find("all_tools = [")
        end = content.find("]\n", start)
        if start != -1:
            tools_str = content[start:end]
            tool_count = tools_str.count('"tool(')
            print(f"发现 {tool_count} 个工具定义")
            # 打印前3个工具名称
            tools_list = tools_str.split(",")
            for i, t in enumerate(tools_list[:3], 1):
                print(f"  工具 {i}: {t[:50]}...")

    # 检查 create_sdk_mcp_server 调�调用
    if "server = create_sdk_mcp_server(" in content:
        print("✅ 使用 create_sdk_mcp_server 创建服务器")
    else:
        print("❌ 未使用 create_sdk_mcp_server")

else:
    print(f"❌ MCP服务器文件不存在: {mcp_server_file}")

# 检查 config.py 的 _build_tools_config 方法
print("\n=== 诊断：检查 config.py 的 _build_tools_config 方法 ===")

config_file = backend_path / "agents/config.py"
if config_file.exists():
    print(f"✅ config.py 文件存在: {config_file}")
    content = config_file.read_text()

    # 查找 _build_tools_config 方法
    if "def _build_tools_config(self)" in content:
        print("✅ 找到 _build_tools_config 方法定义")

        # 检查方法内部的分支逻辑
        start = content.find("def _build_tools_config(self)")
        if start != -1:
            # 找到方法结束
            end_bracket = 0
            open_brackets = 0
            for i in range(start, len(content)):
                if content[i] == ":":
                    if open_brackets > 0:
                        open_brackets -= 1
                        if open_brackets == 0:
                            end = i
                            break
                else:
                    break

            method_code = content[start:end]

            # 检查分支结构
            if "if self.mode" in method_code:
                print("❌ 问题：使用了 if self.mode 分支")
                print("   这意味着只有 Manager 模式才会配置工具")
            else:
                print("✅ 没有 if self.mode 分支，所有模式都会配置")

            # 检查 MCP 服务器是否被添加
            if "mcp_servers" in method_code or "self.mcp_servers" in method_code:
                print("✅ MCP 服务器配置存在")
            else:
                print("❌ 未找到 mcp_servers 配置")
                print("   这可能是 MCP 工具不工作的原因")

            # 查找 allowed_tools
            if "allowed_tools" in method_code:
                print("✅ allowed_tools 配置存在")
            else:
                print("❌ 未找到 allowed_tools 配置")

    else:
        print("❌ 未找到 _build_tools_config 方法定义")
else:
    print(f"❌ config.py 文件不存在: {config_file}")

# 诊断结论
print("\n=== 诊断结论 ===")
print("✅ 修复方案：")
print("1. 移除 if self.mode 分支")
print("2. 确保 mcp_servers 在 all 上下文中")
print("3. 确保 allowed_tools 在配置中（或者移除它让 SDK 自动管理）")
print("4. 检查 MCP 服务器的工具是否正确注册")
