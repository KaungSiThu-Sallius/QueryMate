import os
import pandas as pd

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
