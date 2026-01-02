import logging
import os
import sys
from datetime import datetime
from functools import partial
from pathlib import Path

from dotenv import load_dotenv
from PySide6.QtCore import QDate, QRegularExpression, Qt
from PySide6.QtGui import (
    QFont,
    QIntValidator,
    QRegularExpressionValidator,
    QTextDocument,
)
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QDateEdit,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

# === Настройки приложения ===
APP_NAME = "TINI Calculator"
APP_TITLE = "TINI Calculator — Тромбо-воспалительный индекс"
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
TINI_LOW_THRESHOLD = 100_000
TINI_HIGH_THRESHOLD = 500_000

# === Даты ===
MIN_DATE = QDate(1920, 1, 1)
MAX_DATE = QDate.currentDate()
DEFAULT_DATE_BORN = QDate(1985, 1, 1)
DEFAULT_DATE_RESEARCH = QDate.currentDate()
DATE_FORMAT = "dd.MM.yyyy"

# === Сообщения и надписи ===
ERROR_MESSAGE_CT = (
    "Объем поражения лёгких должен быть целым числом от 0 до 100"
)
INSTRUCTION_DEFAULT = "Введите все обязательные поля (*)"
EXTRA_WARNING_CT_TINI = (
    "\n⚠️ При TINI более 500 000 и КТ более 70%\nриск смерти превышает 95%"
)

# Поля ввода: (метка, ключ, placeholder)
SURNAME_DESC = ("Фамилия", "surname")
NAME_DESC = ("Имя", "name")
PATRONYMIC_DESC = ("Отчество", "patronymic")
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
GENDER = "Пол"
BIRTH_DATE = "Дата рождения"
AGE = "Возраст на момент исследования"
RESEARCH_DATE = "Дата исследования"

FULL_NAME_PLACEHOLDER = f"Только буквы, {MIN_NAME_LEN}–{MAX_NAME_LEN} символов"
FULL_NAME_PATTERN = f"^[а-яА-ЯёЁa-zA-Z]{{{MIN_NAME_LEN},{MAX_NAME_LEN}}}$"
UNKNOWN_STATUS = "Не указано"

# === Пол ===
GENDER_MALE = "Мужской"
GENDER_FEMALE = "Женский"

# === Тексты кнопок ===
BUTTON_CALCULATE = "ВЫПОЛНИТЬ РАСЧЁТ"
BUTTON_RESET = "Сбросить"
BUTTON_COPY = "Скопировать отчёт"
BUTTON_SAVE_PDF = "Сохранить в PDF"

# === Интерпретация ===
RISK_LOW = "Низкий риск смерти"
RISK_MODERATE = "Умеренный риск"
RISK_HIGH = "Высокий риск смерти"
COLOR_LOW = "#4CAF50"
COLOR_MODERATE = "#FFC107"
COLOR_HIGH = "#F44336"


def calculate_tini(
    d_dimer: float, interleukins: float, lymphocytes: float
) -> float:
    """Вычисляет TINI-индекс с защитой от деления на ноль."""
    denominator = lymphocytes if lymphocytes > 0 else 0.1
    return (d_dimer * interleukins) / denominator


def interpret_tini(tini: float):
    """Возвращает уровень риска и цвет по значению TINI."""
    if tini < TINI_LOW_THRESHOLD:
        return RISK_LOW, COLOR_LOW
    elif tini <= TINI_HIGH_THRESHOLD:
        return RISK_MODERATE, COLOR_MODERATE
    else:
        return RISK_HIGH, COLOR_HIGH


def create_float_regex(
    max_integer_digits: int, max_decimal_digits: int = 5
) -> str:
    """Генерирует регулярное выражение для чисел с плавающей точкой."""
    int_part = f"\\d{{1,{max_integer_digits}}}"
    dec_part = f"\\.\\d{{1,{max_decimal_digits}}}"
    return f"^({int_part}{dec_part}?|{dec_part})$"


def setup_logger(debug: bool = False):
    """Настраивает логирование в файл по дате."""
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    log_file = logs_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8")],
    )
    logging.info("Запуск TINI Calculator")


class TINICalculatorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(*WINDOW_SIZE)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        self.fields = {}

        # === Заголовок ===
        title_label = QLabel(APP_NAME)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont(FONT_FAMILY, FONT_SIZE_TITLE, QFont.Bold))
        layout.addWidget(title_label)

        # === Блок 1: Данные пациента ===
        patient_group = QGroupBox("Данные пациента")
        patient_group.setAlignment(Qt.AlignCenter)
        patient_layout = QVBoxLayout()

        # --- ФИО ---
        for label_text, key in [SURNAME_DESC, NAME_DESC, PATRONYMIC_DESC]:
            row = QHBoxLayout()
            label = QLabel(label_text)
            line_edit = QLineEdit()
            line_edit.setMaxLength(MAX_NAME_LEN)
            line_edit.setPlaceholderText(FULL_NAME_PLACEHOLDER)
            pattern = FULL_NAME_PATTERN
            validator = QRegularExpressionValidator(
                QRegularExpression(pattern)
            )
            line_edit.setValidator(validator)
            line_edit.textChanged.connect(self.on_input_changed)
            row.addWidget(label, 1)
            row.addWidget(line_edit, 2)
            patient_layout.addLayout(row)
            self.fields[key] = line_edit

        # --- Пол ---
        gender_layout = QHBoxLayout()
        gender_label = QLabel(GENDER)
        self.radio_not_specified = QRadioButton(UNKNOWN_STATUS)
        self.radio_male = QRadioButton(GENDER_MALE)
        self.radio_female = QRadioButton(GENDER_FEMALE)
        self.gender_group = QButtonGroup()
        for radio in [
            self.radio_not_specified,
            self.radio_male,
            self.radio_female,
        ]:
            self.gender_group.addButton(radio)
        self.radio_not_specified.setChecked(True)
        self.gender_group.buttonToggled.connect(self.on_input_changed)
        gender_layout.addWidget(gender_label, 1)
        gender_layout.addWidget(self.radio_not_specified)
        gender_layout.addWidget(self.radio_male)
        gender_layout.addWidget(self.radio_female)
        patient_layout.addLayout(gender_layout)

        # --- Дата рождения ---
        dob_layout = QHBoxLayout()
        dob_label = QLabel(BIRTH_DATE)
        self.dob_unknown = QCheckBox(UNKNOWN_STATUS)
        self.dob_unknown.setChecked(True)
        self.dob_edit = QDateEdit()
        self.dob_edit.setCalendarPopup(True)
        self.dob_edit.setDisplayFormat(DATE_FORMAT)
        self.dob_edit.setDateRange(MIN_DATE, MAX_DATE)
        self.dob_edit.setDate(DEFAULT_DATE_BORN)
        self.dob_edit.setEnabled(False)
        self.dob_unknown.toggled.connect(
            partial(self.toggle_date_input, self.dob_edit)
        )
        self.dob_edit.dateChanged.connect(self.on_input_changed)
        dob_layout.addWidget(dob_label, 1)
        dob_layout.addWidget(self.dob_unknown)
        dob_layout.addWidget(self.dob_edit, 2)
        patient_layout.addLayout(dob_layout)
        self.fields["date_birth"] = self.dob_edit
        self.fields["dob_unknown"] = self.dob_unknown

        # --- Возраст ---
        age_layout = QHBoxLayout()
        age_label = QLabel(AGE)
        self.age_display = QLineEdit()
        self.age_display.setReadOnly(True)
        self.age_display.setPlaceholderText("—")
        age_layout.addWidget(age_label, 1)
        age_layout.addWidget(self.age_display, 2)
        patient_layout.addLayout(age_layout)

        patient_group.setLayout(patient_layout)
        layout.addWidget(patient_group)

        # === Блок 2: Данные исследования ===
        study_group = QGroupBox("Данные исследования")
        study_group.setAlignment(Qt.AlignCenter)
        study_layout = QVBoxLayout()

        # --- Дата исследования ---
        study_date_layout = QHBoxLayout()
        study_date_label = QLabel(RESEARCH_DATE)
        self.study_date_unknown = QCheckBox(UNKNOWN_STATUS)
        self.study_date_unknown.setChecked(True)
        self.study_date_edit = QDateEdit()
        self.study_date_edit.setCalendarPopup(True)
        self.study_date_edit.setDisplayFormat(DATE_FORMAT)
        self.study_date_edit.setDateRange(MIN_DATE, MAX_DATE)
        self.study_date_edit.setDate(DEFAULT_DATE_RESEARCH)
        self.study_date_edit.setEnabled(False)
        self.study_date_unknown.toggled.connect(
            partial(self.toggle_date_input, self.study_date_edit)
        )
        self.study_date_edit.dateChanged.connect(self.on_input_changed)
        study_date_layout.addWidget(study_date_label, 1)
        study_date_layout.addWidget(self.study_date_unknown)
        study_date_layout.addWidget(self.study_date_edit, 2)
        study_layout.addLayout(study_date_layout)
        self.fields["study_date"] = self.study_date_edit
        self.fields["study_date_unknown"] = self.study_date_unknown

        # --- Параметры ---
        for desc in [
            D_DIMER_DESC,
            INTERLEUKINS_DESC,
            LYMPHOCYTES_DESC,
            CT_PERCENT_DESC,
        ]:
            row = QHBoxLayout()
            label = QLabel(desc[0])
            line_edit = QLineEdit()
            line_edit.setPlaceholderText(desc[2])
            key = desc[1]
            if key in ("d_dimer", "interleukins"):
                regex = create_float_regex(5, DECIMAL_PLACES)
                line_edit.setValidator(
                    QRegularExpressionValidator(QRegularExpression(regex))
                )
            elif key == "lymphocytes":
                regex = create_float_regex(2, DECIMAL_PLACES)
                line_edit.setValidator(
                    QRegularExpressionValidator(QRegularExpression(regex))
                )
            elif key == "ct_percent":
                line_edit.setValidator(
                    QIntValidator(MIN_CT_PERCENT, MAX_CT_PERCENT)
                )
            line_edit.textChanged.connect(self.on_input_changed)
            row.addWidget(label, 1)
            row.addWidget(line_edit, 2)
            study_layout.addLayout(row)
            self.fields[key] = line_edit

        study_group.setLayout(study_layout)
        layout.addWidget(study_group)

        # === Блок 3: Результат TINI ===
        result_group = QGroupBox("Результат TINI")
        result_group.setAlignment(Qt.AlignCenter)
        result_layout = QVBoxLayout()

        self.instruction_label = QLabel(INSTRUCTION_DEFAULT)
        self.instruction_label.setFont(
            QFont(FONT_FAMILY, FONT_SIZE_RESULT_MESSAGE)
        )
        self.instruction_label.setAlignment(Qt.AlignCenter)
        self.instruction_label.setWordWrap(True)
        result_layout.addWidget(self.instruction_label)

        self.result_value = QLabel("")
        self.result_value.setFont(QFont(FONT_FAMILY, FONT_SIZE_RESULT_VALUE))
        self.result_value.setAlignment(Qt.AlignCenter)
        self.result_value.setWordWrap(True)
        self.result_value.hide()
        result_layout.addWidget(self.result_value)

        self.risk_label = QLabel("")
        self.risk_label.setFont(QFont(FONT_FAMILY, FONT_SIZE_RESULT_MESSAGE))
        self.risk_label.setAlignment(Qt.AlignCenter)
        self.risk_label.setWordWrap(True)
        self.risk_label.hide()
        result_layout.addWidget(self.risk_label)

        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

        # === Кнопки ===
        btn_row1 = QHBoxLayout()
        self.calculate_btn = QPushButton(BUTTON_CALCULATE)
        self.reset_btn = QPushButton(BUTTON_RESET)
        self.calculate_btn.clicked.connect(self.on_calculate)
        self.reset_btn.clicked.connect(self.reset_form)
        btn_row1.addWidget(self.calculate_btn)
        btn_row1.addWidget(self.reset_btn)

        btn_row2 = QHBoxLayout()
        self.copy_btn = QPushButton(BUTTON_COPY)
        self.pdf_btn = QPushButton(BUTTON_SAVE_PDF)
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        self.pdf_btn.clicked.connect(self.save_to_pdf)
        btn_row2.addWidget(self.copy_btn)
        btn_row2.addWidget(self.pdf_btn)

        result_layout.addLayout(btn_row1)
        result_layout.addLayout(btn_row2)

        # Инициализация состояния кнопок
        self.calculate_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)
        self.copy_btn.setEnabled(False)
        self.pdf_btn.setEnabled(False)

        self.on_input_changed()  # инициализация состояния

    def get_float(self, key: str, default: float = 0.0) -> float:
        """
        Безопасно преобразует текст из поля ввода в число с плавающей точкой.
        Заменяет запятые на точки (для удобства ввода в русскоязычной среде)
        и возвращает значение по умолчанию при некорректном или пустом вводе.
        """
        text = self.fields[key].text().strip().replace(",", ".")
        if not text:
            return default
        try:
            return float(text)
        except ValueError:
            return default

    def toggle_date_input(self, date_edit: QDateEdit, checked: bool):
        """
        Переключает доступность виджета даты
        в зависимости от состояния чекбокса.
        """
        date_edit.setEnabled(not checked)
        self.on_input_changed()

    def calculate_age(self, birth: QDate, study: QDate) -> int:
        """Рассчитывает возраст."""
        if not birth.isValid() or not study.isValid():
            return 0
        years = study.year() - birth.year()
        if (study.month(), study.day()) < (birth.month(), birth.day()):
            years -= 1
        return max(0, years)

    def is_ct_valid(self) -> bool:
        """Проверяет, что КТ — целое число от 0 до 100."""
        text = self.fields["ct_percent"].text().strip()
        if not text:
            return True
        try:
            value = float(text.replace(",", "."))
            return (
                MIN_CT_PERCENT <= value <= MAX_CT_PERCENT
                and value.is_integer()
            )
        except ValueError:
            return False

    def on_input_changed(self):
        """
        Обрабатывает изменение любого поля ввода.
        Обновляет отображаемый возраст (если указаны обе даты) и проверяет,
        заполнены ли все обязательные лабораторные параметры.
        Управляет видимостью инструкции и
        активностью кнопки 'Выполнить расчёт'.
        """
        # Обновление возраста
        if (
            not self.fields["dob_unknown"].isChecked()
            and not self.fields["study_date_unknown"].isChecked()
        ):
            age = self.calculate_age(
                self.dob_edit.date(), self.study_date_edit.date()
            )
            self.age_display.setText(str(age))
        else:
            self.age_display.setText("—")

        # Проверка обязательных полей
        d_dimer = self.get_float("d_dimer")
        interleukins = self.get_float("interleukins")
        lymphocytes = self.get_float("lymphocytes")
        all_filled = d_dimer > 0 and interleukins > 0 and lymphocytes > 0

        self.instruction_label.setText(INSTRUCTION_DEFAULT)
        self.instruction_label.setVisible(not all_filled)

        # Только кнопка расчёта зависит от ввода
        self.calculate_btn.setEnabled(all_filled)

    def on_calculate(self):
        """Основная логика."""
        d_dimer = self.get_float("d_dimer")
        interleukins = self.get_float("interleukins")
        lymphocytes = self.get_float("lymphocytes")

        if not (d_dimer > 0 and interleukins > 0 and lymphocytes > 0):
            return

        # Проверка КТ
        if not self.is_ct_valid():
            self.show_error(ERROR_MESSAGE_CT)
            return

        # Расчёт
        tini = calculate_tini(d_dimer, interleukins, lymphocytes)
        risk, color = interpret_tini(tini)

        extra = (
            EXTRA_WARNING_CT_TINI
            if self.get_float("ct_percent") > 70 and tini > TINI_HIGH_THRESHOLD
            else ""
        )

        self.result_value.setText(f"{tini:,.0f}")
        self.result_value.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.risk_label.setText(risk + extra)
        self.risk_label.setStyleSheet(f"color: {color};")

        self.result_value.show()
        self.risk_label.show()

        # === Формирование отчёта ===
        surname = self.fields["surname"].text().strip()
        name = self.fields["name"].text().strip()
        patronymic = self.fields["patronymic"].text().strip()
        full_name = (
            UNKNOWN_STATUS
            if not (surname or name or patronymic)
            else " ".join(filter(None, [surname, name, patronymic])).title()
        )

        gender = UNKNOWN_STATUS
        if self.radio_male.isChecked():
            gender = GENDER_MALE
        elif self.radio_female.isChecked():
            gender = GENDER_FEMALE

        dob_str = (
            UNKNOWN_STATUS
            if self.fields["dob_unknown"].isChecked()
            else self.dob_edit.date().toString(DATE_FORMAT)
        )
        study_str = (
            UNKNOWN_STATUS
            if self.fields["study_date_unknown"].isChecked()
            else self.study_date_edit.date().toString(DATE_FORMAT)
        )
        age_str = (
            UNKNOWN_STATUS
            if self.fields["dob_unknown"].isChecked()
            or self.fields["study_date_unknown"].isChecked()
            else f"{self.calculate_age(self.dob_edit.date(), self.study_date_edit.date())} лет"
        )

        # Обработка КТ: либо число, либо "Не указано"
        ct_text = self.fields["ct_percent"].text().strip()
        ct_str = (
            UNKNOWN_STATUS
            if not ct_text
            else f"{int(float(ct_text.replace(',', '.')))} %"
        )

        self.full_report = (
            f"Пациент: {full_name}\n"
            f"{GENDER}: {gender}\n"
            f"{BIRTH_DATE}: {dob_str}\n"
            f"{AGE}: {age_str}\n"
            f"{RESEARCH_DATE}: {study_str}\n\n"
            f"{D_DIMER_DESC[0].replace(' *', '')}: {d_dimer} нг/мл\n"
            f"{INTERLEUKINS_DESC[0].replace(' *', '')}: {interleukins} пг/мл\n"
            f"{LYMPHOCYTES_DESC[0].replace(' *', '')}: {lymphocytes} ×10⁹/л\n"
            f"{CT_PERCENT_DESC[0]}: {ct_str}\n"
            f"TINI-индекс: {tini:,.0f}\n"
            f"Интерпретация: {risk}{extra}\n"
        )

        # Активация кнопок
        for btn in [self.reset_btn, self.copy_btn, self.pdf_btn]:
            btn.setEnabled(True)

    def show_error(self, msg: str):
        """
        Отображает сообщение об ошибке в области инструкции и
        скрывает результаты расчёта.
        Отключает кнопки экспорта, чтобы
        предотвратить сохранение некорректных данных.
        """
        self.instruction_label.setText(msg)
        self.instruction_label.show()
        self.result_value.hide()
        self.risk_label.hide()
        self.copy_btn.setEnabled(False)
        self.pdf_btn.setEnabled(False)

    def reset_form(self):
        """
        Сбрасывает все поля формы к начальному состоянию.
        Очищает текстовые поля, сбрасывает радиокнопки и чекбоксы,
        скрывает результаты расчёта, восстанавливает инструкцию и
        деактивирует все кнопки, кроме 'Выполнить расчёт' (которая
        будет обновлена через вызов on_input_changed).
        """
        for key in ("surname", "name", "patronymic"):
            self.fields[key].clear()
        self.radio_not_specified.setChecked(True)
        self.dob_unknown.setChecked(True)
        self.study_date_unknown.setChecked(True)
        self.age_display.setText("—")
        for key in ("d_dimer", "interleukins", "lymphocytes", "ct_percent"):
            self.fields[key].clear()
        self.result_value.hide()
        self.risk_label.hide()
        self.instruction_label.setText(INSTRUCTION_DEFAULT)
        self.instruction_label.show()
        for btn in [self.reset_btn, self.copy_btn, self.pdf_btn]:
            btn.setEnabled(False)
        self.on_input_changed()

    def copy_to_clipboard(self):
        """Копирование в буфер обмена."""
        QApplication.clipboard().setText(self.full_report)
        QMessageBox.information(
            self, "Копирование", "Отчёт скопирован в буфер обмена."
        )

    def save_to_pdf(self):
        """Сохранение в pdf."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить отчёт в PDF",
            "",
            "PDF Files (*.pdf)",
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"

        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(path)

        doc = QTextDocument()
        html = (
            "<h2>Отчёт: TINI Calculator</h2>"
            "<pre style='font-family: Consolas, monospace; font-size: 12pt;'>"
            + self.full_report.replace("\n", "<br>")
            + "</pre>"
        )
        doc.setHtml(html)
        doc.print_(printer)

        QMessageBox.information(self, "Успешно", f"Отчёт сохранён:\n{path}")


def main():
    load_dotenv()
    debug_mode = os.getenv("DEBUG", "False").lower() == "true"
    if debug_mode:
        print("Программа запущена в режиме отладки")

    setup_logger(debug_mode)
    app = QApplication(sys.argv)
    app.setFont(QFont(FONT_FAMILY, FONT_SIZE_BASE))
    window = TINICalculatorApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
