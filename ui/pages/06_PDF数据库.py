"""
文档数据库管理页面（仅管理员可见）

提供文档数据库管理功能：
- 显示所有已审批通过且处理完成的文档列表
- 支持搜索过滤
- 支持删除文档（同时删除ChromaDB中的向量数据）
- 显示知识库统计信息
"""

import streamlit as st
import requests

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ui.components.common import hide_login_nav, get_api_base, get_user_headers, require_admin, init_api_base, safe_error_msg

st.set_page_config(
    page_title="文档数据库 - 设备检修知识系统",
    page_icon="📚",
)

hide_login_nav()
require_admin()


def render_kb_stats():
    """渲染知识库统计信息"""
    st.markdown("### 📊 知识库统计")

    try:
        resp = requests.get(f"{get_api_base()}/admin/stats", headers=get_user_headers(), timeout=5)
        if resp.status_code == 200:
            stats = resp.json().get("data", {})

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("已入库文档", stats.get("document_count", 0))
            with col2:
                st.metric("总分块数", stats.get("total_chunks", 0))
            with col3:
                st.metric("向量库状态", "正常")
        else:
            st.error("获取统计信息失败")

    except requests.exceptions.ConnectionError:
        st.error("无法连接到后端服务")
    except Exception as e:
        st.error("操作失败，请稍后重试")


def render_document_list():
    """渲染PDF文档列表"""
    st.markdown("### 📚 文档列表")

    # 搜索过滤
    col_search, col_refresh = st.columns([4, 1])
    with col_search:
        search_keyword = st.text_input(
            "搜索文档",
            placeholder="输入文件名搜索...",
            key="pdf_search",
        )
    with col_refresh:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("刷新", width="stretch", key="pdf_refresh"):
            st.rerun()

    # 获取文档列表
    try:
        resp = requests.get(
            f"{get_api_base()}/upload/list",
            headers=get_user_headers(),
            params={"page": 1, "page_size": 100},
            timeout=30,
        )

        if resp.status_code == 200:
            data = resp.json()
            all_documents = data.get("data", {}).get("documents", [])

            # 过滤：只显示已审批通过且处理完成的文档
            completed_docs = [
                doc for doc in all_documents
                if doc.get("status") in ("completed", "parsed")
            ]

            # 搜索过滤
            if search_keyword:
                completed_docs = [
                    doc for doc in completed_docs
                    if search_keyword.lower() in doc.get("filename", "").lower()
                ]

            if not completed_docs:
                st.info("暂无已入库的文档")
                return

            st.success(f"共 {len(completed_docs)} 个已入库文档")

            # 显示文档表格
            doc_table = []
            for doc in completed_docs:
                uploader_name = doc.get("uploader_name", "")
                if not uploader_name:
                    uploader_id = doc.get("uploader_id", "")
                    uploader_name = uploader_id[:8] if uploader_id else "未知"

                doc_table.append({
                    "document_id": doc.get("document_id", ""),
                    "文件名": doc.get("filename", ""),
                    "上传者": uploader_name,
                    "上传时间": doc.get("created_at", ""),
                    "审批时间": doc.get("reviewed_at", ""),
                    "页数": doc.get("page_count", 0),
                    "分块数": doc.get("chunk_count", 0),
                    "状态": doc.get("status", ""),
                })

            # 显示表格
            for i, row in enumerate(doc_table):
                with st.container():
                    col_info, col_action = st.columns([5, 1])

                    with col_info:
                        st.markdown(f"**{row['文件名']}**")
                        detail_items = []
                        if row["上传者"]:
                            detail_items.append(f"上传者: {row['上传者']}")
                        if row["上传时间"]:
                            detail_items.append(f"上传时间: {row['上传时间']}")
                        if row["审批时间"]:
                            detail_items.append(f"审批时间: {row['审批时间']}")
                        if row["页数"]:
                            detail_items.append(f"页数: {row['页数']}")
                        if row["分块数"]:
                            detail_items.append(f"分块数: {row['分块数']}")
                        st.caption(" | ".join(detail_items))

                    with col_action:
                        if st.button("删除", type="secondary", key=f"del_pdf_{row['document_id']}", width="stretch"):
                            confirm_delete = st.checkbox("确认删除", key=f"confirm_delete_pdf_{row['document_id']}")
                            if confirm_delete:
                                _delete_document(row["document_id"], row["文件名"])
                            else:
                                st.warning("请勾选确认删除")

                    if i < len(doc_table) - 1:
                        st.markdown("---")

        else:
            st.error("获取文档列表失败")

    except requests.exceptions.ConnectionError:
        st.error("无法连接到后端服务")
    except Exception as e:
        st.error("操作失败，请稍后重试")


def _delete_document(document_id: str, filename: str):
    """删除文档及其向量数据"""
    headers = get_user_headers()

    with st.spinner(f"正在删除文档 '{filename}'..."):
        try:
            resp = requests.delete(
                f"{get_api_base()}/upload/{document_id}",
                headers=headers,
                timeout=30,
            )

            if resp.status_code == 200:
                st.success(f"文档 '{filename}' 已删除（包括向量数据）")
                st.rerun()
            else:
                error_data = resp.json()
                st.error(f"删除失败: {error_data.get('detail', '未知错误')}")

        except requests.exceptions.ConnectionError:
            st.error("无法连接到后端服务")
        except Exception as e:
            st.error("操作失败，请稍后重试")


def main():
    init_api_base()

    st.title("📚 文档数据库")

    render_kb_stats()
    st.markdown("---")
    render_document_list()


if __name__ == "__main__":
    main()
