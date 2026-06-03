import re
import logging
from pathlib import Path

try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
except:
    raise EnvironmentError("当前python环境尚未安装openpyxl，请先执行python -m pip install openpyxl")


logger = logging.getLogger()


def _replace_br(text):
    text = text.replace(r'<br>', ' ')
    return re.sub(r"\n\s*", "\n", text, re.DOTALL)


def parse_test_cases_from_markdown(md_text: str, start_index: int = 1) -> dict:
    """从 Markdown 文本中解析测试用例和知识信息

    Args:
        md_text: Markdown 文本内容。
        start_index: 自动生成 ID 时的起始序号，用于跨文件全局递增。
    """
    knowledge = ""
    test_cases = []

    # 提取知识库信息
    # 匹配 # 知识库信息 之后直到下一个大标题或分割线的内容
    knowledge_match = re.search(r'# 测试概述\s*\n(.*?)(?=\n---|\n##|\n# |$)', md_text, re.DOTALL)
    if knowledge_match:
        knowledge = knowledge_match.group(1).strip()

    # 类型映射
    type_mapping = {
        "功能": "functional",
        "边界": "boundary",
        "异常": "error",
        "安全": "security",
        "functional": "functional",
        "boundary": "boundary",
        "error": "error",
        "security": "security"
    }

    # 提取测试用例,可能格式：
    #    ## [MODULE-001] [P1] [功能] Name
    #    ## [P1] [功能][MODULE-001]Name
    #    ## [P1] [功能] MODULE-001Name
    #    ### ADMIN-PANEL-ID\n**[边界][P2]Name**
    segments = re.split(r'\n(?=#{2,}\s)', md_text)

    for seg in segments:
        # 匹配标题区域：从 ##/### 到 **前置条件** 之前（可能多行）
        header_match = re.search(r'(#{2,}\s.*?)(?=\n- \*\*前置条件\*\*)', seg, re.DOTALL)
        if not header_match:
            continue
        header_text = header_match.group(1)
        # 提取整个标题区域中所有方括号中的内容
        tokens = re.findall(r'\[(.*?)\]', header_text)
        tc_priority = None
        tc_type = None
        # 优先级正则 P0-P3
        priority_pattern = r'^P[0-3]$'

        for token in tokens:
            token_strip = token.strip().lstrip("[").rstrip("]")
            if re.match(priority_pattern, token_strip, re.I):
                tc_priority = token_strip.upper()
            elif token_strip.lower() in type_mapping:
                tc_type = type_mapping[token_strip.lower()]
            elif any(k in token_strip for k in type_mapping):
                # 处理带有"测试"后缀的情况，如"功能测试"
                for k, v in type_mapping.items():
                    if k in token_strip:
                        tc_type = v
                        break

        def find_id(text):
            match = re.search(r'[A-Za-z]+(?:-[A-Za-z]+)*-\d+', text)
            if match:
                return match.group(0)
            return None

        tc_id = find_id(header_text)
        if not tc_id:
            tc_id = f"TC_{(start_index + len(test_cases)):0>3}"

        # 从整个标题区域提取用例名称：去掉 ##/### 标记、方括号内容、加粗标记
        name_text = re.sub(r'#{2,}\s*', '', header_text)
        name_text = re.sub(r'\[.*?\]', '', name_text)
        name_text = re.sub(r'\*\*', '', name_text).strip()
        # 按行分割，过滤空行和纯 ID 行（大写+数字+连字符，无中文字符）
        name_lines = []
        for line in name_text.split('\n'):
            line = line.strip()
            if not line:
                continue
            if re.match(r'^[A-Z][A-Z0-9_-]*$', line) and not re.search(r'[一-鿿]', line):
                continue
            name_lines.append(line)
        tc_name = ' '.join(name_lines).strip(" #:")

        tc = {
            "id": tc_id,
            "name": tc_name,
            "priority": tc_priority or "P1",
            "type": tc_type or "functional",
            "precondition": "",
            "steps": "",
            "expected": "",
            "test_data": "",
            "remark": "",
            "case_knowledge": knowledge
        }

        # 提取各个字段
        def get_field(pattern, text, default=None):
            m = re.search(pattern, text,  re.MULTILINE | re.DOTALL)
            return _replace_br(m.group(1).strip("*- ")) if m else default

        # 如果 body 中有明确定义的字段，则覆盖 header 中的
        body_priority = get_field(r'\*\*优先级\*\*[:：]\s*(.*)', seg)
        if body_priority:
            tc["priority"] = body_priority

        body_type = get_field(r'\*\*类型\*\*[:：]\s*(.*)', seg)
        if body_type:
            # 同样对 body 中的类型进行映射
            body_type_lower = body_type.lower()
            if body_type_lower in type_mapping:
                tc["type"] = type_mapping[body_type_lower]
            else:
                for k, v in type_mapping.items():
                    if k in body_type_lower:
                        tc["type"] = v
                        break

        tc["precondition"] = get_field(r'\*\*前置条件\*\*[:：]\s*(.*?)(?=测试步骤)', seg, "")
        tc["test_data"] = get_field(r'\*\*测试数据\*\*[:：]\s*(.*?)(?=备注)', seg, "")
        tc["remark"] = get_field(r'\*\*备注\*\*[:：]\s*(.*?)(?=---|#|\Z)', seg, "")

        # 提取步骤 (多行)
        steps_match = re.search(r'\*\*测试步骤\*\*[:：]\s*(.*?)(?=\n\*\*|\n---|\n##|$)', seg, re.DOTALL)
        if steps_match:
            steps_content = steps_match.group(1).strip()

            # 检查是否包含 Markdown 表格结构
            if '|' in steps_content and '---' in steps_content:
                table_lines = [line.strip() for line in steps_content.split('\n') if line.strip()]
                steps_list = []
                expected_list = []

                for line in table_lines:
                    if re.match(r'^[|\s:-]+$', line):
                        continue
                    if re.search(r'步骤|step|操作|operation|预期|expected', line, re.I):
                        if line == table_lines[0]:
                            continue

                    cols = [c.strip() for c in line.strip('|').split('|')]
                    if len(cols) >= 2:
                        step_num = cols[0]
                        action = cols[1]
                        expected = cols[2] if len(cols) >= 3 else ""

                        prefix = f"{step_num}. " if step_num and not step_num.endswith('.') else f"{step_num} "
                        if not step_num: prefix = ""

                        steps_list.append(f"{action}")
                        if expected:
                            expected_list.append(f"{expected}")

                tc["steps"] = _replace_br("\n".join(steps_list))
                tc["expected"] = _replace_br("\n".join(expected_list))
            else:
                tc["steps"] = _replace_br(steps_content)
                expected_match = re.search(r'\*\*预期结果\*\*[:：]\s*(.*?)(?=\n\*\*|\n---|\n##|$)', seg, re.DOTALL)
                if expected_match:
                    tc["expected"] = _replace_br(expected_match.group(1).strip())
            test_cases.append(tc)
        else:
            if len(test_cases) > 0:
                logger.warning(f"未找到测试步骤标题: {header_text}")

    return {"test_cases": test_cases, "knowledge": knowledge}


def convert_markdown_cases_to_excel(input_dir: str, output_path: str) -> str:
    """将目录中的所有 Markdown 用例文件转换为 Excel 文件。

    Args:
        input_dir: 包含 Markdown 用例文件的目录路径。
        output_path: 输出的 Excel 文件路径（.xlsx）。

    Returns:
        生成的 Excel 文件路径。
    """
    input_path = Path(input_dir)
    if not input_path.is_dir():
        raise ValueError(f"输入路径不是有效的目录: {input_dir}")

    md_files = sorted(input_path.glob("*/*.md"))
    if not md_files:
        raise ValueError(f"目录中没有找到 .md 文件: {input_dir}")

    wb = Workbook()
    ws = wb.active
    ws.title = "测试用例"

    TYPE_LABELS = {
        "functional": "功能",
        "boundary": "边界",
        "error": "异常",
        "security": "安全",
    }

    headers = ["ID", "模块", "优先级", "类型", "标题", "前置条件", "步骤", "预期", "测试数据", "备注"]
    header_font = Font(bold=True, size=11)
    header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    wrap_alignment = Alignment(wrap_text=True, vertical="top")

    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    row = 2
    global_index = 1
    module_ranges: dict[str, list[int]] = {}

    for md_file in md_files:
        relative = md_file.relative_to(input_path)
        parts = list(relative.parent.parts) + [relative.stem]
        module = "-".join(parts) if parts else relative.stem
        module = module.replace("测试用例", "").replace("用例", "").strip("-")

        try:
            content = md_file.read_text(encoding="utf-8")
            result = parse_test_cases_from_markdown(content, start_index=global_index)
            test_cases = result.get("test_cases", [])
            global_index += len(test_cases)
        except Exception as e:
            logger.warning(f"解析文件失败: {md_file}, 错误: {e}")
            continue

        for tc in test_cases:
            tc_type = TYPE_LABELS.get(tc.get("type", ""), tc.get("type", ""))
            ws.cell(row=row, column=1, value=tc.get("id", ""))
            ws.cell(row=row, column=2, value=module)
            ws.cell(row=row, column=3, value=tc.get("priority", ""))
            ws.cell(row=row, column=4, value=tc_type)
            ws.cell(row=row, column=5, value=tc.get("name", ""))
            ws.cell(row=row, column=6, value=tc.get("precondition", ""))
            ws.cell(row=row, column=7, value=tc.get("steps", ""))
            ws.cell(row=row, column=8, value=tc.get("expected", ""))
            ws.cell(row=row, column=9, value=tc.get("test_data", ""))
            ws.cell(row=row, column=10, value=tc.get("remark", ""))

            if module not in module_ranges:
                module_ranges[module] = [row, row]
            else:
                module_ranges[module][1] = row

            row += 1

    # 合并相同模块的单元格
    merge_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for start_row, end_row in module_ranges.values():
        if end_row > start_row:
            ws.merge_cells(start_row=start_row, start_column=2, end_row=end_row, end_column=2)
            ws.cell(row=start_row, column=2).alignment = merge_center

    for col_idx in range(1, len(headers) + 1):
        ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = \
            [14, 22, 8, 8, 30, 30, 50, 50, 18, 22][col_idx - 1]

    for r in range(2, row):
        for c in range(1, len(headers) + 1):
            ws.cell(row=r, column=c).alignment = wrap_alignment

    last_col = chr(64 + len(headers))
    ws.auto_filter.ref = f"A1:{last_col}{row - 1}"
    ws.freeze_panes = "A2"

    wb.save(output_path)
    logger.info(f"Excel 文件已保存: {output_path}，共 {row - 2} 条用例")
    return output_path


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="将目录中的 Markdown 测试用例文件转换为 Excel 文件"
    )
    parser.add_argument(
        "input_dir",
        help="包含 Markdown 用例文件的目录路径",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="输出的 Excel 文件路径（默认在输入目录下生成 testcases.xlsx）",
    )
    args = parser.parse_args()

    input_dir = args.input_dir
    output_path = args.output or str(Path(input_dir) / "testcases.xlsx")

    try:
        result = convert_markdown_cases_to_excel(input_dir, output_path)
        print(f"转换完成! output path: {result}")
    except Exception as e:
        logger.error(f"转换失败: {e}")
        raise


if __name__ == "__main__":
    main()
