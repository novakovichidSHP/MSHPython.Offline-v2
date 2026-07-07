from __future__ import annotations

import base64
import builtins
import ctypes
import io
import json
import keyword
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
import traceback
import zlib
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
import tokenize

import tkinter.font as tkfont

ROOT_DIR = Path(__file__).resolve().parent.parent
RUNTIME_DIR = ROOT_DIR / '.runtime'
PYTHON_DIR = ROOT_DIR / 'python'


def enable_native_dpi_rendering() -> None:
    if os.name != 'nt':
        return
    try:
        awareness_context = ctypes.c_void_p(-4)  # PER_MONITOR_AWARE_V2
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(awareness_context):
            return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


enable_native_dpi_rendering()


def get_best_font(families: list[str], default: str = 'monospace') -> str:
    try:
        available = set(f.lower() for f in tkfont.families())
    except Exception:
        # Create a temporary hidden root if called too early
        temp_root = tk.Tk()
        temp_root.withdraw()
        available = set(f.lower() for f in tkfont.families())
        temp_root.destroy()
        
    for f in families:
        if f.lower() in available:
            return f
    return default

# Font selection based on OS
try:
    if sys.platform == 'darwin':  # macOS
        MONO_FONT_NAME = get_best_font(['JetBrains Mono', 'Menlo', 'Monaco', 'SF Mono', 'Courier New'], 'Courier')
        UI_FONT_NAME = get_best_font(['Rubik', '.AppleSystemUIFont', 'Helvetica Neue'], '.AppleSystemUIFont')
        UI_FONT_SIZE = 13
    elif os.name == 'nt':  # Windows
        MONO_FONT_NAME = get_best_font(['JetBrains Mono', 'Cascadia Code', 'Consolas', 'Courier New'], 'Courier New')
        UI_FONT_NAME = get_best_font(['Rubik', 'Segoe UI Variable Text', 'Segoe UI Variable', 'Segoe UI'], 'Segoe UI')
        UI_FONT_SIZE = 10
    else:  # Linux
        # libtk is now Xft-capable, so we can use fontconfig names
        MONO_FONT_NAME = get_best_font(['JetBrains Mono', 'DejaVu Sans Mono', 'Ubuntu Mono', 'Liberation Mono'], 'monospace')
        UI_FONT_NAME = get_best_font(['Rubik', 'DejaVu Sans', 'Ubuntu'], 'sans-serif')
        UI_FONT_SIZE = 11
except Exception:
    MONO_FONT_NAME = 'monospace'
    UI_FONT_NAME = 'sans-serif'
    UI_FONT_SIZE = 11

EDITOR_FONT = (MONO_FONT_NAME, 12)
CONSOLE_FONT = (MONO_FONT_NAME, 11)
LINE_NUMBER_FONT = (MONO_FONT_NAME, 10)
INPUT_FONT = (MONO_FONT_NAME, 12)
UI_FONT = (UI_FONT_NAME, UI_FONT_SIZE)
UI_FONT_SMALL = (UI_FONT_NAME, max(UI_FONT_SIZE - 1, 9))
UI_FONT_BUTTON = (UI_FONT_NAME, UI_FONT_SIZE)
UI_FONT_BOLD = (UI_FONT_NAME, UI_FONT_SIZE, 'bold' if os.name == 'nt' or sys.platform == 'darwin' else 'normal')
UI_FONT_TITLE = (UI_FONT_NAME, UI_FONT_SIZE + 1, 'bold' if os.name == 'nt' or sys.platform == 'darwin' else 'normal')

def icon(e: str, t: str) -> str:
    """Returns emoji + text for Windows/Mac, or simple text for Linux"""
    if os.name == 'nt' or sys.platform == 'darwin':
        return f'{e} {t}'
    return t

INPUT_WAIT_EMOJI = '⏳' if os.name == 'nt' else '...'

INPUT_PREFIX = '> '

HIGHLIGHT_DELAY_MS = 200
POLL_DELAY_MS = 50
TURTLE_UI_PUMP_INTERVAL = 0.02
TEMP_AUTOSAVE_DELAY_MS = 500

CONTROL_CURSOR = 'pointinghand' if sys.platform == 'darwin' else 'hand2'

THEMES = {
    'light': {
        'app_bg': '#f5f9ff',
        'ambient_bg': '#d8e9ff',
        'panel_bg': '#ffffff',
        'panel_alt_bg': '#eef4ff',
        'toolbar_bg': '#ffffff',
        'toolbar_alt_bg': '#ecf3ff',
        'border': '#c7d8f2',
        'border_soft': '#d9e6f7',
        'accent': '#1c6bff',
        'accent_dark': '#1558d6',
        'accent_2': '#1ab5d8',
        'menu_bg': '#f6faff',
        'menu_fg': '#0f1f3a',
        'menu_active_bg': '#eaf3ff',
        'menu_active_fg': '#1c6bff',
        'run_bg': '#1c6bff',
        'run_bg_active': '#1558d6',
        'stop_bg': '#e04b4b',
        'stop_bg_active': '#c93636',
        'stop_bg_disabled': '#ffe4e4',
        'stop_fg_disabled': '#a33a3a',
        'editor_bg': '#ffffff',
        'editor_fg': '#0f1f3a',
        'console_bg': '#f7fbff',
        'console_fg': '#0f1f3a',
        'line_number_bg': '#f1f6ff',
        'line_number_fg': '#6f7f97',
        'input_bg': '#ffffff',
        'input_bg_focus': '#f6faff',
        'input_fg': '#0f1f3a',
        'selection_bg': '#cfe2ff',
        'selection_fg': '#0f1f3a',
        'status_fg': '#1c6bff',
        'stderr_fg': '#e04b4b',
        'stdin_fg': '#1a8f5a',
        'muted_fg': '#5b6b84',
        'scrollbar_bg': '#d7e5f8',
        'scrollbar_trough': '#f4f8ff',
        'splitter_grip': '#8fa8ca',
        'check_bg': '#eaf3ff',
        'check_fg': '#0f1f3a',
        'syntax_comment': '#5b6b84',
        'syntax_string': '#df0002',
        'syntax_number': '#3a00dc',
        'syntax_keyword': '#c800a4',
        'syntax_builtin': '#1c6bff',
        'syntax_error': '#e04b4b',
        'execution_line_bg': '#dcf7ff',
        'input_wait_bg': '#1c6bff',
        'input_wait_fg': '#ffffff',
    },
    'dark': {
        'app_bg': '#101b2f',
        'ambient_bg': '#17243a',
        'panel_bg': '#17243a',
        'panel_alt_bg': '#1d2d48',
        'toolbar_bg': '#1d2d48',
        'toolbar_alt_bg': '#16253d',
        'border': '#315078',
        'border_soft': '#243b5d',
        'accent': '#6ea8fe',
        'accent_dark': '#4c8ff1',
        'accent_2': '#55d8ee',
        'menu_bg': '#16253d',
        'menu_fg': '#dce9ff',
        'menu_active_bg': '#1d2d48',
        'menu_active_fg': '#ffffff',
        'run_bg': '#1c6bff',
        'run_bg_active': '#6ea8fe',
        'stop_bg': '#e04b4b',
        'stop_bg_active': '#ff8a7a',
        'stop_bg_disabled': '#442733',
        'stop_fg_disabled': '#d68a8a',
        'editor_bg': '#111d31',
        'editor_fg': '#f5f9ff',
        'console_bg': '#101b2f',
        'console_fg': '#f5f9ff',
        'line_number_bg': '#16253d',
        'line_number_fg': '#7f92b2',
        'input_bg': '#111d31',
        'input_bg_focus': '#16253d',
        'input_fg': '#f5f9ff',
        'selection_bg': '#245fb8',
        'selection_fg': '#ffffff',
        'status_fg': '#6ea8fe',
        'stderr_fg': '#ff8a7a',
        'stdin_fg': '#74d69a',
        'muted_fg': '#9aacbf',
        'scrollbar_bg': '#315078',
        'scrollbar_trough': '#16253d',
        'splitter_grip': '#7892b8',
        'check_bg': '#16253d',
        'check_fg': '#f5f9ff',
        'syntax_comment': '#9aacbf',
        'syntax_string': '#ff9a9a',
        'syntax_number': '#9fb7ff',
        'syntax_keyword': '#ff9eea',
        'syntax_builtin': '#55d8ee',
        'syntax_error': '#ff8a7a',
        'execution_line_bg': '#123d57',
        'input_wait_bg': '#1c6bff',
        'input_wait_fg': '#ffffff',
    },
}


class ToolbarLogo(tk.Label):
    def __init__(self, master, *, theme: dict[str, str]) -> None:
        self.theme = theme
        logo_path = ROOT_DIR / 'app' / 'assets' / 'toolbar_logo@2x.png'
        if not logo_path.exists():
            logo_path = ROOT_DIR / 'app' / 'assets' / 'toolbar_logo.png'
        self._source_image = tk.PhotoImage(file=str(logo_path))
        self._image = (
            self._source_image.subsample(2, 2)
            if self._source_image.width() >= 144 and self._source_image.height() >= 88
            else self._source_image
        )
        super().__init__(
            master,
            image=self._image,
            background=theme['toolbar_bg'],
            borderwidth=0,
        )

    def configure(self, cnf=None, **kw):  # type: ignore[override]
        if cnf:
            kw.update(cnf)
        if 'theme' in kw:
            self.theme = kw.pop('theme')
            kw.setdefault('background', self.theme['toolbar_bg'])
        if kw:
            tk.Label.configure(self, **kw)

    config = configure


class FlowToolbar(tk.Frame):
    _BREAKPOINTS = {'medium': 720, 'wide': 1160}

    def __init__(self, master, *, background: str, border: str) -> None:
        super().__init__(
            master,
            background=background,
            bd=0,
            highlightthickness=1,
            highlightbackground=border,
            highlightcolor=border,
        )
        self._items: list[dict[str, object]] = []
        self._layout_pending = False
        self.bind('<Configure>', lambda _event: self._schedule_layout(), add=True)

    def add(
        self,
        widget: tk.Widget,
        *,
        padx: int = 2,
        pady: int = 5,
        fill_y: bool = False,
        slot: str | None = None,
        rows: dict[str, int] | None = None,
        separator: tk.Widget | None = None,
    ) -> tk.Widget:
        self._items.append({
            'widget': widget,
            'padx': padx,
            'pady': pady,
            'fill_y': fill_y,
            'slot': slot,
            'rows': rows,
            'separator': separator,
            'visible': True,
        })
        widget.bind('<Configure>', lambda _event: self._schedule_layout(), add=True)
        self._schedule_layout()
        return widget

    def show(self, widget: tk.Widget) -> None:
        item = self._find_item(widget)
        if item:
            item['visible'] = True
            self._schedule_layout()

    def hide(self, widget: tk.Widget) -> None:
        item = self._find_item(widget)
        if item:
            item['visible'] = False
            widget.place_forget()
            self._schedule_layout()

    def _find_item(self, widget: tk.Widget) -> dict[str, object] | None:
        for item in self._items:
            if item['widget'] is widget:
                return item
        return None

    def _schedule_layout(self) -> None:
        if self._layout_pending:
            return
        self._layout_pending = True
        self.after_idle(self._layout_items)

    def _layout_items(self) -> None:
        self._layout_pending = False
        width = max(self.winfo_width(), 1)
        entries: list[dict[str, object]] = []
        for item in self._items:
            widget = item['widget']
            if not item['visible']:
                continue
            padx = int(item['padx'])
            pady = int(item['pady'])
            item_width = widget.winfo_reqwidth() + padx * 2
            item_height = widget.winfo_reqheight() + pady * 2
            entries.append({
                'item': item,
                'width': item_width,
                'height': item_height,
            })
        if any(entry['item'].get('rows') for entry in entries):
            rows = self._layout_breakpoint_rows(entries, width)
        elif any(entry['item'].get('slot') for entry in entries):
            rows = self._layout_media_rows(entries, width)
        else:
            rows = self._layout_wrapped_rows(entries, width)

        y = 0
        for row in rows:
            row_width = int(row['width'])
            x = max(0, (width - row_width) // 2)
            row_height = int(row['height'])
            for index, entry in enumerate(row['items']):
                item = entry['item']
                widget = item['widget']
                padx = int(item['padx'])
                pady = int(item['pady'])
                item_height = int(entry['height'])
                separator = item.get('separator')
                if isinstance(separator, tk.Widget):
                    if index == 0:
                        separator.pack_forget()
                    elif not separator.winfo_ismapped():
                        separator.pack(side='left', fill='y', padx=(0, 10), pady=4)
                place_args = {'x': x + padx, 'y': y + (row_height - item_height) // 2 + pady}
                if item.get('fill_y'):
                    place_args['height'] = max(1, row_height - pady * 2)
                widget.place(**place_args)
                x += int(entry['width'])
            y += row_height

        self.configure(height=max(y, 1))

    def _layout_wrapped_rows(
        self, entries: list[dict[str, object]], width: int
    ) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        current_row: list[dict[str, object]] = []
        current_width = 0
        current_height = 0
        for entry in entries:
            item_width = int(entry['width'])
            item_height = int(entry['height'])
            if current_row and current_width + item_width > width:
                rows.append({'items': current_row, 'width': current_width, 'height': current_height})
                current_row = []
                current_width = 0
                current_height = 0
            current_row.append(entry)
            current_width += item_width
            current_height = max(current_height, item_height)
        if current_row:
            rows.append({'items': current_row, 'width': current_width, 'height': current_height})
        return rows

    def _layout_breakpoint_rows(
        self, entries: list[dict[str, object]], width: int
    ) -> list[dict[str, object]]:
        mode = self._mode_for_width(width)
        rows_by_index: dict[int, list[dict[str, object]]] = {}
        for entry in entries:
            item = entry['item']
            rows = item.get('rows')
            if isinstance(rows, dict):
                row_index = int(rows.get(mode, rows.get('wide', 0)))
            else:
                row_index = 0
            rows_by_index.setdefault(row_index, []).append(entry)
        return [self._fixed_row(rows_by_index[index]) for index in sorted(rows_by_index)]

    def _layout_media_rows(
        self, entries: list[dict[str, object]], width: int
    ) -> list[dict[str, object]]:
        if width >= self._BREAKPOINTS['wide']:
            slot_rows = (('brand', 'file', 'tab', 'menu', 'temp'),)
        elif width >= self._BREAKPOINTS['medium']:
            slot_rows = (
                ('brand', 'file'),
                ('tab', 'menu', 'temp'),
            )
        else:
            slot_rows = (
                ('brand',),
                ('file',),
                ('tab', 'menu', 'temp'),
            )

        used: set[int] = set()
        rows: list[dict[str, object]] = []
        for slots in slot_rows:
            row_entries = [
                entry for entry in entries
                if entry['item'].get('slot') in slots and id(entry) not in used
            ]
            used.update(id(entry) for entry in row_entries)
            if row_entries:
                rows.append(self._fixed_row(row_entries))
        remaining = [entry for entry in entries if id(entry) not in used]
        if remaining:
            rows.append(self._fixed_row(remaining))
        return rows

    def _fixed_row(self, entries: list[dict[str, object]]) -> dict[str, object]:
        return {
            'items': entries,
            'width': sum(int(entry['width']) for entry in entries),
            'height': max((int(entry['height']) for entry in entries), default=1),
        }

    def _mode_for_width(self, width: int) -> str:
        if width >= self._BREAKPOINTS['wide']:
            return 'wide'
        if width >= self._BREAKPOINTS['medium']:
            return 'medium'
        return 'narrow'


class AppButton(tk.Canvas):
    """A small Tk button with the same command/state surface as ttk.Button."""

    def __init__(
        self,
        master,
        *,
        text: str,
        command=None,
        variant: str = 'default',
        theme: dict[str, str],
        font=UI_FONT_BUTTON,
        padx: int = 10,
        pady: int = 7,
        min_width: int = 0,
        frame_style: str = 'full',
    ) -> None:
        self.command = command
        self.variant = variant
        self.theme = theme
        self.frame_style = frame_style
        self._font = font
        self._state = 'normal'
        self._hover = False
        self._padx = padx
        self._pady = pady
        self._min_width = min_width
        self._text = text
        self._font_obj = tkfont.Font(font=font)
        self._width = 1
        self._height = 1
        super().__init__(
            master,
            bd=0,
            highlightthickness=0,
            takefocus=1,
        )
        self.bind('<Button-1>', self._on_click)
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind('<Return>', self._on_click)
        self.bind('<space>', self._on_click)
        self._resize_to_text()
        self._apply_colors()

    def _parent_bg(self) -> str:
        try:
            return self.master.cget('background')  # type: ignore[union-attr]
        except Exception:
            return self.theme['toolbar_bg']

    def _resize_to_text(self) -> None:
        self._font_obj = tkfont.Font(font=self._font)
        self._width = max(self._min_width, self._font_obj.measure(self._text) + self._padx * 2)
        self._height = self._font_obj.metrics('linespace') + self._pady * 2
        tk.Canvas.configure(self, width=self._width, height=self._height)

    def _rounded_rect(self, x1: int, y1: int, x2: int, y2: int, radius: int, *, fill: str, outline: str) -> None:
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]
        self.create_polygon(points, smooth=True, fill=fill, outline=outline)

    def _colors(self) -> tuple[str, str, str]:
        theme = self.theme
        if self._state == 'disabled':
            return theme['toolbar_alt_bg'], theme['line_number_fg'], theme['toolbar_alt_bg']
        if self.variant == 'primary':
            return theme['accent_dark'] if self._hover else theme['accent'], '#ffffff', theme['accent_dark']
        if self.variant == 'danger':
            return theme['stop_bg_active'] if self._hover else theme['stop_bg'], '#ffffff', theme['stop_bg_active']
        if self.variant == 'ghost':
            bg = theme['panel_alt_bg'] if self._hover else self._parent_bg()
            fg = theme['accent'] if self._hover else theme['editor_fg']
            return bg, fg, theme['accent'] if self._hover else theme['border']
        bg = theme['panel_alt_bg'] if self._hover else self._parent_bg()
        fg = theme['accent'] if self._hover else theme['editor_fg']
        return bg, fg, theme['accent'] if self._hover else theme['border_soft']

    def _apply_colors(self) -> None:
        bg, fg, border = self._colors()
        cursor = '' if self._state == 'disabled' else CONTROL_CURSOR
        tk.Canvas.configure(self, background=self._parent_bg(), cursor=cursor)
        self.delete('all')
        if self.frame_style == 'underline':
            self._rounded_rect(2, 2, self._width - 2, self._height - 2, 8, fill=bg, outline=bg)
            line = self.theme['line_number_fg'] if self._state == 'disabled' else (
                border if border != bg else self.theme['border']
            )
            self.create_line(9, self._height - 5, self._width - 9, self._height - 5, fill=line, width=2)
        else:
            self._rounded_rect(2, 2, self._width - 2, self._height - 2, 8, fill=bg, outline=border)
        self.create_text(
            self._width // 2,
            self._height // 2,
            text=self._text,
            font=self._font,
            fill=fg,
        )

    def _on_enter(self, _event=None) -> None:
        self._hover = True
        self._apply_colors()

    def _on_leave(self, _event=None) -> None:
        self._hover = False
        self._apply_colors()

    def _on_click(self, _event=None) -> str | None:
        if self._state == 'disabled':
            return 'break'
        if self.command:
            self.command()
        return 'break'

    def configure(self, cnf=None, **kw):  # type: ignore[override]
        if cnf:
            kw.update(cnf)
        if 'text' in kw:
            self._text = kw.pop('text')
            self._resize_to_text()
        if 'command' in kw:
            self.command = kw.pop('command')
        if 'state' in kw:
            self._state = kw.pop('state')
        if 'theme' in kw:
            self.theme = kw.pop('theme')
        if 'variant' in kw:
            self.variant = kw.pop('variant')
        if 'frame_style' in kw:
            self.frame_style = kw.pop('frame_style')
        if kw:
            tk.Canvas.configure(self, **kw)
        self._apply_colors()

    config = configure

    def cget(self, key):  # type: ignore[override]
        if key == 'text':
            return self._text
        if key == 'state':
            return self._state
        if key == 'frame_style':
            return self.frame_style
        return super().cget(key)

    def state(self, states=None):
        if not states:
            return ('disabled',) if self._state == 'disabled' else ()
        for state in states:
            if state == 'disabled':
                self._state = 'disabled'
            elif state == '!disabled':
                self._state = 'normal'
        self._apply_colors()
        return self.state()


def read_text_file(path: Path) -> str:
    for encoding in ('utf-8', 'utf-8-sig', 'cp1251', 'latin-1'):
        try:
            return path.read_text(encoding=encoding)
        except Exception:
            continue
    return path.read_text(errors='replace')


def find_python_in_dir(base_dir: Path) -> Path | None:
    if os.name == 'nt':
        names = ['python.exe']
        patterns = ['python-*/python.exe', 'WPy*/python-*/python.exe']
        search_name = 'python.exe'
    else:
        names = ['python3', 'python']
        patterns = [
            'python-*/bin/python3',
            'python-*/bin/python',
            '*/bin/python3',
            '*/bin/python',
        ]
        search_name = 'python3'

    for name in names:
        direct = base_dir / name
        if direct.exists():
            return direct

    for pattern in patterns:
        for candidate in base_dir.glob(pattern):
            if candidate.exists():
                return candidate

    candidates = [p for p in base_dir.rglob(search_name) if p.is_file()]
    if os.name != 'nt':
        candidates.extend([p for p in base_dir.rglob('python') if p.is_file()])
    if not candidates:
        return None
    return sorted(candidates, key=lambda path: len(str(path)))[0]


def get_python_executable() -> str | None:
    env_path = os.environ.get('PYTHON_PORTABLE')
    if env_path and Path(env_path).exists():
        return env_path
    candidate = find_python_in_dir(PYTHON_DIR)
    if candidate:
        return str(candidate)
    return None


class EditorTab:
    def __init__(self, app: 'PortableIDE', path: Path | None = None) -> None:
        self.app = app
        self.path = path
        self.virtual_name: str | None = None
        self.modified = False
        self.highlight_job = None
        self.line_job = None
        self.autosave_job = None
        self.temp_name: str | None = None

        self.frame = ttk.Frame(app.notebook, style='Editor.TFrame')
        self.line_numbers = tk.Canvas(
            self.frame,
            width=48,
            highlightthickness=0,
            bd=0,
        )
        self.line_numbers.pack(side='left', fill='y')

        self.text = tk.Text(
            self.frame,
            wrap='none',
            undo=True,
            font=EDITOR_FONT,
            tabs=('1c',),
        )
        self.text.pack(fill='both', expand=True, side='left')

        self.y_scroll = ttk.Scrollbar(self.frame, orient='vertical', command=self._on_text_scroll)
        self.text.configure(yscrollcommand=self._on_text_yscroll)
        self.y_scroll.pack(fill='y', side='right')

        self.text.bind('<<Modified>>', self.on_modified)
        self.text.bind('<KeyRelease>', self.on_key_release)
        self.text.bind('<MouseWheel>', self.on_scroll_event)
        self.text.bind('<Button-4>', self.on_scroll_event)
        self.text.bind('<Button-5>', self.on_scroll_event)
        self.text.bind('<Configure>', self.on_scroll_event)
        self.text.bind('<Tab>', lambda e: self.app._indent_or_tab(self.text))
        self.text.bind('<Return>', lambda e: self.app._newline_and_indent(self.text))

        self.app.bind_text_shortcuts(self.text)
        self.apply_theme()
        self._update_line_numbers()

    def apply_theme(self) -> None:
        theme = self.app.theme
        self.line_numbers.configure(background=theme['line_number_bg'], highlightthickness=0, bd=0)
        self.text.configure(
            background=theme['editor_bg'],
            foreground=theme['editor_fg'],
            insertbackground=theme['editor_fg'],
            selectbackground=theme['selection_bg'],
            selectforeground=theme['selection_fg'],
            relief='flat',
            borderwidth=0,
            highlightthickness=0,
            padx=12,
            pady=12,
        )
        self._setup_tags()
        self._update_line_numbers()

    def _setup_tags(self) -> None:
        theme = self.app.theme
        self.text.tag_configure('comment', foreground=theme['syntax_comment'])
        self.text.tag_configure('string', foreground=theme['syntax_string'])
        self.text.tag_configure('number', foreground=theme['syntax_number'])
        self.text.tag_configure('keyword', foreground=theme['syntax_keyword'], font=(MONO_FONT_NAME, 12, 'bold'))
        self.text.tag_configure('builtin', foreground=theme['syntax_builtin'])
        self.text.tag_configure('error', foreground=theme['syntax_error'])
        self.text.tag_configure('execution_line', background=theme['execution_line_bg'])

    def on_modified(self, _event=None) -> None:
        if self.text.edit_modified():
            self.modified = True
            self.app.update_tab_title(self)
            self.text.edit_modified(False)
            self.schedule_highlight()
            self.schedule_line_numbers()
            self.app.on_tab_modified(self)

    def on_key_release(self, _event=None) -> None:
        self.schedule_highlight()
        self.schedule_line_numbers()

    def on_scroll_event(self, _event=None) -> None:
        self.schedule_line_numbers()

    def schedule_line_numbers(self) -> None:
        if self.line_job is not None:
            self.text.after_cancel(self.line_job)
        self.line_job = self.text.after(30, self._update_line_numbers)

    def _on_text_yscroll(self, first: str, last: str) -> None:
        self.y_scroll.set(first, last)
        self._update_line_numbers()

    def _on_text_scroll(self, *args) -> None:
        self.text.yview(*args)
        self._update_line_numbers()

    def _update_line_numbers(self) -> None:
        self.line_job = None
        self.line_numbers.delete('all')
        line = self.text.index('@0,0')
        theme = self.app.theme
        while True:
            dline = self.text.dlineinfo(line)
            if dline is None:
                break
            y = dline[1]
            line_number = str(line).split('.')[0]
            self.line_numbers.create_text(
                4,
                y,
                anchor='nw',
                text=line_number,
                fill=theme['line_number_fg'],
                font=LINE_NUMBER_FONT,
            )
            line = self.text.index(f'{line}+1line')

    def schedule_highlight(self) -> None:
        if self.highlight_job is not None:
            self.text.after_cancel(self.highlight_job)
        self.highlight_job = self.text.after(HIGHLIGHT_DELAY_MS, self.apply_highlight)

    def apply_highlight(self) -> None:
        self.highlight_job = None
        code = self.text.get('1.0', 'end-1c')
        for tag in ('comment', 'string', 'number', 'keyword', 'builtin', 'error'):
            self.text.tag_remove(tag, '1.0', 'end')

        if not code.strip():
            return

        try:
            tokens = tokenize.generate_tokens(io.StringIO(code).readline)
            for token_type, token_string, start, end, _line in tokens:
                start_index = f"{start[0]}.{start[1]}"
                end_index = f"{end[0]}.{end[1]}"
                if token_type == tokenize.COMMENT:
                    self.text.tag_add('comment', start_index, end_index)
                elif token_type == tokenize.STRING:
                    self.text.tag_add('string', start_index, end_index)
                elif token_type == tokenize.NUMBER:
                    self.text.tag_add('number', start_index, end_index)
                elif token_type == tokenize.NAME:
                    if token_string in keyword.kwlist:
                        self.text.tag_add('keyword', start_index, end_index)
                    elif token_string in dir(builtins):
                        self.text.tag_add('builtin', start_index, end_index)
        except Exception:
            self.text.tag_add('error', '1.0', 'end')
            return

    def set_content(self, content: str) -> None:
        self.text.delete('1.0', 'end')
        self.text.insert('1.0', content)
        self.text.edit_modified(False)
        self.modified = False
        self.apply_highlight()
        self._update_line_numbers()

    def get_content(self) -> str:
        return self.text.get('1.0', 'end-1c')


class PortableIDE(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self._sync_tk_scaling()
        self.title('МШПайтон.Оффлайн')
        self.geometry('1100x700')
        # Fixed turtle canvas size: 400x400 + padding + borders
        # Minimum window size to accommodate this
        self.minsize(820, 700)
        self.after_idle(self._maximize_window)
        self._icon_image = None
        self._set_app_icon()

        self.process: subprocess.Popen[str] | None = None
        self.output_queue: queue.Queue[tuple[str, str | None, subprocess.Popen[str]]] = queue.Queue()
        self.input_queue: queue.Queue[str] = queue.Queue()
        self.dark_mode = tk.BooleanVar(value=False)
        self.save_on_run_preference: bool | None = None
        self.turtle_screen = None
        self.turtle_visible = False
        self.turtle_running = False
        self.turtle_abort = False
        self.inline_running = False
        self.step_mode = False
        self.step_abort = False
        self.step_event = threading.Event()
        self._turtle_custom_coords = False
        self._turtle_setworld = None
        self._turtle_initialized = False
        self._closing = False
        self._restart_pending = False
        self._silenced_procs: set[subprocess.Popen[str]] = set()
        self._main_created = False
        self._module_counter = 0
        self.save_before_run_var = tk.StringVar(value='ask')
        self.main_tab: EditorTab | None = None
        self.temp_session_dir = RUNTIME_DIR / 'session'
        self.temp_assets: set[str] = set()
        self._waiting_for_input = False
        self.temp_mode_label: tk.Label | None = None
        self.brand_logo_label: ToolbarLogo | None = None
        self.brand_label: tk.Label | None = None
        self.temp_import_button: AppButton | None = None
        self.temp_show_images_button: AppButton | None = None
        self.temp_button_group: tk.Frame | None = None
        self.step_next_button: AppButton | None = None
        self._app_buttons: list[AppButton] = []
        self._toolbar_menus: list[tk.Menu] = []
        self._toolbar_groups: list[tk.Frame] = []
        self._paned_widgets: list[tk.PanedWindow] = []
        self._sash_grips: list[dict[str, object]] = []

        self.theme = THEMES['dark' if self.dark_mode.get() else 'light']

        self._apply_style()
        self._build_ui()
        self._bind_shortcuts()
        self.after(POLL_DELAY_MS, self._poll_output)

        self.new_tab()
        self.after_idle(self._set_initial_pane_layout)
        self.after(250, self._update_sash_grips)
        self.after(750, self._update_sash_grips)
        self.after(100, self._focus_editor)

    def _sync_tk_scaling(self) -> None:
        try:
            self.tk.call('tk', 'scaling', self.winfo_fpixels('1i') / 72.0)
        except Exception:
            pass

    def _maximize_window(self) -> None:
        try:
            self.state('zoomed')
            return
        except tk.TclError:
            pass
        try:
            width = self.winfo_screenwidth()
            height = self.winfo_screenheight()
            self.geometry(f'{width}x{height}+0+0')
        except tk.TclError:
            pass

    def _set_app_icon(self) -> None:
        icon_path = ROOT_DIR / 'app' / 'assets' / 'logo.png'
        if not icon_path.exists():
            return
        try:
            self._icon_image = tk.PhotoImage(file=str(icon_path))
            self.iconphoto(True, self._icon_image)
        except Exception:
            self._icon_image = None

    def _apply_style(self) -> None:
        style = ttk.Style(self)
        try:
            if sys.platform.startswith('linux'):
                style.theme_use('alt')
            else:
                style.theme_use('clam')
        except Exception:
            pass

        theme = self.theme
        self.configure(background=theme['app_bg'])
        style.configure('.', font=UI_FONT)
        style.configure('TFrame', background=theme['app_bg'])
        style.configure('Editor.TFrame', background=theme['panel_bg'], borderwidth=1, relief='solid')
        style.configure('Toolbar.TFrame', background=theme['toolbar_bg'])
        style.configure('Runbar.TFrame', background=theme['toolbar_alt_bg'])
        style.configure('TLabel', background=theme['app_bg'], foreground=theme['editor_fg'], font=UI_FONT)
        style.configure('Toolbar.TLabel', background=theme['toolbar_bg'], foreground=theme['editor_fg'], font=UI_FONT_BOLD)
        style.configure(
            'TCheckbutton',
            background=theme['check_bg'],
            foreground=theme['check_fg'],
            focuscolor=theme['toolbar_bg'],
            borderwidth=0,
            font=UI_FONT,
        )
        style.map(
            'TCheckbutton',
            background=[('active', theme['toolbar_alt_bg'])],
            foreground=[('active', theme['accent'])],
        )
        style.configure(
            'TRadiobutton',
            background=theme['panel_bg'],
            foreground=theme['editor_fg'],
            focuscolor=theme['panel_bg'],
        )
        style.configure(
            'TScrollbar',
            background=theme['scrollbar_bg'],
            troughcolor=theme['scrollbar_trough'],
            bordercolor=theme['border'],
            lightcolor=theme['scrollbar_bg'],
            darkcolor=theme['scrollbar_bg'],
            arrowcolor=theme['scrollbar_bg'],
            relief='flat',
            borderwidth=0,
            gripcount=0,
            arrowsize=0,
            width=12,
        )
        try:
            style.layout(
                'Vertical.TScrollbar',
                [
                    (
                        'Vertical.Scrollbar.trough',
                        {
                            'sticky': 'ns',
                            'children': [
                                ('Vertical.Scrollbar.thumb', {'sticky': 'nswe'}),
                            ],
                        },
                    )
                ],
            )
            style.layout(
                'Horizontal.TScrollbar',
                [
                    (
                        'Horizontal.Scrollbar.trough',
                        {
                            'sticky': 'we',
                            'children': [
                                ('Horizontal.Scrollbar.thumb', {'sticky': 'nswe'}),
                            ],
                        },
                    )
                ],
            )
        except tk.TclError:
            pass
        style.map(
            'TScrollbar',
            background=[('active', theme['accent_2']), ('pressed', theme['accent'])],
            troughcolor=[('active', theme['scrollbar_trough'])],
        )
        style.configure(
            'TPanedwindow',
            background=theme['border_soft'],
            borderwidth=0,
            relief='flat',
            sashthickness=8,
            sashwidth=8,
        )
        style.configure('Toolbar.TButton', background=theme['panel_bg'], foreground=theme['editor_fg'], padding=(12, 7), borderwidth=1, relief='flat')
        style.map(
            'Toolbar.TButton',
            background=[('active', theme['toolbar_alt_bg'])],
            foreground=[('active', theme['accent'])],
        )
        style.configure('Run.TButton', background=theme['run_bg'], foreground='white', padding=(14, 7), borderwidth=0, relief='flat')
        style.map(
            'Run.TButton',
            background=[('active', theme['run_bg_active'])],
            foreground=[('active', 'white')],
        )
        style.configure('Stop.TButton', background=theme['stop_bg'], foreground='white', padding=(14, 7), borderwidth=0, relief='flat')
        style.map(
            'Stop.TButton',
            background=[('disabled', theme['stop_bg_disabled']), ('active', theme['stop_bg_active'])],
            foreground=[('disabled', theme['stop_fg_disabled']), ('active', 'white')],
        )
        style.configure('TNotebook', background=theme['panel_bg'], borderwidth=0)
        style.configure(
            'TNotebook.Tab',
            background=theme['toolbar_bg'],
            foreground=theme['editor_fg'],
            font=UI_FONT_BUTTON,
            padding=(12, 7),
            borderwidth=0,
        )
        style.map(
            'TNotebook.Tab',
            background=[('selected', theme['panel_bg'])],
            foreground=[('selected', theme['accent'])],
        )

    def _frame(
        self,
        master,
        *,
        bg_key: str = 'panel_bg',
        bordered: bool = False,
        border_key: str = 'border',
    ) -> tk.Frame:
        theme = self.theme
        return tk.Frame(
            master,
            background=theme[bg_key],
            bd=0,
            highlightthickness=1 if bordered else 0,
            highlightbackground=theme[border_key],
            highlightcolor=theme[border_key],
        )

    def _button(
        self,
        master,
        text: str,
        command,
        *,
        variant: str = 'default',
        padx: int = 14,
        pady: int = 7,
    ) -> AppButton:
        button = AppButton(
            master,
            text=text,
            command=command,
            variant=variant,
            theme=self.theme,
            padx=padx,
            pady=pady,
        )
        self._app_buttons.append(button)
        return button

    def _toolbar_menu_button(
        self,
        master,
        text: str,
        items: list[tuple[str | None, object | None]],
        *,
        padx: int = 12,
    ) -> AppButton:
        button = self._button(master, text, None, variant='ghost', padx=padx)
        button.configure(frame_style='underline')
        menu = tk.Menu(button, tearoff=0)
        for label, command in items:
            if label is None:
                menu.add_separator()
            else:
                menu.add_command(label=label, command=command)
        self._toolbar_menus.append(menu)
        button.configure(command=lambda b=button, m=menu: self._show_toolbar_menu(b, m))
        return button

    def _show_toolbar_menu(self, button: AppButton, menu: tk.Menu) -> None:
        self._apply_menu_theme()
        try:
            menu.tk_popup(button.winfo_rootx(), button.winfo_rooty() + button.winfo_height())
        finally:
            menu.grab_release()

    def _separator(self, master) -> tk.Frame:
        return tk.Frame(master, width=1, height=24, background=self.theme['border'])

    def _create_sash_grip(self, master, item: dict[str, object], orient: str) -> tk.Canvas:
        grip = tk.Canvas(
            master,
            width=1,
            height=1,
            bd=0,
            highlightthickness=0,
            background=self.theme['border_soft'],
            cursor='sb_v_double_arrow' if orient == 'vertical' else 'sb_h_double_arrow',
        )
        grip.bind('<Button-1>', lambda event, data=item: self._start_sash_drag(data, event))
        grip.bind('<B1-Motion>', lambda event, data=item: self._drag_sash(data, event))
        grip.bind('<ButtonRelease-1>', lambda _event: self._update_sash_grips())
        return grip

    def _add_sash_grip(self, paned: tk.PanedWindow, orient: str) -> None:
        item: dict[str, object] = {'paned': paned, 'orient': orient}
        item['grip'] = self._create_sash_grip(paned.master, item, orient)
        self._sash_grips.append(item)

    def _draw_sash_grip(self, grip: tk.Canvas, orient: str) -> None:
        theme = self.theme
        grip.configure(background=theme['border_soft'])
        grip.delete('all')
        width = max(grip.winfo_width(), int(grip.cget('width') or 1))
        height = max(grip.winfo_height(), int(grip.cget('height') or 1))
        color = theme['splitter_grip']
        if orient == 'vertical':
            x1 = width // 2 - 12
            x2 = width // 2 + 12
            for offset in (-3, 0, 3):
                grip.create_line(x1, height // 2 + offset, x2, height // 2 + offset, fill=color, width=2, capstyle='round')
        else:
            y1 = height // 2 - 12
            y2 = height // 2 + 12
            for offset in (-3, 0, 3):
                grip.create_line(width // 2 + offset, y1, width // 2 + offset, y2, fill=color, width=2, capstyle='round')

    def _update_sash_grips(self, _event=None) -> None:
        for item in getattr(self, '_sash_grips', []):
            paned = item['paned']
            grip = item['grip']
            orient = str(item['orient'])
            if not isinstance(paned, tk.PanedWindow) or not isinstance(grip, tk.Canvas):
                continue
            try:
                panes = paned.panes()
                if len(panes) < 2:
                    grip.place_forget()
                    continue
                target_parent = paned.nametowidget(panes[1])
                if grip.master is not target_parent:
                    grip.destroy()
                    grip = self._create_sash_grip(target_parent, item, orient)
                    item['grip'] = grip
                if orient == 'vertical':
                    grip.configure(width=72, height=10)
                    grip.place(
                        x=max(0, target_parent.winfo_width() // 2 - 36),
                        y=0,
                    )
                else:
                    grip.configure(width=10, height=72)
                    grip.place(
                        x=0,
                        y=max(0, target_parent.winfo_height() // 2 - 36),
                    )
                self._draw_sash_grip(grip, orient)
                grip.lift()
                grip.tkraise()
            except Exception:
                grip.place_forget()

    def _start_sash_drag(self, item: dict[str, object], event) -> None:
        item['drag_root_x'] = event.x_root
        item['drag_root_y'] = event.y_root
        paned = item['paned']
        if isinstance(paned, tk.PanedWindow):
            try:
                item['drag_sash'] = paned.sash_coord(0)
            except Exception:
                item['drag_sash'] = (0, 0)

    def _drag_sash(self, item: dict[str, object], event) -> str:
        paned = item['paned']
        orient = item['orient']
        if not isinstance(paned, tk.PanedWindow):
            return 'break'
        start = item.get('drag_sash', (0, 0))
        if not isinstance(start, tuple):
            start = (0, 0)
        dx = event.x_root - int(item.get('drag_root_x', event.x_root))
        dy = event.y_root - int(item.get('drag_root_y', event.y_root))
        try:
            if orient == 'vertical':
                paned.sash_place(0, 0, max(160, int(start[1]) + dy))
            else:
                paned.sash_place(0, max(180, int(start[0]) + dx), 0)
        except Exception:
            pass
        self._update_sash_grips()
        return 'break'

    def _panedwindow(self, master, orient: str) -> tk.PanedWindow:
        paned = tk.PanedWindow(
            master,
            orient=orient,
            bd=0,
            borderwidth=0,
            relief='flat',
            background=self.theme['border_soft'],
            sashwidth=8,
            sashrelief='flat',
            sashpad=0,
            showhandle=False,
            opaqueresize=True,
        )
        self._paned_widgets.append(paned)
        self._add_sash_grip(paned, orient)
        paned.bind('<Configure>', self._update_sash_grips, add=True)
        paned.bind('<B1-Motion>', self._update_sash_grips, add=True)
        paned.bind('<ButtonRelease-1>', self._update_sash_grips, add=True)
        return paned

    def _set_initial_pane_layout(self) -> None:
        try:
            self.update_idletasks()
            height = self.paned.winfo_height()
            if height > 420:
                self.paned.sash_place(0, 0, height - 250)
            width = self.bottom_paned.winfo_width()
            if width > 700:
                self.bottom_paned.sash_place(0, int(width * 0.55), 0)
            self._update_sash_grips()
        except Exception:
            pass

    def _apply_theme(self) -> None:
        self.theme = THEMES['dark' if self.dark_mode.get() else 'light']
        self._apply_style()

        theme = self.theme
        for widget, bg_key in (
            (getattr(self, 'file_toolbar', None), 'toolbar_bg'),
            (getattr(self, 'brand_frame', None), 'toolbar_bg'),
            (getattr(self, 'run_toolbar', None), 'toolbar_alt_bg'),
            (getattr(self, 'paned_shell', None), 'app_bg'),
            (getattr(self, 'editor_shell', None), 'panel_bg'),
            (getattr(self, 'bottom_shell', None), 'panel_bg'),
            (getattr(self, 'input_header', None), 'toolbar_alt_bg'),
            (getattr(self, 'input_frame', None), 'panel_bg'),
            (getattr(self, 'input_content', None), 'panel_bg'),
        ):
            if widget:
                widget.configure(background=theme[bg_key])
        for widget in (
            getattr(self, 'file_toolbar', None),
            getattr(self, 'run_toolbar', None),
            getattr(self, 'editor_shell', None),
            getattr(self, 'bottom_shell', None),
            getattr(self, 'input_frame', None),
        ):
            if widget:
                widget.configure(highlightbackground=theme['border'], highlightcolor=theme['border'])
        for button in getattr(self, '_app_buttons', []):
            button.configure(theme=theme)
        for group in getattr(self, '_toolbar_groups', []):
            group.configure(background=theme['toolbar_bg'])
        for sep in getattr(self, '_separators', []):
            sep.configure(background=theme['border'])
        for paned in getattr(self, '_paned_widgets', []):
            paned.configure(background=theme['border_soft'])
        self._update_sash_grips()
        if self.brand_label:
            self.brand_label.configure(background=theme['toolbar_bg'], foreground=theme['editor_fg'])
        if self.brand_logo_label:
            self.brand_logo_label.configure(theme=theme)
        if self.temp_mode_label:
            self.temp_mode_label.configure(background=theme['toolbar_alt_bg'], foreground=theme['editor_fg'])
        if hasattr(self, 'run_label'):
            self.run_label.configure(background=theme['toolbar_alt_bg'], foreground=theme['editor_fg'])
        self.console.configure(
            background=theme['console_bg'],
            foreground=theme['console_fg'],
            insertbackground=theme['console_fg'],
            selectbackground=theme['selection_bg'],
            selectforeground=theme['selection_fg'],
            relief='flat',
            borderwidth=0,
            highlightthickness=0,
            padx=12,
            pady=10,
        )
        self.console.tag_configure('stdout', foreground=theme['console_fg'])
        self.console.tag_configure('stderr', foreground=theme['stderr_fg'])
        self.console.tag_configure('status', foreground=theme['status_fg'])
        self.console.tag_configure('stdin', foreground=theme['stdin_fg'])

        self.input_text.configure(
            background=theme['input_bg'],
            foreground=theme['input_fg'],
            insertbackground=theme['input_fg'],
            highlightbackground=theme['border'],
            highlightcolor=theme['accent'],
            selectbackground=theme['selection_bg'],
            selectforeground=theme['selection_fg'],
            relief='flat',
            bd=0,
            highlightthickness=1,
        )
        if hasattr(self, 'input_shortcuts'):
            self.input_shortcuts.configure(background=theme['toolbar_alt_bg'], foreground=theme['line_number_fg'])
        if hasattr(self, 'input_label'):
            self.input_label.configure(background=theme['toolbar_alt_bg'], foreground=theme['editor_fg'])

        for tab in self.tabs_by_frame.values():
            tab.apply_theme()

        self.turtle_canvas.configure(
            background=theme['editor_bg'],
            highlightbackground=theme['border'],
            highlightcolor=theme['accent_2'],
        )

        self._apply_menu_theme()
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            self.settings_window.configure(background=theme['app_bg'])

    def _build_ui(self) -> None:
        self._separators: list[tk.Frame] = []

        file_toolbar = FlowToolbar(self, background=self.theme['toolbar_bg'], border=self.theme['border'])
        self.file_toolbar = file_toolbar
        file_toolbar.pack(fill='x', padx=16, pady=(14, 0))

        def toolbar_group(*, slot: str, padx: int = 4, separator: bool = False) -> tk.Frame:
            group = tk.Frame(file_toolbar, background=self.theme['toolbar_bg'], bd=0, highlightthickness=0)
            self._toolbar_groups.append(group)
            separator_line = None
            if separator:
                separator_line = tk.Frame(group, width=1, background=self.theme['border'])
                self._separators.append(separator_line)
                separator_line.pack(side='left', fill='y', padx=(0, 10), pady=4)
            content = tk.Frame(group, background=self.theme['toolbar_bg'], bd=0, highlightthickness=0)
            self._toolbar_groups.append(content)
            content.pack(side='left')
            file_toolbar.add(group, padx=padx, pady=6, slot=slot, separator=separator_line)
            return content

        brand = tk.Frame(file_toolbar, background=self.theme['toolbar_bg'])
        self._toolbar_groups.append(brand)
        self.brand_frame = brand
        file_toolbar.add(brand, padx=10, pady=6, slot='brand')
        self.brand_logo_label = ToolbarLogo(brand, theme=self.theme)
        self.brand_logo_label.pack(side='left', padx=(0, 9))
        self.brand_label = tk.Label(
            brand,
            text='МШПайтон.Оффлайн',
            font=UI_FONT_TITLE,
            background=self.theme['toolbar_bg'],
            foreground=self.theme['editor_fg'],
        )
        self.brand_label.pack(side='left')

        file_group = toolbar_group(slot='file')
        self._button(file_group, 'Новый', self.new_tab, padx=12).pack(side='left', padx=2, pady=0)
        self._button(file_group, 'Открыть', self.open_file, padx=12).pack(side='left', padx=2, pady=0)
        self._button(file_group, 'Сохранить', self.save_file, padx=12).pack(side='left', padx=2, pady=0)
        self._button(file_group, 'Сохранить все', self.save_all, padx=12).pack(side='left', padx=2, pady=0)

        tab_group = toolbar_group(slot='tab', separator=True)
        self._button(
            tab_group,
            'Переименовать',
            self.rename_current_tab,
            padx=12,
        ).pack(side='left', padx=2, pady=0)
        self._button(tab_group, 'Закрыть', self.close_current_tab, padx=12).pack(
            side='left', padx=2, pady=0
        )

        menu_group = toolbar_group(slot='menu', padx=0)
        self._toolbar_menu_button(
            menu_group,
            'Файл',
            [
                ('Сохранить как...', self.save_file_as),
                (None, None),
                ('Перезапустить приложение', self.restart_app),
                ('Выход', self.on_exit),
            ],
            padx=8,
        ).pack(side='left', padx=2, pady=0)
        self._toolbar_menu_button(
            menu_group,
            'Проект',
            [
                ('Сохранить архив...', self.save_archive),
                (None, None),
                ('Экспорт кода проекта', self.export_project_hash),
                ('Импорт кода проекта', self.import_project_hash),
            ],
            padx=8,
        ).pack(side='left', padx=2, pady=0)
        self._toolbar_menu_button(
            menu_group,
            'Инструменты',
            [
                ('Сделать отступ', self.indent_selection),
                ('Очистить консоль', self.clear_console),
                (None, None),
                ('Настройки', self._open_settings),
            ],
            padx=8,
        ).pack(side='left', padx=2, pady=0)

        self.temp_button_group = toolbar_group(slot='temp', separator=True)
        self.temp_import_button = self._button(
            self.temp_button_group,
            'Импорт картинок',
            self.import_temp_images,
            variant='ghost',
            padx=16,
        )
        self.temp_import_button.pack(side='left', padx=2, pady=0)
        self.temp_show_images_button = self._button(
            self.temp_button_group,
            'Список картинок',
            self.show_temp_images_list,
            variant='ghost',
            padx=16,
        )
        self.temp_show_images_button.pack(side='left', padx=2, pady=0)
        file_toolbar.hide(self.temp_button_group)
        run_toolbar = FlowToolbar(self, background=self.theme['toolbar_alt_bg'], border=self.theme['border'])
        self.run_toolbar = run_toolbar
        run_toolbar.pack(fill='x', padx=16, pady=(8, 0))
        self.run_label = tk.Label(
            run_toolbar,
            text='Запуск',
            font=UI_FONT_BUTTON,
            background=self.theme['toolbar_alt_bg'],
            foreground=self.theme['editor_fg'],
        )
        run_toolbar.add(self.run_label, padx=12, pady=7, rows={'wide': 0, 'medium': 0, 'narrow': 0})
        self.run_button = self._button(
            run_toolbar,
            'Запустить (F5)',
            self.run_current,
            variant='primary',
            padx=18,
        )
        run_toolbar.add(self.run_button, padx=3, pady=6, rows={'wide': 0, 'medium': 0, 'narrow': 0})
        run_toolbar.add(
            self._button(
                run_toolbar,
                'Построчно',
                self.run_current_step,
                variant='primary',
                padx=18,
            ),
            padx=3,
            pady=6,
            rows={'wide': 0, 'medium': 0, 'narrow': 1},
        )
        self.stop_button = self._button(
            run_toolbar,
            'Остановить',
            self.stop_process,
            variant='danger',
            padx=18,
        )
        run_toolbar.add(self.stop_button, padx=3, pady=6, rows={'wide': 0, 'medium': 0, 'narrow': 1})
        self.step_next_button = self._button(
            run_toolbar,
            'Далее',
            self.step_next,
            variant='ghost',
            padx=16,
        )
        run_toolbar.add(self.step_next_button, padx=4, pady=6, rows={'wide': 0, 'medium': 0, 'narrow': 1})
        run_toolbar.hide(self.step_next_button)

        self.temp_mode_label = tk.Label(
            run_toolbar,
            text='Режим: Обычный',
            font=UI_FONT_BUTTON,
            background=self.theme['toolbar_alt_bg'],
            foreground=self.theme['editor_fg'],
        )
        run_toolbar.add(self.temp_mode_label, padx=10, pady=7, rows={'wide': 0, 'medium': 1, 'narrow': 2})
        theme_toggle = ttk.Checkbutton(
            run_toolbar,
            text='Тёмная тема',
            variable=self.dark_mode,
            command=self._apply_theme,
        )
        run_toolbar.add(theme_toggle, padx=10, pady=7, rows={'wide': 0, 'medium': 1, 'narrow': 2})

        self.paned_shell = self._frame(self, bg_key='app_bg')
        self.paned_shell.pack(fill='both', expand=True, padx=16, pady=(12, 16))
        self.paned = self._panedwindow(self.paned_shell, orient='vertical')
        self.paned.pack(fill='both', expand=True)

        editor_frame = self._frame(self.paned, bg_key='panel_bg', bordered=True)
        self.editor_shell = editor_frame
        self.editor_paned = self._panedwindow(editor_frame, orient='horizontal')
        self.editor_paned.pack(fill='both', expand=True, padx=10, pady=10)

        editor_main = ttk.Frame(self.editor_paned, style='Editor.TFrame')
        self.notebook = ttk.Notebook(editor_main)
        self.notebook.pack(fill='both', expand=True)
        self.notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)
        self.editor_paned.add(editor_main, stretch='always', minsize=360)

        # Turtle frame: fixed size, not resizable
        self.turtle_frame = ttk.Frame(self.editor_paned, style='Editor.TFrame')
        self.turtle_frame.pack_propagate(False)
        self.turtle_frame.configure(width=424, height=424)
        
        self.turtle_canvas = tk.Canvas(self.turtle_frame, highlightthickness=1, bd=0, takefocus=1, width=400, height=400)
        self.turtle_canvas.pack(padx=12, pady=12)
        self.turtle_canvas.bind('<Button-1>', lambda _e: self.turtle_canvas.focus_set())
        self.turtle_canvas.bind('<Configure>', self._on_turtle_canvas_resize)
        
        # Bind to prevent sash movement when turtle is visible
        self.editor_paned.bind('<Button-1>', self._on_paned_click, add=True)

        self.paned.add(editor_frame, stretch='always', minsize=360)

        # Bottom panel with console and input side by side
        bottom_frame = self._frame(self.paned, bg_key='panel_bg', bordered=True)
        self.bottom_shell = bottom_frame
        self.bottom_paned = self._panedwindow(bottom_frame, orient='horizontal')
        self.bottom_paned.pack(fill='both', expand=True, padx=10, pady=10)

        console_frame = ttk.Frame(self.bottom_paned, style='Editor.TFrame')
        self.console = tk.Text(
            console_frame,
            height=10,
            wrap='word',
            font=CONSOLE_FONT,
            state='disabled',
            relief='flat',
            bd=0,
            highlightthickness=0,
        )
        self.console.bind('<Control-c>', self._console_copy)
        self.console.bind('<Control-C>', self._console_copy)
        self.console.bind('<Button-1>', lambda _e: self.console.focus_set())
        self.console.configure(takefocus=1)
        self.console.pack(fill='both', expand=True, side='left')

        console_scroll = ttk.Scrollbar(console_frame, orient='vertical', command=self.console.yview)
        self.console.configure(yscrollcommand=console_scroll.set)
        console_scroll.pack(fill='y', side='right')

        self.bottom_paned.add(console_frame, stretch='always', minsize=260)

        # Input frame on the right
        self.input_frame = self._frame(self.bottom_paned, bg_key='panel_bg', bordered=True)
        input_content = self._frame(self.input_frame, bg_key='panel_bg')
        self.input_content = input_content
        input_content.pack(side='left', fill='both', expand=True)
        
        # Input header with title and shortcuts
        input_header = self._frame(input_content, bg_key='toolbar_alt_bg')
        self.input_header = input_header
        input_header.pack(side='top', anchor='w', fill='x', padx=8, pady=(8, 2))
        
        self.input_label = tk.Label(
            input_header,
            text='Ввод:',
            font=UI_FONT_BUTTON,
            background=self.theme['toolbar_alt_bg'],
            foreground=self.theme['editor_fg'],
        )
        self.input_label.pack(side='left', anchor='w')
        
        self.input_shortcuts = tk.Label(
            input_header, 
            text='Enter — отправить  •  Ctrl+Enter — новая строка',
            font=UI_FONT_SMALL,
            foreground=self.theme['line_number_fg'],
            background=self.theme['toolbar_alt_bg'],
        )
        self.input_shortcuts.pack(side='left', padx=(12, 0), anchor='w')
        
        self.input_text = tk.Text(
            input_content,
            height=6,
            wrap='word',
            font=INPUT_FONT,
            relief='flat',
            bd=0,
            highlightthickness=1,
            insertwidth=3,
            insertbackground=self.theme['input_fg'],
        )
        self.input_text.pack(fill='both', expand=True, padx=8, pady=(2, 8))
        self.input_text.bind('<Return>', self._send_console_input)
        self.input_text.bind('<Control-Return>', self._insert_input_newline)
        self.input_text.bind('<FocusIn>', self._on_input_focus_in)
        self.input_text.bind('<FocusOut>', self._on_input_focus_out)
        self._bind_input_shortcuts()
        
        self.bottom_paned.add(self.input_frame, stretch='always', minsize=320)
        self.paned.add(bottom_frame, stretch='never', minsize=160)

        self.tabs_by_frame: dict[str, EditorTab] = {}
        self._apply_theme()
        self._update_temp_mode_ui()
        self._update_input_state()
        self._update_run_controls()

    def _create_menu(self) -> None:
        self.menubar = tk.Menu(self)

        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.file_menu.add_command(label=icon('🆕', 'Новый'), command=self.new_tab)
        self.file_menu.add_command(label=icon('📂', 'Открыть…'), command=self.open_file)
        self.file_menu.add_command(label=icon('💾', 'Сохранить'), command=self.save_file)
        self.file_menu.add_command(label=icon('💾', 'Сохранить как…'), command=self.save_file_as)
        self.file_menu.add_command(label=icon('💾', 'Сохранить все'), command=self.save_all)
        self.file_menu.add_command(label=icon('✏️', 'Переименовать модуль'), command=self.rename_current_tab)
        self.file_menu.add_separator()
        self.file_menu.add_command(label=icon('❌', 'Закрыть вкладку'), command=self.close_current_tab)
        self.file_menu.add_command(label=icon('🔄', 'Перезапустить приложение'), command=self.restart_app)
        self.file_menu.add_command(label=icon('🚪', 'Выход'), command=self.on_exit)

        self.run_menu = tk.Menu(self.menubar, tearoff=0)
        self.run_menu.add_command(label=icon('▶️', 'Запустить (F5)'), command=self.run_current)
        self.run_menu.add_command(label=icon('⏭', 'Построчно'), command=self.run_current_step)
        self.run_menu.add_command(label=icon('⏹', 'Остановить (Shift+F5)'), command=self.stop_process)
        self.run_menu.add_separator()
        self.run_menu.add_command(label=icon('🧹', 'Очистить консоль'), command=self.clear_console)

        self.tools_menu = tk.Menu(self.menubar, tearoff=0)
        self.tools_menu.add_command(label='Сделать отступ', command=self.indent_selection)
        self.tools_menu.add_separator()
        self.tools_menu.add_command(label='Экспорт кода проекта', command=self.export_project_hash)
        self.tools_menu.add_command(label='Импорт кода проекта', command=self.import_project_hash)

        self.menubar.add_cascade(label='Файл', menu=self.file_menu)
        self.menubar.add_cascade(label='Запуск', menu=self.run_menu)
        self.menubar.add_cascade(label='Полезное', menu=self.tools_menu)
        self.menubar.add_command(label=icon('⚙', 'Настройки'), command=self._open_settings)
        self.config(menu=self.menubar)
        self._apply_menu_theme()

    def _bind_shortcuts(self) -> None:
        self.bind('<Control-n>', lambda _e: self.new_tab())
        self.bind('<Control-o>', lambda _e: self.open_file())
        self.bind('<Control-s>', lambda _e: self.save_file())
        self.bind('<Control-Shift-s>', lambda _e: self.save_all())
        self.bind('<Control-Shift-S>', lambda _e: self.save_all())
        self.bind('<Control-w>', lambda _e: self.close_current_tab())
        self.bind('<F5>', lambda _e: self.run_current())
        self.bind('<Shift-F5>', lambda _e: self.stop_process())
        self.bind('<Control-Tab>', lambda _e: self._cycle_tab(1))
        self.bind('<Control-Shift-Tab>', lambda _e: self._cycle_tab(-1))
        self.bind('<Control-ISO_Left_Tab>', lambda _e: self._cycle_tab(-1))
        self.protocol('WM_DELETE_WINDOW', self.on_exit)
        self._bind_all_if_supported('<Control-n>', lambda _e: self.new_tab(), add=True)
        self._bind_all_if_supported('<Control-N>', lambda _e: self.new_tab(), add=True)
        self._bind_all_if_supported('<Control-o>', lambda _e: self.open_file(), add=True)
        self._bind_all_if_supported('<Control-O>', lambda _e: self.open_file(), add=True)
        self._bind_all_if_supported('<Control-s>', lambda _e: self.save_file(), add=True)
        self._bind_all_if_supported('<Control-S>', lambda _e: self.save_file(), add=True)
        self._bind_all_if_supported('<Control-Shift-s>', lambda _e: self.save_all(), add=True)
        self._bind_all_if_supported('<Control-Shift-S>', lambda _e: self.save_all(), add=True)
        self._bind_all_if_supported('<Control-w>', lambda _e: self.close_current_tab(), add=True)
        self._bind_all_if_supported('<Control-W>', lambda _e: self.close_current_tab(), add=True)
        self._bind_all_if_supported('<Control-a>', self._global_select_all, add=True)
        self._bind_all_if_supported('<Control-A>', self._global_select_all, add=True)
        if sys.platform == 'darwin':
            self._bind_all_if_supported('<Command-a>', self._global_select_all, add=True)
            self._bind_all_if_supported('<Command-A>', self._global_select_all, add=True)
        self._bind_all_if_supported('<Control-c>', self._global_copy, add=True)
        self._bind_all_if_supported('<Control-C>', self._global_copy, add=True)
        self._bind_all_if_supported('<Control-v>', self._global_paste, add=True)
        self._bind_all_if_supported('<Control-V>', self._global_paste, add=True)
        self._bind_all_if_supported('<Control-x>', self._global_cut, add=True)
        self._bind_all_if_supported('<Control-X>', self._global_cut, add=True)
        self._bind_all_if_supported('<Control-z>', self._global_undo, add=True)
        self._bind_all_if_supported('<Control-Z>', self._global_undo, add=True)
        self._bind_all_if_supported('<Control-y>', self._global_redo, add=True)
        self._bind_all_if_supported('<Control-Y>', lambda _e: self._global_redo(), add=True)
        self._bind_all_if_supported('<Control-Tab>', lambda _e: self._cycle_tab(1), add=True)
        self._bind_all_if_supported('<Control-Shift-Tab>', lambda _e: self._cycle_tab(-1), add=True)
        self._bind_all_if_supported('<Control-ISO_Left_Tab>', lambda _e: self._cycle_tab(-1), add=True)

    def _bind_if_supported(self, widget, sequence: str, callback, add=None) -> None:
        try:
            widget.bind(sequence, callback, add=add)
        except tk.TclError:
            pass

    def _bind_all_if_supported(self, sequence: str, callback, add=None) -> None:
        try:
            self.bind_all(sequence, callback, add=add)
        except tk.TclError:
            pass

    def _open_settings(self) -> None:
        if hasattr(self, 'settings_window') and self.settings_window.winfo_exists():
            self.settings_window.lift()
            self.settings_window.focus_set()
            return

        self.settings_window = tk.Toplevel(self)
        self.settings_window.title('Настройки')
        self.settings_window.resizable(False, False)
        self.settings_window.configure(background=self.theme['app_bg'])

        frame = ttk.Frame(self.settings_window, padding=12)
        frame.pack(fill='both', expand=True)

        ttk.Label(frame, text='Основные', font=UI_FONT_BOLD).pack(anchor='w')

        ttk.Checkbutton(
            frame,
            text='Тёмная тема',
            variable=self.dark_mode,
            command=self._apply_theme,
        ).pack(anchor='w', pady=(6, 0))

        ttk.Label(frame, text='Сохранение перед запуском', font=UI_FONT_BOLD).pack(
            anchor='w', pady=(12, 0)
        )

        ttk.Radiobutton(
            frame,
            text='Спрашивать и запомнить',
            variable=self.save_before_run_var,
            value='ask',
            command=self._apply_save_before_run_setting,
        ).pack(anchor='w', pady=(4, 0))
        ttk.Radiobutton(
            frame,
            text='Всегда сохранять',
            variable=self.save_before_run_var,
            value='always',
            command=self._apply_save_before_run_setting,
        ).pack(anchor='w')
        ttk.Radiobutton(
            frame,
            text='Никогда не сохранять (временный файл)',
            variable=self.save_before_run_var,
            value='never',
            command=self._apply_save_before_run_setting,
        ).pack(anchor='w')

        ttk.Button(frame, text='Закрыть', command=self.settings_window.destroy).pack(anchor='e', pady=(12, 0))

    def _apply_save_before_run_setting(self) -> None:
        mode = self.save_before_run_var.get()
        if mode == 'ask':
            self.save_on_run_preference = None
        elif mode == 'always':
            self.save_on_run_preference = True
        elif mode == 'never':
            self.save_on_run_preference = False
        self._update_temp_mode_ui()

    def _temporary_mode_active(self) -> bool:
        return self.save_before_run_var.get() == 'never'

    def _update_temp_mode_ui(self) -> None:
        active = self._temporary_mode_active()
        if self.temp_mode_label:
            status = 'Временные файлы' if active else 'Обычный'
            self.temp_mode_label.configure(text=f'Режим: {status}')
        if self.temp_button_group:
            if active:
                self.file_toolbar.show(self.temp_button_group)
            else:
                self.file_toolbar.hide(self.temp_button_group)
        if active:
            self._ensure_temp_session_dir()
            self._autosave_all_tabs()

    def on_tab_modified(self, tab: EditorTab) -> None:
        if self._temporary_mode_active():
            self._schedule_temp_autosave(tab)

    def _ensure_temp_session_dir(self) -> None:
        self.temp_session_dir.mkdir(parents=True, exist_ok=True)

    def _temp_name_for_tab(self, tab: EditorTab) -> str:
        if tab.temp_name:
            return tab.temp_name
        base = self._runtime_name_for_tab(tab)
        if not base.lower().endswith('.py'):
            base = f'{base}.py'
        used = {t.temp_name for t in self.tabs_by_frame.values() if t.temp_name}
        candidate = base
        index = 2
        while candidate in used:
            stem, suffix = os.path.splitext(base)
            candidate = f'{stem}_{index}{suffix}'
            index += 1
        tab.temp_name = candidate
        return candidate

    def _temp_path_for_tab(self, tab: EditorTab) -> Path:
        self._ensure_temp_session_dir()
        return self.temp_session_dir / self._temp_name_for_tab(tab)

    def _schedule_temp_autosave(self, tab: EditorTab) -> None:
        if tab.autosave_job is not None:
            try:
                tab.text.after_cancel(tab.autosave_job)
            except Exception:
                pass
        tab.autosave_job = tab.text.after(TEMP_AUTOSAVE_DELAY_MS, lambda: self._autosave_temp_tab(tab))

    def _autosave_temp_tab(self, tab: EditorTab) -> None:
        if not self._temporary_mode_active():
            return
        try:
            target = self._temp_path_for_tab(tab)
            target.write_text(tab.get_content(), encoding='utf-8')
        except Exception:
            pass

    def _autosave_all_tabs(self) -> None:
        if not self._temporary_mode_active():
            return
        for tab in self.tabs_by_frame.values():
            self._autosave_temp_tab(tab)

    def _has_temp_files(self) -> bool:
        if not self._temporary_mode_active():
            return False
        if self.temp_assets:
            return True
        for tab in self.tabs_by_frame.values():
            if tab.path is None:
                return True
        return self.temp_session_dir.exists()

    def _clear_temp_session(self) -> None:
        if not self.temp_session_dir.exists():
            self.temp_assets.clear()
            for tab in self.tabs_by_frame.values():
                tab.temp_name = None
            return

        def on_error(func, path, exc_info):
            # Try to make writable and delete again
            if not os.access(path, os.W_OK):
                try:
                    os.chmod(path, 0o777)
                    func(path)
                except Exception:
                    pass
        
        try:
            shutil.rmtree(self.temp_session_dir, onerror=on_error)
        except Exception:
            # Fallback: try to delete contents
            for p in self.temp_session_dir.glob('*'):
                try:
                    if p.is_dir():
                        shutil.rmtree(p, ignore_errors=True)
                    else:
                        p.unlink()
                except Exception:
                    pass
                    
        self.temp_assets.clear()
        for tab in self.tabs_by_frame.values():
            tab.temp_name = None

    def _temp_assets_paths(self) -> list[Path]:
        if not self.temp_assets:
            return []
        return [self.temp_session_dir / name for name in sorted(self.temp_assets)]

    def _is_running(self) -> bool:
        return self.process is not None or self.turtle_running or self.inline_running

    def _update_run_controls(self) -> None:
        # _restart_pending тоже считаем «работающим»: пока перезапуск ждёт
        # фактической остановки старого запуска, кнопка должна оставаться в
        # состоянии «Перезапустить», иначе видно ложное «Запустить» и можно
        # кликнуть повторно.
        running = self._is_running() or self._restart_pending
        if running:
            self.run_button.configure(text='Перезапустить (F5)')
            self.stop_button.state(['!disabled'])
        else:
            self.run_button.configure(text='Запустить (F5)')
            self.stop_button.state(['disabled'])

    def _apply_menu_theme(self) -> None:
        theme = self.theme
        menus = list(getattr(self, '_toolbar_menus', []))
        if hasattr(self, 'menubar'):
            menus.extend([self.menubar, self.file_menu, self.run_menu, self.tools_menu])
        for menu in menus:
            menu.configure(
                background=theme['menu_bg'],
                foreground=theme['menu_fg'],
                activebackground=theme['menu_active_bg'],
                activeforeground=theme['menu_active_fg'],
                borderwidth=1,
                relief='flat',
            )

    def _bind_input_shortcuts(self) -> None:
        self.bind_text_shortcuts(self.input_text)

    def bind_text_shortcuts(self, widget: tk.Text) -> None:
        self._bind_if_supported(widget, '<Control-a>', lambda _e, w=widget: self._select_all_widget(w))
        self._bind_if_supported(widget, '<Control-A>', lambda _e, w=widget: self._select_all_widget(w))
        if sys.platform == 'darwin':
            self._bind_if_supported(widget, '<Command-a>', lambda _e, w=widget: self._select_all_widget(w))
            self._bind_if_supported(widget, '<Command-A>', lambda _e, w=widget: self._select_all_widget(w))
        self._bind_if_supported(widget, '<Control-c>', lambda _e, w=widget: self._clipboard_copy_widget(w))
        self._bind_if_supported(widget, '<Control-C>', lambda _e, w=widget: self._clipboard_copy_widget(w))
        self._bind_if_supported(widget, '<Control-x>', lambda _e, w=widget: self._clipboard_cut_widget(w))
        self._bind_if_supported(widget, '<Control-X>', lambda _e, w=widget: self._clipboard_cut_widget(w))
        self._bind_if_supported(widget, '<Control-v>', lambda _e, w=widget: self._clipboard_paste_widget(w))
        self._bind_if_supported(widget, '<Control-V>', lambda _e, w=widget: self._clipboard_paste_widget(w))
        self._bind_if_supported(widget, '<Control-z>', lambda _e, w=widget: self._undo_widget(w))
        self._bind_if_supported(widget, '<Control-Z>', lambda _e, w=widget: self._undo_widget(w))
        self._bind_if_supported(widget, '<Control-y>', lambda _e, w=widget: self._redo_widget(w))
        self._bind_if_supported(widget, '<Control-Y>', lambda _e, w=widget: self._redo_widget(w))
        self._bind_if_supported(widget, '<Control-KeyPress>', lambda e, w=widget: self._handle_control_key(w, e), add=True)
        if sys.platform == 'darwin':
            self._bind_if_supported(widget, '<Command-KeyPress>', lambda e, w=widget: self._handle_control_key(w, e, require_control=False), add=True)

    def _global_select_all(self, _event=None) -> str | None:
        widget = self._resolve_text_target()
        if widget:
            return self._select_all_widget(widget)
        return None

    def _global_copy(self, _event=None) -> str | None:
        widget = self._resolve_text_target()
        if widget:
            return self._clipboard_copy_widget(widget)
        return None

    def _global_paste(self, _event=None) -> str | None:
        widget = self._resolve_text_target()
        if widget:
            return self._clipboard_paste_widget(widget)
        return None

    def _global_cut(self, _event=None) -> str | None:
        widget = self._resolve_text_target()
        if widget:
            return self._clipboard_cut_widget(widget)
        return None

    def _global_undo(self, _event=None) -> str | None:
        widget = self._resolve_text_target()
        if widget:
            return self._undo_widget(widget)
        return None

    def _global_redo(self, _event=None) -> str | None:
        widget = self._resolve_text_target()
        if widget:
            return self._redo_widget(widget)
        return None

    def _handle_control_key(self, widget: tk.Text, event: tk.Event, require_control: bool = True) -> str | None:
        if require_control and not (event.state & 0x4):
            return None
        keysym_map = {
            'a': self._select_all_widget,
            'c': self._clipboard_copy_widget,
            'v': self._clipboard_paste_widget,
            'x': self._clipboard_cut_widget,
            'z': self._undo_widget,
            'y': self._redo_widget,
        }
        keycode_map = {
            65: self._select_all_widget,   # A
            67: self._clipboard_copy_widget,  # C
            86: self._clipboard_paste_widget,  # V
            88: self._clipboard_cut_widget,  # X
            90: self._undo_widget,  # Z
            89: self._redo_widget,  # Y
        }
        action = keysym_map.get(str(getattr(event, 'keysym', '')).lower())
        if action is None:
            action = keycode_map.get(event.keycode)
        if action:
            return action(widget)
        return None

    def _resolve_text_target(self) -> tk.Text | None:
        widget = self.focus_get()
        if isinstance(widget, tk.Text):
            return widget
        tab = self.get_current_tab()
        if tab:
            return tab.text
        return None

    def indent_selection(self) -> None:
        tab = self.get_current_tab()
        if not tab:
            return
        self._indent_selection(tab.text)

    def export_project_hash(self) -> None:
        payload = self._serialize_project()
        if not payload:
            messagebox.showinfo('Экспорт', 'Нет открытых модулей для экспорта.')
            return
        dialog = tk.Toplevel(self)
        dialog.title('Экспорт проекта')
        dialog.configure(background=self.theme['app_bg'])
        dialog.geometry('700x300')

        frame = ttk.Frame(dialog, padding=12)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Хэш проекта (скопируйте и сохраните):').pack(anchor='w')
        text = tk.Text(
            frame,
            height=8,
            wrap='word',
            font=CONSOLE_FONT,
            background=self.theme['input_bg'],
            foreground=self.theme['input_fg'],
            insertbackground=self.theme['input_fg'],
        )
        text.pack(fill='both', expand=True, pady=(6, 8))
        text.insert('1.0', payload)
        text.focus_set()

        def _copy_hash() -> None:
            self.clipboard_clear()
            self.clipboard_append(payload)

        btns = ttk.Frame(frame)
        btns.pack(anchor='e')
        ttk.Button(btns, text='Скопировать', command=_copy_hash).pack(side='right', padx=4)
        ttk.Button(btns, text='Закрыть', command=dialog.destroy).pack(side='right')

    def import_project_hash(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title('Импорт проекта')
        dialog.configure(background=self.theme['app_bg'])
        dialog.geometry('700x320')

        frame = ttk.Frame(dialog, padding=12)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Вставьте хэш проекта:').pack(anchor='w')
        text = tk.Text(
            frame,
            height=8,
            wrap='word',
            font=CONSOLE_FONT,
            background=self.theme['input_bg'],
            foreground=self.theme['input_fg'],
            insertbackground=self.theme['input_fg'],
        )
        text.pack(fill='both', expand=True, pady=(6, 8))
        text.focus_set()
        self.bind_text_shortcuts(text)

        def _do_import() -> None:
            raw = text.get('1.0', 'end-1c')
            payload = ''.join(raw.split())
            if not payload:
                return
            if not self._load_project_from_hash(payload):
                return
            dialog.destroy()

        btns = ttk.Frame(frame)
        btns.pack(anchor='e')
        ttk.Button(btns, text='Импортировать', command=_do_import).pack(side='right', padx=4)
        ttk.Button(btns, text='Отмена', command=dialog.destroy).pack(side='right')

    def _serialize_project(self) -> str:
        if not self.tabs_by_frame:
            return ''
        files: list[dict[str, str]] = []
        for tab in self.tabs_by_frame.values():
            name = self._runtime_name_for_tab(tab)
            files.append({'name': name, 'content': tab.get_content()})
        payload = {'version': 1, 'files': files}
        raw = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        packed = zlib.compress(raw, level=9)
        return base64.b85encode(packed).decode('ascii')

    def _load_project_from_hash(self, token: str) -> bool:
        try:
            raw = base64.b85decode(token.encode('ascii'))
            payload = json.loads(zlib.decompress(raw).decode('utf-8'))
        except Exception:
            messagebox.showerror('Импорт', 'Не удалось прочитать хэш проекта.')
            return False
        files = payload.get('files', [])
        if not files:
            messagebox.showerror('Импорт', 'В хэше нет данных проекта.')
            return False

        for tab in list(self.tabs_by_frame.values()):
            if not self._confirm_discard(tab):
                return False

        for tab in list(self.tabs_by_frame.values()):
            self.notebook.forget(tab.frame)
        self.tabs_by_frame.clear()
        self.main_tab = None
        self._main_created = False

        main_entry = None
        other_entries = []
        for entry in files:
            name = str(entry.get('name', '')).strip()
            if name.lower() == 'main.py' and main_entry is None:
                main_entry = entry
            else:
                other_entries.append(entry)

        main_tab = self._ensure_main_tab()
        if main_entry is not None:
            main_tab.set_content(str(main_entry.get('content', '')))
        else:
            main_tab.set_content('')

        for entry in other_entries:
            name = str(entry.get('name', '')).strip() or self._next_virtual_name()
            tab = EditorTab(self)
            tab.virtual_name = name
            tab.set_content(str(entry.get('content', '')))
            self.notebook.add(tab.frame, text=tab.virtual_name)
            self.tabs_by_frame[str(tab.frame)] = tab
            self.update_tab_title(tab)

        self.notebook.select(main_tab.frame)
        return True

    def _indent_or_tab(self, widget: tk.Text) -> str:
        if widget.tag_ranges('sel'):
            return self._indent_selection(widget)
        widget.insert('insert', '    ')
        return 'break'

    def _newline_and_indent(self, widget: tk.Text) -> str:
        if widget.tag_ranges('sel'):
            widget.delete('sel.first', 'sel.last')

        current_line = widget.get('insert linestart', 'insert')
        indent = current_line[:len(current_line) - len(current_line.lstrip(' \t'))]
        if current_line.rstrip().endswith(':'):
            indent += '    '

        widget.edit_separator()
        widget.insert('insert', '\n' + indent)
        widget.edit_separator()
        widget.see('insert')
        return 'break'

    def _indent_selection(self, widget: tk.Text) -> str:
        try:
            start = widget.index('sel.first')
            end = widget.index('sel.last')
        except tk.TclError:
            widget.insert('insert', '    ')
            return 'break'
        start_line = int(start.split('.')[0])
        end_line = int(end.split('.')[0])
        if end.endswith('.0') and end_line > start_line:
            end_line -= 1
        widget.edit_separator()
        for line in range(start_line, end_line + 1):
            widget.insert(f'{line}.0', '    ')
        widget.tag_remove('sel', '1.0', 'end')
        widget.tag_add('sel', f'{start_line}.0', f'{end_line}.end')
        return 'break'

    def _on_input_focus_in(self, _event=None) -> None:
        if self._waiting_for_input:
            self.input_text.configure(
                background=self.theme['input_wait_bg'],
                foreground=self.theme['input_wait_fg'],
            )

    def _on_input_focus_out(self, _event=None) -> None:
        if not self._waiting_for_input:
            self.input_text.configure(
                background=self.theme['input_bg'],
                foreground=self.theme['input_fg']
            )

    def _update_input_state(self) -> None:
        self.input_text.configure(state='normal')

    def _focus_input(self) -> None:
        self.input_text.focus_set()

    def _pulse_input_focus(self) -> None:
        self._waiting_for_input = True
        self.input_label.configure(text=f'{INPUT_WAIT_EMOJI} Ожидание ввода:')
        self.input_text.configure(
            background=self.theme['input_wait_bg'],
            foreground=self.theme['input_wait_fg'],
            relief='flat',
            bd=0,
            highlightbackground=self.theme['accent'],
            highlightcolor=self.theme['accent'],
            highlightthickness=1,
        )
        self.input_text.focus_set()

    def _insert_input_newline(self, _event=None) -> str:
        self.input_text.insert('insert', '\n')
        return 'break'

    def _append_input_echo(self, text: str) -> None:
        lines = text.split('\n')
        items: list[tuple[str, str]] = []
        if not lines:
            items.append(('stdin', INPUT_PREFIX))
            items.append(('stdout', '\n'))
        else:
            for idx, line in enumerate(lines):
                items.append(('stdin', INPUT_PREFIX))
                items.append(('stdout', line))
                if idx < len(lines) - 1:
                    items.append(('stdout', '\n'))
            items.append(('stdout', '\n'))
        self._append_output_batch(items)

    def _send_console_input(self, _event=None) -> str:
        if _event is not None and (_event.state & 0x4):
            return 'break'

        text = self.input_text.get('1.0', 'end-1c')
        self.input_text.delete('1.0', 'end')
        
        # Clear the blue highlight after input
        self._waiting_for_input = False
        self.input_text.configure(
            background=self.theme['input_bg'],
            foreground=self.theme['input_fg'],
            relief='flat',
            bd=0,
            highlightbackground=self.theme['border'],
            highlightcolor=self.theme['accent'],
            highlightthickness=1,
        )
        self.input_label.configure(text='Ввод:')

        if self.process and self.process.stdin:
            self._append_input_echo(text)
            try:
                payload = text
                if not payload.endswith('\n'):
                    payload += '\n'
                self.process.stdin.write(payload)
                self.process.stdin.flush()
            except Exception as exc:
                self._append_output(f'ОШИБКА ВВОДА: {exc}\n', tag='status')
        elif self.turtle_running:
            if text.strip():
                self._append_input_echo(text)
            self.input_queue.put(text)
        else:
            if text.strip():
                self._append_input_echo(text)
            self._append_output('Нет запущенного процесса.\n', tag='status')
        return 'break'

    def _select_all_widget(self, widget: tk.Text) -> str:
        widget.focus_set()
        try:
            widget.event_generate('<<SelectAll>>')
        except tk.TclError:
            pass
        if not widget.tag_ranges('sel'):
            widget.tag_add('sel', '1.0', 'end')
        return 'break'

    def _clipboard_copy_widget(self, widget: tk.Text) -> str:
        text = self._get_selection(widget)
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
        return 'break'

    def _clipboard_cut_widget(self, widget: tk.Text) -> str:
        text = self._get_selection(widget)
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self._delete_selection(widget)
        return 'break'

    def _clipboard_paste_widget(self, widget: tk.Text) -> str:
        try:
            text = self.clipboard_get()
        except tk.TclError:
            return 'break'
        self._replace_selection(widget, text)
        return 'break'

    def _undo_widget(self, widget: tk.Text) -> str:
        try:
            widget.edit_undo()
        except tk.TclError:
            pass
        return 'break'

    def _redo_widget(self, widget: tk.Text) -> str:
        try:
            widget.edit_redo()
        except tk.TclError:
            pass
        return 'break'

    def _console_copy(self, _event=None) -> str:
        self._clipboard_copy_widget(self.console)
        return 'break'

    def _get_selection(self, widget: tk.Text) -> str:
        try:
            return widget.get('sel.first', 'sel.last')
        except tk.TclError:
            return ''

    def _delete_selection(self, widget: tk.Text) -> None:
        try:
            widget.delete('sel.first', 'sel.last')
        except tk.TclError:
            pass

    def _replace_selection(self, widget: tk.Text, text: str) -> None:
        try:
            widget.delete('sel.first', 'sel.last')
        except tk.TclError:
            pass
        widget.insert('insert', text)

    def new_tab(self) -> None:
        tab = EditorTab(self)
        tab.virtual_name = self._next_virtual_name()
        self.notebook.add(tab.frame, text=tab.virtual_name)
        self.tabs_by_frame[str(tab.frame)] = tab
        if tab.virtual_name == 'main.py':
            self.main_tab = tab
        self.update_tab_title(tab)
        self.notebook.select(tab.frame)
        tab.text.focus_set()

    def _find_tab_by_filename(self, filename: str) -> EditorTab | None:
        """Find an open tab by its filename (checking both path and virtual_name)."""
        for tab in self.tabs_by_frame.values():
            # Check by path name (for saved files)
            if tab.path and tab.path.name == filename:
                return tab
            # Check by virtual name (for unsaved/temp files)
            if tab.virtual_name and tab.virtual_name == filename:
                return tab
        return None

    def open_file(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            filetypes=[('Python', '*.py'), ('All files', '*.*')],
        )
        if not path:
            return
        file_path = Path(path)
        try:
            content = read_text_file(file_path)
        except Exception as exc:
            messagebox.showerror('Не удалось открыть', str(exc))
            return
        
        # Check if a file with the same name is already open
        existing_tab = self._find_tab_by_filename(file_path.name)
        if existing_tab:
            response = messagebox.askyesno(
                'Файл уже открыт',
                f'Файл "{file_path.name}" уже открыт.\n\nОткрыть новый файл вместо текущего?'
            )
            if not response:
                return
            
            # Try to close the existing tab with save confirmation
            if not self._confirm_discard(existing_tab):
                return
            
            # Close the existing tab
            self.notebook.forget(existing_tab.frame)
            self.tabs_by_frame.pop(str(existing_tab.frame), None)
            # If it was main.py, reset the reference
            if existing_tab is self.main_tab:
                self.main_tab = None
        
        tab = EditorTab(self, file_path)
        tab.set_content(content)
        self.notebook.add(tab.frame, text=file_path.name)
        self.tabs_by_frame[str(tab.frame)] = tab
        # If this is main.py, set the reference
        if file_path.name == 'main.py':
            self.main_tab = tab
        self.update_tab_title(tab)
        self.notebook.select(tab.frame)
        tab.text.focus_set()

    def save_file(self) -> bool:
        tab = self.get_current_tab()
        if not tab:
            return False
        if tab.path is None:
            return self.save_file_as()
        return self._write_file(tab.path, tab)

    def save_file_as(self) -> bool:
        tab = self.get_current_tab()
        if not tab:
            return False
        path = filedialog.asksaveasfilename(
            defaultextension='.py',
            filetypes=[('Python', '*.py'), ('All files', '*.*')],
        )
        if not path:
            return False
        tab.path = Path(path)
        return self._write_file(tab.path, tab)

    def save_all(self) -> bool:
        if not self.tabs_by_frame:
            return False
        tabs = list(self.tabs_by_frame.values())
        unsaved = [tab for tab in tabs if tab.path is None]
        target_dir: Path | None = None
        if unsaved or (self._temporary_mode_active() and self.temp_assets):
            selected = filedialog.askdirectory(parent=self, title='Папка для сохранения модулей')
            if not selected:
                return False
            target_dir = Path(selected)
        for tab in tabs:
            if tab.path and tab.modified:
                if not self._write_file(tab.path, tab):
                    return False
        if unsaved and target_dir:
            used: set[str] = set()

            def unique_name(base: str) -> str:
                stem, suffix = os.path.splitext(base)
                if not suffix:
                    suffix = '.py'
                candidate = f'{stem}{suffix}'
                index = 2
                while candidate in used or (target_dir / candidate).exists():
                    candidate = f'{stem}_{index}{suffix}'
                    index += 1
                used.add(candidate)
                return candidate

            for tab in unsaved:
                name = unique_name(self._runtime_name_for_tab(tab))
                path = target_dir / name
                tab.path = path
                if not self._write_file(path, tab):
                    return False
                if tab.temp_name:
                    temp_path = self.temp_session_dir / tab.temp_name
                    if temp_path.exists():
                        try:
                            temp_path.unlink()
                        except Exception:
                            pass
                    tab.temp_name = None
        if self.temp_assets and target_dir:
            used_names: set[str] = set()
            for asset in self._temp_assets_paths():
                if not asset.exists():
                    continue
                dest_name = asset.name
                stem, suffix = os.path.splitext(dest_name)
                index = 2
                while dest_name in used_names or (target_dir / dest_name).exists():
                    dest_name = f'{stem}_{index}{suffix}'
                    index += 1
                used_names.add(dest_name)
                try:
                    shutil.copy2(asset, target_dir / dest_name)
                except Exception:
                    pass
            self.temp_assets.clear()
        return True

    def save_archive(self) -> None:
        if not self.tabs_by_frame:
            messagebox.showinfo('Архив', 'Нет открытых модулей для архивации.')
            return

        target = filedialog.asksaveasfilename(
            defaultextension='.zip',
            filetypes=[('ZIP', '*.zip')],
        )
        if not target:
            return

        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        staging = RUNTIME_DIR / 'archive'
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True, exist_ok=True)

        used: set[str] = set()

        def unique_name(base: str) -> str:
            stem, suffix = os.path.splitext(base)
            if not suffix:
                suffix = '.py'
            candidate = f'{stem}{suffix}'
            index = 2
            while candidate in used:
                candidate = f'{stem}_{index}{suffix}'
                index += 1
            used.add(candidate)
            return candidate

        for tab in self.tabs_by_frame.values():
            name = unique_name(self._runtime_name_for_tab(tab))
            dest = staging / name
            dest.write_text(tab.get_content(), encoding='utf-8')
        for asset in self._temp_assets_paths():
            if not asset.exists():
                continue
            try:
                shutil.copy2(asset, staging / unique_name(asset.name))
            except Exception:
                pass

        try:
            if os.name == 'nt':
                src = str(staging / '*')
                ps_src = src.replace("'", "''")
                ps_dst = target.replace("'", "''")
                cmd = [
                    'powershell',
                    '-NoProfile',
                    '-Command',
                    f"Compress-Archive -Path '{ps_src}' -DestinationPath '{ps_dst}' -Force",
                ]
            else:
                cmd = ['tar', '-czf', target, '-C', str(staging), '.']

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or 'Не удалось создать архив.')
        except FileNotFoundError:
            messagebox.showerror('Архив', 'Системный архиватор не найден.')
            return
        except Exception as exc:
            messagebox.showerror('Архив', str(exc))
            return
        finally:
            shutil.rmtree(staging, ignore_errors=True)

        messagebox.showinfo('Архив', f'Архив сохранён: {target}')

    def import_temp_images(self) -> None:
        if not self._temporary_mode_active():
            messagebox.showinfo('Импорт картинок', 'Импорт доступен только в режиме временных файлов.')
            return
        paths = filedialog.askopenfilenames(
            parent=self,
            title='Импортировать картинки',
            filetypes=[
                ('Изображения', '*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.webp'),
                ('Все файлы', '*.*'),
            ],
        )
        if not paths:
            return
        self._ensure_temp_session_dir()

        def unique_name(base: str) -> str:
            stem, suffix = os.path.splitext(base)
            candidate = f'{stem}{suffix}'
            index = 2
            while candidate in self.temp_assets or (self.temp_session_dir / candidate).exists():
                candidate = f'{stem}_{index}{suffix}'
                index += 1
            return candidate

        added = 0
        for path in paths:
            try:
                source = Path(path)
                dest_name = unique_name(source.name)
                shutil.copy2(source, self.temp_session_dir / dest_name)
                self.temp_assets.add(dest_name)
                added += 1
            except Exception:
                continue
        if added:
            messagebox.showinfo('Импорт картинок', f'Импортировано: {added}')

    def show_temp_images_list(self) -> None:
        if not self._temporary_mode_active():
            return
        if not self.temp_session_dir.exists():
            messagebox.showinfo('Список картинок', 'Нет импортированных картинок.')
            return
        
        images = []
        for ext in ('*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp', '*.webp'):
            for p in self.temp_session_dir.glob(ext):
                images.append(p.name)
        
        if not images:
            messagebox.showinfo('Список картинок', 'Нет импортированных картинок.')
            return
        
        images.sort()
        list_str = '\n'.join(images)
        dialog = tk.Toplevel(self)
        dialog.title('Список картинок')
        dialog.configure(background=self.theme['app_bg'])
        dialog.geometry('400x500')
        
        frame = ttk.Frame(dialog, padding=12)
        frame.pack(fill='both', expand=True)
        
        ttk.Label(frame, text='Импортированные картинки:').pack(anchor='w', pady=(0, 6))
        
        text = tk.Text(
            frame,
            wrap='word',
            font=CONSOLE_FONT,
            background=self.theme['input_bg'],
            foreground=self.theme['input_fg'],
            insertbackground=self.theme['input_fg'],
        )
        text.pack(fill='both', expand=True)
        text.insert('1.0', list_str)
        text.configure(state='disabled')
        
        ttk.Button(frame, text='Закрыть', command=dialog.destroy).pack(anchor='e', pady=(12, 0))

    def rename_current_tab(self) -> None:
        tab = self.get_current_tab()
        if not tab:
            return
        if tab is self.main_tab:
            messagebox.showinfo('Main.py', 'Нельзя переименовать main.py.')
            return
        current = tab.path.name if tab.path else (tab.virtual_name or '')
        new_name = simpledialog.askstring('Переименовать модуль', 'Новое имя модуля:', initialvalue=current)
        if not new_name:
            return
        new_name = new_name.strip()
        if not new_name:
            return
        if not os.path.splitext(new_name)[1]:
            new_name += '.py'
        if tab.path:
            new_path = tab.path.with_name(new_name)
            if new_path.exists():
                messagebox.showerror('Переименование', 'Файл с таким именем уже существует.')
                return
            try:
                tab.path.rename(new_path)
            except Exception as exc:
                messagebox.showerror('Переименование', str(exc))
                return
            tab.path = new_path
            tab.virtual_name = None
        else:
            old_temp = None
            if tab.temp_name:
                old_temp = self.temp_session_dir / tab.temp_name
            tab.virtual_name = new_name
            tab.temp_name = None
            if old_temp and old_temp.exists() and self._temporary_mode_active():
                new_temp = self._temp_path_for_tab(tab)
                try:
                    old_temp.rename(new_temp)
                except Exception:
                    pass
        self.update_tab_title(tab)

    def _write_file(self, path: Path, tab: EditorTab) -> bool:
        try:
            path.write_text(tab.get_content(), encoding='utf-8')
        except Exception as exc:
            messagebox.showerror('Не удалось сохранить', str(exc))
            return False
        if tab is not self.main_tab:
            tab.virtual_name = None
        tab.modified = False
        tab.text.edit_modified(False)
        self.update_tab_title(tab)
        return True

    def update_tab_title(self, tab: EditorTab) -> None:
        if tab is self.main_tab:
            title = 'main.py'
        else:
            title = tab.path.name if tab.path else (tab.virtual_name or 'Без имени')
        if tab.modified:
            title = f'*{title}'
        self.notebook.tab(tab.frame, text=title)

    def _next_virtual_name(self) -> str:
        if not self._main_created:
            self._main_created = True
            return 'main.py'
        used = set()
        for tab in self.tabs_by_frame.values():
            name = tab.path.name if tab.path else (tab.virtual_name or '')
            lower = name.lower()
            if lower.startswith('module') and lower.endswith('.py'):
                digits = lower[6:-3]
                if digits.isdigit():
                    used.add(int(digits))
        index = 1
        while index in used:
            index += 1
        return f'module{index}.py'

    def _ensure_main_tab(self) -> EditorTab:
        if self.main_tab:
            return self.main_tab
        tab = EditorTab(self)
        tab.virtual_name = 'main.py'
        self.notebook.add(tab.frame, text='main.py')
        self.tabs_by_frame[str(tab.frame)] = tab
        self.main_tab = tab
        self._main_created = True
        self.update_tab_title(tab)
        self.notebook.select(tab.frame)
        tab.text.focus_set()
        return tab

    def get_current_tab(self) -> EditorTab | None:
        frame_id = self.notebook.select()
        if not frame_id:
            return None
        return self.tabs_by_frame.get(frame_id)

    def close_current_tab(self) -> None:
        tab = self.get_current_tab()
        if not tab:
            return
        if tab is self.main_tab:
            messagebox.showinfo('Main.py', 'Нельзя закрыть main.py. Он всегда должен быть в проекте.')
            return
        if not self._confirm_discard(tab):
            return
        self.notebook.forget(tab.frame)
        self.tabs_by_frame.pop(str(tab.frame), None)
        if not self.tabs_by_frame:
            self.new_tab()

    def _on_tab_changed(self, _event=None) -> None:
        self._focus_editor()

    def _focus_editor(self) -> None:
        tab = self.get_current_tab()
        if tab and tab.text.winfo_exists():
            tab.text.focus_set()

    def _cycle_tab(self, direction: int) -> str:
        tabs = self.notebook.tabs()
        if not tabs:
            return 'break'
        current = self.notebook.select()
        try:
            index = tabs.index(current)
        except ValueError:
            index = 0
        next_index = (index + direction) % len(tabs)
        self.notebook.select(tabs[next_index])
        self._focus_editor()
        return 'break'

    def _confirm_discard(self, tab: EditorTab) -> bool:
        if not tab.modified:
            return True
        message = 'Сохранить изменения перед закрытием?'
        if self._closing and self._has_temp_files():
            message += '\n\nВременные файлы будут потеряны после закрытия программы.'
        response = messagebox.askyesnocancel('Несохранённые изменения', message)
        if response is None:
            return False
        if response:
            return self._save_or_cancel(tab)
        return True

    def _save_or_cancel(self, tab: EditorTab) -> bool:
        if tab.path is None:
            path = filedialog.asksaveasfilename(
                defaultextension='.py',
                filetypes=[('Python', '*.py'), ('All files', '*.*')],
            )
            if not path:
                return False
            tab.path = Path(path)
        return self._write_file(tab.path, tab)

    def on_exit(self) -> None:
        self._closing = True
        self.turtle_abort = True
        self.step_abort = True
        for tab in list(self.tabs_by_frame.values()):
            if not self._confirm_discard(tab):
                # Закрытие отменено — восстанавливаем флаги, иначе застрявший
                # _closing навсегда ломает перезапуск и обрывает текущий запуск.
                self._closing = False
                self.turtle_abort = False
                self.step_abort = False
                return
        self.stop_process()
        self._clear_temp_session()
        self.destroy()

    def restart_app(self) -> None:
        self._closing = True
        self.turtle_abort = True
        self.step_abort = True
        for tab in list(self.tabs_by_frame.values()):
            if not self._confirm_discard(tab):
                self._closing = False
                self.turtle_abort = False
                self.step_abort = False
                return
        self.stop_process()
        self._clear_temp_session()
        executable = sys.executable
        args = [executable] + sys.argv
        if os.name == 'nt':
            # На Windows настоящего exec нет: os.execv порождает новый процесс
            # и асинхронно завершает текущий. Из-за этого старый экземпляр
            # (окно, удержанные хендлы временной сессии, дочерние процессы)
            # может пережить перезапуск и конфликтовать с новым — отсюда
            # «куча ошибок». Поэтому запускаем новый экземпляр независимым
            # процессом и гарантированно завершаем текущий.
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            try:
                subprocess.Popen(
                    args,
                    close_fds=True,
                    creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                )
            except Exception as exc:
                self._closing = False
                messagebox.showerror('Не удалось перезапустить', str(exc))
                return
            self.destroy()
            os._exit(0)
        self.destroy()
        os.execv(executable, args)

    def run_current(self, step_mode: bool | None = None) -> None:
        if self._restart_pending:
            # Перезапуск уже запланирован — игнорируем повторные клики/F5/меню,
            # иначе накопятся параллельные цепочки _schedule_restart и программа
            # запустится несколько раз подряд.
            return
        tab = self.main_tab or self.get_current_tab()
        if tab is None or tab is not self.main_tab:
            tab = self._ensure_main_tab()
        if not tab:
            return
        if self._is_running():
            # Кнопка работает как «Перезапустить»: останавливаем текущий
            # запуск и автоматически стартуем заново. Запуск нельзя начинать
            # здесь же синхронно — turtle/пошаговый режим выполняются в главном
            # потоке через after-колбэки, и этот вызов может быть реентрантным
            # (из self.update() ещё живого выполнения). Поэтому сначала гасим
            # текущий запуск, а новый ставим в очередь до его фактического конца.
            if step_mode is None:
                step_mode = self.step_mode
            self._restart_pending = True
            self._update_run_controls()
            self.stop_process()
            self._schedule_restart(bool(step_mode))
            return
        self._start_run(tab, step_mode)

    def _schedule_restart(self, step_mode: bool) -> None:
        # Ждём, пока предыдущий запуск действительно завершится (сбросит
        # process/turtle_running/inline_running), и только потом стартуем заново.
        if self._closing:
            self._restart_pending = False
            return
        if self._is_running():
            self.after(50, lambda: self._schedule_restart(step_mode))
            return
        tab = self.main_tab or self.get_current_tab()
        if tab is None or tab is not self.main_tab:
            tab = self._ensure_main_tab()
        # Снимаем флаг перед стартом: дальше состояние «работает» обеспечит сам
        # новый запуск.
        self._restart_pending = False
        if not tab:
            self._update_run_controls()
            return
        self._start_run(tab, step_mode)

    def _start_run(self, tab: EditorTab, step_mode: bool | None) -> None:
        if step_mode is None:
            step_mode = False

        run_context = self._prepare_run_context(tab)
        if not run_context:
            # Перезапуск отменён (диалог сохранения отклонён) — снимаем
            # «завис» кнопки: _restart_pending уже False, _is_running() False,
            # поэтому явно обновляем контролы чтобы кнопка стала «Запустить».
            self._update_run_controls()
            return
        script_path, runtime_dir = run_context

        # Сбрасываем состояние поля ввода от прошлой сессии, чтобы синяя
        # подсветка «Ожидание ввода» не переходила в новый запуск.
        self._waiting_for_input = False
        self.input_label.configure(text='Ввод:')
        self.input_text.configure(
            background=self.theme['input_bg'],
            foreground=self.theme['input_fg'],
            relief='solid',
            bd=1,
        )

        self.step_mode = bool(step_mode)
        self.step_abort = False
        # turtle_abort мог остаться True после перезапуска turtle-программы
        # (stop_process для turtle лишь выставляет флаг). Если его не сбросить,
        # новый запуск с input() через _read_gui_input мгновенно завершится.
        self.turtle_abort = False
        self.step_event.clear()
        self._show_step_controls(self.step_mode)

        code = tab.get_content()
        if self._needs_turtle(tab, script_path):
            self._run_turtle_code(code, script_path, runtime_dir, self.step_mode)
            return

        python_exe = get_python_executable()
        if not python_exe:
            messagebox.showerror(
                'Portable Python не найден',
                'Portable Python не найден в папке python.\n'
                'Запусти скрипт запуска в этой папке, чтобы использовать встроенный Python.',
            )
            return

        self.clear_console()
        if self.step_mode:
            self._append_output(f'Построчный запуск: {script_path}\n', tag='status')
            self._run_step_code(code, script_path, runtime_dir)
        else:
            self._append_output(f'Запуск: {script_path}\n', tag='status')
            self._run_in_console(python_exe, script_path, runtime_dir)
        self._focus_input()
        self._update_run_controls()

    def run_current_step(self) -> None:
        self.run_current(step_mode=True)

    def step_next(self) -> None:
        self.step_event.set()

    def _show_step_controls(self, show: bool) -> None:
        if not self.step_next_button:
            return
        if show:
            self.run_toolbar.show(self.step_next_button)
        else:
            self.run_toolbar.hide(self.step_next_button)

    def _run_in_console(self, python_exe: str, script_path: Path, runtime_dir: Path | None) -> None:
        # Очищаем очередь ввода от предыдущей сессии: если старая программа
        # запрашивала input() и пользователь что-то набрал, эти данные не
        # должны «просочиться» в новый запуск.
        while not self.input_queue.empty():
            try:
                self.input_queue.get_nowait()
            except queue.Empty:
                break
        try:
            env = os.environ.copy()
            if runtime_dir:
                current = env.get('PYTHONPATH', '')
                env['PYTHONPATH'] = str(runtime_dir) + (os.pathsep + current if current else '')
            self.process = subprocess.Popen(
                [python_exe, '-u', str(script_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(script_path.parent),
                env=env,
            )
        except Exception as exc:
            self._append_output(f'Ошибка запуска: {exc}\n', tag='status')
            self.process = None
            return

        proc = self.process
        threading.Thread(target=self._read_stream, args=(proc, proc.stdout, 'stdout'), daemon=True).start()
        threading.Thread(target=self._read_stream, args=(proc, proc.stderr, 'stderr'), daemon=True).start()
        threading.Thread(target=self._watch_process, args=(proc,), daemon=True).start()
        self._update_run_controls()

    def _code_uses_turtle(self, code: str) -> bool:
        try:
            tokens = list(tokenize.generate_tokens(io.StringIO(code).readline))
        except Exception:
            return False
        for idx, (tok_type, tok_str, *_rest) in enumerate(tokens):
            if tok_type == tokenize.NAME and tok_str == 'import':
                j = idx + 1
                while j < len(tokens):
                    t_type, t_str, *_ = tokens[j]
                    if t_type in (tokenize.NEWLINE, tokenize.NL):
                        break
                    if t_type == tokenize.NAME and t_str == 'turtle':
                        return True
                    j += 1
            if tok_type == tokenize.NAME and tok_str == 'from':
                j = idx + 1
                while j < len(tokens):
                    t_type, t_str, *_ = tokens[j]
                    if t_type in (tokenize.NEWLINE, tokenize.NL):
                        break
                    if t_type == tokenize.NAME:
                        return t_str == 'turtle'
                    j += 1
        return False

    def _collect_imports(self, code: str) -> set[str]:
        imports: set[str] = set()
        try:
            tokens = list(tokenize.generate_tokens(io.StringIO(code).readline))
        except Exception:
            return imports
        idx = 0
        while idx < len(tokens):
            tok_type, tok_str, *_ = tokens[idx]
            if tok_type == tokenize.NAME and tok_str == 'import':
                idx += 1
                while idx < len(tokens):
                    t_type, t_str, *_ = tokens[idx]
                    if t_type in (tokenize.NEWLINE, tokenize.NL):
                        break
                    if t_type == tokenize.NAME:
                        imports.add(t_str.split('.')[0])
                    idx += 1
            elif tok_type == tokenize.NAME and tok_str == 'from':
                idx += 1
                while idx < len(tokens):
                    t_type, t_str, *_ = tokens[idx]
                    if t_type in (tokenize.NEWLINE, tokenize.NL):
                        break
                    if t_type == tokenize.NAME:
                        imports.add(t_str.split('.')[0])
                        break
                    idx += 1
            idx += 1
        return imports

    def _module_name_for_tab(self, tab: EditorTab) -> str:
        if tab.path:
            return tab.path.stem
        name = tab.virtual_name or ''
        if name.lower().endswith('.py'):
            return name[:-3]
        return name

    def _load_module_source(self, module_name: str, script_path: Path | None) -> str | None:
        for other in self.tabs_by_frame.values():
            mod_name = self._module_name_for_tab(other)
            if mod_name == module_name:
                return other.get_content()
        if script_path:
            candidate = script_path.parent / f'{module_name}.py'
            if candidate.exists():
                try:
                    return read_text_file(candidate)
                except Exception:
                    return None
        return None

    def _needs_turtle(self, tab: EditorTab, script_path: Path | None) -> bool:
        root_code = tab.get_content()
        if self._code_uses_turtle(root_code):
            return True
        pending = list(self._collect_imports(root_code))
        seen: set[str] = set()
        while pending:
            module_name = pending.pop()
            if module_name in seen:
                continue
            seen.add(module_name)
            source = self._load_module_source(module_name, script_path)
            if not source:
                continue
            if self._code_uses_turtle(source):
                return True
            pending.extend(self._collect_imports(source) - seen)
        return False

    def _show_turtle_panel(self, show: bool) -> None:
        if show and not self.turtle_visible:
            self.editor_paned.add(self.turtle_frame, stretch='never', minsize=424)
            self.turtle_visible = True
            # Lock the sash to prevent resizing
            self.after(10, lambda: self._lock_turtle_sash())
            self.after_idle(self._update_sash_grips)
        elif not show and self.turtle_visible:
            self.editor_paned.forget(self.turtle_frame)
            self.turtle_visible = False
            self.after_idle(self._update_sash_grips)

    def _lock_turtle_sash(self) -> None:
        """Lock the sash between editor and turtle panel to prevent resizing."""
        if self.turtle_visible:
            try:
                # Get current sash position and restore it on any change
                self.turtle_frame.width = 416
                self.turtle_frame.configure(width=416)
            except Exception:
                pass

    def _on_paned_click(self, event) -> str:
        """Prevent sash dragging when turtle panel is visible."""
        if not self.turtle_visible:
            return 'continue'
        
        # Check if click is on the sash (approximately in the middle between panels)
        try:
            sash_x = self.editor_paned.sash_coord(0)[0] if self.editor_paned.sash_coord(0) else None
            if sash_x and abs(event.x - sash_x) < 5:
                # Click on sash - prevent dragging
                return 'break'
        except Exception:
            pass
        return 'continue'

    def _prepare_turtle_screen(self) -> None:
        import turtle

        self._show_turtle_panel(True)
        self.turtle_canvas.focus_set()

        if not self._turtle_initialized or not self.turtle_screen:
            self.turtle_canvas.delete('all')
            turtle.Turtle._screen = None
            turtle.Turtle._pen = None
            self.turtle_screen = turtle.TurtleScreen(self.turtle_canvas)
            self._turtle_initialized = True
        else:
            try:
                self.turtle_screen.clear()
            except Exception:
                self.turtle_canvas.delete('all')

        self.update_idletasks()
        self._turtle_custom_coords = False
        self._turtle_setworld = self.turtle_screen.setworldcoordinates
        self._sync_turtle_world()
        self.turtle_screen.bgcolor(self.theme['panel_bg'])
        self.turtle_screen._delayvalue = 10
        try:
            self.turtle_screen.listen()
        except Exception:
            pass
        self._patch_turtle_keys()
        self._patch_turtle_update()

        turtle.Turtle._screen = self.turtle_screen
        turtle.Turtle._pen = None
        turtle._screen = self.turtle_screen
        turtle._pen = None
        turtle.Screen = lambda: self.turtle_screen
        turtle.getscreen = lambda: self.turtle_screen

        turtle._getscreen = lambda: self.turtle_screen
        turtle._getcanvas = lambda: self.turtle_canvas

        for name in ('bye', 'exitonclick', 'done', 'mainloop'):
            setattr(turtle, name, lambda *args, **kwargs: None)
        self.turtle_screen.bye = lambda *args, **kwargs: None
        self.turtle_screen.mainloop = lambda *args, **kwargs: None
        self._wrap_turtle_setworld()

    def _patch_turtle_keys(self) -> None:
        if not self.turtle_screen:
            return
        key_map = {
            'up': 'Up',
            'down': 'Down',
            'left': 'Left',
            'right': 'Right',
            'esc': 'Escape',
            'escape': 'Escape',
            'space': 'space',
        }

        def normalize(key: str | None) -> str | None:
            if not key or not isinstance(key, str):
                return key
            return key_map.get(key, key)

        for name in ('onkey', 'onkeypress', 'onkeyrelease'):
            original = getattr(self.turtle_screen, name, None)
            if not callable(original):
                continue

            def make_wrapper(func):
                def wrapped(fun, key=None):
                    return func(fun, normalize(key))

                return wrapped

            setattr(self.turtle_screen, name, make_wrapper(original))

    def _patch_turtle_update(self) -> None:
        import turtle

        if hasattr(turtle.Turtle, 'update'):
            return

        def _update(self_turtle):
            try:
                self_turtle.getscreen().update()
            except Exception:
                pass

        turtle.Turtle.update = _update

    def _wrap_turtle_setworld(self) -> None:
        if not self.turtle_screen or not self._turtle_setworld:
            return
        original = self._turtle_setworld

        def wrapped(*args, **kwargs):
            self._turtle_custom_coords = True
            return original(*args, **kwargs)

        self.turtle_screen.setworldcoordinates = wrapped

    def _sync_turtle_world(self) -> None:
        if not self.turtle_screen or self._turtle_custom_coords:
            return
        # Fixed canvas size: 400x400 pixels
        w = 400
        h = 400
        if self._turtle_setworld:
            try:
                if self.turtle_screen:
                    self.turtle_screen.canvwidth = w
                    self.turtle_screen.canvheight = h
                self._turtle_setworld(-w / 2, -h / 2, w / 2, h / 2)
            except Exception:
                pass

    def _on_turtle_canvas_resize(self, _event=None) -> None:
        self._sync_turtle_world()

    def _read_gui_input(self, prompt: str = '') -> str:
        if prompt:
            self._append_output(str(prompt), tag='stdout')
        self._focus_input()
        while True:
            if self.turtle_abort or self.step_abort or self._closing:
                raise SystemExit
            try:
                return self.input_queue.get_nowait()
            except queue.Empty:
                try:
                    self.update()
                except tk.TclError:
                    raise SystemExit
                time.sleep(0.01)

    def _run_turtle_code(
        self,
        code: str,
        script_path: Path,
        runtime_dir: Path | None,
        step_mode: bool = False,
    ) -> None:
        self.clear_console()
        self._append_output(f'Запуск (turtle): {script_path}\n', tag='status')
        self._prepare_turtle_screen()
        self.turtle_running = True
        self.turtle_abort = False
        while not self.input_queue.empty():
            try:
                self.input_queue.get_nowait()
            except queue.Empty:
                break
        self._update_run_controls()

        def _execute() -> None:
            globals_dict = {
                '__name__': '__main__',
                '__file__': str(script_path),
            }
            prev_trace = sys.gettrace()
            prev_cwd = os.getcwd()
            prev_input = builtins.input
            prev_sleep = time.sleep
            script_dir = str(script_path.parent)
            path_inserted = False
            runtime_inserted = False
            last_tick = time.perf_counter()

            def patched_sleep(seconds: float) -> None:
                if self.turtle_abort or self._closing:
                    return
                if seconds < 0:
                    seconds = 0
                end = time.perf_counter() + seconds
                while True:
                    remaining = end - time.perf_counter()
                    if remaining <= 0:
                        break
                    try:
                        self.update()
                    except Exception:
                        pass
                    if self.turtle_abort or self._closing:
                        break
                    step = min(remaining, 0.01)
                    prev_sleep(step)

            def tracer(_frame, event, _arg):
                nonlocal last_tick
                if self.turtle_abort or self._closing:
                    raise SystemExit
                if event == 'line':
                    should_pause = False
                    if step_mode:
                        # Only pause if we are in the user's script
                        if self._is_user_step_frame(_frame, script_path, runtime_dir):
                            should_pause = True
                            self.highlight_execution_line(script_path, _frame.f_lineno)

                    if should_pause:
                        self._wait_for_step()
                        self.clear_execution_highlights()
                    else:
                        now = time.perf_counter()
                        if now - last_tick >= TURTLE_UI_PUMP_INTERVAL:
                            last_tick = now
                            try:
                                if self.turtle_screen:
                                    t_val = getattr(self.turtle_screen, '_tracer', 1)
                                    if t_val:
                                        self.turtle_screen.update()
                                self.update()
                            except Exception:
                                pass
                return tracer

            if not step_mode:
                time.sleep = patched_sleep
            sys.settrace(tracer)
            try:
                builtins.input = self._read_gui_input
                globals_dict['input'] = self._read_gui_input
                if runtime_dir:
                    runtime_str = str(runtime_dir)
                    if runtime_str not in sys.path:
                        sys.path.insert(0, runtime_str)
                        runtime_inserted = True
                if script_dir and script_dir not in sys.path:
                    insert_at = 1 if runtime_inserted else 0
                    sys.path.insert(insert_at, script_dir)
                    path_inserted = True
                try:
                    os.chdir(script_dir)
                except OSError:
                    pass
                exec(compile(code, str(script_path), 'exec'), globals_dict)
            except SystemExit:
                if not self._closing:
                    self._append_output('Остановлено\n', tag='status')
            except Exception:
                self._append_output(traceback.format_exc(), tag='stderr')
            finally:
                sys.settrace(prev_trace)
                builtins.input = prev_input
                if not step_mode:
                    time.sleep = prev_sleep
                self.turtle_running = False
                self.step_mode = False
                if not self._closing:
                    self._show_step_controls(False)
                    self._update_run_controls()
                    if self.turtle_screen:
                        try:
                            self.turtle_screen.update()
                        except Exception:
                            pass
                if path_inserted:
                    try:
                        sys.path.remove(script_dir)
                    except ValueError:
                        pass
                if runtime_inserted:
                    try:
                        sys.path.remove(str(runtime_dir))
                    except ValueError:
                        pass
                try:
                    os.chdir(prev_cwd)
                except OSError:
                    pass
                if not self._closing:
                    self._append_output('Готово.\n', tag='status')

        self.after(10, _execute)

    def _wait_for_step(self) -> None:
        if not self.step_mode:
            return
        self.step_event.clear()
        while not self.step_event.is_set():
            if self.step_abort or self.turtle_abort or self._closing:
                raise SystemExit
            try:
                self.update()
            except tk.TclError:
                raise SystemExit
            time.sleep(0.01)

    def _run_step_code(self, code: str, script_path: Path, runtime_dir: Path | None) -> None:
        # Очищаем очередь ввода от предыдущей сессии (аналогично _run_in_console).
        while not self.input_queue.empty():
            try:
                self.input_queue.get_nowait()
            except queue.Empty:
                break
        self.inline_running = True
        self.step_abort = False
        self._update_run_controls()

        class _ConsoleWriter:
            def __init__(self, app: 'PortableIDE', tag: str) -> None:
                self.app = app
                self.tag = tag

            def write(self, data: str) -> int:
                if data:
                    self.app._append_output(data, tag=self.tag)
                return len(data)

            def flush(self) -> None:
                return None

        def _execute() -> None:
            globals_dict = {
                '__name__': '__main__',
                '__file__': str(script_path),
            }
            prev_trace = sys.gettrace()
            prev_cwd = os.getcwd()
            prev_input = builtins.input
            prev_stdout = sys.stdout
            prev_stderr = sys.stderr
            prev_sleep = time.sleep
            script_dir = str(script_path.parent)
            path_inserted = False
            runtime_inserted = False

            def patched_sleep(seconds: float) -> None:
                if self.step_abort or self._closing:
                    return
                if seconds < 0:
                    seconds = 0
                end = time.perf_counter() + seconds
                while True:
                    remaining = end - time.perf_counter()
                    if remaining <= 0:
                        break
                    try:
                        self.update()
                    except Exception:
                        pass
                    if self.step_abort or self._closing:
                        break
                    step = min(remaining, 0.01)
                    prev_sleep(step)

            def tracer(frame, event, _arg):
                if self.step_abort or self._closing:
                    raise SystemExit
                # Ensure UI stays responsive
                if event == 'line':
                    try:
                        self.update()
                    except Exception:
                        pass
                    
                if event == 'line' and self._is_user_step_frame(frame, script_path, runtime_dir):
                    self.highlight_execution_line(script_path, frame.f_lineno)
                    self._wait_for_step()
                    self.clear_execution_highlights()
                return tracer

            time.sleep = patched_sleep
            sys.settrace(tracer)
            try:
                builtins.input = self._read_gui_input
                globals_dict['input'] = self._read_gui_input
                sys.stdout = _ConsoleWriter(self, 'stdout')
                sys.stderr = _ConsoleWriter(self, 'stderr')
                if runtime_dir:
                    runtime_str = str(runtime_dir)
                    if runtime_str not in sys.path:
                        sys.path.insert(0, runtime_str)
                        runtime_inserted = True
                if script_dir and script_dir not in sys.path:
                    insert_at = 1 if runtime_inserted else 0
                    sys.path.insert(insert_at, script_dir)
                    path_inserted = True
                try:
                    os.chdir(script_dir)
                except OSError:
                    pass
                exec(compile(code, str(script_path), 'exec'), globals_dict)
            except SystemExit:
                if not self._closing:
                    self._append_output('Остановлено\n', tag='status')
            except Exception:
                self._append_output(traceback.format_exc(), tag='stderr')
            finally:
                sys.settrace(prev_trace)
                builtins.input = prev_input
                sys.stdout = prev_stdout
                sys.stderr = prev_stderr
                time.sleep = prev_sleep
                if path_inserted:
                    try:
                        sys.path.remove(script_dir)
                    except ValueError:
                        pass
                if runtime_inserted:
                    try:
                        sys.path.remove(str(runtime_dir))
                    except ValueError:
                        pass
                try:
                    os.chdir(prev_cwd)
                except OSError:
                    pass
                self.inline_running = False
                self.step_mode = False
                if not self._closing:
                    self._show_step_controls(False)
                    self._update_run_controls()
                    self._append_output('Готово.\n', tag='status')

        self.after(10, _execute)

    def highlight_execution_line(self, script_path: Path, lineno: int) -> None:
        # Determine which tab corresponds to this script
        target_tab = None
        
        # Check main tab
        if self.main_tab:
            # Special case for main.py running from snapshot
            if self.main_tab.path and self.main_tab.path == script_path:
                target_tab = self.main_tab
            elif script_path.name == 'main.py': 
                # Relaxed check for main.py if running from temp/snapshot
                if not self.main_tab.path and self.main_tab.virtual_name == 'main.py':
                    target_tab = self.main_tab
        
        # Check other tabs if not found
        if not target_tab:
            for tab in self.tabs_by_frame.values():
                if tab is self.main_tab:
                    continue
                    
                # Exact path match
                if tab.path and tab.path == script_path:
                    target_tab = tab
                    break
                
                # Snapshot/Temp match by name
                if tab.path is None:
                    # e.g. script_path = .../snapshot/module.py, tab name = module.py
                    if script_path.name == (tab.virtual_name or ''):
                        target_tab = tab
                        break
                    # e.g. script_path = .../snapshot/module_2.py, tab name = module_2.py
                    if script_path.name == tab.temp_name:
                        target_tab = tab
                        break

        if target_tab:
            self.notebook.select(target_tab.frame)
            target_tab.text.see(f'{lineno}.0')
            target_tab.text.tag_add('execution_line', f'{lineno}.0', f'{lineno}.end')
            # Force update to show highlight immediately
            try:
                target_tab.text.update_idletasks()
            except Exception:
                pass

    def clear_execution_highlights(self) -> None:
        for tab in self.tabs_by_frame.values():
            tab.text.tag_remove('execution_line', '1.0', 'end')

    def _is_user_step_frame(self, frame, script_path: Path, runtime_dir: Path | None) -> bool:
        filename = frame.f_code.co_filename
        if not filename:
            return False
        
        # Normalize paths
        try:
            file_path = Path(filename).resolve()
            script_resolved = script_path.resolve()
        except Exception:
            # Fallback for simple name matching if resolve fails
            name = Path(filename).name
            return name == script_path.name

        # Check if it matches the main script
        if file_path == script_resolved:
            return True

        # Check if it is inside the runtime directory (imported modules)
        if runtime_dir:
            try:
                runtime_resolved = runtime_dir.resolve()
                if file_path.is_relative_to(runtime_resolved):
                    return True
            except Exception:
                pass
            
            # Text based check as fallback
            if str(runtime_dir) in str(file_path):
                return True
                
        return False

    def _prepare_run_context(self, tab: EditorTab) -> tuple[Path, Path | None] | None:
        tabs = list(self.tabs_by_frame.values())
        modified_tabs = [t for t in tabs if t.modified]
        if modified_tabs:
            mode = self.save_before_run_var.get()
            if mode == 'ask':
                response = messagebox.askyesnocancel(
                    'Несохранённые изменения',
                    'Сохранить изменения перед запуском? (выбор будет запомнен)',
                )
                if response is None:
                    return None
                mode = 'always' if response else 'never'
                self.save_before_run_var.set(mode)
                self.save_on_run_preference = bool(response)
                self._update_temp_mode_ui()
            elif mode == 'always':
                self.save_on_run_preference = True
            elif mode == 'never':
                self.save_on_run_preference = False
            if mode == 'always':
                for t in modified_tabs:
                    if t.path and not self._write_file(t.path, t):
                        return None

        needs_runtime = (
            self._temporary_mode_active()
            or any(t.path is None for t in tabs)
            or any(t.modified for t in tabs)
        )
        if needs_runtime:
            if self._temporary_mode_active():
                primary_path = self._sync_temp_session(tab)
                runtime_dir = self.temp_session_dir
            else:
                primary_path, runtime_dir = self._build_runtime_snapshot(tab)
            if self._temporary_mode_active() or tab.path is None or tab.modified:
                return primary_path, runtime_dir
            if tab.path is None:
                return primary_path, runtime_dir
            return tab.path, runtime_dir

        if tab.path is None:
            return None
        return tab.path, None

    def _runtime_name_for_tab(self, tab: EditorTab) -> str:
        if tab is self.main_tab:
            name = 'main.py'
        elif tab.path:
            name = tab.path.name
        else:
            name = tab.virtual_name or 'module'
        if not name.lower().endswith('.py'):
            name = f'{name}.py'
        return name

    def _build_runtime_snapshot(self, primary_tab: EditorTab) -> tuple[Path, Path]:
        snapshot_dir = RUNTIME_DIR / 'snapshot'
        if snapshot_dir.exists():
            shutil.rmtree(snapshot_dir, ignore_errors=True)
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        used: set[str] = set()

        def unique_name(base: str) -> str:
            stem, suffix = os.path.splitext(base)
            if not suffix:
                suffix = '.py'
            candidate = f'{stem}{suffix}'
            index = 2
            while candidate in used:
                candidate = f'{stem}_{index}{suffix}'
                index += 1
            used.add(candidate)
            return candidate

        primary_name = unique_name(self._runtime_name_for_tab(primary_tab))
        primary_path = snapshot_dir / primary_name
        primary_path.write_text(primary_tab.get_content(), encoding='utf-8')

        for tab in self.tabs_by_frame.values():
            if tab is primary_tab:
                continue
            name = unique_name(self._runtime_name_for_tab(tab))
            (snapshot_dir / name).write_text(tab.get_content(), encoding='utf-8')

        return primary_path, snapshot_dir

    def _sync_temp_session(self, primary_tab: EditorTab) -> Path:
        self._ensure_temp_session_dir()
        desired: set[str] = set()
        for tab in self.tabs_by_frame.values():
            name = self._temp_name_for_tab(tab)
            desired.add(name)
            (self.temp_session_dir / name).write_text(tab.get_content(), encoding='utf-8')
        for candidate in self.temp_session_dir.glob('*.py'):
            if candidate.name not in desired:
                try:
                    candidate.unlink()
                except Exception:
                    pass
        return self.temp_session_dir / self._temp_name_for_tab(primary_tab)

    def _read_stream(self, proc, stream, tag: str) -> None:
        if stream is None:
            return
        while True:
            chunk = stream.read(1)
            if chunk == '':
                break
            self.output_queue.put((tag, chunk, proc))
        stream.close()

    def _watch_process(self, proc) -> None:
        if proc is None:
            return
        code = proc.wait()
        self.output_queue.put(('status', f'\nПроцесс завершён, код: {code}\n', proc))
        self.output_queue.put(('done', None, proc))

    def _poll_output(self) -> None:
        if self._closing:
            # Окно закрывается/перезапускается — не трогаем виджеты и не
            # перепланируем колбэк на уже разрушенном Tk.
            return
        items: list[tuple[str, str]] = []
        try:
            while True:
                tag, text, owner = self.output_queue.get_nowait()
                # Намеренно остановленный процесс: гасим весь его вывод и статус
                # (об остановке уже сообщили), на 'done' снимаем пометку.
                if owner in self._silenced_procs:
                    if tag == 'done':
                        self._silenced_procs.discard(owner)
                    continue
                # Сообщения от прежнего запуска игнорируем ТОЛЬКО если уже есть
                # новый процесс: иначе их 'done' обнулит self.process нового
                # процесса после перезапуска, а старый вывод засорит консоль.
                # Если нового процесса нет (self.process is None) — это обычное
                # завершение, показываем хвостовой вывод и статус как есть.
                if self.process is not None and owner is not self.process:
                    continue
                if tag == 'done':
                    self.process = None
                    self._update_run_controls()
                else:
                    items.append((tag, text or ''))
        except queue.Empty:
            pass
        if items:
            self._append_output_batch(items)
        self.after(POLL_DELAY_MS, self._poll_output)

    def _append_output_batch(self, items: list[tuple[str, str]]) -> None:
        self.console.configure(state='normal')
        combined = ''
        for tag, text in items:
            self.console.insert('end', text, tag)
            combined += text
        self.console.see('end')
        self.console.configure(state='disabled')
        if self.process and combined:
            self._maybe_focus_input_on_output(combined)

    def _append_output(self, text: str, tag: str = 'stdout') -> None:
        self._append_output_batch([(tag, text)])

    def _maybe_focus_input_on_output(self, text: str) -> None:
        if not text.strip():
            return
        if not text.endswith('\n'):
            self._pulse_input_focus()

    def clear_console(self) -> None:
        self.console.configure(state='normal')
        self.console.delete('1.0', 'end')
        self.console.configure(state='disabled')

    def stop_process(self) -> None:
        if self.turtle_running:
            self.turtle_abort = True
            return
        if self.inline_running:
            self.step_abort = True
            self.step_event.set()
            return
        if not self.process:
            self._update_run_controls()
            return
        proc = self.process
        # Помечаем процесс «заглушённым»: мы убиваем его намеренно, поэтому
        # сообщение его наблюдателя «Процесс завершён, код: N» не нужно — иначе
        # после ручного «Остановить»/перезапуска в консоли появляется и
        # «Остановлено», и противоречащий ему код завершения.
        self._silenced_procs.add(proc)
        try:
            proc.terminate()
            proc.wait(timeout=1.5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        self.process = None
        self._append_output('Остановлено\n', tag='status')
        self._update_run_controls()


if __name__ == '__main__':
    app = PortableIDE()
    app.mainloop()
