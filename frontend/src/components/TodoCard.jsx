import React from 'react';
import PropTypes from 'prop-types';
import './TodoCard.css';

/**
 * TodoCard Component
 *
 * Displays a single todo item with:
 * - Priority badge (P0-P3 with color coding)
 * - Type label (e.g. 时间异常, 任务超期)
 * - Title and description
 * - Recommended assignee
 * - Status badge (未处理, 已处理)
 * - Clickable to select and display in right detail panel
 *
 * @component
 * @param {Object} props
 * @param {Object} props.todo - Todo item object
 * @param {string} props.todo.id - Unique identifier
 * @param {string} props.todo.title - Todo title
 * @param {string} props.todo.description - Todo description
 * @param {string} props.todo.type - Todo type (e.g., 时间异常, 运费异常)
 * @param {string} props.todo.priority - Priority level (P0, P1, P2, P3)
 * @param {string} props.todo.status - Status (未处理 or 已处理)
 * @param {string} props.todo.recommended_assignee - Name of recommended assignee
 * @param {boolean} props.isSelected - Whether this todo is currently selected
 * @param {Function} props.onClick - Callback when todo is clicked
 * @param {string} props.className - Additional CSS classes
 */
const TodoCard = ({
  todo,
  isSelected = false,
  onClick,
  className = ''
}) => {
  if (!todo) {
    return null;
  }

  const {
    id,
    title,
    description,
    type,
    priority = 'P3',
    status = '未处理',
    recommended_assignee = '未分配'
  } = todo;

  // 获取分配人名称 - 处理对象和字符串两种情况
  const assigneeName = typeof recommended_assignee === 'object'
    ? recommended_assignee?.name || '未分配'
    : recommended_assignee;

  // Map priority to color class
  const getPriorityColorClass = (priority) => {
    switch (priority) {
      case 'P0':
        return 'priority-p0';
      case 'P1':
        return 'priority-p1';
      case 'P2':
        return 'priority-p2';
      case 'P3':
        return 'priority-p3';
      default:
        return 'priority-p3';
    }
  };

  // Check if handled
  const isHandled = status === '已处理';

  return (
    <div
      className={`todo-card ${isSelected ? 'selected' : ''} ${getPriorityColorClass(priority)} ${className}`}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          onClick?.();
        }
      }}
    >
      {/* Left border indicator - colored by priority */}
      <div className="todo-card-border" />

      <div className="todo-card-content">
        {/* Header row: priority + type + status */}
        <div className="todo-card-header">
          <div className="todo-left-group">
            {/* Priority badge */}
            <span className={`todo-priority ${getPriorityColorClass(priority)}`}>
              {priority}
            </span>

            {/* Type label */}
            <span className="todo-type">{type}</span>
          </div>

          {/* Status badge */}
          <span className={`todo-status ${isHandled ? 'handled' : 'unhandled'}`}>
            {status}
          </span>
        </div>

        {/* Title */}
        <h3 className="todo-title">{title}</h3>

        {/* Description (truncated to 2 lines) */}
        <p className="todo-description">{description}</p>

        {/* Footer: assignee */}
        <div className="todo-footer">
          <span className="todo-assignee">
            👤 {assigneeName}
          </span>
        </div>
      </div>
    </div>
  );
};

TodoCard.propTypes = {
  todo: PropTypes.shape({
    id: PropTypes.string.isRequired,
    title: PropTypes.string.isRequired,
    description: PropTypes.string,
    type: PropTypes.string,
    priority: PropTypes.oneOf(['P0', 'P1', 'P2', 'P3']),
    status: PropTypes.oneOf(['未处理', '已处理']),
    recommended_assignee: PropTypes.string
  }).isRequired,
  isSelected: PropTypes.bool,
  onClick: PropTypes.func,
  className: PropTypes.string
};

export default TodoCard;
