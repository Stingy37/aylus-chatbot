import streamlit as st
import sqlite3
from openai import OpenAI

client = OpenAI()
import logging
import json

from rag import find_relevant_docs

# Paths to avatar images
user_avatar_image = 'assets/user_icon_small.jpg'
assistant_avatar_image = 'assets/assistant_icon_small.jpg'

def initialize_session_state():
    if "model" not in st.session_state:
        st.session_state.model = "gpt-4o"  # Default model
    if "messages" not in st.session_state:
        st.session_state.messages = []

def process_system_instructions(system_instructions, user_input, vector_database):
    relevant_information = str(find_relevant_docs(user_input, vector_database)[0])

    processed_system_instructions = system_instructions.format(
          user_input_placeholder = user_input,
          relevant_information_placeholder = relevant_information
      )
    return processed_system_instructions

def handle_user_input():

    user_input = st.session_state.input_box
    system_instructions = st.session_state['system_instructions']
    vector_database = st.session_state['vector_database']

    processed_system_instructions = process_system_instructions(system_instructions, user_input, vector_database)

    if user_input.strip():
        # Add user message to session state and display it first
        user_message = {"role": "user", "content": user_input.strip()}
        st.session_state.messages.append(user_message)
        with st.chat_message(user_message["role"], avatar=user_avatar_image):
            st.text(user_message["content"])
        
        messages = []

        for message in st.session_state.messages:
            role = message["role"]
            content = message["content"]
            if role == "user":
                user_input_with_context = processed_system_instructions
                messages.append({"role": role, "content": user_input_with_context})
            else:
                messages.append(message)

        # Log the messages being sent to the API
        logging.info(f"Sending messages to OpenAI API:\n{json.dumps(messages, indent=2)}")
        
        with st.chat_message("assistant", avatar=assistant_avatar_image):
            # Create a placeholder
            assistant_placeholder = st.empty()

            # Initialize an empty reply
            full_reply = ""

            try:
                # Generate GPT response with streaming
                response = client.chat.completions.create(
                    model=st.session_state.model,
                    messages=messages,
                    stream=True
                )

                for chunk in response:
                    delta = getattr(chunk.choices[0].delta, 'content', '')
                    if delta:
                        full_reply += delta
                        assistant_placeholder.markdown(full_reply)

                assistant_message = {"role": "assistant", "content": full_reply}
                st.session_state.messages.append(assistant_message)

            except Exception as e:
                # Handle exception
                error_message = {"role": "assistant", "content": f"Error: {e}"}
                st.session_state.messages.append(error_message)

        # Clear input box
        st.session_state.input_box = ""

    else:
        st.error("Please select or create a chat session.")

# Used to display previous chat messages (NOT displaying current interaction, which is handled in handle_user_input)
def display_chat_history():
    for message in st.session_state.messages:
        if message["role"] == "user":
            avatar_image = user_avatar_image
            with st.chat_message(message["role"], avatar=avatar_image):
                st.text(message["content"])
        else:
            avatar_image = assistant_avatar_image
            with st.chat_message(message["role"], avatar=avatar_image):
                st.markdown(message["content"])