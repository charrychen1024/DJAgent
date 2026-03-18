import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import './App.css'

const API_BASE = 'http://127.0.0.1:5005/api'

// 登录页面组件 - 带角色卡片
function LoginPage({ users, onLogin, loading }) {
  const [selectedRole, setSelectedRole] = useState(null)
  const [selectedUserId, setSelectedUserId] = useState('')

  const filteredUsers = selectedRole 
    ? users.filter(u => selectedRole === 'manager' 
        ? u.role === '业务负责人' || u.role === '普通分析人员'
        : u.role === '一线操作人员')
    : []

  const handleLogin = () => {
    if (selectedUserId) {
      const user = users.find(u => u.user_id === selectedUserId)
      if (user) onLogin(user)
    }
  }

  if (loading) {
    return (
      <div className="App login-page">
        <div className="login-container">
          <div className="login-brand">
            <div className="login-logo">🛡️</div>
          </div>
          <h1>风控数字员工</h1>
          <p className="subtitle">加载中...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="App login-page">
      <div className="login-container">
        <div className="login-brand">
          <div className="login-logo">🛡️</div>
        </div>
        <h1>风控数字员工</h1>
        <p className="subtitle">请选择您的身份开始使用</p>
        
        {/* 角色选择卡片 */}
        <div className="role-cards">
          <div 
            className={`role-card manager ${selectedRole === 'manager' ? 'selected' : ''}`}
            onClick={() => { setSelectedRole('manager'); setSelectedUserId('') }}
          >
            <div className="role-icon">👔</div>
            <div className="role-info">
              <div className="role-name">业务负责人</div>
              <div className="role-desc">数据分析 · 任务管理 · 决策支持</div>
            </div>
            <div className="role-check">{selectedRole === 'manager' ? '✓' : ''}</div>
          </div>
          
          <div 
            className={`role-card staff ${selectedRole === 'staff' ? 'selected' : ''}`}
            onClick={() => { setSelectedRole('staff'); setSelectedUserId('') }}
          >
            <div className="role-icon">👥</div>
            <div className="role-info">
              <div className="role-name">一线员工</div>
              <div className="role-desc">任务执行 · 信息反馈 · 协作沟通</div>
            </div>
            <div className="role-check">{selectedRole === 'staff' ? '✓' : ''}</div>
          </div>
        </div>

        {/* 用户下拉选择 */}
        {selectedRole && (
          <select 
            className="user-select"
            value={selectedUserId}
            onChange={(e) => setSelectedUserId(e.target.value)}
          >
            <option value="" disabled>选择用户...</option>
            {filteredUsers.map(user => (
              <option key={user.user_id} value={user.user_id}>
                {user.username} ({user.department})
              </option>
            ))}
          </select>
        )}

        <button 
          className="login-btn"
          onClick={handleLogin}
          disabled={!selectedUserId}
        >
          登录
        </button>
      </div>
    </div>
  )
}

// 业务负责人工作区
function ManagerWorkspace({ currentUser, selectedRegion, onAddToChat }) {
  const [tasks, setTasks] = useState([])
  const [allRiskData, setAllRiskData] = useState([])
  const [selectedRows, setSelectedRows] = useState([])
  const [selectedTask, setSelectedTask] = useState(null)
  const [chatMessages, setChatMessages] = useState([])
  const [taskFeedback, setTaskFeedback] = useState(null)
  const [inputMessage, setInputMessage] = useState('')
  const [pendingFiles, setPendingFiles] = useState([]) // 待发送的文件列表
  const [loading, setLoading] = useState({ tasks: false, riskData: false, chat: false })
  // 是否处于初始对话状态（无消息时显示居中样式）
  const [isInitialChat, setIsInitialChat] = useState(true)
  // 功能卡片预设消息
  const quickPrompts = [
    { id: 1, icon: '📊', text: '请帮我分析今天的风险运单明细数据，对这些数据进行各个维度的分析', label: '今日风险分析' },
    { id: 2, icon: '🔍', text: '请帮我分析本月重点关注的客户、风险运单、风险项和风险指标', label: '月度重点风险分析' },
    { id: 3, icon: '📋', text: '请帮我统计本月下发的任务情况，分析各状态任务数量、类型分布，以及存在风险的任务', label: '任务下发统计' },
    { id: 4, icon: '⚙️', text: '我想创建一个自定义任务/工作流，请引导我描述分析思路、分析数据、下发类型和执行人，我将常用的工作流程创建为自动化任务', label: '创建自定义任务' },
  ]
  // 分页相关状态
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  // 筛选相关状态
  const [searchField, setSearchField] = useState('')
  const [searchValue, setSearchValue] = useState('')
  const [globalSearch, setGlobalSearch] = useState('')
  const messagesEndRef = useRef(null)
  const fileInputRef = useRef(null)
  const inputTextareaRef = useRef(null)
  const [leftWidth, setLeftWidth] = useState(35)
  const [rightWidth, setRightWidth] = useState(25)
  const [isDraggingLeft, setIsDraggingLeft] = useState(false)
  const [isDraggingRight, setIsDraggingRight] = useState(false)

  // Tab切换状态：每日/每月
  const [dataTab, setDataTab] = useState('daily')
  // 月度风险数据
  const [allMonthlyRiskData, setAllMonthlyRiskData] = useState([])
  const [tasksCollapsed, setTasksCollapsed] = useState(false)
  // 添加右侧面板展开状态
  const [rightPanelOpen, setRightPanelOpen] = useState(false)

  useEffect(() => {
    if (currentUser?.user_id) {
      fetchTasks()
      fetchAllRiskData()
    }
  }, [currentUser?.user_id])

  // SSE 事件监听 - 实时接收任务通知
  useEffect(() => {
    if (!currentUser?.user_id) return

    const eventSource = new EventSource(`${API_BASE}/events/${currentUser.user_id}`)

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        console.log('[SSE] 收到事件:', data.type, data)

        if (data.type === 'task_created') {
          // Manager 创建了新任务，刷新任务列表
          console.log('[SSE] 任务创建:', data.task_id)
          fetchTasks()
        } else if (data.type === 'task_completed' || data.type === 'task_updated') {
          // 任务状态更新（Staff 反馈完成），刷新任务列表和详情
          console.log('[SSE] 任务更新:', data.task_id, data.status)
          fetchTasks()
          // 如果当前选中的任务就是被更新的任务，刷新详情
          if (selectedTask && selectedTask.task_id === data.task_id) {
            fetchTaskFeedback(data.task_id)
          }
        }
      } catch (err) {
        console.error('[SSE] 解析事件失败:', err)
      }
    }

    eventSource.onerror = (err) => {
      console.error('[SSE] 连接错误:', err)
      // 自动重连
      eventSource.close()
      console.log('[SSE] 3秒后尝试重新连接...')
      setTimeout(() => {
        if (currentUser?.user_id) {
          const newSource = new EventSource(`${API_BASE}/events/${currentUser.user_id}`)
          console.log('[SSE] 重新连接成功')
        }
      }, 3000)
    }

    return () => {
      eventSource.close()
      console.log('[SSE] Manager 断开连接')
    }
  }, [currentUser?.user_id, selectedTask])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  // 自动调整输入框高度
  useEffect(() => {
    const textarea = inputTextareaRef.current
    if (textarea) {
      // 重置高度，然后设置 scrollHeight，实现自动增长
      textarea.style.height = 'auto'
      const newHeight = Math.min(textarea.scrollHeight, 150) // 最大高度 150px
      textarea.style.height = newHeight + 'px'
    }
  }, [inputMessage])

  useEffect(() => {
    if (isDraggingLeft || isDraggingRight) {
      const handleMouseMove = (e) => {
        if (isDraggingLeft) {
          const newWidth = (e.clientX / window.innerWidth) * 100
          if (newWidth > 20 && newWidth < 50) setLeftWidth(newWidth)
        }
        if (isDraggingRight) {
          const newWidth = ((window.innerWidth - e.clientX) / window.innerWidth) * 100
          if (newWidth > 15 && newWidth < 40) setRightWidth(newWidth)
        }
      }
      const handleMouseUp = () => {
        setIsDraggingLeft(false)
        setIsDraggingRight(false)
      }
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      return () => {
        document.removeEventListener('mousemove', handleMouseMove)
        document.removeEventListener('mouseup', handleMouseUp)
      }
    }
  }, [isDraggingLeft, isDraggingRight])

  // 模拟任务数据
  const mockTasks = [
    { task_id: 'TASK_001', risk_summary: '运单WLYD001重量异常核查', status: '已下发', assigned_to_name: '刘伟快递', created_time: '2026-03-01 10:00', creator_name: '王经理' },
    { task_id: 'TASK_002', risk_summary: '运单WLYD002超时派送核查', status: '反馈完成', assigned_to_name: '刘秀英快递', created_time: '2026-03-01 14:30', creator_name: '王经理', completed_time: '2026-03-01 16:00' },
    { task_id: 'TASK_003', risk_summary: '运单WLYD003未及时签收核查', status: '已创建', assigned_to_name: '黄强快递', created_time: '2026-03-02 09:00', creator_name: '王经理' },
  ]

  const fetchTasks = async () => {
    // 没有用户时不获取任务
    if (!currentUser?.user_id) {
      setTasks([])
      return
    }
    setLoading(prev => ({ ...prev, tasks: true }))
    try {
      // 根据当前Tab获取对应类型的任务（日度/月度）
      const taskType = dataTab === 'daily' ? '日度' : '月度'
      const url = `${API_BASE}/tasks?user_id=${currentUser.user_id}&task_type=${taskType}`
      const response = await fetch(url)
      const data = await response.json()
      setTasks(data.length > 0 ? data : [])
    } catch (err) {
      console.error('[ERROR] 获取任务失败:', err)
      setTasks([])
    } finally {
      setLoading(prev => ({ ...prev, tasks: false }))
    }
  }

  // 获取任务反馈详情
  const fetchTaskFeedback = async (taskId) => {
    try {
      const response = await fetch(`${API_BASE}/feedback/${taskId}`)
      const data = await response.json()
      setTaskFeedback(data)
    } catch (err) {
      console.error('[ERROR] 获取任务反馈失败:', err)
    }
  }

  const fetchAllRiskData = async () => {
    setLoading(prev => ({ ...prev, riskData: true }))
    const allData = []
    for (let i = 1; i <= 10; i++) {
      try {
        const filename = `00${i}`
        const response = await fetch(`${API_BASE}/risk-data/${filename}`)
        if (response.ok) {
          const data = await response.json()
          const actualData = data.data || data
          if (actualData && actualData.length > 0) {
            allData.push(...actualData.map(d => ({ ...d, source: `risk_data_${filename}.csv` })))
          }
        }
      } catch (e) {}
    }
    console.log(`[INFO] 加载了 ${allData.length} 条风险数据`)
    setAllRiskData(allData)
    setLoading(prev => ({ ...prev, riskData: false }))
  }

  // 获取月度风险数据
  const fetchMonthlyRiskData = async () => {
    setLoading(prev => ({ ...prev, riskData: true }))
    const allData = []
    try {
      const response = await fetch(`${API_BASE}/risk-data/monthly`)
      if (response.ok) {
        const files = await response.json()
        for (const file of files) {
          if (file.data && file.data.length > 0) {
            allData.push(...file.data.map(d => ({ ...d, source: file.filename, month: file.month })))
          }
        }
      }
    } catch (e) {
      console.error('[ERROR] 获取月度风险数据失败:', e)
    }
    console.log(`[INFO] 加载了 ${allData.length} 条月度风险数据`)
    setAllMonthlyRiskData(allData)
    setLoading(prev => ({ ...prev, riskData: false }))
  }

  // Tab切换时加载数据和任务
  useEffect(() => {
    if (dataTab === 'daily') {
      fetchAllRiskData()
    } else {
      fetchMonthlyRiskData()
    }
    // 切换Tab时也重新获取对应类型的任务
    fetchTasks()
  }, [dataTab])

  // 获取所有字段名
  const getAllColumns = () => {
    if (filteredRiskData.length === 0) return []
    return Object.keys(filteredRiskData[0]).filter(k => k !== 'source')
  }

  // 全选/取消全选
  const handleSelectAll = () => {
    if (selectedRows.length === filteredRiskData.length) {
      setSelectedRows([])
    } else {
      setSelectedRows(filteredRiskData.map((_, i) => i));
    }
  }

  // 选择/取消单行
  const handleSelectRow = (index) => {
    if (selectedRows.includes(index)) {
      setSelectedRows(selectedRows.filter(i => i !== index))
    } else {
      setSelectedRows([...selectedRows, index])
    }
  }

  // 一键添加到聊天框
  const handleAddSelectedToChat = () => {
    if (selectedRows.length === 0) return
    const selectedData = selectedRows.map(i => filteredRiskData[i])

    // 显示所有字段（排除 source）
    const summary = selectedData.map(d => {
      const entries = Object.entries(d).filter(([k]) => k !== 'source')
      return entries.map(([k, v]) => `${k}: ${v}`).join(', ')
    }).join('\n')

    const message = `我选择了${selectedRows.length}条风险数据，请帮我分析：\n${summary}`
    setInputMessage(message)
  }

  const handleTaskClick = async (task) => {
    // 只更新任务详情和反馈，不刷新聊天记录
    setSelectedTask(task)
    setRightPanelOpen(true)
    setTaskFeedback(null)
    try {
      // 只获取反馈信息，不影响聊天历史
      const feedbackRes = await fetch(`${API_BASE}/feedback/${task.task_id}`)
      if (feedbackRes.ok) {
        const feedbackData = await feedbackRes.json()
        setTaskFeedback(feedbackData)
      }
    } catch (err) {
      console.error('[ERROR] 获取任务信息失败:', err)
    }
  }

  // 文件选择后添加到待发送列表
  const handleFileUpload = (e) => {
    const files = Array.from(e.target.files || [])
    if (files.length === 0) return

    const newFiles = files.map(file => ({
      id: Date.now() + Math.random(),
      name: file.name,
      size: file.size,
      type: file.type,
      file: file
    }))

    setPendingFiles(prev => [...prev, ...newFiles])
    e.target.value = '' // 清空input，允许重复选择同一文件
  }

  // 移除待发送文件
  const handleRemovePendingFile = (fileId) => {
    setPendingFiles(prev => prev.filter(f => f.id !== fileId))
  }

  // 发送消息（包含待发送的文件）
  const handleSendMessage = async () => {
    if (!inputMessage.trim() && pendingFiles.length === 0) return

    // 先将用户消息和文件显示在对话框
    const fileDesc = pendingFiles.length > 0
      ? `\n[附件: ${pendingFiles.map(f => f.name).join(', ')}]`
      : ''

    const userMessage = {
      sender: 'user',
      message: inputMessage + fileDesc,
      timestamp: new Date().toLocaleString(),
      files: pendingFiles.map(f => ({ name: f.name, type: f.type }))
    }
    setChatMessages(prev => [...prev, userMessage])
    setIsInitialChat(false) // 发送消息后退出初始状态

    const messageToSend = inputMessage
    setInputMessage('')
    setPendingFiles([]) // 清空待发送文件
    setLoading(prev => ({ ...prev, chat: true }))

    try {
      // 构建 FormData 发送消息和文件
      const formData = new FormData()
      formData.append('message', messageToSend)
      formData.append('user_id', currentUser.user_id)
      formData.append('username', currentUser.username)
      if (selectedTask) {
        formData.append('task_id', selectedTask.task_id)
      }

      // 添加文件
      pendingFiles.forEach(f => {
        formData.append('files', f.file, f.name)
      })

      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        body: formData
      })

      const data = await response.json()
      setChatMessages(prev => [...prev, { sender: 'agent', message: data.message, timestamp: data.timestamp }])
      fetchTasks()
    } catch (err) {
      console.error('[ERROR] 发送消息失败:', err)
      setChatMessages(prev => [...prev, { sender: 'agent', message: '抱歉，发送消息失败，请稍后重试。', timestamp: new Date().toLocaleString() }])
    } finally {
      setLoading(prev => ({ ...prev, chat: false }))
    }
  }

  // 当前显示的数据源（根据Tab）
  const currentRiskData = dataTab === 'daily' ? allRiskData : allMonthlyRiskData

  // 分页逻辑
  const filteredRiskData = (() => {
    // 先按地区筛选
    let data = selectedRegion 
      ? currentRiskData.filter(d => d.region === selectedRegion)
      : currentRiskData
    // 全局搜索
    if (globalSearch.trim()) {
      const searchTerm = globalSearch.toLowerCase()
      data = data.filter(row => {
        return Object.values(row).some(val => {
          if (val == null) return false
          return String(val).toLowerCase().includes(searchTerm)
        })
      })
    }
    // 字段筛选
    if (searchField && searchValue.trim()) {
      const searchVal = searchValue.toLowerCase()
      data = data.filter(row => {
        const fieldValue = row[searchField]
        if (fieldValue == null) return false
        return String(fieldValue).toLowerCase().includes(searchVal)
      })
    }
    return data
  })()

  const totalPages = Math.ceil(filteredRiskData.length / pageSize)
  const currentPageData = filteredRiskData.slice((currentPage - 1) * pageSize, currentPage * pageSize)

  // 任务列表过滤逻辑
  const filteredTasks = (() => {
    if (!globalSearch.trim()) return tasks
    const searchTerm = globalSearch.toLowerCase()
    return tasks.filter(task => {
      return Object.values(task).some(val => {
        if (val == null) return false
        return String(val).toLowerCase().includes(searchTerm)
      })
    })
  })()

  // 筛选处理函数
  const handleSearch = () => {
    setCurrentPage(1)  // 筛选时重置到第一页
    setSelectedRows([]) // 清除选中项
  }

  const handleResetSearch = () => {
    setSearchField('')
    setSearchValue('')
    setCurrentPage(1)
    setSelectedRows([])
  }

  // 全局搜索处理函数
  const handleGlobalSearch = () => {
    // 全局搜索会在filteredRiskData中过滤
    setCurrentPage(1)
    setSelectedRows([])
  }

  const handleGlobalSearchKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleGlobalSearch()
    }
  }

  // 重置分页到第一页当风险数据变化时
  useEffect(() => {
    setCurrentPage(1)
  }, [allRiskData])

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage)
      setSelectedRows([]) // 切换页面时清除选中项
    }
  }

  const handlePageSizeChange = (newSize) => {
    setPageSize(newSize)
    setCurrentPage(1) // 改变每页条数时回到第一页
    setSelectedRows([])
  }

  const columns = getAllColumns()

  // 计算风险统计
  const riskStats = {
    high: filteredRiskData.filter(d => d['风险等级'] === '高').length,
    medium: filteredRiskData.filter(d => d['风险等级'] === '中').length,
    low: filteredRiskData.filter(d => d['风险等级'] === '低').length,
  }

  return (
    <div className="workspace manager-workspace">
      <div className="sidebar left" style={{ width: `${leftWidth}%` }}>
        <div className="risk-data-section">
          {/* 全局搜索栏 */}
          <div className="global-search-bar">
            <input
              type="text"
              value={globalSearch}
              onChange={e => setGlobalSearch(e.target.value)}
              onKeyDown={handleGlobalSearchKeyDown}
              placeholder="搜索风险明细和任务..."
            />
            <button onClick={handleGlobalSearch}>搜索</button>
          </div>

          {/* Tab切换：每日/每月 */}
          <div className="data-tab-switch">
            <button 
              className={`tab-btn ${dataTab === 'daily' ? 'active' : ''}`}
              onClick={() => setDataTab('daily')}
            >
              日度数据
            </button>
            <button 
              className={`tab-btn ${dataTab === 'monthly' ? 'active' : ''}`}
              onClick={() => setDataTab('monthly')}
            >
              月度数据
            </button>
          </div>

          {/* 风险统计看板 */}
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
            <h3>📊 风险明细数据</h3>
            <div className="action-buttons">
              <button
                className="action-btn"
                onClick={handleAddSelectedToChat}
                disabled={selectedRows.length === 0}
              >
                📤 添加到对话 ({selectedRows.length})
              </button>
            </div>
          </div>
          {loading.riskData ? (
            <div className="loading-tip">加载中...</div>
          ) : filteredRiskData.length > 0 ? (
            <div className="risk-data-container">
              <div className="risk-table-wrapper">
                <table className="risk-table">
                  <thead>
                    <tr>
                      <th className="checkbox-col">
                        <input 
                          type="checkbox" 
                          checked={selectedRows.length === currentPageData.length && currentPageData.length > 0}
                          onChange={handleSelectAll}
                        />
                      </th>
                      {columns.map(col => (
                        <th key={col}>{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {currentPageData.map((row, i) => {
                      const globalIndex = (currentPage - 1) * pageSize + i
                      return (
                        <tr key={globalIndex} className={selectedRows.includes(globalIndex) ? 'selected-row' : ''}>
                          <td className="checkbox-col">
                            <input 
                              type="checkbox" 
                              checked={selectedRows.includes(globalIndex)}
                              onChange={() => handleSelectRow(globalIndex)}
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
                      )
                    })}
                  </tbody>
                </table>
              </div>
              {/* 分页组件 */}
              <div className="pagination">
                <div className="page-info">
                  共 {filteredRiskData.length} 条数据，每页显示 
                  <select value={pageSize} onChange={(e) => handlePageSizeChange(Number(e.target.value))} className="page-size-select">
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
                    onClick={() => handlePageChange(currentPage - 1)}
                  >
                    上一页
                  </button>
                  <div className="page-numbers">
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      let pageNum
                      if (totalPages <= 5) {
                        pageNum = i + 1
                      } else if (currentPage <= 3) {
                        pageNum = i + 1
                      } else if (currentPage >= totalPages - 2) {
                        pageNum = totalPages - 4 + i
                      } else {
                        pageNum = currentPage - 2 + i
                      }
                      return (
                        <button
                          key={pageNum}
                          className={`page-btn ${currentPage === pageNum ? 'active' : ''}`}
                          onClick={() => handlePageChange(pageNum)}
                        >
                          {pageNum}
                        </button>
                      )
                    })}
                  </div>
                  <button 
                    className="page-btn" 
                    disabled={currentPage === totalPages} 
                    onClick={() => handlePageChange(currentPage + 1)}
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
                      const num = Number(e.target.value)
                      if (num >= 1 && num <= totalPages) {
                        handlePageChange(num)
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
        <div className={`task-list-section ${tasksCollapsed ? 'collapsed' : ''}`}>
          <div className="task-list-header">
            <h3>📋 下发任务</h3>
            <button 
              className="collapse-btn icon-only" 
              onClick={() => setTasksCollapsed(!tasksCollapsed)}
              title={tasksCollapsed ? '展开' : '折叠'}
            >
              <span className={`collapse-icon ${tasksCollapsed ? 'collapsed' : ''}`}>
                ▼
              </span>
            </button>
          </div>
          {!tasksCollapsed && (
            <>
              {loading.tasks ? <div className="loading-tip">加载中...</div> : tasks.length === 0 ? (
                <div className="empty-tip">暂无任务</div>
              ) : filteredTasks.length === 0 ? (
                <div className="empty-tip">无搜索结果</div>
              ) : (
                <div className="task-list">
                  {filteredTasks.map(task => (
                    <div key={task.task_id} className={`task-card ${selectedTask?.task_id === task.task_id ? 'selected' : ''}`} onClick={() => handleTaskClick(task)}>
                      <div className="task-header"><span className="task-id">{task.task_id}</span><span className={`task-status ${task.status}`}>{task.status}</span></div>
                      <div className="task-summary">{task.risk_summary}</div>
                      <div className="task-info"><span>创建: {task.creator_name || task.creator_id}</span><span>→ {task.assigned_to_name}</span></div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
      <div className={`resize-handle ${isDraggingLeft ? 'dragging' : ''}`} onMouseDown={() => setIsDraggingLeft(true)} />
      <div className="main-content">
        <div className="chat-header"><h3>💬 智能体对话</h3></div>
        <div className="chat-messages">
          {isInitialChat ? (
            <div className="initial-chat-view">
              {/* 欢迎语 */}
              <div className="welcome-greeting">
                <h2>嗨，{currentUser?.username || '用户'} 👋</h2>
                <p>我是您的专属风控数字员工</p>
              </div>
              
              {/* 提示语 */}
              <div className="welcome-tips">
                <p>通过对话我可以帮您：</p>
                <ul>
                  <li>📊 分析风险数据</li>
                  <li>📝 创建和下发任务</li>
                  <li>📋 查看任务状态</li>
                  <li>💡 获取风险建议</li>
                </ul>
                <p className="tip">⚡ 所有操作都通过对话完成，无需手动创建任务</p>
              </div>

              {/* 功能卡片 */}
              <div className="quick-prompts">
                {quickPrompts.map(prompt => (
                  <button 
                    key={prompt.id}
                    className="quick-prompt-card"
                    onClick={() => {
                      setInputMessage(prompt.text)
                      // 自动发送
                      setTimeout(() => {
                        const sendBtn = document.querySelector('.send-btn')
                        if (sendBtn) sendBtn.click()
                      }, 100)
                    }}
                  >
                    <span className="prompt-icon">{prompt.icon}</span>
                    <span className="prompt-label">{prompt.label}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : chatMessages.length === 0 ? (
            <div className="welcome-message">
              <p>👋 欢迎使用风控Agent助手！</p>
              <p>通过对话我可以帮您：</p>
              <ul><li>分析风险数据</li><li>创建和下发任务</li><li>查看任务状态</li><li>获取风险建议</li></ul>
              <p className="tip">⚡ 所有操作都通过对话完成，无需手动创建任务</p>
            </div>
          ) : null}
          {chatMessages.map((msg, i) => (
            <div key={i} className={`message ${msg.sender}`}>
              <div className="message-header"><span className="sender">{msg.sender === 'user' ? '👤 我' : '🤖 Agent'}</span><span className="timestamp">{msg.timestamp}</span></div>
              <div className="message-content">
                {msg.sender === 'user' ? (
                  <>
                    {msg.files && msg.files.length > 0 && (
                      <div className="msg-files">
                        {msg.files.map((f, idx) => (
                          <div key={idx} className="msg-file">📄 {f.name}</div>
                        ))}
                      </div>
                    )}
                    {msg.message}
                  </>
                ) : (
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.message}</ReactMarkdown>
                )}
              </div>
            </div>
          ))}
          {loading.chat && <div className="message agent loading"><div className="message-content">正在思考...</div></div>}
          <div ref={messagesEndRef} />
        </div>
        <div className="chat-input">
          {/* 待发送文件列表 */}
          {pendingFiles.length > 0 && (
            <div className="pending-files">
              {pendingFiles.map(f => (
                <div key={f.id} className="pending-file">
                  <span className="file-icon">📄</span>
                  <span className="file-name">{f.name}</span>
                  <button className="remove-file" onClick={() => handleRemovePendingFile(f.id)}>×</button>
                </div>
              ))}
            </div>
          )}
          {/* 输入框行 */}
          <div className="input-row">
            <input type="file" ref={fileInputRef} style={{ display: 'none' }} onChange={handleFileUpload} multiple />
            <button className="upload-btn" onClick={() => fileInputRef.current?.click()}>📎</button>
            <textarea 
              ref={inputTextareaRef}
              value={inputMessage} 
              onChange={e => setInputMessage(e.target.value)} 
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  if (!loading.chat && (inputMessage.trim() || pendingFiles.length > 0)) {
                    handleSendMessage()
                  }
                }
              }}
              placeholder="输入消息... (Enter发送，Shift+Enter换行)" 
              rows={1}
              style={{ height: 'auto', minHeight: '44px' }}
            />
            <button onClick={handleSendMessage} disabled={loading.chat || (!inputMessage.trim() && pendingFiles.length === 0)} className="send-btn">➤</button>
          </div>
        </div>
      </div>
      <div className={`resize-handle ${isDraggingRight ? 'dragging' : ''}`} onMouseDown={() => setIsDraggingRight(true)} />
      <div
        className={`sidebar right ${rightPanelOpen ? 'open' : 'collapsed'}`}
        style={rightPanelOpen ? { width: `${rightWidth}%` } : {}}
      >
        {rightPanelOpen ? (
          <>
            <div className="right-panel-header">
              <h3>📋 详情信息</h3>
              <button 
                className="toggle-panel-btn" 
                onClick={() => setRightPanelOpen(false)}
                title="收起"
              >
                <span className="toggle-icon">▶</span>
              </button>
            </div>
            {selectedTask ? (
              <div className="task-detail">
                <h4>任务详情</h4>
                <p><strong>任务ID:</strong> {selectedTask.task_id}</p>
                <p><strong>风险简述:</strong> {selectedTask.risk_summary}</p>
                <p><strong>状态:</strong> <span className={`status-tag ${selectedTask.status}`}>{selectedTask.status}</span></p>
                <p><strong>创建人:</strong> {selectedTask.creator_name}</p>
                <p><strong>执行人:</strong> {selectedTask.assigned_to_name}</p>
                <p><strong>创建时间:</strong> {selectedTask.created_time}</p>
                {selectedTask.completed_time && <p><strong>完成时间:</strong> {selectedTask.completed_time}</p>}
                
                <div className="feedback-section">
                  <h5>📝 反馈详情</h5>
                  {taskFeedback?.feedback_summary ? (
                    <div className="feedback-summary">
                      <p>{taskFeedback.feedback_summary}</p>
                    </div>
                  ) : (
                    <div className="empty-tip">暂无反馈总结</div>
                  )}
                </div>
                
                <div className="files-section">
                  <h5>📎 上传文件</h5>
                  {taskFeedback?.uploaded_files && taskFeedback.uploaded_files.length > 0 ? (
                    <div className="file-list">
                      {taskFeedback.uploaded_files.map((file, i) => (
                        <div key={i} className="file-item">
                          <span>📄 {file.filename}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="empty-tip">暂无上传文件</div>
                  )}
                </div>
              </div>
            ) : <div className="placeholder">点击左侧任务查看详情</div>}
          </>
        ) : (
          <button
            className="expand-panel-btn"
            onClick={() => setRightPanelOpen(true)}
            title="展开详情"
          >
            <span className="expand-icon">◀</span>
          </button>
        )}
      </div>
    </div>
  )
}

// 一线人员工作区
function StaffWorkspace({ currentUser }) {
  const [selectedTask, setSelectedTask] = useState(null)
  const [chatMessages, setChatMessages] = useState([])
  const [inputMessage, setInputMessage] = useState('')
  const [pendingFiles, setPendingFiles] = useState([]) // 待发送的文件列表
  const [loading, setLoading] = useState({ chat: false, init: true })
  const [tasks, setTasks] = useState([])
  const messagesEndRef = useRef(null)
  const fileInputRef = useRef(null)
  const inputTextareaRef = useRef(null)

  // 获取任务列表
  const fetchTasks = async () => {
    if (!currentUser?.user_id) {
      setTasks([])
      return
    }
    try {
      const response = await fetch(`${API_BASE}/tasks?user_id=${currentUser.user_id}`)
      const data = await response.json()
      setTasks(data.length > 0 ? data : [])
    } catch (err) {
      console.error('[ERROR] 获取任务失败:', err)
      setTasks([])
    }
  }

  // 页面加载时自动获取任务并发起对话
  useEffect(() => {
    if (currentUser?.user_id) {
      fetchTasks()
      initConversation()
    }
  }, [currentUser])

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [chatMessages])

  // 自动调整输入框高度
  useEffect(() => {
    const textarea = inputTextareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      const newHeight = Math.min(textarea.scrollHeight, 150)
      textarea.style.height = newHeight + 'px'
    }
  }, [inputMessage])

  // SSE 事件监听 - 实时接收新任务通知
  useEffect(() => {
    if (!currentUser?.user_id) return

    const eventSource = new EventSource(`${API_BASE}/events/${currentUser.user_id}`)

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        console.log('[SSE Staff] 收到事件:', data.type, data)

        if (data.type === 'new_task') {
          // 收到新任务通知
          console.log('[SSE Staff] 收到新任务:', data.task_id)
          
          // 自动切换到新任务
          const newTaskId = data.task_id
          
          // 查找新任务的信息
          const newTask = tasks.find(t => t.task_id === newTaskId)
          if (newTask) {
            setSelectedTask(newTask)
          }

          // 调用后端API触发Staff Agent发送消息
          console.log('[SSE Staff] 调用notify-staff API...')
          fetch(`${API_BASE}/tasks/${data.task_id}/notify-staff`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              user_id: currentUser.user_id,
              username: currentUser.username
            })
          })
            .then(res => res.json())
            .then(result => {
              console.log('[SSE Staff] notify-staff 结果:', result)
              if (result.success) {
                // 获取新任务的聊天记录
                initConversation(newTaskId)
              } else {
                console.error('[SSE Staff] notify-staff 失败:', result)
                alert(`收到新任务: ${data.task_id}\n${data.task_info?.risk_summary || ''}`)
              }
            })
            .catch(err => {
              console.error('[SSE Staff] notify-staff 异常:', err)
              alert(`收到新任务: ${data.task_id}\n${data.task_info?.risk_summary || ''}`)
            })
        } else if (data.type === 'task_message_received') {
          // 后端自动触发StaffAgent发送消息后，推送此事件通知前端
          console.log('[SSE Staff] 收到新消息通知:', data.task_id)

          // 直接追加新消息到当前对话，不获取历史记录（IM端是持续会话）
          const newMessage = data.message
          if (newMessage) {
            setChatMessages(prev => [...prev, {
              sender: 'agent',
              message: newMessage,
              timestamp: new Date().toLocaleString(),
              messageType: 'text'
            }])
            console.log('[SSE Staff] 追加新消息到对话')
          }
        }
      } catch (err) {
        console.error('[SSE Staff] 解析事件失败:', err)
      }
    }

    eventSource.onerror = (err) => {
      console.error('[SSE Staff] 连接错误:', err)
      // 自动重连
      eventSource.close()
      console.log('[SSE Staff] 3秒后尝试重新连接...')
      setTimeout(() => {
        if (currentUser?.user_id) {
          const newSource = new EventSource(`${API_BASE}/events/${currentUser.user_id}`)
          console.log('[SSE Staff] 重新连接成功')
        }
      }, 3000)
    }

    return () => {
      eventSource.close()
      console.log('[SSE Staff] 断开连接')
    }
  }, [currentUser?.user_id])

  const initConversation = async (specificTaskId = null) => {
    try {
      // 获取当前用户的任务列表
      const response = await fetch(`${API_BASE}/tasks?user_id=${currentUser.user_id}`)
      const tasks = await response.json()
      setTasks(tasks)
      
      let targetTask = null
      
      // 如果指定了任务ID，直接使用该任务
      if (specificTaskId) {
        targetTask = tasks.find(t => t.task_id === specificTaskId)
      }
      
      // 否则找最新的待处理任务
      if (!targetTask) {
        targetTask = tasks.find(t => t.status !== '反馈完成') || tasks[0]
      }
      
      if (targetTask) {
        setSelectedTask(targetTask)
        
        // 获取对话历史
        const historyRes = await fetch(`${API_BASE}/tasks/${targetTask.task_id}/chat-history`)
        const historyData = await historyRes.json()
        
        if (Array.isArray(historyData) && historyData.length > 0) {
          setChatMessages(historyData.map(msg => ({
            sender: msg.sender === 'Agent' ? 'agent' : 'user',
            message: msg.message,
            timestamp: msg.timestamp,
            messageType: msg.message_type,
            files: msg.files
          })))
        } else {
          // 如果没有对话历史，发送初始消息让智能体推送任务
          const initResponse = await fetch(`${API_BASE}/tasks/${targetTask.task_id}/message`, {
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
              message: "你好，请告诉我当前有什么任务需要处理", 
              user_id: currentUser.user_id, 
              username: currentUser.username 
            })
          })
          const initData = await initResponse.json()
          if (initData.agent_reply) {
            setChatMessages([{ 
              sender: 'agent', 
              message: initData.agent_reply.message, 
              timestamp: initData.agent_reply.timestamp 
            }])
          }
        }
      }
    } catch (err) { 
      console.error('[ERROR] 初始化对话失败:', err) 
    } finally {
      setLoading(prev => ({ ...prev, init: false }))
    }
  }

  const handleSendMessage = async () => {
    if (!inputMessage.trim() && pendingFiles.length === 0) return
    if (!selectedTask) {
      alert('暂无任务，请先获取任务')
      return
    }

    // 先将用户消息和文件显示在对话框
    const fileDesc = pendingFiles.length > 0
      ? `\n[附件: ${pendingFiles.map(f => f.name).join(', ')}]`
      : ''

    const userMessage = {
      sender: 'user',
      message: inputMessage + fileDesc,
      timestamp: new Date().toLocaleString(),
      files: pendingFiles.map(f => ({ name: f.name, type: f.type }))
    }
    setChatMessages(prev => [...prev, userMessage])

    const messageToSend = inputMessage
    setInputMessage('')
    setPendingFiles([])
    setLoading(prev => ({ ...prev, chat: true }))

    try {
      // 构建 FormData 发送消息和文件
      const formData = new FormData()
      formData.append('message', messageToSend)
      formData.append('user_id', currentUser.user_id)
      formData.append('username', currentUser.username)

      // 添加文件
      pendingFiles.forEach(f => {
        formData.append('files', f.file, f.name)
      })

      const response = await fetch(`${API_BASE}/tasks/${selectedTask.task_id}/message`, {
        method: 'POST',
        body: formData
      })
      const data = await response.json()
      if (data.agent_reply) setChatMessages(prev => [...prev, { sender: 'agent', message: data.agent_reply.message, timestamp: data.agent_reply.timestamp }])
    } catch (err) { console.error('[ERROR] 发送消息失败:', err) }
    finally { setLoading(prev => ({ ...prev, chat: false })) }
  }

  // 文件选择后添加到待发送列表
  const handleFileUpload = (e) => {
    const files = Array.from(e.target.files || [])
    if (files.length === 0) return
    if (!selectedTask) {
      alert('暂无任务，请先获取任务')
      return
    }

    const newFiles = files.map(file => ({
      id: Date.now() + Math.random(),
      name: file.name,
      size: file.size,
      type: file.type,
      file: file
    }))

    setPendingFiles(prev => [...prev, ...newFiles])
    e.target.value = ''
  }

  // 移除待发送文件
  const handleRemovePendingFile = (fileId) => {
    setPendingFiles(prev => prev.filter(f => f.id !== fileId))
  }

  // 完成任务也可以通过对话完成，不需要单独按钮

  // 纯聊天界面渲染
  if (loading.init) {
    return (
      <div className="workspace staff-workspace">
        <div className="staff-main" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div className="loading">正在初始化对话...</div>
        </div>
      </div>
    )
  }

  if (!selectedTask) {
    return (
      <div className="workspace staff-workspace">
        <div className="staff-main" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div className="empty">暂无任务</div>
        </div>
      </div>
    )
  }

  // 按时间分组消息
  const groupMessagesByTime = (messages) => {
    const groups = []
    let lastTime = null
    
    messages.forEach((msg, i) => {
      const msgDate = new Date(msg.timestamp)
      const timeStr = msgDate.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })
      
      if (timeStr !== lastTime) {
        groups.push({ type: 'time', time: timeStr })
        lastTime = timeStr
      }
      groups.push({ type: 'message', data: msg, index: i })
    })
    
    return groups
  }

  const messageGroups = groupMessagesByTime(chatMessages)

  return (
    <div className="workspace staff-workspace">
      {/* 手机模拟器容器 */}
      <div className="phone-container">
        {/* 手机顶部导航栏 */}
        <div className="chat-header im-header">
          <div className="back-btn">←</div>
          <h3>风险核查助手</h3>
          <div className="more-btn">⋮</div>
        </div>
        <div className="staff-main">
          <div className="chat-messages im-style">
          {chatMessages.length === 0 && !loading.chat && <div className="welcome-message"><p>👋 您好！智能体正在准备任务信息...</p></div>}
          {messageGroups.map((item, i) => {
            if (item.type === 'time') {
              return (
                <div key={`time-${i}`} className="time-divider">
                  <span>{item.time}</span>
                </div>
              )
            }
            const msg = item.data
            return (
              <div key={item.index} className={`message ${msg.sender}`}>
                <div className="message-avatar">
                  {msg.sender === 'user' ? '👤' : '🤖'}
                </div>
                <div className="message-bubble">
                  {msg.sender === 'user' ? (
                    <>
                      {msg.files && msg.files.length > 0 && (
                        <div className="msg-files">
                          {msg.files.map((f, i) => (
                            <div key={i} className="msg-file">📄 {f.name}</div>
                          ))}
                        </div>
                      )}
                      {msg.message}
                    </>
                  ) : (
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.message}</ReactMarkdown>
                  )}
                </div>
                <div className="message-time">
                  {new Date(msg.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
            )
          })}
          {loading.chat && <div className="message agent loading"><div className="message-content">正在思考...</div></div>}
          <div ref={messagesEndRef} />
        </div>
        <div className="chat-input">
          {/* 待发送文件列表 */}
          {pendingFiles.length > 0 && (
            <div className="pending-files">
              {pendingFiles.map(f => (
                <div key={f.id} className="pending-file">
                  <span className="file-icon">📄</span>
                  <span className="file-name">{f.name}</span>
                  <button className="remove-file" onClick={() => handleRemovePendingFile(f.id)}>×</button>
                </div>
              ))}
            </div>
          )}
          {/* 输入框行 */}
          <div className="input-row">
            <input type="file" ref={fileInputRef} style={{ display: 'none' }} onChange={handleFileUpload} multiple />
            <button className="upload-btn" onClick={() => fileInputRef.current?.click()}>📎</button>
            <textarea 
              ref={inputTextareaRef}
              value={inputMessage} 
              onChange={e => setInputMessage(e.target.value)} 
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  if (!loading.chat && (inputMessage.trim() || pendingFiles.length > 0)) {
                    handleSendMessage()
                  }
                }
              }}
              placeholder="输入消息... (Enter发送，Shift+Enter换行)" 
              rows={1}
              style={{ height: 'auto', minHeight: '44px' }}
            />
            <button onClick={handleSendMessage} disabled={loading.chat || (!inputMessage.trim() && pendingFiles.length === 0)} className="send-btn">➤</button>
          </div>
        </div>
        </div>
      </div>
    </div>
  )
}

// 主应用
function App() {
  const [users, setUsers] = useState([])
  const [currentUser, setCurrentUser] = useState(null)
  const [loading, setLoading] = useState(true)
  
  // 从URL参数读取用户ID或sessionStorage
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const presetUserId = params.get('user_id')
    
    fetch(`${API_BASE}/users`).then(r => r.json()).then(usersData => {
      setUsers(usersData)
      // 优先从URL参数读取，其次从sessionStorage恢复
      if (presetUserId) {
        const user = usersData.find(u => u.user_id === presetUserId)
        if (user) {
          setCurrentUser(user)
          sessionStorage.setItem('currentUser', JSON.stringify(user))
        }
      } else {
        // 尝试从sessionStorage恢复
        const savedUser = sessionStorage.getItem('currentUser')
        if (savedUser) {
          try {
            const user = JSON.parse(savedUser)
            // 验证用户是否仍然存在
            const exists = usersData.find(u => u.user_id === user.user_id)
            if (exists) setCurrentUser(user)
          } catch (e) {
            sessionStorage.removeItem('currentUser')
          }
        }
      }
    }).catch(console.error).finally(() => setLoading(false))
  }, [])

  const handleLogin = (user) => {
    setCurrentUser(user)
    sessionStorage.setItem('currentUser', JSON.stringify(user))
  }

  const handleUserChange = (e) => {
    const userId = e.target.value
    if (userId) {
      const user = users.find(u => u.user_id === userId)
      setCurrentUser(user)
      sessionStorage.setItem('currentUser', JSON.stringify(user))
    } else {
      setCurrentUser(null)
    }
  }

  // 个人中心下拉菜单状态
  const [showProfileMenu, setShowProfileMenu] = useState(false)

  // 地区下拉框状态
  // 总部用户可以切换地区，地区用户只能看自己的地区（不可切换但仍显示下拉框）
  const isHQUser = currentUser?.region === '总部'
  const [selectedRegion, setSelectedRegion] = useState(() => {
    // 总部用户初始为空（查看所有），地区用户初始为自己的地区
    return currentUser?.region === '总部' ? '' : (currentUser?.region || '')
  })
  const [showRegionMenu, setShowRegionMenu] = useState(false)

  // 地区选项（总部用户可选全部，地区用户只有自己的地区）
  const regionOptions = isHQUser 
    ? ['', '上海区', '北京区', '山西区', '浙北区']
    : [currentUser?.region].filter(Boolean)

  // 退出登录
  const handleLogout = () => {
    sessionStorage.removeItem('currentUser')
    setCurrentUser(null)
    setShowProfileMenu(false)
  }

  // 点击其他地方关闭下拉菜单
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (showProfileMenu && !e.target.closest('.profile-menu')) {
        setShowProfileMenu(false)
      }
    }
    document.addEventListener('click', handleClickOutside)
    return () => document.removeEventListener('click', handleClickOutside)
  }, [showProfileMenu])

  // 登录页面
  if (loading) {
    return <LoginPage users={users} onLogin={handleLogin} loading={loading} />
  }
  
  // 未登录 - 显示登录页
  if (!currentUser) {
    return <LoginPage users={users} onLogin={handleLogin} loading={loading} />
  }

  const isManager = currentUser.role === '业务负责人' || currentUser.role === '普通分析人员'

  return (
    <div className="App">
      <header className="App-header">
        <h1>🛡️ 风控数字员工</h1>
        <div className="header-right">
          {/* 地区选择下拉框 - 所有用户都显示，地区用户不可切换 */}
          <div className="region-selector">
            <select 
              value={selectedRegion} 
              onChange={(e) => {
                if (isHQUser) {
                  setSelectedRegion(e.target.value)
                }
              }}
              className="region-select"
              disabled={!isHQUser}
            >
              {isHQUser ? (
                <>
                  <option value="">🌍 全地区</option>
                  {regionOptions.filter(r => r).map(region => (
                    <option key={region} value={region}>{region}</option>
                  ))}
                </>
              ) : (
                <option value={currentUser?.region}>{currentUser?.region}</option>
              )}
            </select>
          </div>

          {/* 个人中心下拉菜单 */}
          <div className="profile-menu">
            <button className="profile-btn" onClick={(e) => { e.stopPropagation(); setShowProfileMenu(!showProfileMenu); }}>
              👤 个人中心
            </button>
            {showProfileMenu && (
              <div className="profile-dropdown">
                <div className="profile-info">
                  <div className="profile-name">{currentUser.username}</div>
                  <div className="profile-detail">工号: {currentUser.employee_id || currentUser.user_id}</div>
                  <div className="profile-detail">角色: {currentUser.role}</div>
                  <div className="profile-detail">部门: {currentUser.department}</div>
                  <div className="profile-detail">地区: {currentUser.region || '未设置'}</div>
                </div>
                <div className="profile-divider"></div>
                <button className="logout-btn" onClick={handleLogout}>退出登录</button>
              </div>
            )}
          </div>
        </div>
      </header>
      {isManager ? <ManagerWorkspace currentUser={currentUser} selectedRegion={selectedRegion} /> : <StaffWorkspace currentUser={currentUser} />}
    </div>
  )
}

export default App
