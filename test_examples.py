#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試 assets 資料夾中的 DXF 檔案
"""

import os
from main import RebarDXFToSVG

def test_dxf_files():
    """測試 assets 資料夾中的 DXF 檔案"""
    converter = RebarDXFToSVG()
    
    # 檢查 assets 資料夾
    assets_dir = "assets"
    if not os.path.exists(assets_dir):
        print(f"錯誤：找不到 {assets_dir} 資料夾")
        return
    
    # 取得所有 DXF 檔案
    dxf_files = [f for f in os.listdir(assets_dir) if f.endswith('.dxf')]
    
    if not dxf_files:
        print(f"在 {assets_dir} 資料夾中找不到 DXF 檔案")
        return
    
    print(f"找到 {len(dxf_files)} 個 DXF 檔案：")
    for file in dxf_files:
        print(f"  - {file}")
    
    print("\n開始測試轉換...")
    
    # 測試每個檔案
    for dxf_file in dxf_files:
        dxf_path = os.path.join(assets_dir, dxf_file)
        output_name = f"output_{os.path.splitext(dxf_file)[0]}.svg"
        output_path = os.path.join(assets_dir, output_name)
        
        print(f"\n正在處理: {dxf_file}")
        print(f"輸出檔案: {output_name}")
        
        try:
            # 嘗試轉換
            result = converter.convert_dxf_to_svg_template(
                dxf_path=dxf_path,
                output_path=output_path,
                layer_name="1號線"
            )
            
            if result:
                print(f"✅ 轉換成功！")
                print(f"   鋼筋類型: {result['rebar_type']}")
                print(f"   文字位置: {result['text_positions']}")
            else:
                print(f"❌ 轉換失敗")
                
        except Exception as e:
            print(f"❌ 處理 {dxf_file} 時發生錯誤: {e}")
    
    print(f"\n測試完成！請檢查 {assets_dir} 資料夾中的輸出檔案。")

if __name__ == "__main__":
    test_dxf_files() 