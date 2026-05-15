"""
PDF原文档在线预览组件

使用PDF.js在浏览器中直接渲染PDF原文档，实现类似WPS的预览效果。
通过Streamlit的components.html嵌入包含PDF.js的HTML页面。

使用方式：
    from ui.components.preview import render_pdf_preview
    render_pdf_preview(document_id, api_base_url)
"""

import json
import re
import warnings
from urllib.parse import urlparse

import streamlit as st
import streamlit.components.v1 as components


# PDF.js CDN地址
PDFJS_VERSION = "3.11.174"
PDFJS_CDN_BASE = f"https://cdnjs.cloudflare.com/ajax/libs/pdf.js/{PDFJS_VERSION}"
PDFJS_LIB_URL = f"{PDFJS_CDN_BASE}/pdf.min.js"
PDFJS_WORKER_URL = f"{PDFJS_CDN_BASE}/pdf.worker.min.js"
# TODO: 生产环境应添加SRI完整性校验(integrity + crossorigin)，防止CDN篡改风险


def render_pdf_preview(document_id: str, api_base_url: str, height: int = 1200):
    """
    使用PDF.js在线预览PDF原文档

    在Streamlit页面中嵌入一个使用PDF.js渲染的PDF预览器，
    支持翻页、缩放等操作，效果类似WPS的PDF预览。

    Args:
        document_id: 文档ID
        api_base_url: 后端API基础地址，如 "http://localhost:8000/api/v1"
        height: 预览区域高度（像素），默认1200
    """
    if not re.match(r'^[a-zA-Z0-9\-_]+$', document_id):
        st.error("无效的文档ID")
        return

    parsed = urlparse(api_base_url)
    if parsed.scheme not in ("http", "https"):
        st.error("无效的API地址")
        return

    pdf_url = f"{api_base_url}/upload/pdf/{document_id}/view"

    pdfjs_html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>PDF预览</title>
        <script src="{PDFJS_LIB_URL}" crossorigin="anonymous"></script>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            html, body {{
                width: 100%;
                height: 100%;
                background: #e8e8e8;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                overflow: auto;
            }}
            .toolbar {{
                position: sticky;
                top: 0;
                z-index: 100;
                background: #2c2c2c;
                padding: 8px 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 12px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                flex-wrap: wrap;
            }}
            .toolbar button {{
                padding: 6px 16px;
                cursor: pointer;
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 13px;
                transition: background 0.2s;
            }}
            .toolbar button:hover {{ background: #45a049; }}
            .toolbar button:disabled {{
                background: #666;
                cursor: not-allowed;
            }}
            .toolbar .page-info {{
                color: #ccc;
                font-size: 14px;
                padding: 0 10px;
            }}
            .toolbar .zoom-info {{
                color: #999;
                font-size: 12px;
                padding: 0 6px;
            }}
            .toolbar .separator {{
                width: 1px;
                height: 24px;
                background: #555;
            }}
            #pdf-container {{
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 20px 10px;
                gap: 15px;
            }}
            .page-wrapper {{
                background: white;
                box-shadow: 0 2px 12px rgba(0,0,0,0.3);
                display: flex;
                justify-content: center;
            }}
            canvas {{
                display: block;
            }}
            .loading {{
                color: #555;
                text-align: center;
                padding: 100px 20px;
                font-size: 16px;
            }}
            .loading .spinner {{
                display: inline-block;
                width: 40px;
                height: 40px;
                border: 3px solid rgba(0,0,0,0.1);
                border-radius: 50%;
                border-top-color: #4CAF50;
                animation: spin 1s ease-in-out infinite;
                margin-bottom: 15px;
            }}
            @keyframes spin {{
                to {{ transform: rotate(360deg); }}
            }}
            .error-msg {{
                color: #d32f2f;
                text-align: center;
                padding: 80px 20px;
                font-size: 15px;
                max-width: 600px;
                margin: 0 auto;
                line-height: 1.6;
            }}
            .error-msg .error-title {{
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 10px;
            }}
            .error-msg .error-detail {{
                color: #666;
                font-size: 13px;
                word-break: break-all;
            }}
        </style>
    </head>
    <body>
        <div class="toolbar" id="toolbar" style="display:none;">
            <button id="btn-prev" onclick="prevPage()" disabled>上一页</button>
            <span class="page-info">
                第 <span id="pageNum">0</span> / <span id="pageCount">0</span> 页
            </span>
            <button id="btn-next" onclick="nextPage()" disabled>下一页</button>
            <div class="separator"></div>
            <button onclick="zoomOut()">缩小</button>
            <span class="zoom-info" id="zoomInfo">100%</span>
            <button onclick="zoomIn()">放大</button>
            <button onclick="zoomFit()">适应宽度</button>
            <button onclick="renderAllPages()">全部加载</button>
        </div>
        <div id="pdf-container">
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <div>正在加载PDF文档，请稍候...</div>
            </div>
        </div>
        <script>
            pdfjsLib.GlobalWorkerOptions.workerSrc = '{PDFJS_WORKER_URL}';

            let pdfDoc = null;
            let currentPage = 1;
            let scale = 1.5;
            let rendering = false;
            let allPagesMode = false;

            async function loadPDF() {{
                try {{
                    const loadingTask = pdfjsLib.getDocument(JSON.parse({json.dumps(pdf_url)}));
                    pdfDoc = await loadingTask.promise;
                    document.getElementById('pageCount').textContent = pdfDoc.numPages;
                    document.getElementById('loading').style.display = 'none';
                    document.getElementById('toolbar').style.display = 'flex';
                    updateButtons();
                    renderPage(currentPage);
                }} catch(err) {{
                    document.getElementById('loading').style.display = 'none';
                    var container = document.getElementById('pdf-container');
                    var errorMsg = err.message || '未知错误';
                    var hint = '';
                    if (errorMsg.indexOf('500') !== -1) {{
                        hint = '<br><br>可能原因：PDF文件路径不正确或服务器读取文件失败。<br>请检查后端服务日志获取详细错误信息。';
                    }} else if (errorMsg.indexOf('404') !== -1) {{
                        hint = '<br><br>PDF文件不存在，可能已被删除。';
                    }}
                    container.innerHTML = '<div class="error-msg">' +
                        '<div class="error-title">PDF加载失败</div>' +
                        '<div id="pdf-error-msg"></div>' +
                        '<div class="error-detail" id="pdf-error-hint"></div>' +
                        '</div>';
                    document.getElementById('pdf-error-msg').textContent = errorMsg;
                    document.getElementById('pdf-error-hint').textContent = hint;
                }}
            }}

            async function renderPage(num) {{
                if (rendering) return;
                rendering = true;

                try {{
                    const page = await pdfDoc.getPage(num);
                    const viewport = page.getViewport({{ scale: scale }});

                    const container = document.getElementById('pdf-container');
                    container.innerHTML = '';

                    const wrapper = document.createElement('div');
                    wrapper.className = 'page-wrapper';

                    const canvas = document.createElement('canvas');
                    const ctx = canvas.getContext('2d');
                    canvas.height = viewport.height;
                    canvas.width = viewport.width;
                    wrapper.appendChild(canvas);
                    container.appendChild(wrapper);

                    await page.render({{
                        canvasContext: ctx,
                        viewport: viewport
                    }}).promise;

                    document.getElementById('pageNum').textContent = num;
                    updateButtons();
                    updateZoomInfo();
                }} catch(err) {{
                    console.error('渲染页面失败:', err);
                }} finally {{
                    rendering = false;
                }}
            }}

            async function renderAllPages() {{
                if (!pdfDoc) return;
                if (allPagesMode) {{
                    renderPage(currentPage);
                    allPagesMode = false;
                    return;
                }}
                allPagesMode = true;
                const container = document.getElementById('pdf-container');
                container.innerHTML = '<div class="loading"><div class="spinner"></div><div>正在加载全部页面...</div></div>';

                await new Promise(r => setTimeout(r, 50));

                container.innerHTML = '';
                for (let i = 1; i <= pdfDoc.numPages; i++) {{
                    try {{
                        const page = await pdfDoc.getPage(i);
                        const viewport = page.getViewport({{ scale: scale }});

                        const wrapper = document.createElement('div');
                        wrapper.className = 'page-wrapper';

                        const canvas = document.createElement('canvas');
                        const ctx = canvas.getContext('2d');
                        canvas.height = viewport.height;
                        canvas.width = viewport.width;
                        wrapper.appendChild(canvas);
                        container.appendChild(wrapper);

                        await page.render({{
                            canvasContext: ctx,
                            viewport: viewport
                        }}).promise;
                    }} catch(err) {{
                        console.error('渲染第' + i + '页失败:', err);
                    }}
                }}
            }}

            function prevPage() {{
                if (currentPage <= 1) return;
                currentPage--;
                allPagesMode = false;
                renderPage(currentPage);
            }}

            function nextPage() {{
                if (currentPage >= pdfDoc.numPages) return;
                currentPage++;
                allPagesMode = false;
                renderPage(currentPage);
            }}

            function zoomIn() {{
                scale = Math.min(scale + 0.25, 5.0);
                if (allPagesMode) renderAllPages();
                else renderPage(currentPage);
            }}

            function zoomOut() {{
                scale = Math.max(scale - 0.25, 0.25);
                if (allPagesMode) renderAllPages();
                else renderPage(currentPage);
            }}

            function zoomFit() {{
                // 根据容器宽度自适应
                const containerWidth = document.getElementById('pdf-container').clientWidth - 40;
                if (pdfDoc) {{
                    pdfDoc.getPage(currentPage).then(function(page) {{
                        const viewport = page.getViewport({{ scale: 1 }});
                        scale = containerWidth / viewport.width;
                        scale = Math.max(0.25, Math.min(scale, 5.0));
                        if (allPagesMode) renderAllPages();
                        else renderPage(currentPage);
                    }});
                }}
            }}

            function updateButtons() {{
                document.getElementById('btn-prev').disabled = (currentPage <= 1);
                document.getElementById('btn-next').disabled = (currentPage >= pdfDoc.numPages);
            }}

            function updateZoomInfo() {{
                document.getElementById('zoomInfo').textContent = Math.round(scale / 1.5 * 100) + '%';
            }}

            // 键盘快捷键
            document.addEventListener('keydown', function(e) {{
                if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') prevPage();
                else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') nextPage();
                else if (e.key === '+' || e.key === '=') zoomIn();
                else if (e.key === '-') zoomOut();
            }});

            loadPDF();
        </script>
    </body>
    </html>
    '''

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        components.html(pdfjs_html, height=height, scrolling=True)
