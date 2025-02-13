import tkinter as tk
from tkinter import filedialog
from datetime import datetime
import customtkinter as ctk
from pathlib import Path
from PIL import Image, ImageTk
from typing import Optional, Tuple, List
import sys
import os
import re

sys.path.append(str(Path(__file__).resolve().parent.parent))
from pipelines.pipeline_manager import PipelineManager
import threading
from customtkinter import CTkImage


# Updated Color Scheme Inspired by DeepSeek

# Light Theme: Clean and professional with vibrant accents
# Light Theme: Clean and professional with vibrant accents
LIGHT_COLORS = {
    "primary": "#F9FBFD",  # Almost White - clean background
    "accent": "#6C63FF",  # Bright Blue Accent
    "bg": "#FFFFFF",  # Pure White for high contrast areas
    "text": "#1C1C1E",  # Jet Black - crisp, clear text
    "secondary": "#E0E6ED",  # Soft Gray for subtle highlights
    "button": "#6C63FF",  # Bright Blue Buttons
    "file_list_bg": "#F5F7FA",  # Light gray for file list
    "file_list_text": "#2C3E50",  # Dark gray for file names
    "file_list_hover": "#EDF2F7",  # Slightly darker on hover
}

# Dark Theme: Sleek and modern with subtle contrasts
DARK_COLORS = {
    "primary": "#1E1E1E",  # Deep Charcoal - main background
    "accent": "#6C63FF",  # Bright Blue Accent
    "bg": "#121212",  # Deep Black - for high contrast sections
    "text": "#CFD8DC",  # Light Gray - readable text
    "secondary": "#5D7285",  # Muted Slate for subtle elements
    "button": "#6C63FF",  # Bright Blue Buttons
    "file_list_bg": "#2D3436",  # Dark gray for file list
    "file_list_text": "#E2E8F0",  # Light gray for file names
    "file_list_hover": "#3D4852",  # Slightly lighter on hover
}


class ModernWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Set initial theme
        ctk.set_appearance_mode("light")
        self.current_theme = "light"
        self.colors = LIGHT_COLORS.copy()

        # Configure window
        self.title("Modern RAG Chatbot")
        self.geometry("1200x800")
        self.minsize(800, 600)

        # Initialize state
        self.is_typing = False
        self.chat_history = []
        self.vector_store_ready = False
        self.uploaded_files = []
        self.uploads_dir = Path("uploads")
        self.uploads_dir.mkdir(exist_ok=True)  # Ensure uploads directory exists
        self.messages = []  # Store messages here

        # Initialize UI
        self.setup_window()
        self.setup_layout()

        # Load existing files from uploads folder
        self.load_existing_files()

        # Bind keyboard shortcuts
        self.bind("<Control-u>", lambda e: self.handle_upload())
        self.pipeline_manager = PipelineManager()

    def setup_window(self):
        self.overrideredirect(True)
        self.configure(fg_color=self.colors["bg"])
        self.create_title_bar()
        self.bind("<B1-Motion>", self.drag_window)
        self.bind("<Button-1>", self.get_pos)

    def update_file_list_colors(self):
        current_theme = ctk.get_appearance_mode().lower()
        colors = LIGHT_COLORS if current_theme == "light" else DARK_COLORS

        # Dosya listesi arka plan rengini güncelle
        self.files_list.configure(fg_color=colors["file_list_bg"])

        # Dosya öğelerini güncelle
        for file_frame in self.files_list.winfo_children():
            file_frame.configure(fg_color=colors["file_list_bg"])
            for child in file_frame.winfo_children():
                if isinstance(child, ctk.CTkLabel):
                    child.configure(text_color=colors["file_list_text"])
                elif isinstance(child, ctk.CTkButton):
                    child.configure(
                        fg_color=colors["accent"], hover_color=colors["file_list_hover"]
                    )

    # Replace the existing update_theme method
    def format_message_text(self, text: str) -> str:
        """Format message text with proper spacing and markdown-like syntax"""
        # Replace markdown headers
        text = re.sub(r"##\s*([^\n]+)", lambda m: f"\n{m.group(1).upper()}\n", text)

        # Format bold text using asterisks (keep markers for later processing)
        text = re.sub(r"\*\*([^\*]+)\*\*", r"BOLD_START\1BOLD_END", text)

        # Format italic text
        text = re.sub(r"\*([^\*]+)\*", lambda m: f"∙ {m.group(1)}", text)

        # Format lists
        text = re.sub(r"^\s*-\s", "• ", text, flags=re.MULTILINE)
        text = re.sub(
            r"^\s*\d+\.\s", lambda m: f"{m.group()}➤ ", text, flags=re.MULTILINE
        )

        # Add proper spacing around sections
        text = re.sub(r"\n{3,}", "\n\n", text)  # Remove excess newlines

        text = text.rstrip()

        return text

    def refresh_messages(self):
        """Refresh all messages with new theme colors"""
        self.clear_chat()
        for msg in self.messages:
            self.add_message(msg["message"], msg["is_user"], msg["timestamp"])

    def update_theme(self, theme_name: str):
        """Update the color scheme instantly"""
        try:
            self.current_theme = theme_name.lower()
            self.colors = (
                DARK_COLORS.copy()
                if self.current_theme == "dark"
                else LIGHT_COLORS.copy()
            )
            ctk.set_appearance_mode(self.current_theme)

            # Store current messages and clear the list
            current_messages = self.messages.copy()
            self.messages = []  # Clear messages list

            # Clear chat first
            self.clear_chat()

            # Update UI colors
            self.refresh_ui()

            # Re-add messages with new theme colors
            for msg in current_messages:
                self.add_message(
                    msg["message"],
                    msg["is_user"],
                    msg["timestamp"],
                    store_message=False,
                )

            # Restore messages list
            self.messages = current_messages

            # Update file list colors last
            self.update_file_list_colors()
        except Exception as e:
            print(f"Theme update error: {str(e)}")
            self.show_error("Failed to update theme. Please try again.")

    def refresh_ui(self):
        """Refresh all UI elements with new colors"""
        try:
            # Update main window
            self.configure(fg_color=self.colors["bg"])

            # Update title bar
            if hasattr(self, "title_bar"):
                self.title_bar.configure(fg_color=self.colors["primary"])
                for child in self.title_bar.winfo_children():
                    if isinstance(child, ctk.CTkButton):
                        child.configure(
                            fg_color=(
                                self.colors["accent"]
                                if "×" in child._text
                                else self.colors["primary"]
                            )
                        )

            # Update sidebar if it exists
            if hasattr(self, "sidebar"):
                self.sidebar.configure(fg_color=self.colors["primary"])
                for child in self.sidebar.winfo_children():
                    if isinstance(child, ctk.CTkButton):
                        child.configure(
                            text_color=self.colors["text"],
                            hover_color=self.colors["accent"],
                        )

            # Update chat and input areas if they exist
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
            self.show_error("Failed to refresh UI elements")

    def darken_color(self, color: str, amount: float = 0.2) -> str:
        """Simple color darkening for hover effects"""
        color = color.lstrip("#")
        rgb = tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))
        darkened = tuple(max(0, int(c * (1 - amount))) for c in rgb)
        return f"#{darkened[0]:02x}{darkened[1]:02x}{darkened[2]:02x}"

    def create_title_bar(self):
        # Custom title bar
        self.title_bar = ctk.CTkFrame(
            self, fg_color=self.colors["primary"], corner_radius=10
        )
        self.title_bar.pack(fill="x", pady=(0, 5))

        # Title
        title_label = ctk.CTkLabel(
            self.title_bar,
            text="Modern RAG Chatbot",
            text_color=self.colors["text"],
            font=("Inter", 12, "bold"),
        )
        title_label.pack(side="left", padx=10)

        # Window controls
        close_btn = ctk.CTkButton(
            self.title_bar,
            text="×",
            width=40,
            fg_color=self.colors["accent"],
            command=self.quit,
            hover_color="#FF6B6B",  # Darker red on hover
        )
        close_btn.pack(side="right", padx=5, pady=5)

        minimize_btn = ctk.CTkButton(
            self.title_bar,
            text="−",
            width=40,
            fg_color=self.colors["primary"],
            hover_color="#9BAFD3",  # Darker primary on hover
            command=self.iconify,
        )
        minimize_btn.pack(side="right", padx=5, pady=5)

    def setup_layout(self):
        # Main container
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=10, pady=5)

        # Create sidebar
        self.create_sidebar()

        # Create main chat area
        self.create_chat_area()

        # Create input area
        self.create_input_area()

    def create_sidebar(self):
        # Sidebar frame (15% width)
        self.sidebar = ctk.CTkFrame(
            self.main_container,
            fg_color=self.colors["primary"],
            corner_radius=15,
            width=180,
        )
        self.sidebar.pack(side="left", fill="y", padx=(0, 10))

        # Sidebar buttons with commands
        buttons = [
            ("Home", "home", self.handle_home),
            ("History", "history", self.handle_history),
            ("Settings", "settings", self.handle_settings),
            ("Upload", "upload", self.handle_upload),
        ]

        for text, icon, command in buttons:
            btn = ctk.CTkButton(
                self.sidebar,
                text=text,
                fg_color="transparent",
                text_color=self.colors["text"],
                hover_color=self.colors["accent"],
                corner_radius=10,
                command=command,
            )
            btn.pack(pady=5, padx=10, fill="x")

        # Files section
        self.files_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.files_frame.pack(fill="x", pady=10, padx=10)

        files_label = ctk.CTkLabel(
            self.files_frame, text="Uploaded Files", font=("Inter", 12, "bold")
        )
        files_label.pack(fill="x")

        # Scrollable files list
        self.files_list = ctk.CTkScrollableFrame(
            self.files_frame, fg_color=self.colors["file_list_bg"], height=200
        )
        self.files_list.pack(fill="x", pady=5)

        # Profile section at bottom
        self.profile_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.profile_frame.pack(side="bottom", pady=10, padx=10)

        profile_label = ctk.CTkLabel(
            self.profile_frame,
            text="JD",  # User initials
            fg_color=self.colors["accent"],
            corner_radius=20,
            width=40,
            height=40,
        )
        profile_label.pack(side="left", padx=5)

    def create_chat_area(self):
        # Main chat frame (85% width)
        self.chat_frame = ctk.CTkScrollableFrame(
            self.main_container, fg_color=self.colors["bg"], corner_radius=15
        )
        self.chat_frame.pack(side="left", fill="both", expand=True)

        # Welcome message
        self.show_welcome_message()

    def create_input_area(self):
        # Input container
        self.input_container = ctk.CTkFrame(
            self.main_container, fg_color="transparent", height=100
        )
        self.input_container.pack(side="bottom", fill="x", pady=10)

        # Text input with noticeable background color
        self.input_field = ctk.CTkTextbox(
            self.input_container,
            fg_color="#E0E6ED",  # Light gray background for input field
            border_color=self.colors["accent"],  # Accent color for border
            border_width=2,
            corner_radius=15,
            height=80,
        )
        self.input_field.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # Send button
        self.send_btn = ctk.CTkButton(
            self.input_container,
            text="→",
            width=50,
            height=50,
            fg_color=self.colors["accent"],
            corner_radius=25,
            command=self.send_message,
            hover_color="#FF6B6B",  # Darker accent on hover
        )
        self.send_btn.pack(side="right")

        # Bind enter key
        self.input_field.bind("<Return>", self.handle_return)
        self.input_field.bind("<Shift-Return>", self.handle_shift_return)

    def show_welcome_message(self):
        welcome_frame = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        welcome_frame.pack(fill="x", pady=20, padx=20)

        welcome_text = """
        Welcome to the Modern RAG Chatbot!
        
        To get started:
        1. Upload your documents using the Upload button (Ctrl+U)
        2. Wait for processing to complete
        3. Start chatting!
        
        Supported file types: .txt, .pdf, .doc, .docx
        """

        welcome_label = ctk.CTkLabel(
            welcome_frame,
            text=welcome_text,
            text_color=self.colors["text"],
            justify="left",
            font=("Inter", 14),
        )
        welcome_label.pack()

    def handle_upload(self, event=None):
        """Handle file upload with proper checks and user feedback"""
        if not hasattr(self, "pipeline_manager"):
            self.pipeline_manager = PipelineManager()

        filetypes = (
            ("PDF files", "*.pdf"),
            ("Text files", "*.txt"),
            ("Word files", "*.doc;*.docx"),
            ("All files", "*.*"),
        )

        files = filedialog.askopenfilenames(
            title="Select documents to upload", filetypes=filetypes
        )

        if not files:
            return

        # Copy files to uploads directory
        new_files = []
        for file_path in files:
            try:
                source_path = Path(file_path)
                dest_path = self.uploads_dir / source_path.name

                # Copy file to uploads directory if it doesn't exist
                if not dest_path.exists():
                    from shutil import copy2

                    copy2(str(source_path), str(dest_path))
                    new_files.append(str(dest_path))
                    self.add_file(str(dest_path))
                else:
                    self.show_error(
                        f"File {source_path.name} already exists in uploads"
                    )
            except Exception as e:
                self.show_error(f"Error copying file {source_path.name}: {str(e)}")

        if new_files:
            # Show processing message
            self.add_message("Processing new documents...", is_user=False)

            # Process new files without deleting them
            self.pipeline_manager.process_files_async(
                files=new_files,
                callback=lambda msg: self.add_message(msg, is_user=False),
            )

    def add_file(self, file_path: str, initialize: bool = False) -> bool:
        """Add file to UI and tracking list"""
        file_name = Path(file_path).name

        if file_path in self.uploaded_files and not initialize:
            self.show_error("File already uploaded")
            return False

        if not initialize:
            self.uploaded_files.append(file_path)

        # Create file UI element
        file_frame = ctk.CTkFrame(self.files_list, fg_color=self.colors["file_list_bg"])
        file_frame.pack(fill="x", pady=2)

        file_label = ctk.CTkLabel(
            file_frame, text=file_name, text_color=self.colors["file_list_text"]
        )
        file_label.pack(side="left", padx=5)

        return True

    def remove_file(self, file_path: str, file_frame: ctk.CTkFrame):
        """Remove file from UI only (keep file in uploads folder)"""
        self.uploaded_files.remove(file_path)
        file_frame.destroy()

    def load_existing_files(self):
        """Load all existing files from the uploads directory"""
        try:
            for file_path in self.uploads_dir.glob("*.*"):
                if file_path.suffix.lower() in [".pdf", ".txt", ".doc", ".docx"]:
                    self.add_file(str(file_path), initialize=True)

            # Process all files in uploads folder
            if self.uploaded_files:
                self.pipeline_manager.process_files_async(
                    files=self.uploaded_files, callback=self.handle_processing_callback
                )

            # Check if vector store has files
            self.check_vector_store_status()
        except Exception as e:
            self.show_error(f"Error loading existing files: {str(e)}")

    def check_vector_store_status(self):
        """Check if vector store has documents and update status"""
        try:
            vector_store_path = Path("vectorstore")
            # Check if vectorstore directory exists and has files
            self.vector_store_ready = vector_store_path.exists() and any(
                vector_store_path.iterdir()
            )
        except Exception as e:
            self.vector_store_ready = False
            self.show_error(f"Error checking vector store status: {str(e)}")

    def handle_processing_callback(self, msg: str):
        """Handle callback from file processing"""
        self.add_message(msg, is_user=False)
        # Update vector store status after processing
        self.check_vector_store_status()

    def show_error(self, message: str):
        """Show an error message to the user."""
        error_frame = ctk.CTkFrame(self.chat_frame, fg_color=self.colors["accent"])
        error_frame.pack(fill="x", pady=5, padx=20)

        error_label = ctk.CTkLabel(
            error_frame, text=f"Error: {message}", text_color="white"
        )
        error_label.pack(pady=5, padx=10)

        # Auto-remove after 3 seconds
        self.after(3000, error_frame.destroy)

    def handle_home(self):
        """Handle Home button click."""
        self.clear_chat()
        self.show_welcome_message()

    def handle_history(self):
        """Handle History button click."""
        if self.chat_history:
            history_window = HistoryWindow(self)
            history_window.show_history(self.chat_history)

    def handle_settings(self):
        """Handle Settings button click."""
        settings_window = SettingsWindow(self)
        settings_window.show()

    def clear_chat(self):
        """Clear all messages from the chat area."""
        for widget in self.chat_frame.winfo_children():
            widget.destroy()

    def add_message(
        self,
        message: str,
        is_user: bool,
        timestamp: Optional[str] = None,
        store_message: bool = True,
    ):
        """Add a message to the chat area"""
        # Message container
        msg_frame = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        msg_frame.pack(fill="x", pady=5, padx=20)

        # Message content container with better alignment
        content_frame = ctk.CTkFrame(msg_frame, fg_color="transparent")
        content_frame.pack(fill="x", pady=(5, 0))

        if not is_user:  # Only show logo for bot messages
            logo_image = Image.open("image.jpg")
            logo_image = logo_image.resize((45, 45), Image.LANCZOS)
            logo_photo = CTkImage(dark_image=logo_image, size=(45, 45))

            # Logo label with anchor to top
            logo_label = ctk.CTkLabel(content_frame, image=logo_photo, text="")
            logo_label.pack(side="left", anchor="n", padx=5, pady=(0, 5))

        # Message bubble container
        bubble_frame = ctk.CTkFrame(
            content_frame,
            fg_color=self.colors["accent"] if is_user else self.colors["primary"],
            corner_radius=15,
        )
        bubble_frame.pack(side="right" if is_user else "left", pady=5, padx=5)

        formatted_text = self.format_message_text(message)
        parts = re.split(r"(BOLD_START|BOLD_END)", formatted_text)
        bold = False
        current_text = ""

        # Text container inside bubble
        text_container = ctk.CTkFrame(bubble_frame, fg_color="transparent")
        text_container.pack(padx=10, pady=5)

        for part in parts:
            if part == "BOLD_START":
                if (
                    current_text.strip()
                ):  # Only create label if there's non-whitespace text
                    label = ctk.CTkLabel(
                        text_container,
                        text=current_text.rstrip(),  # Remove trailing whitespace
                        text_color="white" if is_user else self.colors["text"],
                        font=("Inter", 14),
                        justify="left",
                        wraplength=500,
                    )
                    label.pack(anchor="w")
                current_text = ""
                bold = True
            elif part == "BOLD_END":
                if (
                    current_text.strip()
                ):  # Only create label if there's non-whitespace text
                    label = ctk.CTkLabel(
                        text_container,
                        text=current_text.rstrip(),  # Remove trailing whitespace
                        text_color="white" if is_user else self.colors["text"],
                        font=("Inter", 14, "bold"),
                        justify="left",
                        wraplength=500,
                    )
                    label.pack(anchor="w")
                current_text = ""
                bold = False
            else:
                current_text += part

        if current_text.strip():  # Only create label if there's non-whitespace text
            label = ctk.CTkLabel(
                text_container,
                text=current_text.rstrip(),  # Remove trailing whitespace
                text_color="white" if is_user else self.colors["text"],
                font=("Inter", 14, "bold" if bold else "normal"),
                justify="left",
                wraplength=500,
            )
            label.pack(anchor="w")

        # Timestamp below the message
        if not timestamp:
            timestamp = datetime.now().strftime("%H:%M")
        time_label = ctk.CTkLabel(
            msg_frame,
            text=timestamp,
            text_color=self.colors["secondary"],
            font=("Inter", 10),
        )
        time_label.pack(side="right" if is_user else "left", pady=(0, 2))

        # Store in history and messages only if store_message is True
        if store_message:
            self.chat_history.append(
                {"message": message, "is_user": is_user, "timestamp": timestamp}
            )
            self.messages.append(
                {"message": message, "is_user": is_user, "timestamp": timestamp}
            )

        # Scroll to bottom
        self.chat_frame._parent_canvas.yview_moveto(1.0)

    def send_message(self):
        """Ensure messages are sent only when the vector store is ready"""
        message = self.input_field.get("1.0", "end-1c").strip()
        if not message:
            return

        if not self.vector_store_ready and not message.lower().startswith(
            ("help", "upload")
        ):
            self.show_error("Please upload documents first!")
            return

        # Clear input
        self.input_field.delete("1.0", "end")

        # Add user message
        self.add_message(message, is_user=True)

        # Show typing indicator
        self.show_typing_indicator()

        # Process message and generate response
        self.process_message(message)

    def process_message(self, message: str):
        """Process user message and generate response using the pipeline."""

        def query_worker():
            # Generate response using pipeline
            response = self.pipeline_manager.query_documents(message)

            # Remove typing indicator and add response
            self.after(0, self.remove_typing_indicator)
            self.after(0, lambda: self.add_message(response, is_user=False))

        # Start query in separate thread
        thread = threading.Thread(target=query_worker)
        thread.daemon = True
        thread.start()

    def show_typing_indicator(self):
        if hasattr(self, "typing_frame"):
            self.typing_frame.destroy()

        self.is_typing = True
        self.typing_frame = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        self.typing_frame.pack(fill="x", pady=5, padx=20)

        # Add logo to typing indicator
        logo_image = Image.open("image.jpg")
        logo_image = logo_image.resize((45, 45), Image.LANCZOS)
        logo_photo = CTkImage(dark_image=logo_image, size=(45, 45))

        # Logo label
        logo_label = ctk.CTkLabel(self.typing_frame, image=logo_photo, text="")
        logo_label.pack(side="left", anchor="n", padx=5, pady=(0, 5))  # Align to top

        # Typing indicator dots
        indicator = ctk.CTkLabel(
            self.typing_frame, text="●●●", text_color=self.colors["secondary"]
        )
        indicator.pack(side="left", pady=5)

    def remove_typing_indicator(self):
        """Remove the typing indicator."""
        if hasattr(self, "typing_frame"):
            self.typing_frame.destroy()
        self.is_typing = False

    def handle_return(self, event):
        """Handle Return key press."""
        if not event.state & 0x1:  # Shift key not pressed
            self.send_message()
            return "break"

    def handle_shift_return(self, event):
        """Handle Shift+Return key press."""
        return  # Allow default behavior (new line)

    def get_pos(self, event):
        """Get initial position for window dragging."""
        self.xwin = event.x
        self.ywin = event.y

    def drag_window(self, event):
        """Handle window dragging."""
        self.geometry(f"+{event.x_root - self.xwin}+{event.y_root - self.ywin}")


class HistoryWindow(ctk.CTkToplevel):
    """Window for displaying chat history."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Chat History")
        self.geometry("600x400")

        # Configure window
        self.configure(fg_color=parent.colors["bg"])

        # Create scrollable frame for history
        self.history_frame = ctk.CTkScrollableFrame(self)
        self.history_frame.pack(fill="both", expand=True, padx=10, pady=10)

    def show_history(self, history: List[dict]):
        """Display chat history."""
        for entry in history:
            # Message container
            msg_frame = ctk.CTkFrame(self.history_frame, fg_color="transparent")
            msg_frame.pack(fill="x", pady=5)

            # Timestamp
            time_label = ctk.CTkLabel(
                msg_frame, text=entry["timestamp"], font=("Inter", 10)
            )
            time_label.pack(side="left", padx=5)

            # User indicator
            user_label = ctk.CTkLabel(
                msg_frame,
                text="You:" if entry["is_user"] else "Bot:",
                font=("Inter", 10, "bold"),
            )
            user_label.pack(side="left", padx=5)

            # Message
            msg_label = ctk.CTkLabel(msg_frame, text=entry["message"], wraplength=400)
            msg_label.pack(side="left", padx=5)


class SettingsWindow(ctk.CTkToplevel):
    """Window for app settings."""

    _instance = None

    def __new__(cls, parent):
        if cls._instance is None:
            cls._instance = super(SettingsWindow, cls).__new__(cls)
        return cls._instance

    def __init__(self, parent):
        if hasattr(self, "_initialized") and self._initialized:
            return
        super().__init__(parent)
        self.title("Settings")
        self.geometry("400x300")
        self.attributes("-topmost", True)
        self.parent = parent

        # Configure window
        self.configure(fg_color=parent.colors["bg"])
        self.create_settings()
        self._initialized = True

    def create_settings(self):
        """Create settings UI."""
        # Theme selection
        theme_frame = ctk.CTkFrame(self, fg_color="transparent")
        theme_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(theme_frame, text="Theme:", font=("Inter", 12, "bold")).pack(
            side="left"
        )

        self.theme_var = ctk.StringVar(value=self.parent.current_theme.capitalize())
        theme_menu = ctk.CTkOptionMenu(
            theme_frame,
            values=["Light", "Dark"],
            command=self.change_theme,
            variable=self.theme_var,
        )
        theme_menu.pack(side="right")

    def change_theme(self, theme: str):
        """Handle theme change."""
        self.parent.update_theme(theme)
        self.configure(fg_color=self.parent.colors["bg"])
        self.parent.update_file_list_colors()  # Corrected function call

    def change_model(self, model: str):
        """Handle model change."""
        # Implement model switching logic here
        pass

    def show(self):
        """Show the settings window."""
        self.deiconify()
        self.lift()

    def destroy(self):
        SettingsWindow._instance = None
        super().destroy()


def main():
    """Initialize and run the chatbot application"""
    try:
        app = ModernWindow()
        # Ensure necessary directories exist
        os.makedirs("uploads", exist_ok=True)
        os.makedirs("vectorstore", exist_ok=True)
        app.mainloop()
    except Exception as e:
        print(f"Error starting application: {str(e)}")
        raise


if __name__ == "__main__":
    main()
