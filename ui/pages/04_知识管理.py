"""
知识管理 / 我的上传 / 文档审批页面

根据用户角色显示不同内容：
- 普通用户：我的上传页面（上传PDF、查看自己的文档列表、删除自己的文档）
- 管理员：文档审批页面（待审批文档列表、已审批文档列表、全部文档管理）
"""

import streamlit as st
import requests

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from ui.components.preview import render_pdf_preview
from ui.components.common import hide_login_nav, get_api_base, get_user_headers, require_login, init_api_base, safe_error_msg

st.set_page_config(
    page_title="知识管理 - 设备检修知识系统",
    page_icon="📚",
)

hide_login_nav()
require_login()


STATUS_MAP = {
    "pending": "待审核",
    "approved": "已通过",
    "rejected": "已拒绝",
    "processing": "处理中",
    "completed": "已完成",
    "parsed": "已解析",
    "failed": "失败",
}


# ========== 普通用户：我的上传 ==========

def render_my_uploads():
    """渲染普通用户的'我的上传'页面"""
    st.markdown("### 📤 我的上传")
    st.markdown("上传PDF文档，管理员审批通过后将自动解析入库")

    # 文件上传区域
    st.markdown("#### 上传文档")
    uploaded_files = st.file_uploader(
        "选择PDF文件（支持多选）",
        type=["pdf"],
        accept_multiple_files=True,
        key="doc_uploader",
    )

    col_cat, col_upload = st.columns([2, 1])
    with col_cat:
        category = st.selectbox(
            "文档分类",
            options=["通用", "变压器", "开关柜", "断路器", "隔离开关",
                     "互感器", "避雷器", "电容器", "电缆", "继电保护装置", "其他"],
            key="doc_category",
        )
    with col_upload:
        st.markdown("<br>", unsafe_allow_html=True)
        upload_clicked = st.button("上传文件", type="primary", width="stretch", key="upload_btn")

    if upload_clicked and uploaded_files:
        for uploaded_file in uploaded_files:
            with st.spinner(f"正在上传 {uploaded_file.name}..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                    data = {"category": category}

                    resp = requests.post(
                        f"{get_api_base()}/upload/pdf",
                        files=files,
                        data=data,
                        headers=get_user_headers(),
                        timeout=60,
                    )

                    if resp.status_code == 200:
                        result = resp.json()
                        st.success(f"{uploaded_file.name} 上传成功，等待管理员审批")
                    else:
                        error_data = resp.json()
                        st.error(f"{uploaded_file.name} 上传失败: {error_data.get('detail', error_data.get('message', '未知错误'))}")

                except requests.exceptions.ConnectionError:
                    st.error("无法连接到后端服务")
                except Exception as e:
                    st.error("操作失败，请稍后重试")

    elif upload_clicked and not uploaded_files:
        st.warning("请先选择要上传的文件")

    st.markdown("---")

    # 我的文档列表
    st.markdown("#### 我的文档列表")

    try:
        resp = requests.get(
            f"{get_api_base()}/upload/my",
            headers=get_user_headers(),
            params={"page": 1, "page_size": 50},
            timeout=30,
        )

        if resp.status_code == 200:
            data = resp.json()
            documents = data.get("data", {}).get("documents", [])

            if documents:
                # 表格展示
                doc_table_data = []
                for doc in documents:
                    status = doc.get("status", "unknown")
                    status_text = STATUS_MAP.get(status, status)
                    review_comment = doc.get("review_comment", "")

                    doc_table_data.append({
                        "文件名": doc.get("filename", ""),
                        "大小": doc.get("file_size_display", ""),
                        "页数": doc.get("page_count", 0),
                        "分块数": doc.get("chunk_count", 0),
                        "状态": status_text,
                        "审批意见": review_comment if review_comment else "-",
                        "上传时间": doc.get("upload_time", ""),
                    })

                st.dataframe(doc_table_data, width="stretch", hide_index=True)
            else:
                st.info("暂无已上传的文档，请上传PDF文件")

    except requests.exceptions.ConnectionError:
        st.error("无法连接到后端服务")
    except Exception as e:
        st.error("操作失败，请稍后重试")


# ========== 管理员：文档审批 ==========

def render_document_approval():
    """渲染管理员的'文档审批'页面"""
    st.markdown("### 📝 文档审批")
    st.markdown("审批用户上传的PDF文档，审批通过后系统将自动解析入库")

    # 三个标签页
    tab_pending, tab_approved, tab_all = st.tabs([
        "⏳ 待审批",
        "✅ 已审批",
        "📄 全部文档",
    ])

    with tab_pending:
        render_pending_documents()

    with tab_approved:
        render_approved_documents()

    with tab_all:
        render_all_documents()


def render_pending_documents():
    """渲染待审批文档列表"""
    st.markdown("#### 待审批文档")

    try:
        resp = requests.get(
            f"{get_api_base()}/upload/pending",
            headers=get_user_headers(),
            params={"page": 1, "page_size": 50},
            timeout=30,
        )

        if resp.status_code == 200:
            data = resp.json()
            documents = data.get("data", {}).get("documents", [])

            if documents:
                st.info(f"共有 {len(documents)} 个文档等待审批")

                for doc in documents:
                    with st.expander(
                        f"**{doc.get('filename', '未命名')}** | "
                        f"上传者: {doc.get('uploader_name', '未知')} | "
                        f"大小: {doc.get('file_size_display', '-')} | "
                        f"时间: {doc.get('upload_time', '-')}"
                    ):
                        # 预览原文档按钮
                        if st.button("预览原文档", key=f"preview_pending_{doc['document_id']}"):
                            st.session_state[f"preview_pending_show_{doc['document_id']}"] = True

                        # 展示PDF预览
                        if st.session_state.get(f"preview_pending_show_{doc['document_id']}", False):
                            st.markdown("---")
                            if st.button("✖ 关闭预览", key=f"close_preview_pending_{doc['document_id']}"):
                                del st.session_state[f"preview_pending_show_{doc['document_id']}"]
                                st.rerun()
                            render_pdf_preview(doc["document_id"], get_api_base(), height=1400)

                        # 审批意见
                        review_comment = st.text_input(
                            "审批意见",
                            placeholder="请输入审批意见（可选）",
                            key=f"review_comment_{doc['document_id']}",
                        )

                        # 审批按钮
                        col_approve, col_reject = st.columns(2)
                        with col_approve:
                            if st.button("通过", type="primary", key=f"approve_{doc['document_id']}"):
                                _do_approve(doc["document_id"], review_comment)
                        with col_reject:
                            if st.button("拒绝", type="secondary", key=f"reject_{doc['document_id']}"):
                                _do_reject(doc["document_id"], review_comment)
            else:
                st.success("暂无待审批文档")

        elif resp.status_code == 403:
            st.error("无权限访问")
        else:
            st.error("获取待审批文档失败")

    except requests.exceptions.ConnectionError:
        st.error("无法连接到后端服务")
    except Exception as e:
        st.error("操作失败，请稍后重试")


def render_approved_documents():
    """渲染已审批文档列表"""
    st.markdown("#### 已审批文档")

    try:
        resp = requests.get(
            f"{get_api_base()}/upload/list",
            headers=get_user_headers(),
            params={"page": 1, "page_size": 50},
            timeout=30,
        )

        if resp.status_code == 200:
            data = resp.json()
            all_docs = data.get("data", {}).get("documents", [])

            # 筛选已审批的文档
            approved_docs = [d for d in all_docs if d.get("status") in ("approved", "rejected", "processing", "completed", "parsed", "failed")]

            if approved_docs:
                doc_table_data = []
                for doc in approved_docs:
                    status = doc.get("status", "unknown")
                    status_text = STATUS_MAP.get(status, status)

                    doc_table_data.append({
                        "文件名": doc.get("filename", ""),
                        "大小": doc.get("file_size_display", ""),
                        "状态": status_text,
                        "审批意见": doc.get("review_comment", "-"),
                        "审批时间": doc.get("reviewed_at", "-"),
                        "上传时间": doc.get("created_at", "-"),
                    })

                st.dataframe(doc_table_data, width="stretch", hide_index=True)
            else:
                st.info("暂无已审批文档")

    except requests.exceptions.ConnectionError:
        st.error("无法连接到后端服务")
    except Exception as e:
        st.error("操作失败，请稍后重试")


def render_all_documents():
    """渲染全部文档列表"""
    st.markdown("#### 全部文档管理")

    try:
        resp = requests.get(
            f"{get_api_base()}/upload/list",
            headers=get_user_headers(),
            params={"page": 1, "page_size": 50},
            timeout=30,
        )

        if resp.status_code == 200:
            data = resp.json()
            documents = data.get("data", {}).get("documents", [])

            if documents:
                doc_table_data = []
                for doc in documents:
                    status = doc.get("status", "unknown")
                    status_text = STATUS_MAP.get(status, status)

                    doc_table_data.append({
                        "文件名": doc.get("filename", ""),
                        "大小": doc.get("file_size_display", ""),
                        "页数": doc.get("page_count", 0),
                        "分块数": doc.get("chunk_count", 0),
                        "状态": status_text,
                        "上传时间": doc.get("created_at", ""),
                    })

                st.dataframe(doc_table_data, width="stretch", hide_index=True)

                # 文档操作区域
                st.markdown("#### 文档操作")

                # 预览功能
                preview_doc_id = st.selectbox(
                    "选择要预览的文档",
                    options=[(doc["document_id"], doc["filename"]) for doc in documents],
                    format_func=lambda x: x[1],
                    key="admin_preview_doc_select",
                )

                if st.button("预览原文档", type="primary", key="admin_preview_doc_btn"):
                    if preview_doc_id:
                        st.session_state["admin_preview_doc_id"] = preview_doc_id[0]

                # 展示PDF原文档预览
                if st.session_state.get("admin_preview_doc_id"):
                    st.markdown("---")
                    if st.button("✖ 关闭预览", key="admin_close_preview"):
                        del st.session_state["admin_preview_doc_id"]
                        st.rerun()
                    render_pdf_preview(st.session_state["admin_preview_doc_id"], get_api_base(), height=1400)

                # 删除操作
                st.markdown("---")
                delete_doc_id = st.selectbox(
                    "选择要删除的文档",
                    options=[(doc["document_id"], doc["filename"]) for doc in documents],
                    format_func=lambda x: x[1],
                    key="admin_delete_doc_select",
                )

                if st.button("删除文档", type="secondary", key="admin_delete_doc_btn"):
                    if delete_doc_id:
                        confirm_delete = st.checkbox("确认删除", key="confirm_delete_doc")
                        if confirm_delete:
                            with st.spinner("正在删除..."):
                                try:
                                    del_resp = requests.delete(
                                        f"{get_api_base()}/upload/{delete_doc_id[0]}",
                                        headers=get_user_headers(),
                                        timeout=30,
                                    )
                                    if del_resp.status_code == 200:
                                        st.success("文档删除成功")
                                        st.rerun()
                                    else:
                                        error_data = del_resp.json()
                                        st.error(f"删除失败: {error_data.get('detail', '未知错误')}")
                                except Exception as e:
                                    st.error("操作失败，请稍后重试")
                        else:
                            st.warning("请勾选确认删除")
            else:
                st.info("暂无文档记录")

    except requests.exceptions.ConnectionError:
        st.error("无法连接到后端服务")
    except Exception as e:
        st.error("操作失败，请稍后重试")


def _do_approve(document_id: str, comment: str):
    """执行审批通过操作"""
    with st.spinner("正在审批..."):
        try:
            resp = requests.post(
                f"{get_api_base()}/upload/{document_id}/approve",
                json={"comment": comment},
                headers=get_user_headers(),
                timeout=30,
            )

            if resp.status_code == 200:
                st.success("审批通过，文档已开始后台处理")
                st.rerun()
            else:
                error_data = resp.json()
                st.error(f"审批失败: {error_data.get('detail', '未知错误')}")

        except Exception as e:
            st.error("操作失败，请稍后重试")


def _do_reject(document_id: str, comment: str):
    """执行审批拒绝操作"""
    with st.spinner("正在审批..."):
        try:
            resp = requests.post(
                f"{get_api_base()}/upload/{document_id}/reject",
                json={"comment": comment},
                headers=get_user_headers(),
                timeout=30,
            )

            if resp.status_code == 200:
                st.success("文档已拒绝")
                st.rerun()
            else:
                error_data = resp.json()
                st.error(f"审批失败: {error_data.get('detail', '未知错误')}")

        except Exception as e:
            st.error("操作失败，请稍后重试")


# ========== 页面主函数 ==========

def main():
    init_api_base()

    user_info = st.session_state.get("user_info", {})
    user_role = user_info.get("role", "")

    if user_role == "admin":
        st.title("📝 文档审批与管理")
        render_document_approval()
    else:
        st.title("📤 我的上传")
        render_my_uploads()


if __name__ == "__main__":
    main()
