import chromadb
import os
import time
import uuid

root_path = os.getcwd()
chroma_db_path = os.path.join(root_path, 'data/chroma_db')

chroma_client = chromadb.PersistentClient(path=chroma_db_path)
collection = chroma_client.get_or_create_collection(name='successful_queries')

def store_successful_query(question: str, sql: str, rows_returned: int, execution_time: float):
    unique_id = str(uuid.uuid4())

    collection.add(
        ids = [unique_id],
        documents = [question],
        metadatas = [{
            "sql": sql,
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
