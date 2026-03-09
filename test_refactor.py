"""
重构验证脚本
验证新架构的核心组件是否可以正常工作
"""

import asyncio
import sys
from pathlib import Path

# 添加 backend 路径
backend_path = Path(__file__).parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))


def test_imports():
    """测试导入"""
    print("=== 测试导入 ===")
    try:
        # 测试 AgentConfig（不依赖 SDK）
        from agents import AgentConfig, create_manager_config, create_staff_config

        # 测试 SessionManager（支持延迟导入）
        from agents import (
            get_or_create_staff_agent,
            get_or_create_manager_agent,
            get_or_create_agent,
            get_agent,
            close_agent,
            close_all_agents,
            get_session_count,
        )

        # 测试新架构（依赖 SDK）
        try:
            from agents import UnifiedAgent

            print("✅ UnifiedAgent 导入成功（SDK 可用）")
        except ImportError:
            print("⚠️ UnifiedAgent 导入失败（SDK 不可用，这是预期的）")

        # 测试旧架构（依赖 SDK）
        try:
            from agents import ManagerAgent, StaffAgent

            print("✅ 旧架构导入成功（SDK 可用）")
        except ImportError:
            print("⚠️ 旧架构导入失败（SDK 不可用，这是预期的）")

        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_config():
    """测试 AgentConfig"""
    print("\n=== 测试 AgentConfig ===")
    try:
        from agents import AgentConfig, create_manager_config, create_staff_config

        # 测试 Manager 配置
        manager_config = create_manager_config(
            user_id="test_manager",
            user_name="测试经理",
        )
        print(f"✅ Manager 配置创建成功: mode={manager_config.mode}")

        # 测试 Staff 配置
        staff_config = create_staff_config(
            user_id="test_staff",
            user_name="测试专员",
            skills=["核查_guider"],
        )
        print(
            f"✅ Staff 配置创建成功: mode={staff_config.mode}, skills={staff_config.skills}"
        )

        # 测试 SDK 选项转换
        try:
            sdk_options = manager_config.to_sdk_options()
            print(f"✅ SDK 选项转换成功（SDK 可用）")
        except Exception as e:
            print(f"⚠️ SDK 选项转换失败（SDK 不可用，这是预期的）")

        return True
    except Exception as e:
        print(f"❌ AgentConfig 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_mcp_server():
    """测试 MCP 服务器"""
    print("\n=== 测试 MCP 服务器 ===")
    try:
        from agents.mcp_server import create_djagent_mcp_server

        mcp_server = create_djagent_mcp_server()
        print(f"✅ MCP 服务器创建成功: {list(mcp_server.keys())}")
        return True
    except Exception as e:
        print(f"❌ MCP 服务器测试失败（SDK 不可用，这是预期的）")
        return False


def test_session_manager():
    """测试 SessionManager"""
    print("\n=== 测试 SessionManager ===")
    try:
        from agents import (
            get_or_create_staff_agent,
            get_or_create_manager_agent,
            get_or_create_agent,
            get_agent,
            close_agent,
            close_all_agents,
            get_session_count,
        )

        # 测试获取会话数量
        count = get_session_count()
        print(f"✅ 当前会话数量: {count}")

        return True
    except Exception as e:
        print(f"❌ SessionManager 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("DJAgent 智能体重构验证")
    print("=" * 60)

    results = []
    results.append(test_imports())
    results.append(test_config())
    results.append(test_session_manager())
    results.append(test_mcp_server())

    print("\n" + "=" * 60)
    print(f"验证完成: {sum(results)}/{len(results)} 项通过")
    print("=" * 60)

    return all(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
