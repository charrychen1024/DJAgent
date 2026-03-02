import { useState, useEffect, useRef } from 'react'
import './App.css'

const API_BASE = 'http://127.0.0.1:5000/api'

// 业务负责人工作区
function ManagerWorkspace({ currentUser }) {
  const [tasks, setTasks] = useState([])
  const [allRiskData, setAllRiskData] = useState([])
  const [selectedTask, setSelectedTask] = useState(null)
  const [chatMessages, setChatMessages] = useState([])
  const [inputMessage, setInputMessage] = useState('')
  const [loading, setLoading] = useState({ tasks: false, riskData: false, chat: false })
  const messagesEndRef = useRef(null)
  const fileInputRef = useRef(null)
  const [leftWidth, setLeftWidth] = useState(25)
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
          if (newWidth > 15 && newWidth < 40) setLeftWidth(newWidth)
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

  const fetchTasks = async () => {
    setLoading(prev => ({ ...prev, tasks: true }))
    try {
      const response = await fetch(`${API_BASE}/tasks`)
      const data = await response.json()
      setTasks(data)
    } catch (err) {
      console.error('[ERROR] 获取任务失败:', err)
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

  return (
    <div className="workspace manager-workspace">
      <div className="sidebar left" style={{ width: `${leftWidth}%` }}>
        <div className="risk-data-section">
          <h3>📊 风险明细数据</h3>
          {loading.riskData ? <div className="loading-tip">加载中...</div> : allRiskData.length > 0 ? (
            <div className="risk-table-wrapper">
              <table className="risk-table">
                <thead><tr><th>运单号</th><th>异常类型</th><th>风险等级</th></tr></thead>
                <tbody>
                  {allRiskData.slice(0, 15).map((row, i) => (
                    <tr key={i}><td>{row.运单号 || '-'}</td><td>{row.异常类型 || '-'}</td><td><span className={`risk-level ${row.风险等级}`}>{row.风险等级 || '-'}</span></td></tr>
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
