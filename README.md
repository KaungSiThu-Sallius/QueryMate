# QueryMate — AI SQL Assistant 🤖

> **Ask your database questions in plain English. Get instant answers, charts, and insights — powered by Google Gemini AI.**

[![Built with Streamlit](https://img.shields.io/badge/Built%20with-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Powered by Gemini](https://img.shields.io/badge/Powered%20by-Google%20Gemini-4285F4?logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![Database](https://img.shields.io/badge/Database-PostgreSQL-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Vector DB](https://img.shields.io/badge/Vector%20DB-ChromaDB-orange)](https://www.trychroma.com/)

---

## ✨ What is QueryMate?

QueryMate bridges the gap between non-technical users and complex relational databases. Instead of writing SQL, you simply type a question like:

> *"What are the top 5 product categories by revenue this year?"*

And QueryMate will:
1. 🧠 **Understand** your question using Google Gemini's LLM
2. ✍️ **Generate** a safe, validated SQL query automatically
3. ⚡ **Execute** it against your live PostgreSQL database
4. 📊 **Visualise** the results as a smart bar chart, line chart, or table
5. 💾 **Remember** the best queries to get smarter over time (RAG)

---

## 🚀 Key Features

| Feature | Description |
|---|---|
| 🗣️ **Natural Language to SQL** | Converts plain English questions into validated SQL queries |
| 📊 **Auto Visualisation** | Automatically selects the best chart type (bar, line, metric, table) |
| 🧠 **RAG Memory** | Stores successful queries in ChromaDB to improve future accuracy |
| 💾 **Session Persistence** | Chat history is saved to PostgreSQL — survives page refreshes |
| 🔒 **SQL Safety** | Validates every query before execution — blocks destructive operations |
| 📥 **Export Results** | Download query results as CSV or Excel with one click |

---

## 🏗️ Architecture

```
User Question
      │
      ▼
 Google Gemini LLM  ◄──── ChromaDB RAG (similar past queries)
      │
      ▼
 SQL Validator (blocks DROP/DELETE/ALTER etc.)
      │
      ▼
 PostgreSQL (Supabase) ──► Results ──► Auto Chart ──► UI
      │
      ▼
 Session saved back to PostgreSQL (chat_sessions table)
```

---

## 🛠️ Tech Stack

- **Frontend**: [Streamlit](https://streamlit.io)
- **LLM**: [Google Gemini 1.5 Flash](https://deepmind.google/technologies/gemini/)
- **Database**: [PostgreSQL](https://www.postgresql.org/) via [Supabase](https://supabase.com)
- **Vector Store**: [ChromaDB](https://www.trychroma.com/) (local persistent)
- **ORM**: [SQLAlchemy](https://www.sqlalchemy.org/)
- **Charts**: [Plotly Express](https://plotly.com/python/plotly-express/)

---

## 🔧 Local Setup

### Prerequisites
- Python 3.10+
- [Pipenv](https://pipenv.pypa.io/en/latest/)
- A running PostgreSQL database
- A [Google Gemini API Key](https://aistudio.google.com/app/apikey)

### 1. Clone the repository
```bash
git clone https://github.com/your-username/QueryMate.git
cd QueryMate
```

### 2. Install dependencies
```bash
pipenv install
```

### 3. Configure environment variables
Create a `.env` file in the root directory:
```env
DB_HOST=your-db-host
DB_PORT=5432
DB_USER=your-db-user
DB_PASS=your-db-password
DB_NAME=your-db-name
GEMINI_API_KEY=your-gemini-api-key
```

### 4. Run the app
```bash
pipenv run streamlit run src/app.py
```

---

## ☁️ Cloud Deployment (Hugging Face Spaces)

1. Create a new **Streamlit Space** on [Hugging Face](https://huggingface.co/spaces)
2. Add your environment variables in **Settings → Repository Secrets**
3. Push your code to the Space's Git repository
4. Done! Your app is live 🚀

> **Note:** The `data/chroma_db` folder acts as a read-only RAG brain in the cloud. To teach the AI new queries, train locally and push the updated folder to the repository.

---

## 📁 Project Structure

```
QueryMate/
├── src/
│   ├── app.py              # Main Streamlit UI & session logic
│   ├── llm_query.py        # Gemini API integration & SQL generation
│   ├── vector_store.py     # ChromaDB RAG implementation
│   ├── utilities.py        # DB connection, SQL validation, chart detection
│   └── prompts.py          # LLM prompt templates
├── data/
│   ├── chroma_db/          # Persistent vector store (RAG brain)
│   └── database_schema.png # Schema reference for the LLM
├── requirements.txt
└── README.md
```

---

## 🔐 Security

- Only `SELECT` queries are permitted — all `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER` operations are blocked at the validation layer before reaching the database.
- API keys and database credentials are managed exclusively through environment variables and never hardcoded.

---

## 👤 Author

Built by **Kaung Si Thu** as a portfolio project demonstrating the integration of LLMs, RAG, and real-time database querying in a production-ready Streamlit application.

[![GitHub](https://img.shields.io/badge/GitHub-KaungSiThu--Sallius-181717?logo=github)](https://github.com/KaungSiThu-Sallius)
