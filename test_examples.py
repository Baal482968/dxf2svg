#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
將 assets 資料夾中的 DXF，將首尾相連的 LINE 合併分群，並與 POLYLINE/LWPOLYLINE 一起輸出 SVG
"""

import os
from main import RebarDXFToSVG
from collections import defaultdict, deque

def find_dxf_files(root_dir):
    """遞迴搜尋所有 DXF 檔案"""
    dxf_files = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.dxf'):
                dxf_files.append(os.path.join(root, file))
    return dxf_files

def point_key(pt, tol=1e-4):
    """將點座標轉為可比較的 key（含容差）"""
    return (round(pt[0]/tol)*tol, round(pt[1]/tol)*tol)

def group_lines_and_polylines(entities, tol=1e-4):
    """
    將所有 LINE 依首尾相連自動分群，POLYLINE/LWPOLYLINE 各自為一群
    回傳: List[List[entity]]
    """
    # 先處理 POLYLINE/LWPOLYLINE
    groups = []
    used = set()
    for idx, entity in enumerate(entities):
        if entity['type'] in ('POLYLINE', 'LWPOLYLINE'):
            groups.append([entity])
            used.add(idx)
    # 對 LINE 進行分群
    # 建立端點到 index 的對應
    point_to_lines = defaultdict(list)
    for idx, entity in enumerate(entities):
        if entity['type'] == 'LINE' and idx not in used:
            start = point_key(entity['start'], tol)
            end = point_key(entity['end'], tol)
            point_to_lines[start].append(idx)
            point_to_lines[end].append(idx)
    # BFS 分群
    visited = set()
    for idx, entity in enumerate(entities):
        if entity['type'] != 'LINE' or idx in used or idx in visited:
            continue
        group = []
        queue = deque([idx])
        while queue:
            cur = queue.popleft()
            if cur in visited:
                continue
            visited.add(cur)
            group.append(entities[cur])
            # 找到與當前線段首尾相連的其他線段
            for pt in [point_key(entities[cur]['start'], tol), point_key(entities[cur]['end'], tol)]:
                for neighbor in point_to_lines[pt]:
                    if neighbor != cur and neighbor not in visited:
                        queue.append(neighbor)
        if group:
            groups.append(group)
    return groups

def test_dxf_entities():
    converter = RebarDXFToSVG()
    assets_dir = "assets"
    if not os.path.exists(assets_dir):
        print(f"錯誤：找不到 {assets_dir} 資料夾")
        return
    dxf_files = find_dxf_files(assets_dir)
    if not dxf_files:
        print(f"在 {assets_dir} 資料夾中找不到 DXF 檔案")
        return
    print(f"找到 {len(dxf_files)} 個 DXF 檔案：")
    for file in dxf_files:
        print(f"  - {file}")
    print("\n開始自動分群並轉換...")
    for dxf_path in dxf_files:
        base_name = os.path.splitext(os.path.basename(dxf_path))[0]
        output_dir = os.path.dirname(dxf_path)
        print(f"\n正在處理: {os.path.basename(dxf_path)}")
        print(f"檔案路徑: {dxf_path}")
        try:
            doc = converter.load_dxf(dxf_path)
            if not doc:
                print(f"❌ 載入失敗: {os.path.basename(dxf_path)}")
                continue
            entities = converter.extract_rebar_lines(doc, layer_name="1號線")
            if not entities:
                print(f"❌ 找不到線條實體: {os.path.basename(dxf_path)}")
                continue
            # 自動分群
            groups = group_lines_and_polylines(entities)
            print(f"  共分群 {len(groups)} 組（自動合併首尾相連的 LINE）")
            for idx, group in enumerate(groups, 1):
                normalized = converter.normalize_coordinates(group)
                rebar_type = converter.identify_rebar_type(normalized)
                path_data = converter.entities_to_svg_paths(normalized)
                text_positions = converter.get_text_positions(rebar_type, normalized)
                svg_element = converter.create_svg(path_data, rebar_type, text_positions)
                from xml.etree.ElementTree import tostring
                from xml.dom.minidom import parseString
                rough_string = tostring(svg_element, 'unicode')
                pretty_svg = parseString(rough_string).toprettyxml(indent="  ")
                pretty_svg = '\n'.join(pretty_svg.split('\n')[1:])
                output_name = f"{base_name}_group{idx}.svg"
                output_path = os.path.join(output_dir, output_name)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(pretty_svg)
                print(f"    ✅ 輸出: {output_name}")
        except Exception as e:
            print(f"❌ 處理 {os.path.basename(dxf_path)} 時發生錯誤: {e}")
    print(f"\n全部完成！請檢查各資料夾中的 SVG 檔案。")

if __name__ == "__main__":
    test_dxf_entities() 