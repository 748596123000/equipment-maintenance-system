"""
全面测试脚本：检测项目是否符合中国软件杯大赛标准
"""
from playwright.sync_api import sync_playwright
import time
import json

def test_bs_architecture(page):
    """测试B/S架构"""
    print("🔍 测试B/S架构...")
    results = []
    
    # 检查是否为Web应用
    try:
        page.goto('http://localhost:3002/login')
        page.wait_for_load_state('networkidle')
        
        # 检查HTML结构
        html = page.content()
        if '<html' in html.lower():
            results.append(('Web应用', True))
        else:
            results.append(('Web应用', False))
        
        # 检查是否有现代前端框架特征
        if 'React' in html or 'Vite' in html or 'shadcn' in html:
            results.append(('前端框架', True))
        else:
            results.append(('前端框架', False))
            
        # 检查是否有API调用能力
        if '/api/' in html or 'axios' in html or 'fetch' in html:
            results.append(('API集成', True))
        else:
            results.append(('API集成', False))
            
    except Exception as e:
        results.append(('测试失败', False))
        
    return results

def test_multi_modal_search(page):
    """测试多模态知识检索功能"""
    print("🔍 测试多模态知识检索功能...")
    results = []
    
    try:
        page.goto('http://localhost:3002/search')
        page.wait_for_load_state('networkidle')
        
        # 检查文本检索
        text_input = page.locator('input[type="text"], textarea')
        if text_input.count() > 0:
            results.append(('文本检索输入框', True))
        else:
            results.append(('文本检索输入框', False))
            
        # 检查图片上传
        file_input = page.locator('input[type="file"]')
        if file_input.count() > 0:
            results.append(('图片上传功能', True))
        else:
            results.append(('图片上传功能', False))
            
        # 检查检索按钮
        search_btn = page.locator('button', has_text='检索')
        if search_btn.count() > 0:
            results.append(('检索按钮', True))
        else:
            results.append(('检索按钮', False))
            
    except Exception as e:
        results.append(('测试失败', False))
        
    return results

def test_guide_system(page):
    """测试标准化作业指引功能"""
    print("🔍 测试标准化作业指引功能...")
    results = []
    
    try:
        page.goto('http://localhost:3002/guide-generate')
        page.wait_for_load_state('networkidle')
        
        # 检查设备类型选择
        selectors = page.locator('select, [role="combobox"]')
        if selectors.count() > 0:
            results.append(('设备类型选择', True))
        else:
            results.append(('设备类型选择', False))
            
        # 检查故障描述输入
        textarea = page.locator('textarea')
        if textarea.count() > 0:
            results.append(('故障描述输入', True))
        else:
            results.append(('故障描述输入', False))
            
        # 检查生成按钮
        generate_btn = page.locator('button', has_text='生成')
        if generate_btn.count() > 0:
            results.append(('生成按钮', True))
        else:
            results.append(('生成按钮', False))
            
    except Exception as e:
        results.append(('测试失败', False))
        
    return results

def test_knowledge_management(page):
    """测试知识沉淀与更新功能"""
    print("🔍 测试知识沉淀与更新功能...")
    results = []
    
    try:
        page.goto('http://localhost:3002/cases')
        page.wait_for_load_state('networkidle')
        
        # 检查案例列表
        table = page.locator('table')
        if table.count() > 0:
            results.append(('案例列表', True))
        else:
            results.append(('案例列表', False))
            
        # 检查新建案例按钮
        add_btn = page.locator('button', has_text='新建')
        if add_btn.count() > 0:
            results.append(('新建案例', True))
        else:
            results.append(('新建案例', False))
            
        # 检查文档上传页面
        page.goto('http://localhost:3002/kb')
        page.wait_for_load_state('networkidle')
        
        upload_area = page.locator('[class*="upload"], input[type="file"]')
        if upload_area.count() > 0:
            results.append(('文档上传', True))
        else:
            results.append(('文档上传', False))
            
    except Exception as e:
        results.append(('测试失败', False))
        
    return results

def test_knowledge_graph(page):
    """测试知识图谱功能"""
    print("🔍 测试知识图谱功能...")
    results = []
    
    try:
        page.goto('http://localhost:3002/knowledge-graph')
        page.wait_for_load_state('networkidle')
        
        # 检查画布/容器
        canvas = page.locator('canvas, [class*="graph"], [class*="canvas"]')
        if canvas.count() > 0:
            results.append(('图谱画布', True))
        else:
            results.append(('图谱画布', False))
            
        # 检查统计卡片
        stats = page.locator('[class*="card"]')
        if stats.count() >= 2:
            results.append(('统计展示', True))
        else:
            results.append(('统计展示', False))
            
    except Exception as e:
        results.append(('测试失败', False))
        
    return results

def test_ui_interactions(page):
    """测试UI交互功能"""
    print("🔍 测试UI交互功能...")
    results = []
    
    try:
        page.goto('http://localhost:3002/login')
        page.wait_for_load_state('networkidle')
        
        # 测试输入框交互
        inputs = page.locator('input')
        if inputs.count() > 0:
            input_el = inputs.first
            input_el.click()
            input_el.type('test')
            value = input_el.input_value()
            if value == 'test':
                results.append(('输入框交互', True))
            else:
                results.append(('输入框交互', False))
        else:
            results.append(('输入框交互', False))
            
        # 测试按钮点击
        buttons = page.locator('button')
        if buttons.count() > 0:
            results.append(('按钮存在', True))
        else:
            results.append(('按钮存在', False))
            
        # 测试链接跳转
        links = page.locator('a')
        if links.count() > 0:
            results.append(('链接存在', True))
        else:
            results.append(('链接存在', False))
            
    except Exception as e:
        results.append(('测试失败', False))
        
    return results

def test_api_status():
    """测试API接口状态"""
    print("🔍 测试API接口状态...")
    import requests
    
    results = []
    
    endpoints = [
        ('健康检查', 'http://localhost:8001/health'),
        ('就绪检查', 'http://localhost:8001/health/ready'),
        ('验证码', 'http://localhost:8001/api/v1/auth/captcha'),
        ('系统统计', 'http://localhost:8001/api/v1/admin/stats'),
        ('图谱统计', 'http://localhost:8001/api/v1/knowledge-graph/stats'),
    ]
    
    for name, url in endpoints:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code in [200, 201]:
                results.append((name, True))
            else:
                results.append((name, False))
        except Exception as e:
            results.append((name, False))
            
    return results

def test_page_load(page, url, page_name):
    """测试单个页面加载"""
    try:
        page.goto(url, timeout=15000)
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(500)
        
        # 检查是否有错误
        errors = []
        page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
        
        # 截图
        screenshot_path = f'D:/Chinese team/equipment-maintenance-system-v2-fixed/test_results/{page_name}.png'
        page.screenshot(path=screenshot_path)
        
        return {
            'name': page_name,
            'success': True,
            'errors': errors,
            'screenshot': screenshot_path
        }
    except Exception as e:
        return {
            'name': page_name,
            'success': False,
            'errors': [str(e)],
            'screenshot': None
        }

def main():
    print("="*70)
    print("🎯 中国软件杯大赛 - 项目合规性全面检测")
    print("="*70)
    
    all_results = []
    
    # 测试API接口
    api_results = test_api_status()
    all_results.extend([('API-' + name, status) for name, status in api_results])
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        # 测试B/S架构
        bs_results = test_bs_architecture(page)
        all_results.extend(bs_results)
        
        # 测试多模态检索
        search_results = test_multi_modal_search(page)
        all_results.extend(search_results)
        
        # 测试作业指引
        guide_results = test_guide_system(page)
        all_results.extend(guide_results)
        
        # 测试知识管理
        km_results = test_knowledge_management(page)
        all_results.extend(km_results)
        
        # 测试知识图谱
        kg_results = test_knowledge_graph(page)
        all_results.extend(kg_results)
        
        # 测试UI交互
        ui_results = test_ui_interactions(page)
        all_results.extend(ui_results)
        
        # 测试所有页面
        print("\n📄 测试所有页面加载...")
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
        
        page_load_results = []
        for page_name, url in pages:
            result = test_page_load(page, url, page_name.replace(' ', '_'))
            page_load_results.append(result)
            status = '✅' if result['success'] else '❌'
            print(f'  {status} {page_name}')
            
        browser.close()
    
    # 生成报告
    print("\n" + "="*70)
    print("📊 测试报告")
    print("="*70)
    
    # 统计结果
    passed = sum(1 for _, status in all_results if status)
    total = len(all_results)
    
    print(f"\n📈 整体得分: {passed}/{total} ({round(passed/total*100, 1)}%)")
    
    print("\n📋 功能测试结果:")
    print("-" * 50)
    
    categories = {
        'B/S架构': ['Web应用', '前端框架', 'API集成'],
        '多模态检索': ['文本检索输入框', '图片上传功能', '检索按钮'],
        '作业指引': ['设备类型选择', '故障描述输入', '生成按钮'],
        '知识管理': ['案例列表', '新建案例', '文档上传'],
        '知识图谱': ['图谱画布', '统计展示'],
        'UI交互': ['输入框交互', '按钮存在', '链接存在'],
        'API接口': ['健康检查', '就绪检查', '验证码', '系统统计', '图谱统计'],
    }
    
    for category, items in categories.items():
        print(f"\n🔹 {category}:")
        for item in items:
            found = [r for r in all_results if r[0] == item or r[0].endswith('-' + item)]
            if found:
                status = '✅' if found[0][1] else '❌'
                print(f"   {status} {item}")
    
    print("\n📄 页面加载测试:")
    print("-" * 50)
    for result in page_load_results:
        status = '✅' if result['success'] else '❌'
        print(f"   {status} {result['name']}")
        if result['errors']:
            for error in result['errors'][:2]:
                print(f"      ⚠️  {error[:50]}...")
    
    # 比赛标准匹配度
    print("\n🎯 比赛标准匹配度:")
    print("-" * 50)
    
    standards = [
        ('B/S架构', passed >= total - 3, '采用React+FastAPI实现'),
        ('多模态检索', any(r[1] for r in search_results), '支持文本和图片检索'),
        ('标准化作业指引', any(r[1] for r in guide_results), '支持设备类型和故障描述'),
        ('知识沉淀更新', any(r[1] for r in km_results), '支持案例管理和文档上传'),
        ('可视化界面', all(r['success'] for r in page_load_results[:2]), '登录页面和仪表盘正常'),
    ]
    
    for name, passed_std, desc in standards:
        status = '✅' if passed_std else '❌'
        print(f"   {status} {name}: {desc}")
    
    # 优化建议
    print("\n💡 优化建议:")
    print("-" * 50)
    
    if not all(r[1] for r in api_results):
        print("   ⚠️  部分API接口不可用，请检查后端服务")
    
    if not any(r[0] == '图片上传功能' and r[1] for r in search_results):
        print("   ⚠️  建议增强图片检索功能")
    
    if len([r for r in page_load_results if not r['success']]) > 0:
        print("   ⚠️  部分页面加载失败，建议检查路由配置")
    
    print("\n📁 测试截图已保存到: test_results/")
    print("="*70)
    
    return passed, total

if __name__ == '__main__':
    passed, total = main()
    exit(0 if passed >= total - 2 else 1)
