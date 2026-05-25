"""
深入诊断作业指引生成问题
"""
import requests
import json

def debug_guide_generator():
    """详细诊断指引生成流程"""
    base_url = 'http://localhost:8001'
    
    print("=" * 80)
    print("🔍 作业指引生成 - 详细诊断")
    print("=" * 80)
    
    # Step 1: 获取Token
    print("\n[1/6] 获取认证Token...")
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
            headers = {'Authorization': f'Bearer {token}'}
        else:
            print(f"   ❌ 登录失败: {login_resp.status_code}")
            return
            
    except Exception as e:
        print(f"   ❌ 异常: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 2: 检查系统状态
    print("\n[2/6] 检查系统状态...")
    try:
        stats_resp = requests.get(f'{base_url}/api/v1/admin/stats', headers=headers, timeout=5)
        if stats_resp.status_code == 200:
            print(f"   ✅ 系统状态正常")
            stats = stats_resp.json()
            print(f"      统计信息: {json.dumps(stats.get('data', {}), ensure_ascii=False)[:200]}")
    except Exception as e:
        print(f"   ⚠️ 无法获取统计: {e}")
    
    # Step 3: 测试知识检索
    print("\n[3/6] 测试知识检索...")
    try:
        search_data = {'query': '发动机维修', 'top_k': 3}
        search_resp = requests.post(
            f'{base_url}/api/v1/search/text',
            json=search_data,
            headers=headers,
            timeout=10
        )
        
        if search_resp.status_code == 200:
            search_result = search_resp.json()
            data = search_result.get('data', {})
            results = data.get('results', [])
            print(f"   ✅ 检索成功: 找到 {len(results)} 个相关文档")
            for i, r in enumerate(results[:2]):
                print(f"      [{i+1}] {r.get('content', '')[:80]}...")
        else:
            print(f"   ❌ 检索失败: {search_resp.status_code}")
            
    except Exception as e:
        print(f"   ⚠️ 检索异常: {e}")
    
    # Step 4: 检查LLM服务配置
    print("\n[4/6] 测试LLM相关接口...")
    
    # 尝试直接检查检索器
    print("\n[5/6] 诊断指引生成接口...")
    
    test_cases = [
        {
            'name': '简单任务',
            'data': {
                'task_description': '检查发动机机油油位',
                'safety_level': 'standard',
                'detail_level': 'brief'
            }
        },
        {
            'name': '完整任务',
            'data': {
                'task_description': '更换柴油发动机空气滤清器',
                'equipment_model': '玉柴YC6G-240',
                'equipment_type': '柴油发动机',
                'safety_level': 'high',
                'detail_level': 'detailed'
            }
        }
    ]
    
    for test in test_cases:
        print(f"\n   测试: {test['name']}")
        try:
            guide_resp = requests.post(
                f'{base_url}/api/v1/guide/generate',
                json=test['data'],
                headers=headers,
                timeout=60
            )
            
            if guide_resp.status_code == 200:
                guide_data = guide_resp.json()
                print(f"      ✅ 生成成功!")
                if 'data' in guide_data:
                    guide = guide_data['data']
                    if isinstance(guide, dict):
                        print(f"      标题: {guide.get('title', 'N/A')}")
                        print(f"      步骤数: {len(guide.get('steps', []))}")
                        if guide.get('steps'):
                            print(f"      步骤示例: {guide['steps'][0].get('title', '')}")
            else:
                print(f"      ❌ 失败 (HTTP {guide_resp.status_code})")
                print(f"      响应: {guide_resp.text[:500]}")
                
        except Exception as e:
            print(f"      ⚠️ 异常: {e}")
    
    print("\n" + "=" * 80)
    print("\n📋 诊断建议:")
    print("   1. 检查后端日志获取详细错误信息")
    print("   2. 验证 LLM API Key 有效性")
    print("   3. 尝试降低 LLM 温度参数 (0.1-0.3)")
    print("   4. 检查网络连接是否正常")
    print("   5. 验证 embedding 服务是否可用")
    print("=" * 80)

if __name__ == '__main__':
    debug_guide_generator()
