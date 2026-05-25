import sys
sys.path.insert(0, '.')
import json
from unittest.mock import patch
from app.api.admin import router
from app.api.auth import hash_password

# 直接测试数据库
from app.models.database import get_database
db = get_database()
conn = db.get_connection()

# 查看用户数据
users = conn.execute("SELECT id, username, role, is_active, status FROM users").fetchall()
print("=== Users ===")
for user in users:
    print(f"  {dict(user)}")

# 查看日志数据
logs = conn.execute("SELECT * FROM logs LIMIT 3").fetchall()
print("\n=== Logs (sample) ===")
for log in logs:
    print(f"  {dict(log)}")

# 测试 list_users 方法
print("\n=== Testing db.list_users() ===")
result = db.list_users(page=1, page_size=20)
print(f"Result keys: {result.keys()}")
print(f"Users: {result['users']}")
print(f"Total: {result['total']}")

# 测试 get_logs 方法
print("\n=== Testing db.get_logs() ===")
result = db.get_logs(page=1, page_size=50)
print(f"Result keys: {result.keys()}")
print(f"Logs: {result['logs']}")
print(f"Total: {result['total']}")