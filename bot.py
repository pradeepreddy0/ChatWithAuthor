import streamlit as st
from pymongo import MongoClient
from passlib.context import CryptContext
from bson.objectid import ObjectId
import os
import urllib.parse
from subprocess import call
from dotenv import load_dotenv

from streamlit_chat import message
from streamlit.components.v1 import html
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai
from langchain.vectorstores.faiss import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from html_templates import css, bot_template, user_template

load_dotenv()
os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text


def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    chunks = text_splitter.split_text(text)
    return chunks


def get_vector_store(text_chunks):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", task_type="RETRIEVAL_DOCUMENT")
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    save_path = "faiss_index"
    os.makedirs(save_path, exist_ok=True)
    vector_store.save_local(save_path)
    print(f"FAISS index saved to {save_path}")


def get_conversational_chain():
    prompt_template = """
    Answer the question as detailed as possible from the provided context, make sure to provide all the details, if the answer is not in
    provided context just say, "answer is not available in the context", don't provide the wrong answer\n\n
    Context:\n {context}?\n
    Question: \n{question}\n

    Answer:
    """

    model = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.9)
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)

    return chain


def user_question(user_input):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    new_db = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
    docs = new_db.similarity_search(user_input)

    chain = get_conversational_chain()
    response = chain({"input_documents": docs, "question": user_input}, return_only_outputs=True)

    st.session_state.past.append(user_input)
    st.session_state.generated.append(response['output_text'])

    # Save the chat history to the database
    user_id = st.session_state.user_id
    create_question(user_id, user_input, response['output_text'])


def on_btn_click():
    del st.session_state.past[:]
    del st.session_state.generated[:]


def Bot():
    st.write(css, unsafe_allow_html=True)

    with st.sidebar:
        st.title("Menu:")
        pdf_docs = st.file_uploader("Upload your PDF Files and Click on the Submit & Process Button", accept_multiple_files=True)
        if st.button("Submit & Process"):
            with st.spinner("Processing..."):
                raw_text = get_pdf_text(pdf_docs)
                text_chunks = get_text_chunks(raw_text)
                get_vector_store(text_chunks)
                st.success("Done")

        # Display user's chat history
        st.title("Chat History")
        if 'user_id' in st.session_state:
            user_id = st.session_state.user_id
            questions = list(questions_collection.find({"user_id": ObjectId(user_id)}))
            for q in questions:
                st.write(f"Q: {q['question_text']}")
                st.write(f"A: {q['response_text']}")

    if 'past' not in st.session_state:
        st.session_state['past'] = []
    if 'generated' not in st.session_state:
        st.session_state['generated'] = []

    st.title('Chat with Author')
    chat_placeholder = st.empty()

    with st.container():
        # st.markdown("""
        # <style>
        # .static-input-container {
        #     display: flex;
        #     justify-content: center;
        #     align-items: center;
        #     height: 100vh; /* Full viewport height */
        #     background-color: #f0f0f0; /* Light grey background */
        # }
        # .static-input {
        #     width: 300px;
        #     padding: 10px;
        #     font-size: 16px;
        #     border: 1px solid #ccc;
        #     border-radius: 4px;
        # }
        # </style>
        # <div class="static-input-container">
        #     <input type="text" class="static-input" placeholder="Type here...">
        # </div>
        # """, unsafe_allow_html=True)
        
        
        question = st.text_input(label="Ask a question on the provided PDF", key='user_input')
        if st.button("Submit"):
            user_question(question)

    with chat_placeholder.container():
        for i in range(len(st.session_state['generated'])):
            message(st.session_state['past'][i], is_user=True, key=f"{i}_user")
            message(st.session_state['generated'][i], key=f"{i}", allow_html=True)
        st.button("Clear messages", on_click=on_btn_click)


# Load environment variables
load_dotenv()

# Get credentials from environment variables
username = os.getenv("MONGODB_USER")
password = os.getenv("MONGODB_PASSWORD")
cluster = os.getenv("MONGODB_CLUSTER")
database = os.getenv("MONGODB_DB")

# Encode username and password
encoded_username = urllib.parse.quote_plus(username)
encoded_password = urllib.parse.quote_plus(password)

# Construct MongoDB URI for Atlas
MONGODB_URL = f"mongodb+srv://{username}:{password}@cluster0.bxzbetp.mongodb.net/?{database}retryWrites=true&w=majority&appName={cluster}"

# Connect to MongoDB Atlas
client = MongoClient(MONGODB_URL)

# Define the database and collections
db = client[database]
users_collection = db["users"]
questions_collection = db["questions"]

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def create_user(username: str, password: str):
    if users_collection.find_one({"username": username}):
        st.error("Username already exists.")
        return None
    hashed_password = get_password_hash(password)
    user = {
        "username": username,
        "hashed_password": hashed_password
    }
    users_collection.insert_one(user)
    return user


def get_user(username: str):
    return users_collection.find_one({"username": username})


def create_question(user_id: str, question_text: str, response_text: str):
    question = {
        "user_id": ObjectId(user_id),
        "question_text": question_text,
        "response_text": response_text
    }
    questions_collection.insert_one(question)
    return question


def main():
    st.title("Chatbot With your PDFs")
    if "logged_in" in st.session_state and st.session_state.logged_in:
        st.sidebar.image("user.png", width=50)
        st.sidebar.write(f"Logged in as: {st.session_state.username}")
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.pop("user_id", None)
            st.session_state.pop("username", None)
            st.success("You have successfully logged out.")
            st.experimental_rerun()

        if st.session_state.logged_in:
            Bot()
        else:
            st.warning("You need to log in to ask a question.")
    else:
        menu = ["Home", "Login", "Sign Up", "Ask Question"]
        choice = st.sidebar.selectbox("Menu", menu)

        if choice == "Home":
            # st.subheader("Home")
            st.info("Welcome to Chatbot with your PDFs!")
            st.text("Our bot can help you to chat with your uploaded PDF and get the response from bot.\nYou can upload multiple PDFs and chat with the multiple PDFs at once.")
            # st.info("Welcome to Chatbot with your PDFs!")
            st.info("Please log in to ask a question.")

        elif choice == "Sign Up":
            st.subheader("Create New Account")
            with st.form(key='signup_form'):
                new_user = st.text_input("Username")
                new_password = st.text_input("Password", type='password')
                signup_button = st.form_submit_button("Sign Up")

            if signup_button:
                if new_user and new_password:
                    user = create_user(new_user, new_password)
                    if user:
                        st.success("You have successfully created an account!")
                        st.info("Go to the Login Menu to log in.")
                else:
                    st.warning("Please enter both username and password.")

        elif choice == "Login":
            st.subheader("Login")
            with st.form(key='login_form'):
                username = st.text_input("Username")
                password = st.text_input("Password", type='password')
                login_button = st.form_submit_button("Login")

            if login_button:
                user = get_user(username)
                if user and verify_password(password, user["hashed_password"]):
                    st.success(f"Logged in as {username}")
                    st.session_state.logged_in = True
                    st.session_state.user_id = str(user["_id"])
                    st.session_state.username = username
                    st.experimental_rerun()
                else:
                    st.error("Invalid username or password")

        elif choice == "Ask Question":
            if "logged_in" in st.session_state and st.session_state.logged_in:
                Bot()
            else:
                st.warning("You need to log in to ask a question.")


if __name__ == "__main__":
    main()
