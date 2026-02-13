"""Chart generation for Finance CLI."""
from typing import List, Optional, Dict
from decimal import Decimal
from datetime import date, timedelta
import io

from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.table import Table

from .models import CategorySummary, MonthlySummary


class ChartRenderer:
    """Render charts in the terminal using ASCII/Unicode."""
    
    BLOCK_CHARS = ["█", "▉", "▊", "▋", "▌", "▍", "▎", "▏"]
    
    def __init__(self):
        self.console = Console()
    
    def render_bar_chart(
        self, 
        data: Dict[str, Decimal], 
        title: str = "",
        max_width: int = 40,
        show_values: bool = True,
        value_format: str = "${:.2f}"
    ) -> Table:
        """Render a horizontal bar chart as a Rich Table."""
        if not data:
            return Table(title="No data")
        
        max_value = max(data.values()) if data else Decimal(0)
        
        table = Table(
            title=title,
            show_header=True,
            header_style="bold magenta",
            box=None,
            pad_edge=False
        )
        table.add_column("Category", style="cyan", width=20)
        table.add_column("Chart", style="green")
        if show_values:
            table.add_column("Amount", style="yellow", justify="right", width=12)
            table.add_column("%", style="dim", justify="right", width=6)
        
        total = sum(data.values())
        
        for label, value in data.items():
            if max_value > 0:
                ratio = float(value / max_value)
                filled = int(ratio * max_width)
                remainder = int((ratio * max_width - filled) * 8)
                
                bar = "█" * filled
                if remainder > 0 and filled < max_width:
                    bar += self.BLOCK_CHARS[8 - remainder]
                
                bar_style = "green" if value < max_value * Decimal("0.5") else "yellow" if value < max_value * Decimal("0.8") else "red"
                bar = f"[{bar_style}]{bar}[/]"
            else:
                bar = ""
            
            percentage = (value / total * 100) if total > 0 else Decimal(0)
            
            if show_values:
                table.add_row(
                    label[:20],
                    bar,
                    value_format.format(float(value)),
                    f"{percentage:.1f}%"
                )
            else:
                table.add_row(label[:20], bar)
        
        return table
    
    def render_pie_chart(
        self,
        data: Dict[str, Decimal],
        title: str = "",
        diameter: int = 20
    ) -> Panel:
        """Render a simple pie chart representation."""
        if not data:
            return Panel("No data", title=title)
        
        # Sort and limit to top 5, group rest as "Other"
        sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)
        
        if len(sorted_items) > 5:
            top_items = sorted_items[:5]
            other_value = sum(v for _, v in sorted_items[5:])
            if other_value > 0:
                top_items.append(("Other", other_value))
        else:
            top_items = sorted_items
        
        total = sum(v for _, v in top_items)
        
        # Create legend with blocks
        colors = ["red", "green", "blue", "yellow", "magenta", "cyan"]
        lines = []
        
        for i, (label, value) in enumerate(top_items):
            percentage = float(value / total * 100)
            color = colors[i % len(colors)]
            block = f"[on {color}]  [/]"
            lines.append(f"{block} {label[:25]:25} {percentage:5.1f}%  ${float(value):,.2f}")
        
        content = "\n".join(lines)
        return Panel(content, title=title, border_style="blue")
    
    def render_sparkline(
        self,
        values: List[Decimal],
        title: str = "",
        width: int = 60
    ) -> Panel:
        """Render a sparkline chart."""
        if not values:
            return Panel("No data", title=title)
        
        # Sparkline characters
        bars = "▁▂▃▄▅▆▇█"
        
        max_val = max(values) if values else Decimal(1)
        min_val = min(values) if values else Decimal(0)
        
        if max_val == min_val:
            max_val = min_val + Decimal(1)
        
        # Sample or interpolate to fit width
        if len(values) > width:
            step = len(values) / width
            sampled = [values[int(i * step)] for i in range(width)]
        else:
            sampled = values
        
        line = ""
        for v in sampled:
            if max_val > min_val:
                ratio = float((v - min_val) / (max_val - min_val))
            else:
                ratio = 0
            idx = min(int(ratio * (len(bars) - 1)), len(bars) - 1)
            line += bars[idx]
        
        stats = f"Min: ${float(min_val):,.2f} | Max: ${float(max_val):,.2f} | Avg: ${float(sum(values)/len(values)):,.2f}"
        
        content = f"{line}\n[dim]{stats}[/]"
        return Panel(content, title=title, border_style="green")
    
    def render_category_breakdown(
        self,
        summaries: List[CategorySummary],
        title: str = "Spending by Category"
    ) -> Table:
        """Render category breakdown with budget indicators."""
        table = Table(
            title=title,
            show_header=True,
            header_style="bold magenta"
        )
        
        table.add_column("Category", style="cyan")
        table.add_column("Amount", justify="right", style="yellow")
        table.add_column("%", justify="right", style="dim")
        table.add_column("Transactions", justify="right", style="blue")
        table.add_column("Budget", justify="right", style="green")
        table.add_column("Status", style="white")
        
        for s in summaries:
            # Budget status indicator
            if s.budget_limit:
                budget_str = f"${float(s.budget_limit):,.0f}"
                if s.budget_used_percentage:
                    if s.budget_used_percentage >= 100:
                        status = "[red]● Over[/]"
                    elif s.budget_used_percentage >= 80:
                        status = f"[yellow]● {s.budget_used_percentage:.0f}%[/]"
                    else:
                        status = f"[green]● {s.budget_used_percentage:.0f}%[/]"
                else:
                    status = "-"
            else:
                budget_str = "-"
                status = "-"
            
            table.add_row(
                s.category_name,
                f"${float(s.total_spent):,.2f}",
                f"{s.percentage_of_total:.1f}%",
                str(s.transaction_count),
                budget_str,
                status
            )
        
        return table
    
    def render_monthly_comparison(
        self,
        summaries: List[MonthlySummary],
        title: str = "Monthly Spending"
    ) -> Table:
        """Render monthly spending comparison."""
        table = Table(
            title=title,
            show_header=True,
            header_style="bold magenta"
        )
        
        table.add_column("Month", style="cyan")
        table.add_column("Total", justify="right", style="yellow")
        table.add_column("Transactions", justify="right", style="blue")
        table.add_column("Daily Avg", justify="right", style="green")
        table.add_column("vs Prev", justify="right")
        table.add_column("Top Category", style="magenta")
        
        for s in summaries:
            month_name = date(s.year, s.month, 1).strftime("%b %Y")
            
            if s.vs_previous_month is not None:
                if s.vs_previous_month > 0:
                    vs_str = f"[red]↑ {s.vs_previous_month:.1f}%[/]"
                else:
                    vs_str = f"[green]↓ {abs(s.vs_previous_month):.1f}%[/]"
            else:
                vs_str = "-"
            
            table.add_row(
                month_name,
                f"${float(s.total_spent):,.2f}",
                str(s.transaction_count),
                f"${float(s.daily_average):,.2f}",
                vs_str,
                s.top_category[:20] if s.top_category else "-"
            )
        
        return table
    
    def render_budget_overview(
        self,
        budgets: List,
        actual_spending: Dict[int, Decimal],
        title: str = "Budget Overview"
    ) -> Table:
        """Render budget vs actual spending."""
        table = Table(
            title=title,
            show_header=True,
            header_style="bold magenta"
        )
        
        table.add_column("Budget", style="cyan")
        table.add_column("Limit", justify="right", style="green")
        table.add_column("Spent", justify="right", style="yellow")
        table.add_column("Remaining", justify="right")
        table.add_column("Progress", min_width=20)
        
        for budget in budgets:
            spent = actual_spending.get(budget.category_id or 0, Decimal(0))
            remaining = budget.amount - spent
            pct = float(spent / budget.amount * 100) if budget.amount > 0 else 0
            
            # Progress bar
            bar_width = 20
            filled = min(int(pct / 100 * bar_width), bar_width)
            
            if pct >= 100:
                color = "red"
                bar_color = "on red"
            elif pct >= 80:
                color = "yellow"
                bar_color = "on yellow"
            else:
                color = "green"
                bar_color = "on green"
            
            bar = f"[{bar_color}]{' ' * filled}[/]{' ' * (bar_width - filled)}"
            
            table.add_row(
                budget.category_name,
                f"${float(budget.amount):,.2f}",
                f"${float(spent):,.2f}",
                f"[{color}]${float(remaining):,.2f}[/]",
                f"{bar} {pct:.0f}%"
            )
        
        return table


def format_currency(amount: Decimal) -> str:
    """Format amount as currency string."""
    return f"${amount:,.2f}"


def get_trend_indicator(current: Decimal, previous: Optional[Decimal]) -> str:
    """Get trend indicator comparing current to previous value."""
    if previous is None or previous == 0:
        return "→"
    
    pct_change = (current - previous) / previous * 100
    
    if pct_change > 5:
        return "↑"
    elif pct_change < -5:
        return "↓"
    else:
        return "→"
