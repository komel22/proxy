"""
Виджет списка прокси.
Отображает таблицу с прокси-серверами и их статусами.
"""

import tkinter as tk
from tkinter import ttk

# Цвета тёмной темы
BG_DARK = "#1e1e2e"
BG_MEDIUM = "#2a2a3e"
BG_LIGHT = "#313149"
TEXT_COLOR = "#cdd6f4"
ACCENT_COLOR = "#89b4fa"
SUCCESS_COLOR = "#a6e3a1"
ERROR_COLOR = "#f38ba8"
WARNING_COLOR = "#fab387"
HEADER_COLOR = "#89dceb"


class ProxyListWidget(tk.Frame):
    """
    Виджет для отображения списка прокси в виде таблицы.
    Поддерживает выделение строк и обратные вызовы при выборе.
    """

    COLUMNS = ("Тип", "Хост", "Порт", "Пользователь", "Статус")

    def __init__(self, parent, on_select=None, **kwargs):
        """
        Args:
            parent: Родительский виджет
            on_select: Callback при выборе прокси (индекс)
        """
        super().__init__(parent, bg=BG_DARK, **kwargs)
        self._on_select = on_select
        self._proxies = []  # Кэш текущих прокси
        self._setup_ui()

    def _setup_ui(self):
        """Создаёт элементы интерфейса."""
        # Настройка стиля таблицы
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "ProxyList.Treeview",
            background=BG_MEDIUM,
            foreground=TEXT_COLOR,
            rowheight=28,
            fieldbackground=BG_MEDIUM,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        style.configure(
            "ProxyList.Treeview.Heading",
            background=BG_LIGHT,
            foreground=HEADER_COLOR,
            font=("Segoe UI", 10, "bold"),
            borderwidth=0,
        )
        style.map(
            "ProxyList.Treeview",
            background=[("selected", BG_LIGHT)],
            foreground=[("selected", ACCENT_COLOR)],
        )

        # Таблица
        self._tree = ttk.Treeview(
            self,
            columns=self.COLUMNS,
            show="headings",
            style="ProxyList.Treeview",
            selectmode="browse",
        )

        # Настройка столбцов
        column_widths = {"Тип": 80, "Хост": 160, "Порт": 70, "Пользователь": 120, "Статус": 150}
        for col in self.COLUMNS:
            self._tree.heading(col, text=col)
            self._tree.column(col, width=column_widths.get(col, 100), minwidth=50, anchor="center")

        # Полоса прокрутки
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)

        # Размещение
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Обработчик выбора
        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Теги цвета для статуса
        self._tree.tag_configure("ok", foreground=SUCCESS_COLOR)
        self._tree.tag_configure("error", foreground=ERROR_COLOR)
        self._tree.tag_configure("checking", foreground=WARNING_COLOR)
        self._tree.tag_configure("default", foreground=TEXT_COLOR)

    def _on_tree_select(self, event):
        """Вызывается при выборе строки в таблице."""
        selected = self._tree.selection()
        if selected and self._on_select:
            # Получаем индекс выбранной строки
            item_id = selected[0]
            children = self._tree.get_children()
            index = list(children).index(item_id)
            self._on_select(index)

    def refresh(self, proxies: list) -> None:
        """
        Обновляет список прокси в таблице.

        Args:
            proxies: Список объектов ProxyConfig
        """
        self._proxies = proxies

        # Сохраняем выбранный элемент
        selected = self._tree.selection()
        selected_index = -1
        if selected:
            children = list(self._tree.get_children())
            if selected[0] in children:
                selected_index = children.index(selected[0])

        # Очищаем таблицу
        self._tree.delete(*self._tree.get_children())

        # Добавляем прокси
        for proxy in proxies:
            # Определяем тег для цветового оформления статуса
            status = proxy.status
            if "ОК" in status or "OK" in status:
                tag = "ok"
            elif "Ошибка" in status or "❌" in status or "отклонено" in status.lower():
                tag = "error"
            elif "Проверка" in status or "..." in status:
                tag = "checking"
            else:
                tag = "default"

            self._tree.insert(
                "",
                "end",
                values=(
                    proxy.proxy_type,
                    proxy.host,
                    proxy.port,
                    proxy.username or "—",
                    status,
                ),
                tags=(tag,),
            )

        # Восстанавливаем выделение
        children = self._tree.get_children()
        if selected_index >= 0 and selected_index < len(children):
            self._tree.selection_set(children[selected_index])

    def get_selected_index(self) -> int:
        """Возвращает индекс выбранной строки или -1."""
        selected = self._tree.selection()
        if not selected:
            return -1
        children = list(self._tree.get_children())
        if selected[0] in children:
            return children.index(selected[0])
        return -1

    def select_row(self, index: int) -> None:
        """Программно выбирает строку по индексу."""
        children = self._tree.get_children()
        if 0 <= index < len(children):
            self._tree.selection_set(children[index])
            self._tree.see(children[index])
