from PySide6.QtCore import QDate

# === Настройки приложения ===
APP_NAME = "CITI Calculator"
APP_TITLE = "CITI Calculator — Тромбо-воспалительный индекс"
WINDOW_SIZE = (440, 400)
FONT_FAMILY = "Segoe UI"
FONT_SIZE_BASE = 10
FONT_SIZE_TITLE = 14
FONT_SIZE_RESULT_VALUE = 16
FONT_SIZE_RESULT_MESSAGE = 12

# === Валидация полей ===
MIN_NAME_LEN = 2
MAX_NAME_LEN = 20
MIN_DDIMER_INTERLEUKINS = 0.0
MAX_DDIMER_INTERLEUKINS = 5000.0
MIN_LYMPHOCYTES = 0.0
MAX_LYMPHOCYTES = 10.0
DECIMAL_PLACES = 5
MIN_CT_PERCENT = 0
MAX_CT_PERCENT = 100

# === Пороги интерпретации ===
CITI_LOW_THRESHOLD = 100_000
CITI_HIGH_THRESHOLD = 500_000

# === Даты ===
MIN_DATE = QDate(1920, 1, 1)
MAX_DATE = QDate.currentDate()
DEFAULT_DATE_BORN = QDate(1985, 1, 1)
DEFAULT_DATE_RESEARCH = QDate.currentDate()
DATE_FORMAT = "dd.MM.yyyy"

# === Сообщения и надписи ===
DEBUG_MODE_ON = "Программа запущена в режиме отладки"
ERROR_MESSAGE_CT = (
    "Объем поражения лёгких должен быть целым числом от 0 до 100"
)
ERROR_EXPORT_HISTORY_IO = "Не удалось сохранить файл истории:\n{}"
ERROR_EXPORT_HISTORY_GENERIC = "Неизвестная ошибка при экспорте истории:\n{}"
ERROR_LOAD_ENTRY_DATE = "Некорректный формат даты в записи: {}"
ERROR_LOAD_HISTORY = "Ошибка загрузки истории: {}"
ERROR_SAVE_HISTORY = "Ошибка сохранения истории:\n{}"
INSTRUCTION_DEFAULT = "Введите все обязательные поля (*)"
EXTRA_WARNING_CT_CITI = (
    "\n⚠️ При CITI более 500 000 и КТ более 70%\nриск смерти превышает 95%"
)

# Поля ввода: (метка, ключ, placeholder)
SURNAME_DESC = ("Фамилия", "surname")
NAME_DESC = ("Имя", "name")
PATRONYMIC_DESC = ("Отчество", "patronymic")
GENDER = "Пол"
D_DIMER_DESC = (
    "D-димер (нг/мл) *",
    "d_dimer",
    f"{MIN_DDIMER_INTERLEUKINS}–{MAX_DDIMER_INTERLEUKINS}",
)
INTERLEUKINS_DESC = (
    "Интерлейкины, IL–6 (пг/мл) *",
    "interleukins",
    f"{MIN_DDIMER_INTERLEUKINS}–{MAX_DDIMER_INTERLEUKINS}",
)
LYMPHOCYTES_DESC = (
    "Лимфоциты (×10⁹/л) *",
    "lymphocytes",
    f"от {MIN_LYMPHOCYTES} до {MAX_LYMPHOCYTES}",
)
CT_PERCENT_DESC = (
    "Объем поражения лёгких \nпо данным МСКТ (%)",
    "ct_percent",
    f"от {MIN_CT_PERCENT} до {MAX_CT_PERCENT}",
)
BIRTH_DATE = "Дата рождения"
AGE = "Возраст на момент исследования"
RESEARCH_DATE = "Дата исследования"

FULL_NAME_PLACEHOLDER = f"Только буквы, {MIN_NAME_LEN}–{MAX_NAME_LEN} символов"
FULL_NAME_PATTERN = f"^[а-яА-ЯёЁa-zA-Z]{{{MIN_NAME_LEN},{MAX_NAME_LEN}}}$"
UNKNOWN_STATUS = "Не указано"

# === Пол ===
GENDER_MALE = "Мужской"
GENDER_FEMALE = "Женский"

# === История расчётов ===
HISTORY_FILENAME = "citi_history.json"
EXPORT_CSV_FILENAME = "citi_history_export.csv"
EXPORT_HISTORY_BUTTON_TEXT = "Экспортировать историю"
HISTORY_DIALOG_TITLE = "Журнал расчётов CITI"
NO_HISTORY_MESSAGE = "История расчётов пуста."

# === Тексты кнопок ===
BUTTON_CALCULATE = "ВЫПОЛНИТЬ РАСЧЁТ"
BUTTON_RESET = "Сбросить"
BUTTON_COPY = "Скопировать отчёт"
BUTTON_SAVE_PDF = "Сохранить в PDF"
JOURNAL_BUTTON = "Журнал"

BUTTON_JOURNAL_OPEN = "Открыть"
BUTTON_JOURNAL_DELETE = "Удалить"
BUTTON_JOURNAL_EXPORT_CSV = "Экспортировать в CSV"
BUTTON_JOURNAL_CLOSE = "Закрыть"

# === Интерпретация ===
RISK_LOW = "Низкий риск смерти"
RISK_MODERATE = "Умеренный риск"
RISK_HIGH = "Высокий риск смерти"
COLOR_LOW = "#4CAF50"
COLOR_MODERATE = "#FFC107"
COLOR_HIGH = "#F44336"
