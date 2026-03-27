import React, { useState, useRef, useCallback, useEffect } from 'react';
import PropTypes from 'prop-types';
import './ChatInput.css';

/**
 * ChatInput Component
 *
 * Universal chat input component supporting:
 * - Text input with multiline support
 * - File upload
 * - Keyboard shortcuts (Enter to send, Shift+Enter for newline)
 * - Loading state
 * - File list display
 * - Skill selection dropdown
 *
 * @component
 */
const ChatInput = ({
  value = '',
  onChange,
  onSend,
  onFileSelect,
  onFileRemove,
  files = [],
  disabled = false,
  loading = false,
  placeholder = '输入消息... (Shift+Enter 换行)',
  userRole = 'manager',
  onSkillButtonClick,
  skillButtonRef
}) => {
  const fileInputRef = useRef(null);
  const textareaRef = useRef(null);
  const [isFocused, setIsFocused] = useState(false);

  // Handle file input change
  const handleFileChange = useCallback((event) => {
    const selectedFiles = Array.from(event.target.files || []);
    onFileSelect?.(selectedFiles);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [onFileSelect]);

  // Reset textarea height to default
  const resetTextareaHeight = useCallback(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = '72px';
    }
  }, []);

  // Handle textarea keydown (for send on Enter)
  const handleKeyDown = useCallback((event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      if ((value.trim() || files.length > 0) && !disabled && !loading) {
        onSend?.();
        resetTextareaHeight();
      }
    }
  }, [value, files.length, disabled, loading, onSend, resetTextareaHeight]);

  // Auto-resize textarea based on content
  const autoResizeTextarea = useCallback(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const scrollHeight = textareaRef.current.scrollHeight;
      const maxHeight = 200;
      const newHeight = Math.min(scrollHeight, maxHeight);
      textareaRef.current.style.height = newHeight + 'px';
    }
  }, []);

  const handleInputChange = useCallback((event) => {
    onChange?.(event.target.value);
    autoResizeTextarea();
  }, [onChange, autoResizeTextarea]);

  useEffect(() => {
    autoResizeTextarea();
  }, [value, autoResizeTextarea]);

  // Handle file remove
  const handleRemoveFile = useCallback((fileToRemove) => {
    onFileRemove?.(fileToRemove);
  }, [onFileRemove]);

  return (
    <div className={`chat-input ${disabled || loading ? 'chat-input--disabled' : ''} ${isFocused ? 'chat-input--focused' : ''}`}>
      {/* File list display */}
      {files.length > 0 && (
        <div className="input-files">
          {files.map((file, idx) => (
            <div key={`${file.name}-${idx}`} className="input-file">
              <span className="file-icon">📎</span>
              <span className="file-name" title={file.name}>
                {file.name}
              </span>
              <button
                className="file-remove-btn"
                onClick={() => handleRemoveFile(file)}
                disabled={disabled || loading}
                aria-label={`Remove ${file.name}`}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Text input */}
      <textarea
        ref={textareaRef}
        className="input-textarea"
        value={value}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        onFocus={() => setIsFocused(true)}
        onBlur={() => setIsFocused(false)}
        disabled={disabled || loading}
        placeholder={placeholder}
        aria-label="Chat message input"
        rows={1}
      />

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        onChange={handleFileChange}
        disabled={disabled || loading}
        style={{ display: 'none' }}
        aria-label="Select files"
      />

      {/* Toolbar */}
      <div className="input-toolbar">
        <div className="toolbar-left">
          <button
            className="toolbar-btn"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled || loading}
            aria-label="Add file"
          >
            <span className="toolbar-btn-icon">📎</span>
            <span className="toolbar-btn-text">上传文件</span>
          </button>
          <button
            className="toolbar-btn"
            disabled={disabled || loading}
            aria-label="Mention"
          >
            <span className="toolbar-btn-icon">👤</span>
            <span className="toolbar-btn-text">选择人员</span>
          </button>
          <button
            ref={skillButtonRef}
            className="toolbar-btn"
            onClick={() => {
              onSkillButtonClick?.();
            }}
            disabled={disabled || loading}
            aria-label="Skills"
          >
            <span className="toolbar-btn-icon">⚙️</span>
            <span className="toolbar-btn-text">使用技能</span>
          </button>
        </div>

        {/* Send button */}
        <button
          className="input-btn input-send-btn"
          onClick={() => {
            onSend?.();
            resetTextareaHeight();
          }}
          disabled={disabled || loading || (!value.trim() && files.length === 0)}
          title={loading ? '发送中...' : '发送消息 (Enter)'}
          aria-label="Send message"
        >
          {loading ? '⏳' : '➤'}
        </button>
      </div>
    </div>
  );
};

ChatInput.propTypes = {
  value: PropTypes.string,
  onChange: PropTypes.func,
  onSend: PropTypes.func,
  onFileSelect: PropTypes.func,
  onFileRemove: PropTypes.func,
  onSkillButtonClick: PropTypes.func,
  files: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string.isRequired
    })
  ),
  disabled: PropTypes.bool,
  loading: PropTypes.bool,
  placeholder: PropTypes.string,
  userRole: PropTypes.oneOf(['manager', 'staff']),
  skillButtonRef: PropTypes.oneOf([PropTypes.object, PropTypes.func])
};

ChatInput.defaultProps = {
  value: '',
  onChange: () => {},
  onSend: () => {},
  onFileSelect: () => {},
  onFileRemove: () => {},
  onSkillButtonClick: () => {},
  files: [],
  disabled: false,
  loading: false,
  placeholder: '输入消息... (Shift+Enter 换行)',
  userRole: 'manager',
  skillButtonRef: null
};

export default ChatInput;
