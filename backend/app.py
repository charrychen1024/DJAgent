from flask import Flask, request, jsonify
from flask_cors import CORS
import csv
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

def read_csv_file(filename):
    """读取CSV文件"""
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

def write_csv_file(filename, data, fieldnames):
    """写入CSV文件"""
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

@app.route('/api/users', methods=['GET'])
def get_users():
    """获取用户列表"""
    users = read_csv_file('users.csv')
    return jsonify(users)

@app.route('/api/users/<user_id>', methods=['GET'])
def get_user(user_id):
    """获取单个用户"""
    users = read_csv_file('users.csv')
    user = next((u for u in users if u['user_id'] == user_id), None)
    if user:
        return jsonify(user)
    return jsonify({'error': 'User not found'}), 404

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """获取任务列表"""
    tasks = read_csv_file('tasks.csv')
    return jsonify(tasks)

@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """获取单个任务"""
    tasks = read_csv_file('tasks.csv')
    task = next((t for t in tasks if t['task_id'] == task_id), None)
    if task:
        return jsonify(task)
    return jsonify({'error': 'Task not found'}), 404

@app.route('/api/tasks', methods=['POST'])
def create_task():
    """创建新任务"""
    data = request.json
    tasks = read_csv_file('tasks.csv')
    
    # 生成新任务ID
    max_id = max([int(t['task_id'].replace('TASK_', '')) for t in tasks], default=0)
    new_task_id = f"TASK_{max_id + 1:03d}"
    
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
    write_csv_file('tasks.csv', tasks, fieldnames)
    
    return jsonify(new_task), 201

@app.route('/api/tasks/<task_id>/status', methods=['PUT'])
def update_task_status(task_id):
    """更新任务状态"""
    data = request.json
    tasks = read_csv_file('tasks.csv')
    
    task = next((t for t in tasks if t['task_id'] == task_id), None)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    task['status'] = data.get('status', task['status'])
    if data.get('status') == '反馈完成':
        task['completed_time'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    fieldnames = ['task_id', 'creator_id', 'creator_name', 'assigned_to_id', 'assigned_to_name', 
                  'status', 'created_time', 'risk_summary', 'risk_data_url', 
                  'suggested_receiver_id', 'confirmed_receiver_id', 'completed_time']
    write_csv_file('tasks.csv', tasks, fieldnames)
    
    return jsonify(task)

@app.route('/api/feedback/<task_id>', methods=['GET'])
def get_feedback(task_id):
    """获取任务反馈"""
    feedback_path = os.path.join(DATA_DIR, 'feedback', f'{task_id}.json')
    if not os.path.exists(feedback_path):
        return jsonify({'error': 'Feedback not found'}), 404
    
    with open(feedback_path, 'r', encoding='utf-8') as f:
        return jsonify(json.load(f))

@app.route('/api/risk-data/<filename>', methods=['GET'])
def get_risk_data(filename):
    """获取风险数据"""
    risk_data = read_csv_file(f'risk_data_{filename}.csv')
    return jsonify(risk_data)

@app.route('/api/chat', methods=['POST'])
def chat():
    """AI对话接口（简化版）"""
    data = request.json
    message = data.get('message', '')
    
    # 这里应该调用Claude Code SDK，简化版返回固定回复
    response = {
        'message': f'收到您的消息：{message}。我是风控助手，可以帮助您分析风险数据、创建任务等。',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
