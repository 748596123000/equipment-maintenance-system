"""
完整的综合测试脚本 - 带正确验证码处理
"""
from playwright.sync_api import sync_playwright
import requests
import json
import time
from datetime import datetime

class FullTestRunner:
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
        self.admin_token = None
        
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
    
    def get_admin_token(self):
        """获取管理员Token"""
        print("\n🔐 获取管理员认证Token...")
        
        try:
            # 获取验证码
            captcha_resp = requests.get(f'{self.base_url}/api/v1/auth/captcha', timeout=5)
            if captcha_resp.status_code != 200:
                self.log_result('api', '获取验证码', False, '获取失败')
                return False
            
            captcha_data = captcha_resp.json()
            captcha_id = captcha_data.get('data', {}).get('captcha_id')
            captcha_code = captcha_data.get('data', {}).get('captcha_code', '0000')  # 尝试默认
            
            print(f"   获取验证码ID: {captcha_id}")
            print(f"   获取验证码Code: {captcha_code}")
            
            # 尝试登录
            login_data = {
                "username": "admin",
                "password": "DCHsyHXaFwAdv9Ur",
                "captcha_code": captcha_code,
                "captcha_id": captcha_id
            }
            
            login_resp = requests.post(
                f'{self.base_url}/api/v1/auth/login',
                json=login_data,
                timeout=5
            )
            
            if login_resp.status_code == 200:
                data = login_resp.json()
                if 'data' in data and 'token' in data['data']:
                    self.admin_token = data['data']['token']
                    self.log_result('api', '管理员登录', True, '登录成功',
                                  {'username': 'admin', 'token_prefix': self.admin_token[:20]})
                    return True
            
            # 如果默认验证码失败，尝试多次
            for _ in range(3):
                time.sleep(0.5)
                captcha_resp = requests.get(f'{self.base_url}/api/v1/auth/captcha', timeout=5)
                if captcha_resp.status_code == 200:
                    captcha_data = captcha_resp.json()
                    captcha_id = captcha_data.get('data', {}).get('captcha_id')
                    captcha_code = captcha_data.get('data', {}).get('captcha_code', '0000')
                    
                    login_data = {
                        "username": "admin",
                        "password": "DCHsyHXaFwAdv9Ur",
                        "captcha_code": captcha_code,
                        "captcha_id": captcha_id
                    }
                    
                    login_resp = requests.post(
                        f'{self.base_url}/api/v1/auth/login',
                        json=login_data,
                        timeout=5
                    )
                    
                    if login_resp.status_code == 200:
                        data = login_resp.json()
                        if 'data' in data and 'token' in data['data']:
                            self.admin_token = data['data']['token']
                            self.log_result('api', '管理员登录(重试)', True, '登录成功',
                                          {'username': 'admin'})
                            return True
            
            self.log_result('api', '管理员登录', False, f'登录失败: {login_resp.status_code}')
            return False
            
        except Exception as e:
            self.log_result('api', '管理员登录', False, f'异常: {str(e)[:50]}')
            return False
    
    def test_api_endpoints(self):
        """测试API接口"""
        print("\n📡 测试API接口...")
        
        # 公共API
        public_endpoints = [
            ('/health', '健康检查'),
            ('/health/ready', '系统就绪'),
            ('/api/v1/auth/captcha', '验证码API'),
        ]
        
        for endpoint, name in public_endpoints:
            try:
                resp = requests.get(f'{self.base_url}{endpoint}', timeout=5)
                if resp.status_code == 200:
                    self.log_result('api', name, True, '正常',
                                  {'status': resp.status_code})
                else:
                    self.log_result('api', name, False, f'异常: {resp.status_code}')
            except Exception as e:
                self.log_result('api', name, False, f'请求失败')
        
        # 需要认证的API
        if not self.admin_token:
            self.log_result('api', '认证API测试', False, '无Token')
            return
        
        headers = {'Authorization': f'Bearer {self.admin_token}'}
        
        auth_endpoints = [
            ('GET', '/api/v1/auth/me', '用户信息'),
            ('GET', '/api/v1/admin/stats', '系统统计'),
            ('GET', '/api/v1/knowledge-graph/stats', '知识图谱统计'),
            ('GET', '/api/v1/case/list', '案例列表'),
            ('GET', '/api/v1/upload/list', '文档列表'),
        ]
        
        for method, endpoint, name in auth_endpoints:
            try:
                if method == 'GET':
                    resp = requests.get(f'{self.base_url}{endpoint}', headers=headers, timeout=5)
                else:
                    resp = requests.post(f'{self.base_url}{endpoint}', headers=headers, timeout=5)
                
                if resp.status_code == 200:
                    self.log_result('api', name, True, '正常',
                                  {'status': resp.status_code})
                else:
                    self.log_result('api', name, False, f'异常: {resp.status_code}')
            except Exception as e:
                self.log_result('api', name, False, f'请求失败')
    
    def test_pages(self, page):
        """测试前端页面"""
        print("\n🖥️ 测试前端页面...")
        
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
                
                body_text = page.locator('body').inner_text()
                has_content = len(body_text) > 50
                
                if has_content:
                    self.log_result('page', name, True, '加载成功',
                                  {'content_length': len(body_text)})
                else:
                    self.log_result('page', name, False, '页面内容过少')
                    
            except Exception as e:
                self.log_result('page', name, False, f'加载失败')
    
    def test_ui_elements(self, page):
        """测试UI交互"""
        print("\n🎨 测试UI元素...")
        
        try:
            page.goto(f'{self.frontend_url}/login', timeout=15000)
            page.wait_for_load_state('networkidle')
            
            # 检查登录表单
            has_username = page.locator('#username').count() > 0
            has_password = page.locator('#password').count() > 0
            has_captcha = page.locator('#captcha').count() > 0
            has_submit = page.locator('button[type="submit"]').count() > 0
            
            if all([has_username, has_password, has_captcha, has_submit]):
                self.log_result('ui', '登录表单完整性', True, '所有表单元素存在')
                
                # 测试输入
                page.locator('#username').fill('testuser')
                if page.locator('#username').input_value() == 'testuser':
                    self.log_result('ui', '用户名输入', True, '输入功能正常')
                
                page.locator('#password').fill('testpass')
                if page.locator('#password').input_value() == 'testpass':
                    self.log_result('ui', '密码输入', True, '输入功能正常')
            else:
                self.log_result('ui', '登录表单完整性', False, '表单元素缺失')
        except Exception as e:
            self.log_result('ui', 'UI测试', False, f'异常')
    
    def test_core_functions(self):
        """测试核心功能"""
        print("\n⚙️ 测试核心业务功能...")
        
        if not self.admin_token:
            self.log_result('function', '业务功能测试', False, '无Token')
            return
        
        headers = {
            'Authorization': f'Bearer {self.admin_token}',
            'Content-Type': 'application/json'
        }
        
        # 知识检索
        try:
            resp = requests.post(
                f'{self.base_url}/api/v1/search/text',
                json={'query': '发动机维修', 'top_k': 5, 'mode': 'hybrid'},
                headers=headers,
                timeout=15
            )
            if resp.status_code == 200:
                self.log_result('function', '知识检索', True, '检索功能正常')
            else:
                self.log_result('function', '知识检索', False, f'异常: {resp.status_code}')
        except Exception as e:
            self.log_result('function', '知识检索', False, '请求异常')
        
        # 作业指引生成 - 使用正确的参数
        try:
            resp = requests.post(
                f'{self.base_url}/api/v1/guide/generate',
                json={
                    'task_description': '发动机启动困难，需要进行故障诊断和维修',
                    'equipment_model': '玉柴YC6G-240',
                    'equipment_type': '柴油发动机',
                    'safety_level': 'high',
                    'detail_level': 'detailed'
                },
                headers=headers,
                timeout=30
            )
            if resp.status_code == 200:
                self.log_result('function', '作业指引生成', True, '生成功能正常')
            else:
                self.log_result('function', '作业指引生成', False, f'异常: {resp.status_code}')
        except Exception as e:
            self.log_result('function', '作业指引生成', False, '请求异常')
        
        # 知识图谱查询
        try:
            resp = requests.get(
                f'{self.base_url}/api/v1/knowledge-graph/graph',
                headers=headers,
                timeout=10
            )
            if resp.status_code == 200:
                self.log_result('function', '知识图谱', True, '图谱功能正常')
            else:
                self.log_result('function', '知识图谱', False, f'异常: {resp.status_code}')
        except Exception as e:
            self.log_result('function', '知识图谱', False, '请求异常')
    
    def generate_report(self):
        """生成报告"""
        print("\n" + "="*70)
        print("📊 综合测试报告")
        print("="*70)
        
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
        
        score = round(passed/total*100, 1) if total > 0 else 0
        
        print(f"\n📈 总体得分: {passed}/{total} ({score}%)")
        print(f"\n📋 分项得分:")
        print(f"   🔌 API接口: {passed_api}/{total_api}")
        print(f"   📄 页面加载: {passed_page}/{total_page}")
        print(f"   ⚙️ 业务功能: {passed_func}/{total_func}")
        print(f"   🎨 UI交互: {passed_ui}/{total_ui}")
        
        print(f"\n📝 详细结果:")
        for category, tests in [
            ('API接口', self.results['api_tests']),
            ('页面加载', self.results['page_tests']),
            ('业务功能', self.results['function_tests']),
            ('UI交互', self.results['ui_tests'])
        ]:
            print(f"\n   {category}:")
            for test in tests:
                status = '✅' if test['passed'] else '❌'
                print(f"      {status} {test['test']}")
                if test['message']:
                    print(f"         {test['message']}")
        
        failed = [t for tests in [self.results['api_tests'], self.results['page_tests'],
                                 self.results['function_tests'], self.results['ui_tests']]
                  for t in tests if not t['passed']]
        
        if failed:
            print(f"\n⚠️ 发现 {len(failed)} 个问题:")
            for test in failed:
                print(f"   ❌ {test['test']}: {test['message']}")
        
        print(f"\n🎯 比赛标准匹配:")
        standards = [
            ('B/S架构', passed_page >= total_page - 1),
            ('API接口', passed_api >= total_api - 1),
            ('知识检索', any('检索' in t['test'] and t['passed'] for t in self.results['function_tests'])),
            ('作业指引', any('指引' in t['test'] and t['passed'] for t in self.results['function_tests'])),
            ('知识图谱', any('图谱' in t['test'] and t['passed'] for t in self.results['function_tests'])),
            ('认证机制', self.admin_token is not None),
        ]
        
        matched = sum(1 for _, p in standards if p)
        for name, passed_std in standards:
            status = '✅' if passed_std else '❌'
            print(f"   {status} {name}")
        
        print(f"\n📊 标准匹配: {matched}/{len(standards)} ({round(matched/len(standards)*100)}%)")
        
        print("\n" + "="*70)
        return score >= 85
    
    def run(self):
        """运行测试"""
        print("="*70)
        print("🎯 设备检修知识系统 - 全面合规性检测")
        print("="*70)
        
        self.get_admin_token()
        self.test_api_endpoints()
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1920, 'height': 1080})
            
            self.test_pages(page)
            self.test_ui_elements(page)
            
            browser.close()
        
        self.test_core_functions()
        
        return self.generate_report()

if __name__ == '__main__':
    runner = FullTestRunner()
    success = runner.run()
    exit(0 if success else 1)
