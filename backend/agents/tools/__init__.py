"""
工具层 - 原子化能力
导出所有工具供Agent和Skill使用
"""

from .file_parser import (
    parse_csv,
    parse_excel,
    parse_pdf,
    parse_word,
    parse_image,
    parse_file,
    set_data_dir as set_file_parser_data_dir,
    get_data_dir as get_file_parser_data_dir
)

from .data_access import (
    read_risk_data,
    list_risk_data_files,
    list_users,
    get_user,
    get_task,
    get_task_detail,
    query_tasks,
    set_data_dir as set_data_access_data_dir,
    get_data_dir as get_data_access_data_dir
)

from .task_manager import (
    create_task,
    update_task_status,
    assign_task,
    save_chat_message,
    set_data_dir as set_task_manager_data_dir,
    get_data_dir as get_task_manager_data_dir
)

from .file_ops import (
    save_uploaded_file,
    save_uploaded_file_from_path,
    read_file_content,
    list_uploaded_files,
    delete_file,
    set_data_dir as set_file_ops_data_dir,
    get_data_dir as get_file_ops_data_dir,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE
)

# 统一设置数据目录
def set_data_dir(data_dir):
    """设置所有工具的数据目录"""
    set_file_parser_data_dir(data_dir)
    set_data_access_data_dir(data_dir)
    set_task_manager_data_dir(data_dir)
    set_file_ops_data_dir(data_dir)


def get_data_dir():
    """获取数据目录"""
    return get_file_parser_data_dir()


# 所有工具字典 - 供Agent注册使用
ALL_TOOLS = {
    # 文件解析
    "parse_csv": parse_csv,
    "parse_excel": parse_excel,
    "parse_pdf": parse_pdf,
    "parse_word": parse_word,
    "parse_image": parse_image,
    "parse_file": parse_file,
    
    # 数据访问
    "read_risk_data": read_risk_data,
    "list_risk_data_files": list_risk_data_files,
    "list_users": list_users,
    "get_user": get_user,
    "get_task": get_task,
    "get_task_detail": get_task_detail,
    "query_tasks": query_tasks,
    
    # 任务管理
    "create_task": create_task,
    "update_task_status": update_task_status,
    "assign_task": assign_task,
    "save_chat_message": save_chat_message,
    
    # 文件操作
    "save_uploaded_file": save_uploaded_file,
    "save_uploaded_file_from_path": save_uploaded_file_from_path,
    "read_file_content": read_file_content,
    "list_uploaded_files": list_uploaded_files,
    "delete_file": delete_file,
}

__all__ = [
    # 工具函数
    'parse_csv',
    'parse_excel',
    'parse_pdf',
    'parse_word',
    'parse_image',
    'parse_file',
    'read_risk_data',
    'list_risk_data_files',
    'list_users',
    'get_user',
    'get_task',
    'get_task_detail',
    'query_tasks',
    'create_task',
    'update_task_status',
    'assign_task',
    'save_chat_message',
    'save_uploaded_file',
    'save_uploaded_file_from_path',
    'read_file_content',
    'list_uploaded_files',
    'delete_file',
    
    # 工具集
    'ALL_TOOLS',
    
    # 数据目录
    'set_data_dir',
    'get_data_dir',
    
    # 常量
    'ALLOWED_EXTENSIONS',
    'MAX_FILE_SIZE'
]
