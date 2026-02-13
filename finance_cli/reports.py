"""Report generation for Finance CLI."""
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich.console import Group
from rich import box

from .database import Database
from .models import MonthlySummary, CategorySummary
from .charts import ChartRenderer, format_currency


@dataclass
class SpendingInsights:
    """Generated insights from spending data."""
    biggest_category: Optional[str]
    biggest_category_amount: Decimal
    most_frequent_category: Optional[str]
    most_frequent_count: int
    average_transaction: Decimal
    biggest_transaction_day: Optional[date]
    biggest_day_amount: Decimal
    savings_rate: Optional[float]
    recommendations: List[str]


class ReportGenerator:
    """Generate financial reports and insights."""
    
    def __init__(self, db: Database):
        self.db = db
        self.charts = ChartRenderer()
    
    def generate_monthly_report(
        self, 
        year: int, 
        month: int,
        show_charts: bool = True
    ) -> Group:
        """Generate a comprehensive monthly report."""
        summary = self.db.get_monthly_summary(year, month)
        category_data = self.db.get_spending_by_category(
            date(year, month, 1),
            date(year, month, 28) if month == 2 else date(year, month, 30)
        )
        
        elements = []
        
        # Header panel
        month_name = date(year, month, 1).strftime("%B %Y")
        header_text = Text()
        header_text.append(f"Monthly Report: {month_name}\n", style="bold underline")
        header_text.append(f"Total Spent: ", style="dim")
        header_text.append(format_currency(summary.total_spent), style="bold yellow")
        header_text.append(f"  |  Transactions: ", style="dim")
        header_text.append(str(summary.transaction_count), style="bold blue")
        header_text.append(f"  |  Daily Avg: ", style="dim")
        header_text.append(format_currency(summary.daily_average), style="bold green")
        
        if summary.vs_previous_month is not None:
            if summary.vs_previous_month > 0:
                header_text.append(f"  |  vs Last Month: +{summary.vs_previous_month:.1f}%", style="red")
            else:
                header_text.append(f"  |  vs Last Month: {summary.vs_previous_month:.1f}%", style="green")
        
        elements.append(Panel(header_text, border_style="blue"))
        
        # Category breakdown
        if category_data:
            cat_table = self.charts.render_category_breakdown(category_data)
            elements.append(cat_table)
            
            # Bar chart
            if show_charts:
                chart_data = {c.category_name: c.total_spent for c in category_data}
                bar_chart = self.charts.render_bar_chart(chart_data, "Spending by Category")
                elements.append(bar_chart)
        
        # Insights
        insights = self._generate_insights(category_data, summary)
        if insights.recommendations:
            rec_text = "\n".join(f"• {r}" for r in insights.recommendations[:5])
            elements.append(Panel(rec_text, title="💡 Insights", border_style="green"))
        
        return Group(*elements)
    
    def generate_yearly_report(self, year: int) -> Group:
        """Generate a comprehensive yearly report."""
        monthly_summaries = self.db.get_yearly_summary(year)
        
        elements = []
        
        # Calculate yearly totals
        yearly_total = sum(s.total_spent for s in monthly_summaries)
        yearly_count = sum(s.transaction_count for s in monthly_summaries)
        
        # Header
        header_text = Text()
        header_text.append(f"Yearly Report: {year}\n", style="bold underline")
        header_text.append(f"Total Spent: ", style="dim")
        header_text.append(format_currency(yearly_total), style="bold yellow")
        header_text.append(f"  |  Total Transactions: ", style="dim")
        header_text.append(str(yearly_count), style="bold blue")
        header_text.append(f"  |  Monthly Avg: ", style="dim")
        header_text.append(format_currency(yearly_total / 12), style="bold green")
        
        elements.append(Panel(header_text, border_style="blue"))
        
        # Monthly breakdown table
        monthly_table = self.charts.render_monthly_comparison(monthly_summaries)
        elements.append(monthly_table)
        
        # Monthly trend sparkline
        monthly_values = [s.total_spent for s in monthly_summaries]
        sparkline = self.charts.render_sparkline(monthly_values, "Monthly Spending Trend")
        elements.append(sparkline)
        
        # Top categories for the year
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        category_data = self.db.get_spending_by_category(start_date, end_date)
        
        if category_data:
            cat_table = self.charts.render_category_breakdown(
                category_data[:5], 
                "Top 5 Categories"
            )
            elements.append(cat_table)
        
        return Group(*elements)
    
    def generate_category_report(
        self,
        category_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Group:
        """Generate a detailed report for a specific category."""
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=90)
        
        expenses = self.db.list_expenses(start_date, end_date, category_id)
        
        # Get category info
        categories = self.db.get_categories()
        category = next((c for c in categories if c.id == category_id), None)
        cat_name = category.name if category else "Unknown"
        
        elements = []
        
        # Header
        total = sum(e.amount for e in expenses)
        avg = total / len(expenses) if expenses else Decimal(0)
        
        header_text = Text()
        header_text.append(f"Category Report: {cat_name}\n", style="bold underline")
        header_text.append(f"Period: {start_date} to {end_date}\n", style="dim")
        header_text.append(f"Total: ", style="dim")
        header_text.append(format_currency(total), style="bold yellow")
        header_text.append(f"  |  Transactions: ", style="dim")
        header_text.append(str(len(expenses)), style="bold blue")
        header_text.append(f"  |  Average: ", style="dim")
        header_text.append(format_currency(avg), style="bold green")
        
        elements.append(Panel(header_text, border_style="blue"))
        
        # Recent transactions
        if expenses:
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Date", style="cyan", width=12)
            table.add_column("Description", style="white")
            table.add_column("Amount", justify="right", style="yellow")
            table.add_column("Method", style="dim")
            
            for e in expenses[:20]:  # Show last 20
                table.add_row(
                    str(e.date),
                    e.description[:40] or "-",
                    format_currency(e.amount),
                    e.payment_method or "-"
                )
            
            elements.append(table)
        
        return Group(*elements)
    
    def generate_budget_report(self) -> Group:
        """Generate budget status report."""
        budgets = self.db.get_budgets()
        
        if not budgets:
            return Group(Panel("No budgets set. Use 'finance budget set' to create budgets.", 
                              border_style="yellow"))
        
        # Get actual spending for each budget
        today = date.today()
        start_of_month = today.replace(day=1)
        
        category_ids = [b.category_id for b in budgets if b.category_id]
        spending_data = self.db.get_spending_by_category(start_of_month, today)
        
        actual_spending = {0: Decimal(0)}  # Overall budget key
        for s in spending_data:
            actual_spending[s.category_id] = s.total_spent
            actual_spending[0] += s.total_spent
        
        elements = []
        
        # Budget overview table
        budget_table = self.charts.render_budget_overview(budgets, actual_spending)
        elements.append(budget_table)
        
        # Alert panel for budgets over threshold
        alerts = []
        for budget in budgets:
            spent = actual_spending.get(budget.category_id or 0, Decimal(0))
            if budget.amount > 0:
                pct = float(spent / budget.amount * 100)
                if pct >= 100:
                    alerts.append(f"🔴 {budget.category_name}: {pct:.0f}% over budget!")
                elif pct >= budget.alert_threshold:
                    alerts.append(f"🟡 {budget.category_name}: {pct:.0f}% of budget used")
        
        if alerts:
            elements.append(Panel("\n".join(alerts), title="Budget Alerts", 
                                 border_style="red"))
        
        return Group(*elements)
    
    def _generate_insights(
        self,
        category_data: List[CategorySummary],
        summary: MonthlySummary
    ) -> SpendingInsights:
        """Generate spending insights and recommendations."""
        recommendations = []
        
        biggest = max(category_data, key=lambda x: x.total_spent) if category_data else None
        most_frequent = max(category_data, key=lambda x: x.transaction_count) if category_data else None
        
        avg_transaction = (summary.total_spent / summary.transaction_count 
                          if summary.transaction_count > 0 else Decimal(0))
        
        # Budget warnings
        for cat in category_data:
            if cat.budget_used_percentage and cat.budget_used_percentage >= 100:
                recommendations.append(
                    f"You've exceeded your {cat.category_name} budget by "
                    f"{cat.budget_used_percentage - 100:.0f}%"
                )
            elif cat.budget_used_percentage and cat.budget_used_percentage >= 80:
                recommendations.append(
                    f"You're at {cat.budget_used_percentage:.0f}% of your "
                    f"{cat.category_name} budget"
                )
        
        # Spending trend
        if summary.vs_previous_month is not None:
            if summary.vs_previous_month > 20:
                recommendations.append(
                    f"Spending is up {summary.vs_previous_month:.0f}% from last month. "
                    "Consider reviewing discretionary expenses."
                )
            elif summary.vs_previous_month < -10:
                recommendations.append(
                    f"Great job! Spending is down {abs(summary.vs_previous_month):.0f}% "
                    "from last month."
                )
        
        # Category-specific insights
        if biggest and biggest.total_spent > summary.total_spent * Decimal("0.4"):
            recommendations.append(
                f"{biggest.category_name} accounts for "
                f"{biggest.percentage_of_total:.0f}% of spending. "
                "Consider setting a stricter budget here."
            )
        
        return SpendingInsights(
            biggest_category=biggest.category_name if biggest else None,
            biggest_category_amount=biggest.total_spent if biggest else Decimal(0),
            most_frequent_category=most_frequent.category_name if most_frequent else None,
            most_frequent_count=most_frequent.transaction_count if most_frequent else 0,
            average_transaction=avg_transaction,
            biggest_transaction_day=None,
            biggest_day_amount=Decimal(0),
            savings_rate=None,
            recommendations=recommendations
        )
    
    def generate_summary_card(self) -> Panel:
        """Generate a quick summary card of current financial status."""
        today = date.today()
        start_of_month = today.replace(day=1)
        
        # This month
        month_summary = self.db.get_monthly_summary(today.year, today.month)
        
        # Last month for comparison
        last_month = today.replace(day=1) - timedelta(days=1)
        last_month_summary = self.db.get_monthly_summary(last_month.year, last_month.month)
        
        # Build content
        content = Text()
        
        content.append("This Month\n", style="bold underline")
        content.append(f"Total: ", style="dim")
        content.append(format_currency(month_summary.total_spent), style="bold yellow")
        content.append(f"  ({month_summary.transaction_count} transactions)\n")
        
        if month_summary.vs_previous_month is not None:
            if month_summary.vs_previous_month > 0:
                content.append(f"vs Last Month: +{month_summary.vs_previous_month:.1f}%", style="red")
            else:
                content.append(f"vs Last Month: {month_summary.vs_previous_month:.1f}%", style="green")
            content.append("\n")
        
        content.append(f"\nTop Category: ", style="dim")
        content.append(month_summary.top_category or "N/A", style="cyan")
        content.append(f"\nDaily Average: ", style="dim")
        content.append(format_currency(month_summary.daily_average), style="green")
        
        # Budget status
        budgets = self.db.get_budgets()
        if budgets:
            total_budget = sum(b.amount for b in budgets if b.category_id is None)
            if total_budget > 0:
                content.append(f"\n\nBudget Status: ", style="bold underline")
                pct = float(month_summary.total_spent / total_budget * 100)
                if pct >= 100:
                    content.append(f"{pct:.0f}% used", style="red")
                elif pct >= 80:
                    content.append(f"{pct:.0f}% used", style="yellow")
                else:
                    content.append(f"{pct:.0f}% used", style="green")
        
        return Panel(content, title="📊 Financial Summary", border_style="blue")
