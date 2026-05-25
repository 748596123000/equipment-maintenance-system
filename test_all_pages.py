from playwright.sync_api import sync_playwright
import time

def test_page(page, url, page_name):
    """测试单个页面"""
    print(f'\n{"="*60}')
    print(f'测试页面: {page_name}')
    print(f'URL: {url}')
    print("="*60)
    
    try:
        # 访问页面
        page.goto(url, timeout=10000)
        page.wait_for_load_state('networkidle', timeout=10000)
        page.wait_for_timeout(1500)  # 等待动画完成
        
        # 保存截图
        filename = f'D:/Chinese team/equipment-maintenance-system-v2-fixed/test_results/{page_name.replace(" ", "_").lower()}.png'
        page.screenshot(path=filename, full_page=False)
        print(f'✅ 截图已保存: {filename}')
        
        # 检查页面标题
        title = page.title()
        print(f'✅ 页面标题: {title}')
        
        # 检查是否有错误
        errors = []
        page.on('console', lambda msg: errors.append(f'{msg.type}: {msg.text}') if msg.type == 'error' else None)
        
        # 检查主要元素
        print('\n检查主要元素:')
        
        # 检查按钮
        buttons = page.locator('button')
        print(f'  - 按钮数量: {buttons.count()}')
        
        # 检查输入框
        inputs = page.locator('input')
        print(f'  - 输入框数量: {inputs.count()}')
        
        # 检查链接
        links = page.locator('a')
        print(f'  - 链接数量: {links.count()}')
        
        # 检查卡片
        cards = page.locator('[class*="card"]')
        print(f'  - 卡片数量: {cards.count()}')
        
        # 检查是否有可见的文本
        body_text = page.locator('body').inner_text()
        if len(body_text) > 0:
            print(f'  - 页面文本长度: {len(body_text)} 字符')
            # 检查是否有错误提示
            if 'error' in body_text.lower() or 'undefined' in body_text.lower():
                print('  ⚠️  页面可能包含错误信息')
        
        # 等待控制台错误
        page.wait_for_timeout(500)
        
        if errors:
            print(f'\n❌ 发现控制台错误:')
            for err in errors[:5]:  # 只显示前5个错误
                print(f'   {err}')
            return False
        else:
            print('\n✅ 页面加载正常，无控制台错误')
            return True
            
    except Exception as e:
        print(f'\n❌ 页面加载失败: {e}')
        import traceback
        traceback.print_exc()
        return False

def main():
    print('='*60)
    print('设备检修知识系统 - 全页面测试')
    print('='*60)
    
    results = []
    
    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        
        # 1. 测试登录页面
        results.append(('登录页面', test_page(page, 'http://localhost:3001/login', 'Login Page')))
        
        # 2. 尝试登录
        print('\n\n尝试登录系统...')
        try:
            # 导航到登录页面
            page.goto('http://localhost:3001/login')
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(1000)
            
            # 填写登录表单
            username_input = page.locator('#username')
            password_input = page.locator('#password')
            captcha_input = page.locator('#captcha')
            
            if username_input.count() > 0 and password_input.count() > 0:
                username_input.fill('admin')
                password_input.fill('password')
                captcha_input.fill('test')  # 假设测试验证码
                
                # 点击登录按钮
                submit_btn = page.locator('button[type="submit"]')
                if submit_btn.count() > 0:
                    submit_btn.click()
                    page.wait_for_timeout(2000)
                    
                    # 检查是否登录成功
                    if '/login' not in page.url:
                        print('✅ 登录成功')
                        logged_in = True
                    else:
                        print('❌ 登录失败')
                        logged_in = False
                else:
                    print('❌ 未找到登录按钮')
                    logged_in = False
            else:
                print('❌ 未找到用户名或密码输入框')
                logged_in = False
        except Exception as e:
            print(f'❌ 登录过程出错: {e}')
            logged_in = False
        
        if logged_in:
            # 3. 测试仪表盘
            results.append(('仪表盘', test_page(page, 'http://localhost:3001/', 'Dashboard')))
            
            # 4. 测试知识检索
            results.append(('知识检索', test_page(page, 'http://localhost:3001/search', 'Search')))
            
            # 5. 测试作业指引
            results.append(('作业指引', test_page(page, 'http://localhost:3001/guide', 'Guide')))
            
            # 6. 测试案例管理
            results.append(('案例管理', test_page(page, 'http://localhost:3001/cases', 'Cases')))
            
            # 7. 测试知识图谱
            results.append(('知识图谱', test_page(page, 'http://localhost:3001/knowledge-graph', 'Knowledge Graph')))
            
            # 8. 测试个人信息
            results.append(('个人信息', test_page(page, 'http://localhost:3001/profile', 'Profile')))
        else:
            print('\n⚠️  未登录成功，跳过其他页面测试')
        
        browser.close()
    
    # 打印总结
    print('\n\n' + '='*60)
    print('测试总结')
    print('='*60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for page_name, success in results:
        status = '✅ 通过' if success else '❌ 失败'
        print(f'{page_name:20s} {status}')
    
    print(f'\n总计: {passed}/{total} 页面测试通过')
    
    if passed == total:
        print('\n🎉 所有测试通过！')
    else:
        print(f'\n⚠️  有 {total - passed} 个页面测试失败')
    
    return passed == total

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
