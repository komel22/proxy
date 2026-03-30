"""
Диалоговые окна настроек.
Диалог добавления/редактирования прокси-сервера.
"""

import tkinter as tk
from tkinter import messagebox

from core.proxy_checker import check_proxy_async
from core.proxy_manager import ProxyConfig

# Цвета тёмной темы
BG_DARK = "#1e1e2e"
BG_MEDIUM = "#2a2a3e"
BG_LIGHT = "#313149"
BG_INPUT = "#45475a"
TEXT_COLOR = "#cdd6f4"
ACCENT_COLOR = "#89b4fa"
SUCCESS_COLOR = "#a6e3a1"
ERROR_COLOR = "#f38ba8"
WARNING_COLOR = "#fab387"
BTN_PRIMARY = "#89b4fa"
BTN_HOVER = "#74c7ec"
BTN_DANGER = "#f38ba8"


class AddProxyDialog(tk.Toplevel):
    """
    Диалог добавления нового прокси-сервера.
    Поля: тип (SOCKS5/HTTP), IP, порт, логин, пароль.
    """

    def __init__(self, parent, on_save=None):
        """
        Args:
            parent: Родительское окно
            on_save: Callback при сохранении (ProxyConfig)
        """
        super().__init__(parent)
        self._on_save = on_save
        self._result: ProxyConfig = None

        self.title("Добавить прокси")
        self.resizable(False, False)
        self.configure(bg=BG_DARK)
        self.grab_set()  # Модальный диалог

        # Центрируем окно относительно родителя
        self.geometry("420x380")
        self._center_on_parent(parent)

        self._setup_ui()

    def _center_on_parent(self, parent):
        """Центрирует окно относительно родительского."""
        parent.update_idletasks()
        px = parent.winfo_x() + parent.winfo_width() // 2
        py = parent.winfo_y() + parent.winfo_height() // 2
        self.geometry(f"+{px - 210}+{py - 190}")

    def _make_label(self, parent, text: str):
        """Создаёт стандартный лейбл."""
        return tk.Label(parent, text=text, bg=BG_DARK, fg=TEXT_COLOR,
                        font=("Segoe UI", 10))

    def _make_entry(self, parent, textvariable=None, show=None, width=30):
        """Создаёт стандартное поле ввода."""
        kwargs = dict(
            bg=BG_INPUT, fg=TEXT_COLOR, insertbackground=TEXT_COLOR,
            relief="flat", font=("Segoe UI", 10), width=width,
        )
        if textvariable:
            kwargs["textvariable"] = textvariable
        if show:
            kwargs["show"] = show
        entry = tk.Entry(parent, **kwargs)
        entry.configure(highlightthickness=1, highlightbackground=BG_LIGHT,
                        highlightcolor=ACCENT_COLOR)
        return entry

    def _setup_ui(self):
        """Строит форму диалога."""
        pad = {"padx": 20, "pady": 6}

        # Заголовок
        tk.Label(
            self, text="Добавить прокси-сервер",
            bg=BG_DARK, fg=ACCENT_COLOR,
            font=("Segoe UI", 13, "bold"),
        ).pack(pady=(18, 10))

        form = tk.Frame(self, bg=BG_DARK)
        form.pack(fill="x", padx=20)

        # Тип прокси
        self._make_label(form, "Тип прокси:").grid(row=0, column=0, sticky="w", pady=6)
        self._type_var = tk.StringVar(value="SOCKS5")
        type_frame = tk.Frame(form, bg=BG_DARK)
        type_frame.grid(row=0, column=1, sticky="w", pady=6)
        for ptype in ("SOCKS5", "HTTP"):
            tk.Radiobutton(
                type_frame, text=ptype, variable=self._type_var, value=ptype,
                bg=BG_DARK, fg=TEXT_COLOR, selectcolor=BG_LIGHT,
                activebackground=BG_DARK, activeforeground=ACCENT_COLOR,
                font=("Segoe UI", 10),
            ).pack(side="left", padx=(0, 12))

        # IP / Хост
        self._make_label(form, "IP / Хост:").grid(row=1, column=0, sticky="w", pady=6)
        self._host_var = tk.StringVar()
        self._host_entry = self._make_entry(form, textvariable=self._host_var)
        self._host_entry.grid(row=1, column=1, sticky="ew", pady=6)

        # Порт
        self._make_label(form, "Порт:").grid(row=2, column=0, sticky="w", pady=6)
        self._port_var = tk.StringVar(value="1080")
        self._port_entry = self._make_entry(form, textvariable=self._port_var, width=10)
        self._port_entry.grid(row=2, column=1, sticky="w", pady=6)

        # Логин
        self._make_label(form, "Логин:").grid(row=3, column=0, sticky="w", pady=6)
        self._user_var = tk.StringVar()
        self._user_entry = self._make_entry(form, textvariable=self._user_var)
        self._user_entry.grid(row=3, column=1, sticky="ew", pady=6)

        # Пароль
        self._make_label(form, "Пароль:").grid(row=4, column=0, sticky="w", pady=6)
        self._pass_var = tk.StringVar()
        self._pass_entry = self._make_entry(form, textvariable=self._pass_var, show="•")
        self._pass_entry.grid(row=4, column=1, sticky="ew", pady=6)

        form.columnconfigure(1, weight=1)

        # Статус проверки
        self._status_var = tk.StringVar(value="")
        self._status_label = tk.Label(
            self, textvariable=self._status_var,
            bg=BG_DARK, fg=WARNING_COLOR,
            font=("Segoe UI", 9), wraplength=380,
        )
        self._status_label.pack(pady=(4, 0))

        # Кнопки
        btn_frame = tk.Frame(self, bg=BG_DARK)
        btn_frame.pack(pady=(12, 18))

        self._check_btn = self._make_button(
            btn_frame, "🔍 Проверить", self._on_check, ACCENT_COLOR
        )
        self._check_btn.pack(side="left", padx=6)

        self._save_btn = self._make_button(
            btn_frame, "💾 Сохранить", self._on_save_click, SUCCESS_COLOR
        )
        self._save_btn.pack(side="left", padx=6)

        self._make_button(
            btn_frame, "✖ Отмена", self.destroy, BTN_DANGER
        ).pack(side="left", padx=6)

        # Фокус на поле хоста
        self._host_entry.focus_set()

    def _make_button(self, parent, text: str, command, fg_color=TEXT_COLOR):
        """Создаёт стандартную кнопку диалога."""
        btn = tk.Button(
            parent, text=text, command=command,
            bg=BG_LIGHT, fg=fg_color, activebackground=BG_MEDIUM,
            activeforeground=fg_color, relief="flat",
            font=("Segoe UI", 10, "bold"), padx=14, pady=6, cursor="hand2",
        )
        return btn

    def _get_proxy_config(self):
        """Создаёт объект ProxyConfig из введённых данных или возвращает None при ошибке."""
        host = self._host_var.get().strip()
        port_str = self._port_var.get().strip()

        if not host:
            messagebox.showerror("Ошибка", "Введите IP-адрес или хост прокси", parent=self)
            return None

        try:
            port = int(port_str)
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            messagebox.showerror("Ошибка", "Порт должен быть числом от 1 до 65535", parent=self)
            return None

        return ProxyConfig(
            proxy_type=self._type_var.get(),
            host=host,
            port=port,
            username=self._user_var.get().strip(),
            password=self._pass_var.get(),
        )

    def _on_check(self):
        """Проверяет доступность введённого прокси."""
        cfg = self._get_proxy_config()
        if not cfg:
            return

        self._status_var.set("⏳ Проверка...")
        self._status_label.config(fg=WARNING_COLOR)
        self._check_btn.config(state="disabled")

        def callback(success, message, elapsed):
            self._check_btn.config(state="normal")
            if success:
                self._status_var.set(f"✅ {message}")
                self._status_label.config(fg=SUCCESS_COLOR)
            else:
                self._status_var.set(f"❌ {message}")
                self._status_label.config(fg=ERROR_COLOR)

        check_proxy_async(cfg, callback)

    def _on_save_click(self):
        """Сохраняет прокси и закрывает диалог."""
        cfg = self._get_proxy_config()
        if not cfg:
            return
        self._result = cfg
        if self._on_save:
            self._on_save(cfg)
        self.destroy()
