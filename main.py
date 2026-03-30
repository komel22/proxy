"""
Точка входа приложения Proxy Switcher.
Запускает графический интерфейс.
"""

import sys
import os
import logging

# Добавляем корневую директорию в sys.path для корректных импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Настройка базового логирования для отладки
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from gui.app import ProxySwitcherApp


def main():
    """Запускает приложение Proxy Switcher."""
    app = ProxySwitcherApp()
    app.mainloop()


if __name__ == "__main__":
    main()
