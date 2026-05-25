import requests

print('=== 检查验证码接口 ===')

# 检查正确的API路径
for path in ['/api/v1/auth/captcha', '/api/auth/captcha']:
    try:
        r = requests.get(f'http://127.0.0.1:8000{path}', timeout=10)
        print(f'{path}: {r.status_code}')
        if r.status_code == 200:
            data = r.json()
            print(f'  response: {data}')
        else:
            print(f'  error: {r.text[:200]}')
    except Exception as e:
        print(f'{path} Error: {e}')