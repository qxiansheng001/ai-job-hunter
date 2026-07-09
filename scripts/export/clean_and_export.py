#!/usr/bin/env python3
"""
数据清洗与 Excel 导出
读取 raw_data.json，去重、格式统一、生成带样式的 .xlsx 文件。

用法:
  python clean_and_export.py --input raw_data.json --output jobs_clean.xlsx
"""

import json
import re
import sys
import os
import argparse
import tempfile
from datetime import datetime

try:
    import pandas as pd
except ImportError:
    print(json.dumps({"error": "缺少 pandas 库，请执行: pip install pandas", "step": "dep"}))
    sys.exit(1)

try:
    from openpyxl import load_workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    print(json.dumps({"error": "缺少 openpyxl 库，请执行: pip install openpyxl", "step": "dep"}))
    sys.exit(1)


def clean_data(raw_path, output_path):
    """主清洗流程"""
    # 读取原始数据
    with open(raw_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    items = raw.get("list_items", [])
    details = raw.get("detail_items", [])
    keyword = raw.get("keyword", "")
    city = raw.get("city", "")

    if not items:
        print(json.dumps({"step": "warn", "message": "没有数据可清洗"}))
        return False

    # 构建详情查找表：url → detail
    detail_map = {}
    for d in details:
        url = d.get("url", "")
        if url:
            detail_map[url] = d

    rows = []
    for item in items:
        link = item.get("link", "")
        detail = detail_map.get(link, {})

        # JD 文本：优先取详情页完整文本，取不到则从列表页拼接
        jd_text = detail.get("jd_text", "")
        if not jd_text:
            jd_text = "（未获取到详细 JD，列表页信息："
            tags = item.get("tags", [])
            if tags:
                jd_text += " | ".join(tags)
            jd_text += "）"

        rows.append({
            "岗位名称": item.get("title", ""),
            "公司名称": item.get("company", ""),
            "工作地点": item.get("location", ""),
            "JD摘要": jd_text,
            "岗位链接": link,
        })

    df = pd.DataFrame(rows)

    # 去重：同公司同岗位保留一条
    before = len(df)
    df = df.drop_duplicates(subset=["岗位名称", "公司名称"], keep="first")
    after = len(df)

    # 写入 Excel（带格式）
    df.to_excel(output_path, index=False, sheet_name="AI岗位数据",
                engine="openpyxl")

    # 格式化
    wb = load_workbook(output_path)
    ws = wb.active

    header_font = Font(name="微软雅黑", bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell_align = Alignment(vertical="top", wrap_text=True)
    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9"),
    )

    # 表头样式
    for col_idx, col_name in enumerate(df.columns, 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    # 数据区域样式
    for row_idx in range(2, ws.max_row + 1):
        for col_idx in range(1, ws.max_column + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.alignment = cell_align
            cell.border = thin_border

    # 列宽
    col_widths = {
        "岗位名称": 22,
        "公司名称": 28,
        "工作地点": 16,
        "JD摘要": 80,
        "岗位链接": 40,
    }
    for col_idx, col_name in enumerate(df.columns, 1):
        width = col_widths.get(col_name, 15)
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    # 冻结首行
    ws.freeze_panes = "A2"

    # 自动筛选
    ws.auto_filter.ref = f"A1:{get_column_letter(len(df.columns))}{ws.max_row}"

    wb.save(output_path)

    report = {
        "step": "done",
        "input_rows": before,
        "after_dedup": after,
        "output": output_path,
        "message": f"清洗完成：{before} 条 → 去重后 {after} 条 → 已导出 {output_path}",
    }
    print(json.dumps(report, ensure_ascii=False))
    print(f"\n📊 数据概览:", file=sys.stderr)
    print(f"  原始条数: {before}", file=sys.stderr)
    print(f"  去重后:   {after}", file=sys.stderr)
    print(f"  输出文件: {output_path}", file=sys.stderr)
    return True


def main():
    parser = argparse.ArgumentParser(description="数据清洗与 Excel 导出")
    default_input = os.path.join(tempfile.gettempdir(), "ai-job-hunter", "raw_data.json")
    parser.add_argument("--input", default=default_input, help="输入 raw_data.json 路径")
    parser.add_argument("--output", default="jobs_clean.xlsx", help="输出 .xlsx 路径")
    args = parser.parse_args()

    clean_data(args.input, args.output)

    # 清理中间文件
    temp_dir = os.path.join(tempfile.gettempdir(), "ai-job-hunter")
    if os.path.exists(temp_dir):
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
