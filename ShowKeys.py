import tkinter as tk
from tkinter import font
from pynput import mouse, keyboard
import threading
from collections import deque
from PIL import Image
import pystray
import sys  # NEW import
import os   # NEW import

# --- NEW: Helper function to find data files in the .exe ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- Configuration ---
APP_WIDTH = 350
APP_HEIGHT = 60
BG_COLOR = "#282a36"
TRANSParent_COLOR = "#010203"
TEXT_COLOR = "#f8f8f2"
ACCENT_COLOR = "#50fa7b"
SCROLL_COLOR = "#89b4fa"
INACTIVE_BUTTON_COLOR = "#44475a"
FONT_FAMILY = "Segoe UI"
KEY_FONT_SIZE = 12
MOUSE_FONT_SIZE = 11
MAX_KEYS_DISPLAYED = 30
MODIFIER_ORDER = ['Ctrl', 'Alt', 'Shift', '⌘']
BLINK_DURATION_MS = 150
KEY_AREA_PADDING = 15
IDLE_CLEAR_DELAY_MS = 5000
CLEAR_INTERVAL_MS = 150

class KeyCastApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("KeyCast")
        self.root.geometry(f"{APP_WIDTH}x{APP_HEIGHT}+100+100")

        self.root.wm_attributes("-topmost", True)
        self.root.overrideredirect(True)
        self.root.wm_attributes("-transparentcolor", TRANSParent_COLOR)
        self.root.config(bg=TRANSParent_COLOR)

        self.key_font = font.Font(family=FONT_FAMILY, size=KEY_FONT_SIZE, weight="bold")
        self.mouse_font = font.Font(family=FONT_FAMILY, size=MOUSE_FONT_SIZE, weight="bold")
        self.mouse_title_font = font.Font(family=FONT_FAMILY, size=7)

        self.main_frame = tk.Frame(self.root, bg=BG_COLOR, highlightthickness=2, highlightbackground=ACCENT_COLOR)
        self.main_frame.pack(expand=True, fill="both")

        self.key_history = deque(maxlen=MAX_KEYS_DISPLAYED)
        self.mouse_buttons_state = {'LMB': False, 'RMB': False, 'MMB': False}
        self.active_modifiers = set()
        self.idle_timer_id = None
        self.window_visible = True

        self._create_widgets()
        self._setup_bindings()
        self.start_background_tasks()

    def _create_widgets(self):
        mouse_frame = tk.Frame(self.main_frame, bg=BG_COLOR)
        mouse_frame.pack(side="left", padx=10, pady=5, fill="y")
        mouse_title = tk.Label(mouse_frame, text="MOUSE", font=self.mouse_title_font, bg=BG_COLOR, fg=TEXT_COLOR)
        mouse_title.pack(side="top", pady=(0, 2))
        buttons_container = tk.Frame(mouse_frame, bg=BG_COLOR)
        buttons_container.pack(side="top")
        self.mouse_labels = {}
        for btn_name in ['LMB', 'MMB', 'RMB']:
            if btn_name != 'MMB':
                frame = tk.Frame(buttons_container, bg=INACTIVE_BUTTON_COLOR, width=35, height=35)
                frame.pack(side="left", padx=2)
                frame.pack_propagate(False)
                lbl = tk.Label(frame, text=btn_name[0], font=self.mouse_font, bg=INACTIVE_BUTTON_COLOR, fg=TEXT_COLOR)
                lbl.pack(expand=True, fill="both")
                self.mouse_labels[btn_name] = {'frame': frame, 'label': lbl}
            else:
                canvas = tk.Canvas(buttons_container, bg=INACTIVE_BUTTON_COLOR, width=25, height=35, highlightthickness=0)
                canvas.pack(side="left", padx=2)
                wheel = canvas.create_rectangle(8, 5, 18, 30, fill=TEXT_COLOR, outline="")
                scroller = canvas.create_line(13, 8, 13, 14, fill=INACTIVE_BUTTON_COLOR, width=2)
                self.mouse_labels[btn_name] = {'canvas': canvas, 'wheel': wheel, 'scroller': scroller}
        separator = tk.Frame(self.main_frame, bg=ACCENT_COLOR, width=2)
        separator.pack(side="left", fill="y", pady=10)
        self.key_display_label = tk.Label(self.main_frame, text="", font=self.key_font, bg=BG_COLOR, fg=TEXT_COLOR, justify="left", anchor="w", padx=10)
        self.key_display_label.pack(side="left", expand=True, fill="both")

    def _setup_bindings(self):
        self._offset_x = 0
        self._offset_y = 0
        self.bind_all_children(self.main_frame, "<ButtonPress-1>", self.on_drag_start)
        self.bind_all_children(self.main_frame, "<B1-Motion>", self.on_drag_motion)
        self.root.bind("<KeyPress-Escape>", self.quit_app)

    def start_background_tasks(self):
        self.mouse_listener = mouse.Listener(on_click=self.on_click, on_scroll=self.on_scroll)
        self.keyboard_listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        threading.Thread(target=self.mouse_listener.start, daemon=True).start()
        threading.Thread(target=self.keyboard_listener.start, daemon=True).start()
        threading.Thread(target=self._run_tray_icon, daemon=True).start()

    def run(self):
        self.root.mainloop()

    # --- System Tray Methods ---
    def _run_tray_icon(self):
        try:
            # MODIFIED: Use the resource_path helper to find the icon
            icon_path = resource_path("KeyCast.ico")
            image = Image.open(icon_path)
            menu = (
                pystray.MenuItem('Show/Hide', self._toggle_window, default=True),
                pystray.MenuItem('Exit', self.quit_app)
            )
            self.tray_icon = pystray.Icon("KeyCast", image, "KeyCast", menu)
            self.tray_icon.run()
        except FileNotFoundError:
            # This error will now be more accurate
            print(f"Error: Icon file not found at {resource_path('KeyCast.ico')}")
        except Exception as e:
            print(f"An error occurred with the system tray: {e}")

    def _toggle_window(self):
        if self.window_visible:
            self.root.withdraw()
        else:
            self.root.deiconify()
        self.window_visible = not self.window_visible

    # --- Event Handlers ---
    def on_press(self, key):
        self._reset_idle_timer()
        key_str = self._format_key(key)
        if self._is_modifier(key):
            self.active_modifiers.add(key_str)
            return
        sorted_modifiers = sorted(list(self.active_modifiers), key=lambda m: MODIFIER_ORDER.index(m) if m in MODIFIER_ORDER else 99)
        display_str = "+".join(sorted_modifiers + [key_str]) if sorted_modifiers else key_str
        self.key_history.append(display_str)
        self.root.after(0, self._update_key_display)

    def on_release(self, key):
        key_str = self._format_key(key)
        if self._is_modifier(key):
            self.active_modifiers.discard(key_str)

    def on_click(self, x, y, button, pressed):
        try:
            win_x, win_y = self.root.winfo_x(), self.root.winfo_y()
            win_width, win_height = self.root.winfo_width(), self.root.winfo_height()
            is_inside = (win_x <= x < win_x + win_width) and (win_y <= y < win_y + win_height)
            if button == mouse.Button.left and is_inside and pressed:
                return
        except tk.TclError:
            return
        btn_name = {mouse.Button.left: 'LMB', mouse.Button.right: 'RMB', mouse.Button.middle: 'MMB'}.get(button)
        if btn_name:
            self.mouse_buttons_state[btn_name] = pressed
            self.root.after(0, self._update_mouse_display)

    def on_scroll(self, x, y, dx, dy):
        self._reset_idle_timer()
        scroll_dir = "Scroll ↑" if dy > 0 else "Scroll ↓"
        self.key_history.append(scroll_dir)
        self.root.after(0, self._update_key_display)
        self.root.after(0, self._trigger_scroll_blink)

    # --- UI Update & Animation Methods ---
    def _update_key_display(self, trim_to_fit=True):
        if trim_to_fit:
            label_width = self.key_display_label.winfo_width()
            if label_width > 10:
                available_width = label_width - KEY_AREA_PADDING
                while self.key_history and self.key_font.measure("  ".join(self.key_history)) > available_width:
                    self.key_history.popleft()
        self.key_display_label.config(text="  ".join(self.key_history))

    def _reset_idle_timer(self):
        if self.idle_timer_id:
            self.root.after_cancel(self.idle_timer_id)
        self.idle_timer_id = self.root.after(IDLE_CLEAR_DELAY_MS, self._start_idle_clear)

    def _start_idle_clear(self):
        self._clear_one_key()

    def _clear_one_key(self):
        if self.key_history:
            self.key_history.popleft()
            self.root.after(0, self._update_key_display, False)
            self.idle_timer_id = self.root.after(CLEAR_INTERVAL_MS, self._clear_one_key)
        else:
            self.idle_timer_id = None

    def _update_mouse_display(self):
        for btn_name, state in self.mouse_buttons_state.items():
            widgets = self.mouse_labels.get(btn_name)
            if not widgets: continue
            if btn_name == 'MMB':
                canvas, wheel, scroller = widgets['canvas'], widgets['wheel'], widgets['scroller']
                if state:
                    canvas.config(bg=ACCENT_COLOR); canvas.itemconfig(wheel, fill=BG_COLOR); canvas.itemconfig(scroller, fill=ACCENT_COLOR)
                else:
                    canvas.config(bg=INACTIVE_BUTTON_COLOR); canvas.itemconfig(wheel, fill=TEXT_COLOR); canvas.itemconfig(scroller, fill=INACTIVE_BUTTON_COLOR)
            else:
                bg = ACCENT_COLOR if state else INACTIVE_BUTTON_COLOR
                fg = BG_COLOR if state else TEXT_COLOR
                widgets['frame'].config(bg=bg); widgets['label'].config(bg=bg, fg=fg)

    def _trigger_scroll_blink(self):
        widgets = self.mouse_labels.get('MMB')
        if not widgets: return
        canvas, wheel, scroller = widgets['canvas'], widgets['wheel'], widgets['scroller']
        canvas.config(bg=SCROLL_COLOR); canvas.itemconfig(wheel, fill=BG_COLOR); canvas.itemconfig(scroller, fill=SCROLL_COLOR)
        self.root.after(BLINK_DURATION_MS, self._update_mouse_display)

    # --- Utility Methods ---
    def _is_modifier(self, key):
        return hasattr(key, 'name') and any(s in key.name for s in ['shift', 'ctrl', 'alt', 'cmd'])

    def _format_key(self, key):
        if hasattr(key, 'char') and key.char and 1 <= ord(key.char) <= 26: return chr(ord(key.char) + 64)
        try: return key.char.upper() if key.char else '??'
        except AttributeError:
            key_name = str(key).replace("Key.", "")
            mappings = {'space':'␣','enter':'↵','shift':'Shift','ctrl':'Ctrl','alt':'Alt','cmd':'⌘','backspace':'⌫','tab':'⇥','caps_lock':'⇪','esc':'Esc','up':'↑','down':'↓','left':'←','right':'→'}
            for mod in ['shift', 'ctrl', 'alt', 'cmd']:
                if key_name.startswith(mod): return mappings.get(mod, mod.capitalize())
            return mappings.get(key_name, key_name.capitalize())

    # --- Window Management ---
    def on_drag_start(self, event):
        self._offset_x = self.root.winfo_pointerx() - self.root.winfo_x()
        self._offset_y = self.root.winfo_pointery() - self.root.winfo_y()

    def on_drag_motion(self, event):
        x = self.root.winfo_pointerx() - self._offset_x
        y = self.root.winfo_pointery() - self._offset_y
        self.root.geometry(f"+{x}+{y}")
        self.root.update_idletasks()

    def bind_all_children(self, widget, event, callback):
        widget.bind(event, callback)
        for child in widget.winfo_children():
            self.bind_all_children(child, event, callback)

    def quit_app(self, event=None):
        if hasattr(self, 'tray_icon'):
            self.tray_icon.stop()
        self.root.destroy()

if __name__ == "__main__":
    app = KeyCastApp()
    app.run()