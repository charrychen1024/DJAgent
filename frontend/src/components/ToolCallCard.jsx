import React, { useState } from 'react';
import PropTypes from 'prop-types';
import './ToolCallCard.css';

/**
 * 工具调用渲染器 - 简约版
 *
 * 显示 AI 调用的工具，使用行内徽章样式
 */
const ToolCallCard = ({ toolUseId, name, input }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // 安全获取 tool name
  const toolName = name || ''

  return (
    <div className={`tool-call-card ${isExpanded ? 'expanded' : ''}`}>
      <div
        className="tool-badge"
        onClick={() => setIsExpanded(!isExpanded)}
        title={toolUseId}
      >
        <span className="tool-icon">🔧</span>
        <span className="tool-name">{toolName}</span>
        <span className="tool-toggle">
          {isExpanded ? '▼' : '▶'}
        </span>
      </div>

      {isExpanded && (
        <div className="tool-content">
          <pre style={{
            margin: '8px 0',
            padding: '8px',
            background: 'var(--bg-gray, #f5f5f5)',
            borderRadius: '4px',
            fontSize: '11px',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word'
          }}>
            {input ? JSON.stringify(input, null, 2) : '{}'}
          </pre>
        </div>
      )}
    </div>
  );
};

ToolCallCard.propTypes = {
  toolUseId: PropTypes.string,
  name: PropTypes.string,
  input: PropTypes.object
};

export default ToolCallCard;
