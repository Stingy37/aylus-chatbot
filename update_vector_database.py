
import streamlit as st
import openai
import os

from rag import (
load_documents, create_database
)

# Initialize variables and paths
openai.api_key = st.secrets["OPENAI_API_KEY"]
context_data_folder = 'LLM_website_context'
files_with_info = [f for f in os.listdir(context_data_folder) if f.endswith('.pdf') and not f.startswith('.')]

# Load documents and initialize database
total_pages = load_documents(context_data_folder, files_with_info)
FAISS_vector_database = create_database(total_pages, openai.api_key)

# Save the FAISS vector database to a folder called 'vector_database'
FAISS_vector_database.save_local('vector_database')