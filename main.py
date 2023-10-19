import os
import streamlit as st
import pickle
from dotenv import load_dotenv
from langchain.document_loaders import UnstructuredURLLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain import OpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.chains import RetrievalQAWithSourcesChain
from langchain.vectorstores import FAISS

# Accessing all the environment variables from .env file (openai api key)
load_dotenv()

# Creating session variables to keep track of the urls entered
if 'urls' not in st.session_state:
    st.session_state["urls"] = []
    st.session_state["i"] = 1

st.title("Ask Away 🔗")
st.sidebar.title("Enter Article URLs")

urls = []
file_path = "faiss_index_store.pkl"

url_container = st.sidebar.container()
col1, col2 = st.sidebar.columns(2)

# Displaying URL fields
if len(st.session_state['urls'])>1:
    for url in st.session_state["urls"]:
        url_text = url_container.text_input(f"URL {url['index']}", key=url['index'], value=url['value'])
        st.session_state['urls'][url['index']-1]['value'] = url_text
        urls.append(url['value'])
elif st.session_state.i==1:
    url = url_container.text_input(f"URL {1}", key=1)
    st.session_state.urls = []
    st.session_state.urls.append({'index': st.session_state.i, 'value': url})
    urls.append(url)

def add_URL(st):
    '''Adding new URL field'''
    global url_container
    if(st.session_state.i >= 1 and st.session_state["urls"] and st.session_state["urls"][st.session_state["i"]-1]["value"]):
        st.session_state.i += 1
        url = url_container.text_input(f"URL {st.session_state.i}")
        st.session_state.urls.append({'index': st.session_state.i, 'value': url})
        urls.append(url)

process_url_clicked = col1.button("Add URL", on_click=lambda: add_URL(st))
process_url_clicked = col2.button("Process URLs")

main_placeholder = st.empty()

if process_url_clicked:
    # Loading data from URLs entered
    # browse https://httpbin.org/get to get your user-agent or remove headers parameter
    loader = UnstructuredURLLoader(urls=urls, headers={"User-Agent": "enter your user-agent"})
    main_placeholder.text("Data Loading...⏳")
    data = loader.load()

    # Splitting data recursively using multiple separators
    text_splitter = RecursiveCharacterTextSplitter(
        separators=['\n\n', '\n', '.', ','],
        chunk_size=1000
    )
    main_placeholder.text("Text Splitting in Progress...🔄")
    docs = text_splitter.split_documents(data)

    # Creating embedding using OpenAI and generating their FAISS index
    embedding = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(docs, embedding)
    main_placeholder.text("Building Embedding Vector...🔄")

    # Saving FAISS index to a pickle file.
    # Instead of using Vector DB, performing in-memory computation as requirement is small.
    with open(file_path, "wb") as f:
        pickle.dump(vectorstore, f)
main_placeholder.text("Data Processing Complete...✅")
main_placeholder.text("")
query = st.text_input("What are you looking for? ")
llm = OpenAI(temperature=0.7, max_tokens=500)

# Fetching related chunks of vectors and hitting OpenAi with query and individual chunks to get the result.
if query:
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            vectorstore = pickle.load(f)
            chain = RetrievalQAWithSourcesChain.from_llm(llm=llm, retriever=vectorstore.as_retriever())
            result = chain({"question": query}, return_only_outputs=True)
            # result --> {"answer": "", "sources": [] }
            st.header("Result: ")
            st.write(result["answer"])
            # Display sources, if available
            sources = result.get("sources", "")
            if sources:
                st.subheader("Sources:")
                sources_list = sources.split("\n")
                for source in sources_list:
                    st.write(source)

