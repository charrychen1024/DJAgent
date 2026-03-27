import React from 'react';
import PropTypes from 'prop-types';
import './TaskTrackingTab.css';

/**
 * TaskTrackingTab Component
 *
 * Displays task tracking with:
 * - Task list with status badges
 * - Collapsible task cards
 * - Task selection support
 * - Task deadline display
 *
 * @component
 * @param {Array} tasks - Array of task objects
 * @param {Object} selectedTask - Currently selected task
 * @param {Function} onSelectTask - Callback when task is selected
 * @param {boolean} tasksCollapsed - Whether task list is collapsed
 * @param {Function} onToggleCollapse - Callback to toggle collapse state
 * @param {Array} filteredTasks - Filtered task list (for search)
 * @param {boolean} loading - Loading state
 * @param {string} className - Additional CSS classes
 */
const TaskTrackingTab = ({
  tasks = [],
  selectedTask = null,
  onSelectTask,
  tasksCollapsed = false,
  onToggleCollapse,
  filteredTasks = null,
  loading = false,
  className = '',
  taskSearchQuery = '',
  onTaskSearchChange = () => {},
  onTaskSearch = () => {}
}) => {
  const displayTasks = filteredTasks !== null ? filteredTasks : tasks;

  return (
    <div className={`task-tracking-tab ${className}`}>
      <div className="task-search-bar">
        <input
          type="text"
          value={taskSearchQuery}
          onChange={(e) => onTaskSearchChange?.(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              onTaskSearch?.();
            }
          }}
          placeholder="搜索任务明细..."
          className="task-search-input"
        />
      </div>

      {(
        <>
          {loading ? (
            <div className="loading-tip">加载中...</div>
          ) : tasks.length === 0 ? (
            <div className="empty-tip">暂无任务</div>
          ) : displayTasks.length === 0 ? (
            <div className="empty-tip">无搜索结果</div>
          ) : (
            <div className="task-list">
              {displayTasks.map(task => (
                <div
                  key={task.task_id}
                  className={`task-card ${selectedTask?.task_id === task.task_id ? 'selected' : ''}`}
                  onClick={() => onSelectTask?.(task)}
                >
                  <div className="task-header">
                    <span className="task-id">{task.task_id}</span>
                    <span className={`task-status ${task.status}`}>
                      {task.status}
                    </span>
                  </div>
                  <div className="task-summary">{task.risk_summary}</div>
                  <div className="task-info">
                    <span>创建: {task.creator_name || task.creator_id}</span>
                    <span>→ {task.assigned_to_name}</span>
                    {task.feedback_deadline && (
                      <span className="task-deadline">
                        截止: {new Date(task.feedback_deadline).toLocaleString('zh-CN', {
                          month: '2-digit',
                          day: '2-digit',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
};

TaskTrackingTab.propTypes = {
  tasks: PropTypes.arrayOf(
    PropTypes.shape({
      task_id: PropTypes.string.isRequired,
      status: PropTypes.string,
      risk_summary: PropTypes.string,
      creator_name: PropTypes.string,
      creator_id: PropTypes.string,
      assigned_to_name: PropTypes.string,
      feedback_deadline: PropTypes.string
    })
  ),
  selectedTask: PropTypes.object,
  onSelectTask: PropTypes.func,
  tasksCollapsed: PropTypes.bool,
  onToggleCollapse: PropTypes.func,
  filteredTasks: PropTypes.array,
  loading: PropTypes.bool,
  className: PropTypes.string
};

export default TaskTrackingTab;
