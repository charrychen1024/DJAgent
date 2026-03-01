from flask import Flask, request, jsonify
from flask_cors import CORS
import csv
import json
import os
from datetime import datetime
import logging

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
    """获取任务列表"""
    logger.info("[API] GET /api/tasks - 获取任务列表")
    tasks = read_csv_file('tasks.csv')
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
    """AI对话接口（简化版）"""
    logger.info("[API] POST /api/chat - AI对话")
    data = request.json
    message = data.get('message', '')
    logger.info(f"[API] 用户消息: {message}")
    
    # 这里应该调用Claude Code SDK，简化版返回固定回复
    # 根据消息内容返回不同回复
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

if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("风控Agent助手后端服务启动")
    logger.info(f"数据目录: {DATA_DIR}")
    logger.info("=" * 50)
    app.run(debug=True, port=5000)
