import os
import pandas as pd
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
import pdfplumber


# Initialize variables and paths
context_data_folder = 'LLM_website_context'
files_with_info = [f for f in os.listdir(context_data_folder) if f.endswith('.pdf') and not f.startswith('.')]


# Metadata setup
def set_doc_metadata(total_pages, index):
    for page in total_pages:
        page.metadata['title'] = files_with_info[index] # Split into different files for each webpage for better metadata 


# Load and split documents
def load_documents(context_data_folder):
    # Configure text splitter
    large_text_splitter = RecursiveCharacterTextSplitter(
        separators=["Scene"],
        chunk_size=5000,
        chunk_overlap=500,
        length_function=len,
        is_separator_regex=False,
    )

    processed_total_pages = []
    for index, file in enumerate(files_with_info):
        loader = PyPDFLoader(os.path.join(context_data_folder, file))
        total_pages = loader.load_and_split(text_splitter=large_text_splitter)
        set_doc_metadata(total_pages, index)
        processed_total_pages += total_pages
    return processed_total_pages


# Create FAISS database
def create_database(processed_total_pages, openai_api_key):
    embeddings = OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=openai_api_key)
    return FAISS.from_documents(processed_total_pages, embeddings)


# Find relevant documents
def find_relevant_docs(query, database):
    docs = database.similarity_search_with_score(query, k=5)
    relevant_page_content = [doc[0].page_content for doc in docs]
    metadata = [doc[0].metadata for doc in docs]
    return [relevant_page_content, metadata]


# Extract tables from a PDF page
def extract_tables(page):

    extracted_tables = page.extract_tables()
    if extracted_tables:
        return pd.DataFrame(extracted_tables[0])
    return None
