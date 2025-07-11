import os
import webbrowser
import requests
import io
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, StringVar, scrolledtext
from PIL import Image, ImageTk
from mutagen import File, MutagenError
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import locale
import sys


ICON_PATH = "icon.ico"
GITHUB_ICON_URL = "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"
GITHUB_PROFILE_URL = "https://github.com/SorakageMeiou"
GITHUB_WIKI_URL = "https://github.com/SorakageMeiou/AudioCoverRemover/wiki"
AUTHOR_EMAIL = "sorakagemo@qq.com"

AUDIO_EXTENSIONS = ('.mp3', '.flac', '.wav', '.aiff', '.ape', '.ogg', '.alac', '.wv', '.mpc')

# ====== 多语言支持 ======
class I18N:
    def __init__(self):
        self.languages = {
            'zh_CN': {'name': '中文', 'flag': '🇨🇳'},
            'en_US': {'name': 'English', 'flag': '🇺🇸'},
        }
        self.current_lang = self._detect_system_language()
        self.translations = self._load_translations()
        self.observers = []

    def _detect_system_language(self) -> str:
        """检测系统语言"""
        try:
            sys_lang = locale.getdefaultlocale()[0]
            return sys_lang if sys_lang in self.languages else 'zh_CN'
        except:
            return 'zh_CN'

    def _load_translations(self) -> Dict[str, Dict[str, str]]:
        """加载翻译字典"""
        return {
            'zh_CN': {
                'app_title': '音频封面移除工具 v1.1',
                'select_mode': '选择模式:',
                'single_file': '处理单个文件',
                'whole_folder': '处理整个文件夹',
                'select_file': '选择文件/文件夹',
                'start_process': '开始处理',
                'contact': f'联系作者: {AUTHOR_EMAIL}',
                'github': ' 访问作者 GitHub',
                'help': '帮助',
                'warning': '警告',
                'no_path': '请选择一个有效的文件或文件夹',
                'processing': '处理中...',
                'complete': '完成',
                'process_complete': '处理完成',
                'success': '成功',
                'fail': '失败',
                'files_processed': '共处理了 {} 个文件',
                'invalid_mp3': '无效的MP3文件格式',
                'no_id3': '没有ID3标签',
                'cover_removed': '封面已删除',
                'no_cover': '没有找到封面',
                'unsupported_format': '不支持的音频格式',
                'no_metadata': '没有找到元数据',
                'metadata_cleared': '元数据已清除',
                'process_error': '处理时出错: {}',
                'id3_error': 'ID3标签处理失败: {}',
                'audio_error': '音频标签处理失败: {}',
                'audio_files': '音频文件',
                'output_dir': '输出目录:',
                'browse': '浏览',
                'scan_subdir': '包含子目录',
                'drag_drop': '或将文件拖放到此处'
            },
            'en_US': {
                'app_title': 'Audio Cover Remover v1.1',
                'select_mode': 'Select Mode:',
                'single_file': 'Single File',
                'whole_folder': 'Whole Folder',
                'select_file': 'Select File/Folder',
                'start_process': 'Start Processing',
                'contact': f'Contact: {AUTHOR_EMAIL}',
                'github': ' Visit GitHub',
                'help': 'Help',
                'warning': 'Warning',
                'no_path': 'Please select a valid file or folder',
                'processing': 'Processing...',
                'complete': 'Complete',
                'process_complete': 'Processing complete',
                'success': 'Success',
                'fail': 'Fail',
                'files_processed': 'Total {} files processed',
                'invalid_mp3': 'Invalid MP3 file format',
                'no_id3': 'No ID3 tag found',
                'cover_removed': 'Cover removed',
                'no_cover': 'No cover found',
                'unsupported_format': 'Unsupported audio format',
                'no_metadata': 'No metadata found',
                'metadata_cleared': 'Metadata cleared',
                'process_error': 'Processing error: {}',
                'id3_error': 'ID3 tag error: {}',
                'audio_error': 'Audio tag error: {}',
                'audio_files': 'Audio Files',
                'output_dir': 'Output Directory:',
                'browse': 'Browse',
                'scan_subdir': 'Include subdirectories',
                'drag_drop': 'or drag and drop files here'
            },
        }

    def add_observer(self, callback):
        """添加语言变更观察者"""
        self.observers.append(callback)

    def set_language(self, lang_code: str):
        """设置当前语言并通知观察者"""
        if lang_code in self.languages:
            self.current_lang = lang_code
            for callback in self.observers:
                callback()

    def get(self, key: str, *args) -> str:
        """获取翻译文本"""
        try:
            text = self.translations[self.current_lang].get(key, key)
            return text.format(*args) if args else text
        except:
            return key

# ====== 核心功能 ======
class AudioCoverRemover:
    @staticmethod
    def remove_cover(file_path: str, output_dir: Optional[str] = None) -> Tuple[bool, str]:
        """Remove audio file cover"""
        try:
            file_path = str(Path(file_path).resolve())
            ext = Path(file_path).suffix.lower()
            
            if output_dir:
                output_path = AudioCoverRemover._get_output_path(file_path, output_dir)
                if not os.path.exists(output_path.parent):
                    os.makedirs(output_path.parent)
                # 先复制文件到输出目录
                import shutil
                shutil.copy2(file_path, output_path)
                file_path = str(output_path)
            
            if ext == '.mp3':
                return AudioCoverRemover._remove_mp3_cover(file_path)
            else:
                return AudioCoverRemover._remove_non_mp3_cover(file_path)
                
        except Exception as e:
            return False, i18n.get('process_error', str(e))

    @staticmethod
    def _get_output_path(original_path: str, output_dir: str) -> Path:
        """获取输出路径"""
        original_path = Path(original_path)
        output_dir = Path(output_dir)
        relative_path = original_path.relative_to(original_path.parent)
        return output_dir / relative_path

    @staticmethod
    def _remove_mp3_cover(file_path: str) -> Tuple[bool, str]:
        """Handle MP3 cover removal"""
        try:
            if not AudioCoverRemover._is_valid_mp3(file_path):
                return False, i18n.get('invalid_mp3')

            audio = MP3(file_path)
            if audio.tags is None:
                return True, i18n.get('no_id3')

            id3 = ID3(file_path)
            apic_frames = id3.getall("APIC")
            if apic_frames:
                id3.delall("APIC")
                id3.save()
                return True, i18n.get('cover_removed')
            return True, i18n.get('no_cover')
            
        except MutagenError as e:
            if "can't sync to MPEG frame" in str(e):
                return False, i18n.get('invalid_mp3')
            return False, i18n.get('id3_error', str(e))

    @staticmethod
    def _remove_non_mp3_cover(file_path: str) -> Tuple[bool, str]:
        """Handle non-MP3 cover removal"""
        try:
            audio = File(file_path)
            if audio is None:
                return False, i18n.get('unsupported_format')

            if not hasattr(audio, 'tags') or audio.tags is None:
                return True, i18n.get('no_metadata')

            ext = Path(file_path).suffix.lower()
            if ext in ('.flac', '.ogg'):
                if hasattr(audio, 'pictures') and len(audio.pictures) > 0:
                    audio.pictures = []
                    audio.save()
                    return True, i18n.get('cover_removed')
                return True, i18n.get('no_cover')
            else:
                audio.tags.clear()
                audio.save()
                return True, i18n.get('metadata_cleared')
                
        except MutagenError as e:
            return False, i18n.get('audio_error', str(e))

    @staticmethod
    def _is_valid_mp3(file_path: str) -> bool:
        """Simple MP3 validation"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(4)
                return len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0
        except:
            return False

class FileProcessor:
    @staticmethod
    def get_audio_files(path: str, recursive: bool = False) -> List[str]:
        """获取音频文件列表"""
        path_obj = Path(path)
        if path_obj.is_file():
            return [str(path_obj)] if path_obj.suffix.lower() in AUDIO_EXTENSIONS else []
        
        if recursive:
            return [str(p) for p in path_obj.rglob('*') if p.suffix.lower() in AUDIO_EXTENSIONS]
        else:
            return [str(p) for p in path_obj.glob('*') if p.suffix.lower() in AUDIO_EXTENSIONS]

# ====== 用户界面 ======
class AudioCoverRemoverApp:
    def __init__(self, master):
        self.master = master
        self._setup_window()
        self._init_ui()
        self._setup_responsive_layout()
        self._init_dnd()
        
        # 注册语言变更观察者
        i18n.add_observer(self._update_ui_text)

    def _setup_window(self):
        """设置主窗口"""
        self._update_window_title()
        self.master.minsize(650, 500)
        self.master.geometry("900x650")
        
        # 设置窗口图标
        self._set_window_icon()
        
        # 设置网格布局权重
        for i in range(6):
            self.master.grid_rowconfigure(i, weight=0)
        self.master.grid_rowconfigure(5, weight=1)  # 日志区域可扩展
        
        for i in range(4):
            self.master.grid_columnconfigure(i, weight=1)

    def _update_window_title(self):
        """更新窗口标题"""
        self.master.title(i18n.get('app_title'))

    def _set_window_icon(self):
        """设置窗口图标"""
        if os.path.exists(ICON_PATH):
            try:
                self.master.iconbitmap(ICON_PATH)
            except:
                pass

    def _init_ui(self):
        """初始化用户界面"""
        # 语言选择
        self._add_language_selector()
        
        # 模式选择
        self.mode = StringVar(value="single")
        
        self.mode_label = ttk.Label(self.master, text=i18n.get('select_mode'))
        self.mode_label.grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        
        self.single_file_radio = ttk.Radiobutton(
            self.master, text=i18n.get('single_file'), 
            variable=self.mode, value="single")
        self.single_file_radio.grid(row=0, column=1, padx=10, pady=10, sticky=tk.W)
        
        self.whole_folder_radio = ttk.Radiobutton(
            self.master, text=i18n.get('whole_folder'), 
            variable=self.mode, value="folder")
        self.whole_folder_radio.grid(row=0, column=2, padx=10, pady=10, sticky=tk.W)

        # 文件路径输入
        self.entry = ttk.Entry(self.master, width=60)
        self.entry.grid(row=1, column=0, columnspan=3, padx=10, pady=5, sticky=tk.EW)
        
        # 拖放提示
        self.dnd_label = ttk.Label(self.master, text=i18n.get('drag_drop'), foreground="gray")
        self.dnd_label.grid(row=2, column=0, columnspan=3, pady=(0, 10))

        # 输出目录
        self.output_dir_var = StringVar()
        ttk.Label(self.master, text=i18n.get('output_dir')).grid(row=3, column=0, padx=10, pady=5, sticky=tk.W)
        self.output_entry = ttk.Entry(self.master, textvariable=self.output_dir_var, width=60)
        self.output_entry.grid(row=3, column=1, columnspan=2, padx=0, pady=5, sticky=tk.EW)
        
        self.browse_button = ttk.Button(
            self.master, text=i18n.get('browse'), 
            command=self._select_output_dir)
        self.browse_button.grid(row=3, column=3, padx=10, pady=5, sticky=tk.W)

        # 递归扫描选项
        self.recursive_var = tk.BooleanVar(value=True)
        self.recursive_check = ttk.Checkbutton(
            self.master, text=i18n.get('scan_subdir'), 
            variable=self.recursive_var)
        self.recursive_check.grid(row=4, column=1, padx=10, pady=5, sticky=tk.W)

        # 操作按钮
        self.select_button = ttk.Button(
            self.master, text=i18n.get('select_file'), 
            command=self._select_path)
        self.select_button.grid(row=4, column=0, padx=10, pady=10, sticky=tk.W)
        
        self.process_button = ttk.Button(
            self.master, text=i18n.get('start_process'), 
            command=self._start_processing)
        self.process_button.grid(row=4, column=2, padx=10, pady=10, sticky=tk.W)
        
        self.help_button = ttk.Button(
            self.master, text=i18n.get('help'),
            command=lambda: webbrowser.open(GITHUB_WIKI_URL))
        self.help_button.grid(row=4, column=3, padx=10, pady=10, sticky=tk.E)

        # 日志区域
        self.log_text = scrolledtext.ScrolledText(
            self.master, width=85, height=20, wrap=tk.WORD)
        self.log_text.grid(row=5, column=0, columnspan=4, padx=10, pady=10, sticky=tk.NSEW)

        # 底部信息
        self._add_footer()

    def _init_dnd(self):
        """初始化拖放支持"""
        try:
            from tkinterdnd2 import TkinterDnD
            if isinstance(self.master, TkinterDnD.Tk):
                self.master.drop_target_register('*')
                self.master.dnd_bind('<<Drop>>', self._handle_drop)
        except ImportError:
            pass  # 如果没有安装tkinterdnd2，则忽略拖放功能

    def _handle_drop(self, event):
        """处理拖放事件"""
        paths = event.data.split('}') if '}' in event.data else event.data.split()
        valid_paths = [p.strip() for p in paths if p.strip() and os.path.exists(p.strip())]
        
        if valid_paths:
            path = valid_paths[0]
            if os.path.isdir(path):
                self.mode.set("folder")
            else:
                self.mode.set("single")
            self.entry.delete(0, tk.END)
            self.entry.insert(0, path)

    def _add_language_selector(self):
        """添加语言选择器"""
        lang_frame = ttk.Frame(self.master)
        lang_frame.grid(row=0, column=3, padx=10, pady=10, sticky=tk.E)
        
        self.lang_var = StringVar(value=i18n.current_lang)
        self.lang_menu = ttk.OptionMenu(
            lang_frame, self.lang_var, i18n.current_lang,
            *[(f"{info['flag']} {info['name']}", code) 
              for code, info in i18n.languages.items()],
            command=lambda lang: i18n.set_language(lang)
        )
        self.lang_menu.pack()

    def _add_footer(self):
        """添加底部信息和按钮"""
        # GitHub按钮
        self._add_github_button()
        
        # 联系方式
        self.contact_label = ttk.Label(
            self.master,
            text=i18n.get('contact'),
            style='Hyperlink.TLabel'
        )
        self.contact_label.grid(row=6, column=1, columnspan=2, pady=(0, 10), sticky=tk.W)
        self.contact_label.bind("<Button-1>", lambda e: webbrowser.open(f"mailto:{AUTHOR_EMAIL}"))

    def _add_github_button(self):
        """添加GitHub按钮"""
        try:
            response = requests.get(GITHUB_ICON_URL, timeout=5)
            response.raise_for_status()
            
            img = Image.open(io.BytesIO(response.content))
            img = img.resize((24, 24), Image.LANCZOS)
            self.github_icon = ImageTk.PhotoImage(img)
            
            self.github_button = ttk.Button(
                self.master,
                text=i18n.get('github'),
                image=self.github_icon,
                compound='left',
                command=lambda: webbrowser.open(GITHUB_PROFILE_URL)
            )
            self.github_button.grid(row=6, column=0, padx=10, pady=(0, 10), sticky=tk.W)
            self.github_button.image = self.github_icon  # 保持引用
        except Exception as e:
            print(f"Failed to load GitHub icon: {e}")

    def _setup_responsive_layout(self):
        """设置响应式布局"""
        for i in range(7):
            self.master.grid_rowconfigure(i, weight=0)
        self.master.grid_rowconfigure(5, weight=1)  # 日志区域可扩展
        
        for i in range(4):
            self.master.grid_columnconfigure(i, weight=1)

    def _update_ui_text(self):
        """更新所有UI文本"""
        self._update_window_title()
        
        # 更新控件文本
        widgets = [
            (self.mode_label, 'select_mode'),
            (self.single_file_radio, 'single_file'),
            (self.whole_folder_radio, 'whole_folder'),
            (self.select_button, 'select_file'),
            (self.process_button, 'start_process'),
            (self.contact_label, 'contact'),
            (self.github_button, 'github'),
            (self.help_button, 'help'),
            (self.dnd_label, 'drag_drop'),
            (self.recursive_check, 'scan_subdir'),
            (self.browse_button, 'browse')
        ]
        
        for widget, key in widgets:
            if hasattr(widget, 'config'):
                widget.config(text=i18n.get(key))
        
        # 更新标签
        for row, key in [(0, 'select_mode'), (3, 'output_dir')]:
            for child in self.master.grid_slaves(row=row, column=0):
                if isinstance(child, ttk.Label):
                    child.config(text=i18n.get(key))

    def _select_output_dir(self):
        """选择输出目录"""
        path = filedialog.askdirectory()
        if path:
            self.output_dir_var.set(path)

    def _select_path(self):
        """选择文件或文件夹路径"""
        if self.mode.get() == "single":
            path = filedialog.askopenfilename(
                filetypes=[(i18n.get('audio_files'), " ".join(f"*{ext}" for ext in AUDIO_EXTENSIONS))]
            )
        else:
            path = filedialog.askdirectory()
        
        if path:
            self.entry.delete(0, tk.END)
            self.entry.insert(0, path)

    def _start_processing(self):
        """开始处理文件"""
        path = self.entry.get().strip()
        if not path:
            messagebox.showwarning(
                i18n.get('warning'),
                i18n.get('no_path')
            )
            return
            
        output_dir = self.output_dir_var.get().strip() or None
        recursive = self.recursive_var.get()
            
        self._log_message(i18n.get('processing'))
        self.master.update()

        if self.mode.get() == "single":
            self._process_single_file(path, output_dir)
        else:
            self._process_folder(path, output_dir, recursive)
            
        messagebox.showinfo(
            i18n.get('complete'),
            i18n.get('process_complete')
        )

    def _process_single_file(self, file_path, output_dir=None):
        """处理单个文件"""
        success, message = AudioCoverRemover.remove_cover(file_path, output_dir)
        status = i18n.get('success') if success else i18n.get('fail')
        self._log_message(f"{status}: {file_path} - {message}")

    def _process_folder(self, folder_path, output_dir=None, recursive=False):
        """处理文件夹中的所有音频文件"""
        count = 0
        file_list = FileProcessor.get_audio_files(folder_path, recursive)
        
        if not file_list:
            self._log_message(i18n.get('no_cover'))
            return
            
        for file_path in file_list:
            self._process_single_file(file_path, output_dir)
            count += 1
                    
        self._log_message("\n" + i18n.get('files_processed', count))

    def _log_message(self, message):
        """记录日志消息"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.master.update()

# ====== 初始化 ======
i18n = I18N()

def main():
    try:
        # 尝试使用tkinterdnd2实现更好的拖放支持
        from tkinterdnd2 import TkinterDnD
        root = TkinterDnD.Tk()
    except ImportError:
        root = tk.Tk()
    
    # 设置主题和样式
    style = ttk.Style()
    style.configure('Hyperlink.TLabel', foreground='blue', font=('Arial', 9, 'underline'))
    
    app = AudioCoverRemoverApp(root)
    
    # 响应窗口大小变化
    root.bind('<Configure>', lambda e: app._setup_responsive_layout())
    
    root.mainloop()

if __name__ == "__main__":
    main()
