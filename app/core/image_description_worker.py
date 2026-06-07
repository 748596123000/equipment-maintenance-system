import logging
import os
import sys
import time


def run_image_descriptions(document_id: str):
    if not os.environ.get("HF_ENDPOINT"):
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
    os.environ["HF_HUB_OFFLINE"] = "1"

    _local_packages = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        ".pip_packages",
    )
    if os.path.isdir(_local_packages) and _local_packages not in sys.path:
        sys.path.insert(0, _local_packages)

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    logger = logging.getLogger(__name__)
    logger.info(f"[独立进程] 开始生成图片描述: document_id={document_id}")

    try:
        from app.models.database import get_database
        from app.services.vision_service import get_vision_service

        db = get_database()
        conn = db.get_connection()

        rows = conn.execute(
            "SELECT id, image_path, image_format, page_number, image_index FROM document_images WHERE document_id = ? AND ai_analyzed = 0",
            (document_id,),
        ).fetchall()

        if not rows:
            logger.info(f"[独立进程] 无待处理图片: document_id={document_id}")
            return

        total = len(rows)
        logger.info(f"[独立进程] 待处理图片={total}, document_id={document_id}")

        vision = get_vision_service()

        for idx, row in enumerate(rows):
            img_id, image_path, image_format, page_number, image_index = row
            try:
                if not image_path or not os.path.exists(image_path):
                    continue

                with open(image_path, "rb") as f:
                    image_bytes = f.read()

                if not image_bytes or len(image_bytes) < 100:
                    continue

                description = vision.describe_image(image_bytes, image_format or "png")

                if description:
                    conn.execute(
                        "UPDATE document_images SET ai_description = ?, ai_analyzed = 1 WHERE id = ?",
                        (description, img_id),
                    )
                    conn.commit()
                    logger.info(f"[独立进程] 图片描述完成: {idx + 1}/{total}, 页{page_number}图{image_index + 1}")
                else:
                    logger.debug(f"[独立进程] 图片描述为空: 页{page_number}图{image_index + 1}")

                time.sleep(0.05)

            except Exception as e:
                logger.warning(f"[独立进程] 图片描述失败: 页{page_number}图{image_index + 1}, 错误: {e}")

        logger.info(f"[独立进程] 图片描述生成完成: document_id={document_id}, 共处理={total}")

    except Exception as e:
        logger.error(f"[独立进程] 图片描述生成失败: {e}", exc_info=True)
