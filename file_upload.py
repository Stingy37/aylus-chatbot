import os
import streamlit as st
import PyPDF2
import pytesseract
from PIL import Image
from database import save_document_text  # Import the function to save document_text

def handle_file_upload(uploaded_files, chat_id):
    context_parts = []

    for uploaded_file in uploaded_files:
        filename = uploaded_file.name
        file_extension = os.path.splitext(filename)[1].lower()

        if file_extension in [".pdf", ".py", ".png", ".jpg", ".jpeg"]:
            content = extract_file_content(uploaded_file, filename, file_extension)
            if content:
                # Format the context
                formatted_content = f"[{filename}] content:\n{content}\n"
                context_parts.append(formatted_content)

    if context_parts:
        # Combine all contents
        combined_context = "\n".join(context_parts)
        # Store the combined context for this chat session
        st.session_state.document_text[chat_id] = combined_context
        # Save to database
        save_document_text(chat_id, combined_context)
        st.success("Files extracted and stored.")

def extract_file_content(file_like, filename, file_extension):
    if file_extension == ".pdf":
        # Use PyPDF2 to read the PDF file
        try:
            pdf_reader = PyPDF2.PdfReader(file_like)
            text = ""
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text()
            return text.strip()
        except Exception as e:
            st.error(f"An error occurred while processing the PDF file {filename}: {e}")
            return None
    elif file_extension == ".py":
        # Read the .py file
        try:
            code = file_like.getvalue().decode("utf-8")
            return code.strip()
        except Exception as e:
            st.error(f"An error occurred while processing the Python file {filename}: {e}")
            return None
    elif file_extension in [".png", ".jpg", ".jpeg"]:
        # Use PIL and pytesseract to read the image and extract text
        try:
            image = Image.open(file_like)
            extracted_text = pytesseract.image_to_string(image)
            if extracted_text.strip():
                return extracted_text.strip()
            else:
                st.warning(f"No text found in the image {filename}.")
                return None
        except Exception as e:
            st.error(f"An error occurred while processing the image {filename}: {e}")
            return None
    else:
        # Unsupported file type
        return None
