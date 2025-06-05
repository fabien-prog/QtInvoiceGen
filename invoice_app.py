import sys
import os
import json
import requests
import traceback
from datetime import datetime
import logging

from PyQt5 import QtCore, QtGui, QtWidgets
import qdarkstyle

STYLE_OVERRIDE_PATH = "custom_style.qss"

# -----------------------
# === CONFIGURATION ===
# -----------------------

API_KEY = "API_KEY"  # ← Replace with your real API key

DEFAULT_TEMPLATE = {
    "logo": "https://yourdomain.com/path/to/logo.png",
    "from": "Your Company Name\n1234 Main St.\nSuite 100\nHometown, QC A1B 2C3\nCanada",
    "currency": "CAD",   # Change if needed (e.g. "EUR" or "USD")
    "invoice_number": 1,
}

TEMPLATE_DIR = "templates"
DATA_FILE = "invoice_data.json"
SETTINGS_FILE = "settings.json"
CUSTOMERS_FILE = "customers.json"
HISTORY_DIR = "history"

# Ensure needed folders exist
os.makedirs(TEMPLATE_DIR, exist_ok=True)
os.makedirs(HISTORY_DIR, exist_ok=True)

# ----------------------------
# === LOGGING SETUP ===
# ----------------------------

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("invoice_app.log", mode="a", encoding="utf-8")
    ]
)

logging.debug("Starting InvoiceApp")

# ----------------------------
# === HELPER FUNCTIONS ===
# ----------------------------

def load_json_file(path, default):
    """
    Load JSON from `path`. If it doesn't exist or is invalid, write `default`
    to it and return `default`.
    """
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                logging.debug(f"Loaded JSON from {path}: {data}")
                return data
        except Exception as e:
            logging.error(f"Failed to parse {path}: {e}")
    # Create or overwrite with default
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2, ensure_ascii=False)
        logging.debug(f"Created default JSON at {path}: {default}")
    except Exception as e:
        logging.error(f"Failed to write default to {path}: {e}")
    return default

def save_json_file(path, data):
    """Save `data` as UTF-8 JSON to `path`."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logging.debug(f"Saved JSON to {path}: {data}")
    except Exception as e:
        logging.error(f"Failed to save JSON to {path}: {e}")

def load_invoice_data():
    """
    Load or initialize invoice numbering data from DATA_FILE.
    Returns a dict with at least "last_invoice_number".
    """
    return load_json_file(DATA_FILE, {"last_invoice_number": DEFAULT_TEMPLATE["invoice_number"]})

def save_invoice_data(data):
    """Persist invoice numbering data to DATA_FILE."""
    save_json_file(DATA_FILE, data)

def next_invoice_number():
    """
    Increment and return the next invoice number (integer).
    """
    data = load_invoice_data()
    nxt = data["last_invoice_number"] + 1
    data["last_invoice_number"] = nxt
    save_invoice_data(data)
    logging.debug(f"Incremented invoice number to: {nxt}")
    return nxt

def load_settings():
    """
    Load settings (logo, from, currency) from SETTINGS_FILE,
    or initialize with DEFAULT_TEMPLATE.
    """
    return load_json_file(SETTINGS_FILE, DEFAULT_TEMPLATE.copy())

def save_settings(settings):
    """Persist `settings` (logo/from/currency) to SETTINGS_FILE."""
    save_json_file(SETTINGS_FILE, settings)

def load_customers():
    """
    Load customers from CUSTOMERS_FILE.
    Each customer is stored as { "address": "...", "prefix": "..." }.
    If file missing or in old format, migrate automatically.
    """
    raw = load_json_file(CUSTOMERS_FILE, {})
    migrated = {}
    for name, value in raw.items():
        if isinstance(value, str):
            # Old format: value was just address
            migrated[name] = {"address": value, "prefix": ""}
        elif isinstance(value, dict):
            addr = value.get("address", "")
            pref = value.get("prefix", "")
            migrated[name] = {"address": addr, "prefix": pref}
        else:
            migrated[name] = {"address": "", "prefix": ""}
    # Overwrite file if migration happened
    if migrated != raw:
        save_customers(migrated)
    return migrated

def save_customers(customers):
    """Persist `customers` dict to CUSTOMERS_FILE."""
    save_json_file(CUSTOMERS_FILE, customers)

# ----------------------------
# === SETTINGS DIALOG ===
# ----------------------------

class SettingsDialog(QtWidgets.QDialog):
    """
    Dialog for editing:
      - Default Logo URL, From-address, Currency
      - Customer list (add/remove customers + addresses + prefix)
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(600, 500)

        self.settings = load_settings()
        self.customers = load_customers()

        main_layout = QtWidgets.QVBoxLayout(self)

        tabs = QtWidgets.QTabWidget()
        main_layout.addWidget(tabs)

        # --- Tab 1: Defaults ---
        tab_defaults = QtWidgets.QWidget()
        tab1_layout = QtWidgets.QFormLayout(tab_defaults)
        tab1_layout.setLabelAlignment(QtCore.Qt.AlignRight)

        # Logo URL
        self.logo_edit = QtWidgets.QLineEdit(self.settings.get("logo", ""))
        tab1_layout.addRow("Logo URL:", self.logo_edit)

        # From Address (multi-line)
        self.from_edit = QtWidgets.QTextEdit()
        self.from_edit.setPlainText(self.settings.get("from", ""))
        self.from_edit.setFixedHeight(80)
        tab1_layout.addRow("From Address:", self.from_edit)

        # Currency
        self.currency_edit = QtWidgets.QLineEdit(self.settings.get("currency", ""))
        tab1_layout.addRow("Currency (e.g. CAD):", self.currency_edit)

        tabs.addTab(tab_defaults, "Defaults")

        # --- Tab 2: Customers ---
        tab_customers = QtWidgets.QWidget()
        tab2_layout = QtWidgets.QVBoxLayout(tab_customers)

        # Section: Add New Customer
        new_group = QtWidgets.QGroupBox("Add New Customer")
        new_layout = QtWidgets.QFormLayout(new_group)
        self.new_cust_name = QtWidgets.QLineEdit()
        self.new_cust_address = QtWidgets.QTextEdit()
        self.new_cust_address.setFixedHeight(60)
        self.new_cust_prefix = QtWidgets.QLineEdit()
        self.new_cust_prefix.setPlaceholderText("e.g. ACME-")
        self.add_cust_btn = QtWidgets.QPushButton("Add Customer")
        self.add_cust_btn.setStyleSheet("border-radius:4px; padding:6px 12px;")

        new_layout.addRow("Name:", self.new_cust_name)
        new_layout.addRow("Address:", self.new_cust_address)
        new_layout.addRow("Order Prefix:", self.new_cust_prefix)
        new_layout.addRow("", self.add_cust_btn)
        tab2_layout.addWidget(new_group)

        # Section: Existing Customers List + Edit/Remove
        exist_group = QtWidgets.QGroupBox("Existing Customers")
        exist_layout = QtWidgets.QVBoxLayout(exist_group)
        self.cust_list = QtWidgets.QListWidget()
        for cname in sorted(self.customers.keys()):
            self.cust_list.addItem(cname)
        exist_layout.addWidget(self.cust_list)

        edit_layout = QtWidgets.QHBoxLayout()
        self.edit_cust_btn = QtWidgets.QPushButton("Edit Selected")
        self.remove_cust_btn = QtWidgets.QPushButton("Remove Selected")
        self.edit_cust_btn.setStyleSheet("border-radius:4px; padding:6px 12px;")
        self.remove_cust_btn.setStyleSheet("border-radius:4px; padding:6px 12px;")
        edit_layout.addWidget(self.edit_cust_btn)
        edit_layout.addWidget(self.remove_cust_btn)
        exist_layout.addLayout(edit_layout)

        tab2_layout.addWidget(exist_group)
        tabs.addTab(tab_customers, "Customers")

        # Dialog Buttons: Save & Cancel
        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        main_layout.addWidget(btns)

        # === Connections ===
        self.add_cust_btn.clicked.connect(self._add_customer)
        self.remove_cust_btn.clicked.connect(self._remove_customer)
        self.edit_cust_btn.clicked.connect(self._edit_customer)

    def _add_customer(self):
        name = self.new_cust_name.text().strip()
        addr = self.new_cust_address.toPlainText().strip()
        pref = self.new_cust_prefix.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, "Error", "Customer name cannot be empty.")
            return
        if name in self.customers:
            QtWidgets.QMessageBox.warning(self, "Error", "Customer already exists.")
            return
        # Add to in-memory dict and list widget
        self.customers[name] = {"address": addr, "prefix": pref}
        self.cust_list.addItem(name)
        self.new_cust_name.clear()
        self.new_cust_address.clear()
        self.new_cust_prefix.clear()
        logging.debug(f"Added new customer: {name} → {addr}, prefix={pref}")

    def _remove_customer(self):
        selected_item = self.cust_list.currentItem()
        if not selected_item:
            return
        name = selected_item.text()
        del self.customers[name]
        self.cust_list.takeItem(self.cust_list.row(selected_item))
        logging.debug(f"Removed customer: {name}")

    def _edit_customer(self):
        selected_item = self.cust_list.currentItem()
        if not selected_item:
            return
        name = selected_item.text()
        data = self.customers.get(name, {"address": "", "prefix": ""})

        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle(f"Edit Customer: {name}")
        dlg.resize(400, 300)
        layout = QtWidgets.QFormLayout(dlg)

        addr_edit = QtWidgets.QTextEdit()
        addr_edit.setPlainText(data.get("address", ""))
        addr_edit.setFixedHeight(60)
        pref_edit = QtWidgets.QLineEdit(data.get("prefix", ""))

        layout.addRow("Address:", addr_edit)
        layout.addRow("Order Prefix:", pref_edit)

        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel
        )
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addRow(btns)

        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            new_addr = addr_edit.toPlainText().strip()
            new_pref = pref_edit.text().strip()
            self.customers[name] = {"address": new_addr, "prefix": new_pref}
            save_customers(self.customers)
            logging.debug(f"Edited customer: {name} → {new_addr}, prefix={new_pref}")

    def accept(self):
        """
        When "Save" is clicked: write both settings.json and customers.json, then close.
        """
        # Gather default settings
        self.settings["logo"] = self.logo_edit.text().strip()
        self.settings["from"] = self.from_edit.toPlainText().strip()
        self.settings["currency"] = self.currency_edit.text().strip()
        save_settings(self.settings)
        logging.debug(f"Saved settings: {self.settings}")

        # Save customers map
        save_customers(self.customers)
        logging.debug(f"Saved customers: {self.customers}")

        super().accept()

# ----------------------------
# === HISTORY DIALOG ===
# ----------------------------

class HistoryDialog(QtWidgets.QDialog):
    """
    Dialog that lists all JSON payloads saved under history/.
    Selecting one and clicking "Load" returns that JSON payload to the caller.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Invoice History")
        self.resize(450, 550)

        layout = QtWidgets.QVBoxLayout(self)

        self.history_list = QtWidgets.QListWidget()
        layout.addWidget(self.history_list)

        # Populate with all .json files in HISTORY_DIR
        for fname in sorted(os.listdir(HISTORY_DIR)):
            if fname.lower().endswith(".json"):
                self.history_list.addItem(fname)

        btn_layout = QtWidgets.QHBoxLayout()
        self.load_btn = QtWidgets.QPushButton("Load Selected")
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.load_btn.setStyleSheet("border-radius:4px; padding:6px 12px;")
        self.cancel_btn.setStyleSheet("border-radius:4px; padding:6px 12px;")
        btn_layout.addWidget(self.load_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.load_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

    def selected_payload(self):
        """
        Return the parsed JSON dict of the selected filename, or None.
        """
        item = self.history_list.currentItem()
        if not item:
            return None
        fname = item.text()
        path = os.path.join(HISTORY_DIR, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                logging.debug(f"Loaded history payload from {path}: {data}")
                return data
        except Exception as e:
            logging.error(f"Failed to load history file {path}: {e}")
            return None

# ----------------------------
# === MAIN WINDOW CLASS ===
# ----------------------------

class InvoiceApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Invoice Generator (Dark Mode)")
        self.resize(1000, 820)

        # Load settings & customers
        self.settings = load_settings()
        self.customers = load_customers()

        self._build_ui()
        self._load_defaults()
        self._connect_signals()

    def _build_ui(self):
        # --- Set Inter font globally (unchanged) ---
        self.setFont(QtGui.QFont("Inter", 10))

        # --- Menu Bar with Settings & History (add icons) ---
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")

        settings_action = QtWidgets.QAction(QtGui.QIcon(":/icons/gear_white.png"), "Settings", self)
        history_action = QtWidgets.QAction(QtGui.QIcon(":/icons/history_white.png"), "History", self)
        file_menu.addAction(settings_action)
        file_menu.addAction(history_action)
        settings_action.triggered.connect(self.open_settings)
        history_action.triggered.connect(self.open_history)

        # --- Central widget & layout ---
        central = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)
        self.setCentralWidget(central)

        # ========== TOP SECTION: Logo Preview + Invoice Info ==========
        top_frame = QtWidgets.QFrame()
        top_frame.setObjectName("topFrame")
        top_frame.setFrameShape(QtWidgets.QFrame.NoFrame)
        top_frame.setLayout(QtWidgets.QHBoxLayout())
        top_frame.layout().setContentsMargins(0, 0, 0, 0)
        top_frame.layout().setSpacing(20)

        # Left: Logo “card”
        logo_card = QtWidgets.QFrame()
        logo_card.setObjectName("card")
        logo_card.setFrameShape(QtWidgets.QFrame.NoFrame)
        logo_card.setLayout(QtWidgets.QVBoxLayout())
        logo_card.layout().setContentsMargins(8, 8, 8, 8)
        logo_card.layout().setSpacing(8)

        logo_header = QtWidgets.QLabel("Logo Preview")
        logo_header.setObjectName("sectionHeader")
        logo_card.layout().addWidget(logo_header)

        self.logo_label = QtWidgets.QLabel(alignment=QtCore.Qt.AlignCenter)
        self.logo_label.setFixedSize(220, 120)
        self.logo_label.setStyleSheet("background: #2e2e2e; border: 1px solid #555;")
        logo_card.layout().addWidget(self.logo_label)

        self.refresh_logo_btn = QtWidgets.QPushButton(QtGui.QIcon(":/icons/refresh_white.png"), "Refresh Logo")
        self.refresh_logo_btn.setFixedHeight(28)
        logo_card.layout().addWidget(self.refresh_logo_btn, alignment=QtCore.Qt.AlignCenter)

        top_frame.layout().addWidget(logo_card, stretch=1)

        # Right: Invoice #, Dates, Customer/From fields in a card
        info_card = QtWidgets.QFrame()
        info_card.setObjectName("card")
        info_card.setFrameShape(QtWidgets.QFrame.NoFrame)
        info_card.setLayout(QtWidgets.QFormLayout())
        info_card.layout().setContentsMargins(8, 8, 8, 8)
        info_card.layout().setSpacing(12)

        info_header = QtWidgets.QLabel("Invoice Details")
        info_header.setObjectName("sectionHeader")
        info_card.layout().addRow(info_header)

        # Invoice Number
        self.invoice_number_edit = QtWidgets.QLineEdit()
        self.invoice_number_edit.setReadOnly(True)
        info_card.layout().addRow("Invoice #:", self.invoice_number_edit)

        # Date with calendar arrow
        self.date_edit = QtWidgets.QDateEdit(calendarPopup=True)
        self.date_edit.setDate(QtCore.QDate.currentDate())
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setFixedWidth(120)
        info_card.layout().addRow("Date:", self.date_edit)

        # Due Date
        self.due_date_edit = QtWidgets.QDateEdit(calendarPopup=True)
        default_due = QtCore.QDate.currentDate().addDays(30)
        self.due_date_edit.setDate(default_due)
        self.due_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.due_date_edit.setFixedWidth(120)
        info_card.layout().addRow("Due Date:", self.due_date_edit)

        # Customer selection
        self.customer_combo = QtWidgets.QComboBox()
        self.customer_combo.addItem("— Select Customer —")
        for cname in sorted(self.customers.keys()):
            self.customer_combo.addItem(cname)
        self.customer_combo.setFixedWidth(200)
        info_card.layout().addRow("Customer:", self.customer_combo)

        # To (address)
        self.to_text = QtWidgets.QTextEdit()
        self.to_text.setFixedHeight(60)
        info_card.layout().addRow("To (Address):", self.to_text)

        # From (your info)
        self.from_text = QtWidgets.QTextEdit()
        self.from_text.setFixedHeight(60)
        info_card.layout().addRow("From (You):", self.from_text)

        top_frame.layout().addWidget(info_card, stretch=2)

        main_layout.addWidget(top_frame)

        # ========== MIDDLE SECTION: Line Items ==========
        items_frame = QtWidgets.QFrame()
        items_frame.setObjectName("card")
        items_frame.setFrameShape(QtWidgets.QFrame.NoFrame)
        items_frame.setLayout(QtWidgets.QVBoxLayout())
        items_frame.layout().setContentsMargins(8, 8, 8, 8)
        items_frame.layout().setSpacing(8)

        items_header = QtWidgets.QLabel("Invoice Items")
        items_header.setObjectName("sectionHeader")
        items_frame.layout().addWidget(items_header)

        # Items table
        self.items_table = QtWidgets.QTableWidget(4, 3)
        self.items_table.setHorizontalHeaderLabels(["Description", "Quantity", "Unit Cost"])
        self.items_table.horizontalHeader().setStretchLastSection(True)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.items_table.setEditTriggers(QtWidgets.QAbstractItemView.AllEditTriggers)
        self.items_table.setFixedHeight(200)
        self.items_table.setAlternatingRowColors(True)

        # Pre-fill rows
        for row in range(4):
            desc = QtWidgets.QTableWidgetItem("")
            qty = QtWidgets.QTableWidgetItem("1")
            unit = QtWidgets.QTableWidgetItem("0.00")
            qty.setTextAlignment(QtCore.Qt.AlignCenter)
            unit.setTextAlignment(QtCore.Qt.AlignCenter)
            self.items_table.setItem(row, 0, desc)
            self.items_table.setItem(row, 1, qty)
            self.items_table.setItem(row, 2, unit)

        items_frame.layout().addWidget(self.items_table)

        # Add/Remove row buttons in a horizontal layout
        row_btn_layout = QtWidgets.QHBoxLayout()
        self.add_item_button = QtWidgets.QPushButton(QtGui.QIcon(":/icons/plus_white.png"), "Add Item")
        self.remove_item_button = QtWidgets.QPushButton(QtGui.QIcon(":/icons/trash_white.png"), "Remove Row")
        self.add_item_button.setFixedHeight(28)
        self.remove_item_button.setFixedHeight(28)
        row_btn_layout.addWidget(self.add_item_button)
        row_btn_layout.addWidget(self.remove_item_button)
        row_btn_layout.addStretch()
        items_frame.layout().addLayout(row_btn_layout)

        main_layout.addWidget(items_frame)

        # ========== EXTRA CHARGES SECTION ==========
        extra_frame = QtWidgets.QFrame()
        extra_frame.setObjectName("card")
        extra_frame.setFrameShape(QtWidgets.QFrame.NoFrame)
        extra_frame.setLayout(QtWidgets.QGridLayout())
        extra_frame.layout().setContentsMargins(8, 8, 8, 8)
        extra_frame.layout().setSpacing(12)

        extra_header = QtWidgets.QLabel("Extras & Taxes")
        extra_header.setObjectName("sectionHeader")
        extra_frame.layout().addWidget(extra_header, 0, 0, 1, 4)

        # Discount
        extra_frame.layout().addWidget(QtWidgets.QLabel("Discount:"), 1, 0)
        self.discount_type_combo = QtWidgets.QComboBox()
        self.discount_type_combo.addItems(["Fixed", "%"])
        self.discount_type_combo.setFixedWidth(60)
        extra_frame.layout().addWidget(self.discount_type_combo, 1, 1)
        self.discount_edit = QtWidgets.QLineEdit("0.00")
        self.discount_edit.setFixedWidth(80)
        extra_frame.layout().addWidget(self.discount_edit, 1, 2)

        # Shipping
        extra_frame.layout().addWidget(QtWidgets.QLabel("Shipping:"), 1, 3)
        self.shipping_edit = QtWidgets.QLineEdit("0.00")
        self.shipping_edit.setFixedWidth(80)
        extra_frame.layout().addWidget(self.shipping_edit, 1, 4)

        # Apply Tax
        self.apply_tax_chk = QtWidgets.QCheckBox("Apply Tax")
        self.apply_tax_chk.setChecked(True)
        extra_frame.layout().addWidget(self.apply_tax_chk, 2, 0)

        # GST %
        extra_frame.layout().addWidget(QtWidgets.QLabel("GST (%):"), 2, 1)
        self.gst_edit = QtWidgets.QLineEdit("5.00")
        self.gst_edit.setFixedWidth(60)
        extra_frame.layout().addWidget(self.gst_edit, 2, 2)

        # QST %
        extra_frame.layout().addWidget(QtWidgets.QLabel("QST (%):"), 2, 3)
        self.qst_edit = QtWidgets.QLineEdit("9.975")
        self.qst_edit.setFixedWidth(60)
        extra_frame.layout().addWidget(self.qst_edit, 2, 4)

        main_layout.addWidget(extra_frame)

        # ========== TOTALS DISPLAY ==========
        totals_frame = QtWidgets.QFrame()
        totals_frame.setObjectName("card")
        totals_frame.setFrameShape(QtWidgets.QFrame.NoFrame)
        totals_frame.setLayout(QtWidgets.QHBoxLayout())
        totals_frame.layout().setContentsMargins(8, 8, 8, 8)
        totals_frame.layout().setSpacing(20)

        self.subtotal_label = QtWidgets.QLabel("Subtotal: 0.00")
        self.subtotal_label.setStyleSheet("font-weight: bold;")
        totals_frame.layout().addWidget(self.subtotal_label)

        self.tax_label = QtWidgets.QLabel("Tax (0.00%): 0.00")
        self.tax_label.setStyleSheet("font-weight: bold;")
        totals_frame.layout().addWidget(self.tax_label)

        self.total_label = QtWidgets.QLabel("Total: 0.00")
        self.total_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        totals_frame.layout().addWidget(self.total_label)

        totals_frame.layout().addStretch()
        main_layout.addWidget(totals_frame)

        # ========== NOTES / TERMS ==========
        notes_frame = QtWidgets.QFrame()
        notes_frame.setObjectName("card")
        notes_frame.setFrameShape(QtWidgets.QFrame.NoFrame)
        notes_frame.setLayout(QtWidgets.QVBoxLayout())
        notes_frame.layout().setContentsMargins(8, 8, 8, 8)
        notes_frame.layout().setSpacing(8)

        notes_header = QtWidgets.QLabel("Notes / Terms")
        notes_header.setObjectName("sectionHeader")
        notes_frame.layout().addWidget(notes_header)

        self.notes_edit = QtWidgets.QTextEdit()
        self.notes_edit.setPlaceholderText("e.g., Merci pour votre confiance !")
        self.notes_edit.setFixedHeight(80)
        notes_frame.layout().addWidget(self.notes_edit)

        main_layout.addWidget(notes_frame)

        # ========== ACTION BUTTONS ==========
        btns_frame = QtWidgets.QFrame()
        btns_frame.setFrameShape(QtWidgets.QFrame.NoFrame)
        btns_frame.setLayout(QtWidgets.QHBoxLayout())
        btns_frame.layout().setContentsMargins(0, 0, 0, 0)
        btns_frame.layout().setSpacing(12)

        self.load_template_btn = QtWidgets.QPushButton(QtGui.QIcon(":/icons/folder_open_white.png"), "Load Template")
        self.save_template_btn = QtWidgets.QPushButton(QtGui.QIcon(":/icons/save_white.png"), "Save Template")
        self.generate_btn = QtWidgets.QPushButton(QtGui.QIcon(":/icons/pdf_white.png"), "Generate Invoice (PDF)")
        self.generate_btn.setObjectName("generateBtn")  # so QSS can highlight this one

        for btn in (self.load_template_btn, self.save_template_btn, self.generate_btn):
            btn.setFixedHeight(32)

        btns_frame.layout().addWidget(self.load_template_btn)
        btns_frame.layout().addWidget(self.save_template_btn)
        btns_frame.layout().addStretch()
        btns_frame.layout().addWidget(self.generate_btn)

        main_layout.addWidget(btns_frame)

    def _load_defaults(self):
        """
        Populate invoice number, "From" address, logo URL, and currency from settings.
        Also load the logo preview and recalc totals.
        """
        data = load_invoice_data()
        # We display just the zero-padded number here; prefix is added when generating
        self.invoice_number_edit.setText(f"{data['last_invoice_number']:04d}")
        self.from_text.setPlainText(self.settings.get("from", ""))
        self.logo_url = self.settings.get("logo", "")
        self.currency = self.settings.get("currency", "CAD")
        self._load_logo_preview()
        self._toggle_tax_fields()  # set enabled/disabled based on checkbox
        self._recalculate_totals()

    def _connect_signals(self):
        # Logo refresh
        self.refresh_logo_btn.clicked.connect(self._load_logo_preview)

        # Customer selection
        self.customer_combo.currentTextChanged.connect(self._customer_selected)

        # Add/remove item rows
        self.add_item_button.clicked.connect(self._add_item_row)
        self.remove_item_button.clicked.connect(self._remove_selected_row)

        # Whenever any cell in items_table changes, recalc totals
        self.items_table.cellChanged.connect(self._recalculate_totals)

        # Whenever discount/gst/qst/shipping edits finish, recalc totals
        self.discount_edit.editingFinished.connect(self._recalculate_totals)
        self.discount_type_combo.currentIndexChanged.connect(self._recalculate_totals)
        self.gst_edit.editingFinished.connect(self._recalculate_totals)
        self.qst_edit.editingFinished.connect(self._recalculate_totals)
        self.shipping_edit.editingFinished.connect(self._recalculate_totals)

        # Toggle tax fields
        self.apply_tax_chk.stateChanged.connect(self._toggle_tax_fields)

        # Load/Save template, Generate invoice
        self.load_template_btn.clicked.connect(self._load_template)
        self.save_template_btn.clicked.connect(self._save_template)
        self.generate_btn.clicked.connect(self._generate_invoice)

    # --- Logo Preview ---
    def _load_logo_preview(self):
        """
        Fetch self.logo_url via HTTP and display it in self.logo_label as a pixmap.
        """
        self.logo_label.setText("")  # clear previous text
        if not getattr(self, "logo_url", "").strip():
            self.logo_label.setText("No Logo URL")
            return
        try:
            resp = requests.get(self.logo_url, timeout=5)
            resp.raise_for_status()
            data = resp.content
            pix = QtGui.QPixmap()
            pix.loadFromData(data)
            scaled = pix.scaled(
                self.logo_label.size(),
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            )
            self.logo_label.setPixmap(scaled)
            logging.debug("Logo preview loaded successfully.")
        except Exception as e:
            logging.error(f"Failed to load logo from {self.logo_url}: {e}")
            self.logo_label.setText("Failed to load\nlogo")

    # --- Toggle GST/QST fields on/off ---
    def _toggle_tax_fields(self):
        enabled = self.apply_tax_chk.isChecked()
        self.gst_edit.setEnabled(enabled)
        self.qst_edit.setEnabled(enabled)
        self._recalculate_totals()

    # --- Customer Selection ---
    def _customer_selected(self, name):
        """
        When a customer is chosen, fill the "To" address and remember its prefix.
        """
        if name in self.customers:
            cust = self.customers[name]
            self.to_text.setPlainText(cust.get("address", ""))
        else:
            self.to_text.clear()

    # --- Line Items Table Management ---
    def _add_item_row(self):
        """
        Insert a new blank row at the bottom of the items table.
        """
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)
        desc = QtWidgets.QTableWidgetItem("")
        qty = QtWidgets.QTableWidgetItem("1")
        unit = QtWidgets.QTableWidgetItem("0.00")
        qty.setTextAlignment(QtCore.Qt.AlignCenter)
        unit.setTextAlignment(QtCore.Qt.AlignCenter)
        self.items_table.setItem(row, 0, desc)
        self.items_table.setItem(row, 1, qty)
        self.items_table.setItem(row, 2, unit)
        logging.debug(f"Added empty item row at index {row}.")

    def _remove_selected_row(self):
        """
        Remove any selected rows in the items table.
        """
        selected = self.items_table.selectionModel().selectedRows()
        for idx in sorted(selected, key=lambda x: x.row(), reverse=True):
            self.items_table.removeRow(idx.row())
            logging.debug(f"Removed item row at index {idx.row()}.")
        self._recalculate_totals()

    def _recalculate_totals(self):
        """
        Recompute subtotal, discount, taxes, shipping, then total.
        Update the labels accordingly.
        """
        # 1) Subtotal = sum(qty * unit_cost)
        subtotal = 0.0
        for row in range(self.items_table.rowCount()):
            name_item = self.items_table.item(row, 0)
            qty_item = self.items_table.item(row, 1)
            unit_item = self.items_table.item(row, 2)
            if not name_item or not name_item.text().strip():
                continue
            try:
                qty = float(qty_item.text())
            except:
                qty = 0.0
            try:
                unit_price = float(unit_item.text())
            except:
                unit_price = 0.0
            subtotal += qty * unit_price

        # 2) Discount
        try:
            disc_val = float(self.discount_edit.text())
        except:
            disc_val = 0.0

        if self.discount_type_combo.currentText() == "%":
            discount_amt = subtotal * (disc_val / 100.0)
        else:
            discount_amt = disc_val

        base_after_discount = max(0.0, subtotal - discount_amt)

        # 3) Shipping
        try:
            shipping_amt = float(self.shipping_edit.text())
        except:
            shipping_amt = 0.0

        # 4) GST & QST (only if enabled)
        if self.apply_tax_chk.isChecked():
            try:
                gst_rate = float(self.gst_edit.text())
            except:
                gst_rate = 0.0
            try:
                qst_rate = float(self.qst_edit.text())
            except:
                qst_rate = 0.0
            # Instead of compounding, we simply add:
            combined_rate = gst_rate + qst_rate
        else:
            gst_rate = 0.0
            qst_rate = 0.0
            combined_rate = 0.0

        # Tax applies on (base_after_discount + shipping_amt)
        taxable_amount = base_after_discount + shipping_amt
        tax_amt = taxable_amount * (combined_rate / 100.0)

        # 5) Total
        total = base_after_discount + shipping_amt + tax_amt

        # Update labels
        self.subtotal_label.setText(f"Subtotal: {subtotal:,.2f}")
        self.tax_label.setText(f"Tax ({combined_rate:.3f}%): {tax_amt:,.2f}")
        self.total_label.setText(f"Total: {total:,.2f}")

        logging.debug(
            f"Recalculated Totals → Subtotal: {subtotal:.2f}, "
            f"Discount: {discount_amt:.2f}, Shipping: {shipping_amt:.2f}, "
            f"Combined Tax Rate: {combined_rate:.3f}%, Tax Amount: {tax_amt:.2f}, "
            f"Total: {total:.2f}"
        )

    # --- Settings & History Windows ---
    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            # Reload settings
            self.settings = load_settings()
            self.customers = load_customers()

            self.from_text.setPlainText(self.settings.get("from", ""))
            self.logo_url = self.settings.get("logo", "")
            self.currency = self.settings.get("currency", "CAD")
            self._load_logo_preview()

            # Refresh customer combo
            self.customer_combo.clear()
            self.customer_combo.addItem("— Select Customer —")
            for cname in sorted(self.customers.keys()):
                self.customer_combo.addItem(cname)

            logging.debug("Settings reloaded after closing Settings dialog.")

    def open_history(self):
        dlg = HistoryDialog(self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            payload = dlg.selected_payload()
            if payload:
                self._load_payload_into_ui(payload)
                logging.debug("Loaded payload from history into UI.")

    # --- Load a saved payload (from history) into the UI for editing ---
    def _load_payload_into_ui(self, data):
        """
        The `data` dict comes from a saved JSON in history/.
        Populate all fields as if the user had loaded a template or prior invoice.
        """
        try:
            # 1) Invoice #, Date, Due Date
            full_number = data.get("number", "")
            # If the stored “number” already has prefix, split it out
            # We assume the format “PREFIX-0001”. Find the last “-”:
            if "-" in full_number:
                prefix_part, num_part = full_number.rsplit("-", 1)
                self.invoice_number_edit.setText(f"{int(num_part):04d}")
            else:
                self.invoice_number_edit.setText(f"{int(full_number):04d}")

            inv_date = data.get("date", "")
            due_date = data.get("due_date", "")
            try:
                qd = QtCore.QDate.fromString(inv_date, "yyyy-MM-dd")
                if qd.isValid():
                    self.date_edit.setDate(qd)
            except:
                pass
            try:
                qd2 = QtCore.QDate.fromString(due_date, "yyyy-MM-dd")
                if qd2.isValid():
                    self.due_date_edit.setDate(qd2)
            except:
                pass

            # 2) From
            self.from_text.setPlainText(data.get("from", ""))

            # 3) To: try matching a known customer
            to_addr = data.get("to", "")
            found = False
            for cname, cust in self.customers.items():
                if cust.get("address", "").strip() == to_addr.strip():
                    idx = self.customer_combo.findText(cname)
                    if idx != -1:
                        self.customer_combo.setCurrentIndex(idx)
                        found = True
                        break
            if not found:
                self.customer_combo.setCurrentIndex(0)
                self.to_text.setPlainText(to_addr)

            # 4) Notes
            self.notes_edit.setPlainText(data.get("notes", ""))

            # 5) Logo & Currency override
            self.logo_url = data.get("logo", self.settings.get("logo", ""))
            self.currency = data.get("currency", self.settings.get("currency", "CAD"))
            self._load_logo_preview()

            # 6) Items
            items = data.get("items", [])
            rowcount = max(4, len(items))
            self.items_table.setRowCount(rowcount)
            for i in range(rowcount):
                if i < len(items):
                    itm = items[i]
                    desc = QtWidgets.QTableWidgetItem(itm.get("name", ""))
                    qty = QtWidgets.QTableWidgetItem(str(itm.get("quantity", "")))
                    unitc = QtWidgets.QTableWidgetItem(str(itm.get("unit_cost", "")))
                else:
                    desc = QtWidgets.QTableWidgetItem("")
                    qty = QtWidgets.QTableWidgetItem("1")
                    unitc = QtWidgets.QTableWidgetItem("0.00")
                qty.setTextAlignment(QtCore.Qt.AlignCenter)
                unitc.setTextAlignment(QtCore.Qt.AlignCenter)
                self.items_table.setItem(i, 0, desc)
                self.items_table.setItem(i, 1, qty)
                self.items_table.setItem(i, 2, unitc)

            # 7) Discount, Shipping, Taxes
            disc_val = data.get("discounts", 0.0)
            disc_type = data.get("fields", {}).get("discounts", True)
            if disc_type == "%":
                self.discount_type_combo.setCurrentText("%")
            else:
                self.discount_type_combo.setCurrentText("Fixed")
            self.discount_edit.setText(str(disc_val))

            self.shipping_edit.setText(str(data.get("shipping", 0.0)))

            # Combined tax was saved under "tax"
            combined_rate = float(data.get("tax", 0.0))
            # We split it back into GST and QST? Not possible exactly—just put combined into GST and zero QST
            self.apply_tax_chk.setChecked(combined_rate>0.0)
            self.gst_edit.setText(f"{combined_rate:.5f}")
            self.qst_edit.setText("0.000")

            # 8) Sync invoice_number to invoice_data.json
            try:
                if "-" in full_number:
                    _, num_part = full_number.rsplit("-", 1)
                    inv_num_int = int(num_part)
                else:
                    inv_num_int = int(full_number)
                d = load_invoice_data()
                d["last_invoice_number"] = inv_num_int
                save_invoice_data(d)
                logging.debug(f"Synchronized invoice_number to {inv_num_int} from history payload.")
            except Exception as e:
                logging.error(f"Failed to sync invoice_number from history payload: {e}")

            self._toggle_tax_fields()
            self._recalculate_totals()

        except Exception:
            logging.error("Failed to load payload from history into UI:\n" + traceback.format_exc())
            QtWidgets.QMessageBox.warning(self, "Error", "Failed to load from history.")

    # --- Load/Save Templates ---
    def _load_template(self):
        """
        Let user pick a JSON template from TEMPLATE_DIR and populate all fields.
        (Note: Templates do NOT include discount/gst/qst/shipping; those default to zero.)
        """
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Load Template", TEMPLATE_DIR, "JSON Files (*.json)"
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logging.debug(f"Loaded template from {path}: {data}")
        except Exception as e:
            logging.error(f"Failed to load template {path}: {e}")
            QtWidgets.QMessageBox.warning(self, "Error", f"Failed to load template:\n{e}")
            return

        try:
            # Invoice #, Date, Due Date
            num_val = data.get("invoice_number", "")
            self.invoice_number_edit.setText(f"{int(num_val):04d}")

            inv_date = data.get("date", "")
            due_date = data.get("due_date", "")
            try:
                qd = QtCore.QDate.fromString(inv_date, "yyyy-MM-dd")
                if qd.isValid():
                    self.date_edit.setDate(qd)
            except:
                pass
            try:
                qd2 = QtCore.QDate.fromString(due_date, "yyyy-MM-dd")
                if qd2.isValid():
                    self.due_date_edit.setDate(qd2)
            except:
                pass

            # From
            self.from_text.setPlainText(data.get("from", ""))

            # To: try matching a known customer
            to_addr = data.get("to", "")
            found = False
            for cname, cust in self.customers.items():
                if cust.get("address", "").strip() == to_addr.strip():
                    idx = self.customer_combo.findText(cname)
                    if idx != -1:
                        self.customer_combo.setCurrentIndex(idx)
                        found = True
                        break
            if not found:
                self.customer_combo.setCurrentIndex(0)
                self.to_text.setPlainText(to_addr)

            # Notes
            self.notes_edit.setPlainText(data.get("notes", ""))

            # Logo & Currency override
            self.logo_url = data.get("logo", self.settings.get("logo", ""))
            self.currency = data.get("currency", self.settings.get("currency", "CAD"))
            self._load_logo_preview()

            # Items
            items = data.get("items", [])
            rowcount = max(4, len(items))
            self.items_table.setRowCount(rowcount)
            for i in range(rowcount):
                if i < len(items):
                    itm = items[i]
                    desc = QtWidgets.QTableWidgetItem(itm.get("name", ""))
                    qty = QtWidgets.QTableWidgetItem(str(itm.get("quantity", "")))
                    unitc = QtWidgets.QTableWidgetItem(str(itm.get("unit_cost", "")))
                else:
                    desc = QtWidgets.QTableWidgetItem("")
                    qty = QtWidgets.QTableWidgetItem("1")
                    unitc = QtWidgets.QTableWidgetItem("0.00")
                qty.setTextAlignment(QtCore.Qt.AlignCenter)
                unitc.setTextAlignment(QtCore.Qt.AlignCenter)
                self.items_table.setItem(i, 0, desc)
                self.items_table.setItem(i, 1, qty)
                self.items_table.setItem(i, 2, unitc)

            # Discount/Shipping/Taxes default to zero
            self.discount_type_combo.setCurrentText("Fixed")
            self.discount_edit.setText("0.00")
            self.shipping_edit.setText("0.00")
            self.apply_tax_chk.setChecked(True)
            self.gst_edit.setText("5.00")
            self.qst_edit.setText("9.975")

            # Sync invoice_number to invoice_data.json
            try:
                inv_num_int = int(num_val)
                d = load_invoice_data()
                d["last_invoice_number"] = inv_num_int
                save_invoice_data(d)
                logging.debug(f"Synchronized invoice_number to {inv_num_int} from template.")
            except Exception as e:
                logging.error(f"Failed to sync invoice_number from template: {e}")

            self._toggle_tax_fields()
            self._recalculate_totals()

        except Exception:
            logging.error("Failed to load template into UI:\n" + traceback.format_exc())
            QtWidgets.QMessageBox.warning(self, "Error", "Failed to load template.")

    def _save_template(self):
        """
        Prompt for a template name, then write current fields to TEMPLATE_DIR/<name>.json.
        (Templates do NOT save discount/gst/qst/shipping because those often vary per invoice.)
        """
        text, ok = QtWidgets.QInputDialog.getText(
            self, "Save Template", "Enter a name for this template (e.g. AcmeCorp):"
        )
        if not ok or not text.strip():
            return
        name = text.strip()
        filename = os.path.join(TEMPLATE_DIR, f"{name}.json")

        data = {
            "invoice_number": int(self.invoice_number_edit.text()),
            "date": self.date_edit.date().toString("yyyy-MM-dd"),
            "due_date": self.due_date_edit.date().toString("yyyy-MM-dd"),
            "from": self.from_text.toPlainText(),
            "to": self.to_text.toPlainText(),
            "notes": self.notes_edit.toPlainText(),
            "logo": self.logo_url,
            "currency": self.currency,
            "items": [],
        }

        for row in range(self.items_table.rowCount()):
            name_item = self.items_table.item(row, 0)
            qty_item = self.items_table.item(row, 1)
            unit_item = self.items_table.item(row, 2)
            if name_item is None or not name_item.text().strip():
                continue
            try:
                qty = float(qty_item.text())
            except:
                qty = 1.0
            try:
                unitc = float(unit_item.text())
            except:
                unitc = 0.0
            data["items"].append({
                "name": name_item.text().strip(),
                "quantity": qty,
                "unit_cost": unitc
            })

        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logging.debug(f"Saved template to {filename}: {data}")
            QtWidgets.QMessageBox.information(self, "Saved", f"Template saved to:\n{filename}")
        except Exception as e:
            logging.error(f"Could not save template to {filename}: {e}")
            QtWidgets.QMessageBox.warning(self, "Error", f"Could not save template:\n{e}")

    def _generate_invoice(self):
        """
        Collect all fields, send a POST to the Invoice-Generator.com API (French locale),
        let the user save the returned PDF, and also save the JSON payload under history/.
        """
        if not API_KEY or API_KEY.startswith("YOUR_API_KEY"):
            QtWidgets.QMessageBox.warning(
                self,
                "Missing API Key",
                "Please set your API key in the code before generating invoices."
            )
            return

        # 1) Build the payload
        # Determine prefix from selected customer
        cust_name = self.customer_combo.currentText()
        prefix = ""
        if cust_name in self.customers:
            prefix = self.customers[cust_name].get("prefix", "")

        raw_number = int(self.invoice_number_edit.text())
        padded = f"{raw_number:04d}"
        full_number = f"{prefix}{padded}"

        payload = {
            "logo": self.logo_url,
            "from": self.from_text.toPlainText(),
            "to": self.to_text.toPlainText(),
            "number": full_number,
            "date": self.date_edit.date().toString("yyyy-MM-dd"),
            "due_date": self.due_date_edit.date().toString("yyyy-MM-dd"),
            "currency": self.currency,
            "notes": self.notes_edit.toPlainText(),
            # Localization via header
        }

        # 2) Line items
        for idx in range(self.items_table.rowCount()):
            name_item = self.items_table.item(idx, 0)
            qty_item = self.items_table.item(idx, 1)
            unit_item = self.items_table.item(idx, 2)
            if name_item is None or not name_item.text().strip():
                continue
            prefix_key = f"items[{idx}]"
            payload[f"{prefix_key}[name]"] = name_item.text().strip()
            payload[f"{prefix_key}[quantity]"] = str(qty_item.text().strip())
            payload[f"{prefix_key}[unit_cost]"] = str(unit_item.text().strip())

        # 3) Discount
        try:
            disc_val = float(self.discount_edit.text())
        except:
            disc_val = 0.0

        if self.discount_type_combo.currentText() == "%":
            payload["discounts"] = disc_val
            discount_field_flag = "%"
        else:
            payload["discounts"] = disc_val
            discount_field_flag = "true"

        # 4) Shipping
        try:
            shipping_amt = float(self.shipping_edit.text())
        except:
            shipping_amt = 0.0
        payload["shipping"] = shipping_amt

        # 5) Combined tax (GST + QST, non-compounded)
        if self.apply_tax_chk.isChecked():
            try:
                gst_rate = float(self.gst_edit.text())
            except:
                gst_rate = 0.0
            try:
                qst_rate = float(self.qst_edit.text())
            except:
                qst_rate = 0.0
            combined_rate = gst_rate + qst_rate
        else:
            combined_rate = 0.0
        payload["tax"] = combined_rate

        # 6) Flattened fields[] parameters
        payload["fields[discounts]"] = discount_field_flag
        payload["fields[shipping]"] = "true"
        payload["fields[tax]"] = "%"

        # Log the payload
        logging.debug("Payload being sent to the API:")
        logging.debug(json.dumps(payload, indent=2, ensure_ascii=False))

        # 7) Call the API
        try:
            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Accept-Language": "fr-FR"
            }
            response = requests.post(
                "https://invoice-generator.com",
                headers=headers,
                data=payload,
                timeout=15
            )
            response.raise_for_status()
            logging.debug("API response status code: %s", response.status_code)
            logging.debug("API response content (first 200 bytes): %s", response.content[:200])
        except requests.exceptions.RequestException as e:
            # Log response body on error, if available
            resp = getattr(e, "response", None)
            if resp is not None:
                try:
                    body = resp.content.decode("utf-8", errors="ignore")
                except:
                    body = "<non-text response>"
                logging.error("Request failed: %s, status: %s, body:\n%s",
                              e, resp.status_code, body)
            else:
                logging.error("Request failed (no response object): %s", e)
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to generate invoice:\n{e}")
            return

        # 8) Prompt user to save the PDF
        default_filename = f"facture_{full_number}.pdf"
        save_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Invoice PDF (Facture)",
            default_filename,
            "PDF Files (*.pdf)"
        )
        if not save_path:
            return

        try:
            with open(save_path, "wb") as f:
                f.write(response.content)
            logging.debug("Saved PDF to %s", save_path)
            QtWidgets.QMessageBox.information(self, "Saved", f"Invoice PDF saved to:\n{save_path}")
        except Exception as e:
            logging.error("Failed to save PDF: %s", e)
            QtWidgets.QMessageBox.warning(self, "Error", f"Could not save PDF:\n{e}")
            return

        # 9) Save the payload JSON to history/ for future editing
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            hist_filename = f"invoice_{full_number}_{timestamp}.json"
            hist_path = os.path.join(HISTORY_DIR, hist_filename)
            with open(hist_path, "w", encoding="utf-8") as hf:
                json.dump(payload, hf, indent=2, ensure_ascii=False)
            logging.debug("Saved payload to history: %s", hist_path)
        except Exception as e:
            logging.error("Failed to save payload to history: %s", e)
            traceback.print_exc()

        # 10) Advance to next invoice number
        new_num = next_invoice_number()
        self.invoice_number_edit.setText(f"{new_num:04d}")
        logging.debug(f"Advanced to next invoice number: {new_num:04d}")

    # --- Settings & History Windows ---
    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            # Reload settings
            self.settings = load_settings()
            self.customers = load_customers()

            self.from_text.setPlainText(self.settings.get("from", ""))
            self.logo_url = self.settings.get("logo", "")
            self.currency = self.settings.get("currency", "CAD")
            self._load_logo_preview()

            # Refresh customer combo
            self.customer_combo.clear()
            self.customer_combo.addItem("— Select Customer —")
            for cname in sorted(self.customers.keys()):
                self.customer_combo.addItem(cname)

            logging.debug("Settings reloaded after closing Settings dialog.")

    def open_history(self):
        dlg = HistoryDialog(self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            payload = dlg.selected_payload()
            if payload:
                self._load_payload_into_ui(payload)
                logging.debug("Loaded payload from history into UI.")

# ----------------------------
# === APPLICATION ENTRY ===
# ----------------------------

def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setFont(QtGui.QFont("Inter", 10))
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    with open(STYLE_OVERRIDE_PATH, "r", encoding="utf-8") as f:
        stylesheet_override = f.read()
        app.setStyleSheet(app.styleSheet() + "\n" + stylesheet_override)
    window = InvoiceApp()
    # Open maximized (windowed fullscreen)
    window.showMaximized()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
