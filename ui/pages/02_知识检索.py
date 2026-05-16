"""
智能检修问答页面

提供统一的AI问答界面，支持两种输入模式：
- 文本问答：用户输入问题，AI基于所有已审批PDF知识库检索并回答
- 图片问答：用户上传设备故障图片，AI识别图片内容并结合知识库给出检修指导

界面设计：
- 顶部标题："智能检修问答"
- 模式切换：文本提问 / 图片提问
- 聊天对话界面
- AI回答时显示引用来源
- 侧边显示知识库信息
"""

import base64
import html
import streamlit as st
import requests

st.set_page_config(
    page_title="智能检修问答 - 设备检修知识系统",
    page_icon="🤖",
)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from ui.components.common import hide_login_nav, get_api_base, get_user_headers, require_login, init_api_base, safe_error_msg

hide_login_nav()
require_login()


@st.cache_data(ttl=60)
def fetch_kb_stats() -> dict:
    """获取知识库统计信息"""
    try:
        resp = requests.get(f"{get_api_base()}/admin/stats", headers=get_user_headers(), timeout=5)
        if resp.status_code == 200:
            return resp.json().get("data", {})
    except Exception:
        pass
    return {}


def render_chat_history(history_key: str):
    """渲染对话历史"""
    chat_history = st.session_state.get(history_key, [])

    if not chat_history:
        st.info("请输入您的问题，AI将基于知识库为您解答。")
        return

    for msg in chat_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        sources = msg.get("sources", [])
        image_base64 = msg.get("image_base64", "")

        if role == "user":
            safe_content = html.escape(content)
            st.markdown(f"""
            <div class="chat-message-user">
                <strong>👤 您：</strong><br>{safe_content}
            </div>
            """, unsafe_allow_html=True)

            if image_base64:
                try:
                    st.image(
                        base64.b64decode(image_base64),
                        caption="上传的图片",
                        width=300,
                    )
                except Exception:
                    pass
        else:
            safe_content = html.escape(content)
            st.markdown(f"""
            <div class="chat-message-assistant">
                <strong>🤖 AI助手：</strong><br>{safe_content}
            </div>
            """, unsafe_allow_html=True)

            if sources:
                with st.expander("📚 查看引用来源", expanded=False):
                    for j, src in enumerate(sources, 1):
                        src_name = src.get("source", f"来源{j}")
                        src_content = src.get("content", "")[:200]
                        src_page = src.get("page_number", "")
                        page_info = f" (第{src_page}页)" if src_page else ""
                        st.markdown(f"**来源 {j}**: {src_name}{page_info}")
                        st.caption(src_content + "..." if len(src.get("content", "")) > 200 else src_content)


def _send_question(question: str, session_id_key: str, history_key: str,
                   image_base64_str: str = None):
    """统一的问答发送函数"""
    chat_history = st.session_state.get(history_key, [])
    chat_history.append({
        "role": "user",
        "content": question,
        **({"image_base64": image_base64_str} if image_base64_str else {}),
    })

    spinner_msg = "AI正在分析图片并检索知识库..." if image_base64_str else "AI正在思考..."
    with st.spinner(spinner_msg):
        try:
            context = []
            for msg in chat_history[:-1]:
                if msg.get("role") in ("user", "assistant"):
                    context.append({
                        "role": msg["role"],
                        "content": msg["content"],
                    })

            payload = {
                "question": question,
                "session_id": st.session_state.get(session_id_key),
                "context": context if context else None,
                "search_mode": "hybrid",
                "top_k": 5,
            }
            if image_base64_str:
                payload["image_base64"] = image_base64_str

            timeout = 90 if image_base64_str else 60
            resp = requests.post(
                f"{get_api_base()}/chat/send",
                json=payload,
                headers=get_user_headers(),
                timeout=timeout,
            )

            if resp.status_code == 200:
                data = resp.json()
                answer = data["data"]["answer"]
                sources = data["data"].get("sources", [])
                session_id = data["data"]["session_id"]

                st.session_state[session_id_key] = session_id

                chat_history.append({
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                })

                st.rerun()
            else:
                error_data = resp.json()
                st.error(f"问答失败: {error_data.get('message', '未知错误')}")
                chat_history.pop()

        except requests.exceptions.ConnectionError:
            st.error("无法连接到后端服务，请确认服务已启动")
            chat_history.pop()
        except requests.exceptions.Timeout:
            st.error("请求超时，请稍后重试")
            chat_history.pop()
        except Exception:
            st.error(safe_error_msg("问答出错"))
            chat_history.pop()


def main():
    init_api_base()
    if "text_chat_history" not in st.session_state:
        st.session_state.text_chat_history = []
    if "image_chat_history" not in st.session_state:
        st.session_state.image_chat_history = []
    if "text_session_id" not in st.session_state:
        st.session_state.text_session_id = None
    if "image_session_id" not in st.session_state:
        st.session_state.image_session_id = None

    st.title("🤖 智能检修问答")

    mode_tab1, mode_tab2 = st.tabs(["💬 文本提问", "🖼️ 图片提问"])

    with mode_tab1:
        col_new, col_clear = st.columns([1, 1])
        with col_new:
            if st.button("新建对话", key="new_chat_text"):
                st.session_state.text_chat_history = []
                st.session_state.text_session_id = None
                st.rerun()
        with col_clear:
            if st.button("清空对话", key="clear_chat_text"):
                st.session_state.text_chat_history = []
                st.rerun()

        st.markdown("---")

        render_chat_history("text_chat_history")

        st.markdown("---")

        col_input, col_send = st.columns([5, 1])
        with col_input:
            text_question = st.text_input(
                "输入问题",
                placeholder="请输入您的检修问题...",
                key="text_question_input",
            )
        with col_send:
            st.markdown("<br>", unsafe_allow_html=True)
            send_clicked = st.button("发送", type="primary", width="stretch", key="text_send_btn")

        if send_clicked and text_question:
            _send_question(text_question, "text_session_id", "text_chat_history")

    with mode_tab2:
        col_new2, col_clear2 = st.columns([1, 1])
        with col_new2:
            if st.button("新建对话", key="new_chat_img"):
                st.session_state.image_chat_history = []
                st.session_state.image_session_id = None
                st.rerun()
        with col_clear2:
            if st.button("清空对话", key="clear_chat_img"):
                st.session_state.image_chat_history = []
                st.rerun()

        st.markdown("---")

        render_chat_history("image_chat_history")

        st.markdown("---")

        st.markdown("#### 上传设备故障图片")
        uploaded_file = st.file_uploader(
            "选择图片",
            type=["png", "jpg", "jpeg", "gif", "webp"],
            key="image_uploader",
        )

        if uploaded_file:
            st.image(uploaded_file, caption="待分析的图片", width=300)

        image_question = st.text_input(
            "问题描述（可选）",
            placeholder="请描述您的问题，例如：这个设备有什么故障？如何处理？",
            key="image_question_input",
        )

        if st.button("发送图片提问", type="primary", width="stretch", key="image_send_btn"):
            if not uploaded_file:
                st.warning("请先上传一张图片")
            else:
                image_bytes = uploaded_file.read()
                image_base64_str = base64.b64encode(image_bytes).decode("utf-8")
                q = image_question if image_question else "请识别这张图片中的设备故障并给出检修指导"
                _send_question(q, "image_session_id", "image_chat_history", image_base64_str)

    with st.sidebar:
        st.markdown("#### 📚 知识库信息")
        kb_stats = fetch_kb_stats()
        st.metric("已入库文档", kb_stats.get("document_count", 0))
        st.metric("总分块数", kb_stats.get("total_chunks", 0))
        st.caption("AI将基于以上知识库内容为您解答检修问题")


if __name__ == "__main__":
    main()
