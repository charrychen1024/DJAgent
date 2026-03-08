
import logging
from typing import Dict, Any

# 确保 backend 路径在 sys.path 中
import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from agents.skills.skill_base import Skill

logger = logging.getLogger(__name__)

class HelloWorldSkill(Skill):
    """
    一个简单的问候技能，用于演示动态技能扩展能力
    """
    
    name = "hello_world"
    description = "向用户打招呼，展示技能系统的扩展性"
    tools = []
    role = "问候大使"
    responsibilities = ["向用户问好", "介绍系统功能"]
    
    def __init__(self):
        super().__init__()
    
    async def execute(self, input_data: Dict, context: Dict) -> Dict:
        """执行问候"""
        logger.info(f"[HelloWorldSkill] 执行问候: {input_data}")
        
        user_name = context.get("username", "朋友")
        
        return {
            "message": f"你好，{user_name}！我是新加入的 HelloWorld 技能。这意味着你可以通过简单的文件添加，轻松扩展我的能力！"
        }
