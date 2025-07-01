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
        self.root.geometry("800x700")
        self.converter = DXFToSVG()
        self.dxf_paths = []  # 多檔案路徑
        self.output_dir = tk.StringVar()
        self.setup_styles()
        self.create_widgets()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        PRIMARY = '#42A5F5'
        PRIMARY_DARK = '#1976D2'
        BG = '#23272E'
        CARD = '#2C313A'
        TEXT = '#E3EAF2'
        DISABLED = '#555555'
        style.configure('.',
            font=('Microsoft JhengHei', 12),
            background=BG,
            foreground=TEXT,
        )
        style.configure('TLabel', background=BG, foreground=TEXT)
        style.configure('TFrame', background=BG)
        style.configure('TLabelframe', background=CARD, borderwidth=0, relief='flat')
        style.configure('TLabelframe.Label', font=('Microsoft JhengHei', 12, 'bold'), foreground=PRIMARY, background=CARD)
        style.configure('TEntry', fieldbackground=BG, foreground=TEXT, bordercolor=PRIMARY, lightcolor=PRIMARY, darkcolor=PRIMARY, borderwidth=2, relief='flat')
        style.map('TEntry', fieldbackground=[('readonly', BG)], foreground=[('readonly', TEXT)])
        style.configure('Convert.TButton',
            font=('Microsoft JhengHei', 13, 'bold'),
            padding=12,
            borderwidth=0,
            relief='flat',
            background=PRIMARY,
            foreground='#fff')
        style.map('Convert.TButton',
            background=[('active', PRIMARY_DARK), ('disabled', DISABLED)],
            foreground=[('disabled', '#fff')])

    def create_file_selection_frame(self):
        file_frame = ttk.Labelframe(self.root, text="檔案選擇", padding=18, style='TLabelframe')
        file_frame.pack(fill='x', padx=48, pady=(0, 24))
        file_frame.columnconfigure(1, weight=1)

        # DXF 多檔案選擇 + Listbox
        ttk.Label(file_frame, text="DXF 檔案:", width=10, anchor='e').grid(row=0, column=0, sticky='ne', pady=12, padx=(10,0))
        self.dxf_listbox = tk.Listbox(file_frame, height=6, selectmode='extended', bg='#23272E', fg='#fff', highlightbackground='#42A5F5', selectbackground='#1976D2')
        self.dxf_listbox.grid(row=0, column=1, padx=8, pady=12, sticky='ew')
        ttk.Button(file_frame, text="選擇檔案", command=self.browse_dxf_files, style='Convert.TButton').grid(row=0, column=2, padx=8, pady=12)
        ttk.Button(file_frame, text="移除選取", command=self.remove_selected_files, style='Convert.TButton').grid(row=1, column=2, padx=8, pady=0)

        # 輸出資料夾選擇
        ttk.Label(file_frame, text="輸出資料夾:", width=10, anchor='e').grid(row=1, column=0, sticky='e', pady=12, padx=(10,0))
        out_entry = ttk.Entry(file_frame, textvariable=self.output_dir, width=48, style='TEntry')
        out_entry.grid(row=1, column=1, padx=8, pady=12, sticky='ew')
        ttk.Button(file_frame, text="選擇資料夾", command=self.browse_output_dir, style='Convert.TButton').grid(row=2, column=2, padx=8, pady=12)

    def browse_dxf_files(self):
        filenames = filedialog.askopenfilenames(
            title="選擇 DXF 檔案",
            filetypes=[("DXF 檔案", "*.dxf"), ("所有檔案", "*.*")]
        )
        if filenames:
            for f in filenames:
                if f not in self.dxf_paths and f.lower().endswith('.dxf'):
                    self.dxf_paths.append(f)
                    self.dxf_listbox.insert(tk.END, f)
            # 自動設定輸出資料夾為第一個檔案的資料夾
            first_dir = os.path.dirname(filenames[0])
            self.output_dir.set(first_dir)

    def remove_selected_files(self):
        selected_indices = list(self.dxf_listbox.curselection())
        for idx in reversed(selected_indices):
            self.dxf_listbox.delete(idx)
            del self.dxf_paths[idx]

    def browse_output_dir(self):
        dirname = filedialog.askdirectory(title="選擇輸出資料夾")
        if dirname:
            self.output_dir.set(dirname)

    def start_conversion(self):
        if not self.dxf_paths:
            messagebox.showerror("錯誤", "請選擇至少一個 DXF 檔案")
            return
        if not self.output_dir.get():
            messagebox.showerror("錯誤", "請選擇輸出資料夾")
            return
        try:
            self.converter.svg_width = int(self.svg_width_var.get())
            self.converter.svg_height = int(self.svg_height_var.get())
            self.converter.stroke_width = float(self.stroke_width_var.get())
        except ValueError:
            messagebox.showerror("錯誤", "請輸入有效的數值")
            return
        self.log_text.delete(1.0, tk.END)
        self.convert_button.config(state='disabled')
        self.disable_open_button()
        self.status_var.set("轉換中...")
        thread = threading.Thread(target=self.perform_batch_conversion)
        thread.daemon = True
        thread.start()

    def perform_batch_conversion(self):
        try:
            for dxf_path in self.dxf_paths:
                base_name = os.path.splitext(os.path.basename(dxf_path))[0]
                output_svg = os.path.join(self.output_dir.get(), base_name + ".svg")
                self.log_message(f"開始轉換: {dxf_path}")
                success, message = self.converter.convert_dxf_to_svg(dxf_path, output_svg)
                if success:
                    self.log_message(f"✓ {message}")
                else:
                    self.log_message(f"✗ {message}")
            self.status_var.set("批次轉換完成")
            self.enable_open_button()
            messagebox.showinfo("完成", "所有 DXF 已批次轉換完成！")
        except Exception as e:
            error_msg = f"批次轉換過程中發生錯誤: {e}"
            self.log_message("✗ " + error_msg)
            self.status_var.set("轉換失敗")
            messagebox.showerror("錯誤", error_msg)
        finally:
            self.root.after(0, self.finish_conversion)

    def create_widgets(self):
        # 主標題
        title_label = ttk.Label(self.root, text="DXF 線條轉 SVG 轉換器", 
                               font=('Microsoft JhengHei', 22, 'bold'),
                               foreground='#42A5F5', anchor='center', background='#23272E')
        title_label.pack(pady=(32, 8))

        # 副標題
        subtitle_label = ttk.Label(self.root, text="將 DXF 內所有線條一鍵轉成 SVG 圖片",
                                   font=('Microsoft JhengHei', 12),
                                   foreground='#B0BEC5', anchor='center', background='#23272E')
        subtitle_label.pack(pady=(0, 24))

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

    def create_settings_frame(self):
        settings_frame = ttk.Labelframe(self.root, text="轉換設定", padding=18, style='TLabelframe')
        settings_frame.pack(fill='x', padx=48, pady=(0, 24))
        settings_frame.columnconfigure(1, weight=1)
        settings_frame.columnconfigure(3, weight=1)

        # SVG 尺寸設定
        ttk.Label(settings_frame, text="SVG 寬度:").grid(row=0, column=0, sticky='e', pady=12, padx=(10,0))
        self.svg_width_var = tk.StringVar(value="800")
        ttk.Entry(settings_frame, textvariable=self.svg_width_var, width=10, style='TEntry').grid(row=0, column=1, padx=8, pady=12)

        ttk.Label(settings_frame, text="SVG 高度:").grid(row=0, column=2, sticky='e', padx=(20,0), pady=12)
        self.svg_height_var = tk.StringVar(value="600")
        ttk.Entry(settings_frame, textvariable=self.svg_height_var, width=10, style='TEntry').grid(row=0, column=3, padx=8, pady=12)

        # 線條寬度設定
        ttk.Label(settings_frame, text="線條寬度:").grid(row=1, column=0, sticky='e', pady=12, padx=(10,0))
        self.stroke_width_var = tk.StringVar(value="1")
        ttk.Entry(settings_frame, textvariable=self.stroke_width_var, width=10, style='TEntry').grid(row=1, column=1, padx=8, pady=12)

    def create_convert_button(self):
        button_frame = ttk.Frame(self.root, style='TFrame')
        button_frame.pack(fill='x', padx=48, pady=18)
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(2, weight=1)

        self.convert_button = ttk.Button(
            button_frame, text="開始轉換",
            style='Convert.TButton',
            command=self.start_conversion
        )
        self.convert_button.grid(row=0, column=0, sticky='ew', padx=(0, 8), ipadx=10, ipady=6)

        self.open_image_button = ttk.Button(
            button_frame, text="開啟圖片",
            style='Convert.TButton',
            command=self.open_image,
            state='disabled'
        )
        self.open_image_button.grid(row=0, column=1, sticky='ew', padx=8, ipadx=10, ipady=6)

        self.open_folder_button = ttk.Button(
            button_frame, text="開啟資料夾",
            style='Convert.TButton',
            command=self.open_output_folder,
            state='disabled'
        )
        self.open_folder_button.grid(row=0, column=2, sticky='ew', padx=(8, 0), ipadx=10, ipady=6)

    def create_log_frame(self):
        log_frame = ttk.Labelframe(self.root, text="轉換日誌", padding=12, style='TLabelframe')
        log_frame.pack(fill='both', expand=True, padx=48, pady=(0, 24))

        self.log_text = tk.Text(log_frame, height=8, font=('Microsoft JhengHei', 11), bg='#23272E', fg='#fff', relief='flat', borderwidth=0, insertbackground='#fff')
        self.log_text.pack(fill='both', expand=True, padx=10, pady=10)

    def create_status_bar(self):
        self.status_var = tk.StringVar(value="就緒")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, 
                              anchor='w', font=('Microsoft JhengHei', 10),
                              background='#263238', foreground='#42A5F5')
        status_bar.pack(side='bottom', fill='x', pady=(0,0))

    def open_image(self):
        import platform
        import subprocess
        import os
        # 取得最新一個 SVG 檔案路徑
        if hasattr(self, 'dxf_paths') and self.dxf_paths and self.output_dir.get():
            # 只打開第一個 SVG（可依需求改成全部打開）
            base_name = os.path.splitext(os.path.basename(self.dxf_paths[0]))[0]
            svg_path = os.path.join(self.output_dir.get(), base_name + ".svg")
            if not os.path.exists(svg_path):
                from tkinter import messagebox
                messagebox.showerror("錯誤", f"找不到 SVG 檔案：{svg_path}")
                return
            try:
                system = platform.system()
                if system == "Darwin":
                    subprocess.run(["open", svg_path])
                elif system == "Windows":
                    subprocess.run(["start", svg_path], shell=True)
                elif system == "Linux":
                    subprocess.run(["xdg-open", svg_path])
                else:
                    from tkinter import messagebox
                    messagebox.showinfo("提示", f"請手動開啟檔案：{svg_path}")
            except Exception as e:
                from tkinter import messagebox
                messagebox.showerror("錯誤", f"無法開啟圖片：{e}")
        else:
            from tkinter import messagebox
            messagebox.showerror("錯誤", "沒有可開啟的圖片檔案")

    def open_output_folder(self):
        import platform
        import subprocess
        import os
        folder = self.output_dir.get()
        if not folder or not os.path.isdir(folder):
            from tkinter import messagebox
            messagebox.showerror("錯誤", "找不到輸出資料夾")
            return
        try:
            system = platform.system()
            if system == "Darwin":
                subprocess.run(["open", folder])
            elif system == "Windows":
                subprocess.run(["start", folder], shell=True)
            elif system == "Linux":
                subprocess.run(["xdg-open", folder])
            else:
                from tkinter import messagebox
                messagebox.showinfo("提示", f"請手動開啟資料夾：{folder}")
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("錯誤", f"無法開啟資料夾：{e}")

    def disable_open_button(self):
        self.open_image_button.config(state='disabled')
        self.open_folder_button.config(state='disabled')

    def enable_open_button(self):
        self.open_image_button.config(state='normal')
        self.open_folder_button.config(state='normal')

    def finish_conversion(self):
        self.convert_button.config(state='normal')

    def log_message(self, message):
        self.log_text.insert('end', f"{message}\n")
        self.log_text.see('end')
        self.root.update_idletasks()

# 啟動點
if __name__ == "__main__":
    root = tk.Tk()
    app = DXFToSVGGUI(root)
    root.mainloop() 