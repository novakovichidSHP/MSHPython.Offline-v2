"""Логика оркестрации перезапуска: guard двойного клика, сброс turtle_abort,
on_exit при отмене закрытия."""
import sys
import importlib.util
from pathlib import Path

APP = Path(__file__).resolve().parent / 'MSHP-IDE-Windows' / 'app' / 'ide.py'
spec = importlib.util.spec_from_file_location('ide_logic', APP)
ide = importlib.util.module_from_spec(spec)
sys.modules['ide_logic'] = ide
spec.loader.exec_module(ide)
print('import ide.py: OK')

TAB = object()
P = ide.PortableIDE


class _FakeLabel:
    def __init__(self): self.text = ''
    def configure(self, **kw): self.text = kw.get('text', self.text)

class _FakeWidget:
    def __init__(self): self._cfg = {}
    def configure(self, **kw): self._cfg.update(kw)

class Fake:
    def __init__(self, running):
        self._running = running
        self._closing = False
        self._restart_pending = False
        self.turtle_abort = False
        self.step_abort = False
        self.step_mode = False
        self.main_tab = TAB
        self.events = []
        self._budget = 200
        self._waiting_for_input = False
        self.input_label = _FakeLabel()
        self.input_text = _FakeWidget()
        self.theme = {'input_bg': '#fff', 'input_fg': '#000'}
    # зависимости
    def get_current_tab(self): return TAB
    def _ensure_main_tab(self): return TAB
    def _is_running(self): return self._running
    def _update_run_controls(self): self.events.append('controls')
    def _show_step_controls(self, x): pass
    def stop_process(self): self.events.append('stop')
    def _confirm_discard(self, tab): return self._confirm
    def _clear_temp_session(self): self.events.append('clear_temp')
    def destroy(self): self.events.append('destroy')
    def after(self, ms, cb):
        self.events.append(f'after{ms}')
        self._budget -= 1
        assert self._budget > 0, 'after-loop не сошёлся'
        cb()
    # _start_run заменяем: фиксируем факт и НЕ запускаем реальный пайплайн
    def _start_run(self, tab, step_mode):
        self.events.append('start')
        self.started_step = step_mode
    # настоящие тестируемые методы
    run_current = P.run_current
    _schedule_restart = P._schedule_restart
    on_exit = P.on_exit


# --- 1: guard — пока _restart_pending, повторный клик игнорируется ---
f = Fake(running=True)
# имитируем, что остановка асинхронная (turtle): _is_running остаётся True,
# пока не «завершится». Сделаем так, чтобы после первого after стало False.
calls = {'n': 0}
def stop_async(self=f):
    self.events.append('stop')
f.stop_process = stop_async
orig_after = f.after
def after_flip(ms, cb):
    f.events.append(f'after{ms}')
    f._running = False           # старый запуск завершился
    cb()
f.after = after_flip

f.run_current()                  # первый клик: ставит pending, stop, schedule
assert f._restart_pending in (False,), 'после полного цикла pending должен сняться'
assert f.events.count('start') == 1, f'ожидался один старт: {f.events}'
print('1 guard/основной цикл: OK ->', f.events)

# --- 2: повторный клик во время pending — no-op ---
f2 = Fake(running=True)
f2.stop_process = lambda: f2.events.append('stop')
f2.after = lambda ms, cb: f2.events.append(f'after{ms}')   # НЕ выполняем cb (висим)
f2.run_current()                 # pending=True, ушли в ожидание (after не дёрнул cb)
assert f2._restart_pending is True, 'pending должен стоять'
before = list(f2.events)
f2.run_current()                 # повторный клик
f2.run_current()                 # ещё раз
assert f2.events == before, f'повторные клики не должны ничего делать: {f2.events}'
assert f2.events.count('stop') == 1, 'stop вызван более одного раза'
print('2 повторные клики при pending — no-op: OK ->', f2.events)

# --- 3: _start_run сбрасывает turtle_abort (до ветки запуска) ---
fake_tab = type('T', (), {'get_content': lambda self: 'code'})()
f3b = Fake(running=False)
f3b.turtle_abort = True
f3b.step_abort = True
f3b._prepare_run_context = lambda tab: (Path('x.py'), None)   # валидный контекст
f3b._needs_turtle = lambda tab, sp: True                       # уходим в turtle-ветку
f3b._run_turtle_code = lambda *a: f3b.events.append('turtle')  # без реального запуска
f3b.step_event = type('E', (), {'clear': lambda self: None})()
f3b._start_run = P._start_run.__get__(f3b)
f3b._start_run(fake_tab, False)
assert f3b.turtle_abort is False, 'turtle_abort не сброшен в _start_run'
assert f3b.step_abort is False, 'step_abort не сброшен в _start_run'
assert 'turtle' in f3b.events, 'не дошли до ветки запуска'
print('3 _start_run сбрасывает turtle_abort/step_abort: OK')

# --- 4: on_exit при отмене закрытия восстанавливает флаги ---
f4 = Fake(running=False)
f4._confirm = False              # пользователь жмёт «Отмена»
f4.tabs_by_frame = {'a': TAB}
f4.on_exit()
assert f4._closing is False, '_closing должен быть восстановлен'
assert f4.turtle_abort is False and f4.step_abort is False, 'abort-флаги не сброшены'
assert 'destroy' not in f4.events, 'окно не должно закрываться при отмене'
print('4 on_exit при отмене восстанавливает флаги: OK')

# --- 5: on_exit при подтверждении закрывает ---
f5 = Fake(running=False)
f5._confirm = True
f5.tabs_by_frame = {'a': TAB}
f5.on_exit()
assert f5._closing is True and 'destroy' in f5.events, 'закрытие не выполнено'
print('5 on_exit при подтверждении закрывает: OK')

print('\nALL ASSERTIONS PASSED')


# --- 6: _start_run вызывает _update_run_controls когда _prepare_run_context → None ---
import queue as _queue
f6 = Fake(running=False)
f6._prepare_run_context = lambda tab: None    # имитируем Cancel в диалоге
f6._waiting_for_input = False
f6.step_event = type('E', (), {'clear': lambda self: None})()
f6._start_run = P._start_run.__get__(f6)
f6._start_run(TAB, False)
assert 'controls' in f6.events, '_update_run_controls не вызван при None-контексте'
print('6 _start_run s None-kontekstom -> _update_run_controls: OK')

# --- 7: _start_run сбрасывает _waiting_for_input и визуальное состояние поля ввода ---
import queue as _queue
fake_tab2 = type('T', (), {'get_content': lambda self: 'print(1)'})()
f7 = Fake(running=False)
f7._waiting_for_input = True
f7.input_label.text = '⏳ Ожидание ввода:'
f7._prepare_run_context = lambda tab: (Path('x.py'), None)
f7._needs_turtle = lambda tab, sp: False
f7._run_in_console = lambda *a: None
f7.input_queue = _queue.Queue()
f7.step_event = type('E', (), {'clear': lambda self: None})()
f7.clear_console = lambda: None
f7._focus_input = lambda: None
f7._append_output = lambda *a, **kw: None
f7._start_run = P._start_run.__get__(f7)
f7._start_run(fake_tab2, False)
assert f7._waiting_for_input is False, '_waiting_for_input не сброшен'
assert f7.input_label.text == 'Ввод:', f'input_label не сброшен: {f7.input_label.text!r}'
print('7 _start_run сбрасывает _waiting_for_input и input_label: OK')

print('\nALL ASSERTIONS PASSED')
