"""
公共UI工具模块

提供所有页面共享的UI工具函数和样式。
"""

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
