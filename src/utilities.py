import os
import pandas as pd
from sqlalchemy import create_engine

def get_engine():
    return create_engine(
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}",
        connect_args={"options": "-c statement_timeout=5000"},
    )

def validate_sql(sql: str) -> tuple[bool, str]:
    """
    Validate SQL query for safety and basic syntax.
    
    Args:
        sql: SQL query to validate
        
    Returns:
        (is_valid, error_message) tuple
    """
    # Check 1: Empty or None
    if not sql or len(sql.strip()) == 0:
        return False, "Error Retrieveing SQL query"
    
    sql_upper = sql.upper()
    
    # Check 2: Destructive operations
    dangerous_keywords = [
        'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 
        'UPDATE', 'INSERT', 'CREATE', 'GRANT', 'REVOKE'
    ]
    
    for keyword in dangerous_keywords:
        if keyword in sql_upper:
            return False, f"Destructive operation '{keyword}' not allowed"
    
    # Check 3: Must start with SELECT
    if not sql_upper.strip().startswith('SELECT'):
        return False, "Only SELECT queries are allowed"
    
    # Check 4: Must have FROM clause
    if 'FROM' not in sql_upper:
        return False, "Invalid SQL: missing FROM clause"
    
    # Check 5: SQL injection patterns
    suspicious_patterns = ['--', '/*', '*/', 'EXEC', 'EXECUTE']
    for pattern in suspicious_patterns:
        if pattern in sql_upper:
            return False, f"Suspicious pattern '{pattern}' detected"
    
    return True, ""


def llm_output_clean(sql):
    cleaned_sql = str.strip(sql)

    if cleaned_sql[:3] == "```":
        if cleaned_sql[:6] == "```sql":
            cleaned_sql = cleaned_sql[6:]
        else:
            cleaned_sql = cleaned_sql[3:]
    if cleaned_sql[-3:] == "```":
        cleaned_sql = cleaned_sql[:-3]
    return str.strip(cleaned_sql)


def detect_chart_type(df: pd.DataFrame, sql: str):
    """Return (chart_type, config) for the given result set."""
    if df is None or df.empty:
        return "none", {}

    rows  = len(df)
    num   = df.select_dtypes(include="number").columns.tolist()
    cat   = [c for c in df.columns if c not in num]
    sql_u = (sql or "").upper()

    # Single scalar value
    if rows == 1 and len(df.columns) == 1:
        return "metric", {}

    # No numeric → table
    if not num or rows > 100:
        return "table", {}

    # Time-series
    DATE_KW = ["date", "month", "year", "week", "day", "time", "period", "quarter"]
    date_col = next((c for c in df.columns if any(k in c.lower() for k in DATE_KW)), None)
    if date_col and num and rows > 1:
        return "line", {"x": date_col, "y": num[0], "title": f"{num[0]} over time"}
    elif date_col and num and rows == 1:
        return "bar", {"x": date_col, "y": num[0], "title": f"{num[0]} (Single Entry)"}

    # Two-column
    if len(df.columns) == 2 and cat and num:
        if "ORDER BY" in sql_u and "LIMIT" in sql_u and rows <= 20:
            return "hbar", {"x": num[0], "y": cat[0], "title": f"Top {rows} by {num[0]}"}
        if rows <= 30:
            return "bar", {"x": cat[0], "y": num[0], "title": f"{num[0]} by {cat[0]}"}

    return "table", {}
