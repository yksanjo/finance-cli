# 💰 Finance CLI

A beautiful, privacy-focused command-line interface for personal finance management. Track expenses, categorize spending, generate insightful reports, and visualize your financial data — all stored locally on your machine.

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey)

## ✨ Features

- **🔒 Privacy-First**: All data stored locally in SQLite — no cloud, no tracking
- **⚡ Fast & Lightweight**: Built with Click and Rich for a snappy CLI experience
- **📊 Rich Visualizations**: Beautiful terminal charts and tables
- **🏷️ Smart Categorization**: Organize expenses with customizable categories
- **📈 Reports & Analytics**: Monthly, yearly, and category-specific reports
- **💰 Budget Tracking**: Set budgets and get alerts when you're close to limits
- **📤 Data Export**: Export to CSV or JSON anytime
- **🔍 Powerful Search**: Find expenses quickly with keyword search

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/finance-cli.git
cd finance-cli

# Install
pip install -e .

# Or install directly
pip install finance-cli
```

### First Steps

```bash
# See available commands
finance --help

# Add your first expense
finance add 45.50 "Food & Dining" -d "Grocery shopping"

# View your spending summary
finance stats

# See recent expenses
finance list --this-month
```

## 📖 Usage Guide

### Adding Expenses

```bash
# Simple expense
finance add 25.00 "Transportation" -d "Uber to airport"

# With date and payment method
finance add 120.00 "Housing" --date 2024-01-15 -p card

# Add tags
finance add 85.00 "Entertainment" -d "Concert tickets" -t fun -t music

# Mark as recurring
finance add 1200.00 "Housing" -d "Monthly rent" --recurring
```

### Listing & Searching

```bash
# Today's expenses
finance list --today

# This month's expenses (with limit)
finance list --this-month --limit 50

# Custom date range
finance list --start-date 2024-01-01 --end-date 2024-01-31

# Search by keyword
finance search "coffee"
```

### Managing Categories

```bash
# List all categories
finance category list

# Add a new category
finance category add "Gym" -d "Fitness memberships" -b 100.00
```

### Reports

```bash
# Monthly report with charts
finance report monthly --month 2 --year 2024

# Yearly overview
finance report yearly --year 2024

# Category-specific report
finance report category "Food & Dining" --days 30

# Budget status
finance report budget
```

### Budgets

```bash
# Set overall monthly budget
finance budget set 3000.00 --period monthly

# Set category budget with alert at 80%
finance budget set 500.00 -c "Food & Dining" --alert 80

# List all budgets
finance budget list
```

### Data Export

```bash
# Export to CSV
finance export --format csv -o my_expenses.csv

# Export specific date range to JSON
finance export --format json --start-date 2024-01-01 --end-date 2024-03-31
```

## 🏗️ Project Structure

```
finance-cli/
├── finance_cli/
│   ├── __init__.py       # Package initialization
│   ├── cli.py            # CLI interface (Click commands)
│   ├── database.py       # SQLite operations
│   ├── models.py         # Data models (Expense, Category, Budget)
│   ├── reports.py        # Report generation
│   └── charts.py         # Terminal chart visualization
├── data/                 # Local data storage (created automatically)
│   └── finance.db        # SQLite database
├── tests/                # Test suite
├── setup.py              # Package setup
├── requirements.txt      # Dependencies
└── README.md             # This file
```

## 🔒 Privacy & Data Storage

All your financial data is stored locally in a SQLite database at:

- **macOS/Linux**: `~/.finance-cli/finance.db`
- **Windows**: `%USERPROFILE%\.finance-cli\finance.db`

To use a custom location:

```bash
export FINANCE_CLI_DATA_DIR=/path/to/your/data
finance list
```

## 🎨 Sample Output

```
📊 Financial Summary
────────────────────────────────────────
This Month
Total: $1,234.56  (45 transactions)
vs Last Month: -12.3%

Top Category: Food & Dining
Daily Average: $41.15

Budget Status: 67% used
```

## 🛠️ Development

```bash
# Clone repo
git clone https://github.com/yourusername/finance-cli.git
cd finance-cli

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## 📝 License

MIT License — feel free to use, modify, and distribute.

## 🙋 FAQ

**Q: Is my data secure?**
A: Yes! All data is stored locally on your machine in a SQLite database. No data is sent to any server.

**Q: Can I import data from other apps?**
A: Currently, you can import data by directly inserting into the SQLite database. CSV import is planned for a future release.

**Q: Can I sync across devices?**
A: Since data is local, you can sync the database file using your preferred method (Dropbox, Syncthing, etc.).

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

<p align="center">Made with 💚 for privacy-conscious individuals</p>
