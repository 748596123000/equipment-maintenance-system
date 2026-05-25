# 设备检修知识检索与作业系统 - 安全审计报告

**审计时间**：2026-05-22 19:20
**审计范围**：后端API + 前端应用 + 数据库安全
**审计方法**：静态代码分析 + OWASP Top 10 对照 + 安全最佳实践
**审计工具**：code-reviewer-cn + code-test-expert + skill-security-evaluator + openclaw-security-auditor

---

## 执行摘要

| 维度 | 得分 | 风险等级 | 主要发现 |
|------|------|----------|---------|
| 认证与授权 | 78/100 | 🟡 良好 | Token存储内存中可扩展性差 |
| 输入验证 | 82/100 | 🟢 良好 | SQL注入防护到位，XSS需注意 |
| 会话管理 | 75/100 | 🟡 良好 | 缺少Token刷新机制 |
| 数据保护 | 80/100 | 🟢 良好 | 密码加密到位，敏感信息处理可优化 |
| 文件上传 | 68/100 | 🟡 注意 | 路径遍历防护到位，内容验证需加强 |
| API安全 | 78/100 | 🟡 良好 | CORS配置需调整 |
| 前端安全 | 72/100 | 🟡 良好 | 缺少XSS防护，Token存储可升级 |

**综合安全评分**：76/100 🟡 良好
**风险等级**：🟡 良好（建议修复警告项）
**建议行动**：重点修复3个高危问题，优先处理DEBUG模式泄露和敏感文件保护

---

## 一、后端安全审计（auth.py）

### 1.1 已实现的安全措施 ✅

| 安全措施 | 状态 | 说明 |
|---------|------|------|
| 密码哈希 | ✅ | bcrypt + SHA256兼容 |
| 防暴力破解 | ✅ | 登录速率限制（5次/5分钟） |
| API限流 | ✅ | IP级别限流（60次/分钟） |
| Token认证 | ✅ | Bearer Token机制 |
| 验证码 | ✅ | 图形验证码防机器人 |
| 日志记录 | ✅ | 完整操作审计日志 |
| 密码长度验证 | ✅ | 最小6字符 |
| 用户审批 | ✅ | 注册需管理员审批 |

### 1.2 发现的安全问题

#### 🟡 中危 - Token存储于内存中

- **位置**：`auth.py:56` `_token_store: dict = {}`
- **问题**：Token存储在进程内存字典中
  - 重启服务后所有用户Token失效
  - 无法跨多实例共享会话
  - 内存泄漏风险（Token未及时清理）
- **影响**：用户体验差，生产环境不适用
- **建议**：
  ```python
  # 方案A：使用Redis存储Token（推荐）
  # pip install redis
  import redis
  _redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
  
  # 方案B：使用JWT替代方案
  # pip install PyJWT
  import jwt
  # JWT可设置过期时间，支持签名验证
  ```

#### 🟡 中危 - 缺少Token刷新机制

- **位置**：`auth.py:157-181`
- **问题**：Token过期后用户必须重新登录
- **影响**：用户需要频繁重新登录
- **建议**：
  ```python
  # 增加refresh_token端点
  @router.post("/refresh", summary="刷新Token")
  async def refresh_token(current_user: dict = Depends(get_current_user)):
      # 生成新Token，延长会话
      new_token = _generate_token()
      # 清理旧Token，存储新Token
      ...
  ```

#### 🟡 中危 - DEBUG模式下验证码答案泄露

- **位置**：`auth.py:258-259`
- **问题**：
  ```python
  from app.config import settings
  if settings.DEBUG:
      result["data"]["captcha_code"] = code  # DEBUG时明文返回验证码！
  ```
- **影响**：生产环境如果误开启DEBUG，攻击者可获取验证码答案
- **建议**：
  ```python
  # 移除DEBUG返回验证码，仅在开发环境返回
  if settings.DEBUG and settings.ENVIRONMENT == "development":
      result["data"]["captcha_code"] = code
  ```

#### 🟢 低危 - 验证码复杂度低

- **位置**：`auth.py:238`
- **问题**：`code = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))`
  - 仅4位字符，可被机器学习模型识别
  - 字符集36个，约21万种组合
- **建议**：
  ```python
  # 增加到6位，加入混淆字符
  code = "".join(random.choices(string.ascii_letters + string.digits, k=6))
  # 或使用更复杂的图形验证码库
  ```

---

## 二、后端安全审计（database.py）

### 2.1 已实现的安全措施 ✅

| 安全措施 | 状态 | 说明 |
|---------|------|------|
| 参数化查询 | ✅ | 所有SQL使用?占位符 |
| 密码加密 | ✅ | bcrypt哈希 |
| 外键约束 | ✅ | 启用PRAGMA foreign_keys=ON |
| WAL模式 | ✅ | 提高并发性能 |
| 软删除 | ✅ | is_active标志 |

### 2.2 发现的安全问题

#### 🟡 中危 - 初始密码写入文件

- **位置**：`database.py:310-334`
- **问题**：
  ```python
  password_file = os.path.join(..., ".initial_passwords")
  with open(password_file, "w", encoding="utf-8") as f:
      f.write(f"admin / {admin_password}\n")
      f.write(f"user / {user_password}\n")
  os.chmod(password_file, 0o600)
  ```
  - 密码以明文形式写入文件系统
  - 文件权限设置为600，但仍存在泄露风险
- **建议**：
  ```python
  # 方案A：仅输出到控制台，不写文件
  logger.warning(f"管理员密码: {admin_password}，请立即修改！")
  
  # 方案B：写入加密文件，需要管理员输入解密密钥
  ```

#### 🟢 低危 - 缺少数据库连接超时

- **位置**：`database.py:70`
- **问题**：`self._connection = sqlite3.connect(self.db_path, check_same_thread=False)`
  - 无连接超时设置
  - 无连接池管理
- **建议**：
  ```python
  self._connection = sqlite3.connect(
      self.db_path, 
      check_same_thread=False,
      timeout=30  # 30秒超时
  )
  ```

---

## 三、后端安全审计（main.py）

### 3.1 已实现的安全措施 ✅

| 安全措施 | 状态 | 说明 |
|---------|------|------|
| 安全响应头 | ✅ | X-Frame-Options, X-XSS-Protection等 |
| CSP内容安全策略 | ✅ | 限制脚本和连接来源 |
| CORS配置 | ✅ | 支持跨域配置 |
| 异常处理 | ✅ | 全局异常处理器 |
| HTTPS强制 | ✅ | HSTS配置 |
| 文档保护 | ✅ | 生产环境关闭Swagger |

### 3.2 发现的安全问题

#### 🔴 高危 - CORS配置过于宽松

- **位置**：`config.py:206-208` + `main.py:146-152`
- **问题**：
  ```python
  CORS_ORIGINS: list = Field(
      default=["http://localhost:80", "http://localhost:3000"],
  )
  # 实际生产可能需要更严格的来源验证
  ```
- **影响**：如果ALLOWED_HOSTS配置不当，可能遭受跨站请求伪造
- **建议**：
  ```python
  # 生产环境应配置具体的域名
  # .env.example 中明确标注需要配置
  CORS_ORIGINS=http://your-domain.com,https://your-domain.com
  
  # 添加来源验证中间件
  @app.middleware("http")
  async def verify_origin(request: Request, call_next):
      origin = request.headers.get("origin")
      if origin and origin not in settings.CORS_ORIGINS:
          # 仅在生产环境拒绝
          if settings.ENVIRONMENT == "production":
              return JSONResponse(status_code=403, content={"detail": "CORS denied"})
  ```

#### 🟡 中危 - 环境检测逻辑可绕过

- **位置**：`main.py:257-259`
- **问题**：
  ```python
  if environment == "production" and settings.DEBUG:
      settings.DEBUG = False
  # 仅在代码层面覆盖DEBUG，未检查其他副作用
  ```
- **建议**：使用环境变量控制，而非运行时检测

---

## 四、后端安全审计（upload.py）

### 4.1 已实现的安全措施 ✅

| 安全措施 | 状态 | 说明 |
|---------|------|------|
| 路径遍历防护 | ✅ | safe_path_join()函数 |
| 文件类型验证 | ✅ | validate_file_type()内容检测 |
| 文件大小限制 | ✅ | MAX_UPLOAD_SIZE限制 |
| 文件扩展名限制 | ✅ | SUPPORTED_EXTENSIONS白名单 |
| 权限控制 | ✅ | 文档删除需所有者或管理员 |
| 内容处置头 | ✅ | Content-Disposition设置 |

### 4.2 发现的安全问题

#### 🟡 中危 - 图片路径遍历（有限制但需注意）

- **位置**：`upload.py:1038-1069`
- **问题**：`get_image_file()` 端点缺少路径验证
  ```python
  @public_router.get("/images/{image_id}/file", ...)
  async def get_image_file(image_id: str):
      # 没有验证image_path是否在允许的目录内
  ```
- **影响**：如果数据库被篡改，可能读取任意文件
- **建议**：
  ```python
  async def get_image_file(image_id: str):
      # 添加路径验证
      real_upload_dir = os.path.realpath(settings.IMAGE_DIR)
      real_image_path = os.path.realpath(image_path)
      if not real_image_path.startswith(real_upload_dir + os.sep):
          raise HTTPException(status_code=403, detail="非法文件路径")
  ```

#### 🟡 中危 - 批量上传无并发限制

- **位置**：`upload.py:325-392`
- **问题**：批量上传API `batch_upload_files()` 缺少请求数限制
- **影响**：可能被用于DDoS攻击
- **建议**：
  ```python
  @router.post("/batch", summary="批量上传文档文件")
  async def batch_upload_files(files: List[UploadFile] = File(...)):
      if len(files) > 10:  # 限制单次最多10个文件
          raise HTTPException(status_code=400, detail="单次批量上传最多10个文件")
  ```

#### 🟢 低危 - 文件名未清理特殊字符

- **位置**：`upload.py:237`
- **问题**：`safe_filename = os.path.basename(filename)` 
  - 仅取basename，但Windows不支持部分特殊字符
  - 文件名过长可能影响存储
- **建议**：
  ```python
  import re
  def sanitize_filename(filename: str) -> str:
      # 移除Windows不兼容的字符
      filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
      # 限制长度
      name, ext = os.path.splitext(filename)
      if len(name) > 100:
          name = name[:100]
      return name + ext
  ```

---

## 五、后端安全审计（chat.py）

### 5.1 已实现的安全措施 ✅

| 安全措施 | 状态 | 说明 |
|---------|------|------|
| 会话隔离 | ✅ | 用户只能访问自己的会话 |
| 管理员访问 | ✅ | 管理员可访问所有会话 |
| 输入长度限制 | ✅ | max_length=5000 |
| 响应缓存 | ✅ | 减少LLM调用，防重复查询 |
| 历史记录限制 | ✅ | limit参数限制 |

### 5.2 发现的安全问题

#### 🟡 中危 - SSE流式接口权限验证缺陷

- **位置**：`chat.py:277-386`
- **问题**：
  ```python
  async def chat_stream(credentials: Optional[HTTPAuthorizationCredentials] = Security(_stream_security)):
      token = credentials.credentials if credentials else None
      current_user = None
      if token:
          current_user = await _verify_stream_token(token)
      # 问题：如果credentials为None，允许匿名访问！
  ```
- **影响**：未认证用户可能进行问答，消耗LLM资源
- **建议**：
  ```python
  # 改为必需认证
  async def chat_stream(
      credentials: HTTPAuthorizationCredentials = Security(_stream_security),
      ...
  ):
      current_user = await _verify_stream_token(credentials.credentials)
  ```

#### 🟡 中危 - 响应缓存可能泄露信息

- **位置**：`chat.py:48-50`
- **问题**：`TTLCache(maxsize=500, ttl=3600)` 缓存所有问答
  - 如果用户问"我的密码是什么"，答案被缓存
  - 多用户共享缓存可能泄露隐私
- **建议**：
  ```python
  # 按用户分隔缓存
  _response_cache: dict = {}  # {user_id: {question_hash: {...}}}
  
  # 或增加隐私选项
  def should_cache(user_id: str, question: str) -> bool:
      sensitive_patterns = ["密码", "password", "密钥", "token"]
      return not any(p in question.lower() for p in sensitive_patterns)
  ```

#### 🟢 低危 - Base64解码无验证

- **位置**：`chat.py:140-151`
- **问题**：`image_bytes = base64.b64decode(request.image_base64)`
  - 可能导致内存耗尽（大Base64字符串）
  - 无图片大小预检测
- **建议**：
  ```python
  # 添加解码前大小估算
  if len(request.image_base64) > 10_000_000:  # ~7.5MB Base64
      raise HTTPException(status_code=400, detail="图片过大")
  ```

---

## 六、前端安全审计

### 6.1 已实现的安全措施 ✅

| 安全措施 | 状态 | 说明 |
|---------|------|------|
| Token存储 | ✅ | localStorage存储 |
| 401自动登出 | ✅ | 响应拦截器处理 |
| CSRF Token | ⚠️ | 有框架但未在后端验证 |
| 输入验证 | ✅ | HTML5原生验证 |
| 安全响应头 | ✅ | CSP策略 |

### 6.2 发现的安全问题

#### 🟡 中危 - Token存储于localStorage

- **位置**：`frontend/src/lib/auth.ts`
- **问题**：
  ```typescript
  export function setToken(token: string): void {
    localStorage.setItem(TOKEN_KEY, token);
  }
  ```
  - localStorage可被XSS攻击读取
  - 共享设备可能泄露Token
- **建议**：
  ```typescript
  // 方案A：使用HttpOnly Cookie（需后端配合）
  // 方案B：使用sessionStorage（浏览器关闭后清除）
  export function setToken(token: string): void {
    sessionStorage.setItem(TOKEN_KEY, token);
  }
  // 方案C：加密存储
  ```

#### 🟡 中危 - 缺少XSS防护

- **位置**：`frontend/src` 全局
- **问题**：React默认防护XSS，但dangerouslySetInnerHTML使用需谨慎
- **影响**：存储型XSS可能窃取Token
- **建议**：
  ```typescript
  // 添加XSS防护库
  // npm install dompurify
  import DOMPurify from 'dompurify';
  
  const sanitizeContent = (content: string) => {
    return DOMPurify.sanitize(content, { ALLOWED_TAGS: [] });
  };
  ```

#### 🟡 中危 - CSRF Token未实际使用

- **位置**：`frontend/src/lib/api.ts:8-31`
- **问题**：
  ```typescript
  export function getCsrfToken(): string | null {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag?.getAttribute('content') || null;
  }
  // 获取了Token但后端未验证
  ```
- **建议**：在后端增加CSRF验证中间件，或移除前端代码

#### 🟢 低危 - 敏感信息日志

- **位置**：多处console.log
- **问题**：生产环境可能打印敏感调试信息
- **建议**：
  ```typescript
  // 添加环境检查
  const log = (message: string, ...args: any[]) => {
    if (import.meta.env.DEV) {
      console.log(message, ...args);
    }
  };
  ```

---

## 七、综合风险矩阵

| 风险 ID | 风险等级 | 类别 | 描述 | 可利用性 | 影响 | 修复优先级 |
|---------|----------|------|------|----------|------|------------|
| HIGH-1 | 高危 | 配置安全 | CORS配置过于宽松 | 中 | 高 | P1 |
| MEDIUM-1 | 中危 | 认证安全 | DEBUG模式泄露验证码 | 低 | 中 | P1 |
| MEDIUM-2 | 中危 | 会话管理 | Token存储内存中 | 中 | 中 | P2 |
| MEDIUM-3 | 中危 | 会话管理 | 缺少Token刷新 | 低 | 中 | P2 |
| MEDIUM-4 | 中危 | 访问控制 | SSE接口可匿名访问 | 中 | 中 | P1 |
| MEDIUM-5 | 中危 | 文件安全 | 图片路径遍历风险 | 低 | 中 | P2 |
| MEDIUM-6 | 中危 | 文件安全 | 批量上传无限制 | 中 | 中 | P2 |
| MEDIUM-7 | 中危 | 数据安全 | 初始密码明文存储 | 中 | 中 | P2 |
| MEDIUM-8 | 中危 | 前端安全 | Token存储localStorage | 中 | 中 | P2 |
| MEDIUM-9 | 中危 | 前端安全 | 缺少XSS防护 | 中 | 中 | P2 |
| MEDIUM-10 | 中危 | 配置安全 | CSRF Token未验证 | 低 | 中 | P3 |
| LOW-1 | 低危 | 验证码 | 验证码复杂度低 | 中 | 低 | P3 |
| LOW-2 | 低危 | 文件安全 | 文件名特殊字符 | 低 | 低 | P3 |
| LOW-3 | 低危 | 性能 | 无数据库连接超时 | 低 | 低 | P3 |
| LOW-4 | 低危 | 前端安全 | 敏感信息日志 | 低 | 低 | P3 |

---

## 八、攻击场景分析

### 场景1：验证码绕过攻击

- **攻击路径**：通过DEBUG模式获取验证码答案
- **利用条件**：生产环境误开启DEBUG=True
- **潜在影响**：攻击者可用获取的验证码答案进行暴力破解
- **防御建议**：
  ```python
  # auth.py 修改
  if settings.DEBUG and settings.ENVIRONMENT == "development":
      result["data"]["captcha_code"] = code
  # 确保生产环境ENVIRONMENT=production
  ```

### 场景2：会话劫持攻击

- **攻击路径**：通过XSS读取localStorage中的Token
- **利用条件**：存在存储型XSS漏洞
- **潜在影响**：攻击者获取用户Token后冒充用户操作
- **防御建议**：
  ```typescript
  // 使用sessionStorage替代localStorage
  sessionStorage.setItem(TOKEN_KEY, token);
  // 限制Token有效期
  // 添加Token与IP绑定验证
  ```

### 场景3：资源耗尽攻击

- **攻击路径**：通过批量上传接口上传大量文件
- **利用条件**：无批量上传限制
- **潜在影响**：磁盘空间耗尽，服务拒绝
- **防御建议**：
  ```python
  if len(files) > 10:
      raise HTTPException(status_code=400, detail="单次最多10个文件")
  ```

### 场景4：跨站请求伪造（CSRF）

- **攻击路径**：利用CORS配置不当发起跨域请求
- **利用条件**：CORS配置过于宽松
- **潜在影响**：用户被诱导执行非预期操作
- **防御建议**：
  - 配置严格的CORS_ORIGINS
  - 实现CSRF Token验证
  - 检查Referer/Origin头

---

## 九、修复建议

### 紧急修复（P0-P1）

#### 1. 修复DEBUG模式验证码泄露

**文件**：`app/api/auth.py`
**位置**：258-259行

```python
# 当前代码
from app.config import settings
if settings.DEBUG:
    result["data"]["captcha_code"] = code

# 修复后
from app.config import settings
if settings.DEBUG and settings.ENVIRONMENT == "development":
    result["data"]["captcha_code"] = code
```

**同时在`.env.example`中添加**：
```
ENVIRONMENT=production  # 确保生产环境设置
```

#### 2. 修复SSE接口权限验证

**文件**：`app/api/chat.py`
**位置**：277-290行

```python
# 当前代码
async def chat_stream(
    question: str = Query(...),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_stream_security),
):
    token = credentials.credentials if credentials else None
    current_user = None
    if token:
        current_user = await _verify_stream_token(token)
    # 问题：credentials为None时仍可访问

# 修复后
async def chat_stream(
    question: str = Query(...),
    credentials: HTTPAuthorizationCredentials = Security(_stream_security),
):
    current_user = await _verify_stream_token(credentials.credentials)
```

#### 3. 配置严格的CORS

**文件**：`app/config.py` 或 `.env`

```python
# .env 中配置（生产环境）
CORS_ORIGINS=http://your-domain.com,https://your-domain.com
ENVIRONMENT=production
```

---

### 高优先级（P2）

#### 4. Token存储改为Redis（可选）

**文件**：`app/api/auth.py`

```python
# 添加依赖
# pip install redis

try:
    import redis
    _redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    REDIS_ENABLED = True
except:
    REDIS_ENABLED = False

async def get_current_user(...):
    token = credentials.credentials
    if REDIS_ENABLED:
        token_data = _redis_client.get(f"token:{token}")
        if token_data:
            token_data = json.loads(token_data)
        # ... 验证逻辑
    else:
        # 回退到内存存储
        token_data = _token_store.get(token)
```

#### 5. 文件访问路径验证

**文件**：`app/api/upload.py`
**位置**：1038-1069行

```python
@public_router.get("/images/{image_id}/file", summary="获取图片文件")
async def get_image_file(image_id: str):
    # ... 获取image_path ...
    
    # 添加路径验证
    real_upload_dir = os.path.realpath(settings.IMAGE_DIR)
    real_image_path = os.path.realpath(image_path)
    if not real_image_path.startswith(real_upload_dir + os.sep):
        raise HTTPException(status_code=403, detail="非法文件路径")
```

#### 6. 批量上传数量限制

**文件**：`app/api/upload.py`
**位置**：325-330行

```python
@router.post("/batch", summary="批量上传文档文件")
async def batch_upload_files(
    files: List[UploadFile] = File(...),
    category: str = Form(default="通用"),
    current_user: dict = Depends(get_current_user),
):
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="单次批量上传最多10个文件")
```

#### 7. 前端Token存储改为sessionStorage

**文件**：`frontend/src/lib/auth.ts`

```typescript
const TOKEN_KEY = "equipment_maintenance_token";

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);  // 改为sessionStorage
}

export function setToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function removeToken(): void {
  sessionStorage.removeItem(TOKEN_KEY);
}
```

---

### 中低优先级（P3）

#### 8. 增强验证码复杂度

**文件**：`app/api/auth.py`

```python
@router.get("/captcha", summary="获取验证码")
async def get_captcha():
    # 使用6位字符
    code = "".join(random.choices(string.ascii_letters + string.digits, k=6))
    # 增大图片和字体
```

#### 9. 数据库连接超时

**文件**：`app/models/database.py`

```python
self._connection = sqlite3.connect(
    self.db_path, 
    check_same_thread=False,
    timeout=30  # 添加30秒超时
)
```

#### 10. 文件名清理

**文件**：`app/api/upload.py`

```python
import re

def sanitize_filename(filename: str) -> str:
    """清理文件名中的特殊字符"""
    name, ext = os.path.splitext(filename)
    # 移除Windows不兼容字符
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    # 限制长度
    if len(name) > 100:
        name = name[:100]
    return name + ext
```

---

## 十、安全配置清单

### 生产环境必做项

| 配置项 | 要求 | 检查位置 |
|--------|------|----------|
| ENVIRONMENT | production | .env |
| DEBUG | False | .env |
| CORS_ORIGINS | 仅允许指定域名 | .env |
| SECRET_KEY | 随机32位字符串 | .env |
| 数据库密码 | 强密码（如果使用远程DB） | .env |
| API文档 | 关闭Swagger | DEBUG=False |
| 日志级别 | WARNING/ERROR | .env |

### 生产环境建议项

| 配置项 | 建议 | 优先级 |
|--------|------|--------|
| HTTPS | 强制使用HTTPS | P1 |
| Redis | Token持久化存储 | P2 |
| CDN | 静态资源使用CDN | P2 |
| WAF | 部署Web应用防火墙 | P2 |
| 监控 | 接入安全监控服务 | P3 |

---

## 十一、附录：OWASP Top 10 对照

| OWASP风险 | 本系统状态 | 说明 |
|-----------|-----------|------|
| A01: Broken Access Control | ✅ 已实现 | require_admin、权限检查到位 |
| A02: Cryptographic Failures | ⚠️ 部分 | 密码加密好，Token存储需改进 |
| A03: Injection | ✅ 已实现 | SQL使用参数化查询 |
| A04: Insecure Design | ⚠️ 需注意 | SSE接口需修复 |
| A05: Security Misconfiguration | ⚠️ 需注意 | CORS配置需加强 |
| A06: Vulnerable Components | ⚠️ 需扫描 | 建议定期依赖扫描 |
| A07: Auth Failures | ✅ 已实现 | 速率限制、验证码到位 |
| A08: Data Integrity | ⚠️ 需注意 | 文件上传需加强验证 |
| A09: Logging Failures | ✅ 已实现 | 完整操作日志 |
| A10: SSRF | ✅ 已防护 | safe_path_join防路径遍历 |

---

**报告生成时间**：2026-05-22 19:20
**审计方法**：静态代码分析 + OWASP Top 10 对照
**有效期**：建议每季度重新审计