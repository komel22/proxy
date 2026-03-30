@echo off
chcp 65001 > nul
echo ========================================
echo    Proxy Switcher - Установка
echo ========================================
echo.
echo Установка зависимостей Python...
pip install -r requirements.txt
echo.
echo ========================================
echo    Установка завершена!
echo    Запуск: python main.py
echo ========================================
pause
