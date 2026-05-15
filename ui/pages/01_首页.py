"""
首页 - 系统介绍与快速入口

展示系统概览信息，根据用户角色提供不同的快速入口：
- 普通用户：知识检索、作业指引、我的上传 + 我的上传统计
- 管理员：知识检索、作业指引、文档审批、系统管理 + 待审批数量提醒
"""

import streamlit as st
import requests

st.set_page_config(
    page_title="首页 - 设备检修知识库学习平台",
    page_icon="🏠",
)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from ui.components.common import hide_login_nav
hide_login_nav()

# ========== 登录检查 ==========
if "user_info" not in st.session_state:
    st.switch_page("pages/00_登录.py")
    st.stop()

# ========== 动画CSS样式 ==========
st.markdown("""
<style>
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    .animated-header {
        background: linear-gradient(-45deg, #1a73e8, #e91e63, #ff9800, #4caf50, #9c27b0);
        background-size: 400% 400%;
        animation: gradientShift 8s ease infinite;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.2rem;
        font-weight: bold;
        text-align: center;
        padding: 1rem 0;
    }


</style>
""", unsafe_allow_html=True)


def get_api_base() -> str:
    """获取API基础地址"""
    return st.session_state.get("api_base_url", "http://localhost:8000/api/v1")


def get_user_headers() -> dict:
    """获取包含用户信息的请求头"""
    user_info = st.session_state.get("user_info", {})
    return {"Authorization": f"Bearer {user_info.get('token', '')}"}


def fetch_system_stats() -> dict:
    """从API获取系统统计数据"""
    try:
        resp = requests.get(f"{get_api_base()}/admin/stats", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("data", {})
    except Exception:
        pass
    return {}


def fetch_pending_count() -> int:
    """获取待审批文档数量"""
    try:
        resp = requests.get(
            f"{get_api_base()}/upload/pending",
            headers=get_user_headers(),
            params={"page": 1, "page_size": 1},
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("data", {}).get("pagination", {}).get("total", 0)
    except Exception:
        pass
    return 0


def fetch_my_upload_count() -> dict:
    """获取当前用户的上传统计"""
    try:
        resp = requests.get(
            f"{get_api_base()}/upload/my",
            headers=get_user_headers(),
            params={"page": 1, "page_size": 100},
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            documents = data.get("data", {}).get("documents", [])
            stats = {
                "total": len(documents),
                "pending": 0,
                "approved": 0,
                "rejected": 0,
                "processing": 0,
                "completed": 0,
            }
            for doc in documents:
                status = doc.get("status", "")
                if status in stats:
                    stats[status] += 1
            return stats
    except Exception:
        pass
    return {"total": 0, "pending": 0, "approved": 0, "rejected": 0, "processing": 0, "completed": 0}


def render_user_home():
    """渲染普通用户首页"""
    st.markdown('<div class="animated-header">🔧 设备检修知识库</div>', unsafe_allow_html=True)
    st.markdown("---")

    # 系统定位说明
    st.markdown("""
    <div class="card card-blue">
        <p>本系统汇集设备检修知识，帮助您从零开始学习设备检修技能。通过AI智能问答，快速获取检修方案和操作指引。</p>
    </div>
    """, unsafe_allow_html=True)

    # 欢迎信息
    user_info = st.session_state.get("user_info", {})
    st.markdown(f"### 欢迎回来，{user_info.get('username', '用户')}")

    # 我的上传统计
    my_stats = fetch_my_upload_count()
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="我的上传",
            value=my_stats.get("total", 0),
            delta="总文档数",
        )
    with col2:
        st.metric(
            label="待审核",
            value=my_stats.get("pending", 0),
            delta="等待审批",
        )
    with col3:
        st.metric(
            label="已通过",
            value=my_stats.get("approved", 0) + my_stats.get("completed", 0),
            delta="审批通过",
        )
    with col4:
        st.metric(
            label="已拒绝",
            value=my_stats.get("rejected", 0),
            delta="需要修改",
        )

    st.markdown("---")

    # 快速入口
    st.markdown("## 🚀 快速入口")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="card card-blue">
            <h3>🔍 知识检索</h3>
            <p>在设备检修知识库中快速查找所需信息</p>
            <ul>
                <li>语义检索</li>
                <li>关键词检索</li>
                <li>图片检索</li>
                <li>设备型号检索</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        if st.button("进入知识检索", width="stretch", type="primary", key="quick_search"):
            st.switch_page("pages/02_知识检索.py")

    with col2:
        st.markdown("""
        <div class="card card-green">
            <h3>📋 作业指引</h3>
            <p>AI智能生成检修作业指引</p>
            <ul>
                <li>步骤化指引</li>
                <li>安全警告</li>
                <li>工具清单</li>
                <li>完成标准</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        if st.button("生成作业指引", width="stretch", type="primary", key="quick_guide"):
            st.switch_page("pages/03_作业指引.py")

    with col3:
        st.markdown("""
        <div class="card card-orange">
            <h3>📤 我的上传</h3>
            <p>上传和管理我的文档</p>
            <ul>
                <li>上传PDF文件</li>
                <li>查看上传状态</li>
                <li>审批进度跟踪</li>
                <li>文档管理</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        if st.button("进入我的上传", width="stretch", type="primary", key="quick_upload"):
            st.switch_page("pages/04_知识管理.py")

    st.markdown("---")

    # AI问答快速入口
    st.markdown("## 💬 快速问答")
    st.markdown("输入您的问题，AI将基于知识库为您解答：")

    col_q, col_b = st.columns([5, 1])
    with col_q:
        question = st.text_input(
            "请输入问题",
            placeholder="例如：变压器油温过高的处理方法是什么？",
            key="quick_question",
        )
    with col_b:
        st.markdown("<br>", unsafe_allow_html=True)
        ask_clicked = st.button("提问", type="primary", key="quick_ask", width="stretch")

    if ask_clicked or (question and st.button("搜索", key="quick_ask_btn")):
        if question:
            st.session_state["quick_question"] = question
            st.switch_page("pages/02_知识检索.py")
        else:
            st.warning("请输入问题")


def render_admin_home():
    """渲染管理员首页"""
    st.markdown('<div class="animated-header">🔧 设备检修知识库</div>', unsafe_allow_html=True)
    st.markdown("---")

    # 系统定位说明
    st.markdown("""
    <div class="card card-blue">
        <p>本系统汇集设备检修知识，帮助您从零开始学习设备检修技能。通过AI智能问答，快速获取检修方案和操作指引。</p>
    </div>
    """, unsafe_allow_html=True)

    # 欢迎信息
    user_info = st.session_state.get("user_info", {})
    st.markdown(f"### 欢迎回来，{user_info.get('username', '管理员')}")

    # 获取系统统计
    stats = fetch_system_stats()
    pending_count = fetch_pending_count()

    # 系统状态卡片
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="知识文档",
            value=stats.get("document_count", 0),
            delta="已入库",
        )
    with col2:
        st.metric(
            label="检修案例",
            value=stats.get("case_count", 0),
            delta="知识沉淀",
        )
    with col3:
        st.metric(
            label="待审批文档",
            value=pending_count,
            delta="需要处理" if pending_count > 0 else "无待审批",
            delta_color="off" if pending_count == 0 else "normal",
        )
    with col4:
        st.metric(
            label="注册用户",
            value=stats.get("user_count", 0),
            delta="系统用户",
        )

    # 待审批提醒
    if pending_count > 0:
        st.warning(f"⚠️ 当前有 **{pending_count}** 个文档等待审批，请及时处理！")

    st.markdown("---")

    # 快速入口
    st.markdown("## 🚀 快速入口")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("""
        <div class="card card-blue animated-card">
            <h3>🔍 知识检索</h3>
            <p>在设备检修知识库中快速查找所需信息</p>
            <ul>
                <li>语义检索</li>
                <li>关键词检索</li>
                <li>图片检索</li>
                <li>设备型号检索</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        if st.button("进入知识检索", width="stretch", type="primary", key="quick_search"):
            st.switch_page("pages/02_知识检索.py")

    with col2:
        st.markdown("""
        <div class="card card-green">
            <h3>📋 作业指引</h3>
            <p>AI智能生成检修作业指引</p>
            <ul>
                <li>步骤化指引</li>
                <li>安全警告</li>
                <li>工具清单</li>
                <li>完成标准</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        if st.button("生成作业指引", width="stretch", type="primary", key="quick_guide"):
            st.switch_page("pages/03_作业指引.py")

    with col3:
        st.markdown("""
        <div class="card card-orange">
            <h3>📝 文档审批</h3>
            <p>审批用户上传的文档</p>
            <ul>
                <li>待审批列表</li>
                <li>审批通过/拒绝</li>
                <li>审批意见</li>
                <li>自动处理入库</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        if st.button("进入文档审批", width="stretch", type="primary", key="quick_approve"):
            st.switch_page("pages/04_知识管理.py")

    with col4:
        st.markdown("""
        <div class="card card-purple">
            <h3>⚙️ 系统管理</h3>
            <p>系统配置和监控</p>
            <ul>
                <li>用户管理</li>
                <li>系统配置</li>
                <li>操作日志</li>
                <li>索引管理</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        if st.button("进入系统管理", width="stretch", type="primary", key="quick_admin"):
            st.switch_page("pages/05_系统管理.py")

    st.markdown("---")

    # AI问答快速入口
    st.markdown("## 💬 快速问答")
    st.markdown("输入您的问题，AI将基于知识库为您解答：")

    col_q, col_b = st.columns([5, 1])
    with col_q:
        question = st.text_input(
            "请输入问题",
            placeholder="例如：变压器油温过高的处理方法是什么？",
            key="quick_question",
        )
    with col_b:
        st.markdown("<br>", unsafe_allow_html=True)
        ask_clicked = st.button("提问", type="primary", key="quick_ask", width="stretch")

    if ask_clicked or (question and st.button("搜索", key="quick_ask_btn")):
        if question:
            st.session_state["quick_question"] = question
            st.switch_page("pages/02_知识检索.py")
        else:
            st.warning("请输入问题")

    st.markdown("---")

    # 系统信息
    st.markdown("## 📊 系统信息")

    col_info1, col_info2 = st.columns(2)

    with col_info1:
        st.markdown("""
        ### 技术架构
        - **后端框架**: FastAPI (Python)
        - **前端框架**: Streamlit
        - **向量数据库**: ChromaDB
        - **关系数据库**: SQLite
        - **大语言模型**: 通义千问 Qwen
        - **Embedding模型**: text-embedding-v3
        """)

    with col_info2:
        st.markdown("""
        ### 系统特性
        - **多模式检索**: 语义、关键词、混合、型号、图片
        - **RAG问答**: 检索增强生成，精准回答
        - **审批流程**: PDF上传审批后自动解析入库
        - **角色权限**: 管理员/普通用户分离
        - **安全可靠**: 完善的权限和日志管理
        """)


def main():
    """页面主函数"""
    # 初始化API地址
    if "api_base_url" not in st.session_state:
        st.session_state.api_base_url = "http://localhost:8000/api/v1"

    # 根据用户角色渲染不同首页
    user_info = st.session_state.get("user_info", {})
    user_role = user_info.get("role", "")

    if user_role == "admin":
        render_admin_home()
    else:
        render_user_home()


if __name__ == "__main__":
    main()
