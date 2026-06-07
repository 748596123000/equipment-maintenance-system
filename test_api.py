import requests
import json
from app.models.database import get_database
from datetime import datetime, timezone, timedelta
import secrets

db = get_database()
conn = db.get_connection()
token = secrets.token_hex(32)
expires = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
admin = conn.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1").fetchone()
if admin:
    conn.execute("INSERT INTO auth_tokens (token, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)", (token, admin["id"], expires, datetime.now().isoformat()))
    conn.commit()
    print(f"Token: {token}")

    headers = {"Authorization": f"Bearer {token}"}

    r = requests.get("http://localhost:8000/api/v1/knowledge-graph/available-documents", headers=headers)
    print("Available documents:")
    print(json.dumps(r.json(), indent=2, ensure_ascii=False))

    r2 = requests.get("http://localhost:8000/api/v1/knowledge-graph/stats", headers=headers)
    print("\nStats:")
    print(json.dumps(r2.json(), indent=2, ensure_ascii=False))
else:
    print("NO ADMIN")
