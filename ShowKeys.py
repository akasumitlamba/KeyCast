import tkinter as tk
from tkinter import font
from pynput import mouse, keyboard
import threading
from collections import deque
from PIL import Image
import pystray
import sys
import os

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

APP_WIDTH            = 400             # Made application slightly narrower
APP_HEIGHT           = 60              # Made slightly shorter
BG_COLOR             = "#1e2030"
TRANSPARENT_COLOR    = "#010203"
TEXT_COLOR           = "#f8f8f2"
ACCENT_COLOR         = "#50fa7b"       # green border / active mouse buttons
KEY_TEXT_COLOR       = "#50fa7b"       # green for normal keystrokes
SHORTCUT_TEXT_COLOR  = "#89b4fa"       # blue for shortcuts and special keys
SCROLL_COLOR         = "#89b4fa"       # blue blink for scroll
INACTIVE_BTN_COLOR   = "#3b3f54"       # inactive mouse buttons
SEPARATOR_COLOR      = ACCENT_COLOR
FONT_FAMILY          = "Segoe UI"
KEY_FONT_SIZE        = 12              # Smaller general font
KEY_FONT_SIZE_SMALL  = 11              # Even smaller for lowercase letters
MOUSE_FONT_SIZE      = 10
MOUSE_TITLE_FONT_SIZE= 7
MAX_KEYS_DISPLAYED   = 40
MODIFIER_ORDER       = ["Ctrl", "Alt", "Shift", "Win"]
BLINK_DURATION_MS    = 160
KEY_AREA_PADDING     = 18
IDLE_CLEAR_DELAY_MS  = 5000
CLEAR_INTERVAL_MS    = 140

# Modifier icons (Unicode symbols)
MODIFIER_ICONS = {
    "Ctrl":  "⌃",
    "Alt":   "⌥",
    "Shift": "⇧",
    "Win":   "⊞",
}

# Special key display mappings (Icon only)
KEY_MAPPINGS = {
    "space":        "␣",          
    "enter":        "↵",
    "shift":        "⇧",
    "ctrl":         "⌃",
    "alt":          "⌥",
    "cmd":          "⊞",
    "backspace":    "⌫",
    "tab":          "⇥",
    "caps_lock":    "⇪",
    "esc":          "⎋",
    "up":           "↑",
    "down":         "↓",
    "left":         "←",
    "right":        "→",
    "delete":       "⌦",
    "home":         "⇱",
    "end":          "⇲",
    "page_up":      "⇞",
    "page_down":    "⇟",
    "print_screen": "⎙",
    "insert":       "Ins",
    "num_lock":     "NumLk",
    "scroll_lock":  "ScrLk",
    "pause":        "Pause",
    "media_play_pause": "▶",
    "media_next":   "⏭",
    "media_previous": "⏮",
    "media_volume_up": "🔊",
    "media_volume_down": "🔉",
    "media_volume_mute": "🔇",
}


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

class KeyCastApp:

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("KeyCast")
        self.root.geometry(f"{APP_WIDTH}x{APP_HEIGHT}+100+100")
        self.root.wm_attributes("-topmost", True)
        self.root.overrideredirect(True)
        self.root.wm_attributes("-transparentcolor", TRANSPARENT_COLOR)
        self.root.config(bg=TRANSPARENT_COLOR)

        # Fonts
        self.key_font         = font.Font(family=FONT_FAMILY, size=KEY_FONT_SIZE, weight="bold")
        self.key_font_small   = font.Font(family=FONT_FAMILY, size=KEY_FONT_SIZE_SMALL, weight="bold")
        self.mouse_font       = font.Font(family=FONT_FAMILY, size=MOUSE_FONT_SIZE, weight="bold")
        self.mouse_title_font = font.Font(family=FONT_FAMILY, size=MOUSE_TITLE_FONT_SIZE)

        # State
        self.key_history           = deque(maxlen=MAX_KEYS_DISPLAYED)
        self.mouse_buttons_state   = {"LMB": False, "RMB": False, "MMB": False}
        self.active_modifiers      = set()
        self.idle_timer_id         = None
        self.window_visible        = True
        self.tray_icon             = None
        self.caps_lock_on          = False

        self._create_widgets()
        self._setup_bindings()
        self.start_background_tasks()

    # -----------------------------------------------------------------------
    # UI Construction
    # -----------------------------------------------------------------------

    def _create_widgets(self):
        # Outer frame (green border)
        self.main_frame = tk.Frame(
            self.root, bg=BG_COLOR,
            highlightthickness=2, highlightbackground=ACCENT_COLOR
        )
        self.main_frame.pack(expand=True, fill="both")

        # --- Mouse section ---
        mouse_frame = tk.Frame(self.main_frame, bg=BG_COLOR)
        mouse_frame.pack(side="left", padx=(10, 6), pady=5, fill="y")

        mouse_title = tk.Label(
            mouse_frame, text="MOUSE",
            font=self.mouse_title_font, bg=BG_COLOR, fg=TEXT_COLOR
        )
        mouse_title.pack(side="top", pady=(0, 1))

        buttons_row = tk.Frame(mouse_frame, bg=BG_COLOR)
        buttons_row.pack(side="top")

        self.mouse_widgets = {}
        self._build_mouse_button(buttons_row, "LMB", "L")
        self._build_scroll_wheel(buttons_row)
        self._build_mouse_button(buttons_row, "RMB", "R")

        # --- Vertical separator ---
        sep = tk.Frame(self.main_frame, bg=SEPARATOR_COLOR, width=2)
        sep.pack(side="left", fill="y", pady=6, padx=(4, 0))

        # --- Key display area ---
        container = tk.Frame(self.main_frame, bg=BG_COLOR)
        container.pack(side="left", expand=True, fill="both", padx=(8, 8))
        
        self.key_text = tk.Text(
            container, bg=BG_COLOR, bd=0, highlightthickness=0,
            state="disabled", wrap="none", height=1, cursor="arrow"
        )
        self.key_text.pack(side="left", expand=True, fill="both", pady=15)
        
        # Tags for colors and sizes
        self.key_text.tag_configure("shortcut", foreground=SHORTCUT_TEXT_COLOR, font=self.key_font)
        self.key_text.tag_configure("shortcut_small", foreground=SHORTCUT_TEXT_COLOR, font=self.key_font_small)
        self.key_text.tag_configure("normal", foreground=KEY_TEXT_COLOR, font=self.key_font)
        self.key_text.tag_configure("normal_small", foreground=KEY_TEXT_COLOR, font=self.key_font_small)

    def _build_mouse_button(self, parent, btn_id, letter):
        frame = tk.Frame(parent, bg=INACTIVE_BTN_COLOR, width=28, height=32)
        frame.pack(side="left", padx=2)
        frame.pack_propagate(False)

        lbl = tk.Label(
            frame, text=letter,
            font=self.mouse_font, bg=INACTIVE_BTN_COLOR, fg=TEXT_COLOR
        )
        lbl.pack(expand=True, fill="both")

        self.mouse_widgets[btn_id] = {"frame": frame, "label": lbl}

    def _build_scroll_wheel(self, parent):
        canvas = tk.Canvas(
            parent, bg=INACTIVE_BTN_COLOR,
            width=20, height=32, highlightthickness=0
        )
        canvas.pack(side="left", padx=2)

        wheel    = canvas.create_rectangle(3, 2, 18, 30, fill=INACTIVE_BTN_COLOR, outline=TEXT_COLOR, width=1)
        scroll_r = canvas.create_rectangle(8, 6, 13, 16, fill=TEXT_COLOR, outline="")

        self.mouse_widgets["MMB"] = {
            "canvas": canvas,
            "wheel": wheel,
            "scroll_r": scroll_r,
        }

    # -----------------------------------------------------------------------
    # Drag & Bindings
    # -----------------------------------------------------------------------

    def _setup_bindings(self):
        self._offset_x = 0
        self._offset_y = 0
        self._bind_recursive(self.main_frame, "<ButtonPress-1>", self._drag_start)
        self._bind_recursive(self.main_frame, "<B1-Motion>",     self._drag_motion)
        self.root.bind("<KeyPress-Escape>", self.quit_app)

    def _bind_recursive(self, widget, event, callback):
        widget.bind(event, callback)
        for child in widget.winfo_children():
            self._bind_recursive(child, event, callback)

    def _drag_start(self, event):
        self._offset_x = self.root.winfo_pointerx() - self.root.winfo_x()
        self._offset_y = self.root.winfo_pointery() - self.root.winfo_y()

    def _drag_motion(self, event):
        x = self.root.winfo_pointerx() - self._offset_x
        y = self.root.winfo_pointery() - self._offset_y
        self.root.geometry(f"+{x}+{y}")
        self.root.update_idletasks()

    # -----------------------------------------------------------------------
    # Background listeners
    # -----------------------------------------------------------------------

    def start_background_tasks(self):
        self.mouse_listener    = mouse.Listener(on_click=self._on_click, on_scroll=self._on_scroll)
        self.keyboard_listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        threading.Thread(target=self.mouse_listener.start,    daemon=True).start()
        threading.Thread(target=self.keyboard_listener.start, daemon=True).start()
        threading.Thread(target=self._run_tray_icon,           daemon=True).start()

    def _run_tray_icon(self):
        try:
            icon_path = resource_path("icon.ico")
            image = Image.open(icon_path)
            menu = (
                pystray.MenuItem("Show / Hide", self._toggle_window, default=True),
                pystray.MenuItem("Exit",        self.quit_app),
            )
            self.tray_icon = pystray.Icon("KeyCast", image, "KeyCast", menu)
            self.tray_icon.run()
        except FileNotFoundError:
            pass
        except Exception:
            pass

    def _toggle_window(self):
        if self.window_visible:
            self.root.after(0, self.root.withdraw)
        else:
            self.root.after(0, self.root.deiconify)
        self.window_visible = not self.window_visible

    # -----------------------------------------------------------------------
    # Keyboard events
    # -----------------------------------------------------------------------

    def _on_press(self, key):
        self._reset_idle_timer()
        
        is_char = False
        ch = None
        key_str = self._format_key(key)

        if hasattr(key, "char") and key.char is not None:
            ch = key.char
            is_char = True
            
        # Treat Space explicitly as NON-character so it prints blue icon
        if key == keyboard.Key.space or ch == ' ':
            is_char = False
            key_str = "␣"
            ch = None

        if hasattr(key, "name") and key.name == "caps_lock":
            self.caps_lock_on = not self.caps_lock_on

        if self._is_modifier(key):
            if key_str in self.active_modifiers:
                return
            self.active_modifiers.add(key_str)

        ordered_mods = sorted(
            self.active_modifiers,
            key=lambda m: MODIFIER_ORDER.index(m) if m in MODIFIER_ORDER else 99
        )

        has_non_shift_modifier = any(m != "Shift" for m in ordered_mods)
        
        is_mod_only = False
        if ordered_mods and (has_non_shift_modifier or not is_char):
            icon_parts = [MODIFIER_ICONS.get(m, m) for m in ordered_mods]
            if key_str in ordered_mods:
                display = "".join(icon_parts)
                is_mod_only = True
            else:
                final_key = key_str.upper() if is_char else key_str
                display = "".join(icon_parts) + " " + final_key
            
            # Smart replace if the previous item was JUST modifiers and we are now completing a combo
            if not is_mod_only and self.key_history and self.key_history[-1].get("is_mod_only"):
                self.key_history.pop()
                
            self.key_history.append({"text": display, "color": "blue", "font": "normal", "is_mod_only": is_mod_only})
        else:
            if is_char:
                if ch.isalpha() and self.caps_lock_on and "Shift" not in ordered_mods:
                    ch = ch.upper()
                display_text = ch
                font_tag = "small" if ch.islower() else "normal"
                self.key_history.append({"text": display_text, "color": "green", "font": font_tag, "is_mod_only": False})
            else:
                self.key_history.append({"text": key_str, "color": "blue", "font": "normal", "is_mod_only": False})

        self.root.after(0, self._update_key_display)

    def _on_release(self, key):
        key_str = self._format_key(key)
        if self._is_modifier(key):
            self.active_modifiers.discard(key_str)

    # -----------------------------------------------------------------------
    # Mouse events
    # -----------------------------------------------------------------------

    def _on_click(self, x, y, button, pressed):
        try:
            wx, wy   = self.root.winfo_x(), self.root.winfo_y()
            ww, wh   = self.root.winfo_width(), self.root.winfo_height()
            inside   = (wx <= x < wx + ww) and (wy <= y < wy + wh)
            if button == mouse.Button.left and inside and pressed:
                return
        except tk.TclError:
            return

        btn_map = {
            mouse.Button.left:   "LMB",
            mouse.Button.right:  "RMB",
            mouse.Button.middle: "MMB",
        }
        btn_id = btn_map.get(button)
        if btn_id:
            self.mouse_buttons_state[btn_id] = pressed
            self.root.after(0, self._update_mouse_display)

    def _on_scroll(self, x, y, dx, dy):
        self._reset_idle_timer()
        direction = "Scroll ↑" if dy > 0 else "Scroll ↓"
        self.key_history.append({
            "text": direction,
            "color": "blue",
            "font": "normal",
            "is_mod_only": False
        })
        self.root.after(0, self._update_key_display)
        self.root.after(0, self._blink_scroll_wheel)

    # -----------------------------------------------------------------------
    # Display updates
    # -----------------------------------------------------------------------

    def _update_key_display(self, trim=True):
        if trim:
            try:
                avail_w = self.key_text.winfo_width()
                if avail_w > 10:
                    spacing = self.key_font.measure("  ")
                    while self.key_history:
                        # calculate total width
                        total = 0
                        for e in self.key_history:
                            f = self.key_font if e["font"] == "normal" else self.key_font_small
                            total += f.measure(e["text"])
                        total += spacing * max(0, len(self.key_history) - 1)
                        if total <= avail_w:
                            break
                        self.key_history.popleft()
            except tk.TclError:
                pass

        self.key_text.config(state="normal")
        self.key_text.delete("1.0", tk.END)

        for i, entry in enumerate(self.key_history):
            text = entry["text"]
            if i < len(self.key_history) - 1:
                text += "  "
            
            tag = "shortcut" if entry["color"] == "blue" else "normal"
            tag += "_small" if entry["font"] == "small" else ""
            
            self.key_text.insert(tk.END, text, tag)

        self.key_text.config(state="disabled")

    def _update_mouse_display(self):
        for btn_id, active in self.mouse_buttons_state.items():
            w = self.mouse_widgets.get(btn_id)
            if not w:
                continue
            if btn_id == "MMB":
                canvas   = w["canvas"]
                wheel    = w["wheel"]
                scroll_r = w["scroll_r"]
                if active:
                    canvas.config(bg=ACCENT_COLOR)
                    canvas.itemconfig(wheel,    fill=ACCENT_COLOR, outline=BG_COLOR)
                    canvas.itemconfig(scroll_r, fill=BG_COLOR)
                else:
                    canvas.config(bg=INACTIVE_BTN_COLOR)
                    canvas.itemconfig(wheel,    fill=INACTIVE_BTN_COLOR, outline=TEXT_COLOR)
                    canvas.itemconfig(scroll_r, fill=TEXT_COLOR)
            else:
                bg = ACCENT_COLOR      if active else INACTIVE_BTN_COLOR
                fg = BG_COLOR          if active else TEXT_COLOR
                w["frame"].config(bg=bg)
                w["label"].config(bg=bg, fg=fg)

    def _blink_scroll_wheel(self):
        w = self.mouse_widgets.get("MMB")
        if not w:
            return
        canvas   = w["canvas"]
        wheel    = w["wheel"]
        scroll_r = w["scroll_r"]
        canvas.config(bg=SCROLL_COLOR)
        canvas.itemconfig(wheel,    fill=SCROLL_COLOR, outline=BG_COLOR)
        canvas.itemconfig(scroll_r, fill=BG_COLOR)
        self.root.after(BLINK_DURATION_MS, self._update_mouse_display)

    # -----------------------------------------------------------------------
    # Idle clear
    # -----------------------------------------------------------------------

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

    # -----------------------------------------------------------------------
    # Key formatting helpers
    # -----------------------------------------------------------------------

    def _is_modifier(self, key):
        return hasattr(key, "name") and any(
            s in key.name for s in ["shift", "ctrl", "alt", "cmd"]
        )

    def _format_key(self, key):
        if hasattr(key, "char") and key.char and 1 <= ord(key.char) <= 26:
            return chr(ord(key.char) + 64)
        try:
            ch = key.char
            if ch:
                return ch.upper()
            return "??"
        except AttributeError:
            raw = str(key).replace("Key.", "")
            for mod in ["shift", "ctrl", "alt", "cmd"]:
                if raw.lower().startswith(mod):
                    return KEY_MAPPINGS.get(mod, mod.capitalize())
            return KEY_MAPPINGS.get(raw.lower(), raw.capitalize())

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------

    def run(self):
        self.root.mainloop()

    def quit_app(self, event=None):
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        self.root.destroy()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = KeyCastApp()
    app.run()
