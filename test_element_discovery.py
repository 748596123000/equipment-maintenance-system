"""
元素发现脚本：检查页面实际元素结构
"""
from playwright.sync_api import sync_playwright

def discover_page_elements(page, url, page_name):
    """发现页面的实际元素"""
    print(f"\n{'='*60}")
    print(f"发现 {page_name} 的元素...")
    print('='*60)
    
    try:
        page.goto(url, timeout=15000)
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(1000)
        
        # 检查按钮
        buttons = page.locator('button').all()
        print(f"\n按钮 ({len(buttons)} 个):")
        for i, btn in enumerate(buttons[:10]):
            text = btn.inner_text()[:30]
            classes = btn.get_attribute('class') or ''
            print(f"  {i+1}. {text} | class: {classes[:50]}")
        
        # 检查输入框
        inputs = page.locator('input').all()
        print(f"\n输入框 ({len(inputs)} 个):")
        for i, inp in enumerate(inputs[:10]):
            inp_type = inp.get_attribute('type') or 'text'
            placeholder = inp.get_attribute('placeholder') or ''
            classes = inp.get_attribute('class') or ''
            print(f"  {i+1}. type={inp_type}, placeholder={placeholder[:30]}, class: {classes[:40]}")
        
        # 检查文本域
        textareas = page.locator('textarea').all()
        print(f"\n文本域 ({len(textareas)} 个):")
        for i, ta in enumerate(textareas[:5]):
            placeholder = ta.get_attribute('placeholder') or ''
            print(f"  {i+1}. placeholder={placeholder[:40]}")
        
        # 检查选择器
        selects = page.locator('select').all()
        print(f"\n下拉选择器 ({len(selects)} 个):")
        for i, sel in enumerate(selects[:5]):
            print(f"  {i+1}. select元素")
        
        # 检查表格
        tables = page.locator('table').all()
        print(f"\n表格 ({len(tables)} 个):")
        if tables:
            print(f"  ✅ 找到表格")
        
        # 检查卡片
        cards = page.locator('[class*="card"]').all()
        print(f"\n卡片 ({len(cards)} 个):")
        print(f"  ✅ 找到 {len(cards)} 个卡片")
        
        # 检查canvas
        canvases = page.locator('canvas').all()
        print(f"\n画布/Canvas ({len(canvases)} 个):")
        if canvases:
            print(f"  ✅ 找到画布")
        
        # 检查上传input
        file_inputs = page.locator('input[type="file"]').all()
        print(f"\n文件上传 ({len(file_inputs)} 个):")
        if file_inputs:
            print(f"  ✅ 找到文件上传input")
        
        return True
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*70)
    print("🔍 元素发现工具")
    print("="*70)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        # 检查各个页面
        pages = [
            ('登录页面', 'http://localhost:3002/login'),
            ('知识检索', 'http://localhost:3002/search'),
            ('指引生成', 'http://localhost:3002/guide-generate'),
            ('案例管理', 'http://localhost:3002/cases'),
            ('知识库', 'http://localhost:3002/kb'),
            ('知识图谱', 'http://localhost:3002/knowledge-graph'),
        ]
        
        for page_name, url in pages:
            discover_page_elements(page, url, page_name)
        
        browser.close()
    
    print("\n" + "="*70)
    print("元素发现完成")
    print("="*70)

if __name__ == '__main__':
    main()
