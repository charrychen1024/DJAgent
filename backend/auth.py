"""用户认证工具"""

import csv
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def validate_user(user_id: str) -> bool:
    """验证用户ID是否有效"""
    try:
        users_file = DATA_DIR / "users.csv"
        if not users_file.exists():
            return False

        with open(users_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("user_id") == user_id:
                    return True
        return False
    except Exception:
        return False


def get_user(user_id: str):
    """获取用户信息"""
    try:
        users_file = DATA_DIR / "users.csv"
        if not users_file.exists():
            return None

        with open(users_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("user_id") == user_id:
                    return row
        return None
    except Exception:
        return None
