import tkinter as tk
from tkinter import filedialog
from datetime import datetime
import customtkinter as ctk
from pathlib import Path
from PIL import Image
from typing import Optional, List
import sys
import os
import re
import threading
from customtkinter import CTkImage

sys.path.append(str(Path(__file__).resolve().parent.parent))
from pipelines.pipeline_manager import PipelineManager

# Light Theme Colors
LIGHT_COLORS = {
    "primary": "#F9FBFD",
    "accent": "#6C63FF",
    "bg": "#FFFFFF",
    "text": "#1C1C1E",
    "secondary": "#E0E6ED",
    "button": "#6C63FF",
    "file_list_bg": "#F5F7FA",
    "file_list_text": "#2C3E50",
    "file_list_hover": "#EDF2F7",
    "title_bar": "#B0B3FF",
}

# Dark Theme Colors
DARK_COLORS = {
    "primary": "#1E1E1E",
    "accent": "#6C63FF",
    "bg": "#121212",
    "text": "#CFD8DC",
    "secondary": "#5D7285",
    "button": "#6C63FF",
    "file_list_bg": "#2D3436",
    "file_list_text": "#E2E8F0",
    "file_list_hover": "#3D4852",
    "title_bar": "#3A3A6C",
}


class ModernWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("light")
        self.current_theme = "light"
        self.colors = LIGHT_COLORS.copy()

        self.title("NebulaAI Chatbot")
        self.geometry("1200x800")
        self.minsize(800, 600)

        self.is_typing = False
        self.chat_history = []
        self.vector_store_ready = False
        self.uploaded_files = []
        self.uploads_dir = Path("uploads")
        self.uploads_dir.mkdir(exist_ok=True)
        self.messages = []

        self.setup_window()
        self.setup_layout()
        self.load_existing_files()
        self.bind("<Control-u>", lambda e: self.handle_upload())
        self.pipeline_manager = PipelineManager()

        # Logo önbelleği ekleyin
        self.cached_logo = self.load_and_cache_logo()

    def load_and_cache_logo(self, size=(60, 60)):
        """Logo yükle ve önbellekte sakla"""
        try:
            logo_image = Image.open("image-modified.png")
            # Daha yüksek çözünürlük için boyutu büyüt
            logo_image = logo_image.resize(size, Image.Resampling.BICUBIC)
            return CTkImage(dark_image=logo_image, size=size)
        except Exception as e:
            print(f"Logo yüklenemedi: {str(e)}")
            return None

    def setup_window(self):
        self.overrideredirect(True)
        self.configure(fg_color=self.colors["bg"])
        self.create_title_bar()

    def update_file_list_colors(self):
        current_theme = ctk.get_appearance_mode().lower()
        colors = LIGHT_COLORS if current_theme == "light" else DARK_COLORS

        self.files_list.configure(fg_color=colors["file_list_bg"])

        for file_frame in self.files_list.winfo_children():
            file_frame.configure(fg_color=colors["file_list_bg"])
            for child in file_frame.winfo_children():
                if isinstance(child, ctk.CTkLabel):
                    child.configure(text_color=colors["file_list_text"])
                elif isinstance(child, ctk.CTkButton):
                    child.configure(
                        fg_color=colors["accent"], hover_color=colors["file_list_hover"]
                    )

    def format_message_text(self, text: str) -> list:
        formatted_segments = []
        paragraphs = text.split("\n\n")  # Paragrafları ayır

        for para_idx, paragraph in enumerate(paragraphs):
            lines = paragraph.split("\n")

            for line_idx, line in enumerate(lines):
                current_pos = 0
                current_line_segments = []

                # Liste işaretleri kontrolü
                if line.strip().startswith(
                    ("•", "→", "-", *[f"{i}." for i in range(1, 10)])
                ):
                    indent = 20  # Liste girinti miktarı
                    list_marker = ""

                    if line.strip()[0].isdigit():  # Numaralı liste
                        num_end = line.find(".")
                        list_marker = line[: num_end + 1] + " "
                        line = line[num_end + 1 :].strip()
                    else:  # Bullet liste
                        if line.strip().startswith("→"):
                            list_marker = "→ "
                        else:
                            list_marker = "• "
                        line = line.strip().lstrip("•→-").strip()

                    current_line_segments.append(
                        {
                            "text": "    " + list_marker,  # Girinti ekle
                            "style": "list_marker",
                            "font": ("Helvetica Neue", 18),
                        }
                    )

                while current_pos < len(line):
                    # Bold için kontrol
                    bold_start = line.find("**", current_pos)
                    if bold_start != -1:
                        bold_end = line.find("**", bold_start + 2)
                        if bold_end != -1:
                            if bold_start > current_pos:
                                current_line_segments.append(
                                    {
                                        "text": line[current_pos:bold_start],
                                        "style": "regular",
                                        "font": ("Helvetica Neue", 18),
                                    }
                                )
                            current_line_segments.append(
                                {
                                    "text": line[bold_start + 2 : bold_end],
                                    "style": "bold",
                                    "font": ("Helvetica Neue", 18, "bold"),
                                }
                            )
                            current_pos = bold_end + 2
                            continue

                    # İtalik için kontrol
                    italic_start = line.find("*", current_pos)
                    if (
                        italic_start != -1
                        and line[italic_start - 1 : italic_start] != "*"
                    ):
                        italic_end = line.find("*", italic_start + 1)
                        if (
                            italic_end != -1
                            and line[italic_end + 1 : italic_end + 2] != "*"
                        ):
                            if italic_start > current_pos:
                                current_line_segments.append(
                                    {
                                        "text": line[current_pos:italic_start],
                                        "style": "regular",
                                        "font": ("Helvetica Neue", 18),
                                    }
                                )
                            current_line_segments.append(
                                {
                                    "text": line[italic_start + 1 : italic_end],
                                    "style": "italic",
                                    "font": ("Helvetica Neue", 18, "italic"),
                                }
                            )
                            current_pos = italic_end + 1
                            continue

                    # Başlık kontrolü
                    if line.startswith("##"):
                        current_line_segments.append(
                            {
                                "text": line[2:],
                                "style": "header",
                                "font": ("Helvetica Neue", 24, "bold"),
                            }
                        )
                        current_pos = len(line)
                        break

                    # Normal metin
                    next_special = float("inf")
                    for marker in ["**", "*"]:
                        pos = line.find(marker, current_pos)
                        if pos != -1:
                            next_special = min(next_special, pos)

                    if next_special == float("inf"):
                        current_line_segments.append(
                            {
                                "text": line[current_pos:],
                                "style": "regular",
                                "font": ("Helvetica Neue", 18),
                            }
                        )
                        break
                    else:
                        current_line_segments.append(
                            {
                                "text": line[current_pos:next_special],
                                "style": "regular",
                                "font": ("Helvetica Neue", 18),
                            }
                        )
                        current_pos = next_special

                # Tüm line segmentlerini ekle
                formatted_segments.extend(current_line_segments)

                # Satır sonlarını sadece aynı paragraftaki sonraki satırlar için ekle
                if line_idx < len(lines) - 1:
                    formatted_segments.append(
                        {
                            "text": "\n",
                            "style": "regular",
                            "font": ("Helvetica Neue", 18),
                        }
                    )

            # Paragraf sonlarını sadece son paragraf değilse ve boş değilse ekle
            if para_idx < len(paragraphs) - 1 and paragraph.strip() != "":
                # Paragraf arasına tek bir satır boşluk ekle
                formatted_segments.append(
                    {
                        "text": "\n\n",
                        "style": "paragraph",
                        "font": ("Helvetica Neue", 18),
                    }
                )

        return formatted_segments

    def split_text_for_formatting(self, text: str) -> list:
        """
        Split text into segments based on markdown formatting
        """
        segments = []
        current_pos = 0

        # Regular expressions for finding markdown elements
        patterns = [
            (r"##\s*[^\n]+", "header"),
            (r"\*\*[^\*]+\*\*", "bold"),
            (r"\*[^\*]+\*", "italic"),
            (r"^\s*-\s(.+)$", "list"),
            (r"^\s*(\d+)\.\s(.+)$", "numbered_list"),
        ]

        while current_pos < len(text):
            match_found = False

            for pattern, style in patterns:
                match = re.match(pattern, text[current_pos:], re.MULTILINE)
                if match:
                    # Add any text before the match
                    if match.start() > 0:
                        segments.append(text[current_pos : current_pos + match.start()])

                    # Add the matched segment
                    segments.append(match.group(0))
                    current_pos += match.end()
                    match_found = True
                    break

            if not match_found:
                # Find next potential markdown element
                next_marker = float("inf")
                for marker in ["##", "**", "*", "\n- ", "\n1. "]:
                    pos = text.find(marker, current_pos)
                    if pos != -1:
                        next_marker = min(next_marker, pos)

                if next_marker == float("inf"):
                    # No more markers, add remaining text
                    segments.append(text[current_pos:])
                    break
                else:
                    # Add text until next marker
                    segments.append(text[current_pos:next_marker])
                    current_pos = next_marker

        return segments

    def refresh_messages(self):
        self.clear_chat()
        for msg in self.messages:
            self.add_message(msg["message"], msg["is_user"], msg["timestamp"])

    def update_theme(self, theme_name: str):
        try:
            self.current_theme = theme_name.lower()
            self.colors = (
                DARK_COLORS.copy()
                if self.current_theme == "dark"
                else LIGHT_COLORS.copy()
            )
            ctk.set_appearance_mode(self.current_theme)

            current_messages = self.messages.copy()
            self.messages = []
            self.clear_chat()
            self.refresh_ui()

            for msg in current_messages:
                self.add_message(
                    msg["message"],
                    msg["is_user"],
                    msg["timestamp"],
                    store_message=False,
                )

            self.messages = current_messages
            self.update_file_list_colors()
        except Exception as e:
            self.show_error("Tema güncellenemedi")

    def refresh_ui(self):
        try:
            self.configure(fg_color=self.colors["bg"])

            if hasattr(self, "title_bar"):
                self.title_bar.configure(fg_color=self.colors["title_bar"])
                for child in self.title_bar.winfo_children():
                    if isinstance(child, ctk.CTkButton):
                        child.configure(
                            fg_color=(
                                self.colors["accent"]
                                if "×" in child._text
                                else self.colors["title_bar"]
                            )
                        )

            if hasattr(self, "sidebar"):
                self.sidebar.configure(fg_color=self.colors["primary"])
                self._update_sidebar_colors(self.sidebar)

            if hasattr(self, "chat_frame"):
                self.chat_frame.configure(fg_color=self.colors["bg"])
            if hasattr(self, "input_container"):
                self.input_container.configure(fg_color=self.colors["bg"])
            if hasattr(self, "input_field"):
                self.input_field.configure(
                    fg_color=self.colors["bg"],
                    border_color=self.colors["accent"],
                    text_color=self.colors["text"],
                )
            if hasattr(self, "send_btn"):
                self.send_btn.configure(
                    fg_color=self.colors["accent"],
                    hover_color=self.darken_color(self.colors["accent"]),
                )

        except Exception as e:
            print(f"UI refresh error: {str(e)}")
            self.show_error("UI öğeleri yenilenemedi")

    def _update_sidebar_colors(self, widget):
        for child in widget.winfo_children():
            if isinstance(child, ctk.CTkButton):
                child.configure(
                    text_color=(
                        "#E0E6ED"
                        if self.current_theme == "dark"
                        else self.colors["text"]
                    ),
                    hover_color=self.colors["accent"],
                )
            elif isinstance(child, ctk.CTkLabel):
                child.configure(
                    text_color=(
                        "#E0E6ED"
                        if self.current_theme == "dark"
                        else self.colors["text"]
                    )
                )

            if isinstance(child, ctk.CTkLabel) and child._text == "v1.0.0":
                child.configure(
                    text_color=(
                        "#E0E6ED"
                        if self.current_theme == "dark"
                        else self.colors["secondary"]
                    )
                )

            if isinstance(child, ctk.CTkScrollableFrame):
                child.configure(fg_color=self.colors["file_list_bg"])
                self._update_sidebar_colors(child)

            if hasattr(child, "winfo_children"):
                self._update_sidebar_colors(child)

    def darken_color(self, color: str, amount: float = 0.2) -> str:
        color = color.lstrip("#")
        rgb = tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))
        darkened = tuple(max(0, int(c * (1 - amount))) for c in rgb)
        return f"#{darkened[0]:02x}{darkened[1]:02x}{darkened[2]:02x}"

    def create_title_bar(self):
        self.title_bar = ctk.CTkFrame(
            self,
            fg_color=self.colors["title_bar"],
            height=26,
            corner_radius=0,
        )
        self.title_bar.pack(fill="x", pady=(0, 5))

        # Add drag bindings specifically to the title bar
        self.title_bar.bind("<B1-Motion>", self.drag_window)
        self.title_bar.bind("<Button-1>", self.get_pos)

        close_btn = ctk.CTkButton(
            self.title_bar,
            text="×",
            width=30,
            fg_color=self.colors["accent"],
            command=self.quit,
            hover_color="#FF6B6B",
        )
        close_btn.pack(side="right", padx=5, pady=5)

        minimize_btn = ctk.CTkButton(
            self.title_bar,
            text="−",
            width=30,
            fg_color=self.colors["title_bar"],
            hover_color="#9BAFD3",
            command=self.iconify,
        )
        minimize_btn.pack(side="right", padx=5, pady=5)

    def setup_layout(self):
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=10, pady=5)

        self.create_sidebar()
        self.create_chat_area()
        self.create_input_area()

    def create_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self.main_container,
            fg_color=self.colors["primary"],
            corner_radius=15,
            width=250,
        )
        self.sidebar.pack(side="left", fill="y", padx=(0, 10))
        self.sidebar.pack_propagate(False)

        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.pack(fill="x", pady=(10, 20), padx=10, anchor="n")

        try:
            logo_image = Image.open("image.jpg")
            logo_image = logo_image.resize((50, 50), Image.LANCZOS)
            logo_photo = CTkImage(dark_image=logo_image, size=(50, 50))
            logo_label = ctk.CTkLabel(brand_frame, image=logo_photo, text="")
            logo_label.pack(side="left", padx=5)
        except Exception as e:
            print(f"Logo yüklenemedi: {str(e)}")

        brand_label = ctk.CTkLabel(
            brand_frame,
            text="NebulaAI",
            font=("Helvetica Neue", 25, "bold"),
            text_color=self.colors["text"],
        )
        brand_label.pack(side="left", padx=5, pady=5)

        nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_frame.pack(fill="x", pady=10)

        nav_items = [
            ("🏠 Ana Sayfa", self.handle_home),
            ("📋 Çeviri", self.handle_translation),
            ("📝 Özet", self.handle_summary),
            ("📊 Analiz", self.handle_analysis),
            ("📜 Geçmiş", self.handle_history),
            ("⚙️ Ayarlar", self.handle_settings),
            ("📤 Yükle", self.handle_upload),
        ]

        for text, command in nav_items:
            nav_btn = ctk.CTkButton(
                nav_frame,
                text=text,
                fg_color="transparent",
                text_color=(
                    "#E2E8F0" if self.current_theme == "dark" else self.colors["text"]
                ),
                hover_color=self.colors["accent"],
                anchor="w",
                height=40,
                font=("Helvetica Neue", 16),
                command=command,
            )
            nav_btn.pack(pady=5, padx=10, fill="x")

        separator = ctk.CTkFrame(
            self.sidebar, height=2, fg_color=self.colors["secondary"]
        )
        separator.pack(fill="x", pady=20, padx=15)

        files_header = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        files_header.pack(fill="x", pady=(0, 10), padx=15)

        files_label = ctk.CTkLabel(
            files_header,
            text="📁 Yüklenen Dosyalar",
            font=("Helvetica Neue", 16, "bold"),
            text_color=(
                "#E2E8F0" if self.current_theme == "dark" else self.colors["text"]
            ),
        )
        files_label.pack(anchor="w")

        self.files_list = ctk.CTkScrollableFrame(
            self.sidebar,
            fg_color=self.colors["file_list_bg"],
            height=200,
            corner_radius=10,
        )
        self.files_list.pack(fill="x", pady=5, padx=10)

        version_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        version_frame.pack(side="bottom", fill="x", pady=15, padx=15)

        version_label = ctk.CTkLabel(
            version_frame,
            text="v1.0.0",
            font=("Helvetica Neue", 12),
            text_color=(
                "#E2E8F0" if self.current_theme == "dark" else self.colors["secondary"]
            ),
        )
        version_label.pack(side="right")

    def handle_translation(self):
        # Placeholder for translation functionality
        self.show_error("Çeviri özelliği yakında eklenecek!")

    def handle_summary(self):
        # Placeholder for summary functionality
        self.show_error("Özet özelliği yakında eklenecek!")

    def handle_analysis(self):
        # Placeholder for analysis functionality
        self.show_error("Analiz özelliği yakında eklenecek!")

    def create_chat_area(self):
        self.chat_frame = ctk.CTkScrollableFrame(
            self.main_container, fg_color=self.colors["bg"], corner_radius=15
        )
        self.chat_frame.pack(side="left", fill="both", expand=True)

        self.show_welcome_message()

    def create_input_area(self):
        self.input_container = ctk.CTkFrame(self, fg_color="transparent", height=90)
        self.input_container.pack(side="bottom", fill="x", pady=(0, 20), padx=(275, 50))
        self.input_container.pack_propagate(False)

        self.input_field = ctk.CTkTextbox(
            self.input_container,
            fg_color="#E0E6ED",
            border_color=self.colors["accent"],
            border_width=2,
            corner_radius=15,
            height=70,
            font=("Helvetica Neue", 16),
        )
        self.input_field.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.send_btn = ctk.CTkButton(
            self.input_container,
            text="→",
            width=50,
            height=50,
            fg_color=self.colors["accent"],
            corner_radius=20,
            command=self.send_message,
            hover_color="#FF6B6B",
        )
        self.send_btn.pack(side="right")

        self.input_field.bind("<Return>", self.handle_return)
        self.input_field.bind("<Shift-Return>", self.handle_shift_return)
        self.input_field.bind("<Control-a>", self.select_input_text)

    def select_input_text(self, event):
        try:
            text = self.input_field.get("1.0", "end-1c").rstrip()
            if not text:
                return "break"

            lines = text.split("\n")
            last_non_empty = len(lines) - 1
            while last_non_empty >= 0 and not lines[last_non_empty].strip():
                last_non_empty -= 1

            if last_non_empty < 0:
                return "break"

            end_line = last_non_empty + 1
            end_char = len(lines[last_non_empty])

            self.input_field.tag_remove("sel", "1.0", "end")
            self.input_field.tag_add("sel", "1.0", f"{end_line}.{end_char}")

            return "break"
        except Exception as e:
            print(f"Selection error: {str(e)}")
            return "break"

    def show_welcome_message(self):
        welcome_frame = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        welcome_frame.pack(fill="x", pady=20, padx=20)

        welcome_text = """
        NebulaAI Chatbot'a Hoş Geldiniz!
        
        Başlamak için:
        1. Yükle düğmesini kullanarak belgelerinizi yükleyin (Ctrl+U)
        2. İşlemin tamamlanmasını bekleyin
        3. Sohbete başlayın!
        
        Desteklenen dosya türleri: .txt, .pdf, .doc, .docx
        """

        welcome_label = ctk.CTkLabel(
            welcome_frame,
            text=welcome_text,
            text_color=self.colors["text"],
            justify="left",
            font=("Helvetica Neue", 16),
        )
        welcome_label.pack()

    def handle_upload(self, event=None):
        if not hasattr(self, "pipeline_manager"):
            self.pipeline_manager = PipelineManager()

        filetypes = (
            ("PDF dosyaları", "*.pdf"),
            ("Metin dosyaları", "*.txt"),
            ("Word dosyaları", "*.doc;*.docx"),
            ("Tüm dosyalar", "*.*"),
        )

        files = filedialog.askopenfilenames(
            title="Yüklenecek belgeleri seçin", filetypes=filetypes
        )

        if not files:
            return

        new_files = []
        for file_path in files:
            try:
                source_path = Path(file_path)
                dest_path = self.uploads_dir / source_path.name

                if not dest_path.exists():
                    from shutil import copy2

                    copy2(str(source_path), str(dest_path))
                    new_files.append(str(dest_path))
                    self.add_file(str(dest_path))
                else:
                    self.show_error(
                        f"{source_path.name} dosyası zaten yüklemeler içinde mevcut"
                    )
            except Exception as e:
                self.show_error(
                    f"{source_path.name} dosyası kopyalanırken hata: {str(e)}"
                )

        if new_files:
            self.add_message("Yeni belgeler işleniyor...", is_user=False)

            self.pipeline_manager.process_files_async(
                files=new_files,
                callback=self.handle_processing_callback,
            )

    def add_file(self, file_path: str, initialize: bool = False) -> bool:
        file_name = Path(file_path).name

        if file_path in self.uploaded_files and not initialize:
            self.show_error("Dosya zaten yüklendi")
            return False

        if not initialize:
            self.uploaded_files.append(file_path)

        file_frame = ctk.CTkFrame(self.files_list, fg_color=self.colors["file_list_bg"])
        file_frame.pack(fill="x", pady=2)

        file_label = ctk.CTkLabel(
            file_frame, text=file_name, text_color=self.colors["file_list_text"]
        )
        file_label.pack(side="left", padx=5)

        return True

    def remove_file(self, file_path: str, file_frame: ctk.CTkFrame):
        self.uploaded_files.remove(file_path)
        file_frame.destroy()

    def load_existing_files(self):
        try:
            for file_path in self.uploads_dir.glob("*.*"):
                if file_path.suffix.lower() in [".pdf", ".txt", ".doc", ".docx"]:
                    self.add_file(str(file_path), initialize=True)

            if self.uploaded_files:
                self.pipeline_manager.process_files_async(
                    files=self.uploaded_files, callback=self.handle_processing_callback
                )

            self.check_vector_store_status()
        except Exception as e:
            self.show_error(f"Mevcut dosyalar yüklenirken hata: {str(e)}")

    def check_vector_store_status(self):
        try:
            vector_store_path = Path("vectorstore")
            self.vector_store_ready = vector_store_path.exists() and any(
                vector_store_path.iterdir()
            )
        except Exception as e:
            self.vector_store_ready = False
            self.show_error(f"Vektör deposu durumu kontrol edilirken hata: {str(e)}")

    def handle_processing_callback(self, msg: str):
        self.add_message(msg, is_user=False)
        self.check_vector_store_status()

    def show_error(self, message: str):
        error_frame = ctk.CTkFrame(self.chat_frame, fg_color=self.colors["accent"])
        error_frame.pack(fill="x", pady=5, padx=20)

        error_label = ctk.CTkLabel(
            error_frame,
            text=f"Hata: {message}",
            text_color="white",
            font=("Helvetica Neue", 18),
        )
        error_label.pack(pady=5, padx=10)

        self.after(3000, error_frame.destroy)

    def handle_home(self):
        self.clear_chat()
        self.show_welcome_message()

    def handle_history(self):
        if self.chat_history:
            history_window = HistoryWindow(self)
            history_window.show_history(self.chat_history)

    def handle_settings(self):
        settings_window = SettingsWindow(self)
        settings_window.show()

    def clear_chat(self):
        for widget in self.chat_frame.winfo_children():
            widget.destroy()

    def add_message(
        self,
        message: str,
        is_user: bool,
        timestamp: Optional[str] = None,
        store_message: bool = True,
    ):
        # Ana mesaj çerçevesi
        msg_frame = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        msg_frame.pack(fill="x", pady=10, padx=20)

        # İçerik çerçevesi
        content_frame = ctk.CTkFrame(msg_frame, fg_color="transparent")
        content_frame.pack(fill="x")

        # Logo ve genişlik hesaplamaları
        logo_width = 60 if not is_user and self.cached_logo else 0
        padding_width = 100  # Kenar boşlukları için
        available_width = self.winfo_width() - padding_width - logo_width
        max_message_width = min(600, available_width)  # Maksimum mesaj genişliği 600px

        # Logo (sadece bot mesajları için)
        if not is_user and self.cached_logo:
            logo_frame = ctk.CTkFrame(
                content_frame, fg_color="transparent", width=logo_width
            )
            logo_frame.pack(side="left", padx=(0, 10))
            logo_frame.pack_propagate(False)

            logo_label = ctk.CTkLabel(logo_frame, image=self.cached_logo, text="")
            logo_label.pack(anchor="n")

        # Mesaj balonu
        bubble_color = self.colors["accent"] if is_user else self.colors["primary"]
        text_color = "white" if is_user else self.colors["text"]

        bubble_frame = ctk.CTkFrame(
            content_frame,
            fg_color=bubble_color,
            corner_radius=15,
        )
        bubble_frame.pack(
            side="right" if is_user else "left", anchor="e" if is_user else "w", padx=5
        )

        # Mesaj içeriği için container
        message_container = ctk.CTkFrame(bubble_frame, fg_color="transparent")
        message_container.pack(padx=15, pady=10)

        # Text segmentlerini işle
        text_segments = self.format_message_text(message)
        current_line_frame = None
        is_list_item = False

        # Her segment için wraplength hesapla
        text_wraplength = max_message_width - 60  # Normal metin için
        list_wraplength = max_message_width - 100  # Liste öğeleri için

        for segment in text_segments:
            if segment["text"] in ["\n", "\n\n"]:
                current_line_frame = None
                continue

            if current_line_frame is None:
                current_line_frame = ctk.CTkFrame(
                    message_container, fg_color="transparent"
                )
                current_line_frame.pack(fill="x", pady=2)
                is_list_item = False

            if segment["style"] == "list_marker":
                is_list_item = True

            # Label oluştur
            label = ctk.CTkLabel(
                current_line_frame,
                text=segment["text"].rstrip(),
                text_color=text_color,
                font=segment["font"],
                justify="left",
                wraplength=list_wraplength if is_list_item else text_wraplength,
            )

            # Liste öğeleri için özel hizalama
            if is_list_item:
                if segment["style"] == "list_marker":
                    label.pack(side="left", padx=(0, 0))
                else:
                    label.pack(side="left", padx=(20, 0), fill="x", expand=True)
            else:
                label.pack(side="left", fill="x", expand=True)

        # Zaman etiketi
        if not timestamp:
            timestamp = datetime.now().strftime("%H:%M")

        time_frame = ctk.CTkFrame(msg_frame, fg_color="transparent", height=20)
        time_frame.pack(fill="x", pady=(2, 0))
        time_frame.pack_propagate(False)

        time_label = ctk.CTkLabel(
            time_frame,
            text=timestamp,
            text_color=self.colors["secondary"],
            font=("Inter", 12),
        )
        time_label.pack(side="right" if is_user else "left")

        # Mesajı kaydet
        if store_message:
            self.chat_history.append(
                {"message": message, "is_user": is_user, "timestamp": timestamp}
            )
            self.messages.append(
                {"message": message, "is_user": is_user, "timestamp": timestamp}
            )

        # En alta kaydır
        self.chat_frame._parent_canvas.yview_moveto(1.0)

    def send_message(self):
        message = self.input_field.get("1.0", "end-1c").strip()
        if not message:
            return

        if not self.vector_store_ready and not message.lower().startswith(
            ("help", "upload")
        ):
            self.show_error("Lütfen önce belgeleri yükleyin!")
            return

        self.input_field.delete("1.0", "end")

        self.add_message(message, is_user=True)

        self.show_typing_indicator()

        self.process_message(message)

    def process_message(self, message: str):
        def query_worker():
            response = self.pipeline_manager.query_documents(message)
            self.after(0, self.remove_typing_indicator)
            self.after(0, lambda: self.add_message(response, is_user=False))

        thread = threading.Thread(target=query_worker)
        thread.daemon = True
        thread.start()

    def show_typing_indicator(self):
        if hasattr(self, "typing_frame"):
            self.typing_frame.destroy()

        self.is_typing = True
        self.typing_frame = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        self.typing_frame.pack(fill="x", pady=5, padx=20)

        if self.cached_logo:
            logo_label = ctk.CTkLabel(
                self.typing_frame, image=self.cached_logo, text=""
            )
            logo_label.pack(side="left", anchor="n", padx=5, pady=(0, 5))

        self.dot_labels = []
        # Create indicator frame
        bubble_frame = ctk.CTkFrame(
            self.typing_frame, fg_color=self.colors["primary"], corner_radius=15
        )
        bubble_frame.pack(side="left", pady=5, padx=10)

        # Create dots container
        self.dots_frame = ctk.CTkFrame(bubble_frame, fg_color="transparent")
        self.dots_frame.pack(padx=10, pady=5)

        # Create three dots
        self.dots = []
        for i in range(3):
            dot = ctk.CTkLabel(
                self.dots_frame,
                text="•",
                font=("Helvetica Neue", 32),
                text_color=self.colors["secondary"],
            )
            dot.pack(side="left", padx=2)
            self.dots.append(dot)

        # Start animation
        self.animate_dots()

    def animate_dots(self):
        if not self.is_typing or not hasattr(self, "dots"):
            return

        # Animation cycle
        if not hasattr(self, "dot_index"):
            self.dot_index = 0

        # Reset all dots to normal color
        for dot in self.dots:
            dot.configure(text_color=self.colors["secondary"])

        # Highlight current dot
        self.dots[self.dot_index].configure(text_color=self.colors["accent"])

        # Move to next dot
        self.dot_index = (self.dot_index + 1) % 3

        # Continue animation if still typing
        if self.is_typing:
            self.after(300, self.animate_dots)

    def remove_typing_indicator(self):
        self.is_typing = False
        if hasattr(self, "typing_frame"):
            self.typing_frame.destroy()
        if hasattr(self, "dot_index"):
            delattr(self, "dot_index")

    def handle_return(self, event):
        if not event.state & 0x1:
            self.send_message()
            return "break"

    def handle_shift_return(self, event):
        return

    def get_pos(self, event):
        self.xwin = event.x
        self.ywin = event.y

    def drag_window(self, event):
        self.geometry(f"+{event.x_root - self.xwin}+{event.y_root - self.ywin}")


class HistoryWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Sohbet Geçmişi")
        self.geometry("600x400")
        self.configure(fg_color=parent.colors["bg"])
        self.history_frame = ctk.CTkScrollableFrame(self)
        self.history_frame.pack(fill="both", expand=True, padx=10, pady=10)

    def show_history(self, history: List[dict]):
        for entry in history:
            msg_frame = ctk.CTkFrame(self.history_frame, fg_color="transparent")
            msg_frame.pack(fill="x", pady=5)

            time_label = ctk.CTkLabel(
                msg_frame, text=entry["timestamp"], font=("Helvetica Neue", 16)
            )
            time_label.pack(side="left", padx=5)

            user_label = ctk.CTkLabel(
                msg_frame,
                text="Sen:" if entry["is_user"] else "Bot:",
                font=("Helvetica Neue", 16, "bold"),
            )
            user_label.pack(side="left", padx=5)

            msg_label = ctk.CTkLabel(msg_frame, text=entry["message"], wraplength=400)
            msg_label.pack(side="left", padx=5)


class SettingsWindow(ctk.CTkToplevel):
    _instance = None

    def __new__(cls, parent):
        if cls._instance is None:
            cls._instance = super(SettingsWindow, cls).__new__(cls)
        return cls._instance

    def __init__(self, parent):
        if hasattr(self, "_initialized") and self._initialized:
            return
        super().__init__(parent)
        self.title("Ayarlar")
        self.geometry("400x300")
        self.attributes("-topmost", True)
        self.parent = parent
        self.configure(fg_color=parent.colors["bg"])
        self.create_settings()
        self._initialized = True

    def create_settings(self):
        theme_frame = ctk.CTkFrame(self, fg_color="transparent")
        theme_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            theme_frame, text="Tema:", font=("Helvetica Neue", 18, "bold")
        ).pack(side="left")

        self.theme_var = ctk.StringVar(value=self.parent.current_theme.capitalize())
        theme_menu = ctk.CTkOptionMenu(
            theme_frame,
            values=["Light", "Dark"],
            command=self.change_theme,
            variable=self.theme_var,
        )
        theme_menu.pack(side="right")

    def change_theme(self, theme: str):
        self.parent.update_theme(theme)
        self.configure(fg_color=self.parent.colors["bg"])
        self.parent.update_file_list_colors()

    def show(self):
        self.deiconify()
        self.lift()

    def destroy(self):
        SettingsWindow._instance = None
        super().destroy()


def main():
    try:
        app = ModernWindow()
        os.makedirs("uploads", exist_ok=True)
        os.makedirs("vectorstore", exist_ok=True)
        app.mainloop()
    except Exception as e:
        print(f"Uygulama başlatılırken hata: {str(e)}")
        raise


if __name__ == "__main__":
    main()
