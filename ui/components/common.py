"""
公共UI工具模块

提供所有页面共享的UI工具函数和样式。
"""

import os
import streamlit as st


def hide_login_nav():
    """隐藏侧边栏中的'登录'页面链接"""
    st.markdown("""
    <style>
        [data-testid="stSidebarNav"] [href*="%E7%99%BB%E5%BD%95"] {
            display: none !important;
        }
    </style>
    """, unsafe_allow_html=True)


def get_api_base() -> str:
    if "api_base_url" not in st.session_state:
        st.session_state.api_base_url = os.environ.get(
            "API_BASE_URL", "http://localhost:8000/api/v1"
        )
    return st.session_state.api_base_url


def get_user_headers() -> dict:
    user_info = st.session_state.get("user_info", {})
    token = user_info.get("token", "")
    return {"Authorization": f"Bearer {token}"}


def require_login():
    if "user_info" not in st.session_state:
        st.warning("请先登录")
        st.switch_page("app.py")
        st.stop()


def require_admin():
    require_login()
    if st.session_state.get("user_info", {}).get("role") != "admin":
        st.error("需要管理员权限")
        st.stop()


def init_api_base():
    if "api_base_url" not in st.session_state:
        st.session_state.api_base_url = os.environ.get(
            "API_BASE_URL", "http://localhost:8000/api/v1"
        )


def safe_error_msg(prefix: str = "操作失败") -> str:
    """返回用户友好的错误提示，不暴露内部异常详情"""
    return prefix + "，请稍后重试"
