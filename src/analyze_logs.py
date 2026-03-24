import os
import pandas as pd
from datetime import datetime

def analyze_logs():
    """Analyze SQL generation logs and create comprehensive metrics report."""
    root_path = os.getcwd()
    logs_path = os.path.join(root_path, 'data/logs')
    logs_file = os.path.join(logs_path, 'sql_generation_logs.csv')
    
    if not os.path.exists(logs_file):
        print("❌ No log file found. Run some queries first!")
        return None
    
    logs_df = pd.read_csv(logs_file)
    
    if len(logs_df) == 0:
        print("⚠️ Log file is empty. No queries to analyze.")
        return None
    
    # === Overall Statistics ===
    total_queries = len(logs_df)
    successful_queries = len(logs_df[logs_df['status'] == 'success'])
    failed_queries = len(logs_df[logs_df['status'] == 'failed'])
    overall_success_rate = round((successful_queries / total_queries) * 100, 2)
    
    # === RAG Usage ===
    with_rag_df = logs_df[logs_df['rag_used'] == True]
    with_rag_count = len(with_rag_df)
    with_rag_percent = round((with_rag_count / total_queries) * 100, 2)
    
    without_rag_df = logs_df[logs_df['rag_used'] == False]
    without_rag_count = len(without_rag_df)
    without_rag_percent = round((without_rag_count / total_queries) * 100, 2)
    
    avg_examples_retrieved = round(logs_df['retrieved_count'].mean(), 2)
    avg_retrieval_time = round(logs_df['retrieval_time_ms'].mean(), 2)
    
    # === RAG Impact on Accuracy ===
    no_rag = logs_df[logs_df['retrieved_count'] == 0]
    low_rag = logs_df[(logs_df['retrieved_count'] >= 1) & (logs_df['retrieved_count'] <= 2)]
    high_rag = logs_df[logs_df['retrieved_count'] >= 3]
    
    success_no_rag = round((no_rag['status'] == 'success').sum() / len(no_rag) * 100, 2) if len(no_rag) > 0 else 0
    success_low_rag = round((low_rag['status'] == 'success').sum() / len(low_rag) * 100, 2) if len(low_rag) > 0 else 0
    success_high_rag = round((high_rag['status'] == 'success').sum() / len(high_rag) * 100, 2) if len(high_rag) > 0 else 0
    
    rag_improvement = round(success_high_rag - success_no_rag, 2)
    
    # === Performance Metrics ===
    avg_generation_time = round(logs_df['execution_time_ms'].mean(), 2)
    min_generation_time = round(logs_df['execution_time_ms'].min(), 2)
    max_generation_time = round(logs_df['execution_time_ms'].max(), 2)
    
    # === Conversation Metrics  ===
    has_conversation_data = 'turn_number' in logs_df.columns
    if has_conversation_data:
        total_conversations = logs_df['turn_number'].max() if 'turn_number' in logs_df.columns else 0
        avg_conversation_length = round(logs_df.groupby('timestamp')['turn_number'].max().mean(), 2) if total_conversations > 0 else 0
        
        turn_1 = logs_df[logs_df['turn_number'] == 1]
        turn_2 = logs_df[logs_df['turn_number'] == 2]
        turn_3_plus = logs_df[logs_df['turn_number'] >= 3]
        
        turn_1_success = round((turn_1['status'] == 'success').sum() / len(turn_1) * 100, 2) if len(turn_1) > 0 else 0
        turn_2_success = round((turn_2['status'] == 'success').sum() / len(turn_2) * 100, 2) if len(turn_2) > 0 else 0
        turn_3_success = round((turn_3_plus['status'] == 'success').sum() / len(turn_3_plus) * 100, 2) if len(turn_3_plus) > 0 else 0
        
        context_used = len(logs_df[logs_df.get('uses_context', False) == True])
        context_used_percent = round((context_used / total_queries) * 100, 2)
    else:
        total_conversations = 0
        avg_conversation_length = 0
        turn_1_success = turn_2_success = turn_3_success = 0
        context_used = context_used_percent = 0
    
    # === Print Report ===
    print("\n" + "=" * 60)
    print("📊 QUERYMATE PERFORMANCE REPORT")
    print("=" * 60)
    
    print(f"\n📈 Overall Statistics:")
    print(f"  • Total queries: {total_queries}")
    print(f"  • Successful: {successful_queries} ({overall_success_rate}%)")
    print(f"  • Failed: {failed_queries} ({100 - overall_success_rate:.2f}%)")
    
    print(f"\n🔍 RAG Usage:")
    print(f"  • With RAG (1+ examples): {with_rag_count} ({with_rag_percent}%)")
    print(f"  • Without RAG (0 examples): {without_rag_count} ({without_rag_percent}%)")
    print(f"  • Avg examples retrieved: {avg_examples_retrieved}")
    print(f"  • Avg retrieval time: {avg_retrieval_time:.0f}ms")
    
    print(f"\n💡 RAG Impact on Accuracy:")
    print(f"  • Success with 0 examples: {success_no_rag:.1f}%")
    print(f"  • Success with 1-2 examples: {success_low_rag:.1f}%")
    print(f"  • Success with 3+ examples: {success_high_rag:.1f}%")
    print(f"  • RAG improvement: +{rag_improvement:.1f}%")
    
    print(f"\n⚡ Performance Metrics:")
    print(f"  • Avg generation time: {avg_generation_time:.0f}ms")
    print(f"  • Min generation time: {min_generation_time:.0f}ms")
    print(f"  • Max generation time: {max_generation_time:.0f}ms")
    
    if has_conversation_data:
        print(f"\n💬 Conversation Statistics:")
        print(f"  • Total conversations: {total_conversations}")
        print(f"  • Avg conversation length: {avg_conversation_length:.1f} turns")
        print(f"  • Turn 1 success rate: {turn_1_success:.1f}%")
        print(f"  • Turn 2 success rate: {turn_2_success:.1f}%")
        print(f"  • Turn 3+ success rate: {turn_3_success:.1f}%")
        print(f"  • Queries using context: {context_used} ({context_used_percent:.1f}%)")
    
    print("\n" + "=" * 60 + "\n")
    
    # === Save to CSV ===
    analysis_dict = {
        'total_queries': total_queries,
        'successful_queries': successful_queries,
        'failed_queries': failed_queries,
        'overall_success_rate': overall_success_rate,
        'with_rag_count': with_rag_count,
        'with_rag_percent': with_rag_percent,
        'without_rag_count': without_rag_count,
        'without_rag_percent': without_rag_percent,
        'avg_examples_retrieved': avg_examples_retrieved,
        'avg_retrieval_time_ms': avg_retrieval_time,
        'success_no_rag': success_no_rag,
        'success_low_rag': success_low_rag,
        'success_high_rag': success_high_rag,
        'rag_improvement': rag_improvement,
        'avg_generation_time_ms': avg_generation_time,
        'min_generation_time_ms': min_generation_time,
        'max_generation_time_ms': max_generation_time,
        'total_conversations': total_conversations,
        'avg_conversation_length': avg_conversation_length,
        'turn_1_success': turn_1_success,
        'turn_2_success': turn_2_success,
        'turn_3_success': turn_3_success,
        'context_used_count': context_used,
        'context_used_percent': context_used_percent,
        'analysis_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    analysis_df = pd.DataFrame([analysis_dict])
    analysis_file = os.path.join(logs_path, 'log_analysis.csv')
    analysis_df.to_csv(analysis_file, index=False)
    
    print(f"✅ Analysis saved to: {analysis_file}")
    
    return analysis_dict


if __name__ == "__main__":
    analyze_logs()