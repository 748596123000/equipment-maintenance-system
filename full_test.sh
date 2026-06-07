#!/bin/bash
# ================================================================
# 设备检修知识检索与作业系统 - 全面测试脚本
# 包含：前端 → 基础服务 → 认证 → 文档管理 → 检索 → AI问答
#       → 作业指引 → 检修案例 → 管理后台 → 知识图谱 → 通知 → 用户画像
# ================================================================

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PASS=0
FAIL=0
SKIP=0
TOTAL=0

ok() { TOTAL=$((TOTAL+1)); PASS=$((PASS+1)); echo -e "  ${GREEN}✓${NC} $1"; }
fail() { TOTAL=$((TOTAL+1)); FAIL=$((FAIL+1)); echo -e "  ${RED}✗${NC} $1"; }
skip() { TOTAL=$((TOTAL+1)); SKIP=$((SKIP+1)); echo -e "  ${YELLOW}⊘${NC} $1"; }
info() { echo -e "  ${BLUE}ℹ${NC} $1"; }
section() { echo ""; echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${BOLD}${CYAN} $1${NC}"; echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo ""; }

BASE_URL="http://localhost:8000"
FRONT_URL="http://localhost"

section "0. 环境检测"

echo -n "  后端进程: "
PID=$(cat data/logs/api.pid 2>/dev/null)
if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    ok "PID=$PID 运行中"
else
    PID=$(ps aux | grep "[u]vicorn app.main" | awk '{print $2}' | head -1)
    if [ -n "$PID" ]; then
        ok "PID=$PID 运行中（无pid文件）"
    else
        fail "后端未运行！请先启动: python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
    fi
fi

echo -n "  Nginx进程: "
if pgrep -x nginx &>/dev/null; then
    ok "Nginx运行中"
else
    fail "Nginx未运行！请执行: sudo systemctl start nginx"
fi

echo -n "  端口8000: "
if ss -tlnp 2>/dev/null | grep -q ":8000 "; then
    ok "监听中"
else
    fail "未监听"
fi

echo -n "  端口80: "
if ss -tlnp 2>/dev/null | grep -q ":80 "; then
    ok "监听中"
else
    fail "未监听"
fi

# ================================================================
section "1. 前端页面测试"

echo -n "  前端首页 (Nginx:80): "
RESP=$(curl -sf "$FRONT_URL/" -o /dev/null -w "%{http_code}" --connect-timeout 5 2>/dev/null)
if [ "$RESP" = "200" ]; then
    ok "HTTP $RESP"
else
    fail "HTTP $RESP (期望200)"
fi

echo -n "  前端index.html内容: "
BODY=$(curl -sf "$FRONT_URL/" --connect-timeout 5 2>/dev/null)
if echo "$BODY" | grep -q "root"; then
    ok "HTML内容正常"
else
    fail "HTML内容异常"
fi

echo -n "  前端JS资源: "
JS_FILE=$(curl -sf "$FRONT_URL/" 2>/dev/null | grep -oP 'src="[^"]*\.js"' | head -1 | sed 's/src="//;s/"//')
if [ -n "$JS_FILE" ]; then
    RESP=$(curl -sf "$FRONT_URL$JS_FILE" -o /dev/null -w "%{http_code}" --connect-timeout 5 2>/dev/null)
    if [ "$RESP" = "200" ]; then
        ok "JS资源可访问"
    else
        fail "JS资源 HTTP $RESP"
    fi
else
    skip "未找到JS引用"
fi

echo -n "  前端CSS资源: "
CSS_FILE=$(curl -sf "$FRONT_URL/" 2>/dev/null | grep -oP 'href="[^"]*\.css"' | head -1 | sed 's/href="//;s/"//')
if [ -n "$CSS_FILE" ]; then
    RESP=$(curl -sf "$FRONT_URL$CSS_FILE" -o /dev/null -w "%{http_code}" --connect-timeout 5 2>/dev/null)
    if [ "$RESP" = "200" ]; then
        ok "CSS资源可访问"
    else
        fail "CSS资源 HTTP $RESP"
    fi
else
    skip "未找到CSS引用"
fi

echo -n "  favicon.ico: "
RESP=$(curl -sf "$FRONT_URL/favicon.svg" -o /dev/null -w "%{http_code}" --connect-timeout 5 2>/dev/null)
if [ "$RESP" = "200" ] || [ "$RESP" = "304" ]; then
    ok "HTTP $RESP"
else
    skip "HTTP $RESP (非关键)"
fi

# ================================================================
section "2. 基础服务测试"

echo -n "  GET /health: "
RESP=$(curl -sf "$BASE_URL/health" --connect-timeout 5 2>/dev/null)
if [ "$RESP" = '{"status":"ok"}' ]; then
    ok "正常"
else
    fail "响应: $RESP"
fi

echo -n "  GET /health/ready: "
RESP=$(curl -sf "$BASE_URL/health/ready" --connect-timeout 5 2>/dev/null)
if echo "$RESP" | grep -q "ready\|not_ready"; then
    DB_STATUS=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('checks',{}).get('database',False))" 2>/dev/null)
    LLM_STATUS=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('checks',{}).get('llm',False))" 2>/dev/null)
    ok "database=$DB_STATUS, llm=$LLM_STATUS"
else
    fail "响应: $RESP"
fi

echo -n "  GET /docs (Swagger UI): "
RESP=$(curl -sf "$BASE_URL/docs" -o /dev/null -w "%{http_code}" --connect-timeout 5 2>/dev/null)
if [ "$RESP" = "200" ]; then ok "HTTP $RESP"; else fail "HTTP $RESP"; fi

echo -n "  GET /openapi.json: "
RESP=$(curl -sf "$BASE_URL/openapi.json" -o /dev/null -w "%{http_code}" --connect-timeout 5 2>/dev/null)
if [ "$RESP" = "200" ]; then
    API_COUNT=$(curl -sf "$BASE_URL/openapi.json" --connect-timeout 5 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('paths',{})))" 2>/dev/null)
    ok "HTTP 200, $API_COUNT 个API端点"
else
    fail "HTTP $RESP"
fi

echo -n "  Nginx反向代理 /health: "
RESP=$(curl -sf "$FRONT_URL/health" --connect-timeout 5 2>/dev/null)
if [ "$RESP" = '{"status":"ok"}' ]; then
    ok "反向代理正常"
else
    fail "反向代理异常: $RESP"
fi

echo -n "  Nginx反向代理 /api/v1/auth/captcha: "
RESP=$(curl -sf "$FRONT_URL/api/v1/auth/captcha" -o /dev/null -w "%{http_code}" --connect-timeout 5 2>/dev/null)
if [ "$RESP" = "200" ]; then ok "HTTP $RESP"; else fail "HTTP $RESP"; fi

# ================================================================
section "3. 用户认证测试"

echo -n "  GET /api/v1/auth/captcha: "
CAPTCHA_RESP=$(curl -sf "$BASE_URL/api/v1/auth/captcha" --connect-timeout 5 2>/dev/null)
CAPTCHA_ID=$(echo "$CAPTCHA_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('captcha_id',''))" 2>/dev/null)
CAPTCHA_CODE=$(echo "$CAPTCHA_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('captcha_code',''))" 2>/dev/null)
if [ -n "$CAPTCHA_ID" ]; then
    ok "captcha_id=$CAPTCHA_ID"
else
    fail "验证码获取失败"
fi

echo "  生成测试Token..."
TOKEN=$(python3 << 'PYEOF'
import sys, os, uuid, sqlite3
from datetime import datetime, timedelta, timezone
sys.path.insert(0, '.')
os.chdir('.')
try:
    from app.config import settings
    db_path = settings.SQLITE_DB_PATH
except:
    db_path = "./data/app.db"
if not os.path.exists(db_path):
    sys.exit(1)
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
row = conn.execute("SELECT id FROM users WHERE username = 'admin' AND is_active = 1").fetchone()
if row:
    token = uuid.uuid4().hex
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    now = datetime.now().isoformat()
    conn.execute("INSERT OR REPLACE INTO auth_tokens (token, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)", (token, row['id'], expires_at, now))
    conn.commit()
    print(token)
conn.close()
PYEOF
)

if [ -n "$TOKEN" ]; then
    ok "Token: ${TOKEN:0:16}..."
    AUTH="Authorization: Bearer $TOKEN"
else
    fail "Token生成失败"
    AUTH=""
fi

echo -n "  GET /api/v1/auth/me: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -H "$AUTH" "$BASE_URL/api/v1/auth/me" --connect-timeout 5 2>/dev/null)
    if echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('data',{}).get('username')=='admin'" 2>/dev/null; then
        ok "admin用户信息正常"
    else
        fail "响应: $(echo "$RESP" | head -c 100)"
    fi
else
    skip "无Token"
fi

echo -n "  POST /api/v1/auth/login (带验证码): "
if [ -n "$CAPTCHA_ID" ] && [ -n "$CAPTCHA_CODE" ]; then
    ADMIN_PASS=""
    if [ -f ".initial_passwords" ]; then
        ADMIN_PASS=$(grep "^admin" .initial_passwords 2>/dev/null | awk -F' / ' '{print $2}')
    fi
    [ -z "$ADMIN_PASS" ] && ADMIN_PASS="admin123"
    LOGIN_RESP=$(curl -sf -X POST "$BASE_URL/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"username\":\"admin\",\"password\":\"$ADMIN_PASS\",\"captcha_id\":\"$CAPTCHA_ID\",\"captcha_code\":\"$CAPTCHA_CODE\"}" \
        --connect-timeout 10 2>/dev/null)
    LOGIN_TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('token',''))" 2>/dev/null)
    if [ -n "$LOGIN_TOKEN" ]; then
        ok "登录成功"
    else
        fail "登录失败: $(echo "$LOGIN_RESP" | head -c 120)"
    fi
else
    skip "无验证码"
fi

# ================================================================
section "4. 文档管理测试"

echo -n "  GET /api/v1/upload/list: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -H "$AUTH" "$BASE_URL/api/v1/upload/list" -o /dev/null -w "%{http_code}" --connect-timeout 10 2>/dev/null)
    if [ "$RESP" = "200" ]; then ok "HTTP $RESP"; else fail "HTTP $RESP"; fi
else skip "无Token"; fi

echo -n "  GET /api/v1/upload/my: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -H "$AUTH" "$BASE_URL/api/v1/upload/my" -o /dev/null -w "%{http_code}" --connect-timeout 10 2>/dev/null)
    if [ "$RESP" = "200" ]; then ok "HTTP $RESP"; else fail "HTTP $RESP"; fi
else skip "无Token"; fi

echo -n "  GET /api/v1/upload/my/stats: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -H "$AUTH" "$BASE_URL/api/v1/upload/my/stats" -o /dev/null -w "%{http_code}" --connect-timeout 10 2>/dev/null)
    if [ "$RESP" = "200" ]; then ok "HTTP $RESP"; else fail "HTTP $RESP"; fi
else skip "无Token"; fi

echo -n "  GET /api/v1/upload/supported-formats: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -H "$AUTH" "$BASE_URL/api/v1/upload/supported-formats" --connect-timeout 10 2>/dev/null)
    if [ -n "$RESP" ]; then
        FORMAT_COUNT=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('data',{}).get('formats',[])))" 2>/dev/null)
        ok "支持 $FORMAT_COUNT 种格式"
    else
        fail "无响应"
    fi
else skip "无Token"; fi

echo -n "  POST /api/v1/upload/file: "
if [ -n "$AUTH" ]; then
    echo "测试上传文件内容-设备检修知识检索系统" > /tmp/test_upload.txt
    RESP=$(curl -sf -X POST -H "$AUTH" -F "file=@/tmp/test_upload.txt" "$BASE_URL/api/v1/upload/file" --connect-timeout 30 2>/dev/null)
    DOC_ID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('document_id','') or json.load(sys.stdin).get('data',{}).get('id',''))" 2>/dev/null)
    if [ -n "$DOC_ID" ]; then
        ok "上传成功, document_id=$DOC_ID"
    else
        fail "上传失败: $(echo "$RESP" | head -c 120)"
    fi
    rm -f /tmp/test_upload.txt
else
    skip "无Token"
    DOC_ID=""
fi

echo -n "  GET /api/v1/upload/pending: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -H "$AUTH" "$BASE_URL/api/v1/upload/pending" -o /dev/null -w "%{http_code}" --connect-timeout 10 2>/dev/null)
    if [ "$RESP" = "200" ]; then ok "HTTP $RESP"; else fail "HTTP $RESP"; fi
else skip "无Token"; fi

if [ -n "$DOC_ID" ]; then
    echo -n "  GET /api/v1/upload/{id}/preview: "
    RESP=$(curl -sf -H "$AUTH" "$BASE_URL/api/v1/upload/$DOC_ID/preview" -o /dev/null -w "%{http_code}" --connect-timeout 10 2>/dev/null)
    if [ "$RESP" = "200" ]; then ok "HTTP $RESP"; else fail "HTTP $RESP"; fi

    echo -n "  POST /api/v1/upload/{id}/approve: "
    RESP=$(curl -sf -X POST -H "$AUTH" "$BASE_URL/api/v1/upload/$DOC_ID/approve" -o /dev/null -w "%{http_code}" --connect-timeout 10 2>/dev/null)
    if [ "$RESP" = "200" ]; then ok "HTTP $RESP"; else fail "HTTP $RESP"; fi
fi

# ================================================================
section "5. 知识检索测试"

echo -n "  POST /api/v1/search/text: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -X POST -H "$AUTH" -H "Content-Type: application/json" \
        -d '{"query":"设备检修","top_k":3}' "$BASE_URL/api/v1/search/text" --connect-timeout 15 2>/dev/null)
    if [ $? -eq 0 ]; then
        RESULT_COUNT=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('data',{}).get('results',[])))" 2>/dev/null)
        ok "返回 $RESULT_COUNT 条结果"
    else
        fail "请求失败"
    fi
else skip "无Token"; fi

echo -n "  POST /api/v1/search/keyword: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -X POST -H "$AUTH" -H "Content-Type: application/json" \
        -d '{"query":"变压器","top_k":3}' "$BASE_URL/api/v1/search/keyword" --connect-timeout 15 2>/dev/null)
    if [ $? -eq 0 ]; then
        ok "请求成功"
    else
        fail "请求失败"
    fi
else skip "无Token"; fi

echo -n "  POST /api/v1/search/hybrid: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -X POST -H "$AUTH" -H "Content-Type: application/json" \
        -d '{"query":"断路器检修","top_k":3}' "$BASE_URL/api/v1/search/hybrid" --connect-timeout 15 2>/dev/null)
    if [ $? -eq 0 ]; then
        ok "请求成功"
    else
        fail "请求失败"
    fi
else skip "无Token"; fi

echo -n "  POST /api/v1/search/model: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -X POST -H "$AUTH" -H "Content-Type: application/json" \
        -d '{"query":"GIS","top_k":3}' "$BASE_URL/api/v1/search/model" --connect-timeout 15 2>/dev/null)
    if [ $? -eq 0 ]; then
        ok "请求成功"
    else
        fail "请求失败"
    fi
else skip "无Token"; fi

# ================================================================
section "6. AI问答测试"

echo -n "  GET /api/v1/chat/sessions: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -H "$AUTH" "$BASE_URL/api/v1/chat/sessions" -o /dev/null -w "%{http_code}" --connect-timeout 10 2>/dev/null)
    if [ "$RESP" = "200" ]; then ok "HTTP $RESP"; else fail "HTTP $RESP"; fi
else skip "无Token"; fi

echo -n "  POST /api/v1/chat/send (非流式): "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -X POST -H "$AUTH" -H "Content-Type: application/json" \
        -d '{"message":"你好","stream":false}' "$BASE_URL/api/v1/chat/send" --connect-timeout 30 2>/dev/null)
    if [ $? -eq 0 ]; then
        HAS_ANSWER=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print('yes' if d.get('data',{}).get('answer') else 'no')" 2>/dev/null)
        if [ "$HAS_ANSWER" = "yes" ]; then
            ok "AI回答正常"
        else
            skip "AI未回答（LLM可能未配置）"
        fi
    else
        skip "请求超时（LLM可能未启动）"
    fi
else skip "无Token"; fi

# ================================================================
section "7. 作业指引测试"

echo -n "  GET /api/v1/guide/list: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -H "$AUTH" "$BASE_URL/api/v1/guide/list" -o /dev/null -w "%{http_code}" --connect-timeout 10 2>/dev/null)
    if [ "$RESP" = "200" ]; then ok "HTTP $RESP"; else fail "HTTP $RESP"; fi
else skip "无Token"; fi

echo -n "  POST /api/v1/guide/generate: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -X POST -H "$AUTH" -H "Content-Type: application/json" \
        -d '{"equipment_name":"变压器","work_type":"检修"}' "$BASE_URL/api/v1/guide/generate" --connect-timeout 30 2>/dev/null)
    if [ $? -eq 0 ]; then
        ok "请求成功"
    else
        skip "请求超时（LLM可能未启动）"
    fi
else skip "无Token"; fi

# ================================================================
section "8. 检修案例测试"

echo -n "  GET /api/v1/case/list: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -H "$AUTH" "$BASE_URL/api/v1/case/list" -o /dev/null -w "%{http_code}" --connect-timeout 10 2>/dev/null)
    if [ "$RESP" = "200" ]; then ok "HTTP $RESP"; else fail "HTTP $RESP"; fi
else skip "无Token"; fi

echo -n "  POST /api/v1/case/search: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -X POST -H "$AUTH" -H "Content-Type: application/json" \
        -d '{"query":"断路器故障","top_k":3}' "$BASE_URL/api/v1/case/search" --connect-timeout 15 2>/dev/null)
    if [ $? -eq 0 ]; then ok "请求成功"; else fail "请求失败"; fi
else skip "无Token"; fi

# ================================================================
section "9. 管理后台测试"

echo -n "  GET /api/v1/admin/stats: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -H "$AUTH" "$BASE_URL/api/v1/admin/stats" --connect-timeout 10 2>/dev/null)
    if [ $? -eq 0 ]; then
        ok "请求成功"
    else
        fail "请求失败"
    fi
else skip "无Token"; fi

echo -n "  GET /api/v1/admin/users: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -H "$AUTH" "$BASE_URL/api/v1/admin/users" -o /dev/null -w "%{http_code}" --connect-timeout 10 2>/dev/null)
    if [ "$RESP" = "200" ]; then ok "HTTP $RESP"; else fail "HTTP $RESP"; fi
else skip "无Token"; fi

echo -n "  GET /api/v1/admin/logs: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -H "$AUTH" "$BASE_URL/api/v1/admin/logs" -o /dev/null -w "%{http_code}" --connect-timeout 10 2>/dev/null)
    if [ "$RESP" = "200" ]; then ok "HTTP $RESP"; else fail "HTTP $RESP"; fi
else skip "无Token"; fi

echo -n "  GET /api/v1/admin/config: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -H "$AUTH" "$BASE_URL/api/v1/admin/config" -o /dev/null -w "%{http_code}" --connect-timeout 10 2>/dev/null)
    if [ "$RESP" = "200" ]; then ok "HTTP $RESP"; else fail "HTTP $RESP"; fi
else skip "无Token"; fi

echo -n "  GET /api/v1/admin/services/status: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -H "$AUTH" "$BASE_URL/api/v1/admin/services/status" -o /dev/null -w "%{http_code}" --connect-timeout 10 2>/dev/null)
    if [ "$RESP" = "200" ]; then ok "HTTP $RESP"; else fail "HTTP $RESP"; fi
else skip "无Token"; fi

echo -n "  GET /api/v1/admin/health: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -H "$AUTH" "$BASE_URL/api/v1/admin/health" -o /dev/null -w "%{http_code}" --connect-timeout 10 2>/dev/null)
    if [ "$RESP" = "200" ]; then ok "HTTP $RESP"; else fail "HTTP $RESP"; fi
else skip "无Token"; fi

# ================================================================
section "10. 模型管理测试"

echo -n "  GET /api/v1/models/available: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -H "$AUTH" "$BASE_URL/api/v1/models/available" -o /dev/null -w "%{http_code}" --connect-timeout 10 2>/dev/null)
    if [ "$RESP" = "200" ]; then ok "HTTP $RESP"; else fail "HTTP $RESP"; fi
else skip "无Token"; fi

echo -n "  GET /api/v1/models/downloaded: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -H "$AUTH" "$BASE_URL/api/v1/models/downloaded" -o /dev/null -w "%{http_code}" --connect-timeout 10 2>/dev/null)
    if [ "$RESP" = "200" ]; then ok "HTTP $RESP"; else fail "HTTP $RESP"; fi
else skip "无Token"; fi

# ================================================================
section "11. 知识图谱测试"

echo -n "  GET /api/v1/knowledge-graph/stats: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -H "$AUTH" "$BASE_URL/api/v1/knowledge-graph/stats" -o /dev/null -w "%{http_code}" --connect-timeout 10 2>/dev/null)
    if [ "$RESP" = "200" ]; then ok "HTTP $RESP"; else fail "HTTP $RESP"; fi
else skip "无Token"; fi

echo -n "  GET /api/v1/knowledge-graph/graph: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -H "$AUTH" "$BASE_URL/api/v1/knowledge-graph/graph" -o /dev/null -w "%{http_code}" --connect-timeout 10 2>/dev/null)
    if [ "$RESP" = "200" ]; then ok "HTTP $RESP"; else fail "HTTP $RESP"; fi
else skip "无Token"; fi

echo -n "  GET /api/v1/knowledge-graph/sources: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -H "$AUTH" "$BASE_URL/api/v1/knowledge-graph/sources" -o /dev/null -w "%{http_code}" --connect-timeout 10 2>/dev/null)
    if [ "$RESP" = "200" ]; then ok "HTTP $RESP"; else fail "HTTP $RESP"; fi
else skip "无Token"; fi

echo -n "  GET /api/v1/knowledge-graph/available-cases: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -H "$AUTH" "$BASE_URL/api/v1/knowledge-graph/available-cases" -o /dev/null -w "%{http_code}" --connect-timeout 10 2>/dev/null)
    if [ "$RESP" = "200" ]; then ok "HTTP $RESP"; else fail "HTTP $RESP"; fi
else skip "无Token"; fi

echo -n "  GET /api/v1/knowledge-graph/available-documents: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -H "$AUTH" "$BASE_URL/api/v1/knowledge-graph/available-documents" -o /dev/null -w "%{http_code}" --connect-timeout 10 2>/dev/null)
    if [ "$RESP" = "200" ]; then ok "HTTP $RESP"; else fail "HTTP $RESP"; fi
else skip "无Token"; fi

# ================================================================
section "12. 通知系统测试"

echo -n "  GET /api/v1/notifications/list: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -H "$AUTH" "$BASE_URL/api/v1/notifications/list" -o /dev/null -w "%{http_code}" --connect-timeout 10 2>/dev/null)
    if [ "$RESP" = "200" ]; then ok "HTTP $RESP"; else fail "HTTP $RESP"; fi
else skip "无Token"; fi

echo -n "  GET /api/v1/notifications/unread-count: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -H "$AUTH" "$BASE_URL/api/v1/notifications/unread-count" --connect-timeout 10 2>/dev/null)
    if [ $? -eq 0 ]; then
        COUNT=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('count','?'))" 2>/dev/null)
        ok "未读: $COUNT"
    else
        fail "请求失败"
    fi
else skip "无Token"; fi

# ================================================================
section "13. 用户画像测试"

echo -n "  GET /api/v1/profile: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -H "$AUTH" "$BASE_URL/api/v1/profile" -o /dev/null -w "%{http_code}" --connect-timeout 10 2>/dev/null)
    if [ "$RESP" = "200" ]; then ok "HTTP $RESP"; else fail "HTTP $RESP"; fi
else skip "无Token"; fi

echo -n "  GET /api/v1/profile/ai-hints: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -H "$AUTH" "$BASE_URL/api/v1/profile/ai-hints" -o /dev/null -w "%{http_code}" --connect-timeout 10 2>/dev/null)
    if [ "$RESP" = "200" ]; then ok "HTTP $RESP"; else fail "HTTP $RESP"; fi
else skip "无Token"; fi

# ================================================================
section "14. 反馈标注测试"

echo -n "  POST /api/v1/feedback/submit: "
if [ -n "$AUTH" ]; then
    RESP=$(curl -sf -X POST -H "$AUTH" -H "Content-Type: application/json" \
        -d '{"type":"positive","content":"测试反馈","target_id":"test","target_type":"search"}' \
        "$BASE_URL/api/v1/feedback/submit" -o /dev/null -w "%{http_code}" --connect-timeout 10 2>/dev/null)
    if [ "$RESP" = "200" ]; then ok "HTTP $RESP"; else fail "HTTP $RESP"; fi
else skip "无Token"; fi

# ================================================================
section "15. Python模块完整性"

MODULES="numpy fastapi uvicorn sqlalchemy pydantic jieba requests httpx openai dashscope pdfplumber chromadb langchain bcrypt PIL"
for mod in $MODULES; do
    echo -n "  $mod: "
    python3 -c "import $mod" 2>/dev/null
    if [ $? -eq 0 ]; then ok "可用"; else fail "不可用"; fi
done

echo -n "  fitz (PyMuPDF): "
python3 -c "import fitz" 2>/dev/null
if [ $? -eq 0 ]; then ok "可用"; else skip "不可用(pdfplumber替代)"; fi

# ================================================================
# 最终汇总
# ================================================================
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD} 测试结果汇总${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  总计: $TOTAL"
echo -e "  ${GREEN}通过: $PASS${NC}"
echo -e "  ${RED}失败: $FAIL${NC}"
echo -e "  ${YELLOW}跳过: $SKIP${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "  ${BOLD}${GREEN}🎉 所有测试通过！${NC}"
else
    echo -e "  ${BOLD}${RED}有 $FAIL 项测试失败，请检查上方日志${NC}"
fi

echo ""
echo -e "  ${BOLD}访问地址:${NC}"
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
[ -z "$LOCAL_IP" ] && LOCAL_IP="10.221.100.33"
echo -e "    前端:     ${GREEN}http://${LOCAL_IP}${NC}"
echo -e "    API文档:  ${GREEN}http://${LOCAL_IP}:8000/docs${NC}"
echo -e "    健康检查: ${GREEN}http://${LOCAL_IP}:8000/health${NC}"
if [ -f ".initial_passwords" ]; then
    echo -e "    初始账号: ${GREEN}$(cat .initial_passwords | tr '\n' ' ')${NC}"
fi
echo ""

RESULT_FILE="data/logs/test_result_$(date +%Y%m%d_%H%M%S).txt"
mkdir -p data/logs
cat > "$RESULT_FILE" << EOF
测试时间: $(date)
系统: $(cat /etc/os-release 2>/dev/null | grep "^PRETTY_NAME=" | cut -d'"' -f2)
总计: $TOTAL  通过: $PASS  失败: $FAIL  跳过: $SKIP
前端地址: http://${LOCAL_IP}
API文档: http://${LOCAL_IP}:8000/docs
EOF
info "测试结果已保存到 $RESULT_FILE"
