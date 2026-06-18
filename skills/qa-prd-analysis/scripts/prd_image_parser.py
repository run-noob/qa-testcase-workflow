#!/usr/bin/env python3
"""
Parse PRD images into structured textual descriptions.

Features:
- Parse all images in a PRD markdown file, or one specific image via --image-path.
- Build per-image context from markdown nearby lines and heading chain.
- Build one PRD-level summary and reuse it across image analyses.
- Cache PRD summary and image analysis results to reduce repeated LLM calls.
- Emit machine-readable JSON and human-readable Markdown reports.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


SUMMARY_PROMPT_VERSION = "v1"
IMAGE_PROMPT_VERSION = "v2"
BATCH_PROMPT_VERSION = "v2"
DEFAULT_MAX_IMAGES = 50
DEFAULT_RETRY = 2
DEFAULT_TIMEOUT = 60
CONTEXT_WINDOW = 50
DEFAULT_BATCH_GAP = 100
DEFAULT_MAX_BATCH = 20


@dataclass
class ImageRef:
    image_id: str
    alt: str
    raw_path: str
    resolved_path: Path
    line_no: int
    raw_line: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Parse PRD images into textual descriptions."
    )
    parser.add_argument("--prd-file", required=True, help="Path to PRD markdown file.")
    parser.add_argument("--output-dir", required=False, help="Output directory.")
    parser.add_argument("--image-path", help="Optional single image path from PRD (relative or absolute).")
    parser.add_argument("--custom-prompt", help="单图模式下的自定义分析指令，与 --image-path 配合使用。用于深度解析某张图的特定信息。")
    parser.add_argument("--model", default="google/gemini-3-flash-preview", help="Model used for summary and image analysis.")
    parser.add_argument("--max-images", type=int, default=DEFAULT_MAX_IMAGES, help="Max image count in full mode.")
    parser.add_argument(
        "--detail-level",
        choices=["brief", "standard", "deep"],
        default="standard",
        help="Description detail level.",
    )
    parser.add_argument("--retry", type=int, default=DEFAULT_RETRY, help="Retry times per model call.")
    parser.add_argument(
        "--on-error",
        choices=["abort", "skip"],
        default="skip",
        help="Error handling strategy.",
    )
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Timeout seconds per model call.")
    parser.add_argument("--dry-run", action="store_true", help="Only scan and prepare outputs, no model calls.")
    parser.add_argument(
        "--include-image-snippet",
        action="store_true",
        help="Include raw markdown image line in outputs.",
    )
    parser.add_argument("--emit-json", action="store_true", help="Emit JSON output.")
    parser.add_argument("--emit-md", action="store_true", help="Emit Markdown output.")
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Ignore caches and force regenerate summary and image analysis.",
    )
    parser.add_argument(
        "--embed",
        action="store_true",
        help="将图片描述嵌入源 Markdown 文件中图片引用的紧后方（幂等，重复运行不重复插入）。",
    )
    parser.add_argument("--batch-gap", type=int, default=DEFAULT_BATCH_GAP,
                        help="Max line gap between adjacent images to include in same batch.")
    parser.add_argument("--max-batch-size", type=int, default=DEFAULT_MAX_BATCH,
                        help="Max images per batch call.")
    parser.add_argument("--no-batch", action="store_true",
                        help="Disable batching, process images one by one.")
    return parser.parse_args()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def get_download_dir(prd_dir: Path):
    return prd_dir / "downloaded-images"


def extract_markdown_images(prd_text: str, prd_dir: Path) -> List[ImageRef]:
    # 模式定义（注意：字符类 [^>] 和 [^)] 默认匹配换行符，无需 DOTALL）
    md_pattern = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
    html_pattern = re.compile(r"<img\s+([^>]*?)\s*/?\s*>", re.IGNORECASE)

    refs: List[ImageRef] = []
    idx = 1

    # 收集所有匹配的 (起始位置, 匹配对象, 类型)
    matches = []

    # Markdown 图片
    for match in md_pattern.finditer(prd_text):
        matches.append((match.start(), 'md', match))

    # HTML 图片
    for match in html_pattern.finditer(prd_text):
        matches.append((match.start(), 'html', match))

    # 按起始位置排序
    matches.sort(key=lambda x: x[0])

    for start_pos, img_type, match in matches:
        # 计算行号（基于原始文本中的换行符）
        line_no = prd_text[:start_pos].count('\n') + 1

        if img_type == 'md':
            alt = match.group(1).strip()
            raw_path = cleanup_markdown_link_path(match.group(2).strip())
        else:  # html
            attr_str = match.group(1)
            src_match = re.search(r'src\s*=\s*(["\'])(.*?)\1', attr_str, re.IGNORECASE)
            alt_match = re.search(r'alt\s*=\s*(["''])(.*?)\1', attr_str, re.IGNORECASE)
            if not src_match:
                continue  # 缺少 src 则跳过
            raw_path = cleanup_markdown_link_path(src_match.group(2).strip())
            alt = alt_match.group(2).strip() if alt_match else ""

        if is_http_url(raw_path):
            resolved = download_image(raw_path, prd_dir)
            if resolved is None:
                continue
        else:
            resolved = (prd_dir / raw_path).resolve() if not Path(raw_path).is_absolute() else Path(raw_path).resolve()
            if not resolved.exists():
                print(f"[WARNING] image path: {resolved} does not exists")
                continue
        # raw_line 使用整个匹配到的原始字符串（可能包含换行）
        raw_line = match.group(0)

        refs.append(
            ImageRef(
                image_id=f"IMG-{idx:03d}",
                alt=alt,
                raw_path=raw_path,
                resolved_path=resolved,
                line_no=line_no,
                raw_line=raw_line,
            )
        )
        idx += 1

    return refs


def cleanup_markdown_link_path(raw: str) -> str:
    candidate = raw.strip().strip("<>").strip()
    if " " in candidate and '"' in candidate:
        candidate = candidate.split('"')[0].strip()
    if " " in candidate and "'" in candidate:
        candidate = candidate.split("'")[0].strip()
    return candidate


def is_http_url(path: str) -> bool:
    return path.startswith("http://") or path.startswith("https://")


def download_image(url: str, prd_dir: Path) -> Optional[Path]:
    """Download an image from a URL to a local cache directory."""
    url_hash = hashlib.md5(url.encode()).hexdigest()
    parsed = url.split("?")[0]
    suffix = Path(parsed).suffix.lower()
    if suffix not in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"):
        suffix = ".png"
    download_dir = get_download_dir(prd_dir)
    local_path = download_dir / f"{url_hash}{suffix}"
    if local_path.exists():
        return local_path
    ensure_dir(download_dir)
    try:
        urllib.request.urlretrieve(url, str(local_path))
        return local_path
    except Exception as e:
        print(f"[WARNING] Failed to download {url}: {e}")
        return None


def resolve_single_image_path(prd_dir: Path, user_image_path: str, cwd: Path) -> Path:
    if is_http_url(user_image_path):
        local = download_image(user_image_path, prd_dir)
        if local is not None:
            return local
        return Path(user_image_path)
    candidate = Path(user_image_path)
    if candidate.is_absolute() and candidate.exists():
        return candidate.resolve()
    prd_candidate = (prd_dir / candidate).resolve()
    if prd_candidate.exists():
        return prd_candidate
    cwd_candidate = (cwd / candidate).resolve()
    if cwd_candidate.exists():
        return cwd_candidate
    return prd_candidate


def heading_chain_until_line(prd_text: str, target_line: int) -> List[str]:
    headings: Dict[int, str] = {}
    for line_no, line in enumerate(prd_text.splitlines(), start=1):
        if line_no > target_line:
            break
        m = re.match(r"^(#{1,6})\s+(.*)$", line.strip())
        if not m:
            continue
        level = len(m.group(1))
        title = m.group(2).strip()
        headings[level] = title
        for key in list(headings.keys()):
            if key > level:
                headings.pop(key, None)
    return [headings[k] for k in sorted(headings.keys())]


def local_context(prd_text: str, line_no: int, window: int = CONTEXT_WINDOW) -> str:
    lines = prd_text.splitlines()
    start = max(1, line_no - window)
    end = min(len(lines), line_no + window)
    out = []
    for idx in range(start, end + 1):
        out.append(f"{lines[idx - 1]}")
    return "\n".join(out)


def cache_paths(cache_dir: Path, key: str, prefix: str) -> Tuple[Path, Path]:
    data = cache_dir / f"{prefix}-{key}.json"
    meta = cache_dir / f"{prefix}-{key}.meta.json"
    return data, meta


def read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def file_summary_key(prd_text: str, model: str) -> str:
    payload = json.dumps(
        {
            "prd_sha": sha256_text(prd_text),
            "summary_prompt_version": SUMMARY_PROMPT_VERSION,
            "model": model,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return sha256_text(payload)


def image_analysis_key(
    image_path: str,
    file_summary_text: str,
    model: str,
    detail_level: str,
    prompt_version: str = IMAGE_PROMPT_VERSION,
    custom_prompt: Optional[str] = None,
) -> str:
    payload_dict: Dict[str, Any] = {
        "image_path": image_path,
        "file_summary_sha": sha256_text(file_summary_text),
        "detail_level": detail_level,
        "image_prompt_version": prompt_version,
        "model": model,
    }
    if custom_prompt:
        payload_dict["custom_prompt_sha"] = sha256_text(custom_prompt)
    payload = json.dumps(
        payload_dict,
        ensure_ascii=False,
        sort_keys=True,
    )
    return sha256_text(payload)


# def _openai_responses_call_openai(
#     model: str,
#     messages: List[Dict[str, Any]],
#     timeout: int,
# ) -> str:
#     api_key = os.environ.get("OPENAI_API_KEY", "")
#     api_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1/completions")
#     if not api_key:
#         raise RuntimeError("Missing OPENAI_API_KEY.")
#     client = openai.OpenAI(api_key=api_key, base_url=api_url)
#
#     try:
#         response = client.chat.completions.create(
#             model=model,
#             messages=messages,
#             temperature=0.2
#         )
#         # 提取回复内容
#         return response.choices[0].message.content
#     except openai.APIError as e:
#         print(f"OpenAI API 错误: {e}")
#         return None
#     except Exception as e:
#         print(f"发生未知错误: {e}")
#         return None


def _get_api_key_and_url():
    openai_base_url = os.environ.get("OPENAI_BASE_URL", "https://copilot.huya.info/api/openai/v1")
    openai_api_key = os.environ.get("OPENAI_API_KEY", "")
    if openai_api_key:
        return openai_base_url, openai_api_key
    anthropic_base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://copilot.huya.info/api/anthropic")
    anthropic_api_key = os.environ.get("ANTHROPIC_AUTH_TOKEN")
    if anthropic_api_key:
        return anthropic_base_url, anthropic_api_key

def _openai_responses_call(
    model: str,
    messages: List[Dict[str, Any]],
    timeout: int,
) -> Optional[str]:
    base_url, api_key = _get_api_key_and_url()

    if not api_key:
        raise RuntimeError("图片分析能力依赖OPENAI_API_KEY和OPENAI_BASE_URL，当前环境没有配置，请引导用户配置该环境变量")

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2
    }
    data = json.dumps(payload).encode("utf-8")
    chat_completion_url = base_url+"/chat/completions"
    req = urllib.request.Request(
        url=chat_completion_url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            result = json.loads(body)
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        # HTTP状态码错误（4xx/5xx）
        err_text = e.read().decode("utf-8", errors="ignore")
        print(f"OpenAI HTTP 错误: {e.code}, {err_text}")
        return None
    except urllib.error.URLError as e:
        # 网络层错误（DNS、连接失败等）
        print(f"网络错误: {e}")
        return None
    except Exception as e:
        print(f"发生未知错误: {e}")
        return None


def call_with_retry(fn, retry: int, on_error: str):
    last_err: Optional[Exception] = None
    for i in range(retry + 1):
        try:
            return fn()
        except Exception as e:  # pylint: disable=broad-except
            last_err = e
            if i < retry:
                time.sleep(min(2 ** i, 4))
                continue
            if on_error == "abort":
                raise
    raise RuntimeError(str(last_err) if last_err else "Unknown error.")


def generate_prd_summary(prd_text: str, model: str, timeout: int, retry: int, on_error: str) -> str:
    truncated = prd_text[:14000]
    system_prompt = (
        "你是资深测试分析师。请基于输入的PRD文本输出精炼文件摘要，"
        "用于后续图片语义理解。只输出摘要正文，不要解释。"
    )
    user_prompt = (
        "请输出以下内容：\n"
        "1) 需求背景和目标\n"
        "2) 核心功能和关键流程\n"
        "3) 主要页面/模块\n"
        "4) 关键业务规则/约束\n"
        "5) 测试高风险点\n\n"
        "PRD文本如下：\n"
        f"{truncated}"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    return call_with_retry(
        lambda: _openai_responses_call(model=model, messages=messages, timeout=timeout),
        retry=retry,
        on_error=on_error,
    )


def group_images_by_proximity(
    refs: List[ImageRef],
    gap_threshold: int,
    max_size: int,
) -> List[List[ImageRef]]:
    if not refs:
        return []
    groups: List[List[ImageRef]] = [[refs[0]]]
    for ref in refs[1:]:
        last_line = groups[-1][-1].line_no
        if ref.line_no - last_line <= gap_threshold and len(groups[-1]) < max_size:
            groups[-1].append(ref)
        else:
            groups.append([ref])
    return groups


def batch_local_context(prd_text: str, refs: List[ImageRef], window: int = CONTEXT_WINDOW) -> str:
    lines = prd_text.splitlines()
    first_line = refs[0].line_no
    last_line = refs[-1].line_no
    start = max(1, first_line - window)
    end = min(len(lines), last_line + window)
    return "\n".join(f"{lines[i - 1]}" for i in range(start, end + 1))


def build_batch_prompt(
    detail_level: str,
    file_summary: str,
    heading_chain: List[str],
    batch_ctx: str,
    batch_refs: List[ImageRef],
) -> str:
    detail_map = {
        "brief": "简洁描述，优先关键点。",
        "standard": "标准深度，覆盖关键细节与边界信息。",
        "deep": "深入描述，尽可能细化组件、流程与条件关系。",
    }
    n = len(batch_refs)
    heading_text = " > ".join(heading_chain) if heading_chain else "[无章节上下文]"
    filenames = [r.resolved_path.name for r in batch_refs]

    prompt = (
        f"你是QA视觉分析助手，本次分析 PRD 同一区域的 {n} 张图片。\n\n"
        "【重要】信息优先级规则：图片/Figma 原型仅作为 UI 参考，优先级低于 PRD 正文。"
        "如果图片中的 UI 布局、字段、交互细节与 PRD 正文描述存在差异，以 PRD 正文中的业务逻辑为准，"
        "在分析结果中标注差异点（使用格式：[与正文不一致: 具体差异描述]），但不要因图片而推翻正文结论。\n\n"
        "可以从以下维度思考：\n"
        "1. 图片类型识别（UI原型、流程图、架构图、状态机图、参考截图等）\n"
        "2. 整体布局和空间关系（如果是UI原型图），按从上至下、从左到右的顺序描述区域/组件\n"
        "3. UI组件的视觉特征及交互状态\n"
        "4. 图表中的数据关系和流向\n"
        "5. 与产品需求的关联（注意标注与 PRD 正文不一致之处）\n\n"
        "输出要求：\n"
        "- 只输出可读文本，不要JSON。\n"
        "- 对无法识别的信息显式标注：[无法识别: xxx]。\n"
        "- 对与 PRD 正文不一致的地方显式标注：[与正文不一致: 具体差异描述]。\n"
        "- 不要输出与图片无关的臆测。\n"
        f"- 详细程度：{detail_map[detail_level]}\n\n"
        "=== PRD文件摘要 ===\n"
        f"{file_summary}\n\n"
        f"=== 图片所在章节链 ===\n{heading_text}\n\n"
        f"=== 区域上下文（第一张图片前后各{CONTEXT_WINDOW}行至最后一张图片前后各{CONTEXT_WINDOW}行）===\n"
        f"{batch_ctx}\n\n"
        # "=== 各图片信息 ===\n"
    )
    # for r in batch_refs:
    #     prompt += f"- {r.resolved_path.name}  alt: {r.alt or '[空]'}\n"

    prompt += (
        "\n=== 输出格式要求 ===\n"
        "逐张分析，使用文件名作为分隔符，格式严格如下（每个 ### 标题单独一行）：\n"
    )
    for fname in filenames:
        prompt += f"### {fname}\n[该图片的分析文本]\n"

    return prompt


def analyze_images_batch(
    filenames_and_paths: List[Tuple[str, Path]],
    prompt_text: str,
    model: str,
    timeout: int,
    retry: int,
    on_error: str,
) -> Optional[str]:
    content: List[Dict[str, Any]] = [{"type": "text", "text": prompt_text}]
    for _fname, img_path in filenames_and_paths:
        mime = guess_mime(img_path)
        b64 = base64.b64encode(img_path.read_bytes()).decode("utf-8")
        content.append({"type": "image_url", "image_url": f"data:{mime};base64,{b64}"})
    messages = [
        {"role": "system", "content": "你是严谨的QA视觉分析助手。"},
        {"role": "user", "content": content},
    ]
    return call_with_retry(
        lambda: _openai_responses_call(model=model, messages=messages, timeout=timeout),
        retry=retry,
        on_error=on_error,
    )


def parse_batch_response(response_text: str, filenames: List[str]) -> Dict[str, str]:
    results: Dict[str, str] = {fn: "" for fn in filenames}
    positions: List[Tuple[int, int, str]] = []
    for fn in filenames:
        pattern = re.compile(r"###\s*" + re.escape(fn) + r"[^\n]*\n?")
        m = pattern.search(response_text)
        if m:
            positions.append((m.start(), m.end(), fn))
    positions.sort()
    for i, (_, content_start, fn) in enumerate(positions):
        next_header = positions[i + 1][0] if i + 1 < len(positions) else len(response_text)
        results[fn] = response_text[content_start:next_header].strip()
    return results


def build_image_prompt(
    detail_level: str,
    file_summary: str,
    heading_chain: List[str],
    local_ctx: str,
    image_alt: str,
    custom_prompt: Optional[str] = None,
) -> str:
    detail_map = {
        "brief": "简洁描述，优先关键点。",
        "standard": "标准深度，覆盖关键细节与边界信息。",
        "deep": "深入描述，尽可能细化组件、流程与条件关系。",
    }
    heading_text = " > ".join(heading_chain) if heading_chain else "[无章节上下文]"
    prompt = (
        "你是一名QA需求分析专家。请根据图片内容、PRD文件摘要和图片局部上下文，"
        "输出一段结构化自然语言描述。\n\n"
        "【重要】信息优先级规则：图片/Figma 原型仅作为 UI 参考，优先级低于 PRD 正文。"
        "如果图片中的 UI 布局、字段、交互细节与 PRD 正文描述存在差异，以 PRD 正文中的业务逻辑为准，"
        "在分析结果中标注差异点（使用格式：[与正文不一致: 具体差异描述]），但不要因图片而推翻正文结论。\n\n"
        "可以从以下维度思考：\n"
        "1. 图片类型识别（UI原型、流程图、状态机图、架构图、参考截图等）\n"
        "2. 整体布局和空间关系(如果是UI原型图），按从上至下，从左到右的顺序描述区域/组件\n"
        "3. UI组件的视觉特征及交互状态\n"
        "4. 图表中的数据关系和流向\n"
        "5. 与产品需求的关联（注意标注与 PRD 正文不一致之处）\n\n"
        "输出要求：\n"
        "- 只输出一段可读文本（analysis_text），不要JSON。\n"
        "- 对无法识别的信息显式标注：[无法识别: xxx]。\n"
        "- 对与 PRD 正文不一致的地方显式标注：[与正文不一致: 具体差异描述]。\n"
        "- 不要输出与图片无关的臆测。\n"
        f"- 详细程度：{detail_map[detail_level]}\n\n"
        "=== PRD文件摘要 ===\n"
        f"{file_summary}\n\n"
    )
    if heading_text:
        prompt += f"=== 图片所在章节链 ===\n{heading_text}\n\n"
    prompt += f"=== 图片局部上下文(前后文) ===\n{local_ctx}\n"
    if image_alt:
        prompt += f"=== 图片标注信息 ===\nalt: {image_alt or '[空]'}\n"
    if custom_prompt:
        prompt += f"\n=== 用户要求的重点关注信息 ===\n{custom_prompt}\n"
    return prompt


def analyze_image(
    image_path: Path,
    prompt_text: str,
    model: str,
    timeout: int,
    retry: int,
    on_error: str,
) -> str:
    mime = guess_mime(image_path)
    image_b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    data_url = f"data:{mime};base64,{image_b64}"

    messages = [
        {
            "role": "system",
            "content": "你是严谨的QA视觉分析助手。",
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_text},
                {"type": "image_url", "image_url": data_url},
            ],
        },
    ]

    return call_with_retry(
        lambda: _openai_responses_call(model=model, messages=messages, timeout=timeout),
        retry=retry,
        on_error=on_error,
    )


def guess_mime(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in (".jpg", ".jpeg"):
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    if suffix == ".gif":
        return "image/gif"
    return "image/png"


def _find_image_in_line(line_content: str, raw_path: str) -> Optional[re.Match]:
    """在行内容中查找图片引用，先尝试 Markdown 语法再尝试 HTML <img> 标签。"""
    escaped = re.escape(raw_path)
    # Markdown 语法: ![alt](path)
    md_re = re.compile(r'!\[[^\]]*\]\(' + escaped + r'\)')
    m = md_re.search(line_content)
    if m:
        return m
    # HTML 语法: <img ... src="path" ...>
    html_re = re.compile(
        r'<img\b[^>]*?src\s*=\s*["\']' + escaped + r'["\'][^>]*?/?\s*>',
        re.IGNORECASE,
    )
    return html_re.search(line_content)


def embed_descriptions_into_markdown(
    md_path: Path,
    image_outputs: List[Dict[str, Any]],
) -> Path:
    """
    将图片分析描述嵌入 Markdown，写入新文件（覆盖 md_path），原始文件归档到 raw_dir。

    - 每张图片的描述都插入到该图片引用之后（不分单图/多图）。
    - Markdown 语法 `![alt](path)`：在图片后插入 blockquote 格式的描述块。
    - HTML 语法 `<img>`：在标签后插入内联 HTML 描述。

    幂等：重复运行不重复插入。
    按行号从大到小倒序处理，同行内按位置从右到左处理，保证插入时前面的位置不漂移。

    Args:
        image_outputs: 图片描述结果
        md_path: 原始markdown文件

    Returns:
        新生成的嵌入描述后的文件路径。
    """

    content = md_path.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)

    # 按 source_line 分组（只保留有描述文本的项）
    line_groups: Dict[int, List[Dict[str, Any]]] = {}
    for item in image_outputs:
        if not item.get("analysis_text", "").strip():
            continue
        ln = item["source_line"]
        line_groups.setdefault(ln, []).append(item)

    embedded = 0
    for line_no in sorted(line_groups.keys(), reverse=True):
        items = line_groups[line_no]
        idx = line_no - 1  # 0-based
        if idx < 0 or idx >= len(lines):
            continue

        line_content = lines[idx]

        # 先找到每张图片在行内的位置，按位置从右到左排序（倒序插入避免位置偏移）
        item_positions: List[Tuple[int, Dict[str, Any]]] = []
        for item in items:
            raw_path = item.get("raw_path", "")
            if not raw_path:
                continue
            m = _find_image_in_line(line_content, raw_path)
            if m:
                item_positions.append((m.start(), item))
            else:
                # 图片引用可能已被之前的嵌入修改；用宽松匹配兜底
                label = raw_path.split("/")[-1]
                fallback = re.compile(re.escape(label))
                fm = fallback.search(line_content)
                if fm:
                    item_positions.append((fm.start(), item))

        # 按位置从右到左处理
        item_positions.sort(key=lambda x: x[0], reverse=True)

        for _, item in item_positions:
            raw_path = item.get("raw_path", "")
            analysis_text = item.get("analysis_text", "").strip()
            if not raw_path or not analysis_text:
                continue

            label = raw_path.split("/")[-1] if raw_path else item.get("image_id", "")

            # 在当前（可能已被修改过的）行内容中重新匹配图片引用
            m = _find_image_in_line(line_content, raw_path)
            if not m:
                continue

            match_text = m.group(0)
            is_html = match_text.lower().startswith("<img")
            img_desc_start = "---图片描述开始---"
            img_desc_end = "---图片描述结束---"
            if is_html:
                # HTML <img> 标签：在标签后插入内联 HTML 描述
                _inline_marker = "图片文件名:"
                marker = f"{_inline_marker} {label}"
                # 幂等检查
                if marker in line_content[m.end():]:
                    continue
                safe_text = analysis_text.replace("\n", "<br/>")
                desc_html = (
                    f"<br/>{img_desc_start}<br/>"
                    f"<b>{marker}</b><br/><br/>"
                    f"{safe_text}<br/>"
                    f"{img_desc_end}"
                )
                line_content = line_content[:m.end()] + desc_html + line_content[m.end():]
                embedded += 1
            else:
                # Markdown ![alt](path) 语法：在图片后插入 blockquote 描述块
                # 幂等检查：图片后紧跟的文本中是否已存在 embed_marker
                embed_marker = "图片文件名:"
                after_match = line_content[m.end():]
                if embed_marker in after_match:
                    continue
                desc_lines = analysis_text.splitlines()
                block_parts = [f"\n{img_desc_start}\n", f"\n{embed_marker} `{label}`\n", "\n```text\n"]
                for dl in desc_lines:
                    block_parts.append(f" {dl}\n" if dl.strip() else "\n")
                block_parts.append("```\n")
                block_parts.append(f"{img_desc_end}\n")
                desc_block = "".join(block_parts)
                line_content = line_content[:m.end()] + desc_block + line_content[m.end():]
                embedded += 1

        lines[idx] = line_content

    new_content = "".join(lines)
    new_md_path = md_path.with_stem(md_path.stem + "-image-desc-embedded")
    new_md_path.write_text(new_content, encoding="utf-8")
    return new_md_path


def build_md_report(
    meta: Dict[str, Any],
    images: List[Dict[str, Any]],
    errors: List[str],
    include_image_snippet: bool,
) -> str:
    lines: List[str] = []
    if meta['mode'] == "single-image":
        lines.append("图片解析结果:\n")
    else:
        lines.append(f"# PRD 图片解析报告 - {meta['feature_name']}")
        lines.append("")
        lines.append("## 元信息")
        lines.append(f"- PRD 文件: `{meta['prd_file']}`")
        lines.append(f"- 生成时间(UTC): `{meta['generated_at']}`")
        lines.append(f"- 模型: `{meta['model']}`")
        lines.append(f"- 模式: `{meta['mode']}`")
        lines.append("")
        lines.append("## 图片解析结果")
        if not images:
            lines.append("- 无可解析图片")

    for item in images:
        lines.append(f"### {item['image_id']}")
        lines.append(f"- 图片路径: `{item['raw_path']}`")
        lines.append(f"- 来源行号: `{item['source_line']}`")
        if include_image_snippet and item.get("image_snippet"):
            lines.append(f"- Markdown 引用: `{item['image_snippet']}`")
        lines.append("")
        alt_text = item.get("alt") or item["image_id"]
        lines.append(f"![{alt_text}]({item['raw_path']})")
        lines.append("")
        lines.append(item["analysis_text"])
        lines.append("")
    if errors:
        lines.append("## 错误与警告")
        for e in errors:
            lines.append(f"- {e}")
    lines.append("")
    return "\n".join(lines)


def _append_output(
    ref: ImageRef,
    analysis_text: str,
    include_image_snippet: bool,
    image_outputs: List[Dict[str, Any]],
) -> None:
    out_item: Dict[str, Any] = {
        "image_id": ref.resolved_path.name,
        "image_path": str(ref.resolved_path),
        "raw_path": str(ref.raw_path),
        "source_line": ref.line_no,
        "alt": ref.alt,
        "analysis_text": analysis_text,
    }
    if include_image_snippet:
        out_item["image_snippet"] = ref.raw_line
    image_outputs.append(out_item)


def parse_prd_images(
    prd_file: Path,
    *,
    output_dir: Optional[Path] = None,
    image_path: Optional[str] = None,
    model: str = "google/gemini-3-flash-preview",
    max_images: int = DEFAULT_MAX_IMAGES,
    detail_level: str = "standard",
    retry: int = DEFAULT_RETRY,
    on_error: str = "skip",
    timeout: int = DEFAULT_TIMEOUT,
    dry_run: bool = False,
    include_image_snippet: bool = False,
    emit_json: bool = False,
    emit_md: bool = True,
    force_refresh: bool = False,
    embed: bool = False,
    batch_gap: int = DEFAULT_BATCH_GAP,
    max_batch_size: int = DEFAULT_MAX_BATCH,
    no_batch: bool = False,
    custom_prompt: Optional[str] = None,
) -> Path | None:
    """
    解析 PRD Markdown 中的图片，生成文字描述，可选嵌入源文件。
    可作为库函数直接调用，也可通过 main() / CLI 使用。
    """
    prd_file = prd_file.resolve()
    feature_name = prd_file.stem
    if not prd_file.exists():
        print(f"[ERROR] PRD file not found: {prd_file}", file=sys.stderr)
        return
    if output_dir is None:
        output_dir = prd_file.parent.resolve()
    else:
        output_dir = output_dir.resolve()
    ensure_dir(output_dir)
    cache_dir = output_dir / ".cache" / "prd-image-parser"
    ensure_dir(cache_dir)

    prd_text = load_text(prd_file)
    prd_dir = prd_file.parent

    refs = extract_markdown_images(prd_text, prd_dir)
    errors: List[str] = []
    selected: List[ImageRef] = []

    if image_path:
        target = resolve_single_image_path(prd_dir, image_path, Path.cwd())
        matched = [r for r in refs if r.resolved_path == target]
        if matched:
            selected = [matched[0]]
        else:
            if not target.exists():
                print(f"[ERROR] Single image not found: {target}", file=sys.stderr)
                return
            errors.append(f"单图模式: 图片未在PRD中找到引用，将降级使用文件级上下文。path={target}")
            selected = [
                ImageRef(
                    image_id="IMG-001",
                    alt="",
                    raw_path=image_path,
                    resolved_path=target,
                    line_no=1,
                    raw_line="",
                )
            ]
    else:
        selected = refs[:max_images]

    if not selected:
        raise ValueError("No images found to parse.")

    if custom_prompt and not image_path:
        print("[HINT] --custom-prompt 仅在单图模式（同时指定 --image-path）下生效，当前为全量模式，该参数将被忽略。")

    summary = ""
    summary_key = file_summary_key(prd_text, model)
    summary_data_path, _ = cache_paths(cache_dir, summary_key, "file-summary")
    if summary_data_path.exists() and not force_refresh:
        summary_payload = read_json(summary_data_path)
        summary = summary_payload["summary_text"]
    elif dry_run:
        summary = "[dry-run] PRD summary skipped."
    else:
        summary = generate_prd_summary(
            prd_text=prd_text,
            model=model,
            timeout=timeout,
            retry=retry,
            on_error=on_error,
        )
        write_json(
            summary_data_path,
            {
                "key": summary_key,
                "summary_prompt_version": SUMMARY_PROMPT_VERSION,
                "model": model,
                "created_at": now_iso(),
                "summary_text": summary,
            },
        )

    image_outputs: List[Dict[str, Any]] = []
    success = 0
    failed = 0

    if no_batch:
        groups: List[List[ImageRef]] = [[ref] for ref in selected]
    else:
        groups = group_images_by_proximity(selected, batch_gap, max_batch_size)

    for group in groups:
        # Separate existing vs missing files
        valid_group: List[ImageRef] = []
        for ref in group:
            if not ref.resolved_path.exists():
                msg = f"图片不存在: {ref.resolved_path}"
                errors.append(msg)
                failed += 1
                if on_error == "abort":
                    print(f"[ERROR] {msg}", file=sys.stderr)
                    return 1
            else:
                valid_group.append(ref)

        if not valid_group:
            continue

        # Pass 1: check single-image cache for each image
        uncached_from_single: List[ImageRef] = []
        group_analysis: Dict[str, Optional[str]] = {}  # str(resolved_path) -> analysis_text

        for ref in valid_group:
            # ctx = local_context(prd_text, ref.line_no) if ref.line_no > 0 else "[无局部上下文]"
            i_key = image_analysis_key(
                image_path=ref.raw_path,
                file_summary_text=summary,
                model=model,
                detail_level=detail_level,
                custom_prompt=custom_prompt,
            )
            img_cache_path, _ = cache_paths(cache_dir, i_key, "image")
            if img_cache_path.exists() and not force_refresh:
                group_analysis[str(ref.resolved_path)] = read_json(img_cache_path)["analysis_text"]
            else:
                uncached_from_single.append(ref)

        if not uncached_from_single:
            # All cached via single-image keys
            for ref in valid_group:
                _append_output(ref, group_analysis[str(ref.resolved_path)], include_image_snippet, image_outputs)
                success += 1
            continue

        use_batch = len(uncached_from_single) >= 2 and not no_batch

        if use_batch:
            # Pass 2: check batch cache for each uncached image
            b_ctx = batch_local_context(prd_text, uncached_from_single)
            still_uncached: List[Tuple[ImageRef, str]] = []  # (ref, b_key)
            for ref in uncached_from_single:
                b_key = image_analysis_key(
                    image_path=ref.raw_path,
                    file_summary_text=summary,
                    model=model,
                    detail_level=detail_level,
                    prompt_version=BATCH_PROMPT_VERSION,
                )
                b_cache_path, _ = cache_paths(cache_dir, b_key, "image")
                if b_cache_path.exists() and not force_refresh:
                    group_analysis[str(ref.resolved_path)] = read_json(b_cache_path)["analysis_text"]
                else:
                    still_uncached.append((ref, b_key))

            if still_uncached:
                if dry_run:
                    for ref, _ in still_uncached:
                        group_analysis[str(ref.resolved_path)] = "[dry-run] image analysis skipped."
                else:
                    refs_to_batch = [r for r, _ in still_uncached]
                    filenames = [r.resolved_path.name for r in refs_to_batch]
                    heading = heading_chain_until_line(prd_text, refs_to_batch[0].line_no)
                    batch_prompt = build_batch_prompt(
                        detail_level=detail_level,
                        file_summary=summary,
                        heading_chain=heading,
                        batch_ctx=b_ctx,
                        batch_refs=refs_to_batch,
                    )
                    try:
                        raw_response = analyze_images_batch(
                            [(r.resolved_path.name, r.resolved_path) for r in refs_to_batch],
                            batch_prompt,
                            model=model,
                            timeout=timeout,
                            retry=retry,
                            on_error=on_error,
                        )
                        per_image = parse_batch_response(raw_response or "", filenames)
                        for ref, b_key in still_uncached:
                            fname = ref.resolved_path.name
                            analysis_text = per_image.get(fname, "")
                            b_cache_path, _ = cache_paths(cache_dir, b_key, "image")
                            if analysis_text:
                                write_json(b_cache_path, {
                                    "key": b_key,
                                    "image_prompt_version": BATCH_PROMPT_VERSION,
                                    "model": model,
                                    "detail_level": detail_level,
                                    "created_at": now_iso(),
                                    "image_path": str(ref.resolved_path),
                                    "raw_path": str(ref.raw_path),
                                    "analysis_text": analysis_text,
                                })
                            group_analysis[str(ref.resolved_path)] = analysis_text
                    except Exception as e:  # pylint: disable=broad-except
                        msg = f"批量解析失败 ({', '.join(filenames)}): {e}"
                        errors.append(msg)
                        for ref, _ in still_uncached:
                            group_analysis[str(ref.resolved_path)] = None
                        if on_error == "abort":
                            print(f"[ERROR] {msg}", file=sys.stderr)
                            return 1
        else:
            # Single-image path for each uncached image
            for ref in uncached_from_single:
                ctx = local_context(prd_text, ref.line_no) if ref.line_no > 0 else "[无局部上下文]"
                i_key = image_analysis_key(
                    image_path=ref.raw_path,
                    file_summary_text=summary,
                    model=model,
                    detail_level=detail_level,
                    custom_prompt=custom_prompt,
                )
                img_cache_path, _ = cache_paths(cache_dir, i_key, "image")
                heading = heading_chain_until_line(prd_text, ref.line_no)
                prompt_text = build_image_prompt(
                    detail_level=detail_level,
                    file_summary=summary,
                    heading_chain=heading,
                    local_ctx=ctx,
                    image_alt=ref.alt,
                    custom_prompt=custom_prompt,
                )
                if dry_run:
                    group_analysis[str(ref.resolved_path)] = "[dry-run] image analysis skipped."
                else:
                    try:
                        analysis_text = analyze_image(
                            image_path=ref.resolved_path,
                            prompt_text=prompt_text,
                            model=model,
                            timeout=timeout,
                            retry=retry,
                            on_error=on_error,
                        )
                        if analysis_text:
                            write_json(img_cache_path, {
                                "key": i_key,
                                "image_prompt_version": IMAGE_PROMPT_VERSION,
                                "model": model,
                                "detail_level": detail_level,
                                "created_at": now_iso(),
                                "image_path": str(ref.resolved_path),
                                "raw_path": str(ref.raw_path),
                                "analysis_text": analysis_text,
                            })
                        group_analysis[str(ref.resolved_path)] = analysis_text or ""
                    except Exception as e:  # pylint: disable=broad-except
                        msg = f"{ref.resolved_path.name} 解析失败: {e}"
                        errors.append(msg)
                        group_analysis[str(ref.resolved_path)] = None
                        if on_error == "abort":
                            print(f"[ERROR] {msg}", file=sys.stderr)
                            return 1

        # Assemble group outputs in original order
        for ref in valid_group:
            path_key = str(ref.resolved_path)
            analysis_text = group_analysis.get(path_key)
            if analysis_text is None:
                failed += 1
                continue
            _append_output(ref, analysis_text, include_image_snippet, image_outputs)
            success += 1

    mode = "single-image" if image_path else "full-prd"
    result = {
        "meta": {
            "prd_file": str(prd_file),
            "feature_name": feature_name,
            "generated_at": now_iso(),
            "model": model,
            "mode": mode,
        },
        "images": image_outputs,
        "summary": {
            "total": len(selected),
            "success": success,
            "failed": failed,
        },
        "errors": errors,
    }

    json_path = output_dir / f"{feature_name}-image-analysis.json"
    md_path = output_dir / f"{feature_name}-image-analysis.md"
    log_path = output_dir / f"{feature_name}-image-analysis-errors.log"

    if mode == "single-image" and image_outputs:
        print(image_outputs[0]["analysis_text"])

    if emit_json:
        write_json(json_path, result)
        if not embed:
            print(f"文件内图片解析完成，JSON结果文件在：{json_path}")
    if emit_md:
        md_text = build_md_report(
            meta=result["meta"],
            images=result["images"],
            errors=result["errors"],
            include_image_snippet=include_image_snippet,
        )
        md_path.write_text(md_text, encoding="utf-8")
        if not embed:
            print(f"文件内图片解析完成，结果文件在：{md_path}")
    if errors:
        log_path.write_text("\n".join(errors) + "\n", encoding="utf-8")
        print(f"ERROR: {log_path}")

    if embed and image_outputs:
        new_md_path = embed_descriptions_into_markdown(prd_file, image_outputs)
        print(f"[EMBED] 已将图片描述嵌入正文内，嵌入后的文件路径： {new_md_path}")
        return new_md_path
    return md_path


def main() -> int:
    args = parse_args()
    emit_md = args.emit_md
    emit_json = args.emit_json
    if not emit_json and not emit_md:
        emit_md = True
    try:
        parse_prd_images(
            prd_file=Path(args.prd_file),
            output_dir=Path(args.output_dir) if args.output_dir else None,
            image_path=args.image_path,
            model=args.model,
            max_images=args.max_images,
            detail_level=args.detail_level,
            retry=args.retry,
            on_error=args.on_error,
            timeout=args.timeout,
            dry_run=args.dry_run,
            include_image_snippet=args.include_image_snippet,
            emit_json=emit_json,
            emit_md=emit_md,
            force_refresh=args.force_refresh,
            embed=args.embed,
            batch_gap=args.batch_gap,
            max_batch_size=args.max_batch_size,
            no_batch=args.no_batch,
            custom_prompt=args.custom_prompt,
        )
        return 0
    except:
        return 1


if __name__ == "__main__":
    # sys.argv[1:] = [
    #     "--prd-file",
    #     # "/Users/zengzhihua/Documents/code/testing-wiki/huya-pc-web/prd/web-nav/web顶部栏tab异化图标支持配置.md",
    #     # r"E:\code\testing-wiki\buff\prd\【日麻AI助手】购买会员\【日麻AI助手】购买会员.md",
    #     r"E:\code\testing-wiki\buff\prd\集五卡·瓜分万元大奖\集五卡·瓜分万元大奖.md",
    #     "--embed",
    #     # "--image-path",
    #     # "images/1a62d0f8786853ccb5dd563ce6df63451b74a00ff8d6775a4afe4098ee388b4a.png"
    # ]
    sys.exit(main())
