import chromadb
import os
import time
import uuid

root_path = os.getcwd()
chroma_db_path = os.path.join(root_path, 'data/chroma_db')

chroma_client = chromadb.PersistentClient(path=chroma_db_path)
collection = chroma_client.get_or_create_collection(name='successful_queries')

def categorize_query(sql):
    sql_upper = sql.upper()

    if "DATE_TRUNC" in sql_upper or 'extract' in sql_upper:
        return "TIME_SERIES"
    elif "ORDER BY" in sql_upper and "LIMIT" in sql_upper:
        return "RANKING"
    elif "JOIN" in sql_upper:
        return "JOIN"
    elif "GROUP BY" in sql_upper:
        return "GROUP_BY"
    elif "SUM(" in sql_upper or "AVG(" in sql_upper or "MAX(" in sql_upper or "MIN(" in sql_upper:
        return "AGGREGATION"
    elif "COUNT(*)" in sql_upper:
        return "COUNT"
    else:
        return "FILTER"

def store_successful_query(question: str, sql: str, rows_returned: int, execution_time: float):
    unique_id = str(uuid.uuid4())

    cateogry = categorize_query(sql)

    collection.add(
        ids = [unique_id],
        documents = [question],
        metadatas = [{
            "sql": sql,
            "query_category": cateogry,
            "rows_returned": rows_returned,
            "execution_time": execution_time,
            "timestamp": time.time()
        }]
    )
    print(f"Successfully added query to ChromaDB with ID: {unique_id}")


def retrieve_similar_queries(user_question: str):
    results = collection.query(
        query_texts=[user_question],
        n_results=3
    )
    
    # print(results['metadatas'][0][0]['sql'])
    questions = results['documents'][0]
    meta_data = results['metadatas'][0]
    similarities = results['distances'][0]
    results_list = []

    for i in range(len(questions)):
        if similarities[i] < 2.0:
            results_list.append(
                {
                    'question': questions[i],
                    'sql': meta_data[i]['sql'],
                    'similarity_score': similarities[i]
                }
            )

    return results_list

def check_duplication(sql, retrieved_examples):
    should_store = True
    if retrieved_examples and len(retrieved_examples) > 0:
        # Check first result's similarity
        first_result = retrieved_examples[0]
        similarity_score = first_result.get('similarity_score', 1.0)
        eg_sql = first_result.get('sql', None)
        
        if similarity_score < 0.3 or eg_sql == sql:
            print(f"⏭️ Skipping storage - very similar to existing query!")
            should_store = False
    return should_store


