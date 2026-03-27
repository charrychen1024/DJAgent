import React, { useState, useRef, useCallback } from 'react';
import PropTypes from 'prop-types';
import TabToday from './TabToday';
import RiskDataTab from './RiskDataTab';
import TaskTrackingTab from './TaskTrackingTab';
import { getTodayUnprocessedTodos } from '../data/mockTodos';
import './TodoTabs.css';

/**
 * TodoTabs Component
 *
 * Left sidebar container with 3 tabs:
 * 1. TabToday - Today's todos grouped by category
 * 2. Risk Data - Risk data table with search, statistics, and pagination
 * 3. Task Tracking - Task tracking list with status badges
 *
 * Features:
 * - Independent tab switching
 * - Collapsible left sidebar with independent state
 * - Smooth transitions between tabs
 * - Status badges showing counts
 * - Full risk data and task management functionality
 * - Draggable divider for resizing panel width
 *
 * @component
 * @param {Object} props
 * @param {Array} props.todos - Array of todo items
 * @param {string} props.selectedTodoId - ID of selected todo
 * @param {Function} props.onSelectTodo - Callback when todo is selected
 * @param {boolean} props.isOpen - Whether left panel is open
 * @param {Function} props.onToggleOpen - Callback to toggle panel open/close
 * @param {Array} props.riskData - Risk data for risk data tab
 * @param {Object} props.riskStats - Risk statistics
 * @param {Array} props.riskColumns - Risk table column names
 * @param {string} props.dataTab - Active data tab ('daily' or 'monthly')
 * @param {Function} props.onDataTabChange - Callback when data tab changes
 * @param {Array} props.selectedRiskRows - Selected risk data rows
 * @param {Function} props.onSelectRiskRow - Callback to select risk row
 * @param {Function} props.onSelectAllRiskRows - Callback to select all risk rows
 * @param {string} props.globalSearch - Global search query
 * @param {Function} props.onGlobalSearchChange - Callback when search changes
 * @param {Function} props.onGlobalSearch - Callback when search is submitted
 * @param {Function} props.onAddToChat - Callback to add selected rows to chat
 * @param {boolean} props.riskLoading - Risk data loading state
 * @param {Array} props.filteredRiskData - Filtered risk data
 * @param {number} props.riskCurrentPage - Current page for risk data
 * @param {number} props.riskPageSize - Page size for risk data
 * @param {Function} props.onRiskPageChange - Callback for page change
 * @param {Function} props.onRiskPageSizeChange - Callback for page size change
 * @param {Function} props.onRiskRowClick - Callback when risk row is clicked
 * @param {Array} props.tasks - Array of tasks
 * @param {Object} props.selectedTask - Selected task
 * @param {Function} props.onSelectTask - Callback when task is selected
 * @param {boolean} props.tasksCollapsed - Whether task list is collapsed
 * @param {Function} props.onToggleTasks - Callback to toggle tasks collapse
 * @param {Array} props.filteredTasks - Filtered tasks
 * @param {boolean} props.tasksLoading - Tasks loading state
 * @param {number} props.width - Panel width (controlled from parent)
 * @param {Function} props.onWidthChange - Callback when width changes
 * @param {string} props.className - Additional CSS classes
 */
const TodoTabs = ({
  todos = [],
  selectedTodoId = null,
  onSelectTodo,
  isOpen = true,
  onToggleOpen,
  // Risk data tab props
  riskData = [],
  riskStats = { high: 0, medium: 0, low: 0 },
  riskColumns = [],
  dataTab = 'daily',
  onDataTabChange,
  selectedRiskRows = [],
  onSelectRiskRow,
  onSelectAllRiskRows,
  globalSearch = '',
  onGlobalSearchChange,
  onGlobalSearch,
  onAddToChat,
  riskLoading = false,
  filteredRiskData = [],
  riskCurrentPage = 1,
  riskPageSize = 10,
  onRiskPageChange,
  onRiskPageSizeChange,
  onRiskRowClick,
  // Task tracking tab props
  tasks = [],
  selectedTask = null,
  onSelectTask,
  tasksCollapsed = false,
  onToggleTasks,
  filteredTasks = null,
  tasksLoading = false,
  // Resize props
  width = 320,
  onWidthChange,
  className = ''
}) => {
  const [activeTab, setActiveTab] = useState('today'); // 'today', 'risk-data', 'task-tracking'
  const containerRef = useRef(null);
  const [isResizing, setIsResizing] = useState(false);

  const handleResizeStart = useCallback(() => {
    setIsResizing(true);
  }, []);

  const handleResizeEnd = useCallback(() => {
    setIsResizing(false);
  }, []);

  const handleResizeMove = useCallback((e) => {
    if (!isResizing || !containerRef.current) return;

    const container = containerRef.current.parentElement;
    if (!container) return;

    const containerRect = container.getBoundingClientRect();
    const newWidth = e.clientX - containerRect.left;

    // Constrain width between min (260px) and max (450px)
    const constrainedWidth = Math.max(260, Math.min(450, newWidth));

    onWidthChange?.(constrainedWidth);
  }, [isResizing, onWidthChange]);

  // Calculate stats for tab badges
  const getTodoStats = () => {
    // Use the same function that TabToday uses to ensure consistency
    const todayUnprocessed = getTodayUnprocessedTodos(todos);
    const p0Count = todayUnprocessed.filter(t => t.priority === 'P0').length;
    return { unprocessed: todayUnprocessed.length, p0Count };
  };

  const stats = getTodoStats();

  if (!isOpen) {
    return (
      <div className={`todo-tabs todo-tabs-closed ${className}`}>
        <button
          className="toggle-btn"
          onClick={() => onToggleOpen?.(true)}
          title="展开左栏"
        >
          ▶
        </button>
      </div>
    );
  }

  return (
    <>
      {isResizing && (
        <div
          className="resize-overlay"
          onMouseMove={handleResizeMove}
          onMouseUp={handleResizeEnd}
          onMouseLeave={handleResizeEnd}
        />
      )}
      <div
        ref={containerRef}
        className={`todo-tabs todo-tabs-open ${className}`}
        style={isOpen ? { width: `${width}px` } : {}}
      >
        {/* Tab headers */}
        <div className="tabs-header">
          {/* Close/collapse button */}
          <button
            className="toggle-btn"
            onClick={() => onToggleOpen?.(false)}
            title="折叠左栏"
          >
            ◀
          </button>

          {/* Tab buttons */}
          <div className="tabs-buttons">
            <button
              className={`tab-btn ${activeTab === 'today' ? 'active' : ''}`}
              onClick={() => setActiveTab('today')}
            >
              <span className="tab-label">今日待办</span>
              {stats.unprocessed > 0 && (
                <span className="tab-badge badge-normal">{stats.unprocessed}</span>
              )}
            </button>

            <button
              className={`tab-btn ${activeTab === 'risk-data' ? 'active' : ''}`}
              onClick={() => setActiveTab('risk-data')}
            >
              <span className="tab-label">风险数据</span>
            </button>

            <button
              className={`tab-btn ${activeTab === 'task-tracking' ? 'active' : ''}`}
              onClick={() => setActiveTab('task-tracking')}
            >
              <span className="tab-label">任务追踪</span>
            </button>
          </div>
        </div>

        {/* Tab content */}
        <div className="tabs-content">
          {/* Tab: Today Todos */}
          {activeTab === 'today' && (
            <TabToday
              todos={todos}
              selectedTodoId={selectedTodoId}
              onSelectTodo={onSelectTodo}
            />
          )}

          {/* Tab: Risk Data */}
          {activeTab === 'risk-data' && (
            <RiskDataTab
              riskData={riskData}
              riskStats={riskStats}
              columns={riskColumns}
              dataTab={dataTab}
              onTabChange={onDataTabChange}
              selectedRows={selectedRiskRows}
              onSelectRow={onSelectRiskRow}
              onSelectAll={onSelectAllRiskRows}
              globalSearch={globalSearch}
              onSearchChange={onGlobalSearchChange}
              onSearch={onGlobalSearch}
              onAddToChat={onAddToChat}
              loading={riskLoading}
              filteredData={filteredRiskData}
              currentPage={riskCurrentPage}
              pageSize={riskPageSize}
              onPageChange={onRiskPageChange}
              onPageSizeChange={onRiskPageSizeChange}
              onRowClick={onRiskRowClick}
            />
          )}

          {/* Tab: Task Tracking */}
          {activeTab === 'task-tracking' && (
            <TaskTrackingTab
              tasks={tasks}
              selectedTask={selectedTask}
              onSelectTask={onSelectTask}
              tasksCollapsed={tasksCollapsed}
              onToggleCollapse={onToggleTasks}
              filteredTasks={filteredTasks}
              loading={tasksLoading}
            />
          )}
        </div>
      </div>

      {/* Resizable divider - only show when open */}
      {isOpen && (
        <div
          className="resize-handle"
          onMouseDown={handleResizeStart}
          title="拖动调整宽度"
        />
      )}
    </>
  );
};

TodoTabs.propTypes = {
  // Todo tab props
  todos: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      priority: PropTypes.oneOf(['P0', 'P1', 'P2', 'P3']),
      status: PropTypes.oneOf(['未处理', '已处理'])
    })
  ),
  selectedTodoId: PropTypes.string,
  onSelectTodo: PropTypes.func,
  isOpen: PropTypes.bool,
  onToggleOpen: PropTypes.func,
  // Risk data tab props
  riskData: PropTypes.array,
  riskStats: PropTypes.object,
  riskColumns: PropTypes.array,
  dataTab: PropTypes.oneOf(['daily', 'monthly']),
  onDataTabChange: PropTypes.func,
  selectedRiskRows: PropTypes.array,
  onSelectRiskRow: PropTypes.func,
  onSelectAllRiskRows: PropTypes.func,
  globalSearch: PropTypes.string,
  onGlobalSearchChange: PropTypes.func,
  onGlobalSearch: PropTypes.func,
  onAddToChat: PropTypes.func,
  riskLoading: PropTypes.bool,
  filteredRiskData: PropTypes.array,
  riskCurrentPage: PropTypes.number,
  riskPageSize: PropTypes.number,
  onRiskPageChange: PropTypes.func,
  onRiskPageSizeChange: PropTypes.func,
  onRiskRowClick: PropTypes.func,
  // Task tracking tab props
  tasks: PropTypes.array,
  selectedTask: PropTypes.object,
  onSelectTask: PropTypes.func,
  tasksCollapsed: PropTypes.bool,
  onToggleTasks: PropTypes.func,
  filteredTasks: PropTypes.array,
  tasksLoading: PropTypes.bool,
  // Resize props
  width: PropTypes.number,
  onWidthChange: PropTypes.func,
  className: PropTypes.string
};

export default TodoTabs;
