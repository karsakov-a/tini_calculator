import logging
from datetime import datetime
from typing import Any, Dict, List

from PySide6.QtWidgets import (QAbstractItemView, QDialog, QFileDialog,
                               QHBoxLayout, QHeaderView, QMessageBox,
                               QPushButton, QTableWidget, QTableWidgetItem,
                               QVBoxLayout)

from config import (BIRTH_DATE, BUTTON_JOURNAL_CLOSE, BUTTON_JOURNAL_DELETE,
                    BUTTON_JOURNAL_EXPORT_CSV, BUTTON_JOURNAL_OPEN,
                    CT_PERCENT_DESC, D_DIMER_DESC,
                    ERROR_EXPORT_HISTORY_GENERIC, ERROR_EXPORT_HISTORY_IO,
                    GENDER, HISTORY_DIALOG_TITLE, INTERLEUKINS_DESC,
                    LYMPHOCYTES_DESC, NAME_DESC, NO_HISTORY_MESSAGE,
                    PATRONYMIC_DESC, RESEARCH_DATE, SURNAME_DESC,
                    UNKNOWN_STATUS)
from core.history import load_history, save_history


class HistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(HISTORY_DIALOG_TITLE)
        self.resize(900, 500)
        self.history: List[Dict[str, Any]] = load_history()
        self.selected_entry = None

        layout = QVBoxLayout(self)

        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            [
                "Дата сохранения",
                "Пациент",
                BIRTH_DATE,
                RESEARCH_DATE,
                "CITI",
                "Риск",
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        # Кнопки
        btn_layout = QHBoxLayout()
        self.open_btn = QPushButton(BUTTON_JOURNAL_OPEN)
        self.delete_btn = QPushButton(BUTTON_JOURNAL_DELETE)
        self.export_btn = QPushButton(BUTTON_JOURNAL_EXPORT_CSV)
        self.close_btn = QPushButton(BUTTON_JOURNAL_CLOSE)
        self.open_btn.clicked.connect(self.open_selected)
        self.delete_btn.clicked.connect(self.delete_selected)
        self.export_btn.clicked.connect(self.export_history)
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.open_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.export_btn)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

        self.populate_table()
        self.open_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)

    def populate_table(self):
        self.table.setRowCount(len(self.history))
        for row, entry in enumerate(self.history):
            timestamp = datetime.fromisoformat(entry["timestamp"])
            save_date_str = timestamp.strftime("%d.%m.%Y %H:%M")

            raw = entry["raw_data"]
            surname = raw.get(SURNAME_DESC[1], "").strip()
            name = raw.get(NAME_DESC[1], "").strip()
            patronymic = raw.get(PATRONYMIC_DESC[1], "").strip()
            if surname or name or patronymic:
                full_name_parts = [
                    part.capitalize()
                    for part in [surname, name, patronymic]
                    if part
                ]
                patient_display = " ".join(full_name_parts)
            else:
                patient_display = UNKNOWN_STATUS

            dob = raw.get("dob", UNKNOWN_STATUS)
            study_date = raw.get("study_date", UNKNOWN_STATUS)
            citi_val = f"{raw.get('citi', 0):,.0f}"
            risk = raw.get("risk", "")

            self.table.setItem(row, 0, QTableWidgetItem(save_date_str))
            self.table.setItem(row, 1, QTableWidgetItem(patient_display))
            self.table.setItem(row, 2, QTableWidgetItem(dob))
            self.table.setItem(row, 3, QTableWidgetItem(study_date))
            self.table.setItem(row, 4, QTableWidgetItem(citi_val))
            self.table.setItem(row, 5, QTableWidgetItem(risk))

    def on_selection_changed(self):
        enabled = bool(self.table.selectedItems())
        self.open_btn.setEnabled(enabled)
        self.delete_btn.setEnabled(enabled)

    def get_selected_index(self) -> int:
        selected = self.table.selectedItems()
        return selected[0].row() if selected else -1

    def open_selected(self):
        index = self.get_selected_index()
        if index >= 0:
            self.selected_entry = self.history[index]
            self.accept()

    def delete_selected(self):
        index = self.get_selected_index()
        if index >= 0:
            reply = QMessageBox.question(
                self,
                "Подтверждение",
                "Удалить выбранную запись из журнала?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                del self.history[index]
                save_history(self.history)
                self.populate_table()
                self.open_btn.setEnabled(False)
                self.delete_btn.setEnabled(False)

    def export_history(self):
        if not self.history:
            QMessageBox.information(self, "Экспорт", NO_HISTORY_MESSAGE)
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить историю в CSV",
            "",
            "CSV Files (*.csv)",
        )
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"

        try:
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write(
                    f"Дата сохранения;ФИО;{BIRTH_DATE};{RESEARCH_DATE};"
                    f"{GENDER};{D_DIMER_DESC[0]};{INTERLEUKINS_DESC[0]};"
                    f"{LYMPHOCYTES_DESC[0]};{CT_PERCENT_DESC[0]};CITI;Риск\n"
                )
                for entry in self.history:
                    d = entry["raw_data"]
                    timestamp = datetime.fromisoformat(
                        entry["timestamp"]
                    ).strftime("%d.%m.%Y %H:%M")

                    surname = d.get(SURNAME_DESC[1], "").strip()
                    name = d.get(NAME_DESC[1], "").strip()
                    patronymic = d.get(PATRONYMIC_DESC[1], "").strip()
                    if surname or name or patronymic:
                        full_name_parts = [
                            part.capitalize()
                            for part in [surname, name, patronymic]
                            if part
                        ]
                        full_name = " ".join(full_name_parts)
                    else:
                        full_name = UNKNOWN_STATUS

                    f.write(
                        f"{timestamp};"
                        f"{full_name};"
                        f"{d.get('dob', UNKNOWN_STATUS)};"
                        f"{d.get('study_date', UNKNOWN_STATUS)};"
                        f"{d.get('gender', UNKNOWN_STATUS)};"
                        f"{d.get(D_DIMER_DESC[1], 0)};"
                        f"{d.get(INTERLEUKINS_DESC[1], 0)};"
                        f"{d.get(LYMPHOCYTES_DESC[1], 0)};"
                        f"{d.get(CT_PERCENT_DESC[1], UNKNOWN_STATUS)};"
                        f"{d.get('citi', 0):.0f};"
                        f"{d.get('risk', '')}\n"
                    )
            QMessageBox.information(
                self, "Успешно", f"История экспортирована:\n{path}"
            )
        except (OSError, PermissionError) as e:
            logging.error(ERROR_EXPORT_HISTORY_IO.format(e))
            QMessageBox.critical(
                self, "Ошибка", ERROR_EXPORT_HISTORY_IO.format(e)
            )
        except Exception as e:
            logging.error(ERROR_EXPORT_HISTORY_GENERIC.format(e))
            QMessageBox.critical(
                self, "Ошибка", ERROR_EXPORT_HISTORY_GENERIC.format(e)
            )
