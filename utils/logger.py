import logging
from datetime import datetime
from pathlib import Path


def setup_logger(debug: bool = False):
    """
    Настраивает логирование в файл по дате.
    """
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8")],
    )
    logging.info("Запуск CITI Calculator")
