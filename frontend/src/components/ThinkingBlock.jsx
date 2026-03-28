import React, { useState } from 'react';
import PropTypes from 'prop-types';
import './ThinkingBlock.css';

/**
 * Thinking Block 组件
 * 
 * 显示 AI 思考过程，可折叠/展开
 */
const ThinkingBlock = ({ thinking, signature, defaultExpanded = false }) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  // 格式化思考内容
  const formattedThinking = thinking
    .split('\n')
    .filter(line => line.trim())
    .map((line, idx) => (
      <div key={idx} className="thinking-line">
        {line.trim()}
      </div>
    ));

  return (
    <div className="thinking-block">
      <div 
        className="thinking-header" 
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="thinking-icon">🧠</span>
        <span className="thinking-title">思考过程</span>
        <span className="thinking-toggle">
          {isExpanded ? '▼' : '▶'}
        </span>
      </div>

      {isExpanded && (
        <div className="thinking-content">
          <div className="thinking-text">
            {formattedThinking}
          </div>

          {signature && (
            <div className="thinking-signature">
              <span className="signature-label">签名：</span>
              <span className="signature-value">{signature.substring(0, 32)}...</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

ThinkingBlock.propTypes = {
  thinking: PropTypes.string.isRequired,
  signature: PropTypes.string,
  defaultExpanded: PropTypes.bool
};

export default ThinkingBlock;
