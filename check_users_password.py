"""
检查数据库用户信息
"""
import sqlite3
import os
import json
from pathlib import Path

db_path = os.path.join(os.path.dirname(__file__), 'data', 'app.db')
print("="*70)
print("检查数据库用户信息")
print("="*70)
print(f"\n数据库路径: {db_path}")

# 检查数据库文件是否存在
if not os.path.exists(db_path):
    print(f"\n❌ 数据库文件不存在！")
    exit(1)

print("\n✅ 数据库文件存在！")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 查看users表结构
print("\n[1/3] 查看users表结构...")
cursor.execute("PRAGMA table_info(users)")
columns = cursor.fetchall()
print("\n表结构:")
for col in columns:
    print(f"  {col[1]} ({col[2]})")

# 查看所有用户
print("\n[2/3] 查看所有用户...")
cursor.execute("SELECT * FROM users")
users = cursor.fetchall()

print(f"\n找到 {len(users)} 个用户:")
print("-"*70)
for i, user in enumerate(users, 1):
    print(f"\n用户 #{i}")
    print(f"  ID: {user[0]}")
    print(f"  用户名: {user[1]}")
    print(f"  密码hash: {user[2][:30]}...")
    print(f"  角色: {user[3]}")
    print(f"  创建时间: {user[4]}")
    print(f"  激活: {'是' if user[5] else '否'}")
    print(f"  状态: {user[6]}")

# 查看初始密码文件
print("\n[3/3] 检查初始密码文件...")
pwd_file = os.path.join(os.path.dirname(__file__), '.initial_passwords')
if os.path.exists(pwd_file):
    print(f"\n✅ 初始密码文件存在！")
    with open(pwd_file, 'r', encoding='utf-8') as f:
        print("\n初始密码:")
        for line in f:
            if line.strip():
                print(f"  {line.strip()}")
else:
    print(f"\n⚠️ 初始密码文件不存在！")

conn.close()
print("\n" + "="*70)
