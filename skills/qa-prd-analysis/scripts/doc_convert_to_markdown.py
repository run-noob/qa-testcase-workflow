"""
文档转 Markdown 工具，基于 mineru 服务。

将 PDF、DOCX、PPTX、XLSX、图片等格式文档转换为 Markdown。
"""

import asyncio
import os.path
import re
import sys
import zipfile
import shutil
import subprocess
from pathlib import Path
import httpx
try:
    from bs4 import BeautifulSoup
except:
    BeautifulSoup = None

DEFAULT_BASE_URL = "http://10.159.154.2:8005"
DEFAULT_POLL_INTERVAL = 2  # 轮询间隔（秒）
DEFAULT_MAX_WAIT = 120  # 异步模式最大等待时间（秒）


async def health_check() -> dict:
    """检测 mineru 服务健康状态。"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{DEFAULT_BASE_URL}/health")
        resp.raise_for_status()
        return resp.json()


def save_zip_file(file_path: Path, content: bytes) -> Path:
    zip_path = str(file_path).replace(file_path.suffix, ".zip")
    with open(zip_path, "wb") as f:
        f.write(content)
    return Path(zip_path)


def extract_zip(zip_path: Path) -> Path:
    """
    解压 zip 文件，读取其中的 markdown 内容。

    解压到原文件所在目录下的 {filename}_output/ 目录，
    返回主 markdown 文件的内容。
    """
    extract_dir = zip_path.parent
    print(f"[TO-MARKDOWN] 正在解压: {zip_path.name}")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)
    office_dir = extract_dir / zip_path.stem / "office"
    if not office_dir.exists():
        raise FileNotFoundError(f"解压后目录为空")
    for name in os.listdir(office_dir):
        # 判断目标路径是否存在，如果存在则删除（可能是之前解压失败残留的）
        target_path = extract_dir / name
        if target_path.exists():
            if target_path.is_file():
                target_path.unlink()
            else:
                shutil.rmtree(target_path)
        shutil.move(os.path.join(office_dir, name), extract_dir)
    shutil.rmtree(office_dir.parent)
    main_md = extract_dir / f"{zip_path.stem}.md"
    if not main_md.exists():
        raise FileNotFoundError(f"解压后未找到文件: {main_md}")
    # images_dir = extract_dir / "images"
    # print(f"Markdown文件解压到路径: {extract_dir}")
    # if images_dir.exists():
    #     print(f"Markdown文件内引用的图片目录：{images_dir}")
    # 格式化 markdown 中的 HTML 块，解决拥挤在一行的问题。
    # format_markdown_html(main_md)  # 弃用，可能会导致图片解析的上下文全部是html标签
    return main_md


def _find_html_blocks(content: str) -> list[tuple[int, int, str]]:
    """
    找到 markdown 内容中的顶级 HTML 块（table, ul, ol）。

    使用栈来正确处理嵌套标签，只返回最外层块。
    返回 [(start, end, tag_name), ...] 按 start 位置排序。
    """
    blocks: list[tuple[int, int, str]] = []

    for tag in ("table", "ul", "ol"):
        open_re = re.compile(r"<" + tag + r"\b[^>]*>", re.IGNORECASE)
        close_re = re.compile(r"</" + tag + r"\s*>", re.IGNORECASE)
        stack: list[int] = []
        pos = 0

        while pos < len(content):
            open_match = open_re.search(content, pos)
            close_match = close_re.search(content, pos)

            if not open_match and not close_match:
                break

            open_pos = open_match.start() if open_match else float("inf")
            close_pos = close_match.start() if close_match else float("inf")

            if open_pos < close_pos:
                stack.append(open_match.start())
                pos = open_match.end()
            else:
                if stack:
                    start_pos = stack.pop()
                    if not stack:
                        # 最外层闭合，记录这个块
                        blocks.append((start_pos, close_match.end(), tag))
                pos = close_match.end()

    # 按起始位置排序
    blocks.sort(key=lambda x: x[0])

    # 去除嵌套在其他块内部的块（如 table 内的 ul）
    top_level: list[tuple[int, int, str]] = []
    for i, (start, end, tag) in enumerate(blocks):
        is_nested = any(
            other_start < start and other_end > end
            for j, (other_start, other_end, _) in enumerate(blocks)
            if i != j
        )
        if not is_nested:
            top_level.append((start, end, tag))

    return top_level


def _format_html_block(html_str: str) -> str:
    """使用 BeautifulSoup 的 prettify() 格式化 HTML 块，添加换行和缩进。"""
    soup = BeautifulSoup(html_str, "html.parser")
    formatted = soup.prettify()
    return formatted.strip()


def format_markdown_html(md_path: Path) -> Path:
    """
    找到 markdown 文件中的 HTML 块（table/ul/ol），用 BeautifulSoup prettify()
    格式化使其可读，解决 mineru 输出挤在一行的问题。

    返回同一个 Path 对象，方便链式调用。
    """
    try:
        content = md_path.read_text(encoding="utf-8")
        blocks = _find_html_blocks(content)
        
        if not blocks:
            return md_path
        if BeautifulSoup is None:
            print("当前python环境未安装beautifulsoup4，无法格式化markdown内容里的html标签，安装：python -m pip install beautifulsoup4")
            return md_path
        # 从后往前替换，保证前面的位置不受影响
        for start, end, _tag in reversed(blocks):
            html_str = content[start:end]

            # 跳过已经是 prettify 格式的块（含至少 3 个换行的块说明已格式化过）
            if html_str.count("\n") >= 3:
                continue

            raw = _format_html_block(html_str)

            # 检查前后是否已有空行，避免重复添加
            prefix = "\n" if start > 0 and not content[start - 1:start] in ("\n", "") else ""
            suffix = "\n" if end < len(content) and not content[end:end + 1] in ("\n", "") else ""

            formatted = prefix + raw + suffix
            content = content[:start] + formatted + content[end:]

        md_path.write_text(content, encoding="utf-8")
        print("HTML 块格式化完成")
    except:
        pass
    return md_path


async def convert_sync(
    file_path: str | Path,
) -> Path:
    """
    同步模式：上传文件并等待转换结果。

    Returns:
        dict 包含 status, md_content, files 等字段
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    async with httpx.AsyncClient(timeout=DEFAULT_MAX_WAIT) as client:
        with open(file_path, "rb") as f:
            form_data = {
                "return_md": True,
                "response_format_zip": True,
                "return_original_file": False,
                "return_images": True
            }
            files = {"files": (file_path.name, f, "application/octet-stream")}
            resp = await client.post(
                f"{DEFAULT_BASE_URL}/file_parse",
                data=form_data,
                files=files,
            )
            resp.raise_for_status()
            return save_zip_file(file_path, resp.content)


async def submit_task(
    file_path: str | Path,
) -> str:
    """
    异步模式：提交转换任务，返回 task_id。
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        with open(file_path, "rb") as f:
            form_data = {"return_md": True, "response_format_zip": True,
                         "return_original_file": False, "return_images": True}
            files = {"files": (file_path.name, f, "application/octet-stream")}
            resp = await client.post(
                f"{DEFAULT_BASE_URL}/tasks",
                data=form_data,
                files=files,
            )
            resp.raise_for_status()
            result = resp.json()
            task_id = result.get("task_id")
            if not task_id:
                raise RuntimeError(f"提交任务失败，未返回 task_id: {result}")
            return task_id


async def get_task_status(task_id: str) -> dict:
    """查询异步任务状态。"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{DEFAULT_BASE_URL}/tasks/{task_id}")
        resp.raise_for_status()
        return resp.json()


async def get_task_result(task_id: str) -> bytes:
    """获取异步任务结果。"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{DEFAULT_BASE_URL}/tasks/{task_id}/result")
        resp.raise_for_status()
        return resp.content


async def convert_async(
    file_path: str | Path,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    max_wait: float = DEFAULT_MAX_WAIT,
) -> Path:
    """
    异步模式：提交任务，轮询等待完成，返回最终结果。

    Args:
        file_path: 输入文件路径
        poll_interval: 轮询间隔（秒）
        max_wait: 最大等待时间（秒）
    """
    task_id = await submit_task(file_path)
    elapsed = 0.0

    # 等待任务完成
    while elapsed < max_wait:
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

        status = await get_task_status(task_id)
        state = status.get("status")

        if state == "completed":
            content = await get_task_result(task_id)
            zip_path = save_zip_file(file_path, content)
            return zip_path
        if state == "failed":
            raise RuntimeError(
                f"转换任务失败 task_id={task_id}: {status.get('error', 'unknown error')}"
            )

        # state 可能为 "pending"、"processing"、"queued" 等
        queued = status.get("queued_ahead", 0)
        if queued > 0:
            print(f"  任务排队中，前方还有 {queued} 个任务...")

    raise TimeoutError(
        f"转换任务超时 task_id={task_id}，已等待 {max_wait}s"
    )


async def convert_to_markdown(
    file_path: str | Path,
    mode: str = "sync",
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    max_wait: float = DEFAULT_MAX_WAIT,
) -> Path:
    """
    将文档转换为 Markdown 文本。

    Args:
        file_path: 输入文件路径
        mode: "sync" 同步模式 或 "async" 异步模式
        poll_interval: 异步模式轮询间隔
        max_wait: 异步模式最大等待时间

    Returns:
        转换后的 zip 文件路径
    """
    file_path = Path(file_path)

    if mode == "sync":
        zip_path = await convert_sync(file_path)
        return zip_path
    elif mode == "async":
        zip_path = await convert_async(file_path, poll_interval, max_wait)
        return zip_path
    else:
        raise ValueError(f"不支持的模式: {mode}，可选 'sync' 或 'async'")


def convert_file(
    file_path: str | Path,
    mode: str = "sync",
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    max_wait: float = DEFAULT_MAX_WAIT,
) -> Path:
    """
    同步入口：将文件转换为 Markdown 文本，解压后返回内容。

    Args:
        file_path: 输入文件路径
        mode: 转换模式
        poll_interval: 轮循间隔
        max_wait: 最大等待时间

    Returns:
        转换后的 markdown 文本内容
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    print(f"开始文档转换: {file_path}")
    _zip_path = asyncio.run(
        convert_to_markdown(file_path, mode, poll_interval, max_wait)
    )
    print(f"服务端转换完成, 下载到本地的zip路径: {_zip_path}")
    return _zip_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="使用 mineru 服务将文档转换为 Markdown，输出在源文档所在目录下"
    )
    parser.add_argument(
        "file", type=str, help="输入文件路径（支持 PDF/DOCX/PPTX/XLSX/图片）"
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="sync",
        choices=["sync", "async"],
        help="转换模式: sync 同步 / async 异步（默认: sync）",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=DEFAULT_POLL_INTERVAL,
        help=f"异步模式轮询间隔秒数（默认: {DEFAULT_POLL_INTERVAL}）",
    )
    parser.add_argument(
        "--max-wait",
        type=float,
        default=DEFAULT_MAX_WAIT,
        help=f"异步模式最大等待秒数（默认: {DEFAULT_MAX_WAIT}）",
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="仅检查服务健康状态后退出",
    )
    parser.add_argument(
        "--parse-images",
        action="store_true",
        help="转换完成后自动调用 prd_image_parser.py 解析图片，并将描述嵌入生成的 Markdown 文件（需配置 OPENAI_API_KEY）",
    )

    args = parser.parse_args()

    if args.health:
        health_result = asyncio.run(health_check())
        print(health_result)
        sys.exit(0)

    zip_file = convert_file(
        file_path=args.file,
        mode=args.mode,
        poll_interval=args.poll_interval,
        max_wait=args.max_wait,
    )

    md_file = extract_zip(zip_file)
    if md_file.exists():
        print(f"文档转换成功！output：{md_file}")
        try:
            extract_dir = zip_file.parent
            # 将zip文件移动到extract_dir/raw目录下，保留原始文件
            raw_dir = extract_dir / "raw"
            raw_dir.mkdir(exist_ok=True)
            zip_file.rename(raw_dir / zip_file.name)
            # 将原始文件也移动到raw目录下
            ori_file_path = Path(args.file)
            ori_file_path.rename(raw_dir / ori_file_path.name)
            print(f"原始文件和转换中间产物zip文件已移动到: {raw_dir}")
        except:
            pass

        if args.parse_images:
            parser_script = Path(__file__).parent / "prd_image_parser.py"
            print(f"开始图片解析并嵌入 Markdown: {md_file}")
            result = subprocess.run(
                [sys.executable, str(parser_script), "--prd-file", str(md_file), "--embed"],
                capture_output=False,
            )
            if result.returncode != 0:
                print(f"[WARNING] 图片解析未完全成功（exit code {result.returncode}），Markdown 已生成，可手动运行 prd_image_parser.py --embed 重试")

