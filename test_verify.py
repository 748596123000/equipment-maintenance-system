import sqlite3, bcrypt, logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

conn = sqlite3.connect('data/app.db')
cur = conn.cursor()

cur.execute('SELECT * FROM users WHERE username = ?', ('admin',))
row = cur.fetchone()
if row:
    logger.info(f'Found user: {row[0]}, {row[1]}')
    logger.info(f'Hash: {row[2][:50]}...')
    
    # Try verify
    test_pwd = 'admin123'
    try:
        result = bcrypt.checkpw(test_pwd.encode('utf-8'), row[2].encode('utf-8'))
        logger.info(f'Password verify result: {result}')
    except Exception as e:
        logger.error(f'Verify error: {e}')
else:
    logger.warning('User not found')

conn.close()