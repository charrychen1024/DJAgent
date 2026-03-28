import React, { useState } from 'react';
import PropTypes from 'prop-types';
import './ToolCallCard.css';

/**
 * 工具调用渲染器
 *
 * 显示 AI 调用的工具及其参数
 * 遵循 Anthropic Tool Use 规范
 */
const ToolCallCard = ({ toolUseId, name, input }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // 判断是否是特殊工具
  const isFormTool = name === 'display_form';
  const isSearchTool = name.includes('search');

  // 获取工具图标
  const getToolIcon = () => {
    if (isFormTool) return '📋';
    if (isSearchTool) return '🔍';
    if (name.includes('weather')) return '🌤';
    return '🔧';
  };

  return (
    <div className="tool-call-card">
      <div className="tool-header" onClick={() => setIsExpanded(!isExpanded)}>
        <span className="tool-icon">{getToolIcon()}</span>
        <span className="tool-name">{name}</span>
        <span className="tool-id" title={toolUseId}>
          #{toolUseId?.substring(-8)}
        </span>
        <span className="tool-toggle">
          {isExpanded ? '▼' : '▶'}
        </span>
      </div>

      {isExpanded && (
        <div className="tool-content">
          <div className="tool-input">
            <div className="tool-input-label">参数：</div>
            <pre className="tool-input-json">
              {JSON.stringify(input, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};

ToolCallCard.propTypes = {
  toolUseId: PropTypes.string.isRequired,
  name: PropTypes.string.isRequired,
  input: PropTypes.object.isRequired
};

export default ToolCallCard;
