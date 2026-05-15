"""
登录页面

提供用户登录和注册功能：
- 用户名+密码登录
- 新用户注册
- 登录成功后跳转到首页
"""

import streamlit as st
import requests

st.set_page_config(
    page_title="登录 - 设备检修知识库学习平台",
    page_icon="🔧",
    initial_sidebar_state="collapsed",
)

# ========== 自定义CSS样式 ==========
st.markdown("""
<style>
    /* 隐藏侧边栏 */
    [data-testid="stSidebar"] {
        display: none;
    }

    /* 登录卡片样式 */
    .login-container {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 80vh;
    }

    .login-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9ff 100%);
        border-radius: 16px;
        padding: 2.5rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        border: 1px solid #e0e4f0;
        max-width: 420px;
        width: 100%;
        margin: 0 auto;
    }

    .login-header {
        text-align: center;
        margin-bottom: 2rem;
    }

    .login-header h1 {
        font-size: 1.8rem;
        font-weight: bold;
        color: #1a237e;
        margin-bottom: 0.5rem;
    }

    .login-header p {
        color: #666;
        font-size: 0.95rem;
    }

    .login-divider {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, #c5cae9, transparent);
        margin: 1.5rem 0;
    }

    .login-footer {
        text-align: center;
        margin-top: 1.5rem;
        color: #999;
        font-size: 0.85rem;
    }

    .register-link {
        text-align: center;
        margin-top: 1rem;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)


def get_api_base() -> str:
    """获取API基础地址"""
    return st.session_state.get("api_base_url", "http://localhost:8000/api/v1")


def do_login(username: str, password: str) -> bool:
    """
    执行登录操作

    Args:
        username: 用户名
        password: 密码

    Returns:
        bool: 是否登录成功
    """
    try:
        resp = requests.post(
            f"{get_api_base()}/auth/login",
            json={"username": username, "password": password},
            timeout=30,
        )

        if resp.status_code == 200:
            data = resp.json()["data"]
            # 将用户信息存入session_state
            user_info = {
                "user_id": data["user_id"],
                "username": data["username"],
                "role": data["role"],
                "token": data["token"],
            }
            st.session_state["user_info"] = user_info
            return True
        else:
            error_data = resp.json()
            detail = error_data.get("detail", "登录失败")
            if "待管理员审批" in detail:
                st.warning("您的账号正在等待管理员审批，请耐心等待。")
            elif "已被拒绝" in detail:
                st.error("您的账号注册已被拒绝，请联系管理员。")
            else:
                st.error(detail)
            return False

    except requests.exceptions.ConnectionError:
        st.error("无法连接到后端服务，请确认服务已启动")
        return False
    except Exception as e:
        st.error(f"登录出错: {str(e)}")
        return False


def do_register(username: str, password: str) -> bool:
    """
    执行注册操作

    Args:
        username: 用户名
        password: 密码

    Returns:
        bool: 是否注册成功
    """
    try:
        resp = requests.post(
            f"{get_api_base()}/auth/register",
            json={"username": username, "password": password},
            timeout=30,
        )

        if resp.status_code == 200:
            st.success("注册成功，请等待管理员审批后登录")
            return True
        else:
            error_data = resp.json()
            st.error(error_data.get("detail", "注册失败"))
            return False

    except requests.exceptions.ConnectionError:
        st.error("无法连接到后端服务，请确认服务已启动")
        return False
    except Exception as e:
        st.error(f"注册出错: {str(e)}")
        return False


def render_login_form():
    """渲染登录表单"""
    st.markdown("""
    <div class="login-card">
        <div class="login-header">
            <h1>🔧 设备检修知识库学习平台</h1>
            <p>汇集设备检修知识，AI智能辅助学习与检修指导</p>
        </div>
        <hr class="login-divider">
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        username = st.text_input(
            "用户名",
            placeholder="请输入用户名",
            key="login_username",
        )
        password = st.text_input(
            "密码",
            type="password",
            placeholder="请输入密码",
            key="login_password",
        )

        login_clicked = st.form_submit_button(
            "登 录",
            type="primary",
            width="stretch",
        )

    if login_clicked:
        if not username or not password:
            st.warning("请输入用户名和密码")
            return

        with st.spinner("正在登录..."):
            if do_login(username, password):
                st.success("登录成功，正在跳转...")
                st.switch_page("pages/01_首页.py")

    st.markdown('<hr class="login-divider">', unsafe_allow_html=True)

    # 注册区域
    st.markdown('<div class="register-link">', unsafe_allow_html=True)
    st.markdown("#### 还没有账号？")
    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("注册新账号", expanded=False):
        with st.form("register_form"):
            reg_username = st.text_input(
                "用户名",
                placeholder="至少3个字符",
                key="reg_username",
            )
            reg_password = st.text_input(
                "密码",
                type="password",
                placeholder="至少6个字符",
                key="reg_password",
            )
            reg_password_confirm = st.text_input(
                "确认密码",
                type="password",
                placeholder="再次输入密码",
                key="reg_password_confirm",
            )

            register_clicked = st.form_submit_button(
                "注 册",
                type="secondary",
                width="stretch",
            )

        if register_clicked:
            if not reg_username or not reg_password:
                st.warning("请填写用户名和密码")
                return
            if len(reg_username) < 3:
                st.warning("用户名至少需要3个字符")
                return
            if len(reg_password) < 6:
                st.warning("密码至少需要6个字符")
                return
            if reg_password != reg_password_confirm:
                st.warning("两次输入的密码不一致")
                return

            with st.spinner("正在注册..."):
                do_register(reg_username, reg_password)

    st.markdown("""
    <hr class="login-divider">
    <div class="login-footer">
        <p>设备检修知识库学习平台 v1.0.0</p>
    </div>
    </div>
    """, unsafe_allow_html=True)


def main():
    """页面主函数"""
    # 如果已登录，直接跳转到首页
    if "user_info" in st.session_state:
        st.switch_page("pages/01_首页.py")
        return

    # 初始化API地址
    if "api_base_url" not in st.session_state:
        st.session_state.api_base_url = "http://localhost:8000/api/v1"

    # 渲染登录表单
    render_login_form()


if __name__ == "__main__":
    main()
