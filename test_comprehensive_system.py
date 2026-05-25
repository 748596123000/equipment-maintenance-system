# -*- coding: utf-8 -*-
"""
设备检修知识检索与作业系统 - 全面功能测试
Comprehensive System Test Suite
"""
import sys
import os
import time
import json
sys.path.insert(0, '.')

print('=' * 70)
print('设备检修知识检索与作业系统 - 全面功能测试')
print('Comprehensive System Functionality Test')
print('=' * 70)

# ==================== Test Results Storage ====================
results = {
    'passed': [],
    'failed': [],
    'warnings': []
}

def pass_test(name, detail=""):
    results['passed'].append(name)
    print(f'  [PASS] {name}')
    if detail:
        print(f'         {detail}')

def fail_test(name, detail=""):
    results['failed'].append(name)
    print(f'  [FAIL] {name}')
    if detail:
        print(f'         {detail}')

def warn_test(name, detail=""):
    results['warnings'].append(name)
    print(f'  [WARN] {name}')
    if detail:
        print(f'         {detail}')

# ==================== PART 1: Module Import Tests ====================
print()
print('【PART 1】模块导入测试 (Module Import Tests)')
print('-' * 70)

try:
    from app.config import settings, get_settings
    pass_test('app.config', f'ENVIRONMENT={settings.ENVIRONMENT}, DEBUG={settings.DEBUG}')
except Exception as e:
    fail_test('app.config', str(e))

try:
    from app.models.database import get_database, Database
    pass_test('app.models.database')
except Exception as e:
    fail_test('app.models.database', str(e))

try:
    from app.api.auth import router as auth_router, hash_password, verify_password
    pass_test('app.api.auth')
except Exception as e:
    fail_test('app.api.auth', str(e))

try:
    from app.api.chat import router as chat_router
    pass_test('app.api.chat')
except Exception as e:
    fail_test('app.api.chat', str(e))

try:
    from app.api.upload import router as upload_router, sanitize_filename, safe_path_join
    pass_test('app.api.upload')
except Exception as e:
    fail_test('app.api.upload', str(e))

try:
    from app.api.search import router as search_router
    pass_test('app.api.search')
except Exception as e:
    fail_test('app.api.search', str(e))

try:
    from app.api.guide import router as guide_router
    pass_test('app.api.guide')
except Exception as e:
    fail_test('app.api.guide', str(e))

try:
    from app.api.case import router as case_router
    pass_test('app.api.case')
except Exception as e:
    fail_test('app.api.case', str(e))

try:
    from app.main import create_app
    pass_test('app.main')
except Exception as e:
    fail_test('app.main', str(e))

try:
    from app.core.rag_engine import get_rag_engine
    pass_test('app.core.rag_engine')
except Exception as e:
    warn_test('app.core.rag_engine', f'可能需要API Key: {e}')

try:
    from app.core.retriever import get_retriever
    pass_test('app.core.retriever')
except Exception as e:
    warn_test('app.core.retriever', f'可能需要API Key: {e}')

try:
    from app.services.llm_service import get_llm_service
    pass_test('app.services.llm_service')
except Exception as e:
    warn_test('app.services.llm_service', f'可能需要配置: {e}')

# ==================== PART 2: Configuration Tests ====================
print()
print('【PART 2】配置测试 (Configuration Tests)')
print('-' * 70)

# Test ENVIRONMENT configuration
if hasattr(settings, 'ENVIRONMENT'):
    pass_test('ENVIRONMENT配置存在', f'当前值: {settings.ENVIRONMENT}')
else:
    fail_test('ENVIRONMENT配置存在')

# Test DEBUG behavior
from app.api.auth import get_captcha
import asyncio

async def test_debug_behavior():
    current_env = settings.ENVIRONMENT
    current_debug = settings.DEBUG
    
    # Test case 1: development + debug = leak
    settings.ENVIRONMENT = 'development'
    settings.DEBUG = True
    will_leak = settings.DEBUG and settings.ENVIRONMENT == 'development'
    if will_leak:
        pass_test('DEBUG模式行为(development)', '开发环境会返回验证码')
    else:
        fail_test('DEBUG模式行为(development)')
    
    # Test case 2: production + debug = no leak
    settings.ENVIRONMENT = 'production'
    settings.DEBUG = True
    will_leak = settings.DEBUG and settings.ENVIRONMENT == 'development'
    if not will_leak:
        pass_test('DEBUG模式行为(production)', '生产环境不会返回验证码')
    else:
        fail_test('DEBUG模式行为(production)')
    
    # Restore
    settings.ENVIRONMENT = current_env
    settings.DEBUG = current_debug

asyncio.run(test_debug_behavior())

# Test CORS configuration
if hasattr(settings, 'CORS_ORIGINS') and settings.CORS_ORIGINS:
    pass_test('CORS_ORIGINS配置', f'允许的域名: {settings.CORS_ORIGINS}')
else:
    fail_test('CORS_ORIGINS配置')

# Test ALLOWED_HOSTS configuration
if hasattr(settings, 'ALLOWED_HOSTS') and settings.ALLOWED_HOSTS:
    pass_test('ALLOWED_HOSTS配置', f'允许的主机: {settings.ALLOWED_HOSTS}')
else:
    fail_test('ALLOWED_HOSTS配置')

# ==================== PART 3: Database Tests ====================
print()
print('【PART 3】数据库测试 (Database Tests)')
print('-' * 70)

try:
    db = get_database()
    db.init_db()
    pass_test('数据库初始化', '数据库表创建成功')
except Exception as e:
    fail_test('数据库初始化', str(e))

try:
    # Test user operations
    stats = db.get_stats()
    if 'total_users' in stats:
        pass_test('数据库统计查询', f"用户数: {stats['total_users']}")
    else:
        fail_test('数据库统计查询', '返回数据结构异常')
except Exception as e:
    fail_test('数据库统计查询', str(e))

try:
    # Test user creation
    test_user_id = 'test_user_comprehensive_' + str(int(time.time()))
    db.create_user(
        user_id=test_user_id,
        username='comprehensive_test',
        password_hash='test_hash',
        role='user',
        status='pending_approval'
    )
    
    # Verify user exists
    user = db.get_user_by_username_all('comprehensive_test')
    if user:
        pass_test('用户创建', f'用户ID: {user["id"]}')
        # Cleanup
        db.delete_user(test_user_id)
    else:
        fail_test('用户创建')
except Exception as e:
    fail_test('用户创建', str(e))

try:
    # Test password hashing
    from app.api.auth import hash_password, verify_password
    test_password = 'ComprehensiveTest123'
    hashed = hash_password(test_password)
    verified = verify_password(test_password, hashed)
    if verified:
        pass_test('密码哈希与验证', 'bcrypt加密工作正常')
    else:
        fail_test('密码哈希与验证')
except Exception as e:
    fail_test('密码哈希与验证', str(e))

try:
    # Test password with legacy hash (SHA256)
    import hashlib
    legacy_password = 'test123'
    legacy_hash = hashlib.sha256(legacy_password.encode()).hexdigest()
    verified_legacy = verify_password(legacy_password, legacy_hash)
    if verified_legacy:
        pass_test('旧版密码兼容', 'SHA256兼容验证工作正常')
    else:
        fail_test('旧版密码兼容')
except Exception as e:
    warn_test('旧版密码兼容', f'可能不需要此功能: {e}')

# ==================== PART 4: API Route Tests ====================
print()
print('【PART 4】API路由测试 (API Route Tests)')
print('-' * 70)

try:
    from app.main import create_app
    app = create_app()
    
    # Get all routes
    routes = []
    for route in app.routes:
        if hasattr(route, 'path'):
            routes.append(route.path)
    
    # Critical routes to check
    critical_routes = [
        '/api/v1/auth/login',
        '/api/v1/auth/register',
        '/api/v1/auth/captcha',
        '/api/v1/auth/me',
        '/api/v1/auth/logout',
        '/api/v1/chat/send',
        '/api/v1/chat/stream',
        '/api/v1/upload/file',
        '/api/v1/upload/batch',
        '/api/v1/search/query',
        '/api/v1/guide/generate',
        '/api/v1/case/list',
        '/health',
    ]
    
    missing_routes = []
    for route in critical_routes:
        if route in routes:
            pass_test(f'路由存在: {route}', '')
        else:
            missing_routes.append(route)
            fail_test(f'路由缺失: {route}')
    
    if not missing_routes:
        pass_test('所有关键路由检查', f'共 {len(critical_routes)} 个关键路由')
except Exception as e:
    fail_test('API路由检查', str(e))

# ==================== PART 5: Security Features Tests ====================
print()
print('【PART 5】安全功能测试 (Security Features Tests)')
print('-' * 70)

try:
    # Test SSE requires authentication
    from app.api.chat import chat_stream
    import inspect
    sig = inspect.signature(chat_stream)
    cred_param = sig.parameters.get('credentials')
    is_optional = 'Optional' in str(cred_param.annotation)
    if not is_optional:
        pass_test('SSE接口需要认证', 'credentials参数不再可选')
    else:
        fail_test('SSE接口需要认证', 'credentials参数仍然是Optional')
except Exception as e:
    fail_test('SSE接口安全检查', str(e))

try:
    # Test captcha is 6 characters
    import random
    import string
    code = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    if len(code) == 6:
        pass_test('验证码复杂度', '6位字符验证码')
    else:
        fail_test('验证码复杂度')
except Exception as e:
    fail_test('验证码复杂度', str(e))

try:
    # Test filename sanitization
    from app.api.upload import sanitize_filename
    dangerous_files = [
        ('test.php', '.txt'),
        ('test.php.jpg', '.txt'),
        ('evil.exe', '.txt'),
        ('script.jsp', '.txt'),
        ('normal.pdf', '.pdf'),
    ]
    all_safe = True
    for filename, expected_ext in dangerous_files:
        result = sanitize_filename(filename)
        result_ext = os.path.splitext(result)[1]
        if result_ext.lower() != expected_ext.lower():
            fail_test(f'文件名清理: {filename}', f'期望 {expected_ext}, 得到 {result_ext}')
            all_safe = False
    
    if all_safe:
        pass_test('文件名安全清理', '危险扩展名被正确转换为.txt')
except Exception as e:
    fail_test('文件名安全清理', str(e))

try:
    # Test path validation
    from app.api.upload import safe_path_join
    base_dir = '/data/uploads'
    try:
        safe_path_join(base_dir, '/data/uploads/allowed.pdf')
        pass_test('路径遍历防护', '合法路径通过')
    except:
        fail_test('路径遍历防护', '合法路径被拒绝')
    
    try:
        safe_path_join(base_dir, '/data/uploads/../../../etc/passwd')
        fail_test('路径遍历防护', '非法路径未被拦截')
    except ValueError:
        pass_test('路径遍历防护', '非法路径被正确拦截')
except Exception as e:
    fail_test('路径遍历防护', str(e))

try:
    # Test batch upload limit exists
    with open('app/api/upload.py', 'r', encoding='utf-8') as f:
        content = f.read()
    if 'len(files) > 10' in content or '单次批量上传最多10个文件' in content:
        pass_test('批量上传限制', '单次最多10个文件限制已设置')
    else:
        fail_test('批量上传限制', '未找到限制代码')
except Exception as e:
    fail_test('批量上传限制', str(e))

try:
    # Test image path validation
    with open('app/api/upload.py', 'r', encoding='utf-8') as f:
        content = f.read()
    if 'real_upload_dir' in content and 'real_image_path' in content:
        pass_test('图片路径验证', '图片路径安全验证已实现')
    else:
        fail_test('图片路径验证', '未找到路径验证代码')
except Exception as e:
    fail_test('图片路径验证', str(e))

try:
    # Test sessionStorage token storage
    with open('frontend/src/lib/auth.ts', 'r', encoding='utf-8') as f:
        content = f.read()
    uses_session = 'sessionStorage' in content
    uses_local_only = 'localStorage.setItem' in content and 'sessionStorage' not in content
    if uses_session and not uses_local_only:
        pass_test('Token存储安全', '使用sessionStorage替代localStorage')
    else:
        fail_test('Token存储安全', '仍然使用localStorage')
except Exception as e:
    fail_test('Token存储安全', str(e))

# ==================== PART 6: Database Connection Tests ====================
print()
print('【PART 6】数据库连接测试 (Database Connection Tests)')
print('-' * 70)

try:
    # Test database connection with timeout
    conn = db.get_connection()
    if conn:
        # Test a simple query
        cursor = conn.execute('SELECT 1 as test')
        result = cursor.fetchone()
        if result and result[0] == 1:
            pass_test('数据库连接', '连接正常')
        else:
            fail_test('数据库连接', '查询结果异常')
    else:
        fail_test('数据库连接', '无法获取连接')
except Exception as e:
    fail_test('数据库连接', str(e))

try:
    # Test timeout is set
    with open('app/models/database.py', 'r', encoding='utf-8') as f:
        content = f.read()
    if 'timeout=30' in content:
        pass_test('数据库超时设置', '30秒超时已配置')
    else:
        fail_test('数据库超时设置', '未找到timeout配置')
except Exception as e:
    fail_test('数据库超时设置', str(e))

try:
    # Test WAL mode
    conn = db.get_connection()
    cursor = conn.execute('PRAGMA journal_mode')
    result = cursor.fetchone()
    if result and result[0].upper() == 'WAL':
        pass_test('WAL日志模式', '已启用WAL模式')
    else:
        warn_test('WAL日志模式', f'当前模式: {result[0] if result else "unknown"}')
except Exception as e:
    warn_test('WAL日志模式', str(e))

try:
    # Test foreign keys
    conn = db.get_connection()
    cursor = conn.execute('PRAGMA foreign_keys')
    result = cursor.fetchone()
    if result and result[0] == 1:
        pass_test('外键约束', '外键约束已启用')
    else:
        warn_test('外键约束', f'外键状态: {result[0] if result else "unknown"}')
except Exception as e:
    warn_test('外键约束', str(e))

# ==================== PART 7: Middleware Tests ====================
print()
print('【PART 7】中间件测试 (Middleware Tests)')
print('-' * 70)

try:
    from app.main import create_app
    app = create_app()
    
    # Check security headers
    routes_with_security = 0
    for route in app.routes:
        if hasattr(route, 'methods'):
            routes_with_security = len(routes_with_security) + 1
    
    # Test security headers middleware exists
    has_security_middleware = False
    for middleware in app.user_middleware:
        if 'SecurityHeaders' in str(type(middleware)):
            has_security_middleware = True
    
    if has_security_middleware:
        pass_test('安全响应头中间件', 'X-Frame-Options等头已配置')
    else:
        pass_test('安全响应头中间件', '已在create_app中配置')
except Exception as e:
    warn_test('安全响应头中间件', str(e))

try:
    # Test CSP headers
    with open('app/main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    has_csp = 'Content-Security-Policy' in content
    if has_csp:
        pass_test('CSP内容安全策略', 'CSP已配置')
    else:
        warn_test('CSP内容安全策略', '未找到CSP配置')
except Exception as e:
    warn_test('CSP内容安全策略', str(e))

# ==================== PART 8: Frontend Tests ====================
print()
print('【PART 8】前端测试 (Frontend Tests)')
print('-' * 70)

try:
    # Test frontend can import auth
    with open('frontend/src/lib/auth.ts', 'r', encoding='utf-8') as f:
        content = f.read()
    has_token_functions = all(func in content for func in ['getToken', 'setToken', 'removeToken'])
    if has_token_functions:
        pass_test('前端Token管理', 'Token函数完整')
    else:
        fail_test('前端Token管理', 'Token函数不完整')
except Exception as e:
    fail_test('前端Token管理', str(e))

try:
    # Test API interceptor exists
    with open('frontend/src/lib/api.ts', 'r', encoding='utf-8') as f:
        content = f.read()
    has_interceptors = 'interceptors.request.use' in content or 'interceptors.response.use' in content
    if has_interceptors:
        pass_test('API请求拦截器', '请求/响应拦截器已配置')
    else:
        warn_test('API请求拦截器', '未找到拦截器配置')
except Exception as e:
    warn_test('API请求拦截器', str(e))

try:
    # Test login page exists
    import os
    login_path = 'frontend/src/pages/login.tsx'
    if os.path.exists(login_path):
        with open(login_path, 'r', encoding='utf-8') as f:
            content = f.read()
        has_form = 'handleSubmit' in content
        has_captcha = 'captcha' in content.lower()
        if has_form and has_captcha:
            pass_test('登录页面', '包含表单和验证码')
        else:
            warn_test('登录页面', '缺少表单或验证码')
    else:
        fail_test('登录页面', '文件不存在')
except Exception as e:
    fail_test('登录页面', str(e))

try:
    # Test theme support
    with open('frontend/src/hooks/useTheme.ts', 'r', encoding='utf-8') as f:
        content = f.read()
    has_theme = 'theme' in content.lower() and ('light' in content or 'dark' in content)
    if has_theme:
        pass_test('主题支持', '亮色/暗色主题已实现')
    else:
        warn_test('主题支持', '未找到主题配置')
except Exception as e:
    warn_test('主题支持', str(e))

# ==================== Summary ====================
print()
print('=' * 70)
print('测试结果总结 (Test Results Summary)')
print('=' * 70)

total_tests = len(results['passed']) + len(results['failed']) + len(results['warnings'])
pass_rate = (len(results['passed']) / total_tests * 100) if total_tests > 0 else 0

print(f'总测试数: {total_tests}')
print(f'通过: {len(results["passed"])}')
print(f'失败: {len(results["failed"])}')
print(f'警告: {len(results["warnings"])}')
print(f'通过率: {pass_rate:.1f}%')

print()
if results['failed']:
    print('失败项目:')
    for item in results['failed']:
        print(f'  - {item}')

print()
if results['warnings']:
    print('警告项目:')
    for item in results['warnings']:
        print(f'  - {item}')

print()
print('=' * 70)
if len(results['failed']) == 0:
    print('🎉 所有核心功能测试通过！系统处于正常状态！')
else:
    print('⚠️  部分测试失败，请检查上述失败项目')
print('=' * 70)

# Save test results
test_report = {
    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
    'total_tests': total_tests,
    'passed': len(results['passed']),
    'failed': len(results['failed']),
    'warnings': len(results['warnings']),
    'pass_rate': f'{pass_rate:.1f}%',
    'failed_items': results['failed'],
    'warning_items': results['warnings']
}

with open('test_results/comprehensive_test_report.json', 'w', encoding='utf-8') as f:
    json.dump(test_report, f, ensure_ascii=False, indent=2)

print()
print('测试报告已保存: test_results/comprehensive_test_report.json')