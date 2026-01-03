import sys
from pathlib import Path

from config import HISTORY_FILENAME


def get_app_dir() -> Path:
    """
    Возвращает путь к папке, где находится исполняемый файл.
    """
    if getattr(sys, "frozen", False):
        # Запуск из .exe (PyInstaller)
        return Path(sys.executable).parent
    else:
        # Запуск из исходного кода
        return Path(__file__).parent.parent.resolve()


def get_history_file_path() -> Path:
    """
    Возвращает полный путь к файлу истории.
    """
    return get_app_dir() / HISTORY_FILENAME
