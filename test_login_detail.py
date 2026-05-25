"""
详细登录测试脚本
"""
import requests
import json

def test_login():
    """详细测试登录"""
    base_url = 'http://localhost:8001'
    
    print("=" * 70)
    print("🔐 详细登录测试")
    print("=" * 70)
    
    # 1. 获取验证码
    print("\n1️⃣ 获取验证码...")
    try:
        captcha_resp = requests.get(f'{base_url}/api/v1/auth/captcha')
        print(f"   状态码: {captcha_resp.status_code}")
        print(f"   响应: {captcha_resp.json()}")
        
        if captcha_resp.status_code == 200:
            captcha_data = captcha_resp.json()
            captcha_id = captcha_data.get('data', {}).get('captcha_id', 'test_captcha')
            print(f"   ✅ 验证码ID: {captcha_id}")
        else:
            print("   ❌ 验证码获取失败")
            captcha_id = 'test_captcha'
    except Exception as e:
        print(f"   ❌ 异常: {e}")
        captcha_id = 'test_captcha'
    
    # 2. 尝试登录
    print("\n2️⃣ 尝试登录...")
    
    login_data = {
        "username": "admin",
        "password": "DCHsyHXaFwAdv9Ur",
        "captcha_code": "0000",
        "captcha_id": captcha_id
    }
    
    print(f"   登录数据: {json.dumps(login_data, ensure_ascii=False)}")
    
    try:
        login_resp = requests.post(
            f'{base_url}/api/v1/auth/login',
            json=login_data,
            timeout=5
        )
        
        print(f"   状态码: {login_resp.status_code}")
        print(f"   响应: {login_resp.text[:500]}")
        
        if login_resp.status_code == 200:
            data = login_resp.json()
            if 'data' in data and 'token' in data['data']:
                token = data['data']['token']
                print(f"   ✅ 登录成功!")
                print(f"   Token: {token[:50]}...")
                
                # 3. 测试使用Token
                print("\n3️⃣ 使用Token测试API...")
                
                headers = {'Authorization': f'Bearer {token}'}
                
                # 测试用户信息
                me_resp = requests.get(
                    f'{base_url}/api/v1/auth/me',
                    headers=headers,
                    timeout=5
                )
                print(f"   /auth/me: {me_resp.status_code}")
                if me_resp.status_code == 200:
                    print(f"   ✅ 用户信息: {me_resp.json()}")
                
                # 测试系统统计
                stats_resp = requests.get(
                    f'{base_url}/api/v1/admin/stats',
                    headers=headers,
                    timeout=5
                )
                print(f"   /admin/stats: {stats_resp.status_code}")
                if stats_resp.status_code == 200:
                    print(f"   ✅ 系统统计: {stats_resp.json()}")
                
                # 测试知识检索
                search_resp = requests.post(
                    f'{base_url}/api/v1/search/text',
                    json={'query': '发动机', 'top_k': 5},
                    headers=headers,
                    timeout=10
                )
                print(f"   /search/text: {search_resp.status_code}")
                if search_resp.status_code == 200:
                    print(f"   ✅ 检索成功")
                    result = search_resp.json()
                    print(f"   检索结果数量: {len(result.get('data', {}).get('results', []))}")
                
                # 测试作业指引生成
                guide_resp = requests.post(
                    f'{base_url}/api/v1/guide/generate',
                    json={
                        'device_type': '发动机',
                        'fault_type': '启动困难',
                        'safety_level': '高',
                        'detail_level': '详细'
                    },
                    headers=headers,
                    timeout=30
                )
                print(f"   /guide/generate: {guide_resp.status_code}")
                if guide_resp.status_code == 200:
                    print(f"   ✅ 指引生成成功")
                
                # 测试知识图谱
                kg_resp = requests.get(
                    f'{base_url}/api/v1/knowledge-graph/graph',
                    headers=headers,
                    timeout=10
                )
                print(f"   /knowledge-graph/graph: {kg_resp.status_code}")
                if kg_resp.status_code == 200:
                    print(f"   ✅ 知识图谱查询成功")
                
                return True
            else:
                print(f"   ❌ Token不存在: {data}")
        else:
            print(f"   ❌ 登录失败")
            return False
            
    except Exception as e:
        print(f"   ❌ 异常: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_login()
    print("\n" + "=" * 70)
    print(f"测试结果: {'✅ 成功' if success else '❌ 失败'}")
    print("=" * 70)
