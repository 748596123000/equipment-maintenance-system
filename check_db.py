import sys
sys.path.insert(0, '.')
from app.models.database import get_database

db = get_database()
conn = db.get_connection()
tables = [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print('Tables:', tables)

# Check if users table exists and has data
try:
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    print(f'Users count: {count}')

    # Check columns
    cols = conn.execute("PRAGMA table_info(users)").fetchall()
    print('Users columns:', [c[1] for c in cols])

    # Check logs
    logs_count = conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
    print(f'Logs count: {logs_count}')

    # Logs columns
    logs_cols = conn.execute("PRAGMA table_info(logs)").fetchall()
    print('Logs columns:', [c[1] for c in logs_cols])

    # Sample data
    users = conn.execute("SELECT id, username, role, is_active FROM users").fetchall()
    print('Users:', users)

    logs = conn.execute("SELECT * FROM logs LIMIT 5").fetchall()
    print('Sample logs:', logs)
except Exception as e:
    import traceback
    print(f'Error: {e}')
    traceback.print_exc()