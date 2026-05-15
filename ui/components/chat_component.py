"""
聊天组件

提供可复用的聊天界面组件，支持：
- 渲染聊天界面
- 显示单条消息（用户/AI不同样式）
- 显示引用来源
- 获取用户输入
"""

import html
import streamlit as st
import requests
from typing import List, Optional, Dict


class ChatComponent:
    """
    聊天界面组件

    封装聊天交互逻辑，提供统一的聊天界面渲染能力。
    支持多轮对话、引用来源展示和会话管理。
    """

    def __init__(self, api_base_url: str = "http://localhost:8000/api/v1"):
        """
        初始化聊天组件

        Args:
            api_base_url: 后端API基础地址
        """
        self.api_base_url = api_base_url

    def _get_auth_headers(self) -> dict:
        try:
            import streamlit as st
            user_info = st.session_state.get("user_info", {})
            token = user_info.get("token", "")
            if token:
                return {"Authorization": f"Bearer {token}"}
        except Exception:
            pass
        return {}

    def render(
        self,
        session_key: str = "default",
        title: str = "AI智能问答",
        placeholder: str = "请输入您的问题...",
        show_history: bool = True,
        search_mode: str = "hybrid",
        top_k: int = 5,
    ):
        """
        渲染完整的聊天界面

        Args:
            session_key: 会话状态键名（用于区分不同页面的聊天实例）
            title: 聊天界面标题
            placeholder: 输入框占位文本
            show_history: 是否显示历史消息
            search_mode: 检索模式
            top_k: 检索结果数量
        """
        # 初始化会话状态
        history_key = f"chat_history_{session_key}"
        session_id_key = f"chat_session_id_{session_key}"

        if history_key not in st.session_state:
            st.session_state[history_key] = []
        if session_id_key not in st.session_state:
            st.session_state[session_id_key] = None

        # 标题和控制按钮
        col_title, col_actions = st.columns([3, 1])
        with col_title:
            st.markdown(f"### {title}")
        with col_actions:
            col_new, col_clear = st.columns(2)
            with col_new:
                if st.button("新建对话", key=f"new_chat_{session_key}"):
                    st.session_state[history_key] = []
                    st.session_state[session_id_key] = None
                    st.rerun()
            with col_clear:
                if st.button("清空", key=f"clear_chat_{session_key}"):
                    st.session_state[history_key] = []
                    st.rerun()

        st.markdown("---")

        # 显示历史消息
        if show_history:
            self._render_message_list(st.session_state[history_key])

        st.markdown("---")

        # 获取用户输入并发送
        self._render_input_area(
            history_key=history_key,
            session_id_key=session_id_key,
            placeholder=placeholder,
            search_mode=search_mode,
            top_k=top_k,
        )

    def _render_message_list(self, messages: List[Dict]):
        """
        渲染消息列表

        Args:
            messages: 消息列表
        """
        if not messages:
            st.info("请输入您的问题，AI将基于知识库为您解答。")
            return

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            sources = msg.get("sources", [])

            self.display_message(role=role, content=content)

            if role == "assistant" and sources:
                self.display_sources(sources)

    def display_message(self, role: str, content: str):
        """
        显示单条消息

        Args:
            role: 消息角色（user / assistant）
            content: 消息内容
        """
        if role == "user":
            safe_content = html.escape(content)
            st.markdown(f"""
            <div class="chat-message-user">
                <strong>👤 您：</strong><br>
                {safe_content}
            </div>
            """, unsafe_allow_html=True)
        elif role == "assistant":
            safe_content = html.escape(content)
            st.markdown(f"""
            <div class="chat-message-assistant">
                <strong>🤖 AI助手：</strong><br>
                {safe_content}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"**[{role}]**: {content}")

    def display_sources(self, sources: List[Dict]):
        """
        显示引用来源

        Args:
            sources: 来源列表
        """
        if not sources:
            return

        with st.expander("📚 查看引用来源", expanded=False):
            for i, src in enumerate(sources, 1):
                src_name = src.get("source", f"来源{i}")
                src_content = src.get("content", "")
                src_score = src.get("score", 0)

                st.markdown(f"**来源 {i}**: {src_name}")
                if src_score:
                    st.caption(f"相似度: {src_score:.2%}")

                # 截断过长内容
                display_content = src_content[:300]
                if len(src_content) > 300:
                    display_content += "..."
                st.caption(display_content)

                if i < len(sources):
                    st.markdown("---")

    def get_user_input(self, placeholder: str = "请输入您的问题...", key: str = "chat_input") -> Optional[str]:
        """
        获取用户输入

        Args:
            placeholder: 输入框占位文本
            key: 输入框唯一键

        Returns:
            Optional[str]: 用户输入的文本，未输入则返回None
        """
        col_input, col_send = st.columns([5, 1])

        with col_input:
            question = st.text_input(
                "输入问题",
                placeholder=placeholder,
                key=key,
            )

        with col_send:
            st.markdown("<br>", unsafe_allow_html=True)
            clicked = st.button("发送", type="primary", width="stretch", key=f"{key}_send")

        if clicked and question:
            return question

        return None

    def _render_input_area(
        self,
        history_key: str,
        session_id_key: str,
        placeholder: str,
        search_mode: str,
        top_k: int,
    ):
        """
        渲染输入区域并处理发送逻辑

        Args:
            history_key: 历史记录的session_state键名
            session_id_key: 会话ID的session_state键名
            placeholder: 输入框占位文本
            search_mode: 检索模式
            top_k: 检索结果数量
        """
        question = self.get_user_input(placeholder=placeholder, key=f"input_{history_key}")

        if question:
            # 添加用户消息到历史
            st.session_state[history_key].append({
                "role": "user",
                "content": question,
            })

            # 调用后端API
            with st.spinner("AI正在思考..."):
                try:
                    # 构建对话上下文
                    context = []
                    for msg in st.session_state[history_key][:-1]:
                        context.append({
                            "role": msg["role"],
                            "content": msg["content"],
                        })

                    resp = requests.post(
                        f"{self.api_base_url}/chat/send",
                        json={
                            "question": question,
                            "session_id": st.session_state[session_id_key],
                            "context": context if context else None,
                            "search_mode": search_mode,
                            "top_k": top_k,
                        },
                        headers=self._get_auth_headers(),
                        timeout=60,
                    )

                    if resp.status_code == 200:
                        data = resp.json()
                        answer = data["data"]["answer"]
                        sources = data["data"].get("sources", [])
                        session_id = data["data"]["session_id"]

                        # 保存会话ID
                        st.session_state[session_id_key] = session_id

                        # 添加AI回答到历史
                        st.session_state[history_key].append({
                            "role": "assistant",
                            "content": answer,
                            "sources": sources,
                        })

                        st.rerun()
                    else:
                        error_data = resp.json()
                        st.error(f"问答失败: {error_data.get('message', '未知错误')}")

                except requests.exceptions.ConnectionError:
                    st.error("无法连接到后端服务，请确认服务已启动")
                except requests.exceptions.Timeout:
                    st.error("请求超时，请稍后重试")
                except Exception as e:
                    st.error(f"问答出错: {str(e)}")

    def send_message(
        self,
        question: str,
        session_id: Optional[str] = None,
        chat_history: Optional[List[Dict]] = None,
        search_mode: str = "hybrid",
        top_k: int = 5,
    ) -> Dict:
        """
        发送消息并获取AI回答

        Args:
            question: 用户问题
            session_id: 会话ID
            chat_history: 对话历史
            search_mode: 检索模式
            top_k: 检索结果数量

        Returns:
            Dict: 包含answer, sources, session_id的字典
        """
        try:
            context = []
            if chat_history:
                for msg in chat_history:
                    context.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", ""),
                    })

            resp = requests.post(
                f"{self.api_base_url}/chat/send",
                json={
                    "question": question,
                    "session_id": session_id,
                    "context": context if context else None,
                    "search_mode": search_mode,
                    "top_k": top_k,
                },
                headers=self._get_auth_headers(),
                timeout=60,
            )

            if resp.status_code == 200:
                data = resp.json()
                return {
                    "success": True,
                    "answer": data["data"]["answer"],
                    "sources": data["data"].get("sources", []),
                    "session_id": data["data"]["session_id"],
                    "confidence": data["data"].get("confidence", 0),
                }
            else:
                error_data = resp.json()
                return {
                    "success": False,
                    "error": error_data.get("message", "未知错误"),
                }

        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "无法连接到后端服务"}
        except requests.exceptions.Timeout:
            return {"success": False, "error": "请求超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def load_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """
        从后端加载对话历史

        Args:
            session_id: 会话ID
            limit: 最大消息数量

        Returns:
            List[Dict]: 消息列表
        """
        try:
            resp = requests.get(
                f"{self.api_base_url}/chat/history/{session_id}",
                params={"limit": limit},
                headers=self._get_auth_headers(),
                timeout=30,
            )

            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", {}).get("messages", [])
            return []

        except Exception:
            return []

    def delete_session(self, session_id: str) -> bool:
        """
        删除对话会话

        Args:
            session_id: 会话ID

        Returns:
            bool: 是否删除成功
        """
        try:
            resp = requests.delete(
                f"{self.api_base_url}/chat/session/{session_id}",
                headers=self._get_auth_headers(),
                timeout=30,
            )
            return resp.status_code == 200
        except Exception:
            return False
