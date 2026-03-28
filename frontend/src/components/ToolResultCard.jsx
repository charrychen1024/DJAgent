import React, { useState } from 'react';
import PropTypes from 'prop-types';
import './ToolResultCard.css';

/**
 * 工具结果渲染器
 * 
 * 显示工具执行的结果
 * 遵循 Anthropic Tool Result 规范
 */
const ToolResultCard = ({ toolUseId, content, isError }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  // 尝试解析 JSON 内容
  let parsedContent = content;
  let isJson = false;
  
  try {
    if (typeof content === 'string') {
      parsedContent = JSON.parse(content);
      isJson = true;
    }
  } catch {
    // 不是 JSON，保持原样
  }
  
  return (
    <div className={`tool-result-card ${isError ? 'error' : 'success'}`}>
      <div 
        className="tool-result-header" 
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="result-icon">
          {isError ? '❌' : '✅'}
        </span>
        <span className="result-label">
          {isError ? '工具调用失败' : '工具调用成功'}
        </span>
        {toolUseId && (
          <span className="result-id">
            #{toolUseId.substring(-8)}
          </span>
        )}
        <span className="result-toggle">
          {isExpanded ? '▼' : '▶'}
        </span>
      </div>
      
      {isExpanded && (
        <div className="tool-result-content">
          {isJson ? (
            <pre className="result-json">
              {JSON.stringify(parsedContent, null, 2)}
            </pre>
          ) : (
            <div className="result-text">
              {content}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

ToolResultCard.propTypes = {
  toolUseId: PropTypes.string,
  content: PropTypes.any.isRequired,
  isError: PropTypes.bool
};

export default ToolResultCard;
