"""
Модуль проверки прокси-серверов.
Выполняет тест доступности и измерение времени отклика прокси.
"""

import socket
import time
import threading
from typing import Callable, Optional, Tuple

# Попытка импорта socks (PySocks). Если не установлен — работаем без него.
try:
    import socks
    SOCKS_AVAILABLE = True
except ImportError:
    SOCKS_AVAILABLE = False

# Тестовый URL и хост для проверки соединения
TEST_HOST = "httpbin.org"
TEST_PORT = 80
TEST_PATH = "/ip"
CONNECT_TIMEOUT = 10  # секунды


def check_proxy(proxy_config) -> Tuple[bool, str, float]:
    """
    Проверяет доступность прокси-сервера.

    Args:
        proxy_config: Объект ProxyConfig с параметрами прокси

    Returns:
        Tuple (успех: bool, сообщение: str, время_пинга: float)
    """
    start_time = time.time()

    try:
        if proxy_config.proxy_type == "SOCKS5":
            return _check_socks5(proxy_config, start_time)
        else:
            return _check_http(proxy_config, start_time)
    except socket.timeout:
        elapsed = time.time() - start_time
        return False, f"Превышено время ожидания ({elapsed:.1f}с)", elapsed
    except ConnectionRefusedError:
        elapsed = time.time() - start_time
        return False, "Соединение отклонено", elapsed
    except OSError as e:
        elapsed = time.time() - start_time
        return False, f"Ошибка сети: {e}", elapsed
    except Exception as e:
        elapsed = time.time() - start_time
        return False, f"Ошибка: {e}", elapsed


def _check_socks5(proxy_config, start_time: float) -> Tuple[bool, str, float]:
    """Проверка SOCKS5 прокси через прямое TCP-подключение к прокси-серверу."""
    if SOCKS_AVAILABLE:
        # Используем PySocks для реальной проверки через прокси
        try:
            s = socks.socksocket()
            s.set_proxy(
                socks.SOCKS5,
                proxy_config.host,
                proxy_config.port,
                username=proxy_config.username or None,
                password=proxy_config.password or None,
            )
            s.settimeout(CONNECT_TIMEOUT)
            s.connect((TEST_HOST, TEST_PORT))
            # Отправляем HTTP-запрос через прокси
            request = f"GET {TEST_PATH} HTTP/1.0\r\nHost: {TEST_HOST}\r\nConnection: close\r\n\r\n"
            s.sendall(request.encode())
            response = s.recv(256).decode("utf-8", errors="ignore")
            s.close()
            elapsed = time.time() - start_time
            if "200" in response or "HTTP/" in response:
                return True, f"ОК ({elapsed * 1000:.0f} мс)", elapsed
            else:
                return False, f"Неожиданный ответ прокси", elapsed
        except socks.ProxyConnectionError as e:
            elapsed = time.time() - start_time
            return False, f"Ошибка подключения к прокси: {e}", elapsed
        except socks.GeneralProxyError as e:
            elapsed = time.time() - start_time
            return False, f"Ошибка прокси: {e}", elapsed
    else:
        # Без PySocks — просто проверяем TCP-подключение к прокси-серверу
        return _check_tcp_connection(proxy_config, start_time)


def _check_http(proxy_config, start_time: float) -> Tuple[bool, str, float]:
    """Проверка HTTP прокси через HTTP CONNECT или обычный GET-запрос."""
    try:
        # Подключаемся к прокси-серверу
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(CONNECT_TIMEOUT)
        s.connect((proxy_config.host, proxy_config.port))

        # Формируем HTTP CONNECT запрос
        if proxy_config.username and proxy_config.password:
            import base64
            credentials = base64.b64encode(
                f"{proxy_config.username}:{proxy_config.password}".encode()
            ).decode()
            auth_header = f"Proxy-Authorization: Basic {credentials}\r\n"
        else:
            auth_header = ""

        connect_req = (
            f"CONNECT {TEST_HOST}:{TEST_PORT} HTTP/1.1\r\n"
            f"Host: {TEST_HOST}:{TEST_PORT}\r\n"
            f"{auth_header}"
            f"Connection: keep-alive\r\n\r\n"
        )
        s.sendall(connect_req.encode())
        response = s.recv(256).decode("utf-8", errors="ignore")
        s.close()

        elapsed = time.time() - start_time
        if "200" in response:
            return True, f"ОК ({elapsed * 1000:.0f} мс)", elapsed
        elif "407" in response:
            return False, "Требуется авторизация (407)", elapsed
        elif "403" in response or "401" in response:
            return False, "Доступ запрещён (403/401)", elapsed
        elif "HTTP/" in response:
            # Прокси ответил — значит он работает, пусть и не через CONNECT
            return True, f"ОК ({elapsed * 1000:.0f} мс)", elapsed
        else:
            return False, "Нет ответа от прокси", elapsed
    except Exception as e:
        elapsed = time.time() - start_time
        return False, f"Ошибка: {e}", elapsed


def _check_tcp_connection(proxy_config, start_time: float) -> Tuple[bool, str, float]:
    """Базовая проверка TCP-соединения с прокси-сервером."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(CONNECT_TIMEOUT)
    s.connect((proxy_config.host, proxy_config.port))
    s.close()
    elapsed = time.time() - start_time
    return True, f"TCP ОК ({elapsed * 1000:.0f} мс)", elapsed


def check_proxy_async(proxy_config, callback: Callable[[bool, str, float], None]) -> None:
    """
    Асинхронная проверка прокси в отдельном потоке.

    Args:
        proxy_config: Конфигурация прокси
        callback: Функция обратного вызова (success, message, elapsed)
    """
    def _run():
        result = check_proxy(proxy_config)
        callback(*result)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
