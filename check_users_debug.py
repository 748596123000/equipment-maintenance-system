import sqlite3

conn = sqlite3.connect('data/app.db')
cur = conn.cursor()

cur.execute('SELECT id, username, password_hash, role, is_active, status FROM users')
rows = cur.fetchall()
print('Users in DB:')
for row in rows:
    print(f'  ID={row[0]}, username={row[1]}, role={row[3]}, active={row[4]}, status={row[5]}')
    print(f'  hash: {row[2][:30]}...')

conn.close()