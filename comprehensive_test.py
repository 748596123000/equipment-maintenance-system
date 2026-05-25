"""
🎯 全面综合测试脚本
检测项目是否符合中国软件杯大赛标准
测试所有功能、页面、UI交互
"""
from playwright.sync_api import sync_playwright
import requests
import json
import time
from datetime import datetime

class ComprehensiveTester:
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'api_tests': [],
            'page_tests': [],
            'function_tests': [],
            'ui_tests': [],
            'issues': [],
            'recommendations': []
        }
        self.token = None
        self.base_url = 'http://localhost:8001'
        self.frontend_url = 'http://localhost:3003'
        
    def log_result(self, category, test_name, passed, message='', details=None):
        """记录测试结果"""
        result = {
            'test': test_name,
            'passed': passed,
            'message': message,
            'details': details or {}
        }
        
        if category == 'api':
            self.results['api_tests'].append(result)
        elif category == 'page':
            self.results['page_tests'].append(result)
        elif category == 'function':
            self.results['function_tests'].append(result)
        elif category == 'ui':
            self.results['ui_tests'].append(result)
        
        status = '✅' if passed else '❌'
        print(f"   {status} {test_name}")
        if message:
            print(f"      {message}")
    
    def test_public_api(self):
        """测试公共API"""
        print("\n1️⃣ 测试公共API接口...")
        
        endpoints = [
            ('/health', '健康检查'),
            ('/health/ready', '系统就绪检查'),
            ('/api/v1/auth/captcha', '验证码获取'),
        ]
        
        for endpoint, name in endpoints:
            try:
                response = requests.get(f'{self.base_url}{endpoint}', timeout=5)
                if response.status_code == 200:
                    self.log_result('api', name, True, '正常响应', 
                                  {'status_code': response.status_code})
                else:
                    self.log_result('api', name, False, f'异常状态码: {response.status_code}',
                                  {'status_code': response.status_code})
            except Exception as e:
                self.log_result('api', name, False, f'请求失败: {str(e)[:50]}')
    
    def get_auth_token(self):
        """获取认证token"""
        print("\n2️⃣ 获取认证Token...")
        
        try:
            # 获取验证码
            captcha_resp = requests.get(f'{self.base_url}/api/v1/auth/captcha')
            if captcha_resp.status_code != 200:
                self.log_result('api', '获取验证码', False, '获取失败')
                return False
            
            # 尝试使用admin账号登录
            # 注意：需要实际存在的账号
            login_data = {
                "username": "admin",
                "password": "DCHsyHXaFwAdv9Ur",  # 默认密码
                "captcha_code": "0000",   # 测试验证码
                "captcha_id": "test"
            }
            
            login_resp = requests.post(
                f'{self.base_url}/api/v1/auth/login',
                json=login_data,
                timeout=5
            )
            
            if login_resp.status_code == 200:
                data = login_resp.json()
                if 'token' in data.get('data', {}):
                    self.token = data['data']['token']
                    self.log_result('api', '获取认证Token', True, 
                                   f'Token获取成功', {'username': 'admin'})
                    return True
            
            # 如果登录失败，尝试创建测试账号
            self.log_result('api', '获取认证Token', False, 
                           f'登录失败: {login_resp.status_code}', 
                           {'username': 'admin', 'password': 'admin123'})
            return False
            
        except Exception as e:
            self.log_result('api', '获取认证Token', False, f'异常: {str(e)[:50]}')
            return False
    
    def test_authenticated_api(self):
        """测试需要认证的API"""
        if not self.token:
            self.log_result('api', '认证API测试', False, '无Token，跳过')
            return
        
        print("\n3️⃣ 测试认证API接口...")
        headers = {'Authorization': f'Bearer {self.token}'}
        
        endpoints = [
            ('/api/v1/auth/me', '用户信息'),
            ('/api/v1/admin/stats', '系统统计'),
            ('/api/v1/knowledge-graph/stats', '知识图谱统计'),
            ('/api/v1/case/list', '案例列表'),
            ('/api/v1/upload/list', '文档列表'),
            ('/api/v1/search/text', '文本检索'),
        ]
        
        for endpoint, name in endpoints:
            try:
                response = requests.get(
                    f'{self.base_url}{endpoint}',
                    headers=headers,
                    timeout=5
                )
                
                if response.status_code == 200:
                    self.log_result('api', name, True, '正常响应',
                                  {'status_code': 200})
                elif response.status_code == 401:
                    self.log_result('api', name, False, '认证失败')
                else:
                    self.log_result('api', name, False, 
                                   f'状态码: {response.status_code}',
                                   {'status_code': response.status_code})
            except Exception as e:
                self.log_result('api', name, False, f'请求异常')
    
    def test_pages(self, page):
        """测试所有前端页面"""
        print("\n4️⃣ 测试前端页面...")
        
        pages = [
            (f'{self.frontend_url}/login', '登录页面'),
            (f'{self.frontend_url}/register', '注册页面'),
            (f'{self.frontend_url}/', '仪表盘'),
            (f'{self.frontend_url}/search', '知识检索'),
            (f'{self.frontend_url}/guide', '作业指引'),
            (f'{self.frontend_url}/guide-generate', '指引生成'),
            (f'{self.frontend_url}/cases', '案例管理'),
            (f'{self.frontend_url}/knowledge', '知识管理'),
            (f'{self.frontend_url}/kb', '知识库'),
            (f'{self.frontend_url}/knowledge-graph', '知识图谱'),
            (f'{self.frontend_url}/profile', '个人信息'),
        ]
        
        for url, name in pages:
            try:
                page.goto(url, timeout=15000)
                page.wait_for_load_state('networkidle', timeout=10000)
                page.wait_for_timeout(500)
                
                # 检查页面标题
                title = page.title()
                
                # 检查是否有内容
                body_text = page.locator('body').inner_text()
                has_content = len(body_text) > 50
                
                if has_content:
                    self.log_result('page', name, True, f'加载成功', 
                                  {'title': title, 'content_length': len(body_text)})
                else:
                    self.log_result('page', name, False, '页面内容过少',
                                  {'title': title, 'content_length': len(body_text)})
                    
            except Exception as e:
                self.log_result('page', name, False, f'加载失败: {str(e)[:40]}')
    
    def test_ui_elements(self, page):
        """测试UI元素和交互"""
        print("\n5️⃣ 测试UI元素和交互...")
        
        # 登录页面测试
        try:
            page.goto(f'{self.frontend_url}/login', timeout=15000)
            page.wait_for_load_state('networkidle')
            
            # 检查登录表单
            username_input = page.locator('#username')
            password_input = page.locator('#password')
            captcha_input = page.locator('#captcha')
            submit_btn = page.locator('button[type="submit"]')
            
            # 检查元素存在
            has_username = username_input.count() > 0
            has_password = password_input.count() > 0
            has_captcha = captcha_input.count() > 0
            has_submit = submit_btn.count() > 0
            
            if has_username and has_password and has_captcha and has_submit:
                self.log_result('ui', '登录表单完整性', True, '所有表单元素存在')
                
                # 测试输入交互
                username_input.fill('testuser')
                value = username_input.input_value()
                if value == 'testuser':
                    self.log_result('ui', '输入框交互', True, '输入功能正常')
                else:
                    self.log_result('ui', '输入框交互', False, '输入功能异常')
                
                # 测试密码输入
                password_input.fill('testpass')
                pass_value = password_input.input_value()
                if pass_value == 'testpass':
                    self.log_result('ui', '密码输入', True, '密码输入正常')
                else:
                    self.log_result('ui', '密码输入', False, '密码输入异常')
            else:
                missing = []
                if not has_username: missing.append('用户名')
                if not has_password: missing.append('密码')
                if not has_captcha: missing.append('验证码')
                if not has_submit: missing.append('提交按钮')
                self.log_result('ui', '登录表单完整性', False, 
                               f'缺失: {", ".join(missing)}')
        except Exception as e:
            self.log_result('ui', '登录表单测试', False, f'异常: {str(e)[:40]}')
        
        # 检查按钮和链接
        try:
            buttons = page.locator('button').count()
            links = page.locator('a').count()
            inputs = page.locator('input').count()
            
            self.log_result('ui', '按钮数量', buttons > 0, f'{buttons} 个按钮')
            self.log_result('ui', '链接数量', links > 0, f'{links} 个链接')
            self.log_result('ui', '输入框数量', inputs > 0, f'{inputs} 个输入框')
        except Exception as e:
            self.log_result('ui', '元素统计', False, f'统计失败')
    
    def test_core_functions(self):
        """测试核心业务功能"""
        print("\n6️⃣ 测试核心业务功能...")
        
        if not self.token:
            self.log_result('function', '业务功能测试', False, '无认证Token')
            return
        
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        
        # 测试知识检索
        try:
            search_data = {
                'query': '发动机维修',
                'top_k': 5,
                'mode': 'hybrid'
            }
            
            response = requests.post(
                f'{self.base_url}/api/v1/search/text',
                json=search_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                self.log_result('function', '知识检索功能', True, '检索正常')
            else:
                self.log_result('function', '知识检索功能', False, 
                               f'状态码: {response.status_code}')
        except Exception as e:
            self.log_result('function', '知识检索功能', False, '请求异常')
        
        # 测试作业指引生成
        try:
            guide_data = {
                'device_type': '发动机',
                'fault_type': '启动困难',
                'safety_level': '高',
                'detail_level': '详细'
            }
            
            response = requests.post(
                f'{self.base_url}/api/v1/guide/generate',
                json=guide_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                self.log_result('function', '作业指引生成', True, '生成正常')
            else:
                self.log_result('function', '作业指引生成', False,
                               f'状态码: {response.status_code}')
        except Exception as e:
            self.log_result('function', '作业指引生成', False, '请求异常')
        
        # 测试知识图谱
        try:
            response = requests.get(
                f'{self.base_url}/api/v1/knowledge-graph/graph',
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                self.log_result('function', '知识图谱查询', True, '查询正常')
            else:
                self.log_result('function', '知识图谱查询', False,
                               f'状态码: {response.status_code}')
        except Exception as e:
            self.log_result('function', '知识图谱查询', False, '请求异常')
    
    def generate_report(self):
        """生成测试报告"""
        print("\n" + "="*70)
        print("📊 全面测试报告")
        print("="*70)
        
        # 统计结果
        total_api = len(self.results['api_tests'])
        passed_api = sum(1 for t in self.results['api_tests'] if t['passed'])
        
        total_page = len(self.results['page_tests'])
        passed_page = sum(1 for t in self.results['page_tests'] if t['passed'])
        
        total_func = len(self.results['function_tests'])
        passed_func = sum(1 for t in self.results['function_tests'] if t['passed'])
        
        total_ui = len(self.results['ui_tests'])
        passed_ui = sum(1 for t in self.results['ui_tests'] if t['passed'])
        
        total = total_api + total_page + total_func + total_ui
        passed = passed_api + passed_page + passed_func + passed_ui
        
        print(f"\n📈 总体得分: {passed}/{total} ({round(passed/total*100, 1) if total > 0 else 0}%)")
        
        print(f"\n📋 分项得分:")
        print(f"   🔌 API接口: {passed_api}/{total_api}")
        print(f"   📄 页面加载: {passed_page}/{total_page}")
        print(f"   ⚙️  业务功能: {passed_func}/{total_func}")
        print(f"   🎨 UI交互: {passed_ui}/{total_ui}")
        
        # 详细结果
        print(f"\n📝 详细测试结果:")
        print("-" * 70)
        
        for category, tests in [
            ('🔌 API接口', self.results['api_tests']),
            ('📄 页面加载', self.results['page_tests']),
            ('⚙️ 业务功能', self.results['function_tests']),
            ('🎨 UI交互', self.results['ui_tests'])
        ]:
            print(f"\n{category}:")
            for test in tests:
                status = '✅' if test['passed'] else '❌'
                print(f"   {status} {test['test']}")
                if test['message']:
                    print(f"      {test['message']}")
        
        # 识别问题
        failed_tests = [
            t for tests in [self.results['api_tests'], self.results['page_tests'],
                          self.results['function_tests'], self.results['ui_tests']]
            for t in tests if not t['passed']
        ]
        
        if failed_tests:
            print(f"\n⚠️  发现 {len(failed_tests)} 个问题:")
            print("-" * 70)
            for test in failed_tests:
                print(f"   ❌ {test['test']}")
                print(f"      {test['message']}")
        
        # 比赛标准匹配度
        print(f"\n🎯 比赛标准匹配度:")
        print("-" * 70)
        
        standards = [
            ('B/S架构', passed_page >= total_page - 1, '前端页面正常加载'),
            ('多模态检索', 
             any('检索' in t['test'] and t['passed'] for t in self.results['function_tests']),
             '知识检索功能正常'),
            ('标准化作业指引',
             any('指引' in t['test'] and t['passed'] for t in self.results['function_tests']),
             '作业指引生成正常'),
            ('知识图谱',
             any('图谱' in t['test'] and t['passed'] for t in self.results['function_tests']),
             '知识图谱功能正常'),
            ('认证机制',
             self.token is not None,
             '用户认证系统正常'),
        ]
        
        matched = 0
        for name, passed_std, desc in standards:
            status = '✅' if passed_std else '❌'
            if passed_std:
                matched += 1
            print(f"   {status} {name}: {desc}")
        
        print(f"\n📊 标准匹配: {matched}/{len(standards)} ({round(matched/len(standards)*100)}%)")
        
        # 优化建议
        print(f"\n💡 优化建议:")
        print("-" * 70)
        
        suggestions = []
        
        if passed_page < total_page:
            suggestions.append("部分页面加载失败，建议检查路由配置")
        
        if not self.token:
            suggestions.append("无法获取认证Token，建议检查用户账号和密码")
        
        if any('检索' in t['test'] and not t['passed'] for t in self.results['function_tests']):
            suggestions.append("知识检索功能异常，建议检查ChromaDB和Embedding服务")
        
        if any('指引' in t['test'] and not t['passed'] for t in self.results['function_tests']):
            suggestions.append("作业指引生成异常，建议检查LLM服务配置")
        
        if any('图谱' in t['test'] and not t['passed'] for t in self.results['function_tests']):
            suggestions.append("知识图谱功能异常，建议检查图谱数据")
        
        if suggestions:
            for i, suggestion in enumerate(suggestions, 1):
                print(f"   {i}. {suggestion}")
        else:
            print("   ✅ 所有功能正常，无需优化")
        
        print("\n" + "="*70)
        
        return passed >= total - 3
    
    def run(self):
        """运行完整测试"""
        print("="*70)
        print("🎯 中国软件杯大赛 - 全面合规性检测")
        print("="*70)
        print(f"测试时间: {self.results['timestamp']}")
        print(f"后端地址: {self.base_url}")
        print(f"前端地址: {self.frontend_url}")
        
        # 1. 测试公共API
        self.test_public_api()
        
        # 2. 获取认证Token
        self.get_auth_token()
        
        # 3. 测试认证API
        self.test_authenticated_api()
        
        # 4. 测试前端页面
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1920, 'height': 1080})
            
            self.test_pages(page)
            self.test_ui_elements(page)
            
            browser.close()
        
        # 5. 测试核心业务功能
        self.test_core_functions()
        
        # 6. 生成报告
        success = self.generate_report()
        
        return success

if __name__ == '__main__':
    tester = ComprehensiveTester()
    success = tester.run()
    exit(0 if success else 1)
