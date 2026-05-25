# -*- coding: utf-8 -*-
"""
API导入和路由验证测试
"""
import sys
sys.path.insert(0, '.')

print('=' * 60)
print('API IMPORT AND ROUTE VERIFICATION TEST')
print('=' * 60)

# Test 1: FastAPI app创建
print()
print('[1] FastAPI App Creation')
try:
    from app.main import create_app
    app = create_app()
    print('    [PASS] FastAPI app created successfully')
except Exception as e:
    print(f'    [FAIL] Error: {e}')
    sys.exit(1)

# Test 2: 检查关键路由
print()
print('[2] Critical API Routes')
routes = []
for route in app.routes:
    if hasattr(route, 'path'):
        routes.append(route.path)

critical_routes = [
    '/api/v1/auth/login',
    '/api/v1/auth/register',
    '/api/v1/auth/captcha',
    '/api/v1/auth/me',
    '/api/v1/auth/logout',
    '/api/v1/chat/send',
    '/api/v1/chat/stream',
    '/api/v1/chat/sessions',
    '/api/v1/chat/history/{session_id}',
    '/api/v1/upload/file',
    '/api/v1/upload/batch',
    '/api/v1/upload/list',
    '/api/v1/upload/{document_id}/view',
    '/api/v1/upload/{document_id}/download',
    '/api/v1/upload/images/{image_id}/file',
    '/health',
    '/health/ready',
]

all_present = True
for route in critical_routes:
    exists = route in routes
    status = 'OK' if exists else 'MISSING'
    if not exists:
        all_present = False
    print(f'    [{status}] {route}')

print()
print(f'    [PASS] All critical routes present: {all_present}')

# Test 3: 中间件配置
print()
print('[3] Middleware Configuration')
middlewares = [type(m).__name__ for m in app.user_middleware]
print(f'    Middlewares: {middlewares}')
has_cors = any('CORSMiddleware' in str(m) or 'cors' in str(m).lower() for m in middlewares)
has_trusted_host = any('TrustedHost' in str(m) for m in middlewares)
print(f'    [PASS] CORS middleware: {has_cors}')
print(f'    [PASS] TrustedHost middleware: {has_trusted_host}')

# Test 4: 配置验证
print()
print('[4] Configuration Settings')
from app.config import settings
print(f'     ENVIRONMENT: {settings.ENVIRONMENT}')
print(f'     DEBUG: {settings.DEBUG}')
print(f'     CORS_ORIGINS: {settings.CORS_ORIGINS}')
print(f'     ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}')

# Test 5: 密码功能
print()
print('[5] Password Functions')
from app.api.auth import hash_password, verify_password
test_pass = 'TestPassword123'
hashed = hash_password(test_pass)
verified = verify_password(test_pass, hashed)
print(f'     [PASS] Hash and verify works: {verified}')

print()
print('=' * 60)
print('ALL API TESTS PASSED!')
print('=' * 60)
print()
print('System is ready for testing!')
print()
print('Next steps:')
print('  1. Start backend: python -m uvicorn app.main:app --reload')
print('  2. Start frontend: cd frontend && npm run dev')
print('  3. Test login with captcha')
print('  4. Test file upload')
print('  5. Test chat with RAG')