import sys
import os
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES
from pathlib import Path

# --- Helper: Handle paths for bundled App/Exe ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- Configuration ---
SIG_INRAW = b'\x69\x4E\x52\x41\x57'  # iNRAW
SIG_INR3D = b'\x69\x4E\x52\x33\x44'  # iNR3D

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# --- Language Assets ---
LANG = {
    'en': {
        'title': "NEV Converter Pro",
        'logo': "NEV TOOL",
        'theme_dark': "Dark Mode",
        'theme_light': "Light Mode",
        'drop_zone': "Drag & Drop Files Here",
        'mode_conv': "Convert (.NEV → .R3D)",
        'mode_rev': "Revert (.R3D → .NEV)",
        'btn_add': "+ Add Files",
        'btn_clear': "Clear Queue",
        'btn_start': "START PROCESSING",
        'status_idle': "Waiting for files...",
        'status_ready': "{} files in queue.",
        'status_done': "Success! Processed {} files.",
        'confirm_msg': "Ready to process {} files. Continue?",
        'warn_empty': "The queue is empty!",
        'dialog_nev': "NEV Video",
        'dialog_r3d': "RED Video"
    },
    'zh': {
        'title': "NEV 专业转换工具",
        'logo': "NEV 工具箱",
        'theme_dark': "深色模式",
        'theme_light': "浅色模式",
        'drop_zone': "请将文件拖放到此处",
        'mode_conv': "转换模式 (.NEV → .R3D)",
        'mode_rev': "还原模式 (.R3D → .NEV)",
        'btn_add': "+ 添加文件",
        'btn_clear': "清空列表",
        'btn_start': "开始处理",
        'status_idle': "等待文件...",
        'status_ready': "队列中有 {} 个文件。",
        'status_done': "成功！处理了 {} 个文件。",
        'confirm_msg': "准备处理 {} 个文件。是否继续？",
        'warn_empty': "列表为空！",
        'dialog_nev': "NEV 视频文件",
        'dialog_r3d': "RED 视频文件"
    }
}

class ConverterApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        
        # --- UNIVERSAL ICON LOADER ---
        try:
            if sys.platform.startswith("win"):
                # Windows: Use .ico
                icon_file = resource_path("icon.ico")
                self.iconbitmap(icon_file)
            else:
                # Mac/Linux: Use .png (Tkinter is unstable with .ico on Mac)
                icon_file = resource_path("icon.png")
                img = tk.PhotoImage(file=icon_file)
                self.iconphoto(True, img)
        except Exception as e:
            print(f"Icon Warning: {e}")

        # --- Initialize Drag & Drop ---
        try:
            self.TkdndVersion = TkinterDnD._require(self)
            self.dnd_enabled = True
        except:
            self.dnd_enabled = False
            print("Warning: tkinterdnd2 library not found.")

        self.cur_lang = 'en'
        self.queue = set()
        self.mode_var = tk.StringVar(value="convert")
        
        self.setup_ui()
        self.update_texts()

    def setup_ui(self):
        self.geometry("850x600")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(7, weight=1)

        self.lbl_logo = ctk.CTkLabel(self.sidebar, text="NEV TOOL", font=ctk.CTkFont(size=26, weight="bold"))
        self.lbl_logo.grid(row=0, column=0, padx=20, pady=(30, 20))

        self.switch_theme = ctk.CTkSwitch(self.sidebar, command=self.toggle_theme, text="Mode", onvalue="Dark", offvalue="Light")
        self.switch_theme.select()
        self.switch_theme.grid(row=1, column=0, padx=20, pady=10, sticky="w")

        self.opt_lang = ctk.CTkOptionMenu(self.sidebar, values=["English", "中文"], command=self.change_lang, width=160)
        self.opt_lang.grid(row=2, column=0, padx=20, pady=10)

        self.rb_conv = ctk.CTkRadioButton(self.sidebar, variable=self.mode_var, value="convert", command=self.refresh_queue_view)
        self.rb_conv.grid(row=3, column=0, padx=20, pady=(20, 10), sticky="w")
        
        self.rb_rev = ctk.CTkRadioButton(self.sidebar, variable=self.mode_var, value="revert", command=self.refresh_queue_view)
        self.rb_rev.grid(row=4, column=0, padx=20, pady=10, sticky="w")

        self.btn_add = ctk.CTkButton(self.sidebar, command=self.open_file_dialog, fg_color="transparent", border_width=2, border_color="#3B8ED0")
        self.btn_add.grid(row=5, column=0, padx=20, pady=(30, 10), sticky="ew")

        self.btn_clear = ctk.CTkButton(self.sidebar, command=self.clear_queue, fg_color="#cf4444", hover_color="#8a2e2e")
        self.btn_clear.grid(row=6, column=0, padx=20, pady=10, sticky="ew")

        # Main Area
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_area.grid_rowconfigure(1, weight=1)
        self.main_area.grid_columnconfigure(0, weight=1)

        self.file_scroll = ctk.CTkScrollableFrame(self.main_area, label_text="Drop Files Here")
        self.file_scroll.grid(row=1, column=0, sticky="nsew", pady=(0, 20))

        self.footer = ctk.CTkFrame(self.main_area, height=70, fg_color="transparent")
        self.footer.grid(row=2, column=0, sticky="ew")
        
        self.lbl_status = ctk.CTkLabel(self.footer, text="...", font=ctk.CTkFont(size=14), text_color="gray")
        self.lbl_status.pack(side="left", padx=10)

        self.btn_start = ctk.CTkButton(self.footer, height=45, width=200, font=ctk.CTkFont(size=16, weight="bold"), command=self.start_process)
        self.btn_start.pack(side="right")

        if self.dnd_enabled:
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<Drop>>', self.on_drop)

    # --- Logic Methods ---
    def toggle_theme(self):
        ctk.set_appearance_mode("Dark" if self.switch_theme.get() == "Dark" else "Light")
        self.update_texts()

    def change_lang(self, choice):
        self.cur_lang = 'zh' if choice == "中文" else 'en'
        self.update_texts()

    def update_texts(self):
        t = LANG[self.cur_lang]
        self.title(t['title'])
        self.lbl_logo.configure(text=t['logo'])
        self.switch_theme.configure(text=t['theme_dark'] if ctk.get_appearance_mode() == "Dark" else t['theme_light'])
        self.rb_conv.configure(text=t['mode_conv'])
        self.rb_rev.configure(text=t['mode_rev'])
        self.btn_add.configure(text=t['btn_add'])
        self.btn_clear.configure(text=t['btn_clear'])
        self.btn_start.configure(text=t['btn_start'])
        self.file_scroll.configure(label_text=t['drop_zone'])
        if "Success" not in self.lbl_status.cget("text"):
            self.lbl_status.configure(text=t['status_idle'])

    def add_files(self, paths):
        added = False
        target_ext = ".nev" if self.mode_var.get() == "convert" else ".r3d"
        for p in paths:
            path_obj = Path(p)
            if (path_obj.is_file() and path_obj.suffix.lower() == target_ext) or path_obj.is_dir():
                if str(path_obj) not in self.queue:
                    self.queue.add(str(path_obj))
                    lbl_text = f"📁 {path_obj.name}" if path_obj.is_dir() else f"  {path_obj.name}"
                    lbl = ctk.CTkLabel(self.file_scroll, text=lbl_text, anchor="w", fg_color=("gray85", "gray25"), corner_radius=6)
                    lbl.pack(fill="x", pady=2, padx=5, ipady=5)
                    added = True
        
        if added:
            t = LANG[self.cur_lang]
            self.lbl_status.configure(text=t['status_ready'].format(len(self.queue)), text_color=("black", "white"))

    def refresh_queue_view(self): pass

    def on_drop(self, event):
        files = self.tk.splitlist(event.data)
        has_nev = any(f.lower().endswith('.nev') for f in files)
        has_r3d = any(f.lower().endswith('.r3d') for f in files)
        if has_nev and not has_r3d: self.mode_var.set("convert")
        elif has_r3d and not has_nev: self.mode_var.set("revert")
        self.add_files(files)

    def open_file_dialog(self):
        t = LANG[self.cur_lang]
        is_conv = self.mode_var.get() == "convert"
        ftypes = [(t['dialog_nev'], "*.NEV")] if is_conv else [(t['dialog_r3d'], "*.R3D")]
        files = filedialog.askopenfilenames(filetypes=ftypes)
        self.add_files(files)

    def clear_queue(self):
        self.queue.clear()
        for widget in self.file_scroll.winfo_children(): widget.destroy()
        self.lbl_status.configure(text=LANG[self.cur_lang]['status_idle'], text_color="gray")

    def start_process(self):
        t = LANG[self.cur_lang]
        if not self.queue:
            messagebox.showwarning("!", t['warn_empty'])
            return
        if not messagebox.askyesno("?", t['confirm_msg'].format(len(self.queue))):
            return

        mode = self.mode_var.get()
        cfg = {
            'target_sig': SIG_INRAW if mode == 'convert' else SIG_INR3D,
            'replace_sig': SIG_INR3D if mode == 'convert' else SIG_INRAW,
            'target_ext': '.NEV' if mode == 'convert' else '.R3D',
            'new_ext': '.R3D' if mode == 'convert' else '.NEV'
        }
        count = 0
        def get_all_files():
            for p_str in self.queue:
                p = Path(p_str)
                if p.is_file(): yield p
                elif p.is_dir():
                    for sub in p.rglob("*"):
                        if sub.is_file(): yield sub

        for file_path in get_all_files():
            if file_path.suffix.lower() == cfg['target_ext'].lower():
                try:
                    with open(file_path, 'r+b') as f:
                        header = f.read(4096)
                        offset = header.find(cfg['target_sig'])
                        if offset != -1:
                            f.seek(offset)
                            f.write(cfg['replace_sig'])
                            new_path = file_path.with_suffix(cfg['new_ext'])
                            file_path.rename(new_path)
                            count += 1
                except Exception as e:
                    print(f"Error: {e}")

        self.clear_queue()
        self.lbl_status.configure(text=t['status_done'].format(count), text_color="#2CC985")

if __name__ == "__main__":
    app = ConverterApp()
    app.mainloop()