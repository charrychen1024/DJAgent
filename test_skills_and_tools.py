#!/usr/bin/env python3
"""
智能体Skill和工具加载专项测试

重点测试：
1. Skill加载和注册是否正常
2. Tool加载和注册是否正常
3. 风险分析Skill能否正常工作
4. 执行人推荐Skill能否正常工作
5. 任务创建Skill能否正常工作
6. 完整对话流程（分析数据→推荐执行人→创建任务）
"""

import sys
import os
import json
import asyncio
import logging
from pathlib import Path

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 添加backend目录到Python路径
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))
os.chdir(str(backend_path))


# 颜色输出
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"


def print_test_header(test_name):
    print(f"\n{'=' * 60}")
    print(f"{Colors.BLUE}测试: {test_name}{Colors.RESET}")
    print(f"{'=' * 60}")


def print_pass(message):
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_fail(message):
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_info(message):
    print(f"{Colors.YELLOW}ℹ {message}{Colors.RESET}")


def print_json(data, indent=2):
    print(json.dumps(data, ensure_ascii=False, indent=indent))


# 测试结果统计
test_results = {"total": 0, "passed": 0, "failed": 0, "details": []}


def run_test(test_func):
    """运行测试并记录结果"""
    test_name = test_func.__name__
    test_results["total"] += 1

    try:
        print_test_header(test_name.replace("test_", "").replace("_", " ").title())
        result = test_func()
        if result:
            test_results["passed"] += 1
            test_results["details"].append({"test": test_name, "status": "passed"})
            return True
        else:
            test_results["failed"] += 1
            test_results["details"].append({"test": test_name, "status": "failed"})
            return False
    except Exception as e:
        print_fail(f"测试异常: {str(e)}")
        import traceback

        traceback.print_exc()
        test_results["failed"] += 1
        test_results["details"].append(
            {"test": test_name, "status": "failed", "error": str(e)}
        )
        return False


# ========== 测试用例 ==========


def test_skill_registry():
    """测试Skill注册表"""
    print_info("导入skill_registry模块...")
    from agents.skills.skill_registry import (
        register_skill,
        get_skill,
        get_all_skills,
        get_all_skill_names,
    )

    print_pass("skill_registry模块导入成功")

    print_info("获取所有已注册的Skill...")
    skills = get_all_skills()
    print_info(f"发现 {len(skills)} 个Skill: {list(skills.keys())}")

    expected_skills = [
        "risk_analyzer",
        "task_creator",
        "receiver_recommender",
        "核查_guider",
        "summary_generator",
    ]
    for skill_name in expected_skills:
        if skill_name in skills:
            skill = skills[skill_name]
            print_pass(
                f"  ✓ {skill_name}: {skill.description.description if hasattr(skill.description, 'description') else skill.description}"
            )
        else:
            print_fail(f"  ✗ {skill_name} 未注册")
            return False

    print_pass("所有必需的Skill都已正确注册")
    return True


def test_tool_registry():
    """测试Tool注册表"""
    print_info("导入tools模块...")
    from agents.tools import ALL_TOOLS

    print_info(f"发现 {len(ALL_TOOLS)} 个Tool: {list(ALL_TOOLS.keys())}")

    expected_tools = [
        "parse_csv",
        "parse_excel",
        "parse_pdf",
        "parse_word",
        "parse_image",
        "parse_file",
        "read_risk_data",
        "list_risk_data_files",
        "list_users",
        "get_user",
        "get_task",
        "get_task_detail",
        "query_tasks",
        "create_task",
        "update_task_status",
        "assign_task",
        "save_chat_message",
        "save_uploaded_file",
        "save_uploaded_file_from_path",
        "read_file_content",
        "list_uploaded_files",
        "delete_file",
    ]

    missing_tools = []
    for tool_name in expected_tools:
        if tool_name in ALL_TOOLS:
            print_pass(f"  ✓ {tool_name}")
        else:
            print_fail(f"  ✗ {tool_name} 未注册")
            missing_tools.append(tool_name)

    if missing_tools:
        print_info(f"缺失的Tool: {missing_tools}")
        return False

    print_pass("所有必需的Tool都已正确注册")
    return True


def test_manager_agent_initialization():
    """测试ManagerAgent初始化"""
    print_info("导入ManagerAgent...")
    from agents.manager_agent import ManagerAgent

    print_info("创建ManagerAgent实例...")
    agent = ManagerAgent("test_user", "测试用户")

    print_info(f"检查Agent属性...")
    print_pass(f"  user_id: {agent.user_id}")
    print_pass(f"  user_name: {agent.user_name}")
    print_pass(f"  tools数量: {len(agent._tools)}")
    print_pass(f"  skills数量: {len(agent._skills)}")
    print_pass(f"  system_prompt长度: {len(agent._system_prompt)} 字符")

    return True


def test_risk_analyzer_skill():
    """测试risk_analyzer Skill"""
    print_info("导入RiskAnalyzerSkill...")
    from agents.skills.risk_analyzer.skill import RiskAnalyzerSkill

    print_info("创建RiskAnalyzerSkill实例...")
    skill = RiskAnalyzerSkill()

    print_info(f"Skill信息:")
    print_pass(f"  name: {skill.name}")
    print_pass(f"  description: {skill.description}")
    print_pass(f"  tools: {skill.tools}")

    print_info("测试执行Skill...")

    async def test_execute():
        # 测试数据
        input_data = {"data_source": "risk_data_001.csv", "analysis_type": "full"}
        context = {"user_id": "test_user", "user_name": "测试用户"}

        result = await skill.execute(input_data, context)
        print_info(f"执行结果:")
        print_json(result, indent=2)

        if "error" in result:
            print_fail(f"Skill执行失败: {result['error']}")
            return False

        if result.get("success"):
            print_pass("Skill执行成功")
            if "data_summary" in result:
                print_info(f"数据摘要: {result['data_summary'][:100]}...")
            if "analysis" in result:
                analysis = result["analysis"]
                print_pass(f"  分析总数: {analysis.get('total_count')}")
                print_pass(f"  风险类型: {list(analysis.get('risk_types', {}).keys())}")
                print_pass(
                    f"  风险等级: {list(analysis.get('risk_levels', {}).keys())}"
                )
            return True

        return False

    return asyncio.run(test_execute())


def test_receiver_recommender_skill():
    """测试receiver_recommender Skill"""
    print_info("导入ReceiverRecommenderSkill...")
    from agents.skills.receiver_recommender.skill import ReceiverRecommenderSkill

    print_info("创建ReceiverRecommenderSkill实例...")
    skill = ReceiverRecommenderSkill()

    print_info(f"Skill信息:")
    print_pass(f"  name: {skill.name}")
    print_pass(f"  description: {skill.description}")
    print_pass(f"  tools: {skill.tools}")

    print_info("测试执行Skill...")

    async def test_execute():
        input_data = {"location": "上海市", "task_id": "TASK_001"}
        context = {"user_id": "test_user", "user_name": "测试用户"}

        result = await skill.execute(input_data, context)
        print_info(f"执行结果:")
        print_json(result, indent=2)

        if "error" in result:
            print_fail(f"Skill执行失败: {result['error']}")
            return False

        if result.get("success"):
            print_pass("Skill执行成功")
            recommendation = result.get("recommendation", {})
            print_pass(
                f"  推荐用户: {recommendation.get('recommended_user', {}).get('username')}"
            )
            print_pass(f"  推荐理由: {recommendation.get('reasons')}")
            return True

        return False

    return asyncio.run(test_execute())


def test_task_creator_skill():
    """测试task_creator Skill"""
    print_info("导入TaskCreatorSkill...")
    from agents.skills.task_creator.skill import TaskCreatorSkill

    print_info("创建TaskCreatorSkill实例...")
    skill = TaskCreatorSkill()

    print_info(f"Skill信息:")
    print_pass(f"  name: {skill.name}")
    print_pass(f"  description: {skill.description}")
    print_pass(f"  tools: {skill.tools}")

    print_info("测试执行Skill...")

    async def test_execute():
        input_data = {
            "creator_id": "001",
            "creator_name": "王经理",
            "assigned_to_id": "016",
            "assigned_to_name": "刘秀英快递",
            "risk_summary": "运单WLYD001超时派送核查",
            "risk_data_url": "risk_data_001.csv",
        }
        context = {"user_id": "001", "user_name": "王经理"}

        result = await skill.execute(input_data, context)
        print_info(f"执行结果:")
        print_json(result, indent=2)

        if "error" in result:
            print_fail(f"Skill执行失败: {result['error']}")
            return False

        if result.get("success"):
            print_pass("Skill执行成功")
            print_pass(f"  操作: {result.get('action')}")
            print_pass(f"  任务ID: {result.get('task_id')}")
            print_pass(f"  消息: {result.get('message')}")
            return True

        return False

    return asyncio.run(test_execute())


def test_complete_workflow():
    """测试完整工作流程：分析数据→推荐执行人→创建任务"""
    print_info("导入必要的模块...")
    from agents.skills import get_skill
    from agents.skills.risk_analyzer.skill import RiskAnalyzerSkill
    from agents.skills.receiver_recommender.skill import ReceiverRecommenderSkill
    from agents.skills.task_creator.skill import TaskCreatorSkill

    print_pass("所有Skill模块导入成功")

    async def workflow():
        # 步骤1：分析风险数据
        print_info("\n步骤1：分析风险数据...")
        risk_analyzer = RiskAnalyzerSkill()
        analysis_result = await risk_analyzer.execute(
            {"data_source": "risk_data_001.csv"},
            {"user_id": "001", "user_name": "王经理"},
        )

        if "error" in analysis_result:
            print_fail(f"风险分析失败: {analysis_result['error']}")
            return False

        print_pass("风险分析成功")
        analysis = analysis_result.get("analysis", {})
        print_info(f"  总数: {analysis.get('total_count')}")
        print_info(f"  风险类型: {analysis.get('risk_types')}")
        print_info(f"  风险等级: {analysis.get('risk_levels')}")

        # 步骤2：推荐执行人
        print_info("\n步骤2：推荐执行人...")
        recommender = ReceiverRecommenderSkill()
        recommendation_result = await recommender.execute(
            {"location": "上海市", "task_id": "TASK_001"},
            {"user_id": "001", "user_name": "王经理"},
        )

        if "error" in recommendation_result:
            print_fail(f"执行人推荐失败: {recommendation_result['error']}")
            return False

        print_pass("执行人推荐成功")
        recommendation = recommendation_result.get("recommendation", {})
        recommended_user = recommendation.get("recommended_user", {})
        print_info(f"  推荐用户: {recommended_user.get('username')}")
        print_info(f"  推荐理由: {recommendation.get('reasons')}")

        # 步骤3：创建任务
        print_info("\n步骤3：创建任务...")
        task_creator = TaskCreatorSkill()
        task_result = await task_creator.execute(
            {
                "creator_id": "001",
                "creator_name": "王经理",
                "assigned_to_id": recommended_user.get("user_id"),
                "assigned_to_name": recommended_user.get("username"),
                "risk_summary": f"风险数据核查 - 共{analysis.get('total_count')}条异常",
                "risk_data_url": "risk_data_001.csv",
            },
            {"user_id": "001", "user_name": "王经理"},
        )

        if "error" in task_result:
            print_fail(f"任务创建失败: {task_result['error']}")
            return False

        print_pass("任务创建成功")
        print_info(f"  任务ID: {task_result.get('task_id')}")
        print_info(f"  消息: {task_result.get('message')}")

        print_pass("\n✓ 完整工作流程测试通过！")
        print_pass("  风险分析 → 执行人推荐 → 任务创建")

        return True

    return asyncio.run(workflow())


def test_manager_agent_chat_workflow():
    """测试ManagerAgent完整对话流程"""
    print_info("导入ManagerAgent...")
    from agents.manager_agent import ManagerAgent
    from dotenv import load_dotenv

    load_dotenv()

    async def chat_workflow():
        print_info("创建ManagerAgent实例...")
        agent = ManagerAgent("001", "王经理")

        print_info("启动Agent会话...")
        async with agent:
            print_pass("Agent会话启动成功")

            # 对话1：帮助分析
            print_info("\n对话1：'帮我分析risk_data_001.csv的风险数据'")
            response1 = await agent.chat("帮我分析risk_data_001.csv的风险数据")
            print_info(f"AI回复: {response1[:200]}...")
            print_pass("对话1完成")

            # 对话2：创建任务
            print_info("\n对话2：'根据分析结果，创建一个任务下发给刘秀英快递'")
            response2 = await agent.chat("根据分析结果，创建一个任务下发给刘秀英快递")
            print_info(f"AI回复: {response2[:200]}...")
            print_pass("对话2完成")

            print_pass("\n✓ ManagerAgent对话流程测试通过！")

        return True

    return asyncio.run(chat_workflow())


# ========== 主函数 ==========


def main():
    print(f"\n{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BLUE}智能体Skill和工具加载专项测试{Colors.RESET}")
    print(f"{Colors.BLUE}{'=' * 60}\n")

    # 基础测试
    run_test(test_skill_registry)
    run_test(test_tool_registry)
    run_test(test_manager_agent_initialization)

    # Skill测试
    run_test(test_risk_analyzer_skill)
    run_test(test_receiver_recommender_skill)
    run_test(test_task_creator_skill)

    # 集成测试
    run_test(test_complete_workflow)
    run_test(test_manager_agent_chat_workflow)

    # 输出测试结果
    print(f"\n{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BLUE}测试结果汇总{Colors.RESET}")
    print(f"{Colors.BLUE}{'=' * 60}{Colors.RESET}")

    print(f"\n总测试数: {test_results['total']}")
    print(f"{Colors.GREEN}通过: {test_results['passed']}{Colors.RESET}")
    print(f"{Colors.RED}失败: {test_results['failed']}{Colors.RESET}")
    print(f"通过率: {test_results['passed'] / test_results['total'] * 100:.1f}%")

    if test_results["failed"] > 0:
        print(f"\n{Colors.RED}失败的测试:{Colors.RESET}")
        for detail in test_results["details"]:
            if detail["status"] == "failed":
                error_msg = f" - {detail['error']}" if "error" in detail else ""
                print(f"  {Colors.RED}✗ {detail['test']}{error_msg}{Colors.RESET}")
    else:
        print(f"\n{Colors.GREEN}✓ 所有测试通过！{Colors.RESET}")

    print(f"\n{Colors.BLUE}{'=' * 60}{Colors.RESET}\n")

    return test_results["failed"] == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
