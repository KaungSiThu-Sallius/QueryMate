def llm_output_clean(sql):
    cleaned_sql = str.strip(sql)

    if cleaned_sql[:3] == "```":
        if cleaned_sql[:6] == "```sql":
            cleaned_sql = cleaned_sql[6:]
        else:
            cleaned_sql = cleaned_sql[3:]
    return str.strip(cleaned_sql)