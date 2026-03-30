"""
Модуль ротации прокси.
Автоматически переключает прокси по таймеру или вручную.
"""

import logging
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class ProxyRotator:
    """
    Ротатор прокси-серверов.
    Переключает активный прокси через заданный интервал времени.
    """

    def __init__(self, proxy_manager, on_rotate: Optional[Callable] = None):
        """
        Args:
            proxy_manager: Менеджер прокси (ProxyManager)
            on_rotate: Callback при смене прокси (вызывается с новым ProxyConfig)
        """
        self._proxy_manager = proxy_manager
        self._on_rotate = on_rotate
        self._timer_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False

    def set_on_rotate(self, callback: Callable) -> None:
        """Устанавливает callback для смены прокси."""
        self._on_rotate = callback

    def is_running(self) -> bool:
        """Проверяет, активна ли автоматическая ротация."""
        return self._running

    def start(self, interval_seconds: int = 60) -> bool:
        """
        Запускает автоматическую ротацию прокси.

        Args:
            interval_seconds: Интервал смены прокси в секундах

        Returns:
            True если запущено успешно
        """
        if self._running:
            return False

        if len(self._proxy_manager.proxies) < 2:
            return False  # Нет смысла ротировать при одном прокси

        self._stop_event.clear()
        self._running = True
        self._timer_thread = threading.Thread(
            target=self._rotation_loop,
            args=(interval_seconds,),
            daemon=True,
        )
        self._timer_thread.start()
        return True

    def stop(self) -> None:
        """Останавливает автоматическую ротацию."""
        if not self._running:
            return
        self._running = False
        self._stop_event.set()
        if self._timer_thread:
            self._timer_thread.join(timeout=2)
            self._timer_thread = None

    def rotate_now(self) -> Optional[object]:
        """
        Немедленно переключает на следующий прокси.

        Returns:
            Новый активный ProxyConfig или None
        """
        new_proxy = self._proxy_manager.next_proxy()
        if new_proxy and self._on_rotate:
            self._on_rotate(new_proxy)
        return new_proxy

    def _rotation_loop(self, interval_seconds: int) -> None:
        """Основной цикл ротации прокси."""
        while not self._stop_event.wait(timeout=interval_seconds):
            if not self._running:
                break
            new_proxy = self._proxy_manager.next_proxy()
            if new_proxy and self._on_rotate:
                try:
                    self._on_rotate(new_proxy)
                except Exception as e:
                    logger.error("Ошибка в callback ротации: %s", e)
