from prompts import get_prompt
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import os
import pandas as pd
import time
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from utilities import llm_output_clean, validate_sql
from vector_store import store_successful_query, retrieve_similar_queries, check_duplication

load_dotenv()
gemini_key = os.getenv('GEMINI_API_KEY')

root_path = os.getcwd()

conversation_history = []

def get_new_logging_dict():
    """Create fresh logging dictionary for each query."""
    return {
        'user_question': None,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'generated_sql': None,
        'execution_time_ms': 0,
        'retrieved_count': 0,
        'retrieval_time_ms': 0,
        'rag_used': False,
        'turn_number': len(conversation_history) + 1,
        'uses_context': False,
        'status': None,
        'error': None
    }

def logging(log_dict):
    """Save query log to CSV."""
    log_path = os.path.join(root_path, 'data/logs')
    log_file = os.path.join(log_path, 'sql_generation_logs.csv')
    
    os.makedirs(log_path, exist_ok=True)

    logging_df = pd.DataFrame([log_dict])
    if os.path.exists(log_file):
        logging_df.to_csv(log_file, mode='a', header=False, index=False)
    else:
        logging_df.to_csv(log_file, mode='w', header=True, index=False)

def add_to_conversation(question, sql, rows_returned):
    """Add a turn to conversation history (max 3 turns)."""
    turn = {
        "turn": len(conversation_history) + 1,
        "question": question,
        "sql": sql,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rows_returned": rows_returned
    }

    conversation_history.append(turn)

    if len(conversation_history) > 3:
        conversation_history.pop(0)
    

def get_conversation_context():
    """Format conversation history for prompt."""
    if not conversation_history:
        return ""
    
    context = "\n\nPrevious conversation:\n"
    for turn in conversation_history:
        context += f"\nTurn {turn['turn']}:\n"
        context += f"User: \"{turn['question']}\"\n"
        context += f"SQL: {turn['sql']}\n"

    context += "\nNow answer the current question using context from previous turns if needed.\n"
    return context

def needs_context(question):
    """Check if question likely needs conversation context."""
    if not conversation_history:
        return False
    
    context_indicators = ['them', 'it', 'those', 'these', 'that', 'also', 'too', 'same', 'previous']
    question_lower = question.lower()
    
    if len(question.split()) < 5 and len(conversation_history) > 0:
        return True
    
    if any(indicator in question_lower for indicator in context_indicators):
        return True
    
    return False

def clear_conversation():
    """Clear conversation memory."""
    global conversation_history
    conversation_history = []
    print("Conversation cleared - starting fresh")

def generate_sql(user_question):
    """
    Generate SQL from natural language using LLM with RAG and conversation memory.
    
    Parameters:
        user_question (string): Natural language question
        
    Returns:
        tuple: (sql_query string, retrieved_examples list, logging_dict)
    """
    
    logging_dict = get_new_logging_dict()
    logging_dict['user_question'] = user_question
    
    prompt = get_prompt()

    uses_context = needs_context(user_question)
    logging_dict['uses_context'] = uses_context

    retrieved_examples = []
    try:
        start_time = time.time()
        retrieved_examples = retrieve_similar_queries(user_question)
        logging_dict['retrieval_time_ms'] = round((time.time() - start_time) * 1000, 2)
        
        if retrieved_examples:
            print(f"Retrieved {len(retrieved_examples)} similar example(s)")
    except Exception as e:
        print(f"⚠️ Warning: Retrieval failed ({e}), using static examples only")
        retrieved_examples = []

    retrieved_examples_count = len(retrieved_examples)
    logging_dict['retrieved_count'] = retrieved_examples_count
    
    if retrieved_examples_count > 0:
        logging_dict['rag_used'] = True

    try:
        conversation_context = get_conversation_context()
        
        print("🤖 Generating SQL with Gemini...")
        start_time = time.time()

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0,
            max_tokens=2000,
            timeout=None,
            max_retries=2,
            convert_system_message_to_human=True
        )

        output_parser = StrOutputParser()
        chain = prompt | llm | output_parser

        sql = chain.invoke({
            "question": user_question, 
            "retrieved_examples": retrieved_examples, 
            "conversation_context": conversation_context
        })
        
        sql = llm_output_clean(sql)

        end_time = time.time()

        logging_dict['generated_sql'] = sql
        logging_dict['execution_time_ms'] = round((end_time - start_time) * 1000, 2)

        return sql, retrieved_examples, logging_dict

    except Exception as e:
        error_str = str(e)
        print(f"❌ Error generating SQL: {e}")
        
        logging_dict['status'] = 'failed'
        logging_dict['error'] = str(e)
        logging(logging_dict)
        
        return None, retrieved_examples, logging_dict

def ask_database(user_question):
    """
    Complete pipeline: Question → SQL → Execution → Results.
    
    Parameters:
        user_question (string): Natural language question
        
    Returns:
        DataFrame or None
    """

    try:
        sql, retrieved_examples, logging_dict = generate_sql(user_question)
    except Exception as e:
        error_str = str(e)
        
        # Check for rate limit errors
        if "429" in error_str or "quota" in error_str.lower() or "rate limit" in error_str.lower():
            print("\n🚫 API Rate Limit Exceeded!")
            print("Gemini API quota is exhausted. Please wait and try again later.")

            logging_dict = get_new_logging_dict()
            logging_dict['user_question'] = user_question
            logging_dict['status'] = 'failed'
            logging_dict['error'] = "Rate limit exceeded"
            logging(logging_dict)
            return None
        else:
            raise e

    if sql is None:
        print("\n❌ Could not generate SQL. Your question might be ambiguous.")
        print("💡 Please provide more details about which tables or columns you're interested in.")
        return None

    is_valid, error_msg = validate_sql(sql)
    if not is_valid:
        print(f"\n🚫 Validation Error: {error_msg}")
        logging_dict['status'] = 'failed'
        logging_dict['error'] = error_msg
        logging(logging_dict)
        return None
    
    dbname = os.getenv('DB_NAME')
    user = os.getenv('DB_USER')
    password = os.getenv('DB_PASS')
    host = os.getenv('DB_HOST')
    port = os.getenv('DB_PORT')

    engine = create_engine(
        f"postgresql://{user}:{password}@{host}:{port}/{dbname}",
        connect_args={'options': '-c statement_timeout=5000'}
    )
    
    try: 
        with engine.connect() as conn:
            start_time = time.time()
            conn.execute(text("SET statement_timeout = '5s'"))
            df = pd.read_sql(text(sql), conn)
            execution_time = round((time.time() - start_time) * 1000, 2)
            rows_returned = len(df)
            
            if not df.empty:
                print("✅ Query Results:")
                print(df.to_string(index=False))
                print(f"\nReturned {rows_returned} row(s) in {execution_time:.0f}ms")
            else:
                print("⚠️ Query executed successfully but returned no results.")
            
            add_to_conversation(user_question, sql, rows_returned)
            
            logging_dict['status'] = 'success'
            logging_dict['error'] = None
            logging(logging_dict)

            if check_duplication(sql, retrieved_examples):
                store_successful_query(user_question, sql, rows_returned, execution_time)
                print("💾 Query stored in ChromaDB")
            else:
                print("⏭️ Skipped storage - duplicate or very similar query")

            return df
                
    except Exception as e:
        error_str = str(e)
        
        if "canceling statement due to statement timeout" in error_str:
            print("\n⏱️ Query Timeout: Query took longer than 5 seconds.")
            print("💡 Try narrowing your search with date filters or LIMIT clause.")
        elif "column" in error_str.lower() and "does not exist" in error_str.lower():
            print(f"\n❌ Column Error: {error_str}")
            print("💡 The LLM may have referenced a non-existent column.")
        elif "relation" in error_str.lower() and "does not exist" in error_str.lower():
            print(f"\n❌ Table Error: {error_str}")
            print("💡 The LLM may have referenced a non-existent table.")
        else:
            print(f"\n❌ SQL Execution Error: {e}")
        
        print(f"\n📝 Generated SQL was:\n{sql}")
        
        logging_dict['status'] = 'failed'
        logging_dict['error'] = str(e)
        logging(logging_dict)
        
        return None

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 Welcome to QueryMate - AI SQL Assistant")
    print("=" * 60)
    print("\nCommands:")
    print("  • Type your question to query the database")
    print("  • 'clear' or 'reset' - Start new conversation")
    print("  • 'exit' or 'quit' - Exit the program")
    print("\n" + "=" * 60 + "\n")

    while True:
        try:
            user_question = input('💬 Your question: ').strip()
            
            if not user_question:
                print("⚠️ Please enter a question\n")
                continue
            
            if user_question.lower() in ['exit', 'quit', 'q', 'bye']:
                print("\n👋 Goodbye! Thanks for using QueryMate!")
                break
            
            if user_question.lower() in ['clear', 'reset', 'new', 'start over']:
                clear_conversation()
                continue
            
            print()
            ask_database(user_question)
            print("\n" + "-" * 60 + "\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            print("Please try again or type 'exit' to quit.\n")


# Test questions for reference:
# """
# Test Questions:
# 1. "How many customers are there?"
# 2. "Show me 10 customers from Sao Paulo"
# 3. "What are the top 5 product categories?"
# 4. "How many orders in January 2017?"
# 5. "What was total revenue in 2017?"
# 6. "Show average order value by state"
# 7. "Show me sales" (intentionally ambiguous)
# 8. "Show orders from 2025" (no data exists)
# 9. "How many users are there?" (wrong table name)
# 10. "Which customers left 5-star reviews and spent over 500?"

# Multi-turn conversation tests:
# 1. "Show me customers from São Paulo" → "How many of them?"
# 2. "What's total revenue?" → "Show me by state"
# 3. "Top 5 products" → "Show me top 10 instead"
# """