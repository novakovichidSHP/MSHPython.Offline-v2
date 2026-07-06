# -*- coding: utf-8 -*-
"""Unit tests for PortableIDE logical components and helper functions."""

import sys
import os
import shutil
import tempfile
import unittest
import importlib.util
from pathlib import Path
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.font as tkfont
import tkinter.messagebox as messagebox

# Setup import path to find ide.py
ROOT = Path(__file__).resolve().parent
APP = ROOT / 'MSHP-IDE-Windows' / 'app' / 'ide.py'

spec = importlib.util.spec_from_file_location('ide_module', APP)
ide = importlib.util.module_from_spec(spec)
sys.modules['ide_module'] = ide
spec.loader.exec_module(ide)

# Suppress message dialogs during testing
messagebox.showerror = lambda title, message: None
messagebox.showwarning = lambda title, message: None
messagebox.showinfo = lambda title, message: None

# Disable console reconfig if not supported, otherwise enforce UTF-8
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


class FakeTab:
    def __init__(self, temp_name=None, path=None, virtual_name=None, content=""):
        self.temp_name = temp_name
        self.path = path
        self.virtual_name = virtual_name
        self._content = content

    def get_content(self):
        return self._content

    def set_content(self, content):
        self._content = content


class FakeStringVar:
    def __init__(self, val=""):
        self.val = val

    def get(self):
        return self.val

    def set(self, val):
        self.val = val


class FakeApp:
    def __init__(self, root=None):
        self.save_before_run_var = FakeStringVar()
        self.temp_assets = []
        self.tabs_by_frame = {}
        self.temp_session_dir = Path("nonexistent_session_dir")
        self._temp_active = True
        self.process = None
        self.turtle_running = False
        self.inline_running = False
        self.main_tab = None
        self._main_created = False
        if root:
            self.notebook = ttk.Notebook(root)
        else:
            self.notebook = None
        self.clipboard_val = ""

    def _temporary_mode_active(self):
        return self._temp_active

    def clipboard_clear(self):
        self.clipboard_val = ""

    def clipboard_append(self, text):
        self.clipboard_val += text

    def clipboard_get(self):
        if not self.clipboard_val:
            raise tk.TclError("clipboard is empty")
        return self.clipboard_val

    def _focus_editor(self):
        pass

    def _runtime_name_for_tab(self, tab):
        return ide.PortableIDE._runtime_name_for_tab(self, tab)

    def _next_virtual_name(self):
        return ide.PortableIDE._next_virtual_name(self)

    def _module_name_for_tab(self, tab):
        return ide.PortableIDE._module_name_for_tab(self, tab)

    def _code_uses_turtle(self, code):
        return ide.PortableIDE._code_uses_turtle(self, code)

    def _collect_imports(self, code):
        return ide.PortableIDE._collect_imports(self, code)

    def _load_module_source(self, module_name, script_path):
        return ide.PortableIDE._load_module_source(self, module_name, script_path)

    def _get_selection(self, widget):
        return ide.PortableIDE._get_selection(self, widget)

    def _delete_selection(self, widget):
        return ide.PortableIDE._delete_selection(self, widget)

    def _replace_selection(self, widget, text):
        return ide.PortableIDE._replace_selection(self, widget, text)

    def _select_all_widget(self, widget):
        return ide.PortableIDE._select_all_widget(self, widget)

    def _clipboard_copy_widget(self, widget):
        return ide.PortableIDE._clipboard_copy_widget(self, widget)

    def _clipboard_cut_widget(self, widget):
        return ide.PortableIDE._clipboard_cut_widget(self, widget)

    def _clipboard_paste_widget(self, widget):
        return ide.PortableIDE._clipboard_paste_widget(self, widget)

    def _undo_widget(self, widget):
        return ide.PortableIDE._undo_widget(self, widget)

    def _redo_widget(self, widget):
        return ide.PortableIDE._redo_widget(self, widget)

    def _bind_if_supported(self, widget, sequence, callback, add=None):
        return ide.PortableIDE._bind_if_supported(self, widget, sequence, callback, add)


class TestIDEUnit(unittest.TestCase):

    # 1. get_best_font
    def test_get_best_font_match(self):
        orig_families = tkfont.families
        try:
            tkfont.families = lambda: ('menlo', 'courier new', 'arial')
            res = ide.get_best_font(['Menlo', 'Courier New'], 'monospace')
            self.assertEqual(res, 'Menlo')
            res2 = ide.get_best_font(['Times New Roman'], 'monospace')
            self.assertEqual(res2, 'monospace')
        finally:
            tkfont.families = orig_families

    # 2. icon
    def test_icon_path_generation(self):
        orig_os_name = ide.os.name
        orig_sys_platform = ide.sys.platform
        try:
            # Windows
            ide.os.name = 'nt'
            ide.sys.platform = 'win32'
            self.assertEqual(ide.icon('🚀', 'Запуск'), '🚀 Запуск')

            # Linux
            ide.os.name = 'posix'
            ide.sys.platform = 'linux'
            self.assertEqual(ide.icon('🚀', 'Запуск'), 'Запуск')
        finally:
            ide.os.name = orig_os_name
            ide.sys.platform = orig_sys_platform

    # 3. read_text_file (UTF-8)
    def test_read_text_file_utf8(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / 'test_utf8.txt'
            p.write_text('hello world', encoding='utf-8')
            self.assertEqual(ide.read_text_file(p), 'hello world')

    # 4. read_text_file (CP1251)
    def test_read_text_file_cp1251(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / 'test_cp1251.txt'
            p.write_bytes('привет'.encode('cp1251'))
            self.assertEqual(ide.read_text_file(p), 'привет')

    # 5. find_python_in_dir (NT structure)
    def test_find_python_in_dir_nt_success(self):
        orig_os_name = ide.os.name
        try:
            ide.os.name = 'nt'
            with tempfile.TemporaryDirectory() as tmpdir:
                p = Path(tmpdir)
                py_exe = p / 'python.exe'
                py_exe.touch()
                res = ide.find_python_in_dir(p)
                self.assertEqual(res, py_exe)
        finally:
            ide.os.name = orig_os_name

    # 6. find_python_in_dir (NT nested structure)
    def test_find_python_in_dir_nt_nested(self):
        orig_os_name = ide.os.name
        try:
            ide.os.name = 'nt'
            with tempfile.TemporaryDirectory() as tmpdir:
                p = Path(tmpdir)
                nested = p / 'WPy64-31500' / 'python-3.15.0'
                nested.mkdir(parents=True)
                py_exe = nested / 'python.exe'
                py_exe.touch()
                res = ide.find_python_in_dir(p)
                self.assertEqual(res, py_exe)
        finally:
            ide.os.name = orig_os_name

    # 7. find_python_in_dir (missing)
    def test_find_python_in_dir_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            res = ide.find_python_in_dir(p)
            self.assertIsNone(res)

    # 8. _temporary_mode_active (true)
    def test_temporary_mode_active_true(self):
        app = FakeApp()
        app.save_before_run_var.set('never')
        self.assertTrue(ide.PortableIDE._temporary_mode_active(app))

    # 9. _temporary_mode_active (false)
    def test_temporary_mode_active_false(self):
        app = FakeApp()
        app.save_before_run_var.set('always')
        self.assertFalse(ide.PortableIDE._temporary_mode_active(app))

    # 10. _temp_name_for_tab (base case)
    def test_temp_name_for_tab(self):
        app = FakeApp()
        tab = FakeTab(path=Path('C:/foo/bar.py'))
        res = ide.PortableIDE._temp_name_for_tab(app, tab)
        self.assertEqual(res, 'bar.py')
        self.assertEqual(tab.temp_name, 'bar.py')

    # 11. _temp_name_for_tab (collision case)
    def test_temp_name_for_tab_collision(self):
        app = FakeApp()
        existing_tab = FakeTab(temp_name='module1.py')
        app.tabs_by_frame = {'f1': existing_tab}

        new_tab = FakeTab()
        app._runtime_name_for_tab = lambda t: 'module1.py'
        res = ide.PortableIDE._temp_name_for_tab(app, new_tab)
        self.assertEqual(res, 'module1_2.py')
        self.assertEqual(new_tab.temp_name, 'module1_2.py')

    # 12. _has_temp_files (empty)
    def test_has_temp_files_empty(self):
        app = FakeApp()
        app._temp_active = True
        app.temp_assets = []
        app.tabs_by_frame = {}
        app.temp_session_dir = Path("nonexistent_session_dir_123")
        self.assertFalse(ide.PortableIDE._has_temp_files(app))

    # 13. _has_temp_files (with unsaved tab)
    def test_has_temp_files_non_empty_tab(self):
        app = FakeApp()
        app._temp_active = True
        app.tabs_by_frame = {'f1': FakeTab(path=None)}
        self.assertTrue(ide.PortableIDE._has_temp_files(app))

    # 14. _has_temp_files (with temp assets)
    def test_has_temp_files_non_empty_assets(self):
        app = FakeApp()
        app._temp_active = True
        app.temp_assets = ['asset.png']
        self.assertTrue(ide.PortableIDE._has_temp_files(app))

    # 15. _has_temp_files (with temp session dir existing)
    def test_has_temp_files_session_dir_exists(self):
        app = FakeApp()
        app._temp_active = True
        with tempfile.TemporaryDirectory() as tmpdir:
            app.temp_session_dir = Path(tmpdir)
            self.assertTrue(ide.PortableIDE._has_temp_files(app))

    # 16. _code_uses_turtle (direct import)
    def test_code_uses_turtle_direct(self):
        app = FakeApp()
        self.assertTrue(ide.PortableIDE._code_uses_turtle(app, "import turtle"))

    # 17. _code_uses_turtle (from import)
    def test_code_uses_turtle_from(self):
        app = FakeApp()
        self.assertTrue(ide.PortableIDE._code_uses_turtle(app, "from turtle import *"))

    # 18. _code_uses_turtle (commented)
    def test_code_uses_turtle_commented(self):
        app = FakeApp()
        self.assertFalse(ide.PortableIDE._code_uses_turtle(app, "# import turtle"))
        self.assertFalse(ide.PortableIDE._code_uses_turtle(app, "# from turtle import *"))

    # 19. _code_uses_turtle (no turtle)
    def test_code_uses_turtle_none(self):
        app = FakeApp()
        self.assertFalse(ide.PortableIDE._code_uses_turtle(app, "import math\nprint('hello')"))

    # 20. _collect_imports (single)
    def test_collect_imports_single(self):
        app = FakeApp()
        self.assertEqual(ide.PortableIDE._collect_imports(app, "import os"), {'os'})

    # 21. _collect_imports (multiple and from)
    def test_collect_imports_multiple(self):
        app = FakeApp()
        code = "import os, sys\nfrom math import sin\nfrom os.path import exists"
        # The parser adds everything imported via from ... import or import
        self.assertEqual(ide.PortableIDE._collect_imports(app, code), {'os', 'sys', 'math', 'sin', 'exists'})

    # 22. _module_name_for_tab (with path)
    def test_module_name_for_tab_with_path(self):
        app = FakeApp()
        tab = FakeTab(path=Path("C:/foo/bar.py"))
        self.assertEqual(ide.PortableIDE._module_name_for_tab(app, tab), 'bar')

    # 23. _module_name_for_tab (virtual with ext)
    def test_module_name_for_tab_virtual_ext(self):
        app = FakeApp()
        tab = FakeTab(virtual_name='module1.py')
        self.assertEqual(ide.PortableIDE._module_name_for_tab(app, tab), 'module1')

    # 24. _module_name_for_tab (virtual no ext)
    def test_module_name_for_tab_virtual_no_ext(self):
        app = FakeApp()
        tab = FakeTab(virtual_name='module1')
        self.assertEqual(ide.PortableIDE._module_name_for_tab(app, tab), 'module1')

    # 25. _runtime_name_for_tab (main tab)
    def test_runtime_name_for_tab_main(self):
        app = FakeApp()
        tab = FakeTab()
        app.main_tab = tab
        self.assertEqual(ide.PortableIDE._runtime_name_for_tab(app, tab), 'main.py')

    # 26. _runtime_name_for_tab (other tab)
    def test_runtime_name_for_tab_other(self):
        app = FakeApp()
        tab = FakeTab(path=Path("C:/foo/bar.py"))
        app.main_tab = None
        self.assertEqual(ide.PortableIDE._runtime_name_for_tab(app, tab), 'bar.py')

    # 27. _next_virtual_name (first call)
    def test_next_virtual_name_first(self):
        app = FakeApp()
        app._main_created = False
        self.assertEqual(ide.PortableIDE._next_virtual_name(app), 'main.py')
        self.assertTrue(app._main_created)

    # 28. _next_virtual_name (sequential calls)
    def test_next_virtual_name_sequential(self):
        app = FakeApp()
        app._main_created = True
        app.tabs_by_frame = {'f1': FakeTab(virtual_name='module1.py')}
        self.assertEqual(ide.PortableIDE._next_virtual_name(app), 'module2.py')

    # 29. _is_running (combinations)
    def test_is_running_combinations(self):
        app = FakeApp()
        app.process = None
        app.turtle_running = False
        app.inline_running = False
        self.assertFalse(ide.PortableIDE._is_running(app))

        app.process = object()
        self.assertTrue(ide.PortableIDE._is_running(app))

        app.process = None
        app.turtle_running = True
        self.assertTrue(ide.PortableIDE._is_running(app))

        app.turtle_running = False
        app.inline_running = True
        self.assertTrue(ide.PortableIDE._is_running(app))

    # 30. _serialize_project (empty)
    def test_serialize_project_empty(self):
        app = FakeApp()
        app.tabs_by_frame = {}
        self.assertEqual(ide.PortableIDE._serialize_project(app), '')

    # 31. _serialize_project and _load_project_from_hash roundtrip
    def test_serialize_project_roundtrip(self):
        orig_EditorTab = ide.EditorTab
        root = tk.Tk()
        root.withdraw()
        try:
            notebook = ttk.Notebook(root)

            class FakeEditorTabWrapper:
                def __init__(self, app, path=None):
                    self.app = app
                    self.path = path
                    self.virtual_name = None
                    self.temp_name = None
                    self._content = ""
                    self.frame = ttk.Frame(notebook)

                def get_content(self):
                    return self._content

                def set_content(self, content):
                    self._content = content

            ide.EditorTab = FakeEditorTabWrapper

            # Prepare serialize payload
            app = FakeApp()
            tab1 = FakeTab(virtual_name='main.py', content='print("hello")')
            tab2 = FakeTab(virtual_name='module2.py', content='x = 1')
            app.tabs_by_frame = {'f1': tab1, 'f2': tab2}
            app._runtime_name_for_tab = lambda t: t.virtual_name

            serialized = ide.PortableIDE._serialize_project(app)
            self.assertNotEqual(serialized, '')

            # Now try deserializing on a clean app
            app2 = FakeApp()
            app2.notebook = notebook
            app2.tabs_by_frame = {}
            app2.main_tab = None
            app2._main_created = False
            app2._confirm_discard = lambda t: True
            app2.update_tab_title = lambda t: None

            def ensure_main():
                if not app2.main_tab:
                    app2.main_tab = FakeEditorTabWrapper(app2)
                    app2.notebook.add(app2.main_tab.frame, text='main.py')
                    app2.tabs_by_frame[str(app2.main_tab.frame)] = app2.main_tab
                return app2.main_tab

            app2._ensure_main_tab = ensure_main
            app2._next_virtual_name = lambda: 'module2.py'

            success = ide.PortableIDE._load_project_from_hash(app2, serialized)
            self.assertTrue(success)
            self.assertIsNotNone(app2.main_tab)
            self.assertEqual(app2.main_tab.get_content(), 'print("hello")')
            self.assertEqual(len(app2.tabs_by_frame), 2)
        finally:
            ide.EditorTab = orig_EditorTab
            root.destroy()

    # 32. _indent_or_tab (no selection)
    def test_indent_or_tab_no_selection(self):
        root = tk.Tk()
        root.withdraw()
        try:
            app = FakeApp()
            text = tk.Text(root)
            text.insert('1.0', 'line1')
            text.mark_set('insert', '1.3')
            res = ide.PortableIDE._indent_or_tab(app, text)
            self.assertEqual(res, 'break')
            self.assertEqual(text.get('1.0', 'end-1c'), 'lin    e1')
        finally:
            root.destroy()

    # 33. _indent_selection
    def test_indent_selection(self):
        root = tk.Tk()
        root.withdraw()
        try:
            app = FakeApp()
            text = tk.Text(root)
            text.insert('1.0', 'line1\nline2\nline3')
            text.tag_add('sel', '1.0', '2.5')
            res = ide.PortableIDE._indent_selection(app, text)
            self.assertEqual(res, 'break')
            self.assertEqual(text.get('1.0', 'end-1c'), '    line1\n    line2\nline3')
        finally:
            root.destroy()

    # 34. _newline_and_indent (same block)
    def test_newline_and_indent_keeps_current_indent(self):
        root = tk.Tk()
        root.withdraw()
        try:
            app = FakeApp()
            text = tk.Text(root)
            text.insert('1.0', '    print("hello")')
            text.mark_set('insert', '1.end')
            res = ide.PortableIDE._newline_and_indent(app, text)
            self.assertEqual(res, 'break')
            self.assertEqual(text.get('1.0', 'end-1c'), '    print("hello")\n    ')
        finally:
            root.destroy()

    # 35. _newline_and_indent (colon block)
    def test_newline_and_indent_after_colon(self):
        root = tk.Tk()
        root.withdraw()
        try:
            app = FakeApp()
            text = tk.Text(root)
            text.insert('1.0', 'if True:')
            text.mark_set('insert', '1.end')
            res = ide.PortableIDE._newline_and_indent(app, text)
            self.assertEqual(res, 'break')
            self.assertEqual(text.get('1.0', 'end-1c'), 'if True:\n    ')
        finally:
            root.destroy()

    # 36. _cycle_tab
    def test_cycle_tab(self):
        root = tk.Tk()
        root.withdraw()
        try:
            notebook = ttk.Notebook(root)
            f1 = ttk.Frame(notebook)
            f2 = ttk.Frame(notebook)
            f3 = ttk.Frame(notebook)
            notebook.add(f1, text='t1')
            notebook.add(f2, text='t2')
            notebook.add(f3, text='t3')

            app = FakeApp()
            app.notebook = notebook
            app._focus_editor_called = False
            app._focus_editor = lambda: setattr(app, '_focus_editor_called', True)

            notebook.select(f1)
            res = ide.PortableIDE._cycle_tab(app, 1)
            self.assertEqual(res, 'break')
            self.assertEqual(notebook.select(), str(f2))
            self.assertTrue(app._focus_editor_called)

            res = ide.PortableIDE._cycle_tab(app, -1)
            self.assertEqual(notebook.select(), str(f1))

            res = ide.PortableIDE._cycle_tab(app, -1)
            self.assertEqual(notebook.select(), str(f3))
        finally:
            root.destroy()

    # 37. _maybe_focus_input_on_output
    def test_maybe_focus_input_on_output(self):
        app = FakeApp()
        app._pulse_called = False
        app._pulse_input_focus = lambda: setattr(app, '_pulse_called', True)

        ide.PortableIDE._maybe_focus_input_on_output(app, "hello\n")
        self.assertFalse(app._pulse_called)

        ide.PortableIDE._maybe_focus_input_on_output(app, "")
        self.assertFalse(app._pulse_called)

        ide.PortableIDE._maybe_focus_input_on_output(app, "hello")
        self.assertTrue(app._pulse_called)

    # 38. _pulse_input_focus
    def test_pulse_input_focus(self):
        class FakeLabel:
            def __init__(self):
                self.text = ""

            def configure(self, text):
                self.text = text

        class FakeWidget:
            def __init__(self):
                self.cfg = {}
                self.focused = False

            def configure(self, **kw):
                self.cfg.update(kw)

            def focus_set(self):
                self.focused = True

        app = FakeApp()
        app.input_label = FakeLabel()
        app.input_text = FakeWidget()

        ide.PortableIDE._pulse_input_focus(app)
        self.assertTrue(app._waiting_for_input)
        # Verify it has the hourglass icon and ends with a colon to be encoding safe
        self.assertIn('⏳', app.input_label.text)
        self.assertTrue(app.input_label.text.strip().endswith(':'))
        self.assertEqual(app.input_text.cfg.get('background'), '#2563eb')
        self.assertTrue(app.input_text.focused)

    # 39. _load_module_source (from tabs)
    def test_load_module_source_from_tabs(self):
        app = FakeApp()
        tab1 = FakeTab(virtual_name='module1.py', content='x = 10')
        app.tabs_by_frame = {'f1': tab1}
        res = ide.PortableIDE._load_module_source(app, 'module1', None)
        self.assertEqual(res, 'x = 10')

    # 40. _load_module_source (from file system)
    def test_load_module_source_from_fs(self):
        app = FakeApp()
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            module_file = p / 'module2.py'
            module_file.write_text('y = 20', encoding='utf-8')
            res = ide.PortableIDE._load_module_source(app, 'module2', module_file)
            self.assertEqual(res, 'y = 20')

    # 41. _needs_turtle (recursive turtle usage)
    def test_needs_turtle_recursive(self):
        app = FakeApp()
        tab = FakeTab(content='import module_a')
        tab_a = FakeTab(virtual_name='module_a.py', content='import module_b')
        tab_b = FakeTab(virtual_name='module_b.py', content='import turtle')

        app.tabs_by_frame = {'f1': tab, 'f2': tab_a, 'f3': tab_b}
        self.assertTrue(ide.PortableIDE._needs_turtle(app, tab, None))

    # 42. _find_tab_by_filename (path match)
    def test_find_tab_by_filename_path(self):
        app = FakeApp()
        tab = FakeTab(path=Path("C:/foo/bar.py"))
        app.tabs_by_frame = {'f1': tab}
        res = ide.PortableIDE._find_tab_by_filename(app, 'bar.py')
        self.assertEqual(res, tab)

    # 43. _find_tab_by_filename (virtual name match)
    def test_find_tab_by_filename_virtual(self):
        app = FakeApp()
        tab = FakeTab(virtual_name='module1.py')
        app.tabs_by_frame = {'f1': tab}
        res = ide.PortableIDE._find_tab_by_filename(app, 'module1.py')
        self.assertEqual(res, tab)

    # 44. _get_selection
    def test_get_selection(self):
        root = tk.Tk()
        root.withdraw()
        try:
            app = FakeApp()
            text = tk.Text(root)
            text.insert('1.0', 'hello world')
            self.assertEqual(ide.PortableIDE._get_selection(app, text), '')

            text.tag_add('sel', '1.0', '1.5')
            self.assertEqual(ide.PortableIDE._get_selection(app, text), 'hello')
        finally:
            root.destroy()

    # 45. _delete_selection
    def test_delete_selection(self):
        root = tk.Tk()
        root.withdraw()
        try:
            app = FakeApp()
            text = tk.Text(root)
            text.insert('1.0', 'hello world')
            text.tag_add('sel', '1.5', '1.11')
            ide.PortableIDE._delete_selection(app, text)
            self.assertEqual(text.get('1.0', 'end-1c'), 'hello')
        finally:
            root.destroy()

    # 46. _replace_selection
    def test_replace_selection(self):
        root = tk.Tk()
        root.withdraw()
        try:
            app = FakeApp()
            text = tk.Text(root)
            text.insert('1.0', 'hello world')
            text.tag_add('sel', '1.6', '1.11')
            ide.PortableIDE._replace_selection(app, text, 'there')
            self.assertEqual(text.get('1.0', 'end-1c'), 'hello there')
        finally:
            root.destroy()

    # 47. get_python_executable (env var set)
    def test_get_python_executable_env(self):
        orig_environ = os.environ
        try:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_name = tmp.name
            try:
                os.environ = {'PYTHON_PORTABLE': tmp_name}
                self.assertEqual(ide.get_python_executable(), tmp_name)
            finally:
                os.unlink(tmp_name)
        finally:
            os.environ = orig_environ

    # 48. get_python_executable (fallback to PYTHON_DIR)
    def test_get_python_executable_fallback(self):
        orig_environ = os.environ
        orig_PYTHON_DIR = ide.PYTHON_DIR
        try:
            os.environ = {}
            with tempfile.TemporaryDirectory() as tmpdir:
                ide.PYTHON_DIR = Path(tmpdir)
                py_exe = ide.PYTHON_DIR / ('python.exe' if os.name == 'nt' else 'python3')
                py_exe.touch()
                self.assertEqual(ide.get_python_executable(), str(py_exe))
        finally:
            os.environ = orig_environ
            ide.PYTHON_DIR = orig_PYTHON_DIR

    # 49. _select_all_widget
    def test_select_all_widget(self):
        root = tk.Tk()
        root.withdraw()
        try:
            app = FakeApp()
            text = tk.Text(root)
            text.insert('1.0', 'hello world')
            res = ide.PortableIDE._select_all_widget(app, text)
            self.assertEqual(res, 'break')
            self.assertEqual(text.get('sel.first', 'sel.last'), 'hello world\n')
        finally:
            root.destroy()

    # 50. _select_all_widget uses Tk virtual event
    def test_select_all_widget_uses_native_virtual_event(self):
        root = tk.Tk()
        root.withdraw()
        try:
            app = FakeApp()
            text = tk.Text(root)
            text.insert('1.0', 'hello world')
            generated = []
            text.bind('<<SelectAll>>', lambda _e: generated.append(True), add=True)
            res = ide.PortableIDE._select_all_widget(app, text)
            self.assertEqual(res, 'break')
            self.assertTrue(generated)
            self.assertEqual(text.get('sel.first', 'sel.last'), 'hello world\n')
        finally:
            root.destroy()

    # 51. _handle_control_key uses keysym
    def test_handle_control_key_uses_keysym(self):
        root = tk.Tk()
        root.withdraw()
        try:
            app = FakeApp()
            text = tk.Text(root)
            text.insert('1.0', 'hello world')

            class Event:
                state = 0x4
                keycode = 0
                keysym = 'a'

            res = ide.PortableIDE._handle_control_key(app, text, Event())
            self.assertEqual(res, 'break')
            self.assertEqual(text.get('sel.first', 'sel.last'), 'hello world\n')
        finally:
            root.destroy()

    # 52. _handle_control_key supports command-filtered events by keycode
    def test_handle_control_key_command_event_uses_keycode(self):
        root = tk.Tk()
        root.withdraw()
        try:
            app = FakeApp()
            text = tk.Text(root)
            text.insert('1.0', 'hello world')

            class Event:
                state = 0
                keycode = 65
                keysym = 'Cyrillic_ef'

            res = ide.PortableIDE._handle_control_key(app, text, Event(), require_control=False)
            self.assertEqual(res, 'break')
            self.assertEqual(text.get('sel.first', 'sel.last'), 'hello world\n')
        finally:
            root.destroy()

    # 53. bind_text_shortcuts does not bind Command on non-macOS
    def test_bind_text_shortcuts_command_only_on_macos(self):
        root = tk.Tk()
        root.withdraw()
        orig_platform = ide.sys.platform
        try:
            app = FakeApp()
            text = tk.Text(root)
            calls = []
            app._bind_if_supported = lambda _w, sequence, _callback, add=None: calls.append(sequence)
            ide.sys.platform = 'win32'
            ide.PortableIDE.bind_text_shortcuts(app, text)
            self.assertNotIn('<Command-a>', calls)
            self.assertNotIn('<Command-KeyPress>', calls)

            calls.clear()
            ide.sys.platform = 'darwin'
            ide.PortableIDE.bind_text_shortcuts(app, text)
            self.assertIn('<Command-a>', calls)
            self.assertIn('<Command-KeyPress>', calls)
        finally:
            ide.sys.platform = orig_platform
            root.destroy()

    # 54. clipboard helpers (copy, cut, paste)
    def test_clipboard_helpers(self):
        root = tk.Tk()
        root.withdraw()
        try:
            app = FakeApp()
            text = tk.Text(root)
            text.insert('1.0', 'clipboard test')

            # Select 'clipboard'
            text.tag_add('sel', '1.0', '1.9')

            # Copy helper
            res1 = ide.PortableIDE._clipboard_copy_widget(app, text)
            self.assertEqual(res1, 'break')
            self.assertEqual(app.clipboard_val, 'clipboard')

            # Cut helper
            text.tag_remove('sel', '1.0', 'end')
            text.tag_add('sel', '1.10', '1.14') # selects 'test'
            res2 = ide.PortableIDE._clipboard_cut_widget(app, text)
            self.assertEqual(res2, 'break')
            self.assertEqual(app.clipboard_val, 'test')
            self.assertEqual(text.get('1.0', 'end-1c'), 'clipboard ')

            # Paste helper
            text.mark_set('insert', '1.10')
            res3 = ide.PortableIDE._clipboard_paste_widget(app, text)
            self.assertEqual(res3, 'break')
            self.assertEqual(text.get('1.0', 'end-1c'), 'clipboard test')
        finally:
            root.destroy()


if __name__ == '__main__':
    unittest.main()
