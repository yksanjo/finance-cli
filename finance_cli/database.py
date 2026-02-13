"""Database layer for Finance CLI - SQLite with local storage."""
import sqlite3
import os
import json
from datetime import datetime, date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import List, Optional, Tuple
from contextlib import contextmanager

from .models import Expense, Category, Budget, MonthlySummary, CategorySummary


class Database:
    """SQLite database manager for local finance data."""
    
    DEFAULT_CATEGORIES = [
        ("Food & Dining", "Groceries, restaurants, takeout", "#ef4444", None),
        ("Transportation", "Gas, public transit, rideshare", "#3b82f6", None),
        ("Housing", "Rent, mortgage, utilities", "#10b981", None),
        ("Entertainment", "Movies, games, hobbies", "#f59e0b", None),
        ("Shopping", "Clothing, electronics, gifts", "#8b5cf6", None),
        ("Health", "Medical, pharmacy, fitness", "#ec4899", None),
        ("Personal", "Haircuts, subscriptions, etc.", "#6366f1", None),
        ("Education", "Books, courses, training", "#14b8a6", None),
        ("Travel", "Flights, hotels, vacations", "#f97316", None),
        ("Savings", "Investments, emergency fund", "#22c55e", None),
    ]
    
    def __init__(self, data_dir: Optional[str] = None):
        """Initialize database with optional custom data directory."""
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            # Store in user's home directory for privacy
            self.data_dir = Path.home() / ".finance-cli"
        
        self.data_dir.mkdir(exist_ok=True)
        self.db_path = self.data_dir / "finance.db"
        self._init_db()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Categories table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    budget_limit DECIMAL(10, 2),
                    color TEXT DEFAULT '#6366f1',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Expenses table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount DECIMAL(10, 2) NOT NULL,
                    category_id INTEGER,
                    description TEXT,
                    date DATE NOT NULL,
                    payment_method TEXT DEFAULT 'cash',
                    tags TEXT DEFAULT '[]',
                    is_recurring BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
                )
            """)
            
            # Budgets table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS budgets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER,
                    amount DECIMAL(10, 2) NOT NULL,
                    period TEXT DEFAULT 'monthly',
                    start_date DATE,
                    end_date DATE,
                    alert_threshold INTEGER DEFAULT 80,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
                )
            """)
            
            # Indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_date_category ON expenses(date, category_id)")
            
            # Insert default categories if empty
            cursor.execute("SELECT COUNT(*) FROM categories")
            if cursor.fetchone()[0] == 0:
                cursor.executemany(
                    """INSERT INTO categories (name, description, color, budget_limit) 
                       VALUES (?, ?, ?, ?)""",
                    self.DEFAULT_CATEGORIES
                )
    
    # === Expense Operations ===
    
    def add_expense(self, expense: Expense) -> int:
        """Add a new expense and return its ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO expenses (amount, category_id, description, date, 
                                    payment_method, tags, is_recurring)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                float(expense.amount),
                expense.category_id,
                expense.description,
                expense.date.isoformat(),
                expense.payment_method,
                json.dumps(expense.tags),
                expense.is_recurring
            ))
            return cursor.lastrowid
    
    def get_expense(self, expense_id: int) -> Optional[Expense]:
        """Get a single expense by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.*, c.name as category_name 
                FROM expenses e
                LEFT JOIN categories c ON e.category_id = c.id
                WHERE e.id = ?
            """, (expense_id,))
            row = cursor.fetchone()
            return Expense.from_row(tuple(row)) if row else None
    
    def update_expense(self, expense: Expense) -> bool:
        """Update an existing expense."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE expenses 
                SET amount = ?, category_id = ?, description = ?, date = ?,
                    payment_method = ?, tags = ?, is_recurring = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                float(expense.amount),
                expense.category_id,
                expense.description,
                expense.date.isoformat(),
                expense.payment_method,
                json.dumps(expense.tags),
                expense.is_recurring,
                expense.id
            ))
            return cursor.rowcount > 0
    
    def delete_expense(self, expense_id: int) -> bool:
        """Delete an expense by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
            return cursor.rowcount > 0
    
    def list_expenses(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Expense]:
        """List expenses with optional filtering."""
        query = """
            SELECT e.*, c.name as category_name 
            FROM expenses e
            LEFT JOIN categories c ON e.category_id = c.id
            WHERE 1=1
        """
        params = []
        
        if start_date:
            query += " AND e.date >= ?"
            params.append(start_date.isoformat())
        if end_date:
            query += " AND e.date <= ?"
            params.append(end_date.isoformat())
        if category_id:
            query += " AND e.category_id = ?"
            params.append(category_id)
        
        query += " ORDER BY e.date DESC, e.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [Expense.from_row(tuple(row)) for row in cursor.fetchall()]
    
    def search_expenses(self, keyword: str, limit: int = 50) -> List[Expense]:
        """Search expenses by description."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.*, c.name as category_name 
                FROM expenses e
                LEFT JOIN categories c ON e.category_id = c.id
                WHERE e.description LIKE ?
                ORDER BY e.date DESC LIMIT ?
            """, (f"%{keyword}%", limit))
            return [Expense.from_row(tuple(row)) for row in cursor.fetchall()]
    
    # === Category Operations ===
    
    def get_categories(self) -> List[Category]:
        """Get all categories."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM categories ORDER BY name")
            return [Category.from_row(tuple(row)) for row in cursor.fetchall()]
    
    def get_category_by_name(self, name: str) -> Optional[Category]:
        """Get category by name (case-insensitive)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM categories WHERE LOWER(name) = LOWER(?)", 
                (name,)
            )
            row = cursor.fetchone()
            return Category.from_row(tuple(row)) if row else None
    
    def add_category(self, category: Category) -> int:
        """Add a new category."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO categories (name, description, budget_limit, color)
                VALUES (?, ?, ?, ?)
            """, (
                category.name,
                category.description,
                float(category.budget_limit) if category.budget_limit else None,
                category.color
            ))
            return cursor.lastrowid
    
    def update_category(self, category: Category) -> bool:
        """Update a category."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE categories 
                SET name = ?, description = ?, budget_limit = ?, color = ?
                WHERE id = ?
            """, (
                category.name,
                category.description,
                float(category.budget_limit) if category.budget_limit else None,
                category.color,
                category.id
            ))
            return cursor.rowcount > 0
    
    def delete_category(self, category_id: int, reassign_to: Optional[int] = None) -> bool:
        """Delete a category and optionally reassign its expenses."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if reassign_to:
                cursor.execute(
                    "UPDATE expenses SET category_id = ? WHERE category_id = ?",
                    (reassign_to, category_id)
                )
            
            cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
            return cursor.rowcount > 0
    
    # === Budget Operations ===
    
    def set_budget(self, budget: Budget) -> int:
        """Set or update a budget."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if budget exists
            cursor.execute(
                "SELECT id FROM budgets WHERE category_id IS ?",
                (budget.category_id,)
            )
            existing = cursor.fetchone()
            
            if existing:
                cursor.execute("""
                    UPDATE budgets 
                    SET amount = ?, period = ?, start_date = ?, 
                        end_date = ?, alert_threshold = ?
                    WHERE id = ?
                """, (
                    float(budget.amount),
                    budget.period,
                    budget.start_date.isoformat() if budget.start_date else None,
                    budget.end_date.isoformat() if budget.end_date else None,
                    budget.alert_threshold,
                    existing[0]
                ))
                return existing[0]
            else:
                cursor.execute("""
                    INSERT INTO budgets (category_id, amount, period, start_date, end_date, alert_threshold)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    budget.category_id,
                    float(budget.amount),
                    budget.period,
                    budget.start_date.isoformat() if budget.start_date else None,
                    budget.end_date.isoformat() if budget.end_date else None,
                    budget.alert_threshold
                ))
                return cursor.lastrowid
    
    def get_budgets(self) -> List[Budget]:
        """Get all budgets."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT b.*, c.name as category_name 
                FROM budgets b
                LEFT JOIN categories c ON b.category_id = c.id
                ORDER BY b.category_id IS NULL DESC, c.name
            """)
            return [Budget.from_row(tuple(row)) for row in cursor.fetchall()]
    
    # === Analytics & Reports ===
    
    def get_spending_by_category(
        self, 
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[CategorySummary]:
        """Get spending summary by category."""
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date.replace(day=1)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get total spent
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM expenses
                WHERE date BETWEEN ? AND ?
            """, (start_date.isoformat(), end_date.isoformat()))
            total = Decimal(str(cursor.fetchone()[0] or 0))
            
            # Get per-category breakdown
            cursor.execute("""
                SELECT 
                    c.id,
                    c.name,
                    c.color,
                    COALESCE(SUM(e.amount), 0) as total,
                    COUNT(e.id) as count,
                    c.budget_limit
                FROM categories c
                LEFT JOIN expenses e ON c.id = e.category_id 
                    AND e.date BETWEEN ? AND ?
                GROUP BY c.id
                HAVING total > 0
                ORDER BY total DESC
            """, (start_date.isoformat(), end_date.isoformat()))
            
            results = []
            for row in cursor.fetchall():
                cat_total = Decimal(str(row[3]))
                budget_limit = Decimal(str(row[5])) if row[5] else None
                budget_used = None
                if budget_limit and budget_limit > 0:
                    budget_used = float(cat_total / budget_limit * 100)
                
                results.append(CategorySummary(
                    category_id=row[0],
                    category_name=row[1],
                    category_color=row[2] or "#6366f1",
                    total_spent=cat_total,
                    transaction_count=row[4],
                    percentage_of_total=float(cat_total / total * 100) if total > 0 else 0,
                    budget_limit=budget_limit,
                    budget_used_percentage=budget_used
                ))
            
            return results
    
    def get_monthly_summary(self, year: int, month: int) -> MonthlySummary:
        """Get summary for a specific month."""
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Current month totals
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0), COUNT(*)
                FROM expenses
                WHERE date BETWEEN ? AND ?
            """, (start_date.isoformat(), end_date.isoformat()))
            total, count = cursor.fetchone()
            total = Decimal(str(total or 0))
            
            # Category breakdown
            cursor.execute("""
                SELECT c.name, COALESCE(SUM(e.amount), 0)
                FROM categories c
                LEFT JOIN expenses e ON c.id = e.category_id 
                    AND e.date BETWEEN ? AND ?
                GROUP BY c.id
                HAVING SUM(e.amount) > 0
                ORDER BY SUM(e.amount) DESC
            """, (start_date.isoformat(), end_date.isoformat()))
            
            breakdown = {row[0]: Decimal(str(row[1])) for row in cursor.fetchall()}
            top_category = max(breakdown, key=breakdown.get) if breakdown else ""
            
            # Previous month for comparison
            prev_start = start_date.replace(day=1) - timedelta(days=1)
            prev_start = prev_start.replace(day=1)
            if month == 1:
                prev_start = date(year - 1, 12, 1)
            
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0)
                FROM expenses
                WHERE date >= ? AND date < ?
            """, (prev_start.isoformat(), start_date.isoformat()))
            prev_total = Decimal(str(cursor.fetchone()[0] or 0))
            
            vs_prev = None
            if prev_total > 0:
                vs_prev = float((total - prev_total) / prev_total * 100)
            
            days_in_month = (end_date - start_date).days + 1
            daily_avg = total / days_in_month if days_in_month > 0 else Decimal(0)
            
            return MonthlySummary(
                year=year,
                month=month,
                total_spent=total,
                transaction_count=count,
                category_breakdown=breakdown,
                daily_average=daily_avg,
                top_category=top_category,
                vs_previous_month=vs_prev
            )
    
    def get_yearly_summary(self, year: int) -> List[MonthlySummary]:
        """Get monthly summaries for a year."""
        summaries = []
        for month in range(1, 13):
            try:
                summaries.append(self.get_monthly_summary(year, month))
            except Exception:
                pass
        return summaries
    
    # === Data Export ===
    
    def export_to_csv(self, filepath: str, start_date: Optional[date] = None, 
                      end_date: Optional[date] = None):
        """Export expenses to CSV file."""
        import csv
        
        expenses = self.list_expenses(start_date, end_date, limit=10000)
        
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Date', 'Category', 'Description', 'Amount', 
                           'Payment Method', 'Tags'])
            for e in expenses:
                writer.writerow([
                    e.date.isoformat(),
                    e.category_name,
                    e.description,
                    float(e.amount),
                    e.payment_method,
                    ', '.join(e.tags)
                ])
    
    def export_to_json(self, filepath: str, start_date: Optional[date] = None,
                       end_date: Optional[date] = None):
        """Export expenses to JSON file."""
        expenses = self.list_expenses(start_date, end_date, limit=10000)
        
        data = {
            "exported_at": datetime.now().isoformat(),
            "count": len(expenses),
            "expenses": [
                {
                    "id": e.id,
                    "date": e.date.isoformat(),
                    "category": e.category_name,
                    "description": e.description,
                    "amount": float(e.amount),
                    "payment_method": e.payment_method,
                    "tags": e.tags,
                    "is_recurring": e.is_recurring
                }
                for e in expenses
            ]
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_stats(self) -> dict:
        """Get database statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM expenses")
            total_count, total_amount = cursor.fetchone()
            
            cursor.execute("SELECT COUNT(*) FROM categories")
            category_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT MIN(date), MAX(date) FROM expenses")
            date_range = cursor.fetchone()
            
            return {
                "total_expenses": total_count,
                "total_amount": Decimal(str(total_amount or 0)),
                "total_categories": category_count,
                "first_expense_date": date_range[0],
                "last_expense_date": date_range[1],
                "database_path": str(self.db_path),
                "database_size": os.path.getsize(self.db_path)
            }
