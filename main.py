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

from calculator import calculate_ivc, interpret_ivc

load_dotenv()

DEBUG = os.getenv("DEBUG", "False").lower() == "true"

if DEBUG:
    print("Программа запущена в режиме отладки")


SIZE_MAIN_WINDOW = (440, 400)

# Сообщения
EXTRA_WARNING_CT_IVC = (
    "\n⚠️ При IVC более 500 000 и КТ более 70%\nриск смерти превышает 95%"
)


# Шрифты
FONT = "Segoe UI"
FONT_SIZE = 10
FONT_SIZE_TITLE = 14
FONT_SIZE_RESULT_IVC = 16
FONT_SIZE_RESULT_MESSAGE = 12

# Валидация данных в полях ввода
MIN_NAME_SURNAME_PATRONYMIC_LENGTH = 2
MAX_NAME_SURNAME_PATRONYMIC_LENGTH = 50
MIN_DDIMER_INTERLEUKINS = 0.0
MAX_DDIMER_INTERLEUKINS = 5000.0
MIN_LYMPHOCYTES = 0.0
MAX_LYMPHOCYTES = 10.0
DECIMAL_PLACES = 5

MIN_CT_PERCENT = 0
MAX_CT_PERCENT = 100

MIN_ALLOWED_DATE = QDate(1920, 1, 1)
MAX_ALLOWED_DATE = QDate.currentDate()

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


class IVCCalculatorApp(QMainWindow):
    """
    Основной класс приложения — наследуется от QMainWindow.
    В нём создаётся весь интерфейс и логика взаимодействия.
    """

    def __init__(self):
        # Вызываем конструктор родительского класса (обязательно!)
        super().__init__()

        # Устанавливаем заголовок окна
        self.setWindowTitle(
            "IVC Calculator — Индекс воспалительно-коагуляционного риска"
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

        # === Заголовок ===
        title_label = QLabel("IVC Calculator")
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
            line_edit.setPlaceholderText("Только буквы, 2–50 символов")
            name_regex = QRegularExpression(r"^[а-яА-ЯёЁa-zA-Z]{2,50}$")
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
        self.dob_unknown_checkbox = QCheckBox("Неизвестно")
        self.dob_unknown_checkbox.setChecked(True)  # по умолчанию включено
        self.dob_edit = QDateEdit()
        self.dob_edit.setCalendarPopup(True)
        self.dob_edit.setDisplayFormat("dd.MM.yyyy")
        self.dob_edit.setDateRange(MIN_ALLOWED_DATE, MAX_ALLOWED_DATE)
        self.dob_edit.setDate(MIN_ALLOWED_DATE)
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
        self.age_display.setPlaceholderText("Авто")
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
        self.study_date_unknown_checkbox = QCheckBox("Неизвестно")
        self.study_date_unknown_checkbox.setChecked(
            True
        )  # по умолчанию включено
        self.study_date_edit = QDateEdit()
        self.study_date_edit.setCalendarPopup(True)
        self.study_date_edit.setDisplayFormat("dd.MM.yyyy")
        self.study_date_edit.setDateRange(MIN_ALLOWED_DATE, MAX_ALLOWED_DATE)
        self.study_date_edit.setDate(MIN_ALLOWED_DATE)
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
                line_edit.setValidator(
                    QDoubleValidator(
                        MIN_DDIMER_INTERLEUKINS,
                        MAX_DDIMER_INTERLEUKINS,
                        DECIMAL_PLACES,
                    )
                )
            elif key == "lymphocytes":
                line_edit.setValidator(
                    QDoubleValidator(
                        MIN_LYMPHOCYTES, MAX_LYMPHOCYTES, DECIMAL_PLACES
                    )
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

        # === Блок 3: Результат IVC ===
        result_group = QGroupBox("Результат IVC")
        result_group.setAlignment(Qt.AlignCenter)
        result_layout = QVBoxLayout()

        self.result_value = QLabel("")
        self.result_value.setFont(QFont(FONT, FONT_SIZE_RESULT_IVC))
        self.result_value.setAlignment(Qt.AlignCenter)
        self.result_value.setWordWrap(True)
        result_layout.addWidget(self.result_value)

        self.risk_label = QLabel("")
        self.risk_label.setFont(QFont(FONT, FONT_SIZE_RESULT_MESSAGE))
        self.risk_label.setAlignment(Qt.AlignCenter)
        self.risk_label.setWordWrap(True)
        result_layout.addWidget(self.risk_label)

        button_layout = QHBoxLayout()
        self.copy_btn = QPushButton("Скопировать отчёт")
        self.pdf_btn = QPushButton("Сохранить в PDF")
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        self.pdf_btn.clicked.connect(self.save_to_pdf)
        button_layout.addWidget(self.copy_btn)
        button_layout.addWidget(self.pdf_btn)
        result_layout.addLayout(button_layout)

        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

        # Вызываем расчёт сразу при запуске
        self.on_input_changed()

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
        """
        Основной метод пересчёта.
        Вызывается при любом изменении любого поля ввода.
        """
        birth_date = self.dob_edit.date()
        study_date = self.study_date_edit.date()
        age = self.calculate_age(birth_date, study_date)
        self.age_display.setText(str(age))

        # --- Валидация ФИО ---
        for key in ("surname", "name", "patronymic"):
            text = self.fields[key].text().strip()
            if text and not self.fields[key].hasAcceptableInput():
                self.result_value.setText("ФИО: только буквы, 2–50 символов")
                self.risk_label.setText("")
                return

        # --- Получение лабораторных данных ---
        d_dimer = self.get_float("d_dimer")
        interleukins = self.get_float("interleukins")
        lymphocytes = self.get_float("lymphocytes")

        # --- Проверка обязательных полей ---
        if d_dimer == 0 or interleukins == 0 or lymphocytes == 0:
            self.result_value.setText("Введите все обязательные параметры (*)")
            self.risk_label.setText("")
            return

        # --- Расчёт IVC ---
        ivc = calculate_ivc(d_dimer, interleukins, lymphocytes)
        risk_level, color = interpret_ivc(ivc)

        # --- Дополнительное предупреждение по КТ ---
        extra_warning = ""
        ct = self.get_float("ct_percent")
        if ct > 70 and ivc > 500_000:
            extra_warning = EXTRA_WARNING_CT_IVC

        # --- Обновление интерфейса ---
        self.result_value.setText(f"{ivc:,.0f}")
        self.result_value.setStyleSheet(f"color: {color}; font-weight: bold;")

        risk_text = risk_level
        self.risk_label.setText(risk_text + extra_warning)
        self.risk_label.setStyleSheet(f"color: {color};")
        self.risk_label.setWordWrap(True)

        # --- Обработка дат ---
        dob_unknown = self.fields["dob_unknown"].isChecked()
        study_date_unknown = self.fields["study_date_unknown"].isChecked()

        birth_date = None
        study_date = None

        if dob_unknown or study_date_unknown:
            self.age_display.setText("—")
            age = None  # возраст не определён
        else:
            birth_date = self.dob_edit.date()
            study_date = self.study_date_edit.date()
            age = self.calculate_age(birth_date, study_date)
            self.age_display.setText(str(age))

        # --- Формирование полного отчёта ---
        surname = self.fields["surname"].text().strip()
        name = self.fields["name"].text().strip()
        patronymic = self.fields["patronymic"].text().strip()
        full_name = f"{surname} {name} {patronymic}".strip()

        # Пол
        if self.not_specified_radio.isChecked():
            gender = "Не указано"
        elif self.male_radio.isChecked():
            gender = "Мужской"
        else:
            gender = "Женский"

        # Дата рождения
        if dob_unknown:
            dob_str = "Неизвестно"
        else:
            dob_str = birth_date.toString("dd.MM.yyyy")

        # Дата исследования
        if study_date_unknown:
            study_date_str = "Неизвестно"
        else:
            study_date_str = study_date.toString("dd.MM.yyyy")

        # Возраст
        age_str = str(age) + " лет" if age is not None else "—"

        self.full_report = (
            f"Пациент: {full_name.title()}\n"
            f"Пол: {gender}\n"
            f"Дата рождения: {dob_str}\n"
            f"Возраст на момент исследования: {age_str}\n"
            f"Дата исследования: {study_date_str}\n"
            f"\n"
            f"IVC-индекс: {ivc:,.0f}\n"
            f"Интерпретация: {risk_text}{extra_warning}\n"
            f"{D_DIMER_DESCRIPTION[0]}: {d_dimer} нг/мл\n"
            f"{INTERLEUKINS_DESCRIPTION[0]}: {interleukins} пг/мл\n"
            f"{LYMPHOCYTES_DESCRIPTION[0]}: {lymphocytes} ×10⁹/л"
        )

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
            "<h2>Отчёт: IVC Calculator</h2>"
            "<pre style='font-family: Consolas, monospace; font-size: 12pt;'>"
            + self.full_report.replace("\n", "<br>")
            + "</pre>"
        )
        doc.setHtml(html)
        doc.print_(printer)  # Сохраняет в PDF

        QMessageBox.information(self, "Успешно", f"Отчёт сохранён:\n{path}")


def main():
    # QApplication — обязательный объект, управляющий GUI и событиями
    app = QApplication(sys.argv)

    # Устанавливаем общий шрифт для всего приложения
    app.setFont(QFont(FONT, FONT_SIZE))

    # Создаём и показываем главное окно
    window = IVCCalculatorApp()
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

валидация даты рождения и даты исследования. Дата рождения не может быть позже даты исследования.
Дата исследования не может быть в будущем (позже текущей даты).

Добавить иконку приложения

Сохранение истории расчётов (локально, без облака)
Каждый расчёт сохраняется в ~/.ivc_calculator/history.json (или в AppData на Windows).
В интерфейсе — кнопка «История» → мини-таблица (дата, IVC, возраст, КТ %).
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
