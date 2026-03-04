from flask import Flask, request, jsonify
from flask_cors import CORS
import csv
import json
import os
from datetime import datetime
import logging
import asyncio

# 导入智能体模块
from agents import (
    get_or_create_staff_agent,
    get_or_create_manager_agent,
    close_agent,
    close_all_agents,
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

def read_csv_file(filename):
    """读取CSV文件"""
    filepath = os.path.join(DATA_DIR, filename)
    logger.info(f"[READ] 读取文件: {filepath}")
    if not os.path.exists(filepath):
        logger.warning(f"[WARN] 文件不存在: {filepath}")
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            data = list(reader)
            logger.info(f"[SUCCESS] 读取 {filename} 成功, 共 {len(data)} 条记录")
            return data
    except Exception as e:
        logger.error(f"[ERROR] 读取文件失败 {filename}: {str(e)}")
        return []

def write_csv_file(filename, data, fieldnames):
    """写入CSV文件"""
    filepath = os.path.join(DATA_DIR, filename)
    logger.info(f"[WRITE] 写入文件: {filepath}, 记录数: {len(data)}")
    try:
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        logger.info(f"[SUCCESS] 写入 {filename} 成功")
        return True
    except Exception as e:
        logger.error(f"[ERROR] 写入文件失败 {filename}: {str(e)}")
        return False

@app.route('/api/users', methods=['GET'])
def get_users():
    """获取用户列表"""
    logger.info("[API] GET /api/users - 获取用户列表")
    users = read_csv_file('users.csv')
    logger.info(f"[API] 返回用户数: {len(users)}")
    return jsonify(users)

@app.route('/api/users/<user_id>', methods=['GET'])
def get_user(user_id):
    """获取单个用户"""
    logger.info(f"[API] GET /api/users/{user_id} - 获取用户")
    users = read_csv_file('users.csv')
    user = next((u for u in users if u['user_id'] == user_id), None)
    if user:
        logger.info(f"[API] 找到用户: {user.get('username')}")
        return jsonify(user)
    logger.warning(f"[API] 用户不存在: {user_id}")
    return jsonify({'error': 'User not found'}), 404

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """获取任务列表（支持user_id过滤）"""
    logger.info("[API] GET /api/tasks - 获取任务列表")
    user_id = request.args.get('user_id')
    tasks = read_csv_file('tasks.csv')
    
    # 如果提供了user_id，根据角色过滤
    if user_id:
        users = read_csv_file('users.csv')
        user = next((u for u in users if u['user_id'] == user_id), None)
        if user:
            role = user.get('role', '')
            if role == '业务负责人' or role == '普通分析人员':
                # 业务负责人看到自己创建的任务
                tasks = [t for t in tasks if t['creator_id'] == user_id]
            else:
                # 一线人员看到分配给自己的任务
                tasks = [t for t in tasks if t['assigned_to_id'] == user_id]
    
    logger.info(f"[API] 返回任务数: {len(tasks)}")
    return jsonify(tasks)

@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """获取单个任务"""
    logger.info(f"[API] GET /api/tasks/{task_id} - 获取任务")
    tasks = read_csv_file('tasks.csv')
    task = next((t for t in tasks if t['task_id'] == task_id), None)
    if task:
        logger.info(f"[API] 找到任务: {task.get('risk_summary')}")
        return jsonify(task)
    logger.warning(f"[API] 任务不存在: {task_id}")
    return jsonify({'error': 'Task not found'}), 404

@app.route('/api/tasks', methods=['POST'])
def create_task():
    """创建新任务"""
    logger.info("[API] POST /api/tasks - 创建新任务")
    data = request.json
    logger.info(f"[API] 请求数据: {data}")
    
    tasks = read_csv_file('tasks.csv')
    
    # 生成新任务ID
    max_id = max([int(t['task_id'].replace('TASK_', '')) for t in tasks], default=0)
    new_task_id = f"TASK_{max_id + 1:03d}"
    logger.info(f"[API] 新任务ID: {new_task_id}")
    
    new_task = {
        'task_id': new_task_id,
        'creator_id': data.get('creator_id'),
        'creator_name': data.get('creator_name'),
        'assigned_to_id': data.get('assigned_to_id'),
        'assigned_to_name': data.get('assigned_to_name'),
        'status': '已创建',
        'created_time': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'risk_summary': data.get('risk_summary'),
        'risk_data_url': data.get('risk_data_url'),
        'suggested_receiver_id': data.get('assigned_to_id'),
        'confirmed_receiver_id': data.get('assigned_to_id'),
        'completed_time': ''
    }
    
    tasks.append(new_task)
    fieldnames = ['task_id', 'creator_id', 'creator_name', 'assigned_to_id', 'assigned_to_name', 
                  'status', 'created_time', 'risk_summary', 'risk_data_url', 
                  'suggested_receiver_id', 'confirmed_receiver_id', 'completed_time']
    
    if write_csv_file('tasks.csv', tasks, fieldnames):
        logger.info(f"[API] 任务创建成功: {new_task_id}")
        return jsonify(new_task), 201
    else:
        logger.error("[API] 任务创建失败")
        return jsonify({'error': 'Failed to create task'}), 500

@app.route('/api/tasks/<task_id>/status', methods=['PUT'])
def update_task_status(task_id):
    """更新任务状态"""
    logger.info(f"[API] PUT /api/tasks/{task_id}/status - 更新任务状态")
    data = request.json
    logger.info(f"[API] 新状态: {data}")
    
    tasks = read_csv_file('tasks.csv')
    
    task = next((t for t in tasks if t['task_id'] == task_id), None)
    if not task:
        logger.warning(f"[API] 任务不存在: {task_id}")
        return jsonify({'error': 'Task not found'}), 404
    
    task['status'] = data.get('status', task['status'])
    if data.get('status') == '反馈完成':
        task['completed_time'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        logger.info(f"[API] 任务完成时间: {task['completed_time']}")
    
    fieldnames = ['task_id', 'creator_id', 'creator_name', 'assigned_to_id', 'assigned_to_name', 
                  'status', 'created_time', 'risk_summary', 'risk_data_url', 
                  'suggested_receiver_id', 'confirmed_receiver_id', 'completed_time']
    
    if write_csv_file('tasks.csv', tasks, fieldnames):
        logger.info(f"[API] 任务状态更新成功: {task_id} -> {task['status']}")
        return jsonify(task)
    else:
        logger.error(f"[API] 任务状态更新失败: {task_id}")
        return jsonify({'error': 'Failed to update task'}), 500

@app.route('/api/feedback/<task_id>', methods=['GET'])
def get_feedback(task_id):
    """获取任务反馈"""
    logger.info(f"[API] GET /api/feedback/{task_id} - 获取反馈")
    feedback_path = os.path.join(DATA_DIR, 'feedback', f'{task_id}.json')
    
    if not os.path.exists(feedback_path):
        logger.warning(f"[API] 反馈文件不存在: {task_id}")
        return jsonify({'error': 'Feedback not found'}), 404
    
    try:
        with open(feedback_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"[API] 读取反馈成功: {task_id}")
            return jsonify(data)
    except Exception as e:
        logger.error(f"[API] 读取反馈失败 {task_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/risk-data/<filename>', methods=['GET'])
def get_risk_data(filename):
    """获取风险数据"""
    logger.info(f"[API] GET /api/risk-data/{filename} - 获取风险数据")
    risk_data = read_csv_file(f'risk_data_{filename}.csv')
    logger.info(f"[API] 返回风险数据: {len(risk_data)} 条")
    return jsonify(risk_data)

@app.route('/api/chat', methods=['POST'])
def chat():
    """AI对话接口（主Agent - 业务负责人使用）"""
    logger.info("[API] POST /api/chat - AI对话")
    data = request.json
    message = data.get('message', '')
    user_id = data.get('user_id', 'manager_default')
    username = data.get('username', '业务负责人')
    
    logger.info(f"[API] 用户消息: {message}")
    
    # 调用 ManagerAgent 获取真实回复
    try:
        # 获取 ManagerAgent（会话复用）
        agent = get_or_create_manager_agent(user_id, username)
        
        # 调用 Agent.chat() 获取回复（异步）
        async def get_agent_response():
            return await agent.chat(message)
        
        response_text = asyncio.run(get_agent_response())
        
        logger.info(f"[API] ManagerAgent 回复成功")
        
    except Exception as e:
        logger.error(f"[ERROR] ManagerAgent 调用失败: {str(e)}")
        # 降级使用规则回复
        response_text = get_ai_response(message)
    
    response = {
        'message': response_text,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    logger.info(f"[API] AI回复: {response_text[:50]}...")
    
    return jsonify(response)

def get_ai_response(message):
    """根据用户消息返回AI回复"""
    message = message.lower()
    
    if any(kw in message for kw in ['分析', '风险', '数据']):
        return "我可以从风险数据中分析潜在的风险模式，包括异常交易、超时派送、虚假签收等问题。请问您想分析哪方面的风险？"
    elif any(kw in message for kw in ['任务', '创建', '新建']):
        return "您可以点击右上角的'+ 新建任务'按钮来创建新的风险核查任务。需要指定风险简述、执行人和风险数据。"
    elif any(kw in message for kw in ['状态', '进度', '查看']):
        return "您可以在左侧的任务列表中查看所有任务的状态。任务状态包括：已创建、已下发、反馈完成、已超期。"
    elif any(kw in message for kw in ['帮助', '功能']):
        return "我可以帮您：\n1. 分析风险数据\n2. 创建和下发任务\n3. 查看任务状态和反馈\n4. 提供风险管控建议"
    else:
        return f"收到您的消息：{message}。我是风控助手，可以帮助您分析风险数据、创建任务、查看状态等。请问有什么可以帮您？"

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    logger.info("[API] GET /api/health - 健康检查")
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'data_dir': DATA_DIR
    })

# === 补充的API ===

@app.route('/api/tasks/<task_id>/chat-history', methods=['GET'])
def get_chat_history(task_id):
    """获取任务的对话历史"""
    logger.info(f"[API] GET /api/tasks/{task_id}/chat-history")
    
    # 获取用户信息
    user_id = request.args.get('user_id')
    username = request.args.get('username', '一线人员')
    
    # 先检查是否有已保存的对话历史
    feedback_path = os.path.join(DATA_DIR, 'feedback', f'{task_id}.json')
    
    if os.path.exists(feedback_path):
        try:
            with open(feedback_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                existing_history = data.get('chat_history', [])
                # 如果有历史对话，直接返回
                if existing_history:
                    return jsonify(existing_history)
        except Exception as e:
            logger.error(f"[ERROR] 读取对话历史失败: {str(e)}")
    
    # 如果没有对话历史，调用 Agent.init_task() 生成初始消息
    try:
        # 获取 StaffAgent
        agent = get_or_create_staff_agent(user_id, username)
        
        # 调用 Agent 初始化任务（异步）
        async def init_and_get_message():
            return await agent.init_task(task_id)
        
        initial_agent_message = asyncio.run(init_and_get_message())
        
        # 保存初始消息到反馈文件
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        initial_message = {
            'timestamp': timestamp,
            'sender': 'Agent',
            'message': initial_agent_message,
            'message_type': 'text'
        }
        
        # 保存到反馈文件
        os.makedirs(os.path.dirname(feedback_path), exist_ok=True)
        feedback_data = {
            'task_id': task_id,
            'chat_history': [initial_message],
            'uploaded_files': [],
            'status': '进行中'
        }
        with open(feedback_path, 'w', encoding='utf-8') as f:
            json.dump(feedback_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"[API] Agent 初始化任务成功: {task_id}")
        return jsonify([initial_message])
        
    except Exception as e:
        logger.error(f"[ERROR] Agent 初始化任务失败: {str(e)}")
        # 降级返回固定消息
        tasks = read_csv_file('tasks.csv')
        task = next((t for t in tasks if t['task_id'] == task_id), None)
        if task:
            initial_message = {
                'timestamp': task['created_time'],
                'sender': 'Agent',
                'message': f'您好！您有新任务需要核查。\n\n风险简述：{task.get("risk_summary", "")}\n风险数据：{task.get("risk_data_url", "")}\n\n请根据风险数据进行核查，并在完成后上传相关证明文件。',
                'message_type': 'text'
            }
            return jsonify([initial_message])
    
    return jsonify({'chat_history': []})

@app.route('/api/tasks/<task_id>/creation-history', methods=['GET'])
def get_creation_history(task_id):
    """获取任务创建对话历史（Web端业务负责人使用）"""
    logger.info(f"[API] GET /api/tasks/{task_id}/creation-history")
    creation_path = os.path.join(DATA_DIR, 'task_creation', f'{task_id}.json')
    
    if os.path.exists(creation_path):
        try:
            with open(creation_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return jsonify(data.get('creation_history', []))
        except Exception as e:
            logger.error(f"[ERROR] 读取任务创建对话失败: {str(e)}")
            return jsonify({'creation_history': []})
    
    # 如果没有创建对话文件，返回默认消息
    return jsonify([
        {
            'timestamp': '',
            'sender': 'Agent',
            'message': '暂无任务创建对话记录',
            'message_type': 'text'
        }
    ])

@app.route('/api/tasks/<task_id>/message', methods=['POST'])
def send_message(task_id):
    """一线人员发送消息，获取AI回复"""
    logger.info(f"[API] POST /api/tasks/{task_id}/message")
    data = request.json
    message = data.get('message', '')
    user_id = data.get('user_id')
    username = data.get('username', '')
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 用户消息
    user_message = {
        'timestamp': timestamp,
        'sender': username,
        'message': message,
        'message_type': 'text'
    }
    
    # 调用 Agent 获取真实回复
    try:
        # 获取 StaffAgent（会话复用）
        agent = get_or_create_staff_agent(user_id, username)
        
        # 设置当前任务
        agent.current_task_id = task_id
        
        # 调用 Agent.chat() 获取回复（异步）
        async def get_agent_response():
            return await agent.chat(message)
        
        ai_response = asyncio.run(get_agent_response())
        
        logger.info(f"[API] Agent 回复成功: {task_id}")
        
    except Exception as e:
        logger.error(f"[ERROR] Agent 调用失败: {str(e)}")
        # 降级使用规则回复
        ai_response = get_staff_ai_response(message, task_id)
    
    agent_reply = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'sender': 'Agent',
        'message': ai_response,
        'message_type': 'text'
    }
    
    # 保存到反馈文件
    save_chat_message(task_id, user_message, user_id)
    save_chat_message(task_id, agent_reply, user_id)
    
    return jsonify({
        'user_message': user_message,
        'agent_reply': agent_reply
    })

def save_chat_message(task_id, message, user_id):
    """保存对话消息到反馈文件"""
    feedback_dir = os.path.join(DATA_DIR, 'feedback')
    os.makedirs(feedback_dir, exist_ok=True)
    feedback_path = os.path.join(feedback_dir, f'{task_id}.json')
    
    if os.path.exists(feedback_path):
        with open(feedback_path, 'r', encoding='utf-8') as f:
            feedback = json.load(f)
    else:
        feedback = {
            'task_id': task_id,
            'chat_history': [],
            'uploaded_files': [],
            'status': '进行中'
        }
    
    feedback['chat_history'].append(message)
    
    with open(feedback_path, 'w', encoding='utf-8') as f:
        json.dump(feedback, f, ensure_ascii=False, indent=2)

def get_staff_ai_response(message, task_id):
    """一线人员AI回复"""
    message = message.lower()
    
    if any(kw in message for kw in ['上传', '文件', '证明']):
        return "好的，请上传核查相关的证明文件。您可以点击输入框旁的📎按钮上传文件，支持PDF、图片等格式。"
    elif any(kw in message for kw in ['完成', '提交', '确认']):
        return "感谢您的核查工作！请点击上方的'确认完成'按钮完成此任务。"
    elif any(kw in message for kw in ['查看', '数据', '风险']):
        tasks = read_csv_file('tasks.csv')
        task = next((t for t in tasks if t['task_id'] == task_id), None)
        if task:
            risk_data_url = task.get('risk_data_url', '')
            if risk_data_url:
                filename = risk_data_url.replace('data/risk_data_', '').replace('.csv', '')
                risk_data = read_csv_file(f'risk_data_{filename}.csv')
                if risk_data:
                    info = risk_data[0]
                    return f"风险数据信息：\n" + "\n".join([f"{k}: {v}" for k, v in list(info.items())[:5]])
        return "您可以查看任务详情中的风险数据。"
    else:
        return f"收到您的消息：{message}。我会记录您的反馈。请继续完成核查工作，上传相关证明文件后点击'确认完成'。"

@app.route('/api/tasks/<task_id>/upload-file', methods=['POST'])
def upload_file(task_id):
    """上传文件"""
    logger.info(f"[API] POST /api/tasks/{task_id}/upload-file")
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    user_id = request.form.get('user_id')
    filename = request.form.get('filename', file.filename)
    
    # 创建上传目录
    upload_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads', task_id, user_id)
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)
    
    file_size = os.path.getsize(file_path)
    upload_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 保存到反馈文件
    feedback_dir = os.path.join(DATA_DIR, 'feedback')
    feedback_path = os.path.join(feedback_dir, f'{task_id}.json')
    
    if os.path.exists(feedback_path):
        with open(feedback_path, 'r', encoding='utf-8') as f:
            feedback = json.load(f)
    else:
        feedback = {
            'task_id': task_id,
            'chat_history': [],
            'uploaded_files': [],
            'status': '进行中'
        }
    
    feedback['uploaded_files'].append({
        'filename': filename,
        'upload_time': upload_time,
        'file_path': f'uploads/{task_id}/{user_id}/{filename}',
        'file_size': file_size
    })
    
    with open(feedback_path, 'w', encoding='utf-8') as f:
        json.dump(feedback, f, ensure_ascii=False, indent=2)
    
    logger.info(f"[API] 文件上传成功: {filename}")
    
    return jsonify({
        'message': f'文件 {filename} 上传成功！正在进行验证...',
        'verification_status': '验证中',
        'filename': filename,
        'file_path': f'uploads/{task_id}/{user_id}/{filename}',
        'upload_time': upload_time,
        'file_size': file_size
    })

@app.route('/api/tasks/<task_id>/complete', methods=['POST'])
def complete_task(task_id):
    """完成任务"""
    logger.info(f"[API] POST /api/tasks/{task_id}/complete")
    data = request.json
    user_id = data.get('user_id')
    
    # 生成反馈总结
    feedback_path = os.path.join(DATA_DIR, 'feedback', f'{task_id}.json')
    feedback_summary = "任务已完成核查。"
    
    if os.path.exists(feedback_path):
        with open(feedback_path, 'r', encoding='utf-8') as f:
            feedback = json.load(f)
            files = feedback.get('uploaded_files', [])
            if files:
                file_names = [f['filename'] for f in files]
                feedback_summary += f"已上传文件：{', '.join(file_names)}。"
    
    # 更新任务状态
    tasks = read_csv_file('tasks.csv')
    task = next((t for t in tasks if t['task_id'] == task_id), None)
    if task:
        task['status'] = '反馈完成'
        task['completed_time'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        fieldnames = ['task_id', 'creator_id', 'creator_name', 'assigned_to_id', 'assigned_to_name', 
                      'status', 'created_time', 'risk_summary', 'risk_data_url', 
                      'suggested_receiver_id', 'confirmed_receiver_id', 'completed_time']
        write_csv_file('tasks.csv', tasks, fieldnames)
        
        # 更新反馈文件
        if os.path.exists(feedback_path):
            with open(feedback_path, 'r', encoding='utf-8') as f:
                feedback = json.load(f)
        else:
            feedback = {'task_id': task_id, 'chat_history': [], 'uploaded_files': []}
        
        feedback['feedback_summary'] = feedback_summary
        feedback['summary_timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        feedback['status'] = 'completed'
        
        with open(feedback_path, 'w', encoding='utf-8') as f:
            json.dump(feedback, f, ensure_ascii=False, indent=2)
    
    return jsonify({
        'task_id': task_id,
        'status': '反馈完成',
        'feedback_summary': feedback_summary,
        'summary_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

if __name__ == '__main__':
    import atexit
    
    # 注册服务关闭时的清理函数
    def cleanup():
        logger.info("正在关闭服务，清理Agent会话...")
        close_all_agents()
        logger.info("服务已关闭")
    
    atexit.register(cleanup)
    
    logger.info("=" * 50)
    logger.info("风控Agent助手后端服务启动")
    logger.info(f"数据目录: {DATA_DIR}")
    logger.info("=" * 50)
    app.run(debug=True, port=5005)
