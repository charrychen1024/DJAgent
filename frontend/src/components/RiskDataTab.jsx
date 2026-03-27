import React, { useState } from 'react';
import PropTypes from 'prop-types';
import './RiskDataTab.css';

/**
 * RiskDataTab Component
 *
 * Displays risk data with:
 * - Global search bar
 * - Daily/Monthly data toggle
 * - Risk statistics cards
 * - Risk data table with pagination
 * - Row selection support
 *
 * @component
 * @param {Array} riskData - Array of risk data records
 * @param {Object} riskStats - Risk statistics {high, medium, low}
 * @param {Array} columns - Table column names
 * @param {string} dataTab - Active data tab ('daily' or 'monthly')
 * @param {Function} onTabChange - Callback when data tab changes
 * @param {Array} selectedRows - Array of selected row indices
 * @param {Function} onSelectRow - Callback when row is selected
 * @param {Function} onSelectAll - Callback when select-all is clicked
 * @param {string} globalSearch - Current search query
 * @param {Function} onSearchChange - Callback when search changes
 * @param {Function} onSearch - Callback when search is submitted
 * @param {Function} onAddToChat - Callback to add selected rows to chat
 * @param {boolean} loading - Loading state
 * @param {Array} filteredData - Filtered risk data
 * @param {number} currentPage - Current page number
 * @param {number} pageSize - Items per page
 * @param {Function} onPageChange - Callback when page changes
 * @param {Function} onPageSizeChange - Callback when page size changes
 * @param {Function} onRowClick - Callback when row is clicked to view details
 */
const RiskDataTab = ({
  riskData = [],
  riskStats = { high: 0, medium: 0, low: 0 },
  columns = [],
  dataTab = 'daily',
  onTabChange,
  selectedRows = [],
  onSelectRow,
  onSelectAll,
  globalSearch = '',
  onSearchChange,
  onSearch,
  onAddToChat,
  loading = false,
  filteredData = [],
  currentPage = 1,
  pageSize = 10,
  onPageChange,
  onPageSizeChange,
  onRowClick,
  className = ''
}) => {
  const currentPageData = filteredData.slice((currentPage - 1) * pageSize, currentPage * pageSize);
  const totalPages = Math.ceil(filteredData.length / pageSize);

  return (
    <div className={`risk-data-tab ${className}`}>
      {/* Global search bar */}
      <div className="global-search-bar">
        <input
          type="text"
          value={globalSearch}
          onChange={(e) => onSearchChange?.(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              onSearch?.();
            }
          }}
          placeholder="搜索风险数据明细..."
        />
      </div>

      {/* Tab switch: Daily/Monthly */}
      <div className="data-tab-switch">
        <button
          className={`tab-btn ${dataTab === 'daily' ? 'active' : ''}`}
          onClick={() => onTabChange?.('daily')}
        >
          日度数据
        </button>
        <button
          className={`tab-btn ${dataTab === 'monthly' ? 'active' : ''}`}
          onClick={() => onTabChange?.('monthly')}
        >
          月度数据
        </button>
      </div>

      {/* Risk statistics dashboard */}
      <div className="risk-stats">
        <div className="stat-card high">
          <div className="stat-value">{riskStats.high}</div>
          <div className="stat-label">高风险</div>
        </div>
        <div className="stat-card medium">
          <div className="stat-value">{riskStats.medium}</div>
          <div className="stat-label">中风险</div>
        </div>
        <div className="stat-card low">
          <div className="stat-value">{riskStats.low}</div>
          <div className="stat-label">低风险</div>
        </div>
      </div>

      <div className="section-header">
        <h3>风险明细数据</h3>
        <div className="action-buttons">
          <button
            className="action-btn"
            onClick={onAddToChat}
            disabled={selectedRows.length === 0}
          >
            📤 添加到对话 ({selectedRows.length})
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading-tip">加载中...</div>
      ) : filteredData.length > 0 ? (
        <div className="risk-data-container">
          <div className="risk-table-wrapper">
            <table className="risk-table">
              <thead>
                <tr>
                  <th className="checkbox-col">
                    <input
                      type="checkbox"
                      checked={selectedRows.length === currentPageData.length && currentPageData.length > 0}
                      onChange={onSelectAll}
                    />
                  </th>
                  {columns.map(col => (
                    <th key={col}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {currentPageData.map((row, i) => {
                  const globalIndex = (currentPage - 1) * pageSize + i;
                  return (
                    <tr
                      key={globalIndex}
                      className={selectedRows.includes(globalIndex) ? 'selected-row' : ''}
                      onClick={() => onRowClick?.(row, globalIndex)}
                    >
                      <td className="checkbox-col">
                        <input
                          type="checkbox"
                          checked={selectedRows.includes(globalIndex)}
                          onChange={() => onSelectRow?.(globalIndex)}
                          onClick={(e) => e.stopPropagation()}
                        />
                      </td>
                      {columns.map(col => (
                        <td key={col}>
                          {col === '风险等级' ? (
                            <span className={`risk-level ${row[col]}`}>{row[col] || '-'}</span>
                          ) : (
                            row[col] || '-'
                          )}
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="pagination">
            <div className="page-info">
              共 {filteredData.length} 条数据，每页显示
              <select
                value={pageSize}
                onChange={(e) => onPageSizeChange?.(Number(e.target.value))}
                className="page-size-select"
              >
                <option value={5}>5条</option>
                <option value={10}>10条</option>
                <option value={20}>20条</option>
                <option value={50}>50条</option>
                <option value={100}>100条</option>
              </select>
            </div>
            <div className="page-controls">
              <button
                className="page-btn"
                disabled={currentPage === 1}
                onClick={() => onPageChange?.(currentPage - 1)}
              >
                上一页
              </button>
              <div className="page-numbers">
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  let pageNum;
                  if (totalPages <= 5) {
                    pageNum = i + 1;
                  } else if (currentPage <= 3) {
                    pageNum = i + 1;
                  } else if (currentPage >= totalPages - 2) {
                    pageNum = totalPages - 4 + i;
                  } else {
                    pageNum = currentPage - 2 + i;
                  }
                  return (
                    <button
                      key={pageNum}
                      className={`page-btn ${currentPage === pageNum ? 'active' : ''}`}
                      onClick={() => onPageChange?.(pageNum)}
                    >
                      {pageNum}
                    </button>
                  );
                })}
              </div>
              <button
                className="page-btn"
                disabled={currentPage === totalPages}
                onClick={() => onPageChange?.(currentPage + 1)}
              >
                下一页
              </button>
            </div>
            <div className="page-jump">
              第 <input
                type="number"
                min={1}
                max={totalPages}
                value={currentPage}
                onChange={(e) => {
                  const num = Number(e.target.value);
                  if (num >= 1 && num <= totalPages) {
                    onPageChange?.(num);
                  }
                }}
                className="page-input"
              /> 页
            </div>
          </div>
        </div>
      ) : (
        <div className="empty-tip">暂无风险数据</div>
      )}
    </div>
  );
};

RiskDataTab.propTypes = {
  riskData: PropTypes.array,
  riskStats: PropTypes.shape({
    high: PropTypes.number,
    medium: PropTypes.number,
    low: PropTypes.number
  }),
  columns: PropTypes.array,
  dataTab: PropTypes.oneOf(['daily', 'monthly']),
  onTabChange: PropTypes.func,
  selectedRows: PropTypes.array,
  onSelectRow: PropTypes.func,
  onSelectAll: PropTypes.func,
  globalSearch: PropTypes.string,
  onSearchChange: PropTypes.func,
  onSearch: PropTypes.func,
  onAddToChat: PropTypes.func,
  loading: PropTypes.bool,
  filteredData: PropTypes.array,
  currentPage: PropTypes.number,
  pageSize: PropTypes.number,
  onPageChange: PropTypes.func,
  onPageSizeChange: PropTypes.func,
  onRowClick: PropTypes.func,
  className: PropTypes.string
};

export default RiskDataTab;
