"""Shared Markdown test-case discovery and parsing helpers."""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def list_completed_case_files(input_path: Path) -> list[Path]:
    """Read the canonical case file list from _progress.md."""
    progress_path = input_path / "_progress.md"
    if not progress_path.is_file():
        raise ValueError(f"缺少用例文件清单: {progress_path}")

    rows = []
    for raw_line in progress_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not (line.startswith("|") and line.endswith("|")):
            continue
        columns = [column.strip() for column in line.strip("|").split("|")]
        if len(columns) < 4 or columns[0] in {"序号", "---"}:
            continue
        if all(set(column) <= {"-", ":", " "} for column in columns):
            continue
        rows.append(columns)

    completed_files = []
    seen = set()
    root = input_path.resolve()
    for columns in rows:
        relative_name = columns[2].strip().strip('`')
        status = columns[3].strip().strip("`")
        if status != "已完成":
            continue
        case_path = (input_path / relative_name).resolve()
        if case_path.parent != root and root not in case_path.parents:
            raise ValueError(f"用例清单包含越界路径: {relative_name}")
        if case_path.suffix.lower() != ".md":
            raise ValueError(f"用例清单仅支持 Markdown 文件: {relative_name}")
        if case_path in seen:
            raise ValueError(f"用例清单包含重复文件: {relative_name}")
        if not case_path.is_file():
            raise ValueError(f"用例清单中的文件不存在: {relative_name}")
        seen.add(case_path)
        completed_files.append(case_path)

    if not completed_files:
        raise ValueError(f"用例清单中没有状态为“已完成”的文件: {progress_path}")
    return completed_files


def _replace_br(text):
    text = text.replace(r'<br>', ' ')
    return re.sub(r"\n\s*", "\n", text, re.DOTALL)


def parse_test_cases_from_markdown(md_text: str, start_index: int = 1) -> dict:
    """Parse the Markdown case format used by qa-testcase-generation."""
    knowledge = ""
    test_cases = []
    knowledge_match = re.search(r'# 测试概述\s*\n(.*?)(?=\n---|\n##|\n# |$)', md_text, re.DOTALL)
    if knowledge_match:
        knowledge = knowledge_match.group(1).strip()

    type_mapping = {"正常": "functional", "功能": "functional", "边界": "boundary", "异常": "error", "安全": "security", "functional": "functional", "boundary": "boundary", "error": "error", "security": "security"}
    segments = re.split(r'\n(?=#{2,}\s)', md_text)
    for seg in segments:
        title_match = re.match(r'#{2,}\s+([^\n]+)', seg)
        if not title_match or not re.search(r'\*\*前置条件\*\*[:：]', seg):
            continue
        tc_name = re.sub(r'\*\*', '', title_match.group(1)).strip(" #:")

        def find_id(text):
            match = re.search(r'[A-Za-z_]+(?:[_-][A-Za-z_]+)*[_-]\d+', text)
            return match.group(0) if match else None

        case_id_match = re.search(r'\*\*用例编号\*\*[:：][^\S\n]*([^\n]+)', seg)
        if case_id_match and case_id_match.group(1).strip():
            tc_id = case_id_match.group(1).strip()
        else:
            tc_id = find_id(tc_name)
            if tc_id:
                tc_name = re.sub(r'\s*' + re.escape(tc_id) + r'\s*', '', tc_name).strip()
            else:
                tc_id = f"TC_{(start_index + len(test_cases)):0>3}"

        tc = {"id": tc_id, "name": tc_name, "priority": "P1", "type": "functional", "precondition": "", "steps": "", "expected": "", "test_data": "", "remark": "", "case_knowledge": knowledge}

        def get_field(pattern, text, default=None, multiline=False):
            flags = re.MULTILINE | re.DOTALL if multiline else 0
            m = re.search(pattern, text, flags)
            return _replace_br(m.group(1).strip("*- ")) if m else default

        body_priority = get_field(r'\*\*优先级\*\*[:：]\s*([^\n]*)', seg)
        if body_priority:
            tc["priority"] = body_priority.upper()
        body_type = get_field(r'\*\*用例类型\*\*[:：]\s*([^\n]*)', seg)
        if body_type:
            body_type_lower = body_type.replace("测试", "").lower()
            tc["type"] = type_mapping.get(body_type_lower, next((v for k, v in type_mapping.items() if k in body_type_lower), tc["type"]))
        tc["precondition"] = get_field(r'\*\*前置条件\*\*[:：]\s*(.*?)(?=测试步骤)', seg, "", True)
        tc["test_data"] = get_field(r'\*\*测试数据\*\*[:：]\s*(.*?)(?=备注)', seg, "", True)
        tc["remark"] = get_field(r'\*\*备注\*\*[:：]\s*(.*?)(?=---|#|\Z)', seg, "", True)
        steps_match = re.search(r'\*\*测试步骤\*\*[:：]\s*(.*?)(?=\n\*\*|\n---|\n##|$)', seg, re.DOTALL)
        if not steps_match:
            if test_cases:
                logger.warning("未找到测试步骤标题: %s", tc_name)
            continue
        steps_content = steps_match.group(1).strip()
        if '|' in steps_content and '---' in steps_content:
            steps_list, expected_list = [], []
            for line in [line.strip() for line in steps_content.split('\n') if line.strip()]:
                if re.match(r'^[|\s:-]+$', line) or re.search(r'步骤|step|操作|operation|预期|expected', line, re.I) and not steps_list:
                    continue
                cols = [c.strip() for c in line.strip('|').split('|')]
                if len(cols) >= 2:
                    steps_list.append(cols[1])
                    if len(cols) >= 3 and cols[2]:
                        expected_list.append(cols[2])
            tc["steps"] = _replace_br("\n".join(steps_list))
            tc["expected"] = _replace_br("\n".join(expected_list))
        else:
            tc["steps"] = get_field(r'\*\*测试步骤\*\*[:：]\s*(.*?)(?=预期结果)', _replace_br(seg), steps_content, True)
            tc["expected"] = get_field(r'\*\*预期结果\*\*[:：]\s*(.*?)(?=测试数据)', _replace_br(seg), "", True) or ""
        test_cases.append(tc)
    return {"test_cases": test_cases, "knowledge": knowledge}
