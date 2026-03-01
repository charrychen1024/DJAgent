import { useState, useEffect } from 'react'
import './App.css'

const API_BASE = 'http://127.0.0.1:5000/api'

function App() {
  console.log('App component rendering')
  const [users, setUsers] = useState([])
  const [tasks, setTasks] = useState([])
  const [selectedUser, setSelectedUser] = useState(null)
  const [chatMessages, setChatMessages] = useState([])
  const [inputMessage, setInputMessage] = useState('')

  useEffect(() => {
    console.log('useEffect running')
    fetchUsers()
    fetchTasks()
  }, [])

  const fetchUsers = async () => {
    try {
      console.log('Fetching users from:', `${API_BASE}/users`)
      const response = await fetch(`${API_BASE}/users`)
      const data = await response.json()
      console.log('Users fetched:', data.length)
      setUsers(data)
    } catch (error) {
      console.error('Error fetching users:', error)
    }
  }

  const fetchTasks = async () => {
    try {
      console.log('Fetching tasks from:', `${API_BASE}/tasks`)
      const response = await fetch(`${API_BASE}/tasks`)
      const data = await response.json()
      console.log('Tasks fetched:', data.length)
      setTasks(data)
    } catch (error) {
      console.error('Error fetching tasks:', error)
    }
  }

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return
    
    const newMessage = {
      sender: 'user',
      message: inputMessage,
      timestamp: new Date().toLocaleString()
    }
    
    setChatMessages([...chatMessages, newMessage])
    setInputMessage('')
    
    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: inputMessage })
      })
      const data = await response.json()
      
      setChatMessages(prev => [...prev, {
        sender: 'agent',
        message: data.message,
        timestamp: data.timestamp
      }])
    } catch (error) {
      console.error('Error sending message:', error)
    }
  }

  return (
    <div className="App">
      <header className="App-header">
        <h1>🛡️ 风控Agent助手系统</h1>
      </header>
      
      <div className="main-layout">
        <div className="sidebar left">
          <h2>用户列表</h2>
          <div className="user-list">
            {users.map(user => (
              <div 
                key={user.user_id} 
                className={`user-card ${selectedUser?.user_id === user.user_id ? 'selected' : ''}`}
                onClick={() => setSelectedUser(user)}
              >
                <div className="user-name">{user.username}</div>
                <div className="user-role">{user.role}</div>
                <div className="user-dept">{user.department}</div>
              </div>
            ))}
          </div>
          
          <h2>任务列表</h2>
          <div className="task-list">
            {tasks.map(task => (
              <div key={task.task_id} className={`task-card status-${task.status}`}>
                <div className="task-id">{task.task_id}</div>
                <div className="task-summary">{task.risk_summary}</div>
                <div className="task-status">{task.status}</div>
              </div>
            ))}
          </div>
        </div>
        
        <div className="main-content">
          <div className="chat-header">
            <h2>💬 智能体对话</h2>
          </div>
          
          <div className="chat-messages">
            {chatMessages.map((msg, index) => (
              <div key={index} className={`message ${msg.sender}`}>
                <div className="message-header">
                  <span className="sender">{msg.sender === 'user' ? '👤 我' : '🤖 Agent'}</span>
                  <span className="timestamp">{msg.timestamp}</span>
                </div>
                <div className="message-content">{msg.message}</div>
              </div>
            ))}
          </div>
          
          <div className="chat-input">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
              placeholder="输入消息..."
            />
            <button onClick={handleSendMessage}>发送</button>
          </div>
        </div>
        
        <div className="sidebar right">
          <h2>辅助信息</h2>
          {selectedUser ? (
            <div className="user-detail">
              <h3>选中用户</h3>
              <p><strong>姓名:</strong> {selectedUser.username}</p>
              <p><strong>角色:</strong> {selectedUser.role}</p>
              <p><strong>部门:</strong> {selectedUser.department}</p>
              <p><strong>ID:</strong> {selectedUser.user_id}</p>
            </div>
          ) : (
            <div className="placeholder">
              请点击左侧用户查看详情
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default App
