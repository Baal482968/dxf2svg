# dxf2svg_gui.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import threading
import subprocess
import platform
from dxf2svg_core import DXFToSVG

class DXFToSVGGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("DXF 線條轉 SVG 轉換器")
        self.root.geometry("700x600")
        self.converter = DXFToSVG()
        self.dxf_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.setup_styles()
        self.create_widgets()
    # ... 其餘 GUI 相關方法直接複製 main.py 的內容 ...

# 啟動點
if __name__ == "__main__":
    root = tk.Tk()
    app = DXFToSVGGUI(root)
    root.mainloop() 