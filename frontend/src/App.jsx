import { useState, useEffect, useRef } from 'react'
import './App.css'

const API_BASE = 'http://127.0.0.1:5000/api'

// 业务负责人工作区
function ManagerWorkspace({ currentUser, onAddToChat }) {
  const [tasks, setTasks] = useState([])
  const [allRiskData, setAllRiskData] = useState([])
  const [selectedRows, setSelectedRows] = useState([])
  const [selectedTask, setSelectedTask] = useState(null)
  const [chatMessages, setChatMessages] = useState([])
  const [inputMessage, setInputMessage] = useState('')
  const [loading, setLoading] = useState({ tasks: false, riskData: false, chat: false })
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
      const response = await fetch(`${API_BASE}/tasks`)
      const data = await response.json()
      setTasks(data.length > 0 ? data : mockTasks)
    } catch (err) {
      console.error('[ERROR] 获取任务失败:', err)
      setTasks(mockTasks)
    } finally {
      setLoading(prev => ({ ...prev, tasks: false }))
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
          if (data.length > 0) allData.push(...data.map(d => ({ ...d, source: `risk_data_${filename}.csv` })))
        }
      } catch (e) {}
    }
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
    const summary = selectedData.map(d => 
      `运单号: ${d.运单号 || '-'}, 异常类型: ${d.异常类型 || '-'}, 风险等级: ${d.风险等级 || '-'}, 发货地: ${d.发货地 || '-'}, 收货地: ${d.收货地 || '-'}`
    ).join('\n')
    
    const message = `我选择了${selectedRows.length}条风险数据，请帮我分析：\n${summary}`
    setInputMessage(message)
  }

  const handleTaskClick = async (task) => {
    setSelectedTask(task)
    try {
      const response = await fetch(`${API_BASE}/tasks/${task.task_id}/chat-history`)
      if (response.ok) {
        const data = await response.json()
        if (Array.isArray(data)) {
          setChatMessages(data.map(msg => ({
            sender: msg.sender === 'Agent' ? 'agent' : 'user',
            message: msg.message,
            timestamp: msg.timestamp,
            messageType: msg.message_type
          })))
        }
      }
    } catch (err) {
      console.error('[ERROR] 获取对话历史失败:', err)
    }
  }

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return
    const userMessage = { sender: 'user', message: inputMessage, timestamp: new Date().toLocaleString() }
    setChatMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setLoading(prev => ({ ...prev, chat: true }))
    
    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: inputMessage, user_id: currentUser.user_id, role: currentUser.role })
      })
      const data = await response.json()
      setChatMessages(prev => [...prev, { sender: 'agent', message: data.message, timestamp: data.timestamp }])
      fetchTasks()
    } catch (err) {
      console.error('[ERROR] 发送消息失败:', err)
    } finally {
      setLoading(prev => ({ ...prev, chat: false }))
    }
  }

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const fileMessage = { sender: 'user', message: `[上传文件] ${file.name}`, timestamp: new Date().toLocaleString() }
    setChatMessages(prev => [...prev, fileMessage])
    
    if (selectedTask) {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('user_id', currentUser.user_id)
      formData.append('filename', file.name)
      try {
        const response = await fetch(`${API_BASE}/tasks/${selectedTask.task_id}/upload-file`, { method: 'POST', body: formData })
        const data = await response.json()
        setChatMessages(prev => [...prev, { sender: 'agent', message: data.message || `文件 ${file.name} 上传成功`, timestamp: new Date().toLocaleString() }])
      } catch (err) {
        console.error('[ERROR] 文件上传失败:', err)
      }
    }
    e.target.value = ''
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
          {loading.riskData ? <div className="loading-tip">加载中...</div> : allRiskData.length > 0 ? (
            <div className="risk-table-wrapper">
              <table className="risk-table">
                <thead>
                  <tr>
                    <th className="checkbox-col">
                      <input 
                        type="checkbox" 
                        checked={selectedRows.length === allRiskData.length && allRiskData.length > 0}
                        onChange={handleSelectAll}
                      />
                    </th>
                    {columns.map(col => (
                      <th key={col}>{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {allRiskData.slice(0, 20).map((row, i) => (
                    <tr key={i} className={selectedRows.includes(i) ? 'selected-row' : ''}>
                      <td className="checkbox-col">
                        <input 
                          type="checkbox" 
                          checked={selectedRows.includes(i)}
                          onChange={() => handleSelectRow(i)}
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
                  ))}
                </tbody>
              </table>
            </div>
          ) : <div className="empty-tip">暂无风险数据</div>}
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
              <div className="message-content">{msg.message}</div>
            </div>
          ))}
          {loading.chat && <div className="message agent loading"><div className="message-content">正在思考...</div></div>}
          <div ref={messagesEndRef} />
        </div>
        <div className="chat-input">
          <input type="file" ref={fileInputRef} style={{ display: 'none' }} onChange={handleFileUpload} />
          <button className="upload-btn" onClick={() => fileInputRef.current?.click()}>📎</button>
          <input type="text" value={inputMessage} onChange={e => setInputMessage(e.target.value)} onKeyPress={e => e.key === 'Enter' && !loading.chat && handleSendMessage()} placeholder="输入消息... (所有操作可通过对话完成)" disabled={loading.chat} />
          <button onClick={handleSendMessage} disabled={loading.chat || !inputMessage.trim()}>发送</button>
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
              <div className="chat-history-mini">
                {chatMessages.length > 0 ? chatMessages.map((msg, i) => (
                  <div key={i} className={`mini-message ${msg.sender}`}>
                    <span className="mini-sender">{msg.sender === 'user' ? '我' : 'Agent'}:</span>
                    <span className="mini-content">{msg.message.substring(0, 50)}{msg.message.length > 50 ? '...' : ''}</span>
                  </div>
                )) : <div className="empty-tip">暂无对话记录</div>}
              </div>
            </div>
            
            <div className="files-section">
              <h5>📎 上传文件</h5>
              <div className="empty-tip">暂无上传文件</div>
            </div>
          </div>
        ) : <div className="placeholder">点击左侧任务查看详情</div>}
      </div>
    </div>
  )
}

// 一线人员工作区
function StaffWorkspace({ currentUser }) {
  const [tasks, setTasks] = useState([])
  const [selectedTask, setSelectedTask] = useState(null)
  const [chatMessages, setChatMessages] = useState([])
  const [inputMessage, setInputMessage] = useState('')
  const [loading, setLoading] = useState({ tasks: false, chat: false })
  const messagesEndRef = useRef(null)
  const fileInputRef = useRef(null)

  useEffect(() => { fetchTasks() }, [])
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [chatMessages])

  const fetchTasks = async () => {
    setLoading(prev => ({ ...prev, tasks: true }))
    try {
      const response = await fetch(`${API_BASE}/tasks?user_id=${currentUser.user_id}`)
      const data = await response.json()
      setTasks(data)
      const pendingTask = data.find(t => t.status !== '反馈完成')
      if (pendingTask) handleTaskClick(pendingTask)
    } catch (err) { console.error('[ERROR] 获取任务失败:', err) }
    finally { setLoading(prev => ({ ...prev, tasks: false })) }
  }

  const handleTaskClick = async (task) => {
    setSelectedTask(task)
    try {
      const response = await fetch(`${API_BASE}/tasks/${task.task_id}/chat-history`)
      if (response.ok) {
        const data = await response.json()
        if (Array.isArray(data)) {
          setChatMessages(data.map(msg => ({ sender: msg.sender === 'Agent' ? 'agent' : 'user', message: msg.message, timestamp: msg.timestamp, messageType: msg.message_type })))
        }
      }
    } catch (err) { console.error('[ERROR] 获取对话历史失败:', err) }
  }

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || !selectedTask) return
    const userMessage = { sender: 'user', message: inputMessage, timestamp: new Date().toLocaleString() }
    setChatMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setLoading(prev => ({ ...prev, chat: true }))
    try {
      const response = await fetch(`${API_BASE}/tasks/${selectedTask.task_id}/message`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: inputMessage, user_id: currentUser.user_id, username: currentUser.username })
      })
      const data = await response.json()
      if (data.user_message) setChatMessages(prev => [...prev, { sender: 'user', message: data.user_message.message, timestamp: data.user_message.timestamp }])
      if (data.agent_reply) setChatMessages(prev => [...prev, { sender: 'agent', message: data.agent_reply.message, timestamp: data.agent_reply.timestamp }])
    } catch (err) { console.error('[ERROR] 发送消息失败:', err) }
    finally { setLoading(prev => ({ ...prev, chat: false })) }
  }

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file || !selectedTask) return
    const formData = new FormData()
    formData.append('file', file)
    formData.append('user_id', currentUser.user_id)
    formData.append('filename', file.name)
    try {
      const response = await fetch(`${API_BASE}/tasks/${selectedTask.task_id}/upload-file`, { method: 'POST', body: formData })
      const data = await response.json()
      setChatMessages(prev => [...prev, { sender: 'user', message: `[上传文件] ${file.name}`, timestamp: new Date().toLocaleString() }])
      setTimeout(() => setChatMessages(prev => [...prev, { sender: 'agent', message: data.message || `文件已上传`, timestamp: new Date().toLocaleString() }]), 500)
    } catch (err) { console.error('[ERROR] 文件上传失败:', err) }
    e.target.value = ''
  }

  const handleComplete = async () => {
    if (!selectedTask) return
    try {
      const response = await fetch(`${API_BASE}/tasks/${selectedTask.task_id}/complete`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: currentUser.user_id, task_id: selectedTask.task_id })
      })
      const data = await response.json()
      setChatMessages(prev => [...prev, { sender: 'agent', message: `✅ 任务已完成！反馈总结：${data.feedback_summary}`, timestamp: new Date().toLocaleString() }])
      fetchTasks()
    } catch (err) { console.error('[ERROR] 完成任务失败:', err) }
  }

  return (
    <div className="workspace staff-workspace">
      <div className="staff-sidebar">
        <h3>📋 我的任务</h3>
        {loading.tasks ? <div className="loading-tip">加载中...</div> : tasks.length > 0 ? (
          <div className="task-list">
            {tasks.map(task => (
              <div key={task.task_id} className={`task-card ${selectedTask?.task_id === task.task_id ? 'selected' : ''}`} onClick={() => handleTaskClick(task)}>
                <div className="task-header"><span className="task-id">{task.task_id}</span><span className={`task-status ${task.status}`}>{task.status}</span></div>
                <div className="task-summary">{task.risk_summary}</div>
                <div className="task-time">{task.created_time}</div>
              </div>
            ))}
          </div>
        ) : <div className="empty-tip">暂无任务</div>}
      </div>
      <div className="staff-main">
        <div className="chat-header">
          <h3>💬 {selectedTask ? selectedTask.risk_summary : '风险核查助手'}</h3>
          {selectedTask && selectedTask.status !== '反馈完成' && <button className="complete-btn" onClick={handleComplete}>✅ 确认完成</button>}
        </div>
        <div className="chat-messages im-style">
          {chatMessages.length === 0 && selectedTask && <div className="welcome-message"><p>👋 您有新任务需要核查</p><p><strong>风险简述：</strong>{selectedTask.risk_summary}</p><p className="tip">请根据Agent的指导完成核查并上传相关证明文件</p></div>}
          {chatMessages.map((msg, i) => (
            <div key={i} className={`message ${msg.sender}`}>
              <div className="message-content">{msg.message}</div>
              <div className="message-time">{msg.timestamp}</div>
            </div>
          ))}
          {loading.chat && <div className="message agent loading"><div className="message-content">正在思考...</div></div>}
          <div ref={messagesEndRef} />
        </div>
        <div className="chat-input">
          <input type="file" ref={fileInputRef} style={{ display: 'none' }} onChange={handleFileUpload} />
          <button className="upload-btn" onClick={() => fileInputRef.current?.click()}>📎</button>
          <input type="text" value={inputMessage} onChange={e => setInputMessage(e.target.value)} onKeyPress={e => e.key === 'Enter' && !loading.chat && handleSendMessage()} placeholder="输入消息..." disabled={loading.chat || !selectedTask} />
          <button onClick={handleSendMessage} disabled={loading.chat || !inputMessage.trim() || !selectedTask}>发送</button>
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

  useEffect(() => {
    fetch(`${API_BASE}/users`).then(r => r.json()).then(setUsers).catch(console.error).finally(() => setLoading(false))
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
          <h1>🛡️ 风控Agent助手</h1>
          <p>加载中...</p>
        </div>
      </div>
    )
  }

  if (!currentUser) {
    return (
      <div className="App login-page">
        <div className="login-container">
          <h1>🛡️ 风控Agent助手系统</h1>
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
        <h1>🛡️ 风控Agent助手</h1>
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
