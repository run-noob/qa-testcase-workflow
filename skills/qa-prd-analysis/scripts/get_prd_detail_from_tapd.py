#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TAPD 需求详情获取工具。

根据输入的 TAPD 需求链接，解析 workspace_id 和 story_id，
调用 TAPD API 获取需求详情信息。
"""

import hashlib
import os
import re
import time
import argparse
import json
import logging
import sys
from html import unescape
from urllib.parse import urlparse, urljoin

try:
    import httpx
except:
    print("请先安装 httpx 库：python -m pip install httpx")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

TAPD_API_BASE = "https://hytapd.huya.info/proxy"
TAPD_SIGN = os.environ.get("TAPD_SIGN", "")
TAPD_IMAGE_BASE = "https://file.tapd.cn/"

# 需要查询的字段
DEFAULT_FIELDS = "id,name,status,owner,description,priority,iteration_id,created,modified,test_focus"


def get_headers() -> dict:
    """生成 TAPD API 认证请求头。"""
    if not TAPD_SIGN:
        raise ValueError(
            "TAPD_SIGN 环境变量未设置，无法生成认证签名。\n"
            "请在环境变量中配置 TAPD_SIGN，例如: export TAPD_SIGN=your_sign_key"
        )

    timestamp = int(time.time() * 1000)
    sign = TAPD_SIGN + str(timestamp)
    hash_sha256 = hashlib.sha256(sign.encode("utf-8")).hexdigest()

    return {
        "X-HYTAPD-APP": "auto_bug",
        "X-HYTAPD-TS": str(timestamp),
        "X-HYTAPD-CHK": hash_sha256,
    }


def parse_tapd_url(url: str) -> dict:
    """
    解析 TAPD URL，提取 workspace_id 和 story_id。

    支持的 URL 格式：
    1. 列表页 URL:
       https://www.tapd.cn/tapd_fe/58049171/story/list?...&dialog_preview_id=story_1158049171001607427
    2. 详情页 URL:
       https://www.tapd.cn/tapd_fe/58049171/story/detail/1158049171001607427

    Returns:
        dict: {"workspace_id": "58049171", "story_id": "1158049171001607427"}
    """
    workspace_id = None
    story_id = None

    # 提取 workspace_id: tapd_fe/ 后面的数字
    ws_match = re.search(r"tapd_fe/(\d+)", url)
    if ws_match:
        workspace_id = ws_match.group(1)

    # 方式 1: 从 dialog_preview_id 参数中提取 story_id
    # 格式: story_1158049171001607427
    dialog_match = re.search(r"dialog_preview_id=story_(\d+)", url)
    if dialog_match:
        story_id = dialog_match.group(1)

    # 方式 2: 从 /detail/ 路径中提取 story_id
    if not story_id:
        detail_match = re.search(r"/detail/(\d+)", url)
        if detail_match:
            story_id = detail_match.group(1)

    if not workspace_id:
        raise ValueError(f"无法从 URL 中解析 workspace_id: {url}")
    if not story_id:
        raise ValueError(f"无法从 URL 中解析 story_id: {url}")

    return {"workspace_id": workspace_id, "story_id": story_id}


def fetch_story_detail(
    workspace_id: str,
    story_id: str,
    fields: str = DEFAULT_FIELDS,
    timeout: float = 30.0,
) -> dict:
    """
    调用 TAPD API 获取需求详情。

    认证方式优先级：
    1. TAPD_ACCESS_TOKEN 环境变量存在时，使用 Basic Auth（个人访问令牌）
    2. 否则使用 TAPD_SIGN 环境变量 + SHA256 签名认证

    Args:
        workspace_id: 项目空间 ID
        story_id: 需求 ID
        fields: 需要返回的字段，逗号分隔
        timeout: 请求超时时间（秒）

    Returns:
        dict: API 响应的 JSON 数据

    Raises:
        httpx.HTTPError: 网络请求错误
        ValueError: 响应解析错误
    """
    url = f"{TAPD_API_BASE}/stories"
    params = {
        "workspace_id": workspace_id,
        "id": story_id,
        "fields": fields,
    }

    headers = get_headers()
    logger.info(f"使用 TAPD_SIGN 签名认证")

    logger.info(f"请求 TAPD API, workspace_id={workspace_id}, story_id={story_id}")

    try:
        response = httpx.get(url, params=params, headers=headers, timeout=timeout)
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"TAPD API 返回错误状态码: {e.response.status_code}")
        logger.error(f"响应内容: {e.response.text}")
        raise
    except httpx.RequestError as e:
        logger.error(f"请求 TAPD API 失败: {e}")
        raise

    # 检查 API 返回状态
    if data.get("status") != 1:
        error_info = data.get("info", "未知错误")
        logger.error(f"TAPD API 返回错误: {error_info}")
        raise ValueError(f"TAPD API 错误: {error_info}")

    return data


def extract_story_from_response(data: dict) -> dict:
    """
    从 API 响应中提取需求详情。

    Args:
        data: API 响应的完整 JSON 数据

    Returns:
        dict: 需求详情，如果未找到则返回空 dict
    """
    stories = data.get("data", [])
    if not stories:
        logger.warning("API 响应中未找到需求数据")
        return {}

    story = stories[0].get("Story", {})
    return story


def sanitize_filename(name: str) -> str:
    """将需求名称转为安全的文件名，替换非法字符。"""
    # 替换 Windows/macOS/Linux 文件系统不允许的字符
    illegal_chars = r'[\\/:*?"<>|\s]'
    safe_name = re.sub(illegal_chars, "_", name)
    # 去除首尾空格和点号
    safe_name = safe_name.strip(" .")
    # 限制文件名长度（保留扩展名空间）
    if len(safe_name) > 100:
        safe_name = safe_name[:100]
    return safe_name


def extract_images_from_html(html_content: str) -> list:
    """
    从 HTML 内容中提取所有图片的 src 地址。

    Args:
        html_content: HTML 格式的描述内容

    Returns:
        list[dict]: 每项包含 original_src, full_url, filename
    """
    img_tags = re.findall(r'<img[^>]+src="([^"]+)"', html_content)
    seen = set()
    images = []
    for src in img_tags:
        src = unescape(src)
        if src in seen:
            continue
        seen.add(src)
        # 提取文件名
        filename = os.path.basename(urlparse(src).path)
        if not filename:
            # 如果无法解析文件名，使用 hash 生成
            filename = hashlib.md5(src.encode()).hexdigest()[:8] + ".png"
        # 补全图片 URL：仅路径时添加 TAPD 图片域名
        if not src.startswith(("http://", "https://")):
            full_url = urljoin(TAPD_IMAGE_BASE, src)
        else:
            full_url = src
        images.append({
            "original_src": src,
            "full_url": full_url,
            "filename": filename,
        })
    return images


def get_image_download_url(
    workspace_id: str,
    image_path: str,
    timeout: float = 15.0,
) -> str | None:
    """
    通过 TAPD 代理 API 获取单张图片的临时下载链接（有效期 300s）。

    Args:
        workspace_id: 项目空间 ID
        image_path: 图片路径，如 /tfl/captures/2026-07/xxx.png
        timeout: 请求超时时间（秒）

    Returns:
        str | None: 临时下载链接，失败返回 None
    """
    url = f"{TAPD_API_BASE}/files/get_image"
    params = {
        "workspace_id": workspace_id,
        "image_path": image_path,
    }
    headers = get_headers()
    try:
        response = httpx.get(url, params=params, headers=headers, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        if data.get("status") != 1:
            logger.warning(f"获取图片下载链接失败: {data.get('info', '未知错误')}")
            return None
        attachment = data.get("data", {}).get("Attachment", {})
        download_url = attachment.get("download_url", "")
        if not download_url:
            logger.warning(f"API 返回空下载链接: image_path={image_path}")
            return None
        logger.info(f"获取图片下载链接成功: {attachment.get('filename', image_path)}")
        return download_url
    except Exception as e:
        logger.warning(f"请求图片下载链接异常: {e}, image_path={image_path}")
        return None


def download_images(
    images: list,
    images_dir: str,
    workspace_id: str,
    timeout: float = 30.0,
) -> dict:
    """
    下载图片到本地目录。

    先通过 TAPD API 获取临时下载链接（有效期 300s），再下载图片。

    Args:
        images: extract_images_from_html 返回的图片列表
        images_dir: 本地图片保存目录（绝对路径）
        workspace_id: 项目空间 ID，用于获取图片下载链接
        timeout: 单张图片下载超时时间（秒）

    Returns:
        dict: original_src -> local_relative_path 的映射
              下载失败时映射值回退为 original_src
    """
    os.makedirs(images_dir, exist_ok=True)
    image_map = {}
    for img in images:
        local_path = os.path.join(images_dir, img["filename"])
        # 先通过 API 获取临时下载链接
        download_url = get_image_download_url(workspace_id, img["original_src"])
        if not download_url:
            logger.warning(f"无法获取图片下载链接: {img['original_src']}，跳过")
            image_map[img["original_src"]] = img["original_src"]
            continue
        try:
            response = httpx.get(download_url, timeout=timeout)
            response.raise_for_status()
            with open(local_path, "wb") as f:
                f.write(response.content)
            logger.info(f"图片已下载: {img['filename']} ({len(response.content)} bytes)")
            image_map[img["original_src"]] = f"images/{img['filename']}"
        except Exception as e:
            logger.warning(f"图片下载失败: {img['filename']}, 错误: {e}")
            image_map[img["original_src"]] = img["original_src"]
    return image_map


def convert_html_images_to_markdown(html_content: str, image_map: dict) -> str:
    """
    将 HTML 中的 <img> 标签替换为 Markdown 图片语法。

    Args:
        html_content: HTML 格式的描述内容
        image_map: download_images 返回的图片映射

    Returns:
        str: 替换后的内容
    """
    def replace_img(match):
        tag = match.group(0)
        src_match = re.search(r'src="([^"]+)"', tag)
        if not src_match:
            return ""
        original_src = unescape(src_match.group(1))
        local_path = image_map.get(original_src, original_src)
        # 获取 alt 文本，无则留空
        alt_match = re.search(r'alt="([^"]*)"', tag)
        alt = alt_match.group(1) if alt_match else ""
        return f'\n\n![{alt}]({local_path})\n\n'

    return re.sub(r'<img[^>]*/?>', replace_img, html_content)


def build_story_markdown(story: dict) -> str:
    """
    根据需求详情生成 Markdown 内容。

    Args:
        story: 需求详情字典

    Returns:
        str: Markdown 格式的需求信息
    """
    lines = []
    lines.append(f"# {story.get('name', '未知需求')}")
    lines.append("")
    lines.append("## 基本信息")
    lines.append("")

    field_labels = {
        "id": "需求 ID",
        "name": "需求名称",
        "status": "状态",
        "owner": "负责人",
        "priority": "优先级",
        "iteration_id": "迭代 ID",
        "created": "创建时间",
        "modified": "最后修改时间",
        "test_focus": "测试重点"
    }

    for key, label in field_labels.items():
        value = story.get(key, "")
        if value:
            lines.append(f"- **{label}**: {value}")

    # description 字段单独处理，可能包含 HTML/Markdown
    description = story.get("description", "")
    if description:
        lines.append("")
        lines.append("## 需求描述")
        lines.append("")
        lines.append(description)

    return "\n".join(lines)


def save_story_output(
    story: dict,
    output_dir: str,
    workspace_id: str = "",
    output_format="md",
) -> str:
    """
    将需求详情保存到输出目录。

    如果 description 包含图片引用，会自动下载图片到 images/ 子目录，
    并将 HTML <img> 标签替换为 Markdown 图片语法。

    Args:
        story: 需求详情字典
        output_dir: 输出目录路径
        workspace_id: 项目空间 ID，用于下载图片
        output_format: 输出格式（"md" 或 "json"）

    Returns:
        str: 生成的文件路径
    """
    os.makedirs(output_dir, exist_ok=True)

    story_name = story.get("name", "unknown_story")
    safe_name = "tapd-" + sanitize_filename(story_name)

    # 处理 description 中的图片
    description = story.get("description", "")
    if description and workspace_id:
        images = extract_images_from_html(description)
        if images:
            logger.info(f"发现 {len(images)} 张图片引用，开始下载...")
            images_dir = os.path.join(output_dir, "images")
            image_map = download_images(images, images_dir, workspace_id)
            # 更新 story 的 description，将 HTML <img> 替换为 Markdown
            story = dict(story)  # 浅拷贝，避免修改原始数据
            story["description"] = convert_html_images_to_markdown(description, image_map)
            logger.info(f"图片处理完成：{len(image_map)} 张")

    # 保存 Markdown 文件
    if output_format == "md":
        output_path = os.path.join(output_dir, f"{safe_name}.md")
        md_content = build_story_markdown(story)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        logger.info(f"Markdown 文件已保存: {output_path}")
        return output_path
    else:
        # 保存 JSON 文件
        output_path = os.path.join(output_dir, f"{safe_name}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(story, f, ensure_ascii=False, indent=2)
        logger.info(f"JSON 文件已保存: {output_path}")
        return output_path


def main():
    parser = argparse.ArgumentParser(
        description="获取 TAPD 需求详情信息"
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="TAPD 需求链接（列表页或详情页 URL）",
    )
    parser.add_argument(
        "--workspace-id",
        dest="workspace_id",
        help="项目空间 ID（如果直接提供，则不需要 URL）",
    )
    parser.add_argument(
        "--story-id",
        dest="story_id",
        help="需求 ID（如果直接提供，则不需要 URL）",
    )
    parser.add_argument(
        "--fields",
        default=DEFAULT_FIELDS,
        help=f"需要查询的字段，逗号分隔（默认: {DEFAULT_FIELDS}）",
    )
    parser.add_argument(
        "--output-dir",
        dest="output_dir",
        default=None,
        help="输出目录路径，在此目录下生成 .md 和 .json 文件",
    )

    args = parser.parse_args()
    workspace_id = None
    story_id = None
    # 确定 workspace_id 和 story_id
    if args.url:
        parsed = parse_tapd_url(args.url)
        workspace_id = parsed["workspace_id"]
        story_id = parsed["story_id"]
    elif args.workspace_id and args.story_id:
        workspace_id = args.workspace_id
        story_id = args.story_id
    else:
        parser.error("请提供 TAPD URL，或同时提供 --workspace-id 和 --story-id")
    if not workspace_id or not story_id:
        parser.error("无法解析 workspace_id 或 story_id，请检查输入")
    print(f"正在获取需求详情: workspace_id={workspace_id}, story_id={story_id}")
    # 获取需求详情
    try:
        data = fetch_story_detail(workspace_id, story_id, fields=args.fields)
        story = extract_story_from_response(data)

        if not story:
            logger.error("未获取到需求数据")
            return None
        # 输出到目录（如果指定）
        if args.output_dir:
            output_path = save_story_output(story, args.output_dir, workspace_id)
            print(f"需求正文已保存至文件: {output_path}")
        else:
            # 友好的控制台输出
            print(json.dumps(story, ensure_ascii=False, indent=2))

        return story

    except Exception as e:
        logger.error(f"获取需求详情失败: {e}")
        raise


if __name__ == "__main__":
    main()
