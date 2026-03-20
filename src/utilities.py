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

def anayze_logs():
    root_path = os.getcwd()
    logs_path = os.path.join(root_path, 'data/logs')
    logs_df = pd.read_csv(os.path.join(logs_path, 'sql_generation_logs.csv'))

    total_queries = len(logs_df)

    with_rag_retrieved_df = logs_df[logs_df['rag_used'] == True]
    with_rag_retrieved_len = len(with_rag_retrieved_df)
    with_rag_retrieved_len_percent = round((with_rag_retrieved_len/total_queries) * 100,2)
    with_rag_retrieved = (with_rag_retrieved_len, with_rag_retrieved_len_percent)

    without_rag_retrieved_df = logs_df[logs_df['rag_used'] == False]
    without_rag_retrieved_len = len(without_rag_retrieved_df)
    without_rag_retrieved_len_percent = round((without_rag_retrieved_len/total_queries) * 100,2)
    without_rag_retrieved = (without_rag_retrieved_len, without_rag_retrieved_len_percent)

    avg_examples_retrieved = round(float(logs_df['retrieved_count'].mean()),2)

    no_rag = logs_df[logs_df['retrieved_count'] == 0]
    low_rag = logs_df[(logs_df['retrieved_count'] >= 1) & (logs_df['retrieved_count'] <= 2)]
    high_rag = logs_df[logs_df['retrieved_count'] >= 3]

    success_no_rag = float((no_rag['status'] == 'success').sum() / len(no_rag) * 100 if len(no_rag) > 0 else 0)
    success_low_rag = float((low_rag['status'] == 'success').sum() / len(low_rag) * 100 if len(low_rag) > 0 else 0)
    success_high_rag = float((high_rag['status'] == 'success').sum() / len(high_rag) * 100 if len(high_rag) > 0 else 0)

    rag_improvement = success_high_rag - success_no_rag

    dict = {
        'total_queries': total_queries, 
        'with_rag_retrieved': with_rag_retrieved, 
        'without_rag_retrieved': without_rag_retrieved, 
        'success_no_rag': success_no_rag, 
        'avg_examples_retrieved': avg_examples_retrieved,
        'success_low_rag': success_low_rag, 
        'success_high_rag': success_high_rag, 
        'rag_improvement': rag_improvement
    }
    
    df = pd.DataFrame.from_dict([dict])
    df.to_csv(os.path.join(logs_path, 'log_analysis.csv'))
    print("Successfully saved logs anaysis file to logs directory.")
