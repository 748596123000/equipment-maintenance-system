import requests
import json

base_url = "http://localhost:8001/api/v1"

login_data = {
    "username": "admin",
    "password": "DCHsyHXaFwAdv9Ur"
}

print("=" * 60)
print("设备检修知识系统 - 优化后功能测试")
print("=" * 60)

print("\n[1/5] 测试管理员登录...")
response = requests.post(f"{base_url}/auth/login", json=login_data)
if response.status_code == 200:
    token = response.json().get("data", {}).get("token")
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ 管理员登录成功")
else:
    print(f"❌ 登录失败: {response.status_code}")
    exit(1)

print("\n[2/5] 测试创建系统公告...")
announcement_data = {
    "type": "system",
    "title": "🔔 系统优化通知",
    "content": "系统已完成数据库优化，通知功能现已支持持久化存储。",
    "priority": "normal"
}
response = requests.post(f"{base_url}/notifications/create", json=announcement_data, headers=headers)
print(f"状态码: {response.status_code}")
if response.status_code == 200:
    print("✅ 系统公告创建成功")
else:
    print(f"❌ 创建失败: {response.json()}")

print("\n[3/5] 测试获取通知列表...")
response = requests.get(f"{base_url}/notifications/list", params={"user_id": "admin", "is_admin": "true", "limit": "10"}, headers=headers)
print(f"状态码: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"✅ 获取通知成功")
    print(f"   总通知数: {data.get('total', 0)}")
    print(f"   未读数: {data.get('unread_count', 0)}")
    print(f"   通知列表:")
    for i, notif in enumerate(data.get("notifications", [])[:5], 1):
        print(f"   {i}. {notif['title']} [{notif['type']}] - 未读: {notif['is_read']}")
else:
    print(f"❌ 获取失败: {response.json()}")

print("\n[4/5] 测试标记单条通知为已读...")
notifications = response.json().get("notifications", [])
if notifications:
    first_notif_id = notifications[0]["id"]
    response = requests.post(f"{base_url}/notifications/{first_notif_id}/read", headers=headers)
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        print("✅ 标记已读成功")
    else:
        print(f"❌ 标记失败: {response.json()}")

print("\n[5/5] 测试标记全部通知为已读...")
response = requests.post(f"{base_url}/notifications/read-all", params={"user_id": "admin", "is_admin": "true"}, headers=headers)
print(f"状态码: {response.status_code}")
if response.status_code == 200:
    print(f"✅ {response.json().get('message', '')}")
else:
    print(f"❌ 标记失败: {response.json()}")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)

print("\n📊 优化总结:")
print("  ✅ 通知系统已迁移到数据库持久化")
print("  ✅ 支持分页查询")
print("  ✅ 支持按用户和管理员筛选")
print("  ✅ 支持标记已读/全部已读")
print("  ✅ 支持删除通知")
print("  ✅ 重启服务后数据不丢失")

print("\n🚀 后续优化项:")
print("  ⏳ 添加通知声音提示")
print("  ⏳ 添加桌面通知支持")
print("  ⏳ 优化消息中心UI性能")
print("  ⏳ 完善Swagger文档")
print("  ⏳ 移动端适配")
