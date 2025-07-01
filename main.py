#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DXF 線條轉 SVG 轉換器
從 DXF 檔案中提取所有線條並轉換為 SVG
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
import subprocess
import platform

class DXFToSVG:
    def __init__(self):
        self.svg_width = 800
        self.svg_height = 600
        self.stroke_width = 1
        self.stroke_color = "#000000"
        
    def load_dxf(self, dxf_path):
        """載入 DXF 檔案"""
        try:
            doc = ezdxf.readfile(dxf_path)
            return doc
        except Exception as e:
            print(f"載入 DXF 檔案失敗: {e}")
            return None
    
    def extract_all_lines(self, doc):
        """從 DXF 檔案中提取所有線條實體"""
        msp = doc.modelspace()
        line_entities = []
        
        for entity in msp:
            if entity.dxftype() == 'LINE':
                line_entities.append({
                    'type': 'LINE',
                    'start': (entity.dxf.start.x, entity.dxf.start.y),
                    'end': (entity.dxf.end.x, entity.dxf.end.y),
                    'layer': entity.dxf.layer,
                    'color': getattr(entity.dxf, 'color', 7)  # 預設為白色
                })
            elif entity.dxftype() == 'LWPOLYLINE':
                points = [(point[0], point[1]) for point in entity.get_points()]
                line_entities.append({
                    'type': 'LWPOLYLINE', 
                    'points': points,
                    'closed': entity.closed,
                    'layer': entity.dxf.layer,
                    'color': getattr(entity.dxf, 'color', 7)
                })
            elif entity.dxftype() == 'POLYLINE':
                points = [(vertex.dxf.location.x, vertex.dxf.location.y) 
                         for vertex in entity.vertices]
                line_entities.append({
                    'type': 'POLYLINE',
                    'points': points,
                    'closed': entity.closed,
                    'layer': entity.dxf.layer,
                    'color': getattr(entity.dxf, 'color', 7)
                })
            elif entity.dxftype() == 'ARC':
                # 將圓弧轉換為多個線段
                center = entity.dxf.center
                radius = entity.dxf.radius
                start_angle = math.radians(entity.dxf.start_angle)
                end_angle = math.radians(entity.dxf.end_angle)
                
                # 如果結束角度小於開始角度，加上 360 度
                if end_angle < start_angle:
                    end_angle += 2 * math.pi
                
                # 將圓弧分割為多個線段
                num_segments = max(8, int((end_angle - start_angle) * radius / 10))
                angle_step = (end_angle - start_angle) / num_segments
                
                arc_points = []
                for i in range(num_segments + 1):
                    angle = start_angle + i * angle_step
                    x = center.x + radius * math.cos(angle)
                    y = center.y + radius * math.sin(angle)
                    arc_points.append((x, y))
                
                line_entities.append({
                    'type': 'ARC_SEGMENTS',
                    'points': arc_points,
                    'closed': False,
                    'layer': entity.dxf.layer,
                    'color': getattr(entity.dxf, 'color', 7)
                })
            elif entity.dxftype() == 'CIRCLE':
                # 將圓轉換為多個線段
                center = entity.dxf.center
                radius = entity.dxf.radius
                
                # 將圓分割為 32 個線段
                num_segments = 32
                angle_step = 2 * math.pi / num_segments
                
                circle_points = []
                for i in range(num_segments + 1):
                    angle = i * angle_step
                    x = center.x + radius * math.cos(angle)
                    y = center.y + radius * math.sin(angle)
                    circle_points.append((x, y))
                
                line_entities.append({
                    'type': 'CIRCLE_SEGMENTS',
                    'points': circle_points,
                    'closed': True,
                    'layer': entity.dxf.layer,
                    'color': getattr(entity.dxf, 'color', 7)
                })
        
        return line_entities
    
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
            else:  # POLYLINE, LWPOLYLINE, ARC_SEGMENTS, CIRCLE_SEGMENTS
                for point in entity['points']:
                    x_coords.append(point[0])
                    y_coords.append(point[1])
        
        return min(x_coords), min(y_coords), max(x_coords), max(y_coords)
    
    def normalize_coordinates(self, entities, target_width=800, target_height=600, margin=50):
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
                    'end': new_end,
                    'layer': entity['layer'],
                    'color': entity['color']
                })
            else:  # POLYLINE, LWPOLYLINE, ARC_SEGMENTS, CIRCLE_SEGMENTS
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
                    'closed': entity.get('closed', False),
                    'layer': entity['layer'],
                    'color': entity['color']
                })
        
        return normalized_entities
    
    def get_color_by_index(self, color_index):
        """根據 AutoCAD 顏色索引取得顏色"""
        color_map = {
            1: "#FF0000",    # 紅色
            2: "#FFFF00",    # 黃色
            3: "#00FF00",    # 綠色
            4: "#00FFFF",    # 青色
            5: "#0000FF",    # 藍色
            6: "#FF00FF",    # 洋紅色
            7: "#FFFFFF",    # 白色
            8: "#808080",    # 灰色
            9: "#C0C0C0",    # 淺灰色
            10: "#800000",   # 深紅色
            11: "#808000",   # 橄欖色
            12: "#008000",   # 深綠色
            13: "#008080",   # 深青色
            14: "#000080",   # 深藍色
            15: "#800080",   # 紫色
        }
        return color_map.get(color_index, "#000000")
    
    def entities_to_svg_elements(self, entities):
        """將實體轉換為 SVG 元素"""
        svg_elements = []
        
        for entity in entities:
            color = self.get_color_by_index(entity['color'])
            
            if entity['type'] == 'LINE':
                line = Element('line')
                line.set('x1', f"{entity['start'][0]:.2f}")
                line.set('y1', f"{entity['start'][1]:.2f}")
                line.set('x2', f"{entity['end'][0]:.2f}")
                line.set('y2', f"{entity['end'][1]:.2f}")
                line.set('stroke', color)
                line.set('stroke-width', str(self.stroke_width))
                line.set('stroke-linecap', 'round')
                svg_elements.append(line)
            else:  # POLYLINE, LWPOLYLINE, ARC_SEGMENTS, CIRCLE_SEGMENTS
                if not entity['points']:
                    continue
                    
                path = Element('path')
                path_parts = []
                first_point = entity['points'][0]
                path_parts.append(f"M{first_point[0]:.2f},{first_point[1]:.2f}")
                
                for point in entity['points'][1:]:
                    path_parts.append(f"L{point[0]:.2f},{point[1]:.2f}")
                
                if entity.get('closed', False):
                    path_parts.append("Z")
                
                path.set('d', " ".join(path_parts))
                path.set('stroke', color)
                path.set('stroke-width', str(self.stroke_width))
                path.set('stroke-linecap', 'round')
                path.set('stroke-linejoin', 'round')
                path.set('fill', 'none')
                svg_elements.append(path)
        
        return svg_elements
    
    def create_svg(self, entities):
        """建立完整的 SVG"""
        svg = Element('svg')
        svg.set('width', str(self.svg_width))
        svg.set('height', str(self.svg_height))
        svg.set('viewBox', f'0 0 {self.svg_width} {self.svg_height}')
        svg.set('xmlns', 'http://www.w3.org/2000/svg')
        
        # 加入背景
        background = SubElement(svg, 'rect')
        background.set('width', str(self.svg_width))
        background.set('height', str(self.svg_height))
        background.set('fill', '#FFFFFF')
        
        # 加入所有線條元素
        svg_elements = self.entities_to_svg_elements(entities)
        for element in svg_elements:
            svg.append(element)
        
        return svg
    
    def convert_dxf_to_svg(self, dxf_path, output_path=None):
        """將 DXF 檔案轉換為 SVG"""
        # 載入 DXF 檔案
        doc = self.load_dxf(dxf_path)
        if not doc:
            return False, "無法載入 DXF 檔案"
        
        # 提取所有線條
        entities = self.extract_all_lines(doc)
        if not entities:
            return False, "DXF 檔案中沒有找到線條"
        
        # 標準化座標
        normalized_entities = self.normalize_coordinates(entities, self.svg_width, self.svg_height)
        
        # 建立 SVG
        svg = self.create_svg(normalized_entities)
        
        # 格式化 SVG
        rough_string = tostring(svg, 'unicode')
        reparsed = parseString(rough_string)
        formatted_svg = reparsed.toprettyxml(indent="  ")
        
        # 儲存 SVG 檔案
        if output_path is None:
            base_name = os.path.splitext(dxf_path)[0]
            output_path = f"{base_name}.svg"
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(formatted_svg)
            return True, f"成功轉換為 SVG: {output_path}"
        except Exception as e:
            return False, f"儲存 SVG 檔案失敗: {e}"

class DXFToSVGGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("DXF 線條轉 SVG 轉換器")
        self.root.geometry("600x500")
        
        self.converter = DXFToSVG()
        self.dxf_path = tk.StringVar()
        self.output_path = tk.StringVar()
        
        self.setup_styles()
        self.create_widgets()
    
    def setup_styles(self):
        """設定 GUI 樣式"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # 設定按鈕樣式
        style.configure('Convert.TButton', 
                       font=('新細明體', 12, 'bold'),
                       padding=10)
        
        # 設定標籤樣式
        style.configure('Title.TLabel',
                       font=('新細明體', 14, 'bold'),
                       foreground='#2c3e50')
    
    def create_widgets(self):
        """建立 GUI 元件"""
        # 主標題
        title_label = ttk.Label(self.root, text="DXF 線條轉 SVG 轉換器", 
                               style='Title.TLabel')
        title_label.pack(pady=20)
        
        # 檔案選擇框架
        self.create_file_selection_frame()
        
        # 設定框架
        self.create_settings_frame()
        
        # 轉換按鈕
        self.create_convert_button()
        
        # 日誌框架
        self.create_log_frame()
        
        # 狀態列
        self.create_status_bar()
    
    def create_file_selection_frame(self):
        """建立檔案選擇框架"""
        file_frame = ttk.LabelFrame(self.root, text="檔案選擇", padding=10)
        file_frame.pack(fill='x', padx=20, pady=10)
        
        # DXF 檔案選擇
        ttk.Label(file_frame, text="DXF 檔案:").grid(row=0, column=0, sticky='w', pady=5)
        ttk.Entry(file_frame, textvariable=self.dxf_path, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="瀏覽", command=self.browse_dxf_file).grid(row=0, column=2, pady=5)
        
        # 輸出檔案選擇
        ttk.Label(file_frame, text="輸出檔案:").grid(row=1, column=0, sticky='w', pady=5)
        ttk.Entry(file_frame, textvariable=self.output_path, width=50).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="瀏覽", command=self.browse_output_file).grid(row=1, column=2, pady=5)
    
    def create_settings_frame(self):
        """建立設定框架"""
        settings_frame = ttk.LabelFrame(self.root, text="轉換設定", padding=10)
        settings_frame.pack(fill='x', padx=20, pady=10)
        
        # SVG 尺寸設定
        ttk.Label(settings_frame, text="SVG 寬度:").grid(row=0, column=0, sticky='w', pady=5)
        self.svg_width_var = tk.StringVar(value="800")
        ttk.Entry(settings_frame, textvariable=self.svg_width_var, width=10).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(settings_frame, text="SVG 高度:").grid(row=0, column=2, sticky='w', padx=(20,0), pady=5)
        self.svg_height_var = tk.StringVar(value="600")
        ttk.Entry(settings_frame, textvariable=self.svg_height_var, width=10).grid(row=0, column=3, padx=5, pady=5)
        
        # 線條寬度設定
        ttk.Label(settings_frame, text="線條寬度:").grid(row=1, column=0, sticky='w', pady=5)
        self.stroke_width_var = tk.StringVar(value="1")
        ttk.Entry(settings_frame, textvariable=self.stroke_width_var, width=10).grid(row=1, column=1, padx=5, pady=5)
    
    def create_convert_button(self):
        """建立轉換按鈕"""
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=20)
        
        self.convert_button = ttk.Button(button_frame, text="開始轉換", 
                                        style='Convert.TButton',
                                        command=self.start_conversion)
        self.convert_button.pack()
        
        # 建立開啟圖片按鈕（初始時禁用）
        self.open_image_button = ttk.Button(button_frame, text="開啟圖片", 
                                           style='Convert.TButton',
                                           command=self.open_image,
                                           state='disabled')
        self.open_image_button.pack(pady=5)
    
    def create_log_frame(self):
        """建立日誌框架"""
        log_frame = ttk.LabelFrame(self.root, text="轉換日誌", padding=10)
        log_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, width=70)
        self.log_text.pack(fill='both', expand=True)
    
    def create_status_bar(self):
        """建立狀態列"""
        self.status_var = tk.StringVar(value="就緒")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, 
                              relief='sunken', anchor='w')
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
            base_name = os.path.splitext(filename)[0]
            self.output_path.set(f"{base_name}.svg")
    
    def browse_output_file(self):
        """瀏覽輸出檔案"""
        filename = filedialog.asksaveasfilename(
            title="儲存 SVG 檔案",
            defaultextension=".svg",
            filetypes=[("SVG 檔案", "*.svg"), ("所有檔案", "*.*")]
        )
        if filename:
            self.output_path.set(filename)
    
    def log_message(self, message):
        """記錄訊息到日誌"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def start_conversion(self):
        """開始轉換程序"""
        if not self.dxf_path.get():
            messagebox.showerror("錯誤", "請選擇 DXF 檔案")
            return
        
        # 更新設定
        try:
            self.converter.svg_width = int(self.svg_width_var.get())
            self.converter.svg_height = int(self.svg_height_var.get())
            self.converter.stroke_width = float(self.stroke_width_var.get())
        except ValueError:
            messagebox.showerror("錯誤", "請輸入有效的數值")
            return
        
        # 清空日誌
        self.log_text.delete(1.0, tk.END)
        
        # 禁用按鈕
        self.convert_button.config(state='disabled')
        self.disable_open_button()
        self.status_var.set("轉換中...")
        
        # 在新執行緒中執行轉換
        thread = threading.Thread(target=self.perform_conversion)
        thread.daemon = True
        thread.start()
    
    def perform_conversion(self):
        """執行轉換"""
        try:
            self.log_message("開始載入 DXF 檔案...")
            success, message = self.converter.convert_dxf_to_svg(
                self.dxf_path.get(), 
                self.output_path.get()
            )
            
            if success:
                self.log_message("✓ " + message)
                self.status_var.set("轉換完成")
                self.enable_open_button()
                messagebox.showinfo("成功", message)
            else:
                self.log_message("✗ " + message)
                self.status_var.set("轉換失敗")
                messagebox.showerror("錯誤", message)
                
        except Exception as e:
            error_msg = f"轉換過程中發生錯誤: {e}"
            self.log_message("✗ " + error_msg)
            self.status_var.set("轉換失敗")
            messagebox.showerror("錯誤", error_msg)
        finally:
            # 重新啟用按鈕
            self.root.after(0, self.finish_conversion)
    
    def finish_conversion(self):
        """完成轉換"""
        self.convert_button.config(state='normal')
    
    def open_image(self):
        """開啟生成的 SVG 圖片"""
        if not self.output_path.get():
            messagebox.showerror("錯誤", "沒有可開啟的圖片檔案")
            return
        
        if not os.path.exists(self.output_path.get()):
            messagebox.showerror("錯誤", "圖片檔案不存在")
            return
        
        try:
            system = platform.system()
            if system == "Darwin":  # macOS
                subprocess.run(["open", self.output_path.get()])
            elif system == "Windows":
                subprocess.run(["start", self.output_path.get()], shell=True)
            elif system == "Linux":
                subprocess.run(["xdg-open", self.output_path.get()])
            else:
                messagebox.showinfo("提示", f"請手動開啟檔案：{self.output_path.get()}")
        except Exception as e:
            messagebox.showerror("錯誤", f"無法開啟圖片：{e}")
    
    def enable_open_button(self):
        """啟用開啟圖片按鈕"""
        self.open_image_button.config(state='normal')
    
    def disable_open_button(self):
        """禁用開啟圖片按鈕"""
        self.open_image_button.config(state='disabled')

def main():
    """主程式"""
    root = tk.Tk()
    app = DXFToSVGGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()