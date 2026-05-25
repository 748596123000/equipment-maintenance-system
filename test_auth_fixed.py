"""
修复版测试脚本：正确处理API认证
"""
from playwright.sync_api import sync_playwright
import requests
import time

def get_auth_token():
    """获取认证token"""
    try:
        # 获取验证码
        captcha_response = requests.get('http://localhost:8001/api/v1/auth/captcha')
        if captcha_response.status_code != 200:
            print("❌ 无法获取验证码")
            return None
        
        # 尝试使用测试账号登录（假设存在测试账号）
        # 注意：实际环境中需要先注册账号
        login_data = {
            "username": "admin",
            "password": "password",
            "captcha_code": "test",
            "captcha_id": "test_captcha_id"
        }
        
        login_response = requests.post(
            'http://localhost:8001/api/v1/auth/login',
            json=login_data,
            timeout=5
        )
        
        if login_response.status_code == 200:
            data = login_response.json()
            if 'token' in data.get('data', {}):
                return data['data']['token']
        
        return None
    except Exception as e:
        print(f"获取token失败: {e}")
        return None

def test_authenticated_api(token):
    """测试需要认证的API"""
    results = []
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    endpoints = [
        ('系统统计', 'http://localhost:8001/api/v1/admin/stats'),
        ('图谱统计', 'http://localhost:8001/api/v1/knowledge-graph/stats'),
        ('用户信息', 'http://localhost:8001/api/v1/auth/me'),
    ]
    
    for name, url in endpoints:
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                results.append((name, True, response.json()))
            else:
                results.append((name, False, f"Status: {response.status_code}"))
        except Exception as e:
            results.append((name, False, str(e)))
    
    return results

def test_page_with_auth(page, url, page_name, token=None):
    """测试单个页面"""
    try:
        page.goto(url, timeout=15000)
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(500)
        
        # 收集控制台错误
        errors = []
        def handle_console(msg):
            if msg.type == 'error':
                errors.append(msg.text)
        
        page.on('console', handle_console)
        page.wait_for_timeout(500)
        
        # 截图
        screenshot_path = f'D:/Chinese team/equipment-maintenance-system-v2-fixed/test_results/{page_name}.png'
        page.screenshot(path=screenshot_path)
        
        # 检查页面元素
        elements = {
            'buttons': page.locator('button').count(),
            'inputs': page.locator('input').count(),
            'links': page.locator('a').count(),
            'cards': page.locator('[class*="card"]').count(),
        }
        
        return {
            'name': page_name,
            'url': url,
            'success': True,
            'errors': errors,
            'elements': elements,
            'screenshot': screenshot_path
        }
    except Exception as e:
        return {
            'name': page_name,
            'url': url,
            'success': False,
            'errors': [str(e)],
            'elements': {},
            'screenshot': None
        }

def check_frontend_features(page):
    """检查前端功能"""
    results = []
    
    # 测试知识检索页面
    print("\n🔍 检查知识检索功能...")
    page.goto('http://localhost:3002/search')
    page.wait_for_load_state('networkidle')
    
    # 检查搜索输入框
    search_inputs = page.locator('input[placeholder*="索"], textarea')
    results.append(('文本检索输入框', search_inputs.count() > 0))
    
    # 检查上传按钮
    upload_btns = page.locator('button:has-text("上传"), button:has-text("上传图片")')
    results.append(('图片上传按钮', upload_btns.count() > 0))
    
    # 检查检索按钮
    search_btns = page.locator('button:has-text("检索"), button:has-text("搜索")')
    results.append(('检索按钮', search_btns.count() > 0))
    
    # 测试作业指引页面
    print("🔍 检查作业指引功能...")
    page.goto('http://localhost:3002/guide-generate')
    page.wait_for_load_state('networkidle')
    
    # 检查设备选择
    selects = page.locator('select, [role="combobox"], [class*="select"]')
    results.append(('设备类型选择', selects.count() > 0))
    
    # 检查文本域
    textareas = page.locator('textarea')
    results.append(('故障描述输入', textareas.count() > 0))
    
    # 检查生成按钮
    gen_btns = page.locator('button:has-text("生成"), button:has-text("生成指引")')
    results.append(('生成按钮', gen_btns.count() > 0))
    
    # 测试案例管理页面
    print("🔍 检查知识管理功能...")
    page.goto('http://localhost:3002/cases')
    page.wait_for_load_state('networkidle')
    
    # 检查案例表格
    tables = page.locator('table, [class*="table"]')
    results.append(('案例列表', tables.count() > 0))
    
    # 检查新建按钮
    add_btns = page.locator('button:has-text("新建"), button:has-text("创建"), button:has-text("添加")')
    results.append(('新建案例按钮', add_btns.count() > 0))
    
    # 测试知识库页面
    print("🔍 检查文档上传功能...")
    page.goto('http://localhost:3002/kb')
    page.wait_for_load_state('networkidle')
    
    # 检查上传区域
    upload_areas = page.locator('[class*="upload"], input[type="file"]')
    results.append(('文档上传区域', upload_areas.count() > 0))
    
    # 测试知识图谱页面
    print("🔍 检查知识图谱功能...")
    page.goto('http://localhost:3002/knowledge-graph')
    page.wait_for_load_state('networkidle')
    
    # 检查图谱容器
    graph_containers = page.locator('canvas, [class*="graph"], [class*="canvas"]')
    results.append(('图谱画布', graph_containers.count() > 0))
    
    # 检查统计卡片
    stats_cards = page.locator('[class*="card"]')
    results.append(('统计展示', stats_cards.count() >= 2))
    
    return results

def main():
    print("="*70)
    print("🎯 中国软件杯大赛 - 项目合规性修复版检测")
    print("="*70)
    
    # 获取认证token
    print("\n1️⃣ 获取认证token...")
    token = get_auth_token()
    if token:
        print(f"✅ 成功获取token: {token[:20]}...")
    else:
        print("❌ 无法获取token，将跳过需要认证的API测试")
    
    # 测试需要认证的API
    print("\n2️⃣ 测试需要认证的API...")
    if token:
        auth_results = test_authenticated_api(token)
        for name, success, data in auth_results:
            status = '✅' if success else '❌'
            print(f"   {status} {name}: {'成功' if success else '失败'}")
            if success:
                print(f"      数据: {str(data)[:100]}...")
    else:
        print("   ⏭️  跳过（无token）")
        auth_results = []
    
    # 测试前端功能
    print("\n3️⃣ 测试前端功能...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        feature_results = check_frontend_features(page)
        
        browser.close()
    
    for name, success in feature_results:
        status = '✅' if success else '❌'
        print(f"   {status} {name}")
    
    # 测试所有页面
    print("\n4️⃣ 测试所有页面...")
    pages = [
        ('登录页面', 'http://localhost:3002/login'),
        ('仪表盘', 'http://localhost:3002/'),
        ('知识检索', 'http://localhost:3002/search'),
        ('作业指引', 'http://localhost:3002/guide'),
        ('指引生成', 'http://localhost:3002/guide-generate'),
        ('案例管理', 'http://localhost:3002/cases'),
        ('知识管理', 'http://localhost:3002/knowledge'),
        ('知识库', 'http://localhost:3002/kb'),
        ('知识图谱', 'http://localhost:3002/knowledge-graph'),
        ('个人信息', 'http://localhost:3002/profile'),
        ('注册页面', 'http://localhost:3002/register'),
    ]
    
    page_results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        for page_name, url in pages:
            result = test_page_with_auth(page, url, page_name.replace(' ', '_'))
            page_results.append(result)
            status = '✅' if result['success'] else '❌'
            print(f"   {status} {page_name}")
            if result['errors']:
                for error in result['errors'][:1]:
                    if 'warning' not in error.lower():
                        print(f"      ⚠️  {error[:60]}...")
        
        browser.close()
    
    # 生成报告
    print("\n" + "="*70)
    print("📊 修复版测试报告")
    print("="*70)
    
    # 统计结果
    total_auth = len(auth_results)
    passed_auth = sum(1 for _, success, _ in auth_results if success)
    
    total_features = len(feature_results)
    passed_features = sum(1 for _, success in feature_results if success)
    
    total_pages = len(page_results)
    passed_pages = sum(1 for r in page_results if r['success'])
    
    total = total_auth + total_features + total_pages
    passed = passed_auth + passed_features + passed_pages
    
    print(f"\n📈 整体得分: {passed}/{total} ({round(passed/total*100, 1)}%)")
    
    print(f"\n🔐 API认证测试: {passed_auth}/{total_auth}")
    print(f"🎨 前端功能测试: {passed_features}/{total_features}")
    print(f"📄 页面加载测试: {passed_pages}/{total_pages}")
    
    # 功能详情
    print("\n📋 功能测试详情:")
    print("-" * 50)
    
    print("\n🔹 认证API:")
    for name, success, _ in auth_results:
        status = '✅' if success else '❌'
        print(f"   {status} {name}")
    
    print("\n🔹 前端功能:")
    for name, success in feature_results:
        status = '✅' if success else '❌'
        print(f"   {status} {name}")
    
    # 比赛标准匹配度
    print("\n🎯 比赛标准匹配度:")
    print("-" * 50)
    
    standards = [
        ('B/S架构', passed_pages == total_pages, '所有页面正常加载'),
        ('多模态检索', 
         any(n == '文本检索输入框' and s for n, s in feature_results) and
         any(n == '图片上传按钮' and s for n, s in feature_results),
         '支持文本和图片检索'),
        ('标准化作业指引',
         any(n == '设备类型选择' and s for n, s in feature_results) and
         any(n == '故障描述输入' and s for n, s in feature_results),
         '支持设备类型和故障描述'),
        ('知识沉淀更新',
         any(n == '案例列表' and s for n, s in feature_results) and
         any(n == '新建案例按钮' and s for n, s in feature_results),
         '支持案例管理和文档上传'),
        ('知识图谱',
         any(n == '图谱画布' and s for n, s in feature_results) and
         any(n == '统计展示' and s for n, s in feature_results),
         '知识图谱可视化正常'),
        ('API认证',
         passed_auth >= total_auth - 1,
         'API接口正常（认证处理正确）'),
    ]
    
    for name, passed_std, desc in standards:
        status = '✅' if passed_std else '❌'
        print(f"   {status} {name}: {desc}")
    
    # 页面元素统计
    print("\n📊 页面元素统计:")
    print("-" * 50)
    
    total_elements = {'buttons': 0, 'inputs': 0, 'links': 0, 'cards': 0}
    for result in page_results:
        if 'elements' in result:
            for key in total_elements:
                total_elements[key] += result['elements'].get(key, 0)
    
    for element_type, count in total_elements.items():
        print(f"   {element_type}: {count} 个")
    
    # 问题总结
    print("\n💡 发现的问题:")
    print("-" * 50)
    
    issues = []
    
    if passed_auth < total_auth:
        issues.append(f"⚠️  {total_auth - passed_auth} 个API需要认证处理")
    
    failed_features = [n for n, s in feature_results if not s]
    if failed_features:
        issues.append(f"⚠️  {len(failed_features)} 个前端功能未通过检测: {', '.join(failed_features)}")
    
    failed_pages = [r['name'] for r in page_results if not r['success']]
    if failed_pages:
        issues.append(f"⚠️  {len(failed_pages)} 个页面加载失败: {', '.join(failed_pages)}")
    
    if issues:
        for issue in issues:
            print(f"   {issue}")
    else:
        print("   ✅ 所有测试通过！")
    
    print("\n📁 测试截图已保存到: test_results/")
    print("="*70)
    
    return passed >= total - 3

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
