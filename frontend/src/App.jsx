import { useState, useEffect } from 'react'
import './App.css'

const API_BASE = 'http://127.0.0.1:5000/api'

function App() {
  const [users, setUsers] = useState([])
  const [tasks, setTasks] = useState([])
  const [riskData, setRiskData] = useState([])
  const [selectedUser, setSelectedUser] = useState(null)
  const [selectedTask, setSelectedTask] = useState(null)
  const [chatMessages, setChatMessages] = useState([])
  const [inputMessage, setInputMessage] = useState('')
  const [showTaskModal, setShowTaskModal] = useState(false)
  const [loading, setLoading] = useState({
    users: false,
    tasks: false,
    riskData: false,
    chat: false
  })
  const [error, setError] = useState(null)
  const [newTask, setNewTask] = useState({
    risk_summary: '',
    assigned_to_id: '',
    risk_data_url: ''
  })

  // 初始加载
  useEffect(() => {
    console.log('[INIT] 初始化应用')
    fetchUsers()
    fetchTasks()
  }, [])

  const fetchUsers = async () => {
    console.log('[API] 开始获取用户列表')
    setLoading(prev => ({ ...prev, users: true }))
    setError(null)
    try {
      const response = await fetch(`${API_BASE}/users`)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      const data = await response.json()
      console.log(`[API] 获取用户成功: ${data.length} 条`)
      setUsers(data)
    } catch (err) {
      console.error('[ERROR] 获取用户失败:', err)
      setError(`获取用户失败: ${err.message}`)
    } finally {
      setLoading(prev => ({ ...prev, users: false }))
    }
  }

  const fetchTasks = async () => {
    console.log('[API] 开始获取任务列表')
    setLoading(prev => ({ ...prev, tasks: true }))
    try {
      const response = await fetch(`${API_BASE}/tasks`)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      const data = await response.json()
      console.log(`[API] 获取任务成功: ${data.length} 条`)
      setTasks(data)
    } catch (err) {
      console.error('[ERROR] 获取任务失败:', err)
      setError(`获取任务失败: ${err.message}`)
    } finally {
      setLoading(prev => ({ ...prev, tasks: false }))
    }
  }

  const fetchRiskData = async (filename) => {
    console.log(`[API] 开始获取风险数据: ${filename}`)
    setLoading(prev => ({ ...prev, riskData: true }))
    try {
      const response = await fetch(`${API_BASE}/risk-data/${filename}`)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      const data = await response.json()
      console.log(`[API] 获取风险数据成功: ${data.length} 条`)
      setRiskData(data)
    } catch (err) {
      console.error('[ERROR] 获取风险数据失败:', err)
      setError(`获取风险数据失败: ${err.message}`)
    } finally {
      setLoading(prev => ({ ...prev, riskData: false }))
    }
  }

  const handleUserClick = (user) => {
    console.log('[CLICK] 选择用户:', user.username)
    setSelectedUser(user)
    setSelectedTask(null)
  }

  const handleTaskClick = async (task) => {
    console.log('[CLICK] 选择任务:', task.task_id)
    setSelectedTask(task)
    setSelectedUser(null)
    if (task.risk_data_url) {
      const filename = task.risk_data_url.replace('data/risk_data_', '').replace('.csv', '001')
      await fetchRiskData(filename)
    }
  }

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return
    
    const userMessage = {
      sender: 'user',
      message: inputMessage,
      timestamp: new Date().toLocaleString()
    }
    
    console.log('[CHAT] 用户发送消息:', inputMessage)
    setChatMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setLoading(prev => ({ ...prev, chat: true }))
    
    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: inputMessage })
      })
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      
      const data = await response.json()
      console.log('[CHAT] AI回复:', data.message.substring(0, 50))
      
      setChatMessages(prev => [...prev, {
        sender: 'agent',
        message: data.message,
        timestamp: data.timestamp
      }])
    } catch (err) {
      console.error('[ERROR] 发送消息失败:', err)
      setError(`发送消息失败: ${err.message}`)
    } finally {
      setLoading(prev => ({ ...prev, chat: false }))
    }
  }

  const handleCreateTask = async () => {
    console.log('[TASK] 开始创建任务:', newTask)
    
    if (!newTask.risk_summary || !newTask.assigned_to_id || !newTask.risk_data_url) {
      setError('请填写完整信息')
      console.warn('[WARN] 创建任务信息不完整')
      return
    }
    
    try {
      const response = await fetch(`${API_BASE}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...newTask,
          creator_id: '001',
          creator_name: '李经理',
          assigned_to_name: users.find(u => u.user_id === newTask.assigned_to_id)?.username || ''
        })
      })
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      
      const createdTask = await response.json()
      console.log('[TASK] 创建成功:', createdTask.task_id)
      
      await fetchTasks()
      setShowTaskModal(false)
      setNewTask({ risk_summary: '', assigned_to_id: '', risk_data_url: '' })
      setError(null)
    } catch (err) {
      console.error('[ERROR] 创建任务失败:', err)
      setError(`创建任务失败: ${err.message}`)
    }
  }

  const dismissError = () => {
    console.log('[DISMISS] 关闭错误提示')
    setError(null)
  }

  return (
    <div className="App">
      {error && (
        <div className="error-toast" onClick={dismissError}>
          <span>⚠️ {error}</span>
          <button className="close-btn">×</button>
        </div>
      )}
      
      <header className="App-header">
        <h1>🛡️ 风控Agent助手系统</h1>
        <button className="header-btn" onClick={() => setShowTaskModal(true)}>
          + 新建任务
        </button>
      </header>
      
      <div className="main-layout">
        <div className="sidebar left">
          <h2>
            用户列表
            {loading.users && <span className="loading-dot">...</span>}
          </h2>
          <div className="user-list">
            {users.length === 0 && !loading.users ? (
              <div className="empty-tip">暂无用户</div>
            ) : (
              users.map(user => (
                <div 
                  key={user.user_id} 
                  className={`user-card ${selectedUser?.user_id === user.user_id ? 'selected' : ''}`}
                  onClick={() => handleUserClick(user)}
                >
                  <div className="user-name">{user.username}</div>
                  <div className="user-role">{user.role}</div>
                  <div className="user-dept">{user.department}</div>
                </div>
              ))
            )}
          </div>
          
          <h2>
            任务列表
            {loading.tasks && <span className="loading-dot">...</span>}
          </h2>
          <div className="task-list">
            {tasks.length === 0 && !loading.tasks ? (
              <div className="empty-tip">暂无任务</div>
            ) : (
              tasks.map(task => (
                <div 
                  key={task.task_id} 
                  className={`task-card status-${task.status} ${selectedTask?.task_id === task.task_id ? 'selected' : ''}`}
                  onClick={() => handleTaskClick(task)}
                >
                  <div className="task-id">{task.task_id}</div>
                  <div className="task-summary">{task.risk_summary}</div>
                  <div className="task-time">{task.created_time}</div>
                  <div className="task-status">{task.status}</div>
                </div>
              ))
            )}
          </div>
        </div>
        
        <div className="main-content">
          <div className="chat-header">
            <h2>💬 智能体对话</h2>
          </div>
          
          <div className="chat-messages">
            {chatMessages.length === 0 && (
              <div className="welcome-message">
                <p>👋 欢迎使用风控Agent助手！</p>
                <p>我可以帮助您：</p>
                <ul>
                  <li>分析风险数据</li>
                  <li>创建和下发任务</li>
                  <li>查看任务状态</li>
                  <li>获取风险建议</li>
                </ul>
              </div>
            )}
            {chatMessages.map((msg, index) => (
              <div key={index} className={`message ${msg.sender}`}>
                <div className="message-header">
                  <span className="sender">{msg.sender === 'user' ? '👤 我' : '🤖 Agent'}</span>
                  <span className="timestamp">{msg.timestamp}</span>
                </div>
                <div className="message-content">{msg.message}</div>
              </div>
            ))}
            {loading.chat && (
              <div className="message agent loading">
                <div className="message-content">正在思考...</div>
              </div>
            )}
          </div>
          
          <div className="chat-input">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && !loading.chat && handleSendMessage()}
              placeholder="输入消息..."
              disabled={loading.chat}
            />
            <button onClick={handleSendMessage} disabled={loading.chat || !inputMessage.trim()}>
              {loading.chat ? '发送中...' : '发送'}
            </button>
          </div>
        </div>
        
        <div className="sidebar right">
          <h2>详情信息</h2>
          {loading.riskData ? (
            <div className="loading-tip">加载中...</div>
          ) : selectedTask ? (
            <div className="task-detail">
              <h3>任务详情</h3>
              <p><strong>任务ID:</strong> {selectedTask.task_id}</p>
              <p><strong>风险简述:</strong> {selectedTask.risk_summary}</p>
              <p><strong>状态:</strong> <span className={`status-tag ${selectedTask.status}`}>{selectedTask.status}</span></p>
              <p><strong>创建人:</strong> {selectedTask.creator_name}</p>
              <p><strong>执行人:</strong> {selectedTask.assigned_to_name}</p>
              <p><strong>创建时间:</strong> {selectedTask.created_time}</p>
              {selectedTask.completed_time && <p><strong>完成时间:</strong> {selectedTask.completed_time}</p>}
              
              {riskData.length > 0 && (
                <div className="risk-data-preview">
                  <h4>风险数据预览 ({riskData.length}条)</h4>
                  <div className="risk-table-wrapper">
                    <table className="risk-table">
                      <thead>
                        <tr>
                          {Object.keys(riskData[0] || {}).slice(0, 5).map(key => (
                            <th key={key}>{key}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {riskData.slice(0, 5).map((row, i) => (
                          <tr key={i}>
                            {Object.values(row).slice(0, 5).map((val, j) => (
                              <td key={j}>{val}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          ) : selectedUser ? (
            <div className="user-detail">
              <h3>用户信息</h3>
              <p><strong>姓名:</strong> {selectedUser.username}</p>
              <p><strong>角色:</strong> {selectedUser.role}</p>
              <p><strong>部门:</strong> {selectedUser.department}</p>
              <p><strong>ID:</strong> {selectedUser.user_id}</p>
              {selectedUser.employee_id && <p><strong>员工ID:</strong> {selectedUser.employee_id}</p>}
            </div>
          ) : (
            <div className="placeholder">
              请点击左侧用户或任务查看详情
            </div>
          )}
        </div>
      </div>

      {showTaskModal && (
        <div className="modal-overlay" onClick={() => setShowTaskModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h2>创建新任务</h2>
            <div className="form-group">
              <label>风险简述:</label>
              <input 
                type="text" 
                value={newTask.risk_summary}
                onChange={e => setNewTask({...newTask, risk_summary: e.target.value})}
                placeholder="请输入风险简述"
              />
            </div>
            <div className="form-group">
              <label>指派给:</label>
              <select 
                value={newTask.assigned_to_id}
                onChange={e => setNewTask({...newTask, assigned_to_id: e.target.value})}
              >
                <option value="">请选择执行人</option>
                {users.filter(u => u.role === '一线操作人员').map(user => (
                  <option key={user.user_id} value={user.user_id}>{user.username} - {user.department}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>风险数据:</label>
              <select 
                value={newTask.risk_data_url}
                onChange={e => setNewTask({...newTask, risk_data_url: e.target.value})}
              >
                <option value="">请选择风险数据</option>
                {[1,2,3,4,5,6,7,8,9,10].map(i => (
                  <option key={i} value={`data/risk_data_00${i}.csv`}>风险数据 {i}</option>
                ))}
              </select>
            </div>
            <div className="modal-actions">
              <button onClick={() => setShowTaskModal(false)}>取消</button>
              <button className="primary" onClick={handleCreateTask}>创建</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
