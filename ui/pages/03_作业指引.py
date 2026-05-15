"""
作业指引页面

提供AI驱动的作业指引生成功能：
- 表单输入任务描述、设备信息、安全等级等
- 生成步骤化作业指引
- 展示步骤详情（标题、描述、安全警告、所需工具）
- 导出指引功能
"""

import html
import json
import streamlit as st
import requests

st.set_page_config(
    page_title="作业指引 - 设备检修知识系统",
    page_icon="📋",
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


def get_api_base() -> str:
    """获取API基础地址"""
    return st.session_state.get("api_base_url", "http://localhost:8000/api/v1")


def render_guide_form():
    """渲染作业指引生成表单"""
    st.markdown("### 📋 生成作业指引")
    st.markdown("填写任务信息，AI将为您生成步骤化的检修作业指引")

    with st.form("guide_form"):
        # 任务描述
        task_description = st.text_area(
            "作业任务描述 *",
            placeholder="请详细描述需要执行的检修作业任务，例如：对110kV变压器进行停电检修，检查绕组绝缘状态...",
            height=100,
            key="guide_task",
        )

        # 设备信息
        col_equip1, col_equip2 = st.columns(2)
        with col_equip1:
            equipment_type = st.selectbox(
                "设备类型",
                options=["", "变压器", "开关柜", "断路器", "隔离开关", "互感器",
                         "避雷器", "电容器", "电缆", "继电保护装置", "其他"],
                key="guide_equip_type",
            )
        with col_equip2:
            equipment_model = st.text_input(
                "设备型号",
                placeholder="例如：S11-630/10",
                key="guide_equip_model",
            )

        # 作业环境
        work_environment = st.text_input(
            "作业环境描述",
            placeholder="例如：室外变电站，温度35°C，湿度80%",
            key="guide_env",
        )

        # 安全等级和详细程度
        col_level1, col_level2 = st.columns(2)
        with col_level1:
            safety_level = st.selectbox(
                "安全等级",
                options=["low", "standard", "high", "critical"],
                format_func=lambda x: {
                    "low": "低风险",
                    "standard": "标准",
                    "high": "高风险",
                    "critical": "极高风险",
                }.get(x, x),
                key="guide_safety",
            )
        with col_level2:
            detail_level = st.selectbox(
                "详细程度",
                options=["brief", "medium", "detailed"],
                format_func=lambda x: {
                    "brief": "简要",
                    "medium": "标准",
                    "detailed": "详细",
                }.get(x, x),
                key="guide_detail",
            )

        # 生成按钮
        submitted = st.form_submit_button(
            "🚀 生成作业指引",
            type="primary",
            width="stretch",
        )

    return submitted, task_description, equipment_type, equipment_model, work_environment, safety_level, detail_level


def render_guide_result(guide_data: dict):
    """
    渲染作业指引结果

    Args:
        guide_data: 指引数据字典
    """
    st.markdown("---")
    st.markdown("### 📋 作业指引")

    # 标题
    title = guide_data.get("title", "作业指引")
    st.markdown(f"## {title}")

    # 任务概述
    if guide_data.get("task_summary"):
        st.markdown("#### 📝 任务概述")
        st.info(guide_data["task_summary"])

    # 准备工作
    if guide_data.get("preparation"):
        st.markdown("#### 🛠️ 准备工作")
        for i, item in enumerate(guide_data["preparation"], 1):
            st.markdown(f"{i}. {item}")

    # 安全注意事项
    if guide_data.get("safety_notes"):
        st.markdown("#### ⚠️ 安全注意事项")
        for note in guide_data["safety_notes"]:
            st.warning(note)

    # 作业步骤
    steps = guide_data.get("steps", [])
    if steps:
        st.markdown("---")
        st.markdown("#### 📝 作业步骤")

        for step in steps:
            step_num = step.get("step_number", "?")
            step_title = step.get("title", "")
            step_desc = step.get("description", "")
            warnings = step.get("warnings", [])
            tools = step.get("tools_required", [])
            est_time = step.get("estimated_time", "")
            tips = step.get("tips", [])

            safe_step_num = html.escape(str(step.get("step_number", "")))
            safe_step_title = html.escape(step.get("title", ""))
            safe_step_content = html.escape(step.get("content", ""))

            # 步骤卡片
            with st.container():
                st.markdown(f"""
                <div class="step-card">
                    <span class="step-number">{safe_step_num}</span>
                    <strong>{safe_step_title}</strong>
                </div>
                """, unsafe_allow_html=True)

                if step_desc:
                    st.markdown(step_desc)

                if est_time:
                    st.caption(f"⏱️ 预计耗时: {est_time}")

                if tools:
                    st.markdown("**🔧 所需工具:** " + ", ".join(tools))

                if warnings:
                    for w in warnings:
                        st.error(f"⚠️ {w}")

                if tips:
                    for tip in tips:
                        st.info(f"💡 {tip}")

                st.markdown("---")

    # 完成标准
    if guide_data.get("completion_criteria"):
        st.markdown("#### ✅ 完成标准")
        for i, criterion in enumerate(guide_data["completion_criteria"], 1):
            st.markdown(f"{i}. {criterion}")

    # 工具清单汇总
    all_tools = set()
    for step in steps:
        for tool in step.get("tools_required", []):
            all_tools.add(tool)

    if all_tools:
        st.markdown("#### 🔧 工具清单")
        tool_cols = st.columns(min(len(all_tools), 4))
        for i, tool in enumerate(sorted(all_tools)):
            with tool_cols[i % len(tool_cols)]:
                st.markdown(f"- {tool}")


def main():
    """页面主函数"""
    if "api_base_url" not in st.session_state:
        st.session_state.api_base_url = "http://localhost:8000/api/v1"

    st.title("📋 作业指引生成")

    # 历史指引
    tab_generate, tab_history = st.tabs(["生成指引", "历史指引"])

    with tab_generate:
        submitted, task_description, equipment_type, equipment_model, \
            work_environment, safety_level, detail_level = render_guide_form()

        if submitted:
            if not task_description:
                st.error("请填写作业任务描述")
                return

            with st.spinner("AI正在生成作业指引，请稍候..."):
                try:
                    resp = requests.post(
                        f"{get_api_base()}/guide/generate",
                        json={
                            "task_description": task_description,
                            "equipment_type": equipment_type or None,
                            "equipment_model": equipment_model or None,
                            "work_environment": work_environment or None,
                            "safety_level": safety_level,
                            "detail_level": detail_level,
                        },
                        timeout=120,
                    )

                    if resp.status_code == 200:
                        data = resp.json()
                        guide_data = data.get("data", {})
                        st.session_state["current_guide"] = guide_data
                        st.session_state["current_guide_id"] = guide_data.get("guide_id", "")

                        render_guide_result(guide_data)

                        # 导出按钮
                        guide_id = guide_data.get("guide_id", "")
                        if guide_id:
                            col_export1, col_export2 = st.columns(2)
                            with col_export1:
                                if st.button("📥 导出为文本", key="export_txt"):
                                    try:
                                        export_resp = requests.get(
                                            f"{get_api_base()}/guide/export/{guide_id}",
                                            timeout=30,
                                        )
                                        if export_resp.status_code == 200:
                                            st.download_button(
                                                label="下载指引文件",
                                                data=export_resp.text,
                                                file_name=f"作业指引_{guide_id[:8]}.txt",
                                                mime="text/plain",
                                                key="download_guide",
                                            )
                                        else:
                                            st.error("导出失败")
                                    except Exception as e:
                                        st.error(f"导出失败: {str(e)}")

                            with col_export2:
                                if st.button("📋 复制指引内容", key="copy_guide"):
                                    try:
                                        guide_text = json.dumps(guide_data, ensure_ascii=False, indent=2)
                                        st.session_state["clipboard_guide"] = guide_text
                                        st.success("指引内容已复制到剪贴板（会话内）")
                                    except Exception:
                                        st.error("复制失败")

                    else:
                        error_data = resp.json()
                        st.error(f"生成失败: {error_data.get('message', '未知错误')}")

                except requests.exceptions.ConnectionError:
                    st.error("无法连接到后端服务，请确认服务已启动")
                except requests.exceptions.Timeout:
                    st.error("生成超时，请稍后重试")
                except Exception as e:
                    st.error(f"生成出错: {str(e)}")

        # 如果已有生成的指引，显示
        elif "current_guide" in st.session_state:
            render_guide_result(st.session_state["current_guide"])

    with tab_history:
        st.markdown("### 📚 历史指引列表")

        try:
            resp = requests.get(
                f"{get_api_base()}/guide/list",
                params={"page": 1, "page_size": 20},
                timeout=30,
            )

            if resp.status_code == 200:
                data = resp.json()
                guides = data.get("data", {}).get("guides", [])

                if guides:
                    for guide in guides:
                        col_info, col_action = st.columns([4, 1])
                        with col_info:
                            st.markdown(f"**{guide.get('title', '未命名')}**")
                            st.caption(
                                f"设备: {guide.get('equipment_type', '-')} | "
                                f"型号: {guide.get('equipment_model', '-')} | "
                                f"安全等级: {guide.get('safety_level', '-')} | "
                                f"创建时间: {guide.get('created_at', '-')}"
                            )
                        with col_action:
                            if st.button("查看", key=f"view_guide_{guide['guide_id']}"):
                                try:
                                    detail_resp = requests.get(
                                        f"{get_api_base()}/guide/{guide['guide_id']}",
                                        timeout=30,
                                    )
                                    if detail_resp.status_code == 200:
                                        detail_data = detail_resp.json()
                                        st.session_state["current_guide"] = detail_data["data"]
                                        st.session_state["current_guide_id"] = guide["guide_id"]
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"获取详情失败: {str(e)}")
                        st.markdown("---")
                else:
                    st.info("暂无历史指引记录")
            else:
                st.error("获取指引列表失败")

        except requests.exceptions.ConnectionError:
            st.error("无法连接到后端服务")
        except Exception as e:
            st.error(f"获取指引列表出错: {str(e)}")


if __name__ == "__main__":
    main()
