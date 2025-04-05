# ChatWithAuthor
# 📚 ChatWithAuthor

An intelligent PDF chatbot web application where users can chat with their uploaded documents. The system understands context from the documents and responds accordingly. It includes user authentication and chat history features.

---

## ✨ Features

- 📄 Upload and chat with PDF documents
- 💬 Context-aware answers powered by Gemini Pro via LangChain
- 🔐 User authentication (Sign up / Log in)
- 💾 MongoDB integration for storing users and chat history
- 🧠 Vector similarity search using FAISS
- 🌐 Built with Streamlit for fast and clean web UI

---

## 🧰 Tech Stack

- **Frontend:** Streamlit
- **Backend:** Python
- **AI Model:** Google Generative AI (Gemini)
- **Vector DB:** FAISS
- **Database:** MongoDB Atlas
- **Libraries:** LangChain, PyPDF, Google Generative AI, bcrypt, pymongo, etc.

---

## 🔧 Requirements

Create and activate a virtual environment first:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install -r requirements.txt

```

ChatWithAuthor/
├── chat_with_author_bot.py     # Main Streamlit app
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (ignored by git)
├── .gitignore                  # Ignore config
└── README.md                   # Project documentation


## Add a .env file and give all the required feilds.

MONGO_USERNAME=your_username
MONGO_PASSWORD=your_password
MONGO_CLUSTER=your_cluster
MONGO_DB_NAME=your_database_name
GOOGLE_API_KEY=your_gemini_api_key

```
