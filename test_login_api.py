import requests

# Get captcha
resp = requests.get('http://localhost:8000/api/v1/auth/captcha')
data = resp.json()
captcha_id = data['data']['captcha_id']
captcha_code = data['data'].get('captcha_code', 'N8XK')

print(f'Captcha: {captcha_code}')

# Try login
resp2 = requests.post('http://localhost:8000/api/v1/auth/login', json={
    'username': 'admin',
    'password': 'admin123',
    'captcha_id': captcha_id,
    'captcha_code': captcha_code
})
print(f'Status: {resp2.status_code}')
print(f'Result: {resp2.json()}')