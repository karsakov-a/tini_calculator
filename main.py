import locale
import os
import sys

from dotenv import load_dotenv
from PySide6.QtCore import QDate, QRegularExpression, Qt
from PySide6.QtGui import (
    QDoubleValidator,
    QFont,
    QIntValidator,
    QRegularExpressionValidator,
    QTextDocument,
    QIcon,
    QValidator,
)
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
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
    QCheckBox,
    QVBoxLayout,
    QWidget,
)

import resources_rc
from calculator import calculate_citi, interpret_citi

load_dotenv()

DEBUG = os.getenv("DEBUG", "False").lower() == "true"

if DEBUG:
    print("Программа запущена в режиме отладки")


SIZE_MAIN_WINDOW = (440, 400)

# Сообщения
EXTRA_WARNING_CT_CITI = (
    "\n⚠️ При CITI более 500 000 и КТ более 70%\nриск смерти превышает 95%"
)


# Шрифты
FONT = "Segoe UI"
FONT_SIZE = 10
FONT_SIZE_TITLE = 14
FONT_SIZE_RESULT_CITI = 16
FONT_SIZE_RESULT_MESSAGE = 12

# Валидация данных в полях ввода
MIN_NAME_SURNAME_PATRONYMIC_LENGTH = 2
MAX_NAME_SURNAME_PATRONYMIC_LENGTH = 20
MIN_DDIMER_INTERLEUKINS = 0.0
MAX_DDIMER_INTERLEUKINS = 5000.0
MIN_LYMPHOCYTES = 0.0
MAX_LYMPHOCYTES = 10.0
DECIMAL_PLACES = 5

MIN_CT_PERCENT = 0
MAX_CT_PERCENT = 100

MIN_ALLOWED_DATE = QDate(1920, 1, 1)
MAX_ALLOWED_DATE = QDate.currentDate()
SET_DATE_BORN = QDate(1985, 1, 1)
SET_DATE_RESEARCH = QDate.currentDate()

# Описание полей ввода: (метка, внутренний ключ, placeholder)
SURNAME_DESCRIPTION = (
    "Фамилия",
    "surname",
)
NAME_DESCRIPTION = (
    "Имя",
    "name",
)
PATRONYMIC_DESCRIPTION = (
    "Отчество",
    "patronymic",
)
D_DIMER_DESCRIPTION = (
    "D-димер (нг/мл) *",
    "d_dimer",
    f"{MIN_DDIMER_INTERLEUKINS}–{MAX_DDIMER_INTERLEUKINS}",
)
INTERLEUKINS_DESCRIPTION = (
    "Интерлейкины, IL–6 (пг/мл) *",
    "interleukins",
    f"{MIN_DDIMER_INTERLEUKINS}–{MAX_DDIMER_INTERLEUKINS}",
)
LYMPHOCYTES_DESCRIPTION = (
    "Лимфоциты (×10⁹/л) *",
    "lymphocytes",
    f"от {MIN_LYMPHOCYTES} до {MAX_LYMPHOCYTES}",
)

CT_PERCENT_DESCRIPTION = (
    "Объем поражения лёгких \nпо данным МСКТ (%)",
    "ct_percent",
    f"от {MIN_CT_PERCENT} до {MAX_CT_PERCENT}",
)


def create_float_regex(
    max_integer_digits: int, max_decimal_digits: int = 5
) -> str:
    """
    Генерирует регулярное выражение для чисел с плавающей точкой.
    Пример:
        max_integer_digits=5, max_decimal_digits=5 → до 99999.99999
        Допускает: '0', '123', '123.45', '.5' → интерпретируется как 0.5
    """
    int_part = f"\\d{{1,{max_integer_digits}}}"  # 1–5 цифр
    dec_part = f"\\.\\d{{1,{max_decimal_digits}}}"  # .1–.99999
    # Варианты: целое число | число с дробной частью | только дробная часть
    pattern = f"^({int_part}{dec_part}?|{dec_part})$"
    return pattern


class CITICalculatorApp(QMainWindow):
    """
    Основной класс приложения — наследуется от QMainWindow.
    В нём создаётся весь интерфейс и логика взаимодействия.
    """

    def __init__(self):
        # Вызываем конструктор родительского класса (обязательно!)
        super().__init__()

        # Устанавливаем заголовок окна
        self.setWindowTitle(
            "CITI Calculator — Индекс воспалительно-коагуляционного риска"
        )
        # Устанавливаем начальный размер окна (ширина=400, высота=400 пикселей)
        self.resize(SIZE_MAIN_WINDOW[0], SIZE_MAIN_WINDOW[1])

        if DEBUG:
            self.move(550, 100)

        # Создаём центральный виджет — в Qt главное окно не может напрямую содержать другие виджеты,
        # поэтому нужно установить один центральный виджет, внутри которого будет весь интерфейс.
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Создаём вертикальный макет (VBox): виджеты будут располагаться сверху вниз
        layout = QVBoxLayout(central_widget)

        # Словарь для хранения ссылок на поля ввода (чтобы к ним можно было обращаться позже)
        self.fields = {}

        # Устанавливаем иконку приложения
        icon_path = self.get_icon_path()
        if icon_path and os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # === Заголовок ===
        title_label = QLabel("CITI Calculator")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont(FONT, FONT_SIZE_TITLE, QFont.Bold))
        layout.addWidget(title_label)

        # === Блок 1: Данные пациента ===
        patient_group = QGroupBox("Данные пациента")
        patient_group.setAlignment(Qt.AlignCenter)
        patient_layout = QVBoxLayout()

        # --- ФИО ---
        name_fields = [
            SURNAME_DESCRIPTION,
            NAME_DESCRIPTION,
            PATRONYMIC_DESCRIPTION,
        ]
        for label_text, key in name_fields:
            row = QHBoxLayout()
            label = QLabel(label_text)
            line_edit = QLineEdit()
            line_edit.setMaxLength(MAX_NAME_SURNAME_PATRONYMIC_LENGTH)
            line_edit.setPlaceholderText(
                f"Только буквы, {MIN_NAME_SURNAME_PATRONYMIC_LENGTH}–"
                f"{MAX_NAME_SURNAME_PATRONYMIC_LENGTH} символов"
            )
            pattern = (
                f"^[а-яА-ЯёЁa-zA-Z]{{{MIN_NAME_SURNAME_PATRONYMIC_LENGTH},"
                f"{MAX_NAME_SURNAME_PATRONYMIC_LENGTH}}}$"
            )
            name_regex = QRegularExpression(pattern)
            line_edit.setValidator(QRegularExpressionValidator(name_regex))
            line_edit.textChanged.connect(self.on_input_changed)
            row.addWidget(label, 1)
            row.addWidget(line_edit, 2)
            patient_layout.addLayout(row)
            self.fields[key] = line_edit

        # --- Пол ---
        gender_layout = QHBoxLayout()
        gender_label = QLabel("Пол")
        self.not_specified_radio = QRadioButton("Не указано")
        self.male_radio = QRadioButton("Мужской")
        self.female_radio = QRadioButton("Женский")

        # Группа для взаимоисключающего выбора
        self.gender_group = QButtonGroup()
        self.gender_group.addButton(self.not_specified_radio)
        self.gender_group.addButton(self.male_radio)
        self.gender_group.addButton(self.female_radio)

        self.not_specified_radio.setChecked(True)

        self.gender_group.buttonToggled.connect(self.on_input_changed)

        gender_layout.addWidget(gender_label, 1)
        gender_layout.addWidget(self.not_specified_radio)
        gender_layout.addWidget(self.male_radio)
        gender_layout.addWidget(self.female_radio)
        patient_layout.addLayout(gender_layout)

        # --- Дата рождения с опцией "неизвестна" ---
        dob_layout = QHBoxLayout()
        dob_label = QLabel("Дата рождения")
        self.dob_unknown_checkbox = QCheckBox("Не указано")
        self.dob_unknown_checkbox.setChecked(True)  # по умолчанию включено
        self.dob_edit = QDateEdit()
        self.dob_edit.setCalendarPopup(True)
        self.dob_edit.setDisplayFormat("dd.MM.yyyy")
        self.dob_edit.setDateRange(MIN_ALLOWED_DATE, MAX_ALLOWED_DATE)
        self.dob_edit.setDate(SET_DATE_BORN)
        self.dob_edit.setEnabled(False)  # заблокировано по умолчанию
        self.dob_unknown_checkbox.toggled.connect(self.toggle_dob_input)
        self.dob_edit.dateChanged.connect(self.on_input_changed)
        dob_layout.addWidget(dob_label, 1)
        dob_layout.addWidget(self.dob_unknown_checkbox)
        dob_layout.addWidget(self.dob_edit, 2)
        patient_layout.addLayout(dob_layout)
        self.fields["date_birth"] = self.dob_edit
        self.fields["dob_unknown"] = (
            self.dob_unknown_checkbox
        )  # <-- новая ссылка

        # --- Возраст на момент исследования (только для отображения) ---
        age_layout = QHBoxLayout()
        age_label = QLabel("Возраст на момент исследования")
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

        # --- Дата исследования с опцией "неизвестна" ---
        study_date_layout = QHBoxLayout()
        study_date_label = QLabel("Дата исследования")
        self.study_date_unknown_checkbox = QCheckBox("Не указано")
        self.study_date_unknown_checkbox.setChecked(
            True
        )  # по умолчанию включено
        self.study_date_edit = QDateEdit()
        self.study_date_edit.setCalendarPopup(True)
        self.study_date_edit.setDisplayFormat("dd.MM.yyyy")
        self.study_date_edit.setDateRange(MIN_ALLOWED_DATE, MAX_ALLOWED_DATE)
        self.study_date_edit.setDate(SET_DATE_RESEARCH)
        self.study_date_edit.setEnabled(False)  # заблокировано по умолчанию
        self.study_date_unknown_checkbox.toggled.connect(
            self.toggle_study_date_input
        )
        self.study_date_edit.dateChanged.connect(self.on_input_changed)
        study_date_layout.addWidget(study_date_label, 1)
        study_date_layout.addWidget(self.study_date_unknown_checkbox)
        study_date_layout.addWidget(self.study_date_edit, 2)
        study_layout.addLayout(study_date_layout)
        self.fields["study_date"] = self.study_date_edit
        self.fields["study_date_unknown"] = (
            self.study_date_unknown_checkbox
        )  # <-- новая ссылка

        # --- Лабораторные параметры ---
        lab_inputs = [
            D_DIMER_DESCRIPTION,
            INTERLEUKINS_DESCRIPTION,
            LYMPHOCYTES_DESCRIPTION,
            CT_PERCENT_DESCRIPTION,
        ]
        for label_text, key, placeholder in lab_inputs:
            row = QHBoxLayout()
            label = QLabel(label_text)
            line_edit = QLineEdit()
            line_edit.setPlaceholderText(placeholder)
            if key in ("d_dimer", "interleukins"):
                regex = create_float_regex(
                    max_integer_digits=5, max_decimal_digits=DECIMAL_PLACES
                )
                line_edit.setValidator(
                    QRegularExpressionValidator(QRegularExpression(regex))
                )
            elif key == "lymphocytes":
                regex = create_float_regex(
                    max_integer_digits=2, max_decimal_digits=DECIMAL_PLACES
                )
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

        # === Блок 3: Результат CITI ===
        result_group = QGroupBox("Результат CITI")
        result_group.setAlignment(Qt.AlignCenter)
        result_layout = QVBoxLayout()

        # Надпись-заглушка (всегда видна)
        self.instruction_label = QLabel("Введите все обязательные поля (*)")
        self.instruction_label.setFont(QFont(FONT, FONT_SIZE_RESULT_MESSAGE))
        self.instruction_label.setAlignment(Qt.AlignCenter)
        self.instruction_label.setWordWrap(True)
        result_layout.addWidget(self.instruction_label)

        # Метка для CITI-значения (изначально скрыта)
        self.result_value = QLabel("")
        self.result_value.setFont(QFont(FONT, FONT_SIZE_RESULT_CITI))
        self.result_value.setAlignment(Qt.AlignCenter)
        self.result_value.setWordWrap(True)
        self.result_value.hide()
        result_layout.addWidget(self.result_value)

        # Метка для интерпретации риска (изначально скрыта)
        self.risk_label = QLabel("")
        self.risk_label.setFont(QFont(FONT, FONT_SIZE_RESULT_MESSAGE))
        self.risk_label.setAlignment(Qt.AlignCenter)
        self.risk_label.setWordWrap(True)
        self.risk_label.hide()
        result_layout.addWidget(self.risk_label)

        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

        # === Кнопки в два ряда ===
        # Ряд 1: Выполнить и Сбросить
        row1_layout = QHBoxLayout()
        self.calculate_btn = QPushButton("ВЫПОЛНИТЬ РАСЧЁТ")
        self.reset_btn = QPushButton("Сбросить")
        self.calculate_btn.clicked.connect(self.on_calculate)
        self.reset_btn.clicked.connect(self.reset_form)
        self.calculate_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)
        row1_layout.addWidget(self.calculate_btn)
        row1_layout.addWidget(self.reset_btn)

        # Ряд 2: Скопировать и Сохранить
        row2_layout = QHBoxLayout()
        self.copy_btn = QPushButton("Скопировать отчёт")
        self.pdf_btn = QPushButton("Сохранить в PDF")
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        self.pdf_btn.clicked.connect(self.save_to_pdf)
        self.copy_btn.setEnabled(False)
        self.pdf_btn.setEnabled(False)
        row2_layout.addWidget(self.copy_btn)
        row2_layout.addWidget(self.pdf_btn)

        # Добавляем оба ряда в макет результата
        result_layout.addLayout(row1_layout)
        result_layout.addLayout(row2_layout)

    def get_float(self, key: str, default: float = 0.0) -> float:
        """
        Безопасно извлекает число из текстового поля.
        Заменяет запятую на точку (для удобства ввода в РФ),
        возвращает default, если ввод некорректен или пуст.
        """
        text = self.fields[key].text().strip().replace(",", ".")
        if not text:
            return default
        try:
            return float(text)
        except ValueError:
            return default

    def toggle_dob_input(self, checked: bool):
        """Блокирует/разблокирует поле даты рождения."""
        self.dob_edit.setEnabled(not checked)
        self.on_input_changed()

    def toggle_study_date_input(self, checked: bool):
        """Блокирует/разблокирует поле даты исследования."""
        self.study_date_edit.setEnabled(not checked)
        self.on_input_changed()

    def on_input_changed(self):
        """Обновляет возраст и надпись о заполнении обязательных полей."""
        # Обновляем возраст
        dob_unknown = self.fields["dob_unknown"].isChecked()
        study_date_unknown = self.fields["study_date_unknown"].isChecked()
        if not dob_unknown and not study_date_unknown:
            age = self.calculate_age(
                self.dob_edit.date(), self.study_date_edit.date()
            )
            self.age_display.setText(str(age))
        else:
            self.age_display.setText("—")

        # Проверяем обязательные поля
        d_dimer = self.get_float("d_dimer")
        interleukins = self.get_float("interleukins")
        lymphocytes = self.get_float("lymphocytes")
        all_filled = d_dimer > 0 and interleukins > 0 and lymphocytes > 0

        # Управление надписью
        if all_filled:
            # Восстанавливаем стандартную инструкцию
            self.instruction_label.setText("Введите все обязательные поля (*)")
            self.instruction_label.hide()
        else:
            self.instruction_label.setText("Введите все обязательные поля (*)")
            self.instruction_label.show()

        # Активность кнопок
        self.calculate_btn.setEnabled(all_filled)

    def calculate_age(self, birth_date: QDate, study_date: QDate) -> int:
        """
        Рассчитывает возраст в годах на дату исследования.
        Учитывает, был ли уже день рождения в этом году.
        """
        if not birth_date.isValid() or not study_date.isValid():
            return 0
        years = study_date.year() - birth_date.year()
        # Если день рождения ещё не наступил в год исследования — минус 1 год
        if (study_date.month(), study_date.day()) < (
            birth_date.month(),
            birth_date.day(),
        ):
            years -= 1
        return max(0, years)

    def is_field_valid(self, key: str) -> bool:
        """Проверяет, является ли содержимое поля допустимым."""
        widget = self.fields[key]
        if isinstance(widget, QLineEdit):
            text = widget.text()
            if not text:
                return False
            # Проверяем через валидатор
            validator = widget.validator()
            if validator:
                state, _, _ = validator.validate(text, 0)
                return state == QValidator.State.Acceptable
            return True
        return True

    def on_calculate(self):
        """Выполняет расчёт и показывает результат."""
        # Проверка данных
        d_dimer = self.get_float("d_dimer")
        interleukins = self.get_float("interleukins")
        lymphocytes = self.get_float("lymphocytes")

        if d_dimer <= 0 or interleukins <= 0 or lymphocytes <= 0:
            return  # Кнопка не должна быть активна, но на всякий случай

        # Валидация дат
        dob_unknown = self.fields["dob_unknown"].isChecked()
        study_date_unknown = self.fields["study_date_unknown"].isChecked()

        if not dob_unknown and not study_date_unknown:
            birth_date = self.dob_edit.date()
            study_date = self.study_date_edit.date()

            if not birth_date.isValid() or not study_date.isValid():
                self.show_error("Некорректные даты")
                return

            if birth_date > study_date:
                self.show_error(
                    "Дата рождения не может быть позже даты исследования"
                )
                return

            if study_date > QDate.currentDate():
                self.show_error("Дата исследования не может быть в будущем")
                return

        # Проверяем КТ: если поле не пустое, оно должно быть <= 100
        ct_text = self.fields["ct_percent"].text().strip()
        if ct_text:
            if not self.is_field_valid("ct_percent"):
                self.show_error(
                    "Объем поражения лёгких должен быть от 0 до 100"
                )
                return

        # Расчёт
        citi = calculate_citi(d_dimer, interleukins, lymphocytes)
        risk_level, color = interpret_citi(citi)

        # Доп. предупреждение
        extra_warning = ""
        ct = self.get_float("ct_percent")
        if ct > 70 and citi > 500_000:
            extra_warning = EXTRA_WARNING_CT_CITI

        # Обновление интерфейса
        self.result_value.setText(f"{citi:,.0f}")
        self.result_value.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.risk_label.setText(risk_level + extra_warning)
        self.risk_label.setStyleSheet(f"color: {color};")

        # Показываем результат
        self.result_value.show()
        self.risk_label.show()

        # Активируем кнопки экспорта
        self.copy_btn.setEnabled(True)
        self.pdf_btn.setEnabled(True)

        # Активируем ВСЕ кнопки после успешного расчёта
        self.calculate_btn.setEnabled(
            True
        )  # можно пересчитать при изменении данных
        self.reset_btn.setEnabled(True)
        self.copy_btn.setEnabled(True)
        self.pdf_btn.setEnabled(True)

        # === Формирование отчёта ===
        surname = self.fields["surname"].text().strip()
        name = self.fields["name"].text().strip()
        patronymic = self.fields["patronymic"].text().strip()

        # Правило для ФИО: если все пустые — "Не указано", иначе объединяем
        if surname == "" and name == "" and patronymic == "":
            full_name = "Не указано"
        else:
            parts = [surname, name, patronymic]
            full_name = " ".join(
                part for part in parts if part
            )  # убираем лишние пробелы
            full_name = full_name.title()

        if self.not_specified_radio.isChecked():
            gender = "Не указано"
        elif self.male_radio.isChecked():
            gender = "Мужской"
        else:
            gender = "Женский"

        dob_unknown = self.fields["dob_unknown"].isChecked()
        study_date_unknown = self.fields["study_date_unknown"].isChecked()

        dob_str = (
            "Не указано"
            if dob_unknown
            else self.dob_edit.date().toString("dd.MM.yyyy")
        )
        study_date_str = (
            "Не указано"
            if study_date_unknown
            else self.study_date_edit.date().toString("dd.MM.yyyy")
        )
        if dob_unknown or study_date_unknown:
            age_str = "Не указано"
        else:
            age = self.calculate_age(
                self.dob_edit.date(), self.study_date_edit.date()
            )
            age_str = f"{age} лет"

        # Убираем символ '*' из описаний
        d_dimer_label = D_DIMER_DESCRIPTION[0].replace(" *", "")
        interleukins_label = INTERLEUKINS_DESCRIPTION[0].replace(" *", "")
        lymphocytes_label = LYMPHOCYTES_DESCRIPTION[0].replace(" *", "")

        self.full_report = (
            f"Пациент: {full_name.title()}\n"
            f"Пол: {gender}\n"
            f"Дата рождения: {dob_str}\n"
            f"Возраст на момент исследования: {age_str}\n"
            f"Дата исследования: {study_date_str}\n"
            f"\n"
            f"CITI-индекс: {citi:,.0f}\n"
            f"Интерпретация: {risk_level}{extra_warning}\n"
            f"{d_dimer_label}: {d_dimer} нг/мл\n"
            f"{interleukins_label}: {interleukins} пг/мл\n"
            f"{lymphocytes_label}: {lymphocytes} ×10⁹/л"
        )

    def show_error(self, message: str):
        """Показывает ошибку в стиле инструкции (как 'Введите все обязательные поля')."""
        self.instruction_label.setText(message)
        self.instruction_label.show()
        # Скрываем результаты расчёта
        self.result_value.hide()
        self.risk_label.hide()
        # Отключаем кнопки экспорта
        self.copy_btn.setEnabled(False)
        self.pdf_btn.setEnabled(False)

    def reset_form(self):
        """Сбрасывает всё к стартовому состоянию."""
        # Скрываем результаты
        self.result_value.hide()
        self.risk_label.hide()

        # Сбрасываем кнопки
        self.calculate_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)
        self.copy_btn.setEnabled(False)
        self.pdf_btn.setEnabled(False)

        # Очищаем все поля
        for key in ("surname", "name", "patronymic"):
            self.fields[key].clear()

        self.not_specified_radio.setChecked(True)

        self.dob_unknown_checkbox.setChecked(True)
        self.study_date_unknown_checkbox.setChecked(True)
        self.age_display.setText("—")

        for key in ("d_dimer", "interleukins", "lymphocytes", "ct_percent"):
            self.fields[key].clear()

        # Восстанавливаем надпись
        self.instruction_label.setText("Введите все обязательные поля (*)")
        self.instruction_label.show()

        # Убираем full_report (чтобы не остался старый)
        if hasattr(self, "full_report"):
            delattr(self, "full_report")

        self.on_input_changed()

    def copy_to_clipboard(self):
        """
        Копирует полный отчёт в буфер обмена системы.
        """
        clipboard = QApplication.clipboard()  # Получаем доступ к буферу
        clipboard.setText(self.full_report)
        # Показываем всплывающее окно с подтверждением
        QMessageBox.information(
            self, "Копирование", "Отчёт скопирован в буфер обмена."
        )

    def save_to_pdf(self):
        """
        Сохраняет отчёт в PDF через Qt (без внешних библиотек).
        """
        # Проверка: есть ли что сохранять?
        if not hasattr(self, "full_report") or not self.full_report.strip():
            QMessageBox.warning(self, "Ошибка", "Нет данных для сохранения.")
            return

        # Открываем диалог выбора файла для сохранения
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить отчёт в PDF", "", "PDF Files (*.pdf)"
        )
        if not path:  # Пользователь нажал "Отмена"
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"

        # Настраиваем "принтер" для PDF
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(path)

        # ВАЖНО: Qt иногда ломает форматирование чисел из-за локали (особенно в РФ).
        # Устанавливаем локаль "C" (стандартную), чтобы точки/запятые не путались при рендеринге.
        try:
            locale.setlocale(locale.LC_NUMERIC, "C")
        except locale.Error:
            pass  # если не удалось — продолжаем

        # Создаём документ, который можно напечатать или сохранить
        doc = QTextDocument()
        # Форматируем отчёт как HTML (просто для структуры и шрифта)
        html = (
            "<h2>Отчёт: CITI Calculator</h2>"
            "<pre style='font-family: Consolas, monospace; font-size: 12pt;'>"
            + self.full_report.replace("\n", "<br>")
            + "</pre>"
        )
        doc.setHtml(html)
        doc.print_(printer)  # Сохраняет в PDF

        QMessageBox.information(self, "Успешно", f"Отчёт сохранён:\n{path}")

    def get_icon_path(self):
        """Возвращает путь к иконке, работает как в .py, так и в .exe."""
        if getattr(sys, "frozen", False):
            # Запуск из .exe — иконка встроена в ресурсы
            return ":/icon.ico"
        else:
            # Запуск из исходного кода
            return os.path.join(os.path.dirname(__file__), "icon.ico")


def main():
    # QApplication — обязательный объект, управляющий GUI и событиями
    app = QApplication(sys.argv)

    # Устанавливаем общий шрифт для всего приложения
    app.setFont(QFont(FONT, FONT_SIZE))

    # Создаём и показываем главное окно
    window = CITICalculatorApp()
    window.show()  # Отображает окно (по умолчанию оно скрыто)

    # Запускаем цикл обработки событий (ожидание действий пользователя)
    # sys.exit(...) гарантирует, что код завершится с правильным кодом ОС
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


"""
Логи должны сохраняться в папку logs/ с разбивкой по датам.
Каждый лог-файл — это простой текстовый файл с именем YYYY-MM-DD.log.
Код логирования вынести в if __name__ == "__main__":, чтобы не мешал при импорте.
дописать ридми
доработать валидацию - можно вводить разные числа которые валидатор не ловит
"""

"""
возможные фичи

Сохранение истории расчётов (локально, без облака)
Каждый расчёт сохраняется в ~/.ivc_calculator/history.json (или в AppData на Windows).
В интерфейсе — кнопка «История» → мини-таблица (дата, CITI, возраст, КТ %).
Можно копировать или экспортировать группу расчётов в PDF.

Валидация единиц измерения (с подсказками)
При фокусе на поле — показывать tooltip:
«Д-димер: в нг/мл (не мкг/мл!). Норма: <500 нг/мл»
Если введено значение >10 000 — показывать предупреждение: «Проверьте единицы измерения!»

Настройка пороговых значений (через конфиг или GUI)
Файл config.json с порогами:
json
1234
{
  "low_threshold": 100000,
  "high_threshold": 500000
}
Приложение загружает его при старте; если отсутствует — создаёт с дефолтами.
(Опционально) вкладка «Настройки» для редактирования без правки файлов.
"""
