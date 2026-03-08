"""
Simple ReAct Agent - 具备自我规划和工具调用能力的智能体
替代简单的规则式响应，实现真正的智能交互
"""

import os
import json
import logging
import httpx
import re
import asyncio
from typing import List, Dict, Any, Optional

from agents.skills.skill_registry import get_all_skills, get_skill

logger = logging.getLogger(__name__)

class SimpleAgent:
    """
    具备 ReAct (Reasoning + Acting) 能力的智能体
    """
    
    def __init__(self, user_id: str = "default", username: str = "User"):
        self.user_id = user_id
        self.username = username
        self.skills = get_all_skills()
        self.max_steps = 5  # 最大思考步骤
        
        # Claude API 配置
        self.api_key = os.getenv("ANTHROPIC_AUTH_TOKEN", "")
        self.api_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1/messages")
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        
    def _get_system_prompt(self) -> str:
        """构建系统提示词，包含可用技能描述"""
        skill_descs = []
        for name, skill in self.skills.items():
            skill_descs.append(f"- {name}: {skill.description}")
            
        skills_str = "\n".join(skill_descs)
        
        return f"""你是一个智能风控助手，你的名字是 DJAgent。
你可以帮助用户分析风险数据、创建任务、推荐核查人员等。

你拥有以下技能(Skills)可以使用：
{skills_str}

**思考与行动模式 (ReAct)**：
当收到用户请求时，请按照以下步骤进行：
1. **思考 (Thought)**: 分析用户需求，决定是否需要使用工具/技能。
2. **行动 (Action)**: 如果需要使用技能，请严格使用以下格式输出：
   Action: <SkillName>
   Action Input: <JSON格式的参数>
3. **观察 (Observation)**: 我会执行该技能并将结果反馈给你。
4. **回答 (Final Answer)**: 根据观察结果，给用户最终回复。

**重要规则**：
- 如果用户只是闲聊或问候，直接回答即可，不需要使用技能。
- 每次回复只能包含一个 Action。
- Action Input 必须是合法的 JSON 字符串。
- 最终回答不需要特定格式，自然流畅即可。

**示例**：
用户：帮我分析 risk_data_001.csv
Thought: 用户需要分析风险数据，我应该使用 risk_analyzer 技能。
Action: risk_analyzer
Action Input: {{"data_source": "risk_data_001.csv"}}
Observation: ... (技能执行结果) ...
Thought: 分析结果显示...
Final Answer: 根据分析，risk_data_001.csv 中存在...
"""

    async def _call_llm(self, messages: List[Dict]) -> str:
        """调用 Claude API"""
        if not self.api_key:
            # 模拟模式 (无 API Key)
            logger.warning("[SimpleAgent] 未配置 API Key，使用模拟响应")
            last_msg = messages[-1]['content']
            if "分析" in last_msg:
                return 'Thought: 用户需要分析数据。\nAction: risk_analyzer\nAction Input: {"data_source": "risk_data_001.csv"}'
            return "我是 DJAgent (模拟模式)。请配置 ANTHROPIC_AUTH_TOKEN 以启用智能功能。"

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "system": self._get_system_prompt(),
            "messages": messages
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.api_url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                return data['content'][0]['text']
        except Exception as e:
            logger.error(f"[SimpleAgent] LLM 调用失败: {e}")
            return f"系统错误: 无法连接 AI 服务 ({str(e)})"

    async def chat(self, user_message: str) -> str:
        """主对话循环"""
        messages = [{"role": "user", "content": user_message}]
        
        for step in range(self.max_steps):
            # 1. 调用 LLM
            logger.info(f"[SimpleAgent] Step {step+1}: Calling LLM...")
            llm_response = await self._call_llm(messages)
            logger.info(f"[SimpleAgent] LLM Response: {llm_response[:100]}...")
            
            # 2. 解析 Action
            action_match = re.search(r"Action:\s*(\w+)", llm_response)
            input_match = re.search(r"Action Input:\s*(\{.*\})", llm_response, re.DOTALL)
            
            if action_match and input_match:
                skill_name = action_match.group(1)
                try:
                    action_input = json.loads(input_match.group(1))
                except json.JSONDecodeError:
                    logger.error(f"[SimpleAgent] JSON 解析失败: {input_match.group(1)}")
                    messages.append({"role": "assistant", "content": llm_response})
                    messages.append({"role": "user", "content": "System: Action Input JSON 解析失败，请检查格式。"})
                    continue
                
                # 3. 执行 Skill
                skill = self.skills.get(skill_name)
                if skill:
                    logger.info(f"[SimpleAgent] Executing Skill: {skill_name}")
                    try:
                        # 执行技能
                        result = await skill.execute(action_input, context={"user_id": self.user_id})
                        observation = f"Observation: {json.dumps(result, ensure_ascii=False)}"
                    except Exception as e:
                        observation = f"Observation: 技能执行出错: {str(e)}"
                else:
                    observation = f"Observation: 找不到技能 '{skill_name}'"
                
                # 4. 更新历史
                messages.append({"role": "assistant", "content": llm_response})
                messages.append({"role": "user", "content": observation})
                
            else:
                # 没有 Action，认为是最终回答
                return llm_response

        return "任务处理超时，请重试。"
