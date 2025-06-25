#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鋼筋 DXF 轉 SVG 轉換器
從 DXF 檔案中提取鋼筋形狀並轉換為標準化 SVG 模板
"""

import ezdxf
import math
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

# GUI 相關 import
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import threading

class RebarDXFToSVG:
    def __init__(self):
        self.svg_width = 200
        self.svg_height = 100
        self.stroke_width = 2
        self.stroke_color = "#2c3e50"
        
    def load_dxf(self, dxf_path):
        """載入 DXF 檔案"""
        try:
            doc = ezdxf.readfile(dxf_path)
            return doc
        except Exception as e:
            print(f"載入 DXF 檔案失敗: {e}")
            return None
    
    def extract_rebar_lines(self, doc, layer_name="1號線"):
        """從指定圖層提取鋼筋線條"""
        msp = doc.modelspace()
        rebar_entities = []
        
        for entity in msp:
            if entity.dxf.layer == layer_name:
                if entity.dxftype() == 'LINE':
                    rebar_entities.append({
                        'type': 'LINE',
                        'start': (entity.dxf.start.x, entity.dxf.start.y),
                        'end': (entity.dxf.end.x, entity.dxf.end.y)
                    })
                elif entity.dxftype() == 'LWPOLYLINE':
                    points = [(point[0], point[1]) for point in entity.get_points()]
                    rebar_entities.append({
                        'type': 'LWPOLYLINE', 
                        'points': points,
                        'closed': entity.closed
                    })
                elif entity.dxftype() == 'POLYLINE':
                    points = [(vertex.dxf.location.x, vertex.dxf.location.y) 
                             for vertex in entity.vertices]
                    rebar_entities.append({
                        'type': 'POLYLINE',
                        'points': points,
                        'closed': entity.closed
                    })
        
        return rebar_entities
    
    def get_bounding_box(self, entities):
        """計算所有實體的邊界框"""
        if not entities:
            return 0, 0, 100, 100
            
        x_coords = []
        y_coords = []
        
        for entity in entities:
            if entity['type'] == 'LINE':
                x_coords.extend([entity['start'][0], entity['end'][0]])
                y_coords.extend([entity['start'][1], entity['end'][1]])
            else:  # POLYLINE 或 LWPOLYLINE
                for point in entity['points']:
                    x_coords.append(point[0])
                    y_coords.append(point[1])
        
        return min(x_coords), min(y_coords), max(x_coords), max(y_coords)
    
    def normalize_coordinates(self, entities, target_width=200, target_height=100, margin=20):
        """將座標標準化到目標尺寸"""
        min_x, min_y, max_x, max_y = self.get_bounding_box(entities)
        
        # 計算原始尺寸
        orig_width = max_x - min_x
        orig_height = max_y - min_y
        
        # 計算縮放比例（保持長寬比）
        available_width = target_width - 2 * margin
        available_height = target_height - 2 * margin
        
        scale_x = available_width / orig_width if orig_width > 0 else 1
        scale_y = available_height / orig_height if orig_height > 0 else 1
        scale = min(scale_x, scale_y)
        
        # 計算偏移量（置中）
        scaled_width = orig_width * scale
        scaled_height = orig_height * scale
        offset_x = margin + (available_width - scaled_width) / 2
        offset_y = margin + (available_height - scaled_height) / 2
        
        # 轉換所有實體的座標
        normalized_entities = []
        for entity in entities:
            if entity['type'] == 'LINE':
                new_start = (
                    (entity['start'][0] - min_x) * scale + offset_x,
                    target_height - ((entity['start'][1] - min_y) * scale + offset_y)  # Y軸翻轉
                )
                new_end = (
                    (entity['end'][0] - min_x) * scale + offset_x,
                    target_height - ((entity['end'][1] - min_y) * scale + offset_y)
                )
                normalized_entities.append({
                    'type': 'LINE',
                    'start': new_start,
                    'end': new_end
                })
            else:  # POLYLINE
                new_points = []
                for point in entity['points']:
                    new_point = (
                        (point[0] - min_x) * scale + offset_x,
                        target_height - ((point[1] - min_y) * scale + offset_y)
                    )
                    new_points.append(new_point)
                normalized_entities.append({
                    'type': entity['type'],
                    'points': new_points,
                    'closed': entity.get('closed', False)
                })
        
        return normalized_entities
    
    def entities_to_svg_paths(self, entities):
        """將實體轉換為 SVG 路徑字串"""
        paths = []
        
        for entity in entities:
            if entity['type'] == 'LINE':
                path = f"M{entity['start'][0]:.1f},{entity['start'][1]:.1f} L{entity['end'][0]:.1f},{entity['end'][1]:.1f}"
                paths.append(path)
            else:  # POLYLINE
                if not entity['points']:
                    continue
                    
                path_parts = []
                first_point = entity['points'][0]
                path_parts.append(f"M{first_point[0]:.1f},{first_point[1]:.1f}")
                
                for point in entity['points'][1:]:
                    path_parts.append(f"L{point[0]:.1f},{point[1]:.1f}")
                
                if entity.get('closed', False):
                    path_parts.append("Z")
                
                paths.append(" ".join(path_parts))
        
        return " ".join(paths)
    
    def create_svg(self, path_data, rebar_type="unknown", text_positions=None):
        """建立完整的 SVG"""
        svg = Element('svg')
        svg.set('width', str(self.svg_width))
        svg.set('height', str(self.svg_height))
        svg.set('viewBox', f'0 0 {self.svg_width} {self.svg_height}')
        svg.set('xmlns', 'http://www.w3.org/2000/svg')
        
        # 加入鋼筋路徑
        path = SubElement(svg, 'path')
        path.set('d', path_data)
        path.set('stroke', self.stroke_color)
        path.set('stroke-width', str(self.stroke_width))
        path.set('stroke-linecap', 'round')
        path.set('stroke-linejoin', 'round')
        path.set('fill', 'none')
        
        # 加入文字位置標記（用於後續程式填入）
        if text_positions:
            for pos_name, (x, y) in text_positions.items():
                text = SubElement(svg, 'text')
                text.set('x', str(x))
                text.set('y', str(y))
                text.set('text-anchor', 'middle')
                text.set('font-family', '新細明體, PMingLiU, serif')
                text.set('font-size', '12')
                text.set('fill', self.stroke_color)
                text.text = f'{{{pos_name}}}'  # 佔位符，如 {A}, {B}
        
        return svg
    
    def identify_rebar_type(self, entities):
        """根據實體特徵識別鋼筋類型"""
        if not entities:
            return "unknown"
        
        line_count = sum(1 for e in entities if e['type'] == 'LINE')
        polyline_count = sum(1 for e in entities if e['type'] in ['POLYLINE', 'LWPOLYLINE'])
        
        # 簡單的鋼筋類型識別邏輯（可根據需要擴展）
        if line_count == 1 and polyline_count == 0:
            return "II-0"  # 直筋
        elif line_count == 2 and polyline_count == 0:
            return "LI-0"  # L形筋
        elif polyline_count > 0:
            # 檢查是否為封閉形狀（箍筋）
            for entity in entities:
                if entity['type'] in ['POLYLINE', 'LWPOLYLINE'] and entity.get('closed', False):
                    return "stirrup"  # 箍筋
            return "bent"  # 彎折筋
        else:
            return "complex"  # 複雜形狀
    
    def get_text_positions(self, rebar_type, entities):
        """根據鋼筋類型計算文字位置"""
        min_x, min_y, max_x, max_y = self.get_bounding_box(entities)
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        
        positions = {}
        
        if rebar_type == "II-0":  # 直筋
            positions = {
                'A': (center_x, center_y - 15),
                'total': (center_x, center_y + 25)
            }
        elif rebar_type == "LI-0":  # L形筋
            positions = {
                'A': (min_x - 10, center_y),
                'B': (center_x, min_y - 10),
                'total': (center_x, max_y + 15)
            }
        elif rebar_type == "stirrup":  # 箍筋
            positions = {
                'H': (min_x - 10, center_y),
                'W': (center_x, min_y - 10),
                'total': (center_x, max_y + 15)
            }
        else:  # 其他類型
            positions = {
                'param1': (center_x, center_y - 15),
                'total': (center_x, max_y + 15)
            }
        
        return positions
    
    def convert_dxf_to_svg_template(self, dxf_path, output_path=None, layer_name="1號線"):
        """主要轉換函數"""
        # 載入 DXF
        doc = self.load_dxf(dxf_path)
        if not doc:
            return None
        
        # 提取鋼筋線條
        entities = self.extract_rebar_lines(doc, layer_name)
        if not entities:
            print(f"在圖層 '{layer_name}' 中找不到任何實體")
            return None
        
        # 標準化座標
        normalized_entities = self.normalize_coordinates(entities)
        
        # 識別鋼筋類型
        rebar_type = self.identify_rebar_type(normalized_entities)
        
        # 轉換為 SVG 路徑
        path_data = self.entities_to_svg_paths(normalized_entities)
        
        # 計算文字位置
        text_positions = self.get_text_positions(rebar_type, normalized_entities)
        
        # 建立 SVG
        svg_element = self.create_svg(path_data, rebar_type, text_positions)
        
        # 格式化輸出
        rough_string = tostring(svg_element, 'unicode')
        reparsed = parseString(rough_string)
        pretty_svg = reparsed.toprettyxml(indent="  ")
        
        # 移除 XML 宣告行
        pretty_svg = '\n'.join(pretty_svg.split('\n')[1:])
        
        # 儲存檔案
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(pretty_svg)
            print(f"SVG 已儲存至: {output_path}")
        
        return {
            'svg_content': pretty_svg,
            'rebar_type': rebar_type,
            'text_positions': text_positions,
            'path_data': path_data
        }

# GUI 類別
class DXFToSVGGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("鋼筋 DXF 轉 SVG 轉換器")
        self.root.geometry("800x600")
        self.root.configure(bg='#f0f0f0')
        
        # 初始化轉換器
        self.converter = RebarDXFToSVG()
        
        # 檔案路徑變數 - 在 create_widgets 之前初始化
        self.dxf_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.layer_name = tk.StringVar(value="1號線")
        
        # 設定樣式
        self.setup_styles()
        
        # 建立主框架
        self.create_widgets()
        
    def setup_styles(self):
        """設定 GUI 樣式"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # 設定按鈕樣式
        style.configure('Action.TButton', 
                       font=('新細明體', 10, 'bold'),
                       padding=10)
        
        # 設定標籤樣式
        style.configure('Title.TLabel',
                       font=('新細明體', 14, 'bold'),
                       foreground='#2c3e50')
        
        style.configure('Subtitle.TLabel',
                       font=('新細明體', 11),
                       foreground='#34495e')
    
    def create_widgets(self):
        """建立 GUI 元件"""
        # 主標題
        title_frame = tk.Frame(self.root, bg='#f0f0f0')
        title_frame.pack(pady=20)
        
        title_label = ttk.Label(title_frame, 
                               text="鋼筋 DXF 轉 SVG 轉換器",
                               style='Title.TLabel')
        title_label.pack()
        
        subtitle_label = ttk.Label(title_frame,
                                  text="上傳 DXF 檔案並轉換為標準化 SVG 模板",
                                  style='Subtitle.TLabel')
        subtitle_label.pack(pady=5)
        
        # 檔案選擇區域
        self.create_file_selection_frame()
        
        # 設定區域
        self.create_settings_frame()
        
        # 轉換按鈕
        self.create_convert_button()
        
        # 日誌區域
        self.create_log_frame()
        
        # 狀態列
        self.create_status_bar()
    
    def create_file_selection_frame(self):
        """建立檔案選擇框架"""
        file_frame = ttk.LabelFrame(self.root, text="檔案選擇", padding=15)
        file_frame.pack(fill='x', padx=20, pady=10)
        
        # DXF 檔案選擇
        dxf_frame = tk.Frame(file_frame)
        dxf_frame.pack(fill='x', pady=5)
        
        ttk.Label(dxf_frame, text="DXF 檔案:").pack(side='left')
        ttk.Entry(dxf_frame, textvariable=self.dxf_path, width=50).pack(side='left', padx=5)
        ttk.Button(dxf_frame, text="瀏覽", 
                  command=self.browse_dxf_file).pack(side='left')
        
        # 輸出檔案選擇
        output_frame = tk.Frame(file_frame)
        output_frame.pack(fill='x', pady=5)
        
        ttk.Label(output_frame, text="輸出位置:").pack(side='left')
        ttk.Entry(output_frame, textvariable=self.output_path, width=50).pack(side='left', padx=5)
        ttk.Button(output_frame, text="瀏覽", 
                  command=self.browse_output_file).pack(side='left')
    
    def create_settings_frame(self):
        """建立設定框架"""
        settings_frame = ttk.LabelFrame(self.root, text="轉換設定", padding=15)
        settings_frame.pack(fill='x', padx=20, pady=10)
        
        # 圖層名稱設定
        layer_frame = tk.Frame(settings_frame)
        layer_frame.pack(fill='x', pady=5)
        
        ttk.Label(layer_frame, text="圖層名稱:").pack(side='left')
        ttk.Entry(layer_frame, textvariable=self.layer_name, width=20).pack(side='left', padx=5)
        
        # SVG 尺寸設定
        size_frame = tk.Frame(settings_frame)
        size_frame.pack(fill='x', pady=5)
        
        ttk.Label(size_frame, text="SVG 寬度:").pack(side='left')
        self.svg_width_var = tk.StringVar(value="200")
        ttk.Entry(size_frame, textvariable=self.svg_width_var, width=10).pack(side='left', padx=5)
        
        ttk.Label(size_frame, text="SVG 高度:").pack(side='left', padx=(20, 0))
        self.svg_height_var = tk.StringVar(value="100")
        ttk.Entry(size_frame, textvariable=self.svg_height_var, width=10).pack(side='left', padx=5)
    
    def create_convert_button(self):
        """建立轉換按鈕"""
        button_frame = tk.Frame(self.root, bg='#f0f0f0')
        button_frame.pack(pady=20)
        
        self.convert_button = ttk.Button(button_frame, 
                                        text="開始轉換",
                                        style='Action.TButton',
                                        command=self.start_conversion)
        self.convert_button.pack()
        
        # 進度條
        self.progress = ttk.Progressbar(button_frame, mode='indeterminate')
        self.progress.pack(pady=10, fill='x')
    
    def create_log_frame(self):
        """建立日誌框架"""
        log_frame = ttk.LabelFrame(self.root, text="轉換日誌", padding=15)
        log_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, 
                                                 height=10,
                                                 font=('新細明體', 9))
        self.log_text.pack(fill='both', expand=True)
    
    def create_status_bar(self):
        """建立狀態列"""
        self.status_var = tk.StringVar(value="就緒")
        status_bar = ttk.Label(self.root, 
                              textvariable=self.status_var,
                              relief='sunken',
                              anchor='w')
        status_bar.pack(side='bottom', fill='x')
    
    def browse_dxf_file(self):
        """瀏覽 DXF 檔案"""
        filename = filedialog.askopenfilename(
            title="選擇 DXF 檔案",
            filetypes=[("DXF 檔案", "*.dxf"), ("所有檔案", "*.*")]
        )
        if filename:
            self.dxf_path.set(filename)
            # 自動設定輸出檔案名稱
            base_name = os.path.splitext(os.path.basename(filename))[0]
            output_dir = os.path.dirname(filename)
            self.output_path.set(os.path.join(output_dir, f"{base_name}_template.svg"))
            self.log_message(f"已選擇 DXF 檔案: {filename}")
    
    def browse_output_file(self):
        """瀏覽輸出檔案位置"""
        filename = filedialog.asksaveasfilename(
            title="選擇輸出位置",
            defaultextension=".svg",
            filetypes=[("SVG 檔案", "*.svg"), ("所有檔案", "*.*")]
        )
        if filename:
            self.output_path.set(filename)
            self.log_message(f"輸出位置設定為: {filename}")
    
    def log_message(self, message):
        """記錄訊息到日誌區域"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def start_conversion(self):
        """開始轉換程序"""
        # 驗證輸入
        if not self.dxf_path.get():
            messagebox.showerror("錯誤", "請選擇 DXF 檔案")
            return
        
        if not self.output_path.get():
            messagebox.showerror("錯誤", "請設定輸出位置")
            return
        
        # 更新設定
        try:
            self.converter.svg_width = int(self.svg_width_var.get())
            self.converter.svg_height = int(self.svg_height_var.get())
        except ValueError:
            messagebox.showerror("錯誤", "SVG 尺寸必須為數字")
            return
        
        # 禁用按鈕並開始進度條
        self.convert_button.config(state='disabled')
        self.progress.start()
        self.status_var.set("轉換中...")
        
        # 在新執行緒中執行轉換
        thread = threading.Thread(target=self.perform_conversion)
        thread.daemon = True
        thread.start()
    
    def perform_conversion(self):
        """執行轉換程序"""
        try:
            self.log_message("開始轉換 DXF 檔案...")
            
            # 執行轉換
            result = self.converter.convert_dxf_to_svg_template(
                dxf_path=self.dxf_path.get(),
                output_path=self.output_path.get(),
                layer_name=self.layer_name.get()
            )
            
            if result:
                self.log_message(f"轉換成功！")
                self.log_message(f"鋼筋類型: {result['rebar_type']}")
                self.log_message(f"文字位置: {result['text_positions']}")
                self.log_message(f"SVG 已儲存至: {self.output_path.get()}")
                
                # 在主執行緒中顯示成功訊息
                self.root.after(0, lambda: messagebox.showinfo("成功", 
                    f"轉換完成！\n鋼筋類型: {result['rebar_type']}\n檔案已儲存至: {self.output_path.get()}"))
            else:
                self.log_message("轉換失敗")
                self.root.after(0, lambda: messagebox.showerror("錯誤", "轉換失敗，請檢查檔案和設定"))
                
        except Exception as e:
            error_msg = f"轉換過程中發生錯誤: {str(e)}"
            self.log_message(error_msg)
            self.root.after(0, lambda: messagebox.showerror("錯誤", error_msg))
        
        finally:
            # 恢復按鈕並停止進度條
            self.root.after(0, self.finish_conversion)
    
    def finish_conversion(self):
        """完成轉換後的清理工作"""
        self.convert_button.config(state='normal')
        self.progress.stop()
        self.status_var.set("就緒")

# 主函數 - 啟動 GUI
def main():
    """啟動 GUI 介面"""
    root = tk.Tk()
    app = DXFToSVGGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()