"""Data models for Finance CLI."""
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal, InvalidOperation
import json


@dataclass
class Category:
    """Expense category with optional budget limit."""
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    budget_limit: Optional[Decimal] = None
    color: str = "#6366f1"  # Default indigo color
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_row(cls, row: tuple) -> "Category":
        """Create Category from database row."""
        return cls(
            id=row[0],
            name=row[1],
            description=row[2] or "",
            budget_limit=Decimal(str(row[3])) if row[3] else None,
            color=row[4] or "#6366f1",
            created_at=datetime.fromisoformat(row[5]) if row[5] else None
        )


@dataclass
class Expense:
    """Individual expense transaction."""
    id: Optional[int] = None
    amount: Decimal = Decimal("0")
    category_id: Optional[int] = None
    category_name: str = ""  # Joined field
    description: str = ""
    date: date = field(default_factory=date.today)
    payment_method: str = ""  # cash, card, transfer, etc.
    tags: List[str] = field(default_factory=list)
    is_recurring: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_row(cls, row: tuple) -> "Expense":
        """Create Expense from database row.
        
        Expected row structure from SELECT e.*, c.name as category_name:
        id, amount, category_id, description, date, payment_method, tags, 
        is_recurring, created_at, updated_at, category_name
        """
        return cls(
            id=row[0],
            amount=Decimal(str(row[1])),
            category_id=row[2],
            description=row[3] or "",
            date=date.fromisoformat(row[4]) if row[4] else date.today(),
            payment_method=row[5] or "",
            tags=json.loads(row[6]) if row[6] else [],
            is_recurring=bool(row[7]),
            created_at=datetime.fromisoformat(row[8]) if row[8] else None,
            updated_at=datetime.fromisoformat(row[9]) if row[9] else None,
            category_name=row[10] if len(row) > 10 and row[10] else "Uncategorized"
        )


@dataclass
class Budget:
    """Budget setting for a category or overall."""
    id: Optional[int] = None
    category_id: Optional[int] = None  # None for overall budget
    category_name: str = ""  # Joined field
    amount: Decimal = Decimal("0")
    period: str = "monthly"  # daily, weekly, monthly, yearly
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    alert_threshold: int = 80  # Alert when spending reaches % of budget
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_row(cls, row: tuple) -> "Budget":
        """Create Budget from database row.
        
        Expected row structure from SELECT b.*, c.name as category_name:
        id, category_id, amount, period, start_date, end_date, 
        alert_threshold, created_at, category_name
        """
        # Handle amount parsing safely
        try:
            amount = Decimal(str(row[2])) if row[2] is not None else Decimal("0")
        except (InvalidOperation, ValueError):
            amount = Decimal("0")
        
        return cls(
            id=row[0],
            category_id=row[1],
            amount=amount,
            period=row[3] or "monthly",
            start_date=date.fromisoformat(row[4]) if row[4] else None,
            end_date=date.fromisoformat(row[5]) if row[5] else None,
            alert_threshold=row[6] if row[6] is not None else 80,
            created_at=datetime.fromisoformat(row[7]) if row[7] else None,
            category_name=row[8] if len(row) > 8 and row[8] else "Overall"
        )


@dataclass
class MonthlySummary:
    """Monthly spending summary."""
    year: int
    month: int
    total_spent: Decimal
    transaction_count: int
    category_breakdown: dict = field(default_factory=dict)
    daily_average: Decimal = Decimal("0")
    top_category: str = ""
    vs_previous_month: Optional[float] = None  # Percentage change


@dataclass
class CategorySummary:
    """Category spending summary."""
    category_id: int
    category_name: str
    category_color: str
    total_spent: Decimal
    transaction_count: int
    percentage_of_total: float
    budget_limit: Optional[Decimal] = None
    budget_used_percentage: Optional[float] = None
