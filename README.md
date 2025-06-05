# QtInvoiceGen

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> A sleek, dark-mode invoice generator built with PyQt5. Easily create, preview, and generate professional PDF invoices for your clients. Open-source and extensible.

---

## Table of Contents

* [Description](#description)
* [Features](#features)
* [Demo](#demo)
* [Installation](#installation)
* [Configuration](#configuration)
* [Usage](#usage)
* [Template & History](#template--history)
* [Dependencies](#dependencies)
* [Contributing](#contributing)
* [License](#license)
* [Contact](#contact)

---

## Description

**QtInvoiceGen** is an open-source desktop application that streamlines the process of creating, managing, and exporting PDF invoices. Built with PyQt5 and styled with **qDarkStyle**, it offers a modern, dark-mode user interface.
Users can:

* Define default settings (logo, “from” address, currency).
* Maintain a customer list (addresses & invoice prefixes).
* Add line items with quantities and unit costs.
* Apply discounts, shipping fees, GST/QST taxes.
* Preview your company logo in real time.
* Save and load invoice templates (JSON).
* Generate fully-formatted PDF invoices via the Invoice-Generator.com API.
* Store every generated invoice payload in a local `history/` folder for easy reloading or editing.

Because it’s built in Python and Qt, you can customize layouts, colors, or add new features (e.g., additional tax rules, custom layouts, or different PDF engines). All source code is MIT-licensed, so you are free to fork, modify, and distribute.

---

## Features

* **Dark-mode UI** with “card”-style sections for clarity.
* **Logo Preview**: fetch and display your company logo URL instantly.
* **Customer Management**: add, edit, or remove customers (addresses + invoice prefixes).
* **Line-Item Table**: add/remove rows, auto-calculate subtotals, discounts, taxes, shipping, and totals in real time.
* **Discount Options**: fixed amount or percentage.
* **Tax Controls**: GST and QST fields (toggle on/off).
* **Save & Load Templates**: export your current invoice as a JSON template; load later for new invoices.
* **History Folder**: every generated invoice’s JSON payload is saved under `history/` with a timestamped filename.
* **PDF Generation**: one-click “Generate Invoice” calls the Invoice-Generator.com API (French locale by default) and saves a PDF to your disk.
* **Settings Dialog**: configure defaults (logo URL, “from” address, currency) and manage customers.

---

## Demo

> ![Screenshot 2025-06-05 162856](https://github.com/user-attachments/assets/103c2f69-7679-44a0-97ee-3c7d5c7200d1)
> *Example of the main window with invoice items, tax controls, and a previewed logo.*

---


## Installation

1. **Clone this repository**

   ```bash
   git clone https://github.com/YourGitHubUsername/QtInvoiceGen.git
   cd QtInvoiceGen
   ```

2. **Create & activate a Python virtual environment (recommended)**

   ```bash
   python3 -m venv venv
   source venv/bin/activate     # macOS/Linux
   venv\Scripts\activate.bat    # Windows
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Compile Qt Resources (if not precompiled)**
   If you see an `icons.qrc` file, generate `icons_rc.py` by running:

   ```bash
   pyrcc5 icons.qrc -o icons_rc.py
   ```

5. **Run the application**

   ```bash
   python invoice_app.py
   ```

---

## Configuration

1. **API Key**
   The app uses [Invoice-Generator.com](https://invoice-generator.com/) to produce PDFs. In `invoice_app.py`, locate the line:

   ```python
   API_KEY = "API-KEY-HERE"  # ← Replace with your real API key
   ```

   Replace the placeholder with your actual Invoice-Generator.com API key. Without a valid key, PDF generation will not work.

2. **Default Settings**
   On first run, a `settings.json` file is created under the project root. You can open the **File ▶ Settings** dialog to change:

   * **Logo URL** (any publicly accessible image link).
   * **From Address** (your company’s name & mailing address).
   * **Currency** (e.g., “CAD”, “USD”, “EUR”).

3. **Customers**
   In the same **Settings** dialog, add as many customers as needed. Each customer entry stores:

   * **Name** (shown in the “Customer” dropdown).
   * **Address** (populated into the “To (Address)” field when selected).
   * **Invoice Prefix** (e.g., “ACME-”, so invoices become ACME-0001, ACME-0002, etc.).

All configuration files live alongside the executable in the project root:

```
invoice_app.py
settings.json
customers.json
invoice_data.json
/templates/        ← saved JSON templates
/history/          ← generated invoice JSON payloads
```

---

## Usage

1. **Launch the App**

   ```bash
   python invoice_app.py
   ```

   You’ll see a dark-mode window. If your defaults are already set, logo and “from” address will display immediately.

2. **Set Invoice Number & Dates**

   * Invoice # is auto-incremented from `invoice_data.json`.
   * Click the calendar icon to pick a custom Invoice Date or Due Date.

3. **Select a Customer**

   * Choose from the dropdown. Their address auto-fills “To (Address).”
   * If you leave “— Select Customer —,” you can type a custom address manually.

4. **Add Line Items**

   * By default, four blank rows appear.
   * Click **Add Item** to insert a new row.
   * Enter description, quantity, and unit cost.
   * Click **Remove Row** to delete the selected row.

5. **Apply Discount / Shipping / Taxes**

   * Choose “Fixed” or “%” under Discount.
   * Enter a discount value (e.g., “10.00” or “5” for 5%).
   * Toggle “Apply Tax” to enable or disable GST/QST inputs.
   * The subtotal, tax amount, and total update automatically as you type.

6. **Enter Notes / Terms**

   * In the “Notes / Terms” section, add any custom text (e.g., “Merci pour votre confiance !”).

7. **Generate PDF Invoice**

   * Click **Generate Invoice (PDF)**.
   * A dialog appears asking where to save the PDF (default filename: `facture_<PREFIX><####>.pdf`).
   * Once saved, a JSON copy of your payload is stored under `history/invoice_<PREFIX><####>_<YYYYMMDD_HHMMSS>.json`.
   * The invoice number then advances automatically (e.g., 0001 → 0002).

8. **Load / Save Templates**

   * **Save Template**: Click the toolbar button and enter a name (e.g., “AcmeCorp”). A JSON file is created under `templates/AcmeCorp.json`.
   * **Load Template**: Select a JSON from the `templates/` folder; all fields (except discounts/taxes) are populated. Discount and tax fields revert to default values when loading a template.

9. **History**

   * Use **File ▶ History** to browse previously generated invoices. Select one and click **Load Selected** to repopulate the UI with that invoice’s data. This is useful for re-issuing the same invoice or editing past entries.

---

## Template & History Folder Structure

```
/templates
    ├─ AcmeCorp.json
    └─ MyStartup.json

/history
    ├─ invoice_ACME-0001_20250605_143512.json
    ├─ invoice_ACME-0002_20250606_101023.json
    └─ invoice_0003_20250607_091010.json
```

* **templates/**: Save your most-used invoice layouts here. Each file stores:

  * Invoice number
  * Date & due\_date
  * From, To, Notes, Logo, Currency
  * List of items (name, quantity, unit\_cost)

* **history/**: Every time you press “Generate Invoice,” a timestamped JSON payload is created. You can revisit, modify, and regenerate any past invoice.

---

## Dependencies

* **Python 3.7+**
* [PyQt5](https://pypi.org/project/PyQt5/)
* [qDarkStyle](https://pypi.org/project/qdarkstyle/)
* [requests](https://pypi.org/project/requests/)
* [pyrcc5](https://doc.qt.io/qtforpython/tutorials/pyside6/qrc.html) (for compiling Qt resource files)

You can install everything via:

```bash
pip install -r requirements.txt
```

Contents of `requirements.txt`:

```
PyQt5>=5.15.0
qdarkstyle>=3.0.2
requests>=2.22.0
```

---

## Contributing

Contributions are welcome! Here’s a suggested workflow:

1. **Fork the repository**
2. **Create a feature branch**

   ```bash
   git checkout -b feature/awesome-tax-calc
   ```
3. **Commit your changes**

   ```bash
   git commit -m "Implement new tax-override logic"
   ```
4. **Push to your fork**

   ```bash
   git push origin feature/awesome-tax-calc
   ```
5. **Open a Pull Request** on GitHub. Describe your feature, bugfix, or enhancement in detail.

Please ensure you:

* Follow the existing *PEP 8* style, and keep functions and methods concise.
* Add or update unit tests if you modify core logic (e.g., `_recalculate_totals()`).
* Update this README if your feature changes usage, adds new dependencies, or alters configuration.
* Respect the MIT license in all contributions.

---

## License

This project is licensed under the [MIT License](LICENSE). Feel free to use, modify, and distribute under the terms of MIT.

---

## Contact

* **Author**: Fabien Gaudreau
* **Email**: [fabi.gaudreau@gmail.com](mailto:fabi.gaudreau@gmail.com)
* **Repo**: [https://github.com/fabien-prog/QtInvoiceGen](https://github.com/YourGitHubUsername/QtInvoiceGen)
* **Issues**: [https://github.com/fabien-prog/QtInvoiceGen/issues](https://github.com/YourGitHubUsername/QtInvoiceGen/issues)

Thank you for using **QtInvoiceGen**! We hope it streamlines your billing workflow.
