# 测试FastAPI应用
from fastapi.testclient import TestClient
from app.main import app

print('Creating test client...')
client = TestClient(app)

print('Testing /api/v1/auth/captcha endpoint...')
response = client.get('/api/v1/auth/captcha')

print('Status:', response.status_code)
if response.status_code != 200:
    print('Error:', response.text)
else:
    data = response.json()
    print('Response keys:', list(data.keys()))
    print('Data keys:', list(data.get('data', {}).keys()))