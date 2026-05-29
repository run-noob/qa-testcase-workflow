"""
文档转 Markdown 工具，基于 mineru 服务。

将 PDF、DOCX、PPTX、XLSX、图片等格式文档转换为 Markdown。
"""

import asyncio
import os.path
import sys
import zipfile
import shutil
from pathlib import Path
import httpx
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
    print(f"正在解压结果: {zip_path.name}")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)
    office_dir = extract_dir / zip_path.stem / "office"
    if not office_dir.exists():
        raise FileNotFoundError(f"解压后目录为空")
    for name in os.listdir(office_dir):
        shutil.move(os.path.join(office_dir, name), extract_dir)
    shutil.rmtree(office_dir.parent)
    main_md = extract_dir / f"{zip_path.stem}.md"
    if not main_md.exists():
        raise FileNotFoundError(f"解压后未找到文件: {main_md}")
    images_dir = extract_dir / "images"
    print(f"Markdown文件解压到路径: {extract_dir}")
    if images_dir.exists():
        print(f"Markdown文件内引用的图片目录：{images_dir}")
    print(f"文档转换成功！output：{main_md}")
    return main_md


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

    extract_zip(zip_file)

