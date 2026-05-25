"""
SQLite数据库操作模块

管理系统的持久化数据存储，包括：
- 用户表 (users): 用户账号和权限管理
- 文档表 (documents): 上传的PDF文档记录
- 案例表 (cases): 检修案例记录
- 审核表 (reviews): 内容审核记录
- 反馈表 (feedback): AI回答反馈
- 日志表 (logs): 系统操作日志
- 对话会话表 (chat_sessions): AI对话会话
- 对话消息表 (chat_messages): AI对话消息
- 作业指引表 (guides): 生成的作业指引
- 系统配置表 (system_config): 系统配置项

使用标准sqlite3库，所有CRUD操作使用参数化查询防止SQL注入。
"""

import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import bcrypt

from app.config import settings

logger = logging.getLogger(__name__)


class Database:
    """
    数据库管理类

    封装SQLite数据库的连接管理和CRUD操作。
    使用WAL日志模式和参数化查询。

    Attributes:
        db_path: 数据库文件路径
        _connection: 数据库连接实例
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化数据库连接

        Args:
            db_path: 数据库文件路径，默认从配置读取
        """
        self.db_path = db_path or settings.SQLITE_DB_PATH
        self._connection: Optional[sqlite3.Connection] = None

    def get_connection(self) -> sqlite3.Connection:
        """
        获取数据库连接（延迟初始化）

        自动创建数据库目录，启用WAL模式和外键约束。

        Returns:
            sqlite3.Connection: 数据库连接实例
        """
        if self._connection is None:
            # 确保数据库目录存在
            db_dir = os.path.dirname(self.db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
            self._connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30  # 30秒连接超时
            )
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA foreign_keys=ON")
        return self._connection

    def close(self) -> None:
        """关闭数据库连接"""
        if self._connection is not None:
            self._connection.close()
            self._connection = None
            logger.info("数据库连接已关闭")

    def init_db(self) -> None:
        """
        初始化数据库表结构

        创建所有必要的表，如果表已存在则跳过。
        包含：users, documents, cases, reviews, feedback, logs,
              chat_sessions, chat_messages, guides, system_config。
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # ========== 用户表 ==========
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                created_at TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                status TEXT DEFAULT 'active'
            )
        """)

        # ========== 文档表 ==========
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                filepath TEXT NOT NULL,
                file_size INTEGER DEFAULT 0,
                page_count INTEGER DEFAULT 0,
                upload_time TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                chunk_count INTEGER DEFAULT 0,
                uploader_id TEXT DEFAULT '',
                reviewer_id TEXT DEFAULT '',
                review_comment TEXT DEFAULT '',
                reviewed_at TEXT DEFAULT '',
                category TEXT DEFAULT '通用'
            )
        """)

        # ========== 检修案例表 ==========
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                device_model TEXT DEFAULT '',
                fault_type TEXT DEFAULT '',
                solution TEXT DEFAULT '',
                fault_analysis TEXT,
                repair_process TEXT,
                lessons_learned TEXT,
                tags TEXT,
                author_id TEXT,
                status TEXT DEFAULT 'pending_review',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (author_id) REFERENCES users(id)
            )
        """)

        # ========== 审核表 ==========
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                reviewer_id TEXT NOT NULL,
                review_type TEXT DEFAULT 'approve',
                comment TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (case_id) REFERENCES cases(id),
                FOREIGN KEY (reviewer_id) REFERENCES users(id)
            )
        """)

        # ========== 反馈表 ==========
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                response TEXT NOT NULL,
                corrected_response TEXT DEFAULT '',
                source TEXT DEFAULT '',
                applied INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)

        # ========== 日志表 ==========
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                action TEXT NOT NULL,
                detail TEXT DEFAULT '',
                ip_address TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # ========== 对话会话表 ==========
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                title TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # ========== 对话消息表 ==========
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources TEXT DEFAULT '[]',
                confidence REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
            )
        """)

        # ========== 作业指引表 ==========
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS guides (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                task_description TEXT NOT NULL,
                equipment_type TEXT DEFAULT '',
                equipment_model TEXT DEFAULT '',
                safety_level TEXT DEFAULT 'standard',
                guide_content TEXT DEFAULT '',
                created_by TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """)

        # ========== 系统配置表 ==========
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                description TEXT DEFAULT '',
                updated_at TEXT NOT NULL
            )
        """)

        # ========== 知识图谱节点表 ==========
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_graph_nodes (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                properties TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            )
        """)

        # ========== 知识图谱边表 ==========
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_graph_edges (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                properties TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY (source_id) REFERENCES knowledge_graph_nodes(id),
                FOREIGN KEY (target_id) REFERENCES knowledge_graph_nodes(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_images (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                image_index INTEGER NOT NULL,
                image_path TEXT NOT NULL,
                width INTEGER DEFAULT 0,
                height INTEGER DEFAULT 0,
                image_format TEXT DEFAULT 'png',
                ai_description TEXT DEFAULT '',
                ai_analyzed INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(id)
            )
        """)

        # ========== 创建索引 ==========
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_author ON cases(author_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_case ON reviews(case_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_user ON logs(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_created ON logs(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kg_nodes_type ON knowledge_graph_nodes(type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kg_nodes_name ON knowledge_graph_nodes(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kg_edges_source ON knowledge_graph_edges(source_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kg_edges_target ON knowledge_graph_edges(target_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kg_edges_relation ON knowledge_graph_edges(relation)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_doc_images_document ON document_images(document_id)")

        try:
            cursor.execute("ALTER TABLE feedback ADD COLUMN applied INTEGER DEFAULT 0")
        except Exception:
            pass

        conn.commit()
        logger.info("数据库表初始化完成")

        now = datetime.now().isoformat()
        admin_exists = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()
        if not admin_exists:
            import secrets
            admin_password = secrets.token_urlsafe(12)
            admin_password_hash = bcrypt.hashpw(admin_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            cursor.execute(
                """INSERT INTO users (id, username, password_hash, role, created_at, is_active, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ("admin_001", "admin", admin_password_hash, "admin", now, 1, "active")
            )

            user_password = secrets.token_urlsafe(12)
            user_password_hash = bcrypt.hashpw(user_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            cursor.execute(
                """INSERT INTO users (id, username, password_hash, role, created_at, is_active, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ("user_001", "user", user_password_hash, "user", now, 1, "active")
            )

            conn.commit()
            # 仅输出到日志，不写入文件，避免密码文件泄露风险
            logger.warning("=" * 60)
            logger.warning("初始用户已创建：")
            logger.warning(f"  管理员账号: admin / {admin_password}")
            logger.warning(f"  普通账号: user / {user_password}")
            logger.warning("请立即使用这些账号登录并修改密码！")
            logger.warning("=" * 60)

    # ========== 用户操作 ==========

    def create_user(
        self,
        user_id: str,
        username: str,
        password_hash: str,
        role: str = "user",
        status: str = "active",
    ) -> Dict[str, Any]:
        """
        创建新用户

        Args:
            user_id: 用户ID
            username: 用户名
            password_hash: 密码哈希
            role: 角色 (admin/user)
            status: 用户状态 (active/pending_approval/rejected)

        Returns:
            dict: 用户信息
        """
        conn = self.get_connection()
        now = datetime.now().isoformat()
        conn.execute(
            """INSERT INTO users (id, username, password_hash, role, created_at, is_active, status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, username, password_hash, role, now, 1, status)
        )
        conn.commit()
        logger.info(f"用户创建成功: {username}, status={status}")
        return {"id": user_id, "username": username, "role": role, "status": status}

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        根据用户ID查询用户

        Args:
            user_id: 用户ID

        Returns:
            Optional[dict]: 用户信息（不含密码哈希），不存在则返回None
        """
        conn = self.get_connection()
        cursor = conn.execute(
            "SELECT id, username, role, created_at, is_active, status FROM users WHERE id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        根据用户名查询用户

        Args:
            username: 用户名

        Returns:
            Optional[dict]: 用户信息，不存在则返回None
        """
        conn = self.get_connection()
        cursor = conn.execute(
            "SELECT * FROM users WHERE username = ? AND is_active = 1",
            (username,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_user_by_username_all(self, username: str) -> Optional[Dict[str, Any]]:
        """
        根据用户名查询用户（包括所有状态，用于登录检查）

        Args:
            username: 用户名

        Returns:
            Optional[dict]: 用户信息，不存在则返回None
        """
        conn = self.get_connection()
        cursor = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_user(
        self,
        user_id: str,
        username: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        password_hash: Optional[str] = None,
        status: Optional[str] = None,
    ) -> bool:
        """
        更新用户信息

        Args:
            user_id: 用户ID
            username: 新用户名
            role: 新角色
            is_active: 是否激活
            password_hash: 新密码哈希
            status: 用户状态 (active/pending_approval/rejected)

        Returns:
            bool: 是否更新成功
        """
        conn = self.get_connection()
        allowed_fields = {
            "username": username,
            "role": role,
            "password_hash": password_hash,
            "is_active": 1 if is_active else 0 if is_active is not None else None,
            "status": status,
        }
        updates = [f"{k} = ?" for k, v in allowed_fields.items() if v is not None]
        values = [v for v in allowed_fields.values() if v is not None]

        if not updates:
            return False

        values.append(user_id)
        cursor = conn.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
            values
        )
        conn.commit()
        return cursor.rowcount > 0

    def delete_user(self, user_id: str) -> bool:
        """
        删除用户（软删除，设置is_active=0）

        Args:
            user_id: 用户ID

        Returns:
            bool: 是否删除成功
        """
        conn = self.get_connection()
        cursor = conn.execute(
            "UPDATE users SET is_active = 0 WHERE id = ?", (user_id,)
        )
        conn.commit()
        return cursor.rowcount > 0

    def list_users(
        self,
        page: int = 1,
        page_size: int = 20,
        role: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取用户列表

        Args:
            page: 页码
            page_size: 每页数量
            role: 角色筛选
            status: 状态筛选

        Returns:
            dict: 包含users列表和total总数
        """
        conn = self.get_connection()

        where_clause = "WHERE is_active = 1"
        params: list = []
        if role:
            where_clause += " AND role = ?"
            params.append(role)
        if status:
            where_clause += " AND status = ?"
            params.append(status)

        # 查询总数
        count_result = conn.execute(
            f"SELECT COUNT(*) FROM users {where_clause}", params
        ).fetchone()
        total = count_result[0]

        # 查询列表
        offset = (page - 1) * page_size
        cursor = conn.execute(
            f"SELECT id, username, role, created_at, is_active, status FROM users {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset]
        )
        users = [dict(row) for row in cursor.fetchall()]

        return {"users": users, "total": total}

    # ========== 文档操作 ==========

    def save_document(
        self,
        document_id: str,
        filename: str,
        filepath: str,
        file_size: int = 0,
        uploader_id: str = "",
        category: str = "通用",
    ) -> Dict[str, Any]:
        """
        保存文档记录

        Args:
            document_id: 文档ID
            filename: 文件名
            filepath: 文件路径
            file_size: 文件大小
            uploader_id: 上传者ID
            category: 文档分类

        Returns:
            dict: 文档信息
        """
        conn = self.get_connection()
        now = datetime.now().isoformat()
        conn.execute(
            """INSERT INTO documents (id, filename, filepath, file_size, upload_time, status, chunk_count, uploader_id, category)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (document_id, filename, filepath, file_size, now, "pending", 0, uploader_id, category)
        )
        conn.commit()
        return {"id": document_id, "filename": filename, "status": "pending"}

    def update_document(
        self,
        document_id: str,
        status: Optional[str] = None,
        page_count: Optional[int] = None,
        chunk_count: Optional[int] = None,
    ) -> bool:
        """
        更新文档信息

        Args:
            document_id: 文档ID
            status: 处理状态 (pending/approved/rejected/processing/completed/failed)
            page_count: 页数
            chunk_count: 文本块数量

        Returns:
            bool: 是否更新成功
        """
        conn = self.get_connection()
        allowed_fields = {
            "status": status,
            "page_count": page_count,
            "chunk_count": chunk_count,
        }
        updates = [f"{k} = ?" for k, v in allowed_fields.items() if v is not None]
        values = [v for v in allowed_fields.values() if v is not None]

        if not updates:
            return False

        values.append(document_id)
        cursor = conn.execute(
            f"UPDATE documents SET {', '.join(updates)} WHERE id = ?",
            values
        )
        conn.commit()
        return cursor.rowcount > 0

    def update_document_review(
        self,
        document_id: str,
        status: str,
        reviewer_id: str,
        review_comment: str = "",
    ) -> bool:
        """
        更新文档审批信息

        Args:
            document_id: 文档ID
            status: 审批状态 (approved/rejected)
            reviewer_id: 审核者ID
            review_comment: 审核意见

        Returns:
            bool: 是否更新成功
        """
        conn = self.get_connection()
        now = datetime.now().isoformat()
        cursor = conn.execute(
            """UPDATE documents SET status = ?, reviewer_id = ?, review_comment = ?, reviewed_at = ?
               WHERE id = ?""",
            (status, reviewer_id, review_comment, now, document_id)
        )
        conn.commit()
        return cursor.rowcount > 0

    def list_documents_by_uploader(
        self,
        uploader_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """
        获取指定用户上传的文档列表

        Args:
            uploader_id: 上传者ID
            page: 页码
            page_size: 每页数量

        Returns:
            dict: 文档列表和分页信息
        """
        conn = self.get_connection()

        count_result = conn.execute(
            "SELECT COUNT(*) FROM documents WHERE uploader_id = ?", (uploader_id,)
        ).fetchone()
        total = count_result[0]

        offset = (page - 1) * page_size
        cursor = conn.execute(
            "SELECT * FROM documents WHERE uploader_id = ? ORDER BY upload_time DESC LIMIT ? OFFSET ?",
            (uploader_id, page_size, offset)
        )
        documents = [dict(row) for row in cursor.fetchall()]

        return {"documents": documents, "total": total}

    def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取文档信息

        Args:
            document_id: 文档ID

        Returns:
            Optional[dict]: 文档信息
        """
        conn = self.get_connection()
        cursor = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (document_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def list_documents(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取文档列表

        Args:
            page: 页码
            page_size: 每页数量
            status: 状态筛选

        Returns:
            dict: 文档列表和分页信息
        """
        conn = self.get_connection()

        where_clause = ""
        params: list = []
        if status:
            where_clause = "WHERE status = ?"
            params.append(status)

        count_result = conn.execute(
            f"SELECT COUNT(*) FROM documents {where_clause}", params
        ).fetchone()
        total = count_result[0]

        offset = (page - 1) * page_size
        cursor = conn.execute(
            f"SELECT * FROM documents {where_clause} ORDER BY upload_time DESC LIMIT ? OFFSET ?",
            params + [page_size, offset]
        )
        documents = [dict(row) for row in cursor.fetchall()]

        return {"documents": documents, "total": total}

    def delete_document(self, document_id: str) -> bool:
        """
        删除文档记录

        Args:
            document_id: 文档ID

        Returns:
            bool: 是否删除成功
        """
        conn = self.get_connection()
        cursor = conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        conn.commit()
        return cursor.rowcount > 0

    # ========== 案例操作 ==========

    def create_case(
        self,
        case_id: str,
        title: str,
        description: str,
        device_model: str = "",
        fault_type: str = "",
        solution: str = "",
        author_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        创建检修案例

        Args:
            case_id: 案例ID
            title: 标题
            description: 描述
            device_model: 设备型号
            fault_type: 故障类型
            solution: 解决方案
            author_id: 作者ID

        Returns:
            dict: 案例信息
        """
        conn = self.get_connection()
        now = datetime.now().isoformat()
        conn.execute(
            """INSERT INTO cases (id, title, description, device_model, fault_type, solution, author_id, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (case_id, title, description, device_model, fault_type, solution, author_id, "pending_review", now, now)
        )
        conn.commit()
        logger.info(f"案例创建成功: {title}")
        return {"id": case_id, "title": title, "status": "pending_review"}

    def get_case_by_id(self, case_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取案例详情

        Args:
            case_id: 案例ID

        Returns:
            Optional[dict]: 案例信息
        """
        conn = self.get_connection()
        cursor = conn.execute(
            "SELECT * FROM cases WHERE id = ?", (case_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def list_cases(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        device_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取案例列表

        Args:
            page: 页码
            page_size: 每页数量
            status: 状态筛选
            device_model: 设备型号筛选

        Returns:
            dict: 案例列表和分页信息
        """
        conn = self.get_connection()

        conditions = []
        params: list = []

        if status:
            conditions.append("status = ?")
            params.append(status)
        if device_model:
            conditions.append("device_model = ?")
            params.append(device_model)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        count_result = conn.execute(
            f"SELECT COUNT(*) FROM cases {where_clause}", params
        ).fetchone()
        total = count_result[0]

        offset = (page - 1) * page_size
        cursor = conn.execute(
            f"SELECT * FROM cases {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset]
        )
        cases = [dict(row) for row in cursor.fetchall()]

        return {"cases": cases, "total": total}

    def update_case(
        self,
        case_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        device_model: Optional[str] = None,
        fault_type: Optional[str] = None,
        solution: Optional[str] = None,
        status: Optional[str] = None,
    ) -> bool:
        """
        更新案例信息

        Args:
            case_id: 案例ID
            title: 标题
            description: 描述
            device_model: 设备型号
            fault_type: 故障类型
            solution: 解决方案
            status: 状态

        Returns:
            bool: 是否更新成功
        """
        conn = self.get_connection()
        allowed_fields = {
            "title": title,
            "description": description,
            "device_model": device_model,
            "fault_type": fault_type,
            "solution": solution,
            "status": status,
        }
        updates = [f"{k} = ?" for k, v in allowed_fields.items() if v is not None]
        values = [v for v in allowed_fields.values() if v is not None]

        if not updates:
            return False

        updates.append("updated_at = ?")
        values.append(datetime.now().isoformat())

        values.append(case_id)
        cursor = conn.execute(
            f"UPDATE cases SET {', '.join(updates)} WHERE id = ?",
            values
        )
        conn.commit()
        return cursor.rowcount > 0

    def delete_case(self, case_id: str) -> bool:
        """
        删除案例

        Args:
            case_id: 案例ID

        Returns:
            bool: 是否删除成功
        """
        conn = self.get_connection()
        cursor = conn.execute("DELETE FROM cases WHERE id = ?", (case_id,))
        conn.commit()
        return cursor.rowcount > 0

    # ========== 审核操作 ==========

    def create_review(
        self,
        review_id: str,
        case_id: str,
        reviewer_id: str,
        review_type: str,
        comment: str = "",
    ) -> Dict[str, Any]:
        """
        创建审核记录

        Args:
            review_id: 审核ID
            case_id: 案例ID
            reviewer_id: 审核人ID
            review_type: 审核类型 (approve/reject)
            comment: 审核意见

        Returns:
            dict: 审核信息
        """
        conn = self.get_connection()
        now = datetime.now().isoformat()

        # 创建审核记录
        conn.execute(
            """INSERT INTO reviews (id, case_id, reviewer_id, review_type, comment, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (review_id, case_id, reviewer_id, review_type, comment, now)
        )

        # 同步更新案例状态
        case_status = "approved" if review_type == "approve" else "rejected"
        conn.execute(
            "UPDATE cases SET status = ?, updated_at = ? WHERE id = ?",
            (case_status, now, case_id)
        )

        conn.commit()
        logger.info(f"案例审核完成: case_id={case_id}, type={review_type}")
        return {"id": review_id, "case_id": case_id, "review_type": review_type}

    def list_reviews(
        self,
        case_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """
        获取审核记录列表

        Args:
            case_id: 案例ID筛选
            page: 页码
            page_size: 每页数量

        Returns:
            dict: 审核列表和分页信息
        """
        conn = self.get_connection()

        where_clause = ""
        params: list = []
        if case_id:
            where_clause = "WHERE case_id = ?"
            params.append(case_id)

        count_result = conn.execute(
            f"SELECT COUNT(*) FROM reviews {where_clause}", params
        ).fetchone()
        total = count_result[0]

        offset = (page - 1) * page_size
        cursor = conn.execute(
            f"SELECT * FROM reviews {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset]
        )
        reviews = [dict(row) for row in cursor.fetchall()]

        return {"reviews": reviews, "total": total}

    # ========== 反馈操作 ==========

    def save_feedback(
        self,
        query: str,
        response: str,
        corrected_response: str = "",
        source: str = "",
    ) -> str:
        """
        保存AI回答反馈

        Args:
            query: 用户查询
            response: AI回答
            corrected_response: 纠正后的回答
            source: 来源

        Returns:
            str: 反馈ID
        """
        conn = self.get_connection()
        feedback_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        conn.execute(
            """INSERT INTO feedback (id, query, response, corrected_response, source, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (feedback_id, query, response, corrected_response, source, now)
        )
        conn.commit()
        return feedback_id

    def list_feedback(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """
        获取反馈列表

        Args:
            page: 页码
            page_size: 每页数量

        Returns:
            dict: 反馈列表和分页信息
        """
        conn = self.get_connection()

        count_result = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()
        total = count_result[0]

        offset = (page - 1) * page_size
        cursor = conn.execute(
            "SELECT * FROM feedback ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (page_size, offset)
        )
        feedbacks = [dict(row) for row in cursor.fetchall()]

        return {"feedbacks": feedbacks, "total": total}

    # ========== 对话操作 ==========

    def save_chat_message(
        self,
        session_id: str,
        role: str,
        content: str,
        sources: Optional[List[dict]] = None,
        confidence: float = 0.0,
        user_id: Optional[str] = None,
    ) -> str:
        """
        保存对话消息

        Args:
            session_id: 会话ID
            role: 角色 (user/assistant)
            content: 消息内容
            sources: 引用来源
            confidence: 置信度
            user_id: 用户ID

        Returns:
            str: 消息ID
        """
        conn = self.get_connection()
        message_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        conn.execute(
            """INSERT OR IGNORE INTO chat_sessions (id, user_id, created_at, updated_at) VALUES (?, ?, ?, ?)""",
            (session_id, user_id, now, now)
        )

        # 保存消息
        conn.execute(
            """INSERT INTO chat_messages (id, session_id, role, content, sources, confidence, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (message_id, session_id, role, content, json.dumps(sources or []), confidence, now)
        )

        # 更新会话时间
        conn.execute(
            "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
            (now, session_id)
        )

        conn.commit()
        return message_id

    def get_chat_history(
        self,
        session_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        获取对话历史

        Args:
            session_id: 会话ID
            limit: 最大消息数量

        Returns:
            List[dict]: 消息列表
        """
        conn = self.get_connection()
        cursor = conn.execute(
            """SELECT id, role, content, sources, confidence, created_at
               FROM chat_messages WHERE session_id = ?
               ORDER BY created_at ASC LIMIT ?""",
            (session_id, limit)
        )
        messages = []
        for row in cursor.fetchall():
            msg = dict(row)
            if msg.get("sources"):
                try:
                    msg["sources"] = json.loads(msg["sources"])
                except json.JSONDecodeError:
                    msg["sources"] = []
            messages.append(msg)
        return messages

    def delete_chat_session(self, session_id: str) -> bool:
        """
        删除对话会话及其所有消息

        Args:
            session_id: 会话ID

        Returns:
            bool: 是否删除成功
        """
        conn = self.get_connection()
        # 先删除消息（外键级联删除）
        conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        cursor = conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
        conn.commit()
        return cursor.rowcount > 0

    # ========== 作业指引操作 ==========

    def save_guide(
        self,
        guide_id: str,
        title: str,
        task_description: str,
        guide_content: str,
        equipment_type: str = "",
        equipment_model: str = "",
        safety_level: str = "standard",
        created_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        保存作业指引

        Args:
            guide_id: 指引ID
            title: 标题
            task_description: 任务描述
            guide_content: 指引内容（JSON格式）
            equipment_type: 设备类型
            equipment_model: 设备型号
            safety_level: 安全等级
            created_by: 创建者ID

        Returns:
            dict: 指引信息
        """
        conn = self.get_connection()
        now = datetime.now().isoformat()
        conn.execute(
            """INSERT INTO guides (id, title, task_description, equipment_type, equipment_model, safety_level, guide_content, created_by, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (guide_id, title, task_description, equipment_type, equipment_model, safety_level, guide_content, created_by, now, now)
        )
        conn.commit()
        return {"id": guide_id, "title": title}

    def get_guide_by_id(self, guide_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取作业指引

        Args:
            guide_id: 指引ID

        Returns:
            Optional[dict]: 指引信息
        """
        conn = self.get_connection()
        cursor = conn.execute(
            "SELECT * FROM guides WHERE id = ?", (guide_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def list_guides(
        self,
        page: int = 1,
        page_size: int = 20,
        equipment_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取作业指引列表

        Args:
            page: 页码
            page_size: 每页数量
            equipment_type: 设备类型筛选

        Returns:
            dict: 指引列表和分页信息
        """
        conn = self.get_connection()

        where_clause = ""
        params: list = []
        if equipment_type:
            where_clause = "WHERE equipment_type = ?"
            params.append(equipment_type)

        count_result = conn.execute(
            f"SELECT COUNT(*) FROM guides {where_clause}", params
        ).fetchone()
        total = count_result[0]

        offset = (page - 1) * page_size
        cursor = conn.execute(
            f"SELECT * FROM guides {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset]
        )
        guides = [dict(row) for row in cursor.fetchall()]

        return {"guides": guides, "total": total}

    # ========== 日志操作 ==========

    def save_log(
        self,
        user_id: Optional[str],
        action: str,
        detail: str = "",
        ip_address: str = "",
    ) -> str:
        """
        保存系统操作日志

        Args:
            user_id: 操作用户ID
            action: 操作类型
            detail: 详细信息
            ip_address: IP地址

        Returns:
            str: 日志ID
        """
        conn = self.get_connection()
        log_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        conn.execute(
            """INSERT INTO logs (id, user_id, action, detail, ip_address, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (log_id, user_id, action, detail, ip_address, now)
        )
        conn.commit()
        return log_id

    def get_logs(
        self,
        page: int = 1,
        page_size: int = 50,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取系统日志列表

        Args:
            page: 页码
            page_size: 每页数量
            user_id: 用户ID筛选
            action: 操作类型筛选
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            dict: 日志列表和分页信息
        """
        conn = self.get_connection()

        conditions = []
        params: list = []

        if user_id:
            conditions.append("user_id = ?")
            params.append(user_id)
        if action:
            conditions.append("action = ?")
            params.append(action)
        if start_date:
            conditions.append("created_at >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("created_at <= ?")
            params.append(end_date)

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        count_result = conn.execute(
            f"SELECT COUNT(*) FROM logs {where_clause}", params
        ).fetchone()
        total = count_result[0]

        offset = (page - 1) * page_size
        cursor = conn.execute(
            f"SELECT * FROM logs {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset]
        )
        logs = [dict(row) for row in cursor.fetchall()]

        return {"logs": logs, "total": total}

    # ========== 系统配置操作 ==========

    def get_config(self, key: str) -> Optional[str]:
        """
        获取系统配置值

        Args:
            key: 配置键

        Returns:
            Optional[str]: 配置值
        """
        conn = self.get_connection()
        cursor = conn.execute(
            "SELECT value FROM system_config WHERE key = ?", (key,)
        )
        row = cursor.fetchone()
        return row["value"] if row else None

    def set_config(self, key: str, value: str, description: str = "") -> None:
        """
        设置系统配置值

        Args:
            key: 配置键
            value: 配置值
            description: 配置描述
        """
        conn = self.get_connection()
        now = datetime.now().isoformat()
        conn.execute(
            """INSERT INTO system_config (key, value, description, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = ?""",
            (key, value, description, now, value, now)
        )
        conn.commit()

    # ========== 统计操作 ==========

    def get_stats(self) -> Dict[str, Any]:
        """
        获取系统统计数据

        统计各表的数据量，用于系统管理页面展示。

        Returns:
            dict: 包含各表数据量的统计字典
        """
        conn = self.get_connection()

        # 文档总数
        doc_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        # 案例总数
        case_count = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
        # 对话消息总数（代表查询次数）
        query_count = conn.execute(
            "SELECT COUNT(*) FROM chat_messages WHERE role = 'user'"
        ).fetchone()[0]
        # 用户总数
        user_count = conn.execute(
            "SELECT COUNT(*) FROM users WHERE is_active = 1"
        ).fetchone()[0]
        # 作业指引总数
        guide_count = conn.execute("SELECT COUNT(*) FROM guides").fetchone()[0]
        # 反馈总数
        feedback_count = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
        # 审核待处理数
        pending_reviews = conn.execute(
            "SELECT COUNT(*) FROM cases WHERE status = 'pending_review'"
        ).fetchone()[0]

        # 数据库文件大小
        db_size_mb = 0.0
        try:
            if os.path.exists(self.db_path):
                db_size_mb = os.path.getsize(self.db_path) / (1024 * 1024)
        except Exception:
            pass

        return {
            "total_documents": doc_count,
            "total_cases": case_count,
            "total_queries": query_count,
            "total_users": user_count,
            "total_guides": guide_count,
            "total_feedback": feedback_count,
            "pending_reviews": pending_reviews,
            "db_size_mb": round(db_size_mb, 2),
        }


# 全局数据库单例
_db_instance: Optional[Database] = None


def get_database() -> Database:
    """
    获取全局数据库实例

    首次调用时自动初始化数据库表结构。

    Returns:
        Database: 全局数据库实例
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
        _db_instance.init_db()
    return _db_instance
