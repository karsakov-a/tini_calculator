import json
import logging
from datetime import datetime
from typing import Any, Dict, List

from config import (AGE, BIRTH_DATE, CT_PERCENT_DESC, D_DIMER_DESC,
                    ERROR_LOAD_HISTORY, ERROR_SAVE_HISTORY, GENDER,
                    INTERLEUKINS_DESC, LYMPHOCYTES_DESC, RESEARCH_DATE,
                    UNKNOWN_STATUS)
from core.calculator import get_interpretation_text
from utils.paths import get_history_file_path


def load_history() -> List[Dict[str, Any]]:
    """Загружает историю из JSON-файла."""
    history_file = get_history_file_path()
    if not history_file.exists():
        return []
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError) as e:
        logging.error(ERROR_LOAD_HISTORY.format(e))
        return []


def save_history(history: List[Dict[str, Any]]):
    """Сохраняет историю в JSON-файл."""
    history_file = get_history_file_path()
    try:
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except IOError as e:
        logging.error(ERROR_SAVE_HISTORY.format(e))
        raise


def create_history_entry(full_report, raw_data):
    """Создаёт запись для истории на основе расчёта."""
    return {
        "id": datetime.now().strftime("%Y%m%d_%H%M%S")
        + f"_{hash(full_report) % 10000:04d}",
        "timestamp": datetime.now().isoformat(),
        "full_report": full_report,
        "raw_data": raw_data,
    }


def build_full_report(
    surname: str,
    name: str,
    patronymic: str,
    gender: str,
    dob_str: str,
    study_str: str,
    age_str: str,
    d_dimer: float,
    interleukins: float,
    lymphocytes: float,
    ct_str: str,
    citi: float,
    risk: str,
) -> str:
    """
    Формирует текстовый отчёт для копирования и PDF.
    """
    full_name = (
        UNKNOWN_STATUS
        if not (surname or name or patronymic)
        else " ".join(filter(None, [surname, name, patronymic])).title()
    )

    # Получаем CT-значение для логики предупреждения
    ct_value = 0.0
    if ct_str != UNKNOWN_STATUS:
        try:
            ct_value = float(ct_str.replace(" %", ""))
        except (ValueError, AttributeError):
            ct_value = 0.0

    full_interpretation = get_interpretation_text(citi, ct_value)

    return (
        f"Пациент: {full_name}\n"
        f"{GENDER}: {gender}\n"
        f"{BIRTH_DATE}: {dob_str}\n"
        f"{AGE}: {age_str}\n"
        f"{RESEARCH_DATE}: {study_str}\n\n"
        f"{D_DIMER_DESC[0].replace(' *', '')}: {d_dimer} нг/мл\n"
        f"{INTERLEUKINS_DESC[0].replace(' *', '')}: {interleukins} пг/мл\n"
        f"{LYMPHOCYTES_DESC[0].replace(' *', '')}: {lymphocytes} ×10⁹/л\n"
        f"{CT_PERCENT_DESC[0]}: {ct_str}\n"
        f"CITI-индекс: {citi:,.0f}\n"
        f"Интерпретация: {full_interpretation}\n"
    )
