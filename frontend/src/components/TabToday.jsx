import React, { useMemo, useState } from 'react';
import PropTypes from 'prop-types';
import TodoCard from './TodoCard';
import { getTodayUnprocessedTodos, groupTodosByCategory, getTodoStats } from '../data/mockTodos';
import './TabToday.css';

/**
 * TabToday Component
 *
 * Displays today's unprocessed todo items grouped by category and type,
 * sorted by priority (P0 → P3).
 *
 * @component
 * @param {Array} todos - Array of todo items
 * @param {string} selectedTodoId - ID of currently selected todo
 * @param {Function} onSelectTodo - Callback when a todo is selected
 * @param {string} className - Additional CSS classes
 */
const TabToday = ({
  todos = [],
  selectedTodoId = null,
  onSelectTodo,
  className = ''
}) => {
  // Get today's unprocessed todos and group them by category
  const groupedTodos = useMemo(() => {
    const todayTodos = getTodayUnprocessedTodos(todos);
    return groupTodosByCategory(todayTodos);
  }, [todos]);

  // Get todo statistics per category
  const todoStats = useMemo(() => {
    const todayTodos = getTodayUnprocessedTodos(todos);
    return getTodoStats(todayTodos);
  }, [todos]);

  // Category title mapping and order
  const categoryMap = {
    '运单数据问题': { title: '风险运单与客户', order: 1 },
    '任务问题': { title: '异常下发任务', order: 2 },
    '异常问题': { title: '其他异常', order: 3 }
  };

  const sortedCategories = Object.keys(groupedTodos).sort(
    (a, b) => (categoryMap[a]?.order || 999) - (categoryMap[b]?.order || 999)
  );

  // Track collapsed state for each category
  const [collapsedCategories, setCollapsedCategories] = useState({});

  const toggleCategory = (category) => {
    setCollapsedCategories(prev => ({
      ...prev,
      [category]: !prev[category]
    }));
  };

  return (
    <div className={`tab-today ${className}`}>
      {sortedCategories.length === 0 ? (
        <div className="tab-empty-state">
          <div className="empty-icon">✓</div>
          <p className="empty-title">太棒了！</p>
          <p className="empty-description">今天没有待处理项目</p>
        </div>
      ) : (
        <>
          {sortedCategories.map((category) => (
            <div key={category} className="todo-category-group">
              {/* Category header with count and divider */}
              <div
                className="category-header"
                onClick={() => toggleCategory(category)}
                title="点击展开/折叠"
              >
                <h4 className="category-title">{categoryMap[category]?.title || category}</h4>
                <span className="category-count">
                  {todoStats[category] || 0}
                </span>
              </div>

              {/* Category content - group by type */}
              {!collapsedCategories[category] && (
                <div className="category-content">
                  {Object.entries(groupedTodos[category]).map(([type, todoList]) => (
                    <div key={type} className="type-group">
                      {/* Todo cards for this type - no subheader */}
                      <div className="todo-list">
                        {todoList.map((todo) => (
                          <TodoCard
                            key={todo.id}
                            todo={todo}
                            isSelected={selectedTodoId === todo.id}
                            onClick={() => onSelectTodo?.(todo.id)}
                          />
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </>
      )}
    </div>
  );
};

TabToday.propTypes = {
  todos: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string.isRequired,
      title: PropTypes.string.isRequired,
      category: PropTypes.string,
      type: PropTypes.string,
      priority: PropTypes.oneOf(['P0', 'P1', 'P2', 'P3']),
      status: PropTypes.oneOf(['未处理', '已处理'])
    })
  ),
  selectedTodoId: PropTypes.string,
  onSelectTodo: PropTypes.func,
  className: PropTypes.string
};

export default TabToday;
