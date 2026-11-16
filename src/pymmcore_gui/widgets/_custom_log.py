from datetime import datetime

from pymmcore_gui._qt.QtWidgets import QFileDialog
from pymmcore_gui._qt.QtWidgets import (
    QDialog,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
)


class CustomLog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Custom Log")
        self.resize(650, 400)

        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)

        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.text.clear)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.hide)

        buttons = QHBoxLayout()
        buttons.addWidget(clear_button)
        buttons.addStretch()
        buttons.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.text)
        layout.addLayout(buttons)

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_log)

        buttons.addWidget(save_button)

    def add_result(self, task: str, result: dict) -> None:
        timestamp = datetime.now().astimezone().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        self.text.appendPlainText(
            f"[{timestamp}] {task}"
        )

        for key, value in result.items():
            self.text.appendPlainText(f"    {key}: {value}")

        self.text.appendPlainText("")

    def add_error(self, task: str, message: str) -> None:
        timestamp = datetime.now().astimezone().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        self.text.appendPlainText(
            f"[{timestamp}] ERROR - {task}\n    {message}\n"
        )

    def save_log(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save log",
            "custom_log.txt",
            "Text files (*.txt);;All files (*)",
        )

        if filename:
            with open(filename, "w", encoding="utf-8") as file:
                file.write(self.text.toPlainText())