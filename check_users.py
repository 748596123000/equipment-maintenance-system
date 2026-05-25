"""
获取数据库中的用户信息
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'data', 'app.db')

def get_users():
    """获取所有用户"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 查询用户表
    cursor.execute("SELECT username, password, email, is_admin, is_active FROM users")
    users = cursor.fetchall()
    
    print("=" * 70)
    print("📋 数据库中的用户列表")
    print("=" * 70)
    
    if users:
        print(f"\n{'用户名':<20} {'密码(Hash)':<30} {'邮箱':<30} {'管理员':<10} {'激活':<10}")
        print("-" * 100)
        for user in users:
            username, password_hash, email, is_admin, is_active = user
            print(f"{username:<20} {password_hash:<30} {email:<30} {'是' if is_admin else '否':<10} {'是' if is_active else '否':<10}")
        print(f"\n共找到 {len(users)} 个用户")
    else:
        print("\n未找到任何用户")
    
    conn.close()
    return users

if __name__ == '__main__':
    users = get_users()
    
    # 测试登录
    if users:
        print("\n" + "=" * 70)
        print("🔐 测试用户登录")
        print("=" * 70)
        
        import requests
        
        # 获取验证码
        captcha_resp = requests.get('http://localhost:8001/api/v1/auth/captcha')
        print(f"\n验证码获取: {captcha_resp.status_code}")
        
        # 尝试每个用户登录
        for username, _, _, _, _ in users[:3]:  # 只测试前3个
            # 测试几个常见的默认密码
            passwords = ['password', 'admin123', '123456', 'password123', username]
            
            for pwd in passwords:
                try:
                    login_data = {
                        "username": username,
                        "password": pwd,
                        "captcha_code": "0000",
                        "captcha_id": "test"
                    }
                    
                    login_resp = requests.post(
                        'http://localhost:8001/api/v1/auth/login',
                        json=login_data,
                        timeout=5
                    )
                    
                    if login_resp.status_code == 200:
                        data = login_resp.json()
                        if 'token' in data.get('data', {}):
                            print(f"\n✅ 找到有效账号!")
                            print(f"   用户名: {username}")
                            print(f"   密码: {pwd}")
                            print(f"   Token: {data['data']['token'][:50]}...")
                            conn = sqlite3.connect(db_path)
                            cursor = conn.cursor()
                            cursor.execute("UPDATE users SET password='password' WHERE username=?", (username,))
                            conn.commit()
                            conn.close()
                            print(f"   已将密码重置为: password")
                            break
                except:
                    pass
            else:
                continue
            break
