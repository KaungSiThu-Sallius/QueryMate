# 🤖 QueryMate — AI SQL Assistant

Ask your e-commerce database anything in plain English. QueryMate converts your question into SQL using **Google Gemini**, executes it against a PostgreSQL database, and displays the results in a clean chat interface.

## Features

- 💬 **Natural language to SQL** — powered by Gemini AI
- 📚 **RAG memory** — learns from successful queries via ChromaDB
- 🔄 **Conversation context** — understands follow-up questions ("How many of *them*?")
- 📊 **Results as tables** — interactive, sortable dataframes
- 🛡️ **SQL safety validation** — blocks destructive operations automatically
- 📈 **Session analytics** — tracks success rate, RAG usage, response times

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Google Gemini (`gemini-3.1-flash-lite-preview`) |
| Orchestration | LangChain |
| Vector Store | ChromaDB |
| Database | PostgreSQL (via SQLAlchemy) |
| Frontend | Streamlit |

## Dataset

Olist Brazilian E-Commerce dataset — ~100K orders across 7 tables (customers, orders, products, order_items, payments, reviews, categories). Dates shifted to 2023–2025.

## Setup

### 1. PostgreSQL (Docker)

```bash
docker volume create postgres-data
docker run --name querymate-db \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_USER=user \
  -e POSTGRES_DB=ecommerce \
  -p 5432:5432 \
  -v postgres-data:/var/lib/postgresql \
  -d postgres
```

### 2. Environment Variables

Create a `.env` file in the project root:

```
DB_NAME=ecommerce
DB_USER=user
DB_PASS=password
DB_HOST=localhost
DB_PORT=5432
GEMINI_API_KEY=your_key_here
```

### 3. Install Dependencies

```bash
pipenv install
pipenv shell
```

### 4. Load Data

```bash
python src/data_loader.py
```

### 5. Run the App

```bash
streamlit run src/app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

## Example Questions

- *"How many customers are there?"*
- *"Show top 5 product categories by number of orders"*
- *"What was total revenue in 2024?"*
- *"Show me customers from São Paulo"*
- *"Which orders had 5-star reviews and spent over 500?"*

## Project Structure

```
QueryMate/
├── src/
│   ├── app.py           ← Streamlit frontend
│   ├── llm_query.py     ← Core pipeline (SQL generation + execution)
│   ├── prompts.py       ← LangChain prompt template + DB schema
│   ├── vector_store.py  ← ChromaDB RAG store
│   ├── utilities.py     ← SQL validation + cleanup
│   ├── data_loader.py   ← CSV → PostgreSQL loader
│   └── analyze_logs.py  ← Performance analytics
├── data/
│   ├── raw_data_used/   ← CSV source files
│   ├── chroma_db/       ← Persisted vector store
│   └── logs/            ← Query logs + analysis
├── .streamlit/
│   └── config.toml      ← Dark theme config
├── requirements.txt
├── Pipfile
└── .env                 ← (not committed)
```
