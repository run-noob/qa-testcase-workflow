"""Convert completed Markdown test cases into a standard XMind workbook."""

import argparse
import json
import logging
import uuid
import re
import zipfile
from pathlib import Path

from markdown_case_parser import list_completed_case_files, parse_test_cases_from_markdown

logger = logging.getLogger(__name__)

def _topic(
    title: str,
    *,
    children: list[dict] | None = None,
    style_id: str | None = None,
    folded: bool = False,
) -> dict:
    result = {"id": str(uuid.uuid4()), "title": title}
    if children:
        result["children"] = {"attached": children}
        if folded:
            result["branch"] = "folded"
    if style_id:
        result["style"] = {"id": style_id}
    return result


def _lines(value: str) -> list[str]:
    return [line.strip() for line in (value or "").splitlines() if line.strip()]


def _numbered_lines(value: str) -> str:
    lines = _lines(value)
    # XMind renders CRLF more consistently than LF inside a single topic.
    return "\r\n".join(
        line if re.match(r"^\d+[.)]\s*", line) else f"{index}. {line}"
        for index, line in enumerate(lines, 1)
    )


def _case_topic(case: dict) -> dict:
    # Keep the case title as the first branch and make priority part of it.
    title = f"{case['priority']} {case['name']}".strip()
    steps = case.get("steps") or ""
    expected = case.get("expected") or ""

    expected_topic = _topic(
        "预期结果：\r\n" + _numbered_lines(expected),
        style_id="case-detail",
    ) if _lines(expected) else None
    steps_topic = _topic(
        "测试步骤：\r\n" + _numbered_lines(steps),
        children=[expected_topic] if expected_topic else None,
        style_id="case-detail",
    ) if _lines(steps) else expected_topic
    precondition_topic = _topic(
        f"前置条件：{(case['precondition'] or '无').strip()}",
        children=[steps_topic] if steps_topic else None,
        style_id="case-detail",
    )
    return _topic(
        title,
        children=[precondition_topic],
        style_id="case-title",
        folded=True,
    )


def convert_markdown_cases_to_xmind(input_dir: str, output_path: str) -> str:
    """Convert completed cases listed in ``_progress.md`` to ``.xmind``."""
    input_path = Path(input_dir).resolve()
    if not input_path.is_dir():
        raise ValueError(f"输入路径不是有效的目录: {input_dir}")

    module_topics = []
    global_index = 1
    for md_file in list_completed_case_files(input_path):
        relative = md_file.relative_to(input_path)
        module_parts = list(relative.parent.parts) + [relative.stem]
        module = "-".join(module_parts) if module_parts else relative.stem
        module = module.replace("测试用例", "").replace("用例", "").strip("-")
        result = parse_test_cases_from_markdown(md_file.read_text(encoding="utf-8"), start_index=global_index)
        cases = result["test_cases"]
        global_index += len(cases)
        if cases:
            module_topics.append(_topic(module, children=[_case_topic(case) for case in cases]))

    if not module_topics:
        raise ValueError("已完成的 Markdown 用例中没有解析到有效用例")

    root_children = module_topics
    root = _topic(input_path.name, children=root_children)
    content = [{"id": str(uuid.uuid4()), "class": "sheet", "title": input_path.name, "rootTopic": root}]
    manifest = {"file-entries": {"content.json": {}, "metadata.json": {}, "styles.json": {}, "manifest.json": {}}}
    metadata = {"creator": "qa-testcase-workflow", "title": input_path.name}
    styles = [
        {"id": "case-title", "type": "topic", "properties": {"fo:font-weight": "bold", "fo:font-size": "16pt"}},
        {"id": "case-detail", "type": "topic", "properties": {"svg:width": "520px", "fo:font-size": "13pt", "fo:line-spacing": "1.25", "fo:wrap-option": "wrap"}},
    ]

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as workbook:
        workbook.writestr("content.json", json.dumps(content, ensure_ascii=False, indent=2))
        workbook.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        workbook.writestr("metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2))
        workbook.writestr("styles.json", json.dumps(styles, ensure_ascii=False, indent=2))
    logger.info("XMind 文件已保存: %s，共 %d 个模块", target, len(module_topics))
    return str(target)


def main():
    parser = argparse.ArgumentParser(description="将 _progress.md 清单中的已完成 Markdown 测试用例转换为 XMind 文件")
    parser.add_argument("input_dir", help="包含 _progress.md 和 Markdown 用例文件的目录路径")
    parser.add_argument("-o", "--output", default=None, help="输出的 XMind 文件路径（默认在输入目录下生成 testcases.xmind）")
    args = parser.parse_args()
    result = convert_markdown_cases_to_xmind(args.input_dir, args.output or str(Path(args.input_dir) / "testcases.xmind"))
    print(f"转换完成! output path: {result}")


if __name__ == "__main__":
    main()
