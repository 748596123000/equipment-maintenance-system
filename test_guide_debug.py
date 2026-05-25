"""
测试作业指引生成并诊断错误
"""
import requests

def test_guide_generation():
    """测试指引生成"""
    base_url = 'http://localhost:8001'
    
    print("=" * 70)
    print("🔍 作业指引生成问题诊断")
    print("=" * 70)
    
    # 1. 先登录获取token
    print("\n1️⃣ 获取Token...")
    try:
        # 获取验证码
        captcha_resp = requests.get(f'{base_url}/api/v1/auth/captcha', timeout=5)
        captcha_id = captcha_resp.json().get('data', {}).get('captcha_id')
        
        # 登录
        login_data = {
            "username": "admin",
            "password": "DCHsyHXaFwAdv9Ur",
            "captcha_code": "0000",
            "captcha_id": captcha_id
        }
        
        login_resp = requests.post(
            f'{base_url}/api/v1/auth/login',
            json=login_data,
            timeout=5
        )
        
        if login_resp.status_code == 200:
            token = login_resp.json()['data']['token']
            print(f"   ✅ Token获取成功")
        else:
            print(f"   ❌ 登录失败")
            return
            
    except Exception as e:
        print(f"   ❌ 异常: {e}")
        return
    
    # 2. 尝试生成指引
    print("\n2️⃣ 测试指引生成...")
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    guide_data = {
        'task_description': '发动机启动困难，需要进行故障诊断和维修',
        'equipment_model': '玉柴YC6G-240',
        'equipment_type': '柴油发动机',
        'safety_level': 'high',
        'detail_level': 'detailed'
    }
    
    print(f"   请求数据: {guide_data}")
    
    try:
        resp = requests.post(
            f'{base_url}/api/v1/guide/generate',
            json=guide_data,
            headers=headers,
            timeout=30
        )
        
        print(f"   状态码: {resp.status_code}")
        print(f"   响应: {resp.text[:1000]}")
        
        if resp.status_code == 200:
            print(f"   ✅ 指引生成成功")
            data = resp.json()
            if 'data' in data and 'guide' in data['data']:
                guide = data['data']['guide']
                print(f"\n   📝 生成指引内容:")
                print(f"   {guide[:500]}...")
        else:
            print(f"   ❌ 指引生成失败")
            try:
                error = resp.json()
                print(f"   错误信息: {error}")
            except:
                print(f"   响应内容: {resp.text}")
                
    except Exception as e:
        print(f"   ❌ 请求异常: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)

if __name__ == '__main__':
    test_guide_generation()
