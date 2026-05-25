"""
pytest配置文件

配置pytest以正确处理Unicode字符
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')