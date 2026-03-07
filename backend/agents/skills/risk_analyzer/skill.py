"""
风险分析Skill
分析风险数据，识别风险模式，提供决策建议
"""

# 动态添加路径
import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List

# 动态添加路径
backend_path = Path(__file__).parent.parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from agents.skills.skill_base import Skill

logger = logging.getLogger(__name__)


class RiskAnalyzerSkill(Skill):
    """风险分析Skill"""
    
    name = "risk_analyzer"
    description = "分析风险数据，识别风险模式，提供决策建议"
    tools = [
        "parse_csv",
        "parse_excel", 
        "read_risk_data",
        "list_users",
        "list_risk_data_files"
    ]
    role = "资深风控专家"
    responsibilities = [
        "解析用户提供的风险数据文件",
        "识别风险模式（超时、重量异常、虚假签收等）",
        "分析异常特征和风险等级",
        "提供专业分析报告和建议"
    ]
    
    def __init__(self):
        super().__init__()
        self.data = None
        self.analysis_result = None
    
    async def execute(self, input_data: Dict, context: Dict) -> Dict:
        """
        执行风险分析
        
        Args:
            input_data: 输入数据，包含:
                - data_source: 数据来源（文件路径或文件名）
                - analysis_type: 分析类型（可选）
            context: 上下文信息
            
        Returns:
            分析结果
        """
        logger.info(f"[RiskAnalyzerSkill] 执行分析: {input_data}")
        
        # 验证输入
        validation = self.validate_input(input_data, ["data_source"])
        if not validation.get("success"):
            return validation
        
        data_source = input_data.get("data_source")
        
        try:
            # 导入工具
            from agents.tools import (
                parse_csv, parse_excel, read_risk_data, 
                list_risk_data_files
            )
            
            # 尝试多种方式读取数据
            data_result = None
            
            # 方式1：直接读取风险数据文件
            if isinstance(data_source, str) and "risk_data" in data_source.lower():
                data_result = read_risk_data(data_source)
            
            # 方式2：尝试解析文件
            if data_result is None or "error" in data_result:
                if data_source.endswith('.csv'):
                    data_result = parse_csv(data_source)
                elif data_source.endswith(('.xlsx', '.xls')):
                    data_result = parse_excel(data_source)
            
            # 方式3：列出可用文件让用户选择
            if data_result is None or "error" in data_result:
                files_result = list_risk_data_files()
                return {
                    "success": True,
                    "action": "list_files",
                    "message": "请选择要分析的风险数据文件",
                    "available_files": files_result.get("files", [])
                }
            
            if "error" in data_result:
                return data_result
            
            # 保存数据
            self.data = data_result
            
            # 分析数据
            analysis = await self._analyze_data(data_result, context)
            self.analysis_result = analysis
            
            return {
                "success": True,
                "action": "analysis_complete",
                "data_summary": data_result.get("summary", ""),
                "analysis": analysis
            }
            
        except Exception as e:
            logger.error(f"[RiskAnalyzerSkill] 分析失败: {str(e)}")
            return {"error": f"分析失败: {str(e)}"}
    
    async def _analyze_data(self, data: Dict, context: Dict) -> Dict:
        """
        分析数据
        
        Args:
            data: 风险数据
            context: 上下文
            
        Returns:
            分析结果
        """
        records = data.get("data", [])
        
        if not records:
            return {"error": "数据为空"}
        
        # 基本统计
        total = len(records)
        
        # 风险类型统计
        risk_types = {}
        risk_levels = {}
        
        for record in records:
            # 统计异常类型
            if "异常类型" in record:
                atype = record.get("异常类型", "未知")
                risk_types[atype] = risk_types.get(atype, 0) + 1
            
            # 统计风险等级
            if "风险等级" in record:
                level = record.get("风险等级", "未知")
                risk_levels[level] = risk_levels.get(level, 0) + 1
        
        # 生成分析报告
        analysis = {
            "total_count": total,
            "risk_types": risk_types,
            "risk_levels": risk_levels,
            "key_findings": self._generate_findings(risk_types, risk_levels),
            "recommendations": self._generate_recommendations(risk_types, risk_levels)
        }
        
        return analysis
    
    def _generate_findings(self, risk_types: Dict, risk_levels: Dict) -> List[str]:
        """生成关键发现"""
        findings = []
        
        # 风险类型发现
        if risk_types:
            top_type = max(risk_types.items(), key=lambda x: x[1])
            findings.append(f"主要异常类型：{top_type[0]}，共{top_type[1]}条")
        
        # 风险等级发现
        if "高" in risk_levels:
            high_count = risk_levels.get("高", 0)
            findings.append(f"高风险：{high_count}条，需要优先处理")
        
        return findings
    
    def _generate_recommendations(self, risk_types: Dict, risk_levels: Dict) -> List[str]:
        """生成建议"""
        recommendations = []
        
        # 根据风险等级建议
        if risk_levels.get("高", 0) > 0:
            recommendations.append("建议立即安排高风险任务的下发和核查")
        
        # 根据风险类型建议
        if "超时派送" in risk_types:
            recommendations.append("超时派送风险需要核实配送路线和时效")
        
        if "虚假签收" in risk_types:
            recommendations.append("虚假签收风险需要核实签收人和签收凭证")
        
        if "重量异常" in risk_types:
            recommendations.append("重量异常需要核实称重记录和货物情况")
        
        if not recommendations:
            recommendations.append("建议定期核查风险数据，及时处理异常")
        
        return recommendations


__all__ = ['RiskAnalyzerSkill']
