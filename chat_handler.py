import streamlit as st
import sqlite3
from openai import OpenAI

client = OpenAI()
import logging
import json

from rag import find_relevant_docs
from database import load_chat_messages, save_message, load_document_text

def initialize_session_state():
    if "model" not in st.session_state:
        st.session_state.model = "gpt-4-turbo"  # Default model
    if "document_text" not in st.session_state:
        st.session_state.document_text = {}  # To store document texts per chat_id
    if "active_chat_id" not in st.session_state:
        st.session_state.active_chat_id = None
    if "previous_chat_id" not in st.session_state:
        st.session_state.previous_chat_id = None
    if "messages" not in st.session_state:
        st.session_state.messages = []

def sidebar_chat_sessions():
    st.sidebar.title("Chat Sessions")
    # Connect to the database
    conn = sqlite3.connect("chat_history.db")
    conn.execute("PRAGMA foreign_keys = ON;")  # Enable foreign key constraints
    cursor = conn.cursor()
    # Fetch all chats
    cursor.execute("SELECT id, name FROM chats ORDER BY created_at DESC")
    chats = cursor.fetchall()
    chat_names = [chat[1] for chat in chats]
    chat_ids = [chat[0] for chat in chats]
    # Select a chat
    if chats:
        selected_chat_index = st.sidebar.selectbox(
            "Select a chat session",
            range(len(chat_names)),
            format_func=lambda idx: chat_names[idx],
        )
        st.session_state.active_chat_id = chat_ids[selected_chat_index]
    else:
        st.session_state.active_chat_id = None
        st.sidebar.info("No chat sessions. Create a new one below.")

    # Detect active chat changes
    if st.session_state.active_chat_id != st.session_state.get("previous_chat_id"):
        st.session_state.previous_chat_id = st.session_state.active_chat_id

        # Load messages from the database for the active chat
        st.session_state.messages = load_chat_messages(st.session_state.active_chat_id)

        # Load document_text from the database
        document_text = load_document_text(st.session_state.active_chat_id)
        st.session_state.document_text[st.session_state.active_chat_id] = document_text

    # Create a new chat
    new_chat_name = st.sidebar.text_input("New chat name")
    if st.sidebar.button("Create New Chat"):
        if new_chat_name.strip():
            # Check if the chat name already exists
            cursor.execute("SELECT id FROM chats WHERE name = ?", (new_chat_name.strip(),))
            existing_chat = cursor.fetchone()
            if existing_chat:
                st.sidebar.error("A chat with that name already exists. Please choose another name.")
            else:
                cursor.execute("INSERT INTO chats (name) VALUES (?)", (new_chat_name.strip(),))
                conn.commit()
                st.sidebar.success(f"Chat '{new_chat_name}' created.")
                st.session_state.active_chat_id = cursor.lastrowid  # Set the new chat as active
                st.session_state.messages = []  # Clear messages for the new chat
                st.session_state.document_text[st.session_state.active_chat_id] = ''  # Initialize document_text for the new chat
                st.rerun()
        else:
            st.sidebar.error("Please enter a chat name.")

    # Delete chat
    if st.session_state.active_chat_id:
        if st.sidebar.button("Delete Chat"):
            chat_id = st.session_state.active_chat_id
            try:
                # Delete the chat; associated messages will be deleted automatically due to ON DELETE CASCADE
                cursor.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
                conn.commit()
                st.sidebar.success("Chat deleted.")
                # Remove document_text for this chat
                if chat_id in st.session_state.document_text:
                    del st.session_state.document_text[chat_id]
                st.session_state.active_chat_id = None
                st.session_state.messages = []
                st.rerun()
            except Exception as e:
                logging.error(f"Error deleting chat: {e}")
                st.sidebar.error(f"An error occurred while deleting the chat: {e}")

    # Rename chat
    if st.session_state.active_chat_id:
        rename_chat_name = st.sidebar.text_input("Rename chat")
        if st.sidebar.button("Rename"):
            if rename_chat_name.strip():
                cursor.execute("""
                    UPDATE chats SET name = ? WHERE id = ?
                """, (rename_chat_name.strip(), st.session_state.active_chat_id))
                conn.commit()
                st.sidebar.success("Chat renamed.")
                st.rerun()
            else:
                st.sidebar.error("Please enter a valid chat name.")

    # Close the database connection
    conn.close()

def process_system_instructions(system_instructions, user_input, vector_database):
    relevant_information = str(find_relevant_docs(user_input, vector_database)[0])

    processed_system_instructions = system_instructions.format(
          user_input_placeholder = user_input,
          relevant_information_placeholder = relevant_information
      )
    return processed_system_instructions

def handle_user_input(system_instructions, vector_database):
    user_input = st.session_state.input_box
    processed_system_instructions = process_system_instructions(system_instructions, user_input, vector_database)

    if user_input.strip() and st.session_state.active_chat_id:
        chat_id = st.session_state.active_chat_id
        # Add user message to session state
        user_message = {"role": "user", "content": user_input.strip()}
        st.session_state.messages.append(user_message)
        # Save user message to the database
        save_message(chat_id, user_message["role"], user_message["content"])
        # Prepare messages for the API call
        messages = []
        # Get the document_text specific to the current chat_id
        document_text = st.session_state.document_text.get(chat_id, "")
        for message in st.session_state.messages:
            role = message["role"]
            content = message["content"]
            if role == "user":
                if document_text:
                    pass # document_text is not needed in this project - no file upload functionality
                else:
                    user_input_with_context = processed_system_instructions
                messages.append({"role": role, "content": user_input_with_context})
            else:
                messages.append(message)
        # Log the messages being sent to the API
        logging.info(f"Sending messages to OpenAI API:\n{json.dumps(messages, indent=2)}")
        try:
            # Generate GPT response
            with st.spinner("Assistant is typing..."):
                response = client.chat.completions.create(model=st.session_state.model,
                messages=messages)
            reply = response.choices[0].message.content
            assistant_message = {"role": "assistant", "content": reply}
            st.session_state.messages.append(assistant_message)
            # Save assistant message to the database
            save_message(chat_id, assistant_message["role"], assistant_message["content"])
        except Exception as e:
            # Handle exception
            error_message = {"role": "assistant", "content": f"Error: {e}"}
            st.session_state.messages.append(error_message)
            # Save error message to the database
            save_message(chat_id, error_message["role"], error_message["content"])
        # Clear input box
        st.session_state.input_box = ""
    else:
        st.error("Please select or create a chat session.")

def display_chat_history():
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "user":
                st.text(message["content"])
            else:
                st.markdown(message["content"])