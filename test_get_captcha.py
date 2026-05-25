# 直接导入auth模块测试
from app.api.auth import get_captcha
import asyncio

print('Testing get_captcha directly...')
async def test():
    try:
        result = await get_captcha()
        print('Result keys:', list(result.keys()))
        print('Data keys:', list(result.get('data', {}).keys()))
        return result
    except Exception as e:
        print('Error:', type(e).__name__, ':', e)
        import traceback
        traceback.print_exc()
        return None

asyncio.run(test())