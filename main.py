import os
import sys
import sqlite3
from pathlib import Path
from functools import partial
from cryptography.fernet import Fernet
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QLineEdit, QDialog, QLabel, QHeaderView, QMessageBox, QInputDialog
)


# --- Config ---
MASTER_PASSWORD = "****"
KEY = b"VhVE3I1RTUMiB-g6X-B31V6SXkbdGBOEg9jzW6TRobU="
# ----------------


# ==== DB Path ====
APPDATA = os.getenv('APPDATA') or os.path.expanduser("~")
DB_DIR = Path(APPDATA) / "MyPasswordManager"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "passwords.db"


# ==== Settings ====
def init_db(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS passwords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data BLOB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()


# ==== Resource Path for EXE ====
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# ==== Master Password Window ====
class MasterPasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Master Password")
        self.setWindowIcon(QIcon(resource_path("logo.png")))
        self.setFixedSize(300, 150)

        self.setStyleSheet("""
            QDialog { background-color: #121212; }
            QLabel { color: #e0e0e0; font-weight: bold; font-size: 15pt; }
            QLineEdit { background-color: #1e1e1e; border: 1px solid #3a3a3a; border-radius: 4px; color: #e0e0e0; padding: 4px; }
            QPushButton { background-color: #2b2b2b; border: 1px solid #3a3a3a; border-radius: 6px; color: #e0e0e0; font-weight: bold; padding: 6px 10px; }
            QPushButton:hover { background-color: #333333; }
            QPushButton:pressed { background-color: #222222; }
        """)

        layout = QVBoxLayout()
        label = QLabel("Enter master password:")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setFixedWidth(200)
        layout.addWidget(self.password_input, alignment=Qt.AlignmentFlag.AlignCenter)

        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def get_password(self):
        return self.password_input.text()


# ==== Main Window ====
class PasswordGui(QWidget):
    def __init__(self, conn, fernet):
        super().__init__()
        self.conn = conn
        self.fernet = fernet

        self.setWindowTitle("Password Manager")
        self.setFixedSize(720, 400)
        self.setWindowIcon(QIcon(resource_path("logo.png")))

        self.setStyleSheet("""
            QWidget { background-color: #121212; color: #e0e0e0; font-size: 12px; font-weight: bold; }
            QTableWidget { background-color: #1e1e1e; gridline-color: #2a2a2a; }
            QHeaderView::section { font-weight: bold; font-size: 10pt; background-color: #1f1f1f; border: 1px solid #2a2a2a; padding: 4px; }
            QPushButton#deleteBtn { border-radius: 0px; }
            QPushButton { background-color: #2b2b2b; border: 1px solid #3a3a3a; padding: 6px 10px; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #333333; }
            QPushButton:pressed { background-color: #222222; }
        """)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        top_row = QHBoxLayout()
        title = QLabel("<b>Developer Pexa6</b>")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        top_row.addWidget(title)
        top_row.addStretch()

        self.btn_refresh = QPushButton("Update")
        self.btn_refresh.clicked.connect(self.load_data)
        top_row.addWidget(self.btn_refresh)

        self.btn_add = QPushButton("Add")
        self.btn_add.clicked.connect(self.add_dialog)
        top_row.addWidget(self.btn_add)

        self.layout.addLayout(top_row)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Creation Date", "Label : Password", ""])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 170)
        self.table.setColumnWidth(2, 380)
        self.table.setColumnWidth(3, 70)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.layout.addWidget(self.table)
        self.load_data()

    # ==== Settings ====
    def load_data(self):
        cur = self.conn.cursor()
        cur.execute("SELECT id, data, created_at FROM passwords ORDER BY id;")
        rows = cur.fetchall()
        self.table.setRowCount(0)
        for i, row in enumerate(rows):
            _id, blob, created_at = row
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(str(_id)))
            self.table.setItem(i, 1, QTableWidgetItem(str(created_at)))
            try:
                plain = self.fernet.decrypt(blob).decode("utf-8")
            except Exception as e:
                plain = f"[Decryption Error: {e}]"
            data_item = QTableWidgetItem(plain)
            data_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 2, data_item)

            btn = QPushButton("Delete")
            btn.setObjectName("deleteBtn")
            btn.clicked.connect(partial(self.on_delete_clicked, _id))
            self.table.setCellWidget(i, 3, btn)
        self.table.resizeRowsToContents()

    # ==== Settings ====
    def add_dialog(self):
        text, ok = QInputDialog.getText(self, "Add Entry", "Enter the entry in the format:\nLabel : Password")
        if not ok: return
        s = text.strip()
        if not s:
            QMessageBox.warning(self, "Empty String", "Adding a record — cancelled.")
            return
        if ":" not in s:
            QMessageBox.warning(self, "Invalid Format", "The string must be in the format:\nLabel : Password")
            return
        cipher = self.fernet.encrypt(s.encode("utf-8"))
        cur = self.conn.cursor()
        cur.execute("INSERT INTO passwords (data) VALUES (?);", (cipher,))
        self.conn.commit()
        self.load_data()

    # ==== Settings ====
    def on_delete_clicked(self, row_id):
        reply = QMessageBox.question(
            self, "Deletion Confirmation", f"Are you sure you want to delete the entry? ID: {row_id}",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )
        if reply != QMessageBox.StandardButton.Ok:
            return
        cur = self.conn.cursor()
        cur.execute("DELETE FROM passwords WHERE id = ?;", (row_id,))
        self.conn.commit()
        self.load_data()


# ==== Main ====
if __name__ == "__main__":
    fernet = Fernet(KEY)
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    app = QApplication(sys.argv)

    dlg = MasterPasswordDialog()
    if dlg.exec() != QDialog.DialogCode.Accepted or dlg.get_password() != MASTER_PASSWORD:
        sys.exit()

    win = PasswordGui(conn, fernet)
    win.show()
    sys.exit(app.exec())
