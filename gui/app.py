"""
Главное окно приложения Proxy Switcher.
Реализует весь основной интерфейс пользователя.
"""

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

from core.app_launcher import AppLauncher
from core.proxy_checker import check_proxy_async
from core.proxy_manager import ProxyManager
from core.rotator import ProxyRotator
from gui.proxy_list import ProxyListWidget
from gui.settings import AddProxyDialog

# ── Палитра тёмной темы (Catppuccin Mocha) ──────────────────────────────────
BG_DARK = "#1e1e2e"
BG_MEDIUM = "#2a2a3e"
BG_LIGHT = "#313149"
BG_INPUT = "#45475a"
TEXT_COLOR = "#cdd6f4"
TEXT_MUTED = "#6c7086"
ACCENT_COLOR = "#89b4fa"
SUCCESS_COLOR = "#a6e3a1"
ERROR_COLOR = "#f38ba8"
WARNING_COLOR = "#fab387"
BTN_START = "#a6e3a1"
BTN_STOP = "#f38ba8"
BTN_DEFAULT = "#89b4fa"


class ProxySwitcherApp(tk.Tk):
    """
    Главное окно приложения.
    Управляет всем жизненным циклом: прокси, запуском приложения, ротацией.
    """

    def __init__(self):
        super().__init__()

        # Инициализация компонентов ядра
        self._manager = ProxyManager()
        self._launcher = AppLauncher()
        self._rotator = ProxyRotator(self._manager, on_rotate=self._on_proxy_rotated)
        self._is_running = False

        # Лог-колбэк для лаунчера
        self._launcher.set_log_callback(self._append_log)

        # Настройка окна
        self.title("Proxy Switcher")
        self.geometry("820x640")
        self.minsize(700, 540)
        self.configure(bg=BG_DARK)
        self._set_icon()

        # Строим интерфейс
        self._build_ui()

        # Загружаем сохранённые данные
        self._refresh_proxy_list()
        self._refresh_app_label()
        self._refresh_rotation_ui()

        # Периодическое обновление статуса приложения
        self._schedule_status_update()

        # Обработчик закрытия окна
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Иконка окна ──────────────────────────────────────────────────────────

    def _set_icon(self):
        """Устанавливает иконку окна если она есть."""
        icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

    # ── Построение UI ────────────────────────────────────────────────────────

    def _build_ui(self):
        """Строит весь интерфейс главного окна."""
        # Заголовок
        header = tk.Frame(self, bg=BG_MEDIUM, pady=10)
        header.pack(fill="x")
        tk.Label(
            header, text="🔒 Proxy Switcher",
            bg=BG_MEDIUM, fg=ACCENT_COLOR,
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left", padx=20)

        # Статус подключения
        self._status_var = tk.StringVar(value="● Остановлено")
        self._status_label = tk.Label(
            header, textvariable=self._status_var,
            bg=BG_MEDIUM, fg=ERROR_COLOR,
            font=("Segoe UI", 10, "bold"),
        )
        self._status_label.pack(side="right", padx=20)

        # Основной контент
        content = tk.Frame(self, bg=BG_DARK)
        content.pack(fill="both", expand=True, padx=12, pady=8)

        # Левая панель (список прокси + кнопки управления)
        self._build_left_panel(content)

        # Правая панель (приложение + ротация)
        self._build_right_panel(content)

        # Лог панель внизу
        self._build_log_panel()

    def _build_left_panel(self, parent):
        """Создаёт левую панель со списком прокси."""
        left = tk.Frame(parent, bg=BG_DARK)
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))

        # Заголовок секции
        self._section_label(left, "Список прокси-серверов")

        # Список прокси
        self._proxy_list = ProxyListWidget(
            left, on_select=self._on_proxy_selected
        )
        self._proxy_list.pack(fill="both", expand=True)

        # Кнопки управления прокси
        btn_row = tk.Frame(left, bg=BG_DARK)
        btn_row.pack(fill="x", pady=(6, 0))

        self._btn(btn_row, "➕ Добавить", self._on_add_proxy).pack(side="left", padx=(0, 4))
        self._btn(btn_row, "🗑 Удалить", self._on_remove_proxy).pack(side="left", padx=(0, 4))
        self._btn(btn_row, "🔍 Проверить", self._on_check_proxy).pack(side="left", padx=(0, 4))
        self._btn(btn_row, "🔄 Проверить все", self._on_check_all).pack(side="left")

    def _build_right_panel(self, parent):
        """Создаёт правую панель: выбор приложения и ротация."""
        right = tk.Frame(parent, bg=BG_DARK, width=260)
        right.pack(side="right", fill="y", padx=(6, 0))
        right.pack_propagate(False)

        # ── Выбор приложения ──
        self._section_label(right, "Целевое приложение")

        app_frame = tk.Frame(right, bg=BG_MEDIUM, padx=10, pady=10, bd=0)
        app_frame.pack(fill="x", pady=(0, 8))

        self._app_name_var = tk.StringVar(value="Не выбрано")
        tk.Label(
            app_frame, textvariable=self._app_name_var,
            bg=BG_MEDIUM, fg=TEXT_COLOR,
            font=("Segoe UI", 9), wraplength=220,
            justify="left", anchor="w",
        ).pack(fill="x", pady=(0, 6))

        self._btn(app_frame, "📂 Выбрать .exe", self._on_choose_app).pack(fill="x")

        # ── Запуск / Остановка ──
        self._section_label(right, "Управление")

        ctrl_frame = tk.Frame(right, bg=BG_DARK)
        ctrl_frame.pack(fill="x", pady=(0, 8))

        self._start_btn = tk.Button(
            ctrl_frame, text="▶ Запустить",
            command=self._on_toggle_running,
            bg=BTN_START, fg=BG_DARK, relief="flat",
            font=("Segoe UI", 11, "bold"), pady=8,
            cursor="hand2", activebackground="#94e8a0",
        )
        self._start_btn.pack(fill="x")

        # Текущий прокси
        self._current_proxy_var = tk.StringVar(value="Прокси: не выбран")
        tk.Label(
            ctrl_frame, textvariable=self._current_proxy_var,
            bg=BG_DARK, fg=TEXT_MUTED,
            font=("Segoe UI", 9),
        ).pack(pady=(6, 0))

        # ── Ротация прокси ──
        self._section_label(right, "Ротация прокси")

        rot_frame = tk.Frame(right, bg=BG_MEDIUM, padx=10, pady=10)
        rot_frame.pack(fill="x", pady=(0, 8))

        # Переключатель ротации
        self._rotation_var = tk.BooleanVar(value=self._manager.rotation_enabled)
        rot_check = tk.Checkbutton(
            rot_frame, text="Авто-ротация",
            variable=self._rotation_var,
            command=self._on_rotation_toggle,
            bg=BG_MEDIUM, fg=TEXT_COLOR,
            selectcolor=BG_LIGHT, activebackground=BG_MEDIUM,
            activeforeground=ACCENT_COLOR,
            font=("Segoe UI", 10),
        )
        rot_check.pack(anchor="w")

        # Интервал ротации
        interval_row = tk.Frame(rot_frame, bg=BG_MEDIUM)
        interval_row.pack(fill="x", pady=(6, 0))

        tk.Label(
            interval_row, text="Интервал (сек):",
            bg=BG_MEDIUM, fg=TEXT_COLOR,
            font=("Segoe UI", 9),
        ).pack(side="left")

        self._interval_var = tk.StringVar(value=str(self._manager.rotation_interval))
        interval_entry = tk.Entry(
            interval_row, textvariable=self._interval_var,
            bg=BG_INPUT, fg=TEXT_COLOR, insertbackground=TEXT_COLOR,
            relief="flat", width=6, font=("Segoe UI", 10),
        )
        interval_entry.pack(side="left", padx=(6, 0))

        # Кнопка "Следующий прокси"
        self._btn(
            rot_frame, "⏭ Следующий прокси", self._on_rotate_now
        ).pack(fill="x", pady=(8, 0))

    def _build_log_panel(self):
        """Создаёт нижнюю панель логов."""
        log_frame = tk.Frame(self, bg=BG_DARK)
        log_frame.pack(fill="x", padx=12, pady=(0, 8))

        header = tk.Frame(log_frame, bg=BG_DARK)
        header.pack(fill="x")
        self._section_label(header, "Журнал событий").pack(side="left")
        self._btn(header, "Очистить", self._clear_log, small=True).pack(side="right")

        # Текстовое поле лога
        log_text_frame = tk.Frame(log_frame, bg=BG_MEDIUM, padx=2, pady=2)
        log_text_frame.pack(fill="x")

        self._log_text = tk.Text(
            log_text_frame,
            height=7, state="disabled",
            bg=BG_MEDIUM, fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR,
            relief="flat", font=("Consolas", 9),
            wrap="word",
        )
        scrollbar = tk.Scrollbar(log_text_frame, command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self._log_text.pack(fill="x")

    # ── Вспомогательные методы UI ────────────────────────────────────────────

    def _section_label(self, parent, text: str):
        """Создаёт заголовок секции."""
        label = tk.Label(
            parent, text=text,
            bg=BG_DARK, fg=ACCENT_COLOR,
            font=("Segoe UI", 10, "bold"), pady=4,
        )
        label.pack(anchor="w")
        return label

    def _btn(self, parent, text: str, command, small: bool = False):
        """Создаёт стандартную кнопку."""
        btn = tk.Button(
            parent, text=text, command=command,
            bg=BG_LIGHT, fg=TEXT_COLOR,
            activebackground=BG_MEDIUM, activeforeground=ACCENT_COLOR,
            relief="flat", cursor="hand2",
            font=("Segoe UI", 8 if small else 9),
            padx=6 if small else 10, pady=3 if small else 5,
        )
        return btn

    # ── Обновление UI ────────────────────────────────────────────────────────

    def _refresh_proxy_list(self):
        """Обновляет список прокси в таблице."""
        self._proxy_list.refresh(self._manager.proxies)
        # Восстанавливаем выделение текущего прокси
        if self._manager.proxies:
            self._proxy_list.select_row(self._manager.get_current_index())

    def _refresh_app_label(self):
        """Обновляет отображение выбранного приложения."""
        app = self._manager.selected_app
        if app:
            self._app_name_var.set(os.path.basename(app))
        else:
            self._app_name_var.set("Не выбрано")

    def _refresh_rotation_ui(self):
        """Обновляет состояние виджетов ротации."""
        self._rotation_var.set(self._manager.rotation_enabled)
        self._interval_var.set(str(self._manager.rotation_interval))

    def _refresh_current_proxy_label(self):
        """Обновляет лейбл с текущим прокси."""
        proxy = self._manager.get_current_proxy()
        if proxy:
            self._current_proxy_var.set(f"Прокси: {proxy}")
        else:
            self._current_proxy_var.set("Прокси: не выбран")

    def _update_status(self, running: bool):
        """Обновляет статус в заголовке и кнопку запуска."""
        if running:
            self._status_var.set("● Активно")
            self._status_label.config(fg=SUCCESS_COLOR)
            self._start_btn.config(
                text="⏹ Остановить",
                bg=BTN_STOP, fg=BG_DARK,
                activebackground="#f5a0a7",
            )
        else:
            self._status_var.set("● Остановлено")
            self._status_label.config(fg=ERROR_COLOR)
            self._start_btn.config(
                text="▶ Запустить",
                bg=BTN_START, fg=BG_DARK,
                activebackground="#94e8a0",
            )

    # ── Логирование ──────────────────────────────────────────────────────────

    def _append_log(self, message: str):
        """Добавляет строку в лог-панель (thread-safe)."""
        def _do():
            import datetime
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            self._log_text.config(state="normal")
            self._log_text.insert("end", f"[{ts}] {message}\n")
            self._log_text.see("end")
            self._log_text.config(state="disabled")

        # Вызываем из любого потока безопасно
        self.after(0, _do)

    def _clear_log(self):
        """Очищает лог-панель."""
        self._log_text.config(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.config(state="disabled")

    # ── Обработчики событий ──────────────────────────────────────────────────

    def _on_proxy_selected(self, index: int):
        """Вызывается при выборе прокси в списке."""
        self._manager.set_current_index(index)
        self._refresh_current_proxy_label()

    def _on_add_proxy(self):
        """Открывает диалог добавления прокси."""
        def on_save(proxy_config):
            self._manager.add_proxy(proxy_config)
            self._refresh_proxy_list()
            self._append_log(f"➕ Добавлен прокси: {proxy_config}")

        AddProxyDialog(self, on_save=on_save)

    def _on_remove_proxy(self):
        """Удаляет выбранный прокси из списка."""
        index = self._proxy_list.get_selected_index()
        if index < 0:
            messagebox.showwarning("Предупреждение", "Выберите прокси для удаления", parent=self)
            return
        proxy = self._manager.get_proxy(index)
        if proxy and messagebox.askyesno(
            "Подтверждение", f"Удалить прокси {proxy}?", parent=self
        ):
            self._manager.remove_proxy(index)
            self._append_log(f"🗑 Удалён прокси: {proxy}")
            self._refresh_proxy_list()
            self._refresh_current_proxy_label()

    def _on_check_proxy(self):
        """Проверяет выбранный прокси."""
        index = self._proxy_list.get_selected_index()
        if index < 0:
            messagebox.showwarning("Предупреждение", "Выберите прокси для проверки", parent=self)
            return
        proxy = self._manager.get_proxy(index)
        if proxy:
            self._check_single_proxy(proxy, index)

    def _check_single_proxy(self, proxy, index: int):
        """Запускает проверку одного прокси асинхронно."""
        proxy.status = "⏳ Проверка..."
        self._refresh_proxy_list()
        self._append_log(f"🔍 Проверка: {proxy}")

        def callback(success, message, elapsed):
            proxy.status = f"✅ {message}" if success else f"❌ {message}"
            self._manager.save_settings()
            self.after(0, self._refresh_proxy_list)
            self._append_log(
                f"{'✅' if success else '❌'} {proxy.host}:{proxy.port} — {message}"
            )

        check_proxy_async(proxy, callback)

    def _on_check_all(self):
        """Проверяет все прокси в списке."""
        if not self._manager.proxies:
            messagebox.showinfo("Информация", "Список прокси пуст", parent=self)
            return
        self._append_log("🔍 Начало проверки всех прокси...")
        for i, proxy in enumerate(self._manager.proxies):
            self._check_single_proxy(proxy, i)

    def _on_choose_app(self):
        """Открывает диалог выбора .exe файла."""
        path = filedialog.askopenfilename(
            title="Выберите приложение",
            filetypes=[("Исполняемые файлы", "*.exe"), ("Все файлы", "*.*")],
            parent=self,
        )
        if path:
            self._manager.set_selected_app(path)
            self._refresh_app_label()
            self._append_log(f"📂 Выбрано приложение: {os.path.basename(path)}")

    def _on_toggle_running(self):
        """Переключает запуск/остановку проксированного приложения."""
        if self._is_running:
            self._stop_proxy()
        else:
            self._start_proxy()

    def _start_proxy(self):
        """Запускает приложение через прокси."""
        if not self._manager.selected_app:
            messagebox.showwarning(
                "Предупреждение", "Выберите приложение для запуска", parent=self
            )
            return

        if not self._manager.proxies:
            messagebox.showwarning(
                "Предупреждение", "Добавьте хотя бы один прокси", parent=self
            )
            return

        proxy = self._manager.get_current_proxy()
        if not proxy:
            messagebox.showwarning(
                "Предупреждение", "Выберите прокси из списка", parent=self
            )
            return

        success = self._launcher.launch(self._manager.selected_app, proxy)
        if success:
            self._is_running = True
            self._update_status(True)
            self._refresh_current_proxy_label()

            # Запускаем ротацию если включена
            if self._rotation_var.get() and len(self._manager.proxies) > 1:
                try:
                    interval = int(self._interval_var.get())
                    self._rotator.start(interval)
                    self._append_log(f"🔄 Ротация запущена (каждые {interval} сек)")
                except ValueError:
                    pass

    def _stop_proxy(self):
        """Останавливает приложение и ротацию."""
        self._rotator.stop()
        self._launcher.stop()
        self._is_running = False
        self._update_status(False)
        self._append_log("🛑 Проксирование остановлено")

    def _on_rotation_toggle(self):
        """Обрабатывает переключение чекбокса ротации."""
        enabled = self._rotation_var.get()
        self._manager.rotation_enabled = enabled
        self._manager.save_settings()

        if not enabled and self._rotator.is_running():
            self._rotator.stop()
            self._append_log("⏸ Ротация прокси отключена")

    def _on_rotate_now(self):
        """Немедленно переключает на следующий прокси."""
        if len(self._manager.proxies) < 2:
            messagebox.showinfo(
                "Информация", "Нужно минимум 2 прокси для ротации", parent=self
            )
            return
        new_proxy = self._rotator.rotate_now()
        if new_proxy:
            self._refresh_proxy_list()
            self._refresh_current_proxy_label()
            self._append_log(f"🔄 Переключено на: {new_proxy}")

            # Если приложение запущено — перезапускаем с новым прокси
            if self._is_running and self._launcher.is_running():
                self._append_log("🔄 Перезапуск с новым прокси...")
                self._launcher.stop()
                self._launcher.launch(self._manager.selected_app, new_proxy)

    def _on_proxy_rotated(self, new_proxy):
        """Вызывается при автоматической ротации прокси."""
        self.after(0, lambda: self._handle_rotation(new_proxy))

    def _handle_rotation(self, new_proxy):
        """Обрабатывает ротацию прокси в основном потоке GUI."""
        self._refresh_proxy_list()
        self._refresh_current_proxy_label()
        self._append_log(f"🔄 Авто-ротация: {new_proxy}")

        # Перезапускаем приложение с новым прокси
        if self._is_running and self._launcher.is_running():
            self._launcher.stop()
            self._launcher.launch(self._manager.selected_app, new_proxy)

    # ── Периодические задачи ─────────────────────────────────────────────────

    def _schedule_status_update(self):
        """Планирует периодическую проверку статуса запущенного приложения."""
        self._check_app_status()
        self.after(2000, self._schedule_status_update)

    def _check_app_status(self):
        """Проверяет, работает ли запущенное приложение."""
        if self._is_running and not self._launcher.is_running():
            # Приложение завершилось
            self._is_running = False
            self._rotator.stop()
            self._update_status(False)
            self._append_log("ℹ️ Приложение завершило работу")

    # ── Закрытие окна ────────────────────────────────────────────────────────

    def _on_close(self):
        """Обрабатывает закрытие окна: останавливает всё и сохраняет настройки."""
        if self._is_running:
            self._stop_proxy()
        self._manager.save_settings()
        self.destroy()
