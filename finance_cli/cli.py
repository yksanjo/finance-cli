"""CLI interface for Finance CLI using Click and Rich."""
import os
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from .database import Database
from .models import Expense, Category, Budget
from .reports import ReportGenerator
from .charts import ChartRenderer, format_currency

# Global console for rich output
console = Console()


def get_db() -> Database:
    """Get database instance."""
    data_dir = os.environ.get("FINANCE_CLI_DATA_DIR")
    return Database(data_dir)


def validate_amount(ctx, param, value):
    """Validate and parse amount."""
    if value is None:
        return None
    try:
        # Remove currency symbols and commas
        cleaned = str(value).replace("$", "").replace(",", "").strip()
        return Decimal(cleaned)
    except InvalidOperation:
        raise click.BadParameter(f"Invalid amount: {value}")


def validate_date(ctx, param, value):
    """Validate and parse date."""
    if value is None:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise click.BadParameter(f"Invalid date format. Use YYYY-MM-DD: {value}")


@click.group()
@click.version_option(version="1.0.0", prog_name="finance")
@click.option('--data-dir', envvar='FINANCE_CLI_DATA_DIR',
              help='Custom data directory for database storage')
@click.pass_context
def cli(ctx, data_dir):
    """
    💰 Finance CLI - Personal Finance Manager
    
    A privacy-focused CLI tool for tracking expenses, categorizing spending,
    and generating reports. All data is stored locally on your machine.
    
    Examples:
    
        finance add 45.50 "Groceries" -c "Food & Dining" -d "Weekly shopping"
        
        finance list --this-month
        
        finance report monthly --month 2
        
        finance stats
    """
    ctx.ensure_object(dict)
    ctx.obj['data_dir'] = data_dir
    if data_dir:
        os.environ['FINANCE_CLI_DATA_DIR'] = data_dir


# === Expense Commands ===

@cli.group()
def expense():
    """Manage expenses (add, list, edit, delete)."""
    pass


@cli.command()
@click.argument('amount', callback=validate_amount)
@click.argument('category')
@click.option('-d', '--description', default='', help='Description of the expense')
@click.option('--date', 'expense_date', callback=validate_date, 
              help='Date of expense (YYYY-MM-DD, default: today)')
@click.option('-p', '--payment', default='cash', 
              type=click.Choice(['cash', 'card', 'transfer', 'check', 'other']),
              help='Payment method')
@click.option('-t', '--tag', multiple=True, help='Tags for the expense')
@click.option('--recurring', is_flag=True, help='Mark as recurring expense')
def add(amount, category, description, expense_date, payment, tag, recurring):
    """Add a new expense.
    
    Examples:
    
        finance add 45.50 "Food & Dining" -d "Grocery shopping"
        
        finance add 120.00 "Housing" --date 2024-01-15 -p card
    """
    db = get_db()
    
    # Find or create category
    cat = db.get_category_by_name(category)
    if not cat:
        # Ask to create new category
        if click.confirm(f"Category '{category}' doesn't exist. Create it?"):
            cat_id = db.add_category(Category(name=category))
        else:
            # Show available categories
            categories = db.get_categories()
            console.print("Available categories:", style="yellow")
            for c in categories:
                console.print(f"  • {c.name}")
            return
    else:
        cat_id = cat.id
    
    # Create expense
    expense = Expense(
        amount=amount,
        category_id=cat_id,
        description=description,
        date=expense_date or date.today(),
        payment_method=payment,
        tags=list(tag),
        is_recurring=recurring
    )
    
    expense_id = db.add_expense(expense)
    
    console.print(Panel(
        f"Amount: [yellow]{format_currency(amount)}[/]\n"
        f"Category: [cyan]{category}[/]\n"
        f"Description: {description or '-'}\n"
        f"Date: [dim]{expense.date}[/]",
        title=f"✅ Expense Added (ID: {expense_id})",
        border_style="green"
    ))


@cli.command(name='list')
@click.option('-n', '--limit', default=20, help='Number of expenses to show')
@click.option('--today', is_flag=True, help='Show only today')
@click.option('--this-week', 'this_week', is_flag=True, help='Show only this week')
@click.option('--this-month', 'this_month', is_flag=True, help='Show only this month')
@click.option('--category', 'filter_category', help='Filter by category name')
@click.option('--start-date', callback=validate_date, help='Start date (YYYY-MM-DD)')
@click.option('--end-date', callback=validate_date, help='End date (YYYY-MM-DD)')
def list_expenses(limit, today, this_week, this_month, filter_category, start_date, end_date):
    """List expenses with filters.
    
    Examples:
    
        finance list --today
        
        finance list --this-month --limit 50
        
        finance list --start-date 2024-01-01 --end-date 2024-01-31
    """
    db = get_db()
    
    # Determine date range
    end = date.today()
    start = None
    
    if today:
        start = end
    elif this_week:
        start = end - timedelta(days=end.weekday())
    elif this_month:
        start = end.replace(day=1)
    elif start_date or end_date:
        start = start_date
        end = end_date or end
    
    # Get category filter
    category_id = None
    if filter_category:
        cat = db.get_category_by_name(filter_category)
        if cat:
            category_id = cat.id
        else:
            console.print(f"[red]Category '{filter_category}' not found[/]")
            return
    
    expenses = db.list_expenses(start, end, category_id, limit)
    
    if not expenses:
        console.print("[dim]No expenses found.[/]")
        return
    
    # Build table
    table = Table(
        show_header=True,
        header_style="bold magenta",
        box=box.SIMPLE
    )
    table.add_column("ID", style="dim", width=6)
    table.add_column("Date", style="cyan", width=12)
    table.add_column("Category", style="green", width=18)
    table.add_column("Description")
    table.add_column("Amount", justify="right", style="yellow")
    table.add_column("Method", style="dim", width=10)
    
    total = Decimal(0)
    
    for e in expenses:
        table.add_row(
            str(e.id),
            str(e.date),
            e.category_name[:17],
            e.description[:35] or "-",
            format_currency(e.amount),
            e.payment_method or "-"
        )
        total += e.amount
    
    console.print(table)
    console.print(f"\n[dim]Showing {len(expenses)} expenses | Total: [/][yellow]{format_currency(total)}[/]")


@cli.command()
@click.argument('expense_id', type=int)
def edit(expense_id):
    """Edit an existing expense."""
    db = get_db()
    
    expense = db.get_expense(expense_id)
    if not expense:
        console.print(f"[red]Expense #{expense_id} not found[/]")
        return
    
    console.print(f"Editing expense #{expense_id}:")
    
    # Get new values
    new_amount = click.prompt("Amount", default=float(expense.amount), type=float)
    new_desc = click.prompt("Description", default=expense.description)
    new_date = click.prompt("Date (YYYY-MM-DD)", default=str(expense.date))
    
    expense.amount = Decimal(str(new_amount))
    expense.description = new_desc
    expense.date = datetime.strptime(new_date, "%Y-%m-%d").date()
    
    if db.update_expense(expense):
        console.print("[green]✅ Expense updated successfully[/]")
    else:
        console.print("[red]Failed to update expense[/]")


@cli.command()
@click.argument('expense_id', type=int)
@click.confirmation_option(prompt='Are you sure you want to delete this expense?')
def delete(expense_id):
    """Delete an expense."""
    db = get_db()
    
    if db.delete_expense(expense_id):
        console.print(f"[green]✅ Expense #{expense_id} deleted[/]")
    else:
        console.print(f"[red]Expense #{expense_id} not found[/]")


@cli.command()
@click.argument('keyword')
def search(keyword):
    """Search expenses by description."""
    db = get_db()
    
    expenses = db.search_expenses(keyword)
    
    if not expenses:
        console.print(f"[dim]No expenses matching '{keyword}'[/]")
        return
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim")
    table.add_column("Date", style="cyan")
    table.add_column("Category", style="green")
    table.add_column("Description")
    table.add_column("Amount", justify="right", style="yellow")
    
    for e in expenses:
        table.add_row(
            str(e.id),
            str(e.date),
            e.category_name,
            e.description or "-",
            format_currency(e.amount)
        )
    
    console.print(table)


# === Category Commands ===

@cli.group()
def category():
    """Manage categories."""
    pass


@category.command('list')
def list_categories():
    """List all categories."""
    db = get_db()
    
    categories = db.get_categories()
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    table.add_column("Budget Limit", justify="right", style="yellow")
    
    for c in categories:
        table.add_row(
            str(c.id),
            c.name,
            c.description[:40] or "-",
            format_currency(c.budget_limit) if c.budget_limit else "-"
        )
    
    console.print(table)


@category.command('add')
@click.argument('name')
@click.option('-d', '--description', default='', help='Category description')
@click.option('-b', '--budget', type=float, help='Monthly budget limit')
@click.option('--color', default='#6366f1', help='Category color (hex)')
def add_category(name, description, budget, color):
    """Add a new category."""
    db = get_db()
    
    cat = Category(
        name=name,
        description=description,
        budget_limit=Decimal(str(budget)) if budget else None,
        color=color
    )
    
    try:
        cat_id = db.add_category(cat)
        console.print(f"[green]✅ Category '{name}' created (ID: {cat_id})[/]")
    except Exception as e:
        if "UNIQUE" in str(e):
            console.print(f"[red]Category '{name}' already exists[/]")
        else:
            console.print(f"[red]Error: {e}[/]")


# === Report Commands ===

@cli.group()
def report():
    """Generate financial reports."""
    pass


@report.command('monthly')
@click.option('-y', '--year', type=int, default=date.today().year)
@click.option('-m', '--month', type=int, default=date.today().month)
@click.option('--no-charts', is_flag=True, help='Hide charts')
def monthly_report(year, month, no_charts):
    """Generate monthly spending report."""
    db = get_db()
    generator = ReportGenerator(db)
    
    try:
        report_group = generator.generate_monthly_report(year, month, not no_charts)
        console.print(report_group)
    except Exception as e:
        console.print(f"[red]Error generating report: {e}[/]")


@report.command('yearly')
@click.option('-y', '--year', type=int, default=date.today().year)
def yearly_report(year):
    """Generate yearly spending report."""
    db = get_db()
    generator = ReportGenerator(db)
    
    report_group = generator.generate_yearly_report(year)
    console.print(report_group)


@report.command('category')
@click.argument('category_name')
@click.option('--days', default=90, help='Number of days to include')
def category_report(category_name, days):
    """Generate report for a specific category."""
    db = get_db()
    
    cat = db.get_category_by_name(category_name)
    if not cat:
        console.print(f"[red]Category '{category_name}' not found[/]")
        return
    
    generator = ReportGenerator(db)
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    report_group = generator.generate_category_report(cat.id, start_date, end_date)
    console.print(report_group)


@report.command('budget')
def budget_report():
    """Show budget status report."""
    db = get_db()
    generator = ReportGenerator(db)
    
    report_group = generator.generate_budget_report()
    console.print(report_group)


# === Budget Commands ===

@cli.group()
def budget():
    """Manage budgets."""
    pass


@budget.command('set')
@click.argument('amount', type=float)
@click.option('-c', '--category', help='Category name (omit for overall budget)')
@click.option('-p', '--period', default='monthly',
              type=click.Choice(['daily', 'weekly', 'monthly', 'yearly']))
@click.option('--alert', default=80, help='Alert threshold percentage (default: 80)')
def set_budget(amount, category, period, alert):
    """Set a budget for a category or overall."""
    db = get_db()
    
    category_id = None
    if category:
        cat = db.get_category_by_name(category)
        if not cat:
            console.print(f"[red]Category '{category}' not found[/]")
            return
        category_id = cat.id
    
    budget = Budget(
        category_id=category_id,
        amount=Decimal(str(amount)),
        period=period,
        alert_threshold=alert
    )
    
    db.set_budget(budget)
    
    cat_name = category or "Overall"
    console.print(f"[green]✅ Budget set for {cat_name}: {format_currency(Decimal(str(amount)))}/{period}[/]")


@budget.command('list')
def list_budgets():
    """List all budgets."""
    db = get_db()
    
    budgets = db.get_budgets()
    
    if not budgets:
        console.print("[dim]No budgets set.[/]")
        return
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Category", style="cyan")
    table.add_column("Amount", justify="right", style="yellow")
    table.add_column("Period", style="green")
    table.add_column("Alert At", style="dim")
    
    for b in budgets:
        table.add_row(
            b.category_name,
            format_currency(b.amount),
            b.period,
            f"{b.alert_threshold}%"
        )
    
    console.print(table)


# === Utility Commands ===

@cli.command()
def stats():
    """Show database statistics and summary."""
    db = get_db()
    
    stats_data = db.get_stats()
    
    # Summary card
    generator = ReportGenerator(db)
    console.print(generator.generate_summary_card())
    
    # Database info
    console.print(Panel(
        f"Database: [cyan]{stats_data['database_path']}[/]\n"
        f"Size: [yellow]{stats_data['database_size'] / 1024:.1f} KB[/]\n"
        f"Date Range: [dim]{stats_data['first_expense_date'] or 'N/A'} to {stats_data['last_expense_date'] or 'N/A'}[/]",
        title="Database Info",
        border_style="dim"
    ))


@cli.command()
@click.option('-f', '--format', 'output_format', default='csv',
              type=click.Choice(['csv', 'json']))
@click.option('-o', '--output', help='Output file path')
@click.option('--start-date', callback=validate_date)
@click.option('--end-date', callback=validate_date)
def export(output_format, output, start_date, end_date):
    """Export expenses to CSV or JSON."""
    db = get_db()
    
    if not output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"finance_export_{timestamp}.{output_format}"
    
    output_path = Path(output).expanduser().resolve()
    
    try:
        if output_format == 'csv':
            db.export_to_csv(str(output_path), start_date, end_date)
        else:
            db.export_to_json(str(output_path), start_date, end_date)
        
        console.print(f"[green]✅ Exported to {output_path}[/]")
        
        # Show file size
        size = output_path.stat().st_size
        console.print(f"[dim]File size: {size / 1024:.1f} KB[/]")
        
    except Exception as e:
        console.print(f"[red]Export failed: {e}[/]")


@cli.command()
@click.argument('query')
def sql(query):
    """Run a raw SQL query (advanced users).
    
    Example: finance sql "SELECT * FROM expenses LIMIT 10"
    """
    db = get_db()
    
    try:
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            
            # Get column names
            columns = [description[0] for description in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            
            if not columns:
                console.print("[dim]Query executed successfully[/]")
                return
            
            table = Table(show_header=True, header_style="bold magenta")
            for col in columns:
                table.add_column(col)
            
            for row in rows[:100]:  # Limit to 100 rows
                table.add_row(*[str(cell) if cell is not None else "NULL" for cell in row])
            
            console.print(table)
            
            if len(rows) > 100:
                console.print(f"[dim]... and {len(rows) - 100} more rows[/]")
                
    except Exception as e:
        console.print(f"[red]Query error: {e}[/]")


# === Aliases for common commands ===

@cli.command()
@click.pass_context
def summary(ctx):
    """Quick summary of finances (alias for 'stats')."""
    ctx.forward(stats)


# Main entry point
def main():
    """Entry point for the CLI."""
    cli()


if __name__ == '__main__':
    main()
