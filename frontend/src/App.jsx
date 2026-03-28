import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ChatMessage, ChatInput, FormCardBubble, SkillSelector } from './components'
import TodoTabs from './components/TodoTabs'
import { mockTodos } from './data/mockTodos'
import './App.css'

const API_BASE = '/api'
// EventSource 需要完整的 URL 指向后端，不能使用相对路径
const SSE_BASE = 'http://localhost:5005/api'

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
      // 使用 employee_id 匹配（优先）或 user_id
      const user = users.find(u => u.employee_id === selectedUserId || u.user_id === selectedUserId)
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
              <option key={user.employee_id} value={user.employee_id}>
                {user.username} - {user.employee_id}
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
  // 待办项系统 - Phase 1
  const [leftPanelOpen, setLeftPanelOpen] = useState(false) // 左侧面板展开/折叠
  const [selectedTodoId, setSelectedTodoId] = useState(null) // 当前选中的待办项ID
  const [selectedTodo, setSelectedTodo] = useState(null) // 当前选中的待办项详情
  const [todoTabsWidth, setTodoTabsWidth] = useState(400) // TodoTabs面板宽度（像素）

  // 对话相关状态（Web端 Manager 独立存储）
  const [chatList, setChatList] = useState([])  // 对话列表
  const [currentChatId, setCurrentChatId] = useState(null)  // 当前对话ID
  const [showSidebar, setShowSidebar] = useState(false)  // 是否显示历史对话列表（弹窗）
  // 对话左侧边栏状态
  const [chatSidebarOpen, setChatSidebarOpen] = useState(true)  // 是否展开对话左侧栏
  const [chatSidebarWidth, setChatSidebarWidth] = useState(280)  // 对话左侧栏宽度
  // 删除对话确认
  const [deleteConfirm, setDeleteConfirm] = useState(null)  // 要删除的对话ID

  // SkillSelector 状态和 ref
  const [showSkillSelector, setShowSkillSelector] = useState(false)
  const skillButtonRef = useRef(null)

  // SSE 连接 ref - 用于正确管理生命周期
  const eventSourceRef = useRef(null)

  useEffect(() => {
    const userId = currentUser?.employee_id || currentUser?.user_id
    if (userId) {
      fetchTasks()
      fetchAllRiskData()
      fetchChatList()  // 获取对话列表
    }
  }, [currentUser?.employee_id, currentUser?.user_id])

  // 当对话列表加载完成后，自动加载最近一个有消息的对话
  useEffect(() => {
    if (chatList.length > 0 && !currentChatId) {
      const latestChat = chatList[0]
      // 只加载有消息的对话
      if (latestChat.messages && latestChat.messages.length > 0) {
        loadChat(latestChat.chat_id, true)
      }
    }
  }, [chatList])

  // SSE 事件监听 - 实时接收任务通知（改进版：正确的连接管理）
  useEffect(() => {
    const userId = currentUser?.employee_id || currentUser?.user_id
    if (!userId) return

    // 关闭旧连接
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    const eventSource = new EventSource(`${SSE_BASE}/events/${userId}`)
    eventSourceRef.current = eventSource

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
      eventSource.close()
      eventSourceRef.current = null
      console.log('[SSE] 5秒后尝试重新连接...')

      const retryTimer = setTimeout(() => {
        const currentUserId = currentUser?.employee_id || currentUser?.user_id
        if (currentUserId && !eventSourceRef.current) {
          const newSource = new EventSource(`${SSE_BASE}/events/${currentUserId}`)
          eventSourceRef.current = newSource
          console.log('[SSE] 重新连接成功')
        }
      }, 5000)

      return () => clearTimeout(retryTimer)
    }

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
        eventSourceRef.current = null
        console.log('[SSE] Manager 断开连接')
      }
    }
  }, [currentUser?.employee_id, currentUser?.user_id, selectedTask])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  // 待办项选择处理 - 当选中ID变化时，更新selectedTodo
  useEffect(() => {
    if (selectedTodoId) {
      const todo = mockTodos.find(t => t.id === selectedTodoId)
      if (todo) {
        setSelectedTodo(todo)
        setRightPanelOpen(true) // 选中时自动打开右侧面板
      }
    } else {
      setSelectedTodo(null)
    }
  }, [selectedTodoId])

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
    { task_id: 'TASK_002', risk_summary: '运单WLYD002超时派送核查', status: '已完成', assigned_to_name: '刘秀英快递', created_time: '2026-03-01 14:30', creator_name: '王经理', completed_time: '2026-03-01 16:00' },
    { task_id: 'TASK_003', risk_summary: '运单WLYD003未及时签收核查', status: '已创建', assigned_to_name: '黄强快递', created_time: '2026-03-02 09:00', creator_name: '王经理' },
  ]

  const fetchTasks = async () => {
    const userId = currentUser?.employee_id || currentUser?.user_id
    if (!userId) {
      setTasks([])
      return
    }
    setLoading(prev => ({ ...prev, tasks: true }))
    try {
      // 根据当前Tab获取对应类型的任务（日度/月度）
      const taskType = dataTab === 'daily' ? '日度' : '月度'
      const url = `${API_BASE}/tasks?employee_id=${userId}&task_type=${taskType}`
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
    const userId = currentUser?.employee_id || currentUser?.user_id
    setLoading(prev => ({ ...prev, riskData: true }))
    const allData = []
    for (let i = 1; i <= 10; i++) {
      try {
        const filename = `00${i}`
        // 带上user_id参数，后端会根据用户地区过滤数据
        const url = userId ? `${API_BASE}/risk-data/${filename}?employee_id=${userId}` : `${API_BASE}/risk-data/${filename}`
        const response = await fetch(url)
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
    const userId = currentUser?.employee_id || currentUser?.user_id
    setLoading(prev => ({ ...prev, riskData: true }))
    const allData = []
    try {
      // 带上user_id参数，后端会根据用户地区过滤数据
      const url = userId ? `${API_BASE}/risk-data/monthly?employee_id=${userId}` : `${API_BASE}/risk-data/monthly`
      const response = await fetch(url)
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
  // 创建新对话
  const handleNewChat = async () => {
    const userId = currentUser?.employee_id || currentUser?.user_id
    try {
      // 先关闭旧的Agent会话（让新对话完全重新开始）
      await fetch(`${API_BASE}/session/cleanup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ employee_ids: [userId] })
      })
      
      const response = await fetch(`${API_BASE}/chats`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          employee_id: userId,
          username: currentUser.username
        })
      })
      const data = await response.json()
      if (data.status === 'success') {
        setCurrentChatId(data.chat.chat_id)
        setChatMessages([])
        setIsInitialChat(true)
        // 刷新对话列表
        fetchChatList()
      }
    } catch (err) {
      console.error('[ERROR] 创建对话失败:', err)
    }
  }

  // 删除对话
  const handleDeleteChat = async (chatId) => {
    const userId = currentUser?.employee_id || currentUser?.user_id
    try {
      const response = await fetch(`${API_BASE}/chats/${chatId}?employee_id=${userId}`, {
        method: 'DELETE'
      })
      const data = await response.json()
      if (data.status === 'success') {
        // 如果删除的是当前对话，清空当前对话
        if (currentChatId === chatId) {
          setCurrentChatId(null)
          setChatMessages([])
          setIsInitialChat(true)
        }
        // 刷新列表
        fetchChatList()
      }
    } catch (err) {
      console.error('[ERROR] 删除对话失败:', err)
    }
    setDeleteConfirm(null)
  }

  // 获取对话列表
  const fetchChatList = async () => {
    const userId = currentUser?.employee_id || currentUser?.user_id
    try {
      const response = await fetch(`${API_BASE}/chats?employee_id=${userId}`)
      const chats = await response.json()
      setChatList(chats)
    } catch (err) {
      console.error('[ERROR] 获取对话列表失败:', err)
    }
  }

  // 加载指定对话
  // 添加 isAutoLoad 参数区分自动加载和手动点击加载
  const loadChat = async (chatId, isAutoLoad = false) => {
    const userId = currentUser?.employee_id || currentUser?.user_id
    try {
      const response = await fetch(`${API_BASE}/chats/${chatId}?employee_id=${userId}`)
      const data = await response.json()
      if (data.status === 'success' && data.chat) {
        setCurrentChatId(chatId)
        // 转换消息格式
        const messages = data.chat.messages.map(msg => ({
          sender: msg.sender_type === 'user' ? 'user' : 'agent',
          message: msg.message,
          timestamp: msg.timestamp,
          files: msg.files
        }))
        setChatMessages(messages)
        setIsInitialChat(messages.length === 0)
        setShowSidebar(false)
      } else {
        // 对话不存在
        console.warn('[WARN] 对话不存在:', data.message)
        // 如果不是自动加载模式，显示提示
        if (!isAutoLoad) {
          alert('对话已失效，请选择其他对话')
          // 刷新对话列表
          fetchChatList()
        }
        // 清除无效的 chatId
        setCurrentChatId(null)
        setChatMessages([])
      }
    } catch (err) {
      console.error('[ERROR] 加载对话失败:', err)
    }
  }

  // 发送消息 - 流式版本
  const handleSendMessage = async () => {
    if (!inputMessage.trim() && pendingFiles.length === 0) return

    const messageToSend = inputMessage
    const filesToSend = [...pendingFiles]

    // 先将用户消息显示在对话框（乐观更新）
    const fileDesc = filesToSend.length > 0
      ? `\n[附件: ${filesToSend.map(f => f.name).join(', ')}]`
      : ''

    const userMessage = {
      sender: 'user',
      message: messageToSend + fileDesc,
      timestamp: new Date().toLocaleString(),
      files: filesToSend.map(f => ({ name: f.name, type: f.type }))
    }
    setChatMessages(prev => [...prev, userMessage])
    setIsInitialChat(false)

    setInputMessage('')
    setPendingFiles([])
    setLoading(prev => ({ ...prev, chat: true }))

    // 添加空的agent消息占位
    const agentMessageId = `agent-${Date.now()}`
    setChatMessages(prev => [...prev, {
      sender: 'agent',
      message: '',
      messageId: agentMessageId,
      content: [],  // 存储content blocks
      isStreaming: true,
      timestamp: new Date().toLocaleString()
    }])

    const userId = currentUser?.employee_id || currentUser?.user_id

    try {
      // 使用流式API
      const response = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: messageToSend,
          employee_id: userId,
          username: currentUser.username
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let currentEventType = null
      let currentContent = ''
      let currentBlockIndex = -1
      let currentBlockType = null
      let messageContent = []
      let accumulatedText = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEventType = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6).trim())
              const eventData = data.delta || data

              // 处理不同事件类型
              if (currentEventType === 'content_block_start') {
                currentBlockIndex = data.index || 0
                currentBlockType = data.content_block?.type
                currentContent = ''

                // 添加新block
                messageContent.push({
                  type: currentBlockType,
                  text: '',
                  thinking: '',
                  name: data.content_block?.name || '',
                  input: data.content_block?.input || {},
                  id: data.content_block?.id || ''
                })
              } else if (currentEventType === 'content_block_delta') {
                if (eventData.type === 'text_delta' && eventData.text) {
                  accumulatedText += eventData.text
                  // 更新最后一个block
                  if (messageContent.length > 0) {
                    const lastBlock = messageContent[messageContent.length - 1]
                    lastBlock.text = accumulatedText
                  }
                } else if (eventData.type === 'thinking_delta' && eventData.thinking) {
                  if (messageContent.length > 0) {
                    const lastBlock = messageContent[messageContent.length - 1]
                    lastBlock.thinking = (lastBlock.thinking || '') + eventData.thinking
                  }
                }
              }

              // 更新UI
              setChatMessages(prev => prev.map(msg => {
                if (msg.messageId === agentMessageId) {
                  return {
                    ...msg,
                    content: [...messageContent],
                    message: accumulatedText  // 兼容旧字段
                  }
                }
                return msg
              }))
            } catch (e) {
              // 解析JSON失败，跳过
            }
          }
        }
      }

      // 流式结束
      setChatMessages(prev => prev.map(msg => {
        if (msg.messageId === agentMessageId) {
          return { ...msg, isStreaming: false }
        }
        return msg
      }))

    } catch (err) {
      console.error('[ERROR] 发送消息失败:', err)
      // 降级：使用非流式API
      console.log('[INFO] 回退到非流式API')
      try {
        // 先创建对话
        let activeChatId = currentChatId
        if (!activeChatId) {
          const createRes = await fetch(`${API_BASE}/chats`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              employee_id: userId,
              username: currentUser.username
            })
          })
          const createData = await createRes.json()
          if (createData.status === 'success') {
            activeChatId = createData.chat.chat_id
            setCurrentChatId(activeChatId)
          }
        }

        if (activeChatId) {
          const formData = new FormData()
          formData.append('message', messageToSend)
          formData.append('employee_id', userId)
          formData.append('username', currentUser.username)
          filesToSend.forEach(f => formData.append('files', f.file, f.name))

          const response = await fetch(`${API_BASE}/chats/${activeChatId}/messages`, {
            method: 'POST',
            body: formData
          })
          const data = await response.json()
          if (data.status === 'success') {
            // 替换占位消息
            setChatMessages(prev => prev.map(msg => {
              if (msg.messageId === agentMessageId) {
                return {
                  sender: 'agent',
                  message: data.agent_reply.message,
                  timestamp: data.agent_reply.timestamp
                }
              }
              return msg
            }))
            fetchChatList()
            fetchTasks()
          }
        }
      } catch (fallbackErr) {
        console.error('[ERROR] 降级API也失败:', fallbackErr)
        setChatMessages(prev => prev.map(msg => {
          if (msg.messageId === agentMessageId) {
            return {
              ...msg,
              message: '抱歉，发送消息失败，请稍后重试。',
              isStreaming: false
            }
          }
          return msg
        }))
      }
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
      {/* TodoTabs for left sidebar - Phase 2: 集成风险数据和任务追踪 */}
      <TodoTabs
        // Tab 1: Todos
        todos={mockTodos}
        selectedTodoId={selectedTodoId}
        onSelectTodo={setSelectedTodoId}
        isOpen={leftPanelOpen}
        onToggleOpen={setLeftPanelOpen}
        // Tab 2: Risk Data
        riskData={filteredRiskData}
        riskStats={riskStats}
        riskColumns={columns}
        dataTab={dataTab}
        onDataTabChange={setDataTab}
        selectedRiskRows={selectedRows}
        onSelectRiskRow={handleSelectRow}
        onSelectAllRiskRows={handleSelectAll}
        globalSearch={globalSearch}
        onGlobalSearchChange={setGlobalSearch}
        onGlobalSearch={handleGlobalSearch}
        onAddToChat={handleAddSelectedToChat}
        riskLoading={loading.riskData}
        filteredRiskData={filteredRiskData}
        riskCurrentPage={currentPage}
        riskPageSize={pageSize}
        onRiskPageChange={handlePageChange}
        onRiskPageSizeChange={handlePageSizeChange}
        onRiskRowClick={() => {}} // TODO: implement detail panel for risk data
        // Tab 3: Task Tracking
        tasks={tasks}
        selectedTask={selectedTask}
        onSelectTask={handleTaskClick}
        tasksCollapsed={tasksCollapsed}
        onToggleTasks={setTasksCollapsed}
        filteredTasks={filteredTasks}
        tasksLoading={loading.tasks}
        // Resize props
        width={todoTabsWidth}
        onWidthChange={setTodoTabsWidth}
      />

      {/* 对话左侧栏 - 可折叠 */}
      <div className={`chat-sidebar ${chatSidebarOpen ? 'open' : 'collapsed'}`} style={{ width: chatSidebarOpen ? chatSidebarWidth : 0 }}>
        <div className="sidebar-header">
          <button className="new-chat-btn" onClick={() => { handleNewChat(); setChatSidebarOpen(false); }}>
            <span className="btn-icon">+</span> 新建对话
          </button>
        </div>
        <div className="sidebar-section-title">历史对话</div>
        <div className="sidebar-content">
          {chatList.length === 0 ? (
            <p className="no-chats">暂无历史对话</p>
          ) : (
            <ul className="chat-list">
              {chatList.map(chat => (
                <li 
                  key={chat.chat_id} 
                  className={`chat-list-item ${currentChatId === chat.chat_id ? 'active' : ''}`}
                  onClick={() => { loadChat(chat.chat_id); setChatSidebarOpen(false); }}
                >
                  <div className="chat-item-info">
                    <div className="chat-item-title">{chat.title.length > 15 ? chat.title.substring(0, 15) + '...' : chat.title}</div>
                    <div className="chat-item-meta">{chat.created_at}</div>
                  </div>
                  <button 
                    className="chat-item-delete" 
                    onClick={(e) => { e.stopPropagation(); setDeleteConfirm(chat.chat_id); }}
                    title="删除对话"
                  >
                    ×
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* 删除确认弹窗 */}
      {deleteConfirm && (
        <div className="modal-overlay" onClick={() => setDeleteConfirm(null)}>
          <div className="confirm-dialog" onClick={e => e.stopPropagation()}>
            <h3>确认删除</h3>
            <p>确定要删除这条历史对话吗？此操作不可恢复。</p>
            <div className="confirm-actions">
              <button className="cancel-btn" onClick={() => setDeleteConfirm(null)}>取消</button>
              <button className="confirm-btn danger" onClick={() => handleDeleteChat(deleteConfirm)}>确认删除</button>
            </div>
          </div>
        </div>
      )}

      <div className="main-content" style={{ marginLeft: chatSidebarOpen ? 0 : 0 }}>
        <div className="chat-header">
          <div className="chat-header-left">
            <button 
              className={`sidebar-toggle-btn ${chatSidebarOpen ? 'active' : ''}`} 
              onClick={() => setChatSidebarOpen(!chatSidebarOpen)}
              title={chatSidebarOpen ? "收起侧边栏" : "展开侧边栏"}
            >
              <span className="menu-lines">
                <span className="line line-1"></span>
                <span className="line line-2"></span>
                <span className="line line-3"></span>
              </span>
            </button>
            <h3>💬 盾仔</h3>
          </div>
        </div>
        {/* 保留原来的弹窗式历史列表作为备用（可以删除） */}
        {showSidebar && chatList.length > 0 && (
          <div className="chat-list-dropdown">
            <ul className="chat-list">
              {chatList.map(chat => (
                <li 
                  key={chat.chat_id} 
                  className={`chat-list-item ${currentChatId === chat.chat_id ? 'active' : ''}`}
                  onClick={() => loadChat(chat.chat_id)}
                >
                  <div className="chat-item-title">{chat.title.length > 15 ? chat.title.substring(0, 15) + '...' : chat.title}</div>
                  <div className="chat-item-meta">{chat.created_at}</div>
                </li>
              ))}
            </ul>
          </div>
        )}
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
                  <li>分析风险数据</li>
                  <li>创建和下发任务</li>
                  <li>查看任务状态</li>
                  <li>获取风险建议</li>
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
            <ChatMessage
              key={i}
              message={{
                type: msg.type || 'text',
                sender: msg.sender === 'user' ? 'user' : 'agent',
                timestamp: msg.timestamp,
                content: msg.message,
                // Backward compatibility: support message field as fallback
                message: msg.message,
                files: msg.files || [],
                // Form fields if present
                schema: msg.schema,
                form_id: msg.form_id,
                task_id: msg.task_id,
                title: msg.title,
                summary: msg.summary,
                status: msg.status,
                data: msg.data
              }}
              onFormSubmit={(data) => console.log('Form submitted:', data)}
              onFormCancel={() => console.log('Form canceled')}
              onFormModify={(data) => console.log('Form modified:', data)}
            />
          ))}
          {loading.chat && (
            <ChatMessage
              message={{
                type: 'text',
                sender: 'agent',
                content: '正在思考...',
                timestamp: new Date().toISOString()
              }}
            />
          )}
          <div ref={messagesEndRef} />
        </div>
        <ChatInput
          value={inputMessage}
          onChange={setInputMessage}
          onSend={handleSendMessage}
          onFileSelect={(files) => {
            // Handle file selection
            const newFiles = Array.from(files).map((file, idx) => ({
              id: Date.now() + idx,
              file,
              name: file.name,
              size: file.size,
              type: file.type
            }))
            setPendingFiles([...pendingFiles, ...newFiles])
          }}
          onFileRemove={(file) => {
            setPendingFiles(pendingFiles.filter(f => f.name !== file.name))
          }}
          files={pendingFiles.map(f => ({ name: f.name }))}
          disabled={loading.chat}
          loading={loading.chat}
          placeholder="输入消息... (Shift+Enter 换行)"
          onSkillButtonClick={() => setShowSkillSelector(!showSkillSelector)}
          skillButtonRef={skillButtonRef}
        />

        {/* 历史对话列表弹窗 */}
        {showSidebar && (
          <div className="chat-list-overlay" onClick={() => setShowSidebar(false)}>
            <div className="chat-list-modal" onClick={e => e.stopPropagation()}>
              <div className="chat-list-header">
                <h3>📋 历史对话</h3>
                <button className="close-btn" onClick={() => setShowSidebar(false)}>×</button>
              </div>
              <div className="chat-list-content">
                {chatList.length === 0 ? (
                  <div className="chat-list-empty">
                    <p>暂无历史对话</p>
                    <button onClick={() => { handleNewChat(); setShowSidebar(false); }}>创建新对话</button>
                  </div>
                ) : (
                  <ul className="chat-list">
                    {chatList.map(chat => (
                      <li 
                        key={chat.chat_id} 
                        className={`chat-list-item ${currentChatId === chat.chat_id ? 'active' : ''}`}
                        onClick={() => loadChat(chat.chat_id)}
                      >
                        <div className="chat-item-title">{chat.title.length > 15 ? chat.title.substring(0, 15) + '...' : chat.title}</div>
                        <div className="chat-item-meta">
                          <span>{chat.created_at}</span>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="chat-list-footer">
                <button className="new-chat-btn" onClick={() => { handleNewChat(); setShowSidebar(false); }}>
                  ➕ 新建对话
                </button>
              </div>
            </div>
          </div>
        )}

        {/* SkillSelector 下拉框 - 在App根层级渲染，避免position:fixed的z-index问题 */}
        <SkillSelector
          visible={showSkillSelector}
          onClose={() => setShowSkillSelector(false)}
          onSelect={(skill, insertText) => {
            setInputMessage(inputMessage + (inputMessage ? '\n' : '') + insertText)
            setShowSkillSelector(false)
          }}
          anchorEl={skillButtonRef.current}
          userRole={currentUser?.role === '业务负责人' || currentUser?.role === '普通分析人员' ? 'manager' : 'staff'}
        />
      </div>
      {rightPanelOpen && (
        <div className={`resize-handle ${isDraggingRight ? 'dragging' : ''}`} onMouseDown={() => setIsDraggingRight(true)} />
      )}
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
            {selectedTodo ? (
              <div className="task-detail">
                <h4>待办项详情</h4>

                {/* Quick action buttons */}
                <div className="quick-action-buttons">
                  <button
                    className="quick-action-btn add-to-chat"
                    title="添加到对话"
                    onClick={() => {
                      // Add selected todo to chat message
                      const todoInfo = `待办项: ${selectedTodo.title}\n优先级: ${selectedTodo.priority}\n类型: ${selectedTodo.type}`;
                      setInputMessage(prev => prev + (prev ? '\n' : '') + todoInfo);
                    }}
                  >
                    💬
                  </button>
                  <button
                    className="quick-action-btn dispatch"
                    title="一键下发"
                    onClick={() => {
                      // Quick dispatch action
                      console.log('Quick dispatch:', selectedTodo.id);
                    }}
                  >
                    ⚡
                  </button>
                </div>

                <p><strong>优先级:</strong> <span className={`priority-tag priority-${selectedTodo.priority?.toLowerCase()}`}>{selectedTodo.priority}</span></p>
                <p><strong>标题:</strong> {selectedTodo.title}</p>
                <p><strong>类型:</strong> {selectedTodo.type}</p>
                <p><strong>描述:</strong> {selectedTodo.description}</p>
                <p><strong>分类:</strong> {selectedTodo.category}</p>
                <p><strong>状态:</strong> <span className={`status-tag ${selectedTodo.status === '已处理' ? 'completed' : 'pending'}`}>{selectedTodo.status}</span></p>
                <p><strong>严重程度:</strong> {selectedTodo.severity}</p>
                <p><strong>推荐分配人:</strong> {typeof selectedTodo.recommended_assignee === 'object' ? selectedTodo.recommended_assignee?.name : selectedTodo.recommended_assignee}</p>
                <p><strong>预期处理时间:</strong> {typeof selectedTodo.expected_handling_time === 'object' ? selectedTodo.expected_handling_time?.due_date : selectedTodo.expected_handling_time}</p>

                {typeof selectedTodo.analysis === 'object' && selectedTodo.analysis && (
                  <div className="analysis-section">
                    <h5>📊 分析结果</h5>
                    <p>{JSON.stringify(selectedTodo.analysis)}</p>
                  </div>
                )}
              </div>
            ) : selectedTask ? (
              <div className="task-detail">
                <h4>任务详情</h4>
                <p><strong>任务ID:</strong> {selectedTask.task_id}</p>
                <p><strong>风险简述:</strong> {selectedTask.risk_summary}</p>
                <p><strong>状态:</strong> <span className={`status-tag ${selectedTask.status}`}>{selectedTask.status}</span></p>
                <p><strong>创建人:</strong> {selectedTask.creator_name}</p>
                <p><strong>执行人:</strong> {selectedTask.assigned_to_name}</p>
                <p><strong>地区:</strong> {selectedTask.region || '-'}</p>
                <p><strong>任务类型:</strong> {selectedTask.task_type || '-'}</p>
                <p><strong>创建时间:</strong> {selectedTask.created_time}</p>
                {selectedTask.sent_time && <p><strong>发送时间:</strong> {selectedTask.sent_time}</p>}
                {selectedTask.completed_time && <p><strong>完成时间:</strong> {selectedTask.completed_time}</p>}
                {selectedTask.feedback_deadline && <p><strong>反馈截止:</strong> {selectedTask.feedback_deadline}</p>}

                <div className="feedback-section">
                  <h5>📝 反馈详情</h5>
                  {(selectedTask.feedback_summary || taskFeedback?.feedback_summary) ? (
                    <div className="feedback-summary">
                      <p>{selectedTask.feedback_summary || taskFeedback?.feedback_summary}</p>
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
            ) : <div className="placeholder">点击左侧任务或待办项查看详情</div>}
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
  const [submittedForms, setSubmittedForms] = useState({}) // Fix 19: 记录已提交的表单状态 {form_id: true}
  const [editingForms, setEditingForms] = useState({}) // Fix 19: 记录正在编辑的表单状态 {form_id: true}
  const tasksRef = useRef([])  // 使用 ref 存储最新任务列表，解决 SSE 闭包问题
  const messagesEndRef = useRef(null)
  const fileInputRef = useRef(null)
  const inputTextareaRef = useRef(null)

  // 获取任务列表
  const fetchTasks = async () => {
    const userId = currentUser?.employee_id || currentUser?.user_id
    if (!userId) {
      setTasks([])
      return
    }
    try {
      const response = await fetch(`${API_BASE}/tasks?employee_id=${userId}`)
      const data = await response.json()
      const taskList = data.length > 0 ? data : []
      setTasks(taskList)
      tasksRef.current = taskList  // 同步更新 ref
    } catch (err) {
      console.error('[ERROR] 获取任务失败:', err)
      setTasks([])
    }
  }

  // 页面加载时初始化
  useEffect(() => {
    const userId = currentUser?.employee_id || currentUser?.user_id
    if (userId) {
      fetchTasks()
      initConversation()
    }
  }, [currentUser?.employee_id, currentUser?.user_id])

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
    const userId = currentUser?.employee_id || currentUser?.user_id
    if (!userId) return

    const eventSource = new EventSource(`${SSE_BASE}/events/${userId}`)

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        console.log('[SSE Staff] 收到事件:', data.type, data)

        if (data.type === 'new_task') {
          // 收到新任务通知
          console.log('[SSE Staff] 收到新任务:', data.task_id)

          // 自动切换到新任务
          const newTaskId = data.task_id

          // 立即刷新任务列表，然后设置 selectedTask
          const fetchAndSetTask = async () => {
            try {
              const response = await fetch(`${API_BASE}/tasks?employee_id=${userId}&_t=${Date.now()}`)
              const updatedTasks = await response.json()
              setTasks(updatedTasks)
              tasksRef.current = updatedTasks

              // 从更新后的任务列表中查找完整任务
              const newTask = updatedTasks.find(t => t.task_id === newTaskId)
              if (newTask) {
                setSelectedTask(newTask)
                console.log('[SSE Staff] 已更新 selectedTask:', newTask.task_id)
              }
            } catch (err) {
              console.error('[SSE Staff] 刷新任务列表失败:', err)
            }
          }

          fetchAndSetTask()

          // 调用后端API触发Staff Agent发送消息
          console.log('[SSE Staff] 调用notify-staff API...')
          fetch(`${API_BASE}/tasks/${data.task_id}/notify-staff`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              employee_id: userId,
              username: currentUser.username
            })
          })
            .then(res => res.json())
            .then(result => {
              console.log('[SSE Staff] notify-staff 结果:', result)
              if (!result.success) {
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

          // 设置当前任务（如果还没有选中任务或者任务不匹配）
          if (data.task_info && (!selectedTask || selectedTask.task_id !== data.task_id)) {
            setSelectedTask(data.task_info)
            console.log('[SSE Staff] 设置当前任务:', data.task_info.task_id)
          }

          // Fix 9 & Fix 10: 从 SSE 事件数据中构建完整的消息对象，包括 message_type、schema、form_id
          // Fix 10: 使用 message_type 替代 type，避免与 SSE 事件类型冲突
          const newMessage = data.message
          if (newMessage) {
            const messageObj = {
              sender: 'agent',
              message: newMessage,
              type: data.message_type === 'form_card' ? 'form_card' : 'text',  // 改为检查 message_type
              timestamp: new Date().toLocaleString(),
            }

            // 如果是表单卡片，添加 schema 和 form_id
            if (data.message_type === 'form_card' && data.schema) {
              messageObj.type = 'form_card'
              messageObj.schema = data.schema
              messageObj.form_id = data.form_id
              console.log('[SSE Staff] 追加表单卡片消息，form_id=', data.form_id)
            } else {
              console.log('[SSE Staff] 追加普通文本消息')
            }

            setChatMessages(prev => [...prev, messageObj])
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
        const userId = currentUser?.employee_id || currentUser?.user_id
        if (userId) {
          const newSource = new EventSource(`${SSE_BASE}/events/${userId}`)
          console.log('[SSE Staff] 重新连接成功')
        }
      }, 3000)
    }

    return () => {
      eventSource.close()
      console.log('[SSE Staff] 断开连接')
    }
  }, [currentUser?.employee_id, currentUser?.user_id])

  const initConversation = async (specificTaskId = null) => {
    const userId = currentUser?.employee_id || currentUser?.user_id
    try {
      // 获取当前用户的任务列表（强制刷新，加时间戳避免缓存）
      const response = await fetch(`${API_BASE}/tasks?employee_id=${userId}&_t=${Date.now()}`)
      const tasks = await response.json()
      setTasks(tasks)
      tasksRef.current = tasks  // 同步更新 ref

      let targetTask = null

      // 如果指定了任务ID，直接使用该任务（优先精确匹配）
      if (specificTaskId) {
        targetTask = tasks.find(t => t.task_id === specificTaskId)
        console.log('[Staff] 查找指定任务:', specificTaskId, '结果:', targetTask ? '找到' : '未找到')
      }

      // 否则找最新的待处理任务
      if (!targetTask) {
        targetTask = tasks.find(t => t.status !== '已完成') || tasks[0]
      }

      console.log('[Staff] 最终选中任务:', targetTask?.task_id)

      // 获取所有任务的历史对话，按时间顺序合并显示
      const allMessages = []
      for (const task of tasks) {
        try {
          const historyRes = await fetch(`${API_BASE}/tasks/${task.task_id}/chat-history?employee_id=${userId}`)
          const historyData = await historyRes.json()
          if (Array.isArray(historyData) && historyData.length > 0) {
            // Fix 12: 确保历史消息完整恢复 type、schema、form_id 字段，与 SSE 新消息字段保持一致
            const msgs = historyData.map(msg => ({
              sender: msg.sender === 'Agent' ? 'agent' : 'user',
              message: msg.message,
              timestamp: msg.timestamp,
              type: msg.message_type === 'form_card' ? 'form_card' : 'text',  // 统一为 type 字段
              schema: msg.schema,  // 恢复表单 schema
              form_id: msg.form_id,  // 恢复表单 ID
              files: msg.files,
              taskId: task.task_id  // 标记消息所属任务
            }))
            allMessages.push(...msgs)
          }
        } catch (e) {
          console.error('[Staff] 获取任务历史失败:', task.task_id, e)
        }
      }

      // 按时间排序
      allMessages.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))

      // 确保 targetTask 存在且有效
      if (!targetTask || !targetTask.task_id) {
        console.error('[Staff] 没有找到有效任务，无法初始化对话')
        setLoading(prev => ({ ...prev, init: false }))
        return
      }

      setSelectedTask(targetTask)

      // 如果没有历史对话，发送初始消息让智能体推送任务
      if (allMessages.length === 0) {
          const initResponse = await fetch(`${API_BASE}/tasks/${targetTask.task_id}/message`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              message: "你好，请告诉我当前有什么任务需要处理",
              employee_id: userId,
              username: currentUser.username
            })
          })
          const initData = await initResponse.json()
          if (initData.agent_reply) {
            // Fix 5: Preserve type, schema, form_id from initData
            setChatMessages([{
              sender: 'agent',
              type: initData.agent_reply.type,
              message: initData.agent_reply.message,
              schema: initData.agent_reply.schema,
              form_id: initData.agent_reply.form_id,
              timestamp: initData.agent_reply.timestamp
            }])
          }
      } else {
        setChatMessages(allMessages)
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
    const userId = currentUser?.employee_id || currentUser?.user_id
    setInputMessage('')
    setPendingFiles([])
    setLoading(prev => ({ ...prev, chat: true }))

    try {
      // 构建 FormData 发送消息和文件
      const formData = new FormData()
      formData.append('message', messageToSend)
      formData.append('employee_id', userId)
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
      // Fix 6: Preserve type, schema, form_id from agent_reply
      if (data.agent_reply) {
        setChatMessages(prev => [...prev, {
          sender: 'agent',
          type: data.agent_reply.type,
          message: data.agent_reply.message,
          schema: data.agent_reply.schema,
          form_id: data.agent_reply.form_id,
          timestamp: data.agent_reply.timestamp
        }])
      }
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

  // Fix 16: 处理表单提交
  const handleFormSubmit = async (formId, schema, formData) => {
    if (!selectedTask) {
      alert('暂无任务，请先获取任务')
      return
    }

    const userId = currentUser?.employee_id || currentUser?.user_id
    setLoading(prev => ({ ...prev, chat: true }))

    try {
      console.log('[Staff] 提交表单:', { formId, formData })

      // Fix 17: 使用FormData而不是JSON.stringify，以支持文件上传
      const requestFormData = new FormData()
      requestFormData.append('form_id', formId)
      requestFormData.append('employee_id', userId)
      requestFormData.append('username', currentUser.username)
      requestFormData.append('task_id', selectedTask.task_id)

      // 遍历formData中的所有字段
      Object.entries(formData).forEach(([key, value]) => {
        if (value instanceof File) {
          // File对象直接append
          requestFormData.append(`data_${key}`, value)
          console.log(`[Staff] 附加文件: ${key} = ${value.name}`)
        } else if (Array.isArray(value)) {
          // 数组处理（多个文件或多选）
          value.forEach((item, index) => {
            if (item instanceof File) {
              requestFormData.append(`data_${key}_${index}`, item)
            } else {
              requestFormData.append(`data_${key}_${index}`, String(item))
            }
          })
        } else {
          // 普通字段
          requestFormData.append(`data_${key}`, String(value || ''))
        }
      })

      // 调用后端表单提交API
      const response = await fetch(`${API_BASE}/form/submit`, {
        method: 'POST',
        body: requestFormData  // 使用FormData而不是JSON
      })

      const result = await response.json()
      console.log('[Staff] 表单提交结果:', result)

      if (result.success) {
        // Fix 19: 表单提交成功后，标记为已提交（禁止编辑），并清除编辑状态
        setSubmittedForms(prev => ({ ...prev, [formId]: true }))
        setEditingForms(prev => {
          const newState = { ...prev }
          delete newState[formId]
          return newState
        })

        // 添加用户提交的表单数据到对话（作为用户消息）
        const dataDisplay = Object.entries(formData)
          .map(([k, v]) => {
            if (v instanceof File) return `- ${k}: ${v.name} (文件)`
            if (Array.isArray(v)) return `- ${k}: [${v.length}项]`
            return `- ${k}: ${v}`
          })
          .join('\n')

        const submissionMessage = {
          sender: 'user',
          message: `提交表单数据:\n${dataDisplay}`,
          timestamp: new Date().toLocaleString(),
          formData: formData,
          form_id: formId
        }
        setChatMessages(prev => [...prev, submissionMessage])

        // 如果有Agent回复，也添加到对话
        if (result.agent_reply) {
          const agentMessage = {
            sender: 'agent',
            message: result.agent_reply,
            type: 'text',
            timestamp: new Date().toLocaleString(),
            form_id: formId
          }
          setChatMessages(prev => [...prev, agentMessage])
        }

        alert('表单提交成功！')
      } else {
        // 处理验证失败或其他错误
        if (result.errors) {
          const errorMsg = Object.entries(result.errors)
            .map(([field, error]) => `${field}: ${error}`)
            .join('\n')
          alert(`表单验证失败:\n${errorMsg}`)
        } else {
          alert(`表单提交失败: ${result.error || result.message}`)
        }
      }
    } catch (err) {
      console.error('[ERROR] 表单提交失败:', err)
      alert(`表单提交失败: ${err.message}`)
    } finally {
      setLoading(prev => ({ ...prev, chat: false }))
    }
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
          {chatMessages.length === 0 && !loading.chat && (
            <div className="welcome-message">
              <p>👋 您好！欢迎使用风控核查助手</p>
              {selectedTask ? (
                <p>智能体正在准备任务信息...</p>
              ) : (
                <p>暂无任务，等待管理员下发...</p>
              )}
            </div>
          )}
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
                    <>
                      {/* Fix 11A: 同时显示文本和表单 - 先显示文本描述 */}
                      {msg.message && (
                        <div className="message-text">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.message}</ReactMarkdown>
                        </div>
                      )}
                      {/* 再显示表单卡片 */}
                      {msg.type === 'form_card' && msg.schema ? (
                        <FormCardBubble
                          schema={{
                            ...msg.schema,
                            // Fix 19: 根据表单状态设置 schema.state 和 actions
                            state: editingForms[msg.form_id] ? 'editable' : (submittedForms[msg.form_id] ? 'readonly' : 'editable'),
                            actions: {
                              // 初始状态（未提交）：只显示提交
                              // 编辑中（修改已提交的表单）：显示取消和确认
                              // readonly（已提交）：只显示修改
                              showSubmit: !submittedForms[msg.form_id] || editingForms[msg.form_id],
                              showCancel: editingForms[msg.form_id],
                              showModify: submittedForms[msg.form_id] && !editingForms[msg.form_id],
                              submitText: editingForms[msg.form_id] ? '确认' : '提交',
                              cancelText: '取消',
                              modifyText: '修改'
                            }
                          }}
                          onSubmit={(formData) => {
                            console.log('Form submitted:', msg.form_id, formData)
                            // Fix 16: 实现表单提交API调用
                            handleFormSubmit(msg.form_id, msg.schema, formData)
                          }}
                          onCancel={() => {
                            console.log('Form cancelled:', msg.form_id)
                            // Fix 19: 取消编辑，回到 readonly 状态
                            setEditingForms(prev => {
                              const newState = { ...prev }
                              delete newState[msg.form_id]
                              return newState
                            })
                          }}
                          onModify={() => {
                            console.log('Form modify:', msg.form_id)
                            // Fix 19: 进入编辑模式
                            setEditingForms(prev => ({ ...prev, [msg.form_id]: true }))
                          }}
                        />
                      ) : null}
                    </>
                  )}
                </div>
                <div className="message-time">
                  {new Date(msg.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
            )
          })}
          {loading.chat && (
            <ChatMessage
              message={{
                type: 'text',
                sender: 'agent',
                content: '正在思考...',
                timestamp: new Date().toISOString()
              }}
            />
          )}
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
      // 优先用 employee_id 匹配，否则用 user_id 匹配
      const user = users.find(u => (u.employee_id || u.user_id) === userId) || users.find(u => u.user_id === userId)
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
          {/* 搜索框 */}
          <div className="header-search">
            <input
              type="text"
              placeholder="🔍 搜索..."
              className="search-input"
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  // Handle search
                }
              }}
            />
          </div>

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
