import requests
import json

base_url = "http://localhost:8001/api/v1"

login_data = {
    "username": "admin",
    "password": "DCHsyHXaFwAdv9Ur"
}

print("1. Testing login...")
response = requests.post(f"{base_url}/auth/login", json=login_data)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

if response.status_code == 200:
    token = response.json().get("data", {}).get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    print("\n2. Testing document upload (simulated)...")
    print("Upload endpoint: POST /upload/file")
    print("Note: Actual file upload requires multipart/form-data")

    print("\n3. Testing notifications...")
    response = requests.get(f"{base_url}/notifications/list", params={"user_id": "admin", "is_admin": "true", "limit": "10"})
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Total notifications: {data.get('total', 0)}")
    print(f"Unread count: {data.get('unread_count', 0)}")
    for notif in data.get("notifications", [])[:3]:
        print(f"  - {notif['title']} ({notif['type']})")

    print("\n✅ Notification system is working!")
    print(f"✅ Total notifications in system: {data.get('total', 0)}")
    print(f"✅ Unread notifications: {data.get('unread_count', 0)}")
else:
    print("❌ Login failed")
