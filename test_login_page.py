from playwright.sync_api import sync_playwright
import time

print('=== 登录页面测试 ===\n')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    
    try:
        # 1. 访问登录页面
        print('1. 访问登录页面')
        page.goto('http://localhost:3001/login')
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(2000)  # 等待动画完成
        
        # 2. 截图保存
        print('2. 保存登录页面截图')
        page.screenshot(path='D:/Chinese team/equipment-maintenance-system-v2-fixed/test_results/login_page.png', full_page=True)
        
        # 3. 检查输入框
        print('\n3. 检查登录表单元素')
        
        # 查找用户名输入框
        username_input = page.locator('input[type="text"], input[placeholder*="用户"]')
        if username_input.count() > 0:
            print(f'   ✅ 找到用户名输入框: {username_input.count()} 个')
            # 检查输入框样式
            box = username_input.first.bounding_box()
            if box:
                print(f'      位置: x={box["x"]}, y={box["y"]}')
                print(f'      尺寸: width={box["width"]}, height={box["height"]}')
        else:
            print('   ❌ 未找到用户名输入框')
        
        # 查找密码输入框
        password_input = page.locator('input[type="password"]')
        if password_input.count() > 0:
            print(f'   ✅ 找到密码输入框: {password_input.count()} 个')
            box = password_input.first.bounding_box()
            if box:
                print(f'      位置: x={box["x"]}, y={box["y"]}')
                print(f'      尺寸: width={box["width"]}, height={box["height"]}')
        else:
            print('   ❌ 未找到密码输入框')
        
        # 4. 检查图标
        print('\n4. 检查图标元素')
        icons = page.locator('svg, [class*="icon"]')
        print(f'   找到图标/图标元素: {icons.count()} 个')
        
        # 5. 检查表单容器
        print('\n5. 检查表单容器')
        form_container = page.locator('form, [class*="form"], [class*="card"]')
        print(f'   找到表单容器: {form_container.count()} 个')
        
        # 6. 获取页面HTML片段
        print('\n6. 分析DOM结构')
        login_card = page.locator('[class*="card"]').first
        if login_card.count() > 0:
            html = login_card.inner_html()
            print(f'   表单容器HTML长度: {len(html)} 字符')
            # 检查是否有输入框在表单内
            inputs_in_card = login_card.locator('input')
            print(f'   表单内输入框数量: {inputs_in_card.count()}')
        
        # 7. 检查控制台错误
        print('\n7. 检查控制台错误')
        page.on('console', lambda msg: print(f'   {msg.type}: {msg.text}') if msg.type == 'error' else None)
        page.reload()
        page.wait_for_timeout(1000)
        
        # 8. 测试表单交互
        print('\n8. 测试表单交互')
        if username_input.count() > 0:
            username_input.first.fill('admin')
            print('   ✅ 用户名输入成功')
        if password_input.count() > 0:
            password_input.first.fill('password')
            print('   ✅ 密码输入成功')
        
        # 截图最终状态
        page.screenshot(path='D:/Chinese team/equipment-maintenance-system-v2-fixed/test_results/login_page_filled.png', full_page=True)
        print('   已保存填写后的截图')
        
    except Exception as e:
        print(f'\n❌ 测试过程中出现错误: {e}')
        import traceback
        traceback.print_exc()
        page.screenshot(path='D:/Chinese team/equipment-maintenance-system-v2-fixed/test_results/error.png', full_page=True)
    finally:
        browser.close()
        
print('\n=== 测试完成 ===')
print('截图已保存到 test_results/ 目录')
