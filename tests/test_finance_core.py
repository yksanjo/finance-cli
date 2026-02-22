from datetime import date
from decimal import Decimal

import click

from finance_cli.cli import validate_amount, validate_date
from finance_cli.database import Database
from finance_cli.models import Expense


def test_validate_amount_parses_currency_string():
    assert validate_amount(None, None, "$1,234.50") == Decimal("1234.50")


def test_validate_amount_rejects_invalid_input():
    try:
        validate_amount(None, None, "not-a-number")
        assert False, "Expected click.BadParameter"
    except click.BadParameter:
        assert True


def test_validate_date_parses_iso_date():
    assert validate_date(None, None, "2026-02-22") == date(2026, 2, 22)


def test_database_add_and_list_expense(tmp_path):
    db = Database(str(tmp_path))
    category = db.get_category_by_name("Food & Dining")
    assert category is not None

    expense_id = db.add_expense(
        Expense(
            amount=Decimal("12.34"),
            category_id=category.id,
            description="Lunch",
            date=date(2026, 2, 22),
            payment_method="card",
        )
    )

    expenses = db.list_expenses(limit=10)
    assert any(e.id == expense_id for e in expenses)
