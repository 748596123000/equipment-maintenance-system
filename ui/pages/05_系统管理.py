"""
系统管理页面（仅管理员可见）

提供系统管理功能：
- 系统统计仪表板
- 用户管理
- 操作日志
- 系统配置
- 索引管理
"""

import streamlit as st
import requests

st.set_page_config(
    page_title="系统管理 - 设备检修知识系统",
    page_icon="⚙️",
)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from ui.components.common import hide_login_nav, get_api_base, get_user_headers, require_admin, init_api_base, safe_error_msg

hide_login_nav()
require_admin()


def render_stats_dashboard():
    """渲染系统统计仪表板"""
    st.markdown("### 📊 系统统计")

    try:
        resp = requests.get(f"{get_api_base()}/admin/stats", headers=get_user_headers(), timeout=5)
        if resp.status_code == 200:
            stats = resp.json().get("data", {})

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("知识文档", stats.get("document_count", 0))
            with col2:
                st.metric("检修案例", stats.get("case_count", 0))
            with col3:
                st.metric("文本块总数", stats.get("total_chunks", 0))
            with col4:
                st.metric("对话会话", stats.get("chat_count", 0))

            col5, col6, col7, col8 = st.columns(4)
            with col5:
                st.metric("作业指引", stats.get("guide_count", 0))
            with col6:
                st.metric("注册用户", stats.get("user_count", 0))
            with col7:
                st.metric("数据库大小", f"{stats.get('db_size_mb', 0)} MB")
            with col8:
                chroma_status = stats.get("chroma_status", "unknown")
                status_text = {"healthy": "正常", "not_initialized": "未初始化", "error": "异常"}.get(chroma_status, chroma_status)
                st.metric("向量库状态", status_text)
        else:
            st.error("获取统计信息失败")

    except requests.exceptions.ConnectionError:
        st.error("无法连接到后端服务")
    except Exception as e:
        st.error("操作失败，请稍后重试")


def render_user_approval():
    """渲染用户审批标签页"""
    st.markdown("### 👤 用户审批")
    st.markdown("审批新注册用户的账号申请")

    try:
        headers = get_user_headers()
        resp = requests.get(
            f"{get_api_base()}/auth/pending-users",
            headers=headers,
            timeout=30,
        )

        if resp.status_code == 200:
            data = resp.json()
            users = data.get("data", {}).get("users", [])
            total = data.get("data", {}).get("total", 0)

            if total > 0:
                st.info(f"当前有 {total} 个用户等待审批")
            else:
                st.success("暂无待审批用户")

            if users:
                for user in users:
                    user_id = user.get("user_id", "")
                    username = user.get("username", "")
                    created_at = user.get("created_at", "")

                    with st.container():
                        col_info, col_actions = st.columns([3, 1])

                        with col_info:
                            st.markdown(f"**用户名**: {username}")
                            st.caption(f"注册时间: {created_at}")

                        with col_actions:
                            col_btn1, col_btn2 = st.columns(2)
                            with col_btn1:
                                if st.button("通过", type="primary", key=f"approve_{user_id}", width="stretch"):
                                    with st.spinner("正在审批..."):
                                        try:
                                            approve_resp = requests.post(
                                                f"{get_api_base()}/auth/{user_id}/approve",
                                                headers=headers,
                                                timeout=30,
                                            )
                                            if approve_resp.status_code == 200:
                                                st.success(f"用户 '{username}' 审批通过")
                                                st.rerun()
                                            else:
                                                error_data = approve_resp.json()
                                                st.error(f"审批失败: {error_data.get('detail', '未知错误')}")
                                        except Exception as e:
                                            st.error("操作失败，请稍后重试")

                            with col_btn2:
                                if st.button("拒绝", type="secondary", key=f"reject_{user_id}", width="stretch"):
                                    with st.spinner("正在拒绝..."):
                                        try:
                                            reject_resp = requests.post(
                                                f"{get_api_base()}/auth/{user_id}/reject",
                                                headers=headers,
                                                timeout=30,
                                            )
                                            if reject_resp.status_code == 200:
                                                st.success(f"已拒绝用户 '{username}' 的注册申请")
                                                st.rerun()
                                            else:
                                                error_data = reject_resp.json()
                                                st.error(f"拒绝失败: {error_data.get('detail', '未知错误')}")
                                        except Exception as e:
                                            st.error("操作失败，请稍后重试")

                        st.markdown("---")
        else:
            st.error("获取待审批用户列表失败")

    except requests.exceptions.ConnectionError:
        st.error("无法连接到后端服务")
    except Exception as e:
        st.error("操作失败，请稍后重试")


def render_user_management():
    """渲染用户管理"""
    st.markdown("### 👥 用户管理")

    # 创建用户表单
    with st.expander("创建新用户", expanded=False):
        with st.form("user_form"):
            col_u1, col_u2 = st.columns(2)
            with col_u1:
                username = st.text_input("用户名 *", placeholder="至少3个字符", key="new_username")
            with col_u2:
                password = st.text_input("密码 *", type="password", placeholder="至少6个字符", key="new_password")

            col_u3, col_u4 = st.columns(2)
            with col_u3:
                display_name = st.text_input("显示名称", key="new_display_name")
            with col_u4:
                role = st.selectbox(
                    "角色",
                    options=["viewer", "editor", "admin"],
                    format_func=lambda x: {
                        "viewer": "查看者",
                        "editor": "编辑者",
                        "admin": "管理员",
                    }.get(x, x),
                    key="new_role",
                )

            department = st.text_input("部门", placeholder="例如：变电检修班", key="new_department")
            create_clicked = st.form_submit_button("创建用户", type="primary", width="stretch")

        if create_clicked:
            if not username or not password:
                st.error("请填写用户名和密码")
                return

            with st.spinner("正在创建用户..."):
                try:
                    resp = requests.post(
                        f"{get_api_base()}/admin/users",
                        json={
                            "username": username,
                            "password": password,
                            "display_name": display_name,
                            "role": role,
                            "department": department,
                        },
                        headers=get_user_headers(),
                        timeout=30,
                    )

                    if resp.status_code == 200:
                        st.success(f"用户 '{username}' 创建成功")
                        st.rerun()
                    else:
                        error_data = resp.json()
                        st.error(f"创建失败: {error_data.get('message', '未知错误')}")

                except requests.exceptions.ConnectionError:
                    st.error("无法连接到后端服务")
                except Exception as e:
                    st.error("操作失败，请稍后重试")

    st.markdown("---")

    # 用户列表
    st.markdown("#### 用户列表")
    try:
        resp = requests.get(
            f"{get_api_base()}/admin/users",
            params={"page": 1, "page_size": 50},
            headers=get_user_headers(),
            timeout=30,
        )

        if resp.status_code == 200:
            data = resp.json()
            users = data.get("data", {}).get("users", [])

            if users:
                user_table = []
                user_ids = []
                for user in users:
                    role_map = {"admin": "管理员", "editor": "编辑者", "viewer": "查看者"}
                    user_table.append({
                        "用户名": user.get("username", ""),
                        "显示名称": user.get("display_name", ""),
                        "角色": role_map.get(user.get("role", ""), user.get("role", "")),
                        "部门": user.get("department", ""),
                        "状态": "启用" if user.get("is_active") else "禁用",
                        "创建时间": user.get("created_at", ""),
                    })
                    user_ids.append({
                        "id": user.get("id", user.get("user_id", "")),
                        "username": user.get("username", ""),
                    })

                st.dataframe(user_table, width="stretch", hide_index=True)

                # 删除用户
                st.markdown("---")
                st.markdown("#### 删除用户")
                deletable_users = [u for u in user_ids if u["username"] != "admin"]
                if deletable_users:
                    col_del1, col_del2 = st.columns([3, 1])
                    with col_del1:
                        del_user = st.selectbox(
                            "选择要删除的用户",
                            options=deletable_users,
                            format_func=lambda x: x["username"],
                            key="delete_user_select",
                        )
                    with col_del2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("🗑️ 删除用户", type="secondary", width="stretch", key="delete_user_btn"):
                            if del_user:
                                confirm_delete = st.checkbox("确认删除", key="confirm_delete_user")
                                if confirm_delete:
                                    with st.spinner("正在删除..."):
                                        try:
                                            resp = requests.delete(
                                                f"{get_api_base()}/admin/users/{del_user['id']}",
                                                headers=get_user_headers(),
                                                timeout=30,
                                            )
                                            if resp.status_code == 200:
                                                st.success(f"用户 '{del_user['username']}' 已删除")
                                                st.rerun()
                                            else:
                                                error_data = resp.json()
                                                st.error(f"删除失败: {error_data.get('detail', '未知错误')}")
                                        except requests.exceptions.ConnectionError:
                                            st.error("无法连接到后端服务")
                                        except Exception as e:
                                            st.error("操作失败，请稍后重试")
                                else:
                                    st.warning("请勾选确认删除")
                else:
                    st.info("没有可删除的用户（admin账户不可删除）")
            else:
                st.info("暂无用户记录")

    except requests.exceptions.ConnectionError:
        st.error("无法连接到后端服务")
    except Exception as e:
        st.error("操作失败，请稍后重试")


def render_operation_logs():
    """渲染操作日志"""
    st.markdown("### 📝 操作日志")

    col_log1, col_log2 = st.columns(2)
    with col_log1:
        log_level = st.selectbox(
            "日志级别",
            options=["全部", "INFO", "WARNING", "ERROR"],
            key="log_level_filter",
        )
    with col_log2:
        log_page = st.number_input("页码", min_value=1, value=1, key="log_page")

    try:
        params = {"page": log_page, "page_size": 50}
        if log_level != "全部":
            params["level"] = log_level

        resp = requests.get(
            f"{get_api_base()}/admin/logs",
            params=params,
            headers=get_user_headers(),
            timeout=30,
        )

        if resp.status_code == 200:
            data = resp.json()
            logs = data.get("data", {}).get("logs", [])
            pagination = data.get("data", {}).get("pagination", {})

            if logs:
                log_table = []
                for log in logs:
                    log_table.append({
                        "时间": log.get("created_at", ""),
                        "级别": log.get("level", ""),
                        "模块": log.get("module", ""),
                        "消息": log.get("message", ""),
                        "详情": log.get("details", ""),
                    })

                st.dataframe(log_table, width="stretch", hide_index=True)

                # 分页信息
                total = pagination.get("total", 0)
                total_pages = pagination.get("total_pages", 1)
                st.caption(f"共 {total} 条记录，第 {log_page}/{total_pages} 页")
            else:
                st.info("暂无日志记录")

    except requests.exceptions.ConnectionError:
        st.error("无法连接到后端服务")
    except Exception as e:
        st.error("操作失败，请稍后重试")


def render_system_config():
    """渲染系统配置"""
    st.markdown("### ⚙️ 系统配置")

    # 获取当前配置
    try:
        resp = requests.get(f"{get_api_base()}/admin/config", headers=get_user_headers(), timeout=5)
        if resp.status_code == 200:
            current_config = resp.json().get("data", {})
        else:
            current_config = {}
    except Exception:
        current_config = {}

    with st.form("config_form"):
        st.markdown("#### 模型配置")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            llm_model = st.text_input(
                "大语言模型",
                value=current_config.get("llm_model", ""),
                key="config_llm_model",
            )
        with col_m2:
            embedding_model = st.text_input(
                "Embedding模型",
                value=current_config.get("embedding_model", ""),
                key="config_embedding_model",
            )

        llm_temperature = st.slider(
            "生成温度",
            min_value=0.0,
            max_value=2.0,
            value=float(current_config.get("llm_temperature", 0.7)),
            step=0.1,
            key="config_temperature",
        )

        llm_max_tokens = st.number_input(
            "最大生成Token数",
            min_value=256,
            max_value=8192,
            value=int(current_config.get("llm_max_tokens", 2048)),
            step=256,
            key="config_max_tokens",
        )

        st.markdown("#### 检索配置")
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            chunk_size = st.number_input(
                "分块大小",
                min_value=100,
                max_value=2000,
                value=int(current_config.get("chunk_size", 500)),
                step=100,
                key="config_chunk_size",
            )
        with col_r2:
            chunk_overlap = st.number_input(
                "分块重叠",
                min_value=0,
                max_value=500,
                value=int(current_config.get("chunk_overlap", 50)),
                step=10,
                key="config_chunk_overlap",
            )

        col_r3, col_r4 = st.columns(2)
        with col_r3:
            top_k = st.number_input(
                "检索结果数",
                min_value=1,
                max_value=20,
                value=int(current_config.get("top_k_results", 5)),
                key="config_top_k",
            )
        with col_r4:
            score_threshold = st.slider(
                "相似度阈值",
                min_value=0.0,
                max_value=1.0,
                value=float(current_config.get("retriever_score_threshold", 0.3)),
                step=0.05,
                key="config_threshold",
            )

        update_clicked = st.form_submit_button("保存配置", type="primary", width="stretch")

    if update_clicked:
        with st.spinner("正在更新配置..."):
            try:
                resp = requests.put(
                    f"{get_api_base()}/admin/config",
                    json={
                        "llm_model": llm_model if llm_model != current_config.get("llm_model") else None,
                        "llm_temperature": llm_temperature if llm_temperature != float(current_config.get("llm_temperature", 0.7)) else None,
                        "chunk_size": chunk_size if chunk_size != int(current_config.get("chunk_size", 500)) else None,
                        "chunk_overlap": chunk_overlap if chunk_overlap != int(current_config.get("chunk_overlap", 50)) else None,
                        "top_k_results": top_k if top_k != int(current_config.get("top_k_results", 5)) else None,
                        "retriever_score_threshold": score_threshold if score_threshold != float(current_config.get("retriever_score_threshold", 0.3)) else None,
                    },
                    headers=get_user_headers(),
                    timeout=30,
                )

                if resp.status_code == 200:
                    st.success("配置更新成功（运行时生效）")
                else:
                    error_data = resp.json()
                    st.error(f"更新失败: {error_data.get('message', '未知错误')}")

            except requests.exceptions.ConnectionError:
                st.error("无法连接到后端服务")
            except Exception as e:
                st.error("操作失败，请稍后重试")


def render_index_management():
    """渲染索引管理"""
    st.markdown("### 🔍 索引管理")

    # 健康检查
    st.markdown("#### 系统健康状态")
    try:
        resp = requests.get(f"{get_api_base()}/admin/health", headers=get_user_headers(), timeout=5)
        if resp.status_code == 200:
            health = resp.json().get("data", {})
            components = health.get("components", {})

            col_h1, col_h2, col_h3, col_h4 = st.columns(4)
            with col_h1:
                db_status = components.get("database", {})
                db_ok = db_status.get("status") == "healthy"
                st.metric("数据库", "正常" if db_ok else "异常")
            with col_h2:
                chroma_status = components.get("chromadb", {})
                chroma_ok = chroma_status.get("status") == "healthy"
                st.metric("向量库", "正常" if chroma_ok else "异常")
            with col_h3:
                llm_status = components.get("llm", {})
                llm_ok = llm_status.get("status") == "healthy"
                st.metric("大模型", "正常" if llm_ok else "不可用")
            with col_h4:
                emb_status = components.get("embedding", {})
                emb_ok = emb_status.get("status") == "healthy"
                st.metric("Embedding", "正常" if emb_ok else "不可用")
        else:
            st.error("健康检查失败")

    except requests.exceptions.ConnectionError:
        st.error("无法连接到后端服务")
    except Exception as e:
        st.error("操作失败，请稍后重试")

    st.markdown("---")

    # 重建索引
    st.markdown("#### 索引操作")
    st.warning("重建索引将重新处理所有文档，可能需要较长时间")

    if st.button("重建向量索引", type="primary", key="reindex_btn"):
        with st.spinner("正在重建索引..."):
            try:
                resp = requests.post(
                    f"{get_api_base()}/admin/reindex",
                    headers=get_user_headers(),
                    timeout=300,
                )

                if resp.status_code == 200:
                    result = resp.json().get("data", {})
                    st.success(f"索引重建完成: {result.get('message', '成功')}")
                else:
                    error_data = resp.json()
                    st.error(f"重建失败: {error_data.get('message', '未知错误')}")

            except requests.exceptions.ConnectionError:
                st.error("无法连接到后端服务")
            except requests.exceptions.Timeout:
                st.error("索引重建超时，请稍后在系统日志中查看进度")
            except Exception as e:
                st.error("操作失败，请稍后重试")


def main():
    init_api_base()

    st.title("⚙️ 系统管理")

    # 六个标签页
    tab_stats, tab_approval, tab_users, tab_logs, tab_config, tab_index = st.tabs([
        "📊 系统统计",
        "👤 用户审批",
        "👥 用户管理",
        "📝 操作日志",
        "⚙️ 系统配置",
        "🔍 索引管理",
    ])

    with tab_stats:
        render_stats_dashboard()

    with tab_approval:
        render_user_approval()

    with tab_users:
        render_user_management()

    with tab_logs:
        render_operation_logs()

    with tab_config:
        render_system_config()

    with tab_index:
        render_index_management()


if __name__ == "__main__":
    main()
