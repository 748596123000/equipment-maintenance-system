"""
知识库页面 - 用户端只读浏览已审批的PDF文档

普通用户可以浏览所有已审批通过且处理完成的PDF文档，
支持搜索、预览原文档。不能上传、删除或审批文档。
"""

import streamlit as st
import requests

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from ui.components.preview import render_pdf_preview
from ui.components.common import hide_login_nav

st.set_page_config(
    page_title="知识库 - 设备检修知识系统",
    page_icon="📚",
)

hide_login_nav()

# ========== 登录检查 ==========
if "user_info" not in st.session_state:
    st.switch_page("pages/00_登录.py")
    st.stop()


def get_api_base() -> str:
    """获取API基础地址"""
    return st.session_state.get("api_base_url", "http://localhost:8000/api/v1")


def get_user_headers() -> dict:
    """获取包含用户信息的请求头"""
    user_info = st.session_state.get("user_info", {})
    return {"Authorization": f"Bearer {user_info.get('token', '')}"}


def main():
    """页面主函数"""
    if "api_base_url" not in st.session_state:
        st.session_state.api_base_url = "http://localhost:8000/api/v1"

    st.title("📚 知识库")
    st.markdown("浏览设备检修知识库中已入库的文档，支持在线预览。")

    # 搜索栏
    col_search, col_refresh = st.columns([4, 1])
    with col_search:
        search_keyword = st.text_input(
            "搜索文档",
            placeholder="输入文件名搜索...",
            key="kb_search_input",
        )
    with col_refresh:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 刷新", width="stretch", key="kb_refresh"):
            st.rerun()

    st.markdown("---")

    # 获取文档列表
    try:
        resp = requests.get(
            f"{get_api_base()}/upload/list",
            params={"page": 1, "page_size": 100},
            timeout=30,
        )

        if resp.status_code == 200:
            data = resp.json()
            all_docs = data.get("data", {}).get("documents", [])

            # 只显示已完成的文档
            completed_docs = [
                d for d in all_docs
                if d.get("status") == "completed"
            ]

            # 搜索过滤
            if search_keyword:
                completed_docs = [
                    d for d in completed_docs
                    if search_keyword.lower() in d.get("filename", "").lower()
                ]

            # 统计信息
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📚 已入库文档", len(completed_docs))
            with col2:
                total_chunks = sum(d.get("chunk_count", 0) for d in completed_docs)
                st.metric("📄 总分块数", total_chunks)
            with col3:
                total_pages = sum(d.get("page_count", 0) for d in completed_docs)
                st.metric("📑 总页数", total_pages)

            st.markdown("---")

            if completed_docs:
                st.markdown(f"共 **{len(completed_docs)}** 个文档")

                for i, doc in enumerate(completed_docs):
                    filename = doc.get("filename", "未知文件")
                    uploader = doc.get("uploader_name", doc.get("uploader_id", "未知"))
                    upload_time = doc.get("created_at", "")
                    page_count = doc.get("page_count", 0)
                    chunk_count = doc.get("chunk_count", 0)

                    # 格式化时间
                    if upload_time and upload_time.endswith("."):
                        upload_time = upload_time[:-1]
                    if "T" in upload_time:
                        upload_time = upload_time.split("T")[0]

                    col_name, col_info, col_action = st.columns([3, 3, 1])

                    with col_name:
                        st.markdown(f"**📄 {filename}**")

                    with col_info:
                        detail_items = []
                        if uploader:
                            detail_items.append(f"上传者: {uploader}")
                        if upload_time:
                            detail_items.append(f"上传时间: {upload_time}")
                        if page_count:
                            detail_items.append(f"页数: {page_count}")
                        if chunk_count:
                            detail_items.append(f"分块数: {chunk_count}")
                        st.caption(" | ".join(detail_items))

                    with col_action:
                        if st.button("预览", type="primary", key=f"kb_preview_{doc['document_id']}", width="stretch"):
                            st.session_state["kb_preview_doc_id"] = doc["document_id"]
                            st.rerun()

                    if i < len(completed_docs) - 1:
                        st.markdown("---")

                # 预览区域
                if "kb_preview_doc_id" in st.session_state:
                    preview_id = st.session_state["kb_preview_doc_id"]
                    st.markdown("---")
                    st.markdown("#### 📖 文档预览")
                    if st.button("✖ 关闭预览", key="kb_close_preview"):
                        del st.session_state["kb_preview_doc_id"]
                        st.rerun()
                    render_pdf_preview(preview_id, get_api_base(), height=1200)
            else:
                if search_keyword:
                    st.info(f"没有找到包含 '{search_keyword}' 的文档")
                else:
                    st.info("知识库暂无已入库文档，请等待管理员审批文档后自动入库。")

        else:
            st.error("获取文档列表失败")

    except requests.exceptions.ConnectionError:
        st.error("无法连接到后端服务，请确认后端已启动")
    except Exception as e:
        st.error(f"获取文档列表出错: {str(e)}")


if __name__ == "__main__":
    main()
