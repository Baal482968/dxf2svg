from dxf2svg_gui import DXFToSVGGUI
import tkinter as tk

if __name__ == "__main__":
    root = tk.Tk()
    app = DXFToSVGGUI(root)
    root.mainloop()