"""
Streamlit前端主入口

系统前端界面入口，配置：
- 页面布局和主题
- 自定义CSS样式（现代化深色/浅色主题，专业工业风格）
- 侧边栏导航（根据用户角色显示不同菜单）
- 全局状态管理
- API服务地址配置
- 登录状态检查
"""

import os
import streamlit as st

# ========== 页面基础配置 ==========
st.set_page_config(
    page_title="设备检修知识库学习平台",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 隐藏Streamlit默认的多页面导航中的"登录"页面链接
st.markdown("""
<style>
    [data-testid="stSidebarNav"] [href*="%E7%99%BB%E5%BD%95"] {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)


# ========== 自定义CSS样式 ==========
st.markdown("""
<style>
    /* ========== 全局样式 ========== */
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1a73e8;
        text-align: center;
        padding: 1rem 0;
    }

    /* ========== 侧边栏样式 ========== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a237e 0%, #283593 100%);
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: #ffffff;
    }
    [data-testid="stSidebar"] .stRadio label {
        color: #e8eaf6;
    }
    [data-testid="stSidebar"] h3, [data-testid="stSidebar"] h4 {
        color: #bbdefb !important;
    }

    /* ========== 卡片样式 ========== */
    .card {
        background: linear-gradient(135deg, #ffffff 0%, #f5f7fa 100%);
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        margin-bottom: 1rem;
        border: 1px solid #e0e0e0;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
    }
    .card-blue {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        border-left: 4px solid #1565c0;
    }
    .card-green {
        background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
        border-left: 4px solid #2e7d32;
    }
    .card-orange {
        background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
        border-left: 4px solid #ef6c00;
    }
    .card-purple {
        background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%);
        border-left: 4px solid #7b1fa2;
    }

    /* ========== 搜索结果高亮 ========== */
    .search-highlight {
        background-color: #fff9c4;
        padding: 2px 4px;
        border-radius: 3px;
        font-weight: bold;
    }

    /* ========== 聊天消息样式 ========== */
    .chat-message-user {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        padding: 1rem 1.2rem;
        border-radius: 12px 12px 4px 12px;
        margin-bottom: 0.8rem;
        border: 1px solid #90caf9;
    }
    .chat-message-assistant {
        background: linear-gradient(135deg, #fafafa 0%, #eeeeee 100%);
        padding: 1rem 1.2rem;
        border-radius: 12px 12px 12px 4px;
        margin-bottom: 0.8rem;
        border: 1px solid #e0e0e0;
    }

    /* ========== 按钮样式增强 ========== */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #1565c0 0%, #1976d2 100%);
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        transition: all 0.2s;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #0d47a1 0%, #1565c0 100%);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(21,101,192,0.4);
    }

    /* ========== 指标卡片 ========== */
    [data-testid="stMetric"] {
        background: #ffffff;
        border-radius: 8px;
        padding: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        border: 1px solid #e0e0e0;
    }

    /* ========== 表格样式 ========== */
    [data-testid="stDataFrame"] {
        border-radius: 8px;
        overflow: hidden;
    }

    /* ========== 标签页样式 ========== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        font-weight: 600;
    }

    /* ========== 步骤卡片 ========== */
    .step-card {
        background: #ffffff;
        border-radius: 10px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        border: 1px solid #e0e0e0;
        border-left: 5px solid #1565c0;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    }
    .step-number {
        display: inline-block;
        background: #1565c0;
        color: white;
        width: 32px;
        height: 32px;
        line-height: 32px;
        text-align: center;
        border-radius: 50%;
        font-weight: bold;
        margin-right: 8px;
    }

    /* ========== 状态标签 ========== */
    .status-processing {
        background-color: #fff3e0;
        color: #e65100;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.85rem;
    }
    .status-completed {
        background-color: #e8f5e9;
        color: #2e7d32;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.85rem;
    }
    .status-failed {
        background-color: #ffebee;
        color: #c62828;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.85rem;
    }
    .status-pending {
        background-color: #e3f2fd;
        color: #1565c0;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.85rem;
    }
    .status-approved {
        background-color: #e8f5e9;
        color: #2e7d32;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.85rem;
    }
    .status-rejected {
        background-color: #ffebee;
        color: #c62828;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.85rem;
    }

    /* ========== 分隔线 ========== */
    hr {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, #90caf9, transparent);
        margin: 1.5rem 0;
    }

    /* ========== 用户信息卡片 ========== */
    .user-info-card {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 1rem;
        margin-top: 1rem;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """
    初始化Streamlit会话状态

    管理全局状态变量，包括：
    - API服务地址
    - 用户登录状态
    - 对话历史
    - 检索结果缓存
    """
    # API配置
    if "api_base_url" not in st.session_state:
        st.session_state.api_base_url = os.environ.get("API_BASE_URL", "http://localhost:8000/api/v1")

    # 用户状态
    if "user_logged_in" not in st.session_state:
        st.session_state.user_logged_in = False
    if "current_user" not in st.session_state:
        st.session_state.current_user = None

    # 对话状态
    if "chat_session_id" not in st.session_state:
        st.session_state.chat_session_id = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # 检索状态
    if "search_results" not in st.session_state:
        st.session_state.search_results = []
    if "last_query" not in st.session_state:
        st.session_state.last_query = ""


@st.cache_data(ttl=30)
def _check_backend_health(api_base: str) -> bool:
    try:
        import requests
        resp = requests.get(f"{api_base.replace('/api/v1', '')}/health", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


def render_sidebar():
    """
    渲染侧边栏

    根据用户角色显示不同的导航菜单：
    - 普通用户：首页、知识检索、作业指引、我的上传
    - 管理员：首页、知识检索、作业指引、文档审批、知识管理、系统管理
    """
    with st.sidebar:
        # 系统标题
        st.markdown("### 🔧 检修知识库")
        st.markdown("---")

        # 获取用户信息
        user_info = st.session_state.get("user_info", {})
        user_role = user_info.get("role", "")
        username = user_info.get("username", "")

        # 根据角色显示导航菜单
        if user_role == "admin":
            st.markdown("#### 📋 导航菜单")

            pages = {
                "🏠 首页": "pages/01_首页.py",
                "🔍 知识检索": "pages/02_知识检索.py",
                "📋 作业指引": "pages/03_作业指引.py",
                "📝 文档审批": "pages/04_知识管理.py",
                "📚 PDF数据库": "pages/06_PDF数据库.py",
                "⚙️ 系统管理": "pages/05_系统管理.py",
            }

            for label, page in pages.items():
                if st.button(label, key=f"nav_{label}", use_container_width=True):
                    st.switch_page(page)
        else:
            st.markdown("#### 📋 导航菜单")

            pages = {
                "🏠 首页": "pages/01_首页.py",
                "🔍 知识检索": "pages/02_知识检索.py",
                "📋 作业指引": "pages/03_作业指引.py",
                "📤 我的上传": "pages/04_知识管理.py",
                "📚 知识库": "pages/07_知识库.py",
            }

            for label, page in pages.items():
                if st.button(label, key=f"nav_{label}", use_container_width=True):
                    st.switch_page(page)

        st.markdown("---")

        # 系统状态
        st.markdown("#### 📊 系统状态")
        if _check_backend_health(st.session_state.api_base_url):
            st.success("✅ 后端服务运行正常")
        else:
            st.warning("⚠️ 后端服务未连接")

        # API配置（地址仅从环境变量/配置读取，不允许用户修改）
        st.markdown("#### 🔗 API配置")
        st.caption(f"API地址: `{st.session_state.api_base_url}`")

        st.markdown("---")

        # 用户信息卡片
        st.markdown("""
        <div class="user-info-card">
        """, unsafe_allow_html=True)

        role_display = "管理员" if user_role == "admin" else "普通用户"
        st.markdown(f"**👤 {username}**")
        st.caption(f"角色：{role_display}")

        st.markdown("</div>", unsafe_allow_html=True)

        # 退出登录按钮
        if st.button("🚪 退出登录", width="stretch", type="secondary", key="logout_btn"):
            # 清除所有session_state
            st.session_state.clear()
            # 清除所有URL参数
            for key in list(st.query_params.keys()):
                del st.query_params[key]
            st.rerun()

        st.markdown("---")
        st.caption("设备检修知识库学习平台 v1.0.0")


def main():
    """主入口函数 - 初始化会话状态、登录检查和页面跳转"""
    # 初始化会话状态
    init_session_state()

    # 登录检查和页面跳转
    if "user_info" in st.session_state:
        # 已登录，渲染侧边栏并跳转到首页
        render_sidebar()
        st.switch_page("pages/01_首页.py")
    else:
        # 未登录，跳转到登录页
        st.switch_page("pages/00_登录.py")


if __name__ == "__main__":
    main()
