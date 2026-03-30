"""
Модуль управления прокси-конфигурациями.
Отвечает за хранение, добавление и удаление прокси из списка,
а также за сохранение/загрузку настроек из JSON-файла.
"""

import json
import logging
import os
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Путь к файлу настроек
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "settings.json")


class ProxyConfig:
    """Конфигурация одного прокси-сервера."""

    def __init__(self, proxy_type: str, host: str, port: int,
                 username: str = "", password: str = ""):
        self.proxy_type = proxy_type  # "SOCKS5" или "HTTP"
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.status = "Не проверен"  # Статус последней проверки

    def to_dict(self) -> Dict:
        """Преобразует конфигурацию в словарь для сохранения."""
        return {
            "proxy_type": self.proxy_type,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ProxyConfig":
        """Создаёт конфигурацию из словаря."""
        cfg = cls(
            proxy_type=data.get("proxy_type", "SOCKS5"),
            host=data.get("host", ""),
            port=int(data.get("port", 1080)),
            username=data.get("username", ""),
            password=data.get("password", ""),
        )
        cfg.status = data.get("status", "Не проверен")
        return cfg

    def __str__(self) -> str:
        auth = f"{self.username}@" if self.username else ""
        return f"{self.proxy_type}://{auth}{self.host}:{self.port}"

    def get_url(self) -> str:
        """Возвращает URL прокси для использования в переменных окружения."""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        elif self.username:
            auth = f"{self.username}@"
        else:
            auth = ""
        scheme = "socks5" if self.proxy_type == "SOCKS5" else "http"
        return f"{scheme}://{auth}{self.host}:{self.port}"


class ProxyManager:
    """
    Менеджер прокси-серверов.
    Управляет списком прокси и настройками приложения.
    """

    def __init__(self):
        self.proxies: List[ProxyConfig] = []
        self.selected_app: str = ""
        self.rotation_enabled: bool = False
        self.rotation_interval: int = 60  # секунды
        self.last_selected_proxy: int = 0
        self._current_index: int = 0
        self.load_settings()

    def add_proxy(self, proxy: ProxyConfig) -> None:
        """Добавляет прокси в список."""
        self.proxies.append(proxy)
        self.save_settings()

    def remove_proxy(self, index: int) -> None:
        """Удаляет прокси по индексу."""
        if 0 <= index < len(self.proxies):
            self.proxies.pop(index)
            # Корректируем текущий индекс
            if self._current_index >= len(self.proxies) and self._current_index > 0:
                self._current_index = len(self.proxies) - 1
            self.save_settings()

    def get_proxy(self, index: int) -> Optional[ProxyConfig]:
        """Возвращает прокси по индексу."""
        if 0 <= index < len(self.proxies):
            return self.proxies[index]
        return None

    def get_current_proxy(self) -> Optional[ProxyConfig]:
        """Возвращает текущий активный прокси."""
        return self.get_proxy(self._current_index)

    def get_current_index(self) -> int:
        """Возвращает индекс текущего активного прокси."""
        return self._current_index

    def set_current_index(self, index: int) -> None:
        """Устанавливает текущий активный прокси."""
        if 0 <= index < len(self.proxies):
            self._current_index = index
            self.last_selected_proxy = index
            self.save_settings()

    def next_proxy(self) -> Optional[ProxyConfig]:
        """Переключается на следующий прокси (для ротации)."""
        if not self.proxies:
            return None
        self._current_index = (self._current_index + 1) % len(self.proxies)
        self.last_selected_proxy = self._current_index
        self.save_settings()
        return self.get_current_proxy()

    def set_selected_app(self, app_path: str) -> None:
        """Устанавливает путь к выбранному приложению."""
        self.selected_app = app_path
        self.save_settings()

    def save_settings(self) -> None:
        """Сохраняет настройки в JSON-файл."""
        data = {
            "proxies": [p.to_dict() for p in self.proxies],
            "selected_app": self.selected_app,
            "rotation_enabled": self.rotation_enabled,
            "rotation_interval": self.rotation_interval,
            "last_selected_proxy": self.last_selected_proxy,
        }
        try:
            os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Ошибка сохранения настроек: %s", e)

    def load_settings(self) -> None:
        """Загружает настройки из JSON-файла."""
        if not os.path.exists(SETTINGS_FILE):
            return
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.proxies = [ProxyConfig.from_dict(p) for p in data.get("proxies", [])]
            self.selected_app = data.get("selected_app", "")
            self.rotation_enabled = data.get("rotation_enabled", False)
            self.rotation_interval = data.get("rotation_interval", 60)
            self.last_selected_proxy = data.get("last_selected_proxy", 0)
            # Восстанавливаем выбранный прокси
            if self.proxies and 0 <= self.last_selected_proxy < len(self.proxies):
                self._current_index = self.last_selected_proxy
        except Exception as e:
            logger.error("Ошибка загрузки настроек: %s", e)
