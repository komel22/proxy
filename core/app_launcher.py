"""
Модуль запуска приложения через прокси.
Запускает целевой .exe с переменными окружения прокси,
что позволяет перехватывать трафик для программ,
уважающих системные переменные окружения прокси.
"""

import os
import subprocess
import sys
from typing import Optional, Callable


class AppLauncher:
    """
    Запускает целевое приложение с проксированием через переменные окружения.

    Устанавливает HTTP_PROXY, HTTPS_PROXY, ALL_PROXY для дочернего процесса,
    что работает для большинства приложений, использующих системные настройки прокси
    (браузеры на Chromium/Firefox, curl, python-requests и т.д.).
    """

    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._log_callback: Optional[Callable[[str], None]] = None

    def set_log_callback(self, callback: Callable[[str], None]) -> None:
        """Устанавливает функцию для логирования."""
        self._log_callback = callback

    def _log(self, message: str) -> None:
        """Отправляет сообщение в лог."""
        if self._log_callback:
            self._log_callback(message)
        else:
            print(message)

    def is_running(self) -> bool:
        """Проверяет, запущено ли приложение."""
        if self._process is None:
            return False
        # Проверяем, что процесс ещё работает
        return self._process.poll() is None

    def launch(self, app_path: str, proxy_config) -> bool:
        """
        Запускает приложение с настройками прокси.

        Args:
            app_path: Путь к .exe файлу
            proxy_config: Конфигурация прокси (объект ProxyConfig)

        Returns:
            True если запуск успешен, False при ошибке
        """
        if not app_path:
            self._log("❌ Приложение не выбрано")
            return False

        if not os.path.exists(app_path):
            self._log(f"❌ Файл не найден: {app_path}")
            return False

        if self.is_running():
            self._log("⚠️ Приложение уже запущено")
            return False

        # Формируем переменные окружения для прокси
        env = os.environ.copy()
        proxy_url = proxy_config.get_url()

        # Устанавливаем прокси для разных протоколов
        env["HTTP_PROXY"] = proxy_url
        env["HTTPS_PROXY"] = proxy_url
        env["ALL_PROXY"] = proxy_url
        # Версии в нижнем регистре тоже поддерживаются многими приложениями
        env["http_proxy"] = proxy_url
        env["https_proxy"] = proxy_url
        env["all_proxy"] = proxy_url

        try:
            self._log(f"🚀 Запуск: {os.path.basename(app_path)}")
            self._log(f"🔗 Прокси: {proxy_config}")

            self._process = subprocess.Popen(
                [app_path],
                env=env,
                # Запускаем в том же каталоге, что и .exe
                cwd=os.path.dirname(app_path),
                # Не создаём новое консольное окно
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )

            self._log(f"✅ Приложение запущено (PID: {self._process.pid})")
            return True

        except PermissionError:
            self._log(f"❌ Нет прав для запуска: {app_path}")
            return False
        except FileNotFoundError:
            self._log(f"❌ Файл не найден: {app_path}")
            return False
        except OSError as e:
            self._log(f"❌ Ошибка запуска: {e}")
            return False

    def stop(self) -> bool:
        """
        Останавливает запущенное приложение.

        Returns:
            True если остановка успешна
        """
        if not self.is_running():
            self._log("⚠️ Приложение не запущено")
            return False

        try:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Принудительно завершаем если не остановилось
                self._process.kill()
                self._process.wait()
            self._log("🛑 Приложение остановлено")
            self._process = None
            return True
        except OSError as e:
            self._log(f"❌ Ошибка остановки: {e}")
            return False

    def get_pid(self) -> Optional[int]:
        """Возвращает PID запущенного процесса."""
        if self._process:
            return self._process.pid
        return None

    def check_status(self) -> str:
        """Возвращает текстовый статус приложения."""
        if self._process is None:
            return "Не запущено"
        poll = self._process.poll()
        if poll is None:
            return f"Работает (PID: {self._process.pid})"
        else:
            return f"Завершено (код: {poll})"
