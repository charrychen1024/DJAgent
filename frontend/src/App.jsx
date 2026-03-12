import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import './App.css'

const API_BASE = 'http://127.0.0.1:5005/api'

// 业务负责人工作区
function ManagerWorkspace({ currentUser, onAddToChat }) {
  const [tasks, setTasks] = useState([])
  const [allRiskData, setAllRiskData] = useState([])
  const [selectedRows, setSelectedRows] = useState([])
  const [selectedTask, setSelectedTask] = useState(null)
  const [chatMessages, setChatMessages] = useState([])
  const [taskFeedback, setTaskFeedback] = useState(null)
  const [inputMessage, setInputMessage] = useState('')
  const [pendingFiles, setPendingFiles] = useState([]) // 待发送的文件列表
  const [loading, setLoading] = useState({ tasks: false, riskData: false, chat: false })
  // 分页相关状态
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  // 筛选相关状态
  const [searchField, setSearchField] = useState('')
  const [searchValue, setSearchValue] = useState('')
  const messagesEndRef = useRef(null)
  const fileInputRef = useRef(null)
  const [leftWidth, setLeftWidth] = useState(35)
  const [rightWidth, setRightWidth] = useState(25)
  const [isDraggingLeft, setIsDraggingLeft] = useState(false)
  const [isDraggingRight, setIsDraggingRight] = useState(false)

  useEffect(() => {
    fetchTasks()
    fetchAllRiskData()
  }, [])

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
    }

    return () => {
      eventSource.close()
      console.log('[SSE] Manager 断开连接')
    }
  }, [currentUser?.user_id, selectedTask])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

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
    setLoading(prev => ({ ...prev, tasks: true }))
    try {
      // 根据用户角色过滤任务：业务负责人看自己创建的，一线人员看分配给自己的
      const url = currentUser?.user_id
        ? `${API_BASE}/tasks?user_id=${currentUser.user_id}`
        : `${API_BASE}/tasks`
      const response = await fetch(url)
      const data = await response.json()
      setTasks(data.length > 0 ? data : mockTasks)
    } catch (err) {
      console.error('[ERROR] 获取任务失败:', err)
      setTasks(mockTasks)
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

  // 获取所有字段名
  const getAllColumns = () => {
    if (allRiskData.length === 0) return []
    return Object.keys(allRiskData[0]).filter(k => k !== 'source')
  }

  // 全选/取消全选
  const handleSelectAll = () => {
    if (selectedRows.length === allRiskData.length) {
      setSelectedRows([])
    } else {
      setSelectedRows(allRiskData.map((_, i) => i));
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
    const selectedData = selectedRows.map(i => allRiskData[i])

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

  // 分页逻辑
  const filteredRiskData = (() => {
    if (!searchField || !searchValue.trim()) return allRiskData
    return allRiskData.filter(row => {
      const fieldValue = row[searchField]
      if (fieldValue == null) return false
      return String(fieldValue).toLowerCase().includes(searchValue.toLowerCase())
    })
  })()

  const totalPages = Math.ceil(filteredRiskData.length / pageSize)
  const currentPageData = filteredRiskData.slice((currentPage - 1) * pageSize, currentPage * pageSize)

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

  return (
    <div className="workspace manager-workspace">
      <div className="sidebar left" style={{ width: `${leftWidth}%` }}>
        <div className="risk-data-section">
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
          {/* 筛选栏 */}
          <div className="risk-filter-bar">
            <select
              value={searchField}
              onChange={e => setSearchField(e.target.value)}
              className="filter-select"
            >
              <option value="">筛选字段</option>
              {columns.map(col => (
                <option key={col} value={col}>{col}</option>
              ))}
            </select>
            <input
              type="text"
              value={searchValue}
              onChange={e => setSearchValue(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
              placeholder="输入关键词..."
              className="filter-input"
            />
            <button onClick={handleSearch} className="filter-btn">搜索</button>
            <button onClick={handleResetSearch} className="filter-btn reset">重置</button>
          </div>
          {loading.riskData ? (
            <div className="loading-tip">加载中...</div>
          ) : allRiskData.length > 0 ? (
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
        <div className="task-list-section">
          <h3>📋 下发任务</h3>
          {loading.tasks ? <div className="loading-tip">加载中...</div> : tasks.length > 0 ? (
            <div className="task-list">
              {tasks.map(task => (
                <div key={task.task_id} className={`task-card ${selectedTask?.task_id === task.task_id ? 'selected' : ''}`} onClick={() => handleTaskClick(task)}>
                  <div className="task-header"><span className="task-id">{task.task_id}</span><span className={`task-status ${task.status}`}>{task.status}</span></div>
                  <div className="task-summary">{task.risk_summary}</div>
                  <div className="task-info"><span>→ {task.assigned_to_name}</span><span>{task.created_time}</span></div>
                </div>
              ))}
            </div>
          ) : <div className="empty-tip">暂无任务</div>}
        </div>
      </div>
      <div className="resize-handle" onMouseDown={() => setIsDraggingLeft(true)} />
      <div className="main-content">
        <div className="chat-header"><h3>💬 智能体对话</h3></div>
        <div className="chat-messages">
          {chatMessages.length === 0 && (
            <div className="welcome-message">
              <p>👋 欢迎使用风控Agent助手！</p>
              <p>通过对话我可以帮您：</p>
              <ul><li>分析风险数据</li><li>创建和下发任务</li><li>查看任务状态</li><li>获取风险建议</li></ul>
              <p className="tip">⚡ 所有操作都通过对话完成，无需手动创建任务</p>
            </div>
          )}
          {chatMessages.map((msg, i) => (
            <div key={i} className={`message ${msg.sender}`}>
              <div className="message-header"><span className="sender">{msg.sender === 'user' ? '👤 我' : '🤖 Agent'}</span><span className="timestamp">{msg.timestamp}</span></div>
              <div className="message-content">
                {msg.sender === 'user' ? (
                  msg.message
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
          <input type="file" ref={fileInputRef} style={{ display: 'none' }} onChange={handleFileUpload} multiple />
          <button className="upload-btn" onClick={() => fileInputRef.current?.click()}>📎</button>
          <textarea value={inputMessage} onChange={e => setInputMessage(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); !loading.chat && handleSendMessage() } }} placeholder="输入消息... (Enter发送)" disabled={loading.chat} rows={inputMessage.split('\n').length > 3 ? 3 : 1} />
          <button onClick={handleSendMessage} disabled={loading.chat || (!inputMessage.trim() && pendingFiles.length === 0)}>发送</button>
        </div>
      </div>
      <div className="resize-handle" onMouseDown={() => setIsDraggingRight(true)} />
      <div className="sidebar right" style={{ width: `${rightWidth}%` }}>
        <h3>📋 详情信息</h3>
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
  const messagesEndRef = useRef(null)
  const fileInputRef = useRef(null)

  // 页面加载时自动获取任务并发起对话
  useEffect(() => {
    if (currentUser?.user_id) {
      initConversation()
    }
  }, [currentUser])

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [chatMessages])

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
          // 弹出通知
          alert(`收到新任务: ${data.task_id}\n${data.task_info?.risk_summary || ''}`)
          // 刷新并初始化新任务对话
          initConversation()
        }
      } catch (err) {
        console.error('[SSE Staff] 解析事件失败:', err)
      }
    }

    eventSource.onerror = (err) => {
      console.error('[SSE Staff] 连接错误:', err)
    }

    return () => {
      eventSource.close()
      console.log('[SSE Staff] 断开连接')
    }
  }, [currentUser?.user_id])

  const initConversation = async () => {
    try {
      // 获取当前用户的待处理任务
      const response = await fetch(`${API_BASE}/tasks?user_id=${currentUser.user_id}`)
      const tasks = await response.json()
      
      // 找到最新的待处理任务
      const pendingTask = tasks.find(t => t.status !== '反馈完成') || tasks[0]
      
      if (pendingTask) {
        setSelectedTask(pendingTask)
        
        // 获取对话历史
        const historyRes = await fetch(`${API_BASE}/tasks/${pendingTask.task_id}/chat-history`)
        const historyData = await historyRes.json()
        
        if (Array.isArray(historyData) && historyData.length > 0) {
          setChatMessages(historyData.map(msg => ({ 
            sender: msg.sender === 'Agent' ? 'agent' : 'user', 
            message: msg.message, 
            timestamp: msg.timestamp, 
            messageType: msg.message_type 
          })))
        } else {
          // 如果没有对话历史，发送初始消息让智能体推送任务
          const initResponse = await fetch(`${API_BASE}/tasks/${pendingTask.task_id}/message`, {
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
      if (data.user_message) setChatMessages(prev => [...prev, { sender: 'user', message: data.user_message.message, timestamp: data.user_message.timestamp }])
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

  return (
    <div className="workspace staff-workspace" style={{ height: '100vh' }}>
      {/* 纯聊天界面，无左侧任务列表，无确认按钮 */}
      <div className="staff-main" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div className="chat-header">
          <h3>💬 风险核查助手</h3>
        </div>
        <div className="chat-messages im-style">
          {chatMessages.length === 0 && !loading.chat && <div className="welcome-message"><p>👋 您好！智能体正在准备任务信息...</p></div>}
          {chatMessages.map((msg, i) => (
            <div key={i} className={`message ${msg.sender}`}>
              <div className="message-content">
                {msg.sender === 'user' ? (
                  msg.message
                ) : (
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.message}</ReactMarkdown>
                )}
              </div>
              <div className="message-time">{msg.timestamp}</div>
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
          <input type="file" ref={fileInputRef} style={{ display: 'none' }} onChange={handleFileUpload} multiple />
          <button className="upload-btn" onClick={() => fileInputRef.current?.click()}>📎</button>
          <textarea value={inputMessage} onChange={e => setInputMessage(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); !loading.chat && handleSendMessage() } }} placeholder="输入消息... (Enter发送)" disabled={loading.chat} rows={inputMessage.split('\n').length > 3 ? 3 : 1} />
          <button onClick={handleSendMessage} disabled={loading.chat || !inputMessage.trim()}>发送</button>
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
  
  // 从URL参数读取用户ID
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const presetUserId = params.get('user_id')
    
    fetch(`${API_BASE}/users`).then(r => r.json()).then(usersData => {
      setUsers(usersData)
      if (presetUserId) {
        const user = usersData.find(u => u.user_id === presetUserId)
        if (user) setCurrentUser(user)
      }
    }).catch(console.error).finally(() => setLoading(false))
  }, [])

  const handleUserChange = (e) => {
    const userId = e.target.value
    if (userId) {
      const user = users.find(u => u.user_id === userId)
      setCurrentUser(user)
    } else {
      setCurrentUser(null)
    }
  }

  if (loading) {
    return (
      <div className="App login-page">
        <div className="login-container">
          <h1>🛡️ 风控数字员工</h1>
          <p>加载中...</p>
        </div>
      </div>
    )
  }

  if (!currentUser) {
    return (
      <div className="App login-page">
        <div className="login-container">
          <h1>🛡️ 风控数字员工</h1>
          <p className="subtitle">请选择您的身份</p>
          <select onChange={handleUserChange} defaultValue="" className="user-select">
            <option value="" disabled>选择用户...</option>
            {users.map(user => (
              <option key={user.user_id} value={user.user_id}>
                {user.username} - {user.role} ({user.department})
              </option>
            ))}
          </select>
        </div>
      </div>
    )
  }

  const isManager = currentUser.role === '业务负责人' || currentUser.role === '普通分析人员'

  return (
    <div className="App">
      <header className="App-header">
        <h1>🛡️ 风控数字员工</h1>
        <div className="header-right">
          <span className="user-info">{currentUser.username} ({currentUser.role})</span>
          <select value={currentUser.user_id} onChange={handleUserChange} className="user-switch">
            {users.map(user => (
              <option key={user.user_id} value={user.user_id}>{user.username}</option>
            ))}
          </select>
          <button className="logout-btn" onClick={() => setCurrentUser(null)}>切换用户</button>
        </div>
      </header>
      {isManager ? <ManagerWorkspace currentUser={currentUser} /> : <StaffWorkspace currentUser={currentUser} />}
    </div>
  )
}

export default App
