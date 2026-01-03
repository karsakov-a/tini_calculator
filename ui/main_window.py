from functools import partial
from typing import Any, Dict

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
    QDialog,
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

from config import (
    AGE,
    APP_NAME,
    BIRTH_DATE,
    BUTTON_CALCULATE,
    BUTTON_COPY,
    BUTTON_RESET,
    BUTTON_SAVE_PDF,
    CT_PERCENT_DESC,
    D_DIMER_DESC,
    DATE_FORMAT,
    DECIMAL_PLACES,
    ERROR_MESSAGE_CT,
    FONT_FAMILY,
    FONT_SIZE_RESULT_MESSAGE,
    FONT_SIZE_RESULT_VALUE,
    FONT_SIZE_TITLE,
    FULL_NAME_PATTERN,
    FULL_NAME_PLACEHOLDER,
    GENDER,
    GENDER_FEMALE,
    GENDER_MALE,
    INSTRUCTION_DEFAULT,
    INTERLEUKINS_DESC,
    JOURNAL_BUTTON,
    LYMPHOCYTES_DESC,
    MAX_CT_PERCENT,
    MAX_NAME_LEN,
    MIN_CT_PERCENT,
    NAME_DESC,
    PATRONYMIC_DESC,
    RESEARCH_DATE,
    SURNAME_DESC,
    UNKNOWN_STATUS,
    MAIN_WINDOW_SIZE,
    ERROR_SAVE_HISTORY,
    MIN_DATE,
    MAX_DATE,
    DEFAULT_DATE_BORN,
    DEFAULT_DATE_RESEARCH,
)
from core.calculator import (
    calculate_citi,
    get_interpretation_text,
    interpret_citi,
)
from core.history import (
    build_full_report,
    create_history_entry,
    load_history,
    save_history,
)
from ui.history_dialog import HistoryDialog


def create_float_regex(
    max_integer_digits: int, max_decimal_digits: int = 5
) -> str:
    """Генерирует регулярное выражение для чисел с плавающей точкой."""
    int_part = f"\\d{{1,{max_integer_digits}}}"
    dec_part = f"\\.\\d{{1,{max_decimal_digits}}}"
    return f"^({int_part}{dec_part}?|{dec_part})$"


class CITICalculatorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(*MAIN_WINDOW_SIZE)

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
            if key in (D_DIMER_DESC[1], INTERLEUKINS_DESC[1]):
                regex = create_float_regex(5, DECIMAL_PLACES)
                line_edit.setValidator(
                    QRegularExpressionValidator(QRegularExpression(regex))
                )
            elif key == LYMPHOCYTES_DESC[1]:
                regex = create_float_regex(2, DECIMAL_PLACES)
                line_edit.setValidator(
                    QRegularExpressionValidator(QRegularExpression(regex))
                )
            elif key == CT_PERCENT_DESC[1]:
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

        # === Кнопка журнала ===
        journal_btn = QPushButton(JOURNAL_BUTTON)
        journal_btn.clicked.connect(self.open_history_journal)
        layout.addWidget(journal_btn)

        # === Расположение кнопок ===
        result_layout.addLayout(btn_row1)
        result_layout.addLayout(btn_row2)

        # Инициализация состояния кнопок
        self.calculate_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)
        self.copy_btn.setEnabled(False)
        self.pdf_btn.setEnabled(False)

        self.on_input_changed()  # инициализация состояния

    def get_float(self, key: str, default: float = 0.0) -> float:
        text = self.fields[key].text().strip().replace(",", ".")
        if not text:
            return default
        try:
            return float(text)
        except ValueError:
            return default

    def toggle_date_input(self, date_edit, checked):
        date_edit.setEnabled(not checked)
        self.on_input_changed()

    def calculate_age(self, birth, study):
        if not birth.isValid() or not study.isValid():
            return 0
        years = study.year() - birth.year()
        if (study.month(), study.day()) < (birth.month(), birth.day()):
            years -= 1
        return max(0, years)

    def is_ct_valid(self) -> bool:
        text = self.fields[CT_PERCENT_DESC[1]].text().strip()
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
        d_dimer = self.get_float(D_DIMER_DESC[1])
        interleukins = self.get_float(INTERLEUKINS_DESC[1])
        lymphocytes = self.get_float(LYMPHOCYTES_DESC[1])
        all_filled = d_dimer > 0 and interleukins > 0 and lymphocytes > 0

        self.instruction_label.setText(INSTRUCTION_DEFAULT)
        self.instruction_label.setVisible(not all_filled)
        self.calculate_btn.setEnabled(all_filled)

    def on_calculate(self):
        d_dimer = self.get_float(D_DIMER_DESC[1])
        interleukins = self.get_float(INTERLEUKINS_DESC[1])
        lymphocytes = self.get_float(LYMPHOCYTES_DESC[1])

        if not (d_dimer > 0 and interleukins > 0 and lymphocytes > 0):
            return

        if not self.is_ct_valid():
            self.show_error(ERROR_MESSAGE_CT)
            return

        citi = calculate_citi(d_dimer, interleukins, lymphocytes)
        risk, color = interpret_citi(citi)
        ct_val = self.get_float(CT_PERCENT_DESC[1])
        full_interpretation = get_interpretation_text(citi, ct_val)

        self.result_value.setText(f"{citi:,.0f}")
        self.result_value.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.risk_label.setText(full_interpretation)
        self.risk_label.setStyleSheet(f"color: {color};")
        self.result_value.show()
        self.risk_label.show()

        # --- Сбор данных для отчёта ---
        surname = self.fields[SURNAME_DESC[1]].text().strip()
        name = self.fields["name"].text().strip()
        patronymic = self.fields["patronymic"].text().strip()

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

        ct_text = self.fields[CT_PERCENT_DESC[1]].text().strip()
        ct_str = (
            UNKNOWN_STATUS
            if not ct_text
            else f"{int(float(ct_text.replace(',', '.')))} %"
        )

        # --- Формирование полного отчёта ---
        self.full_report = build_full_report(
            surname=surname,
            name=name,
            patronymic=patronymic,
            gender=gender,
            dob_str=dob_str,
            study_str=study_str,
            age_str=age_str,
            d_dimer=d_dimer,
            interleukins=interleukins,
            lymphocytes=lymphocytes,
            ct_str=ct_str,
            citi=citi,
            risk=risk,
        )

        # --- Сохранение в историю ---
        raw_data = {
            SURNAME_DESC[1]: surname,
            NAME_DESC[1]: name,
            PATRONYMIC_DESC[1]: patronymic,
            GENDER: gender,
            "dob": dob_str,
            "study_date": study_str,
            D_DIMER_DESC[1]: d_dimer,
            INTERLEUKINS_DESC[1]: interleukins,
            LYMPHOCYTES_DESC[1]: lymphocytes,
            CT_PERCENT_DESC[1]: ct_str,
            "citi": citi,
            "risk": risk,
        }
        try:
            history_entry = create_history_entry(self.full_report, raw_data)
            current_history = load_history()
            current_history.append(history_entry)
            save_history(current_history)
        except (OSError, IOError) as e:
            QMessageBox.critical(self, (ERROR_SAVE_HISTORY).format(e))

        # Активация кнопок
        for btn in [self.reset_btn, self.copy_btn, self.pdf_btn]:
            btn.setEnabled(True)

    def show_error(self, msg: str):
        self.instruction_label.setText(msg)
        self.instruction_label.show()
        self.result_value.hide()
        self.risk_label.hide()
        self.copy_btn.setEnabled(False)
        self.pdf_btn.setEnabled(False)

    def reset_form(self):
        for key in (SURNAME_DESC[1], NAME_DESC[1], PATRONYMIC_DESC[1]):
            self.fields[key].clear()
        self.radio_not_specified.setChecked(True)
        self.dob_unknown.setChecked(True)
        self.study_date_unknown.setChecked(True)
        self.age_display.setText("—")
        for key in (
            D_DIMER_DESC[1],
            INTERLEUKINS_DESC[1],
            LYMPHOCYTES_DESC[1],
            CT_PERCENT_DESC[1],
        ):
            self.fields[key].clear()
        self.result_value.hide()
        self.risk_label.hide()
        self.instruction_label.setText(INSTRUCTION_DEFAULT)
        self.instruction_label.show()
        for btn in [self.reset_btn, self.copy_btn, self.pdf_btn]:
            btn.setEnabled(False)
        self.on_input_changed()

    def copy_to_clipboard(self):
        QApplication.clipboard().setText(self.full_report)
        QMessageBox.information(
            self, "Копирование", "Отчёт скопирован в буфер обмена."
        )

    def save_to_pdf(self):
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
            "<h2>Отчёт: CITI Calculator</h2>"
            "<pre style='font-family: Consolas, monospace; font-size: 12pt;'>"
            + self.full_report.replace("\n", "<br>")
            + "</pre>"
        )
        doc.setHtml(html)
        doc.print_(printer)

        QMessageBox.information(self, "Успешно", f"Отчёт сохранён:\n{path}")

    def open_history_journal(self):
        dialog = HistoryDialog(self)
        if dialog.exec() == QDialog.Accepted and dialog.selected_entry:
            self.load_entry_to_form(dialog.selected_entry)

    def load_entry_to_form(self, entry: Dict[str, Any]):
        d = entry["raw_data"]

        self.fields[SURNAME_DESC[1]].setText(d.get(SURNAME_DESC[1], ""))
        self.fields[NAME_DESC[1]].setText(d.get(NAME_DESC[1], ""))
        self.fields[PATRONYMIC_DESC[1]].setText(d.get(PATRONYMIC_DESC[1], ""))

        gender = d.get("gender", UNKNOWN_STATUS)
        if gender == GENDER_MALE:
            self.radio_male.setChecked(True)
        elif gender == GENDER_FEMALE:
            self.radio_female.setChecked(True)
        else:
            self.radio_not_specified.setChecked(True)

        # Дата рождения
        dob = d.get("dob", UNKNOWN_STATUS)
        if dob == UNKNOWN_STATUS:
            self.dob_unknown.setChecked(True)
        else:
            self.dob_unknown.setChecked(False)
            qdate = QDate.fromString(dob, DATE_FORMAT)
            if qdate.isValid():
                self.dob_edit.setDate(qdate)
            else:
                self.dob_unknown.setChecked(True)

        # Дата исследования
        study = d.get("study_date", UNKNOWN_STATUS)
        if study == UNKNOWN_STATUS:
            self.study_date_unknown.setChecked(True)
        else:
            self.study_date_unknown.setChecked(False)
            qdate = QDate.fromString(study, DATE_FORMAT)
            if qdate.isValid():
                self.study_date_edit.setDate(qdate)
            else:
                self.study_date_unknown.setChecked(True)

        self.fields[D_DIMER_DESC[1]].setText(str(d.get(D_DIMER_DESC[1], "")))
        self.fields[INTERLEUKINS_DESC[1]].setText(
            str(d.get(INTERLEUKINS_DESC[1], ""))
        )
        self.fields[LYMPHOCYTES_DESC[1]].setText(
            str(d.get(LYMPHOCYTES_DESC[1], ""))
        )
        ct_val = d.get(CT_PERCENT_DESC[1], UNKNOWN_STATUS)
        if ct_val != UNKNOWN_STATUS:
            ct_clean = ct_val.replace(" %", "")
            self.fields[CT_PERCENT_DESC[1]].setText(ct_clean)

        self.on_calculate()
