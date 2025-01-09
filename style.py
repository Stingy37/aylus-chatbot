import streamlit as st
import base64

def set_custom_background(background_image_path):
    # Encode the background image
    @st.cache_data
    def get_base64_image(image_file):
        with open(image_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()

    img_base64 = get_base64_image(background_image_path)

    # Custom CSS
    custom_css = f'''
    <style>
    /* Set the background for the entire app */
    .stApp {{
        background: url("data:image/jpg;base64,{img_base64}") no-repeat center center fixed;
        background-size: 115%; 
        background-position: 0px center;
    }}
    /* Keep the main content area's default background */
    .block-container {{
        background-color: rgba(255,255,255,0.7);
        position: relative;
        padding-top: 2rem;
        backdrop-filter: blur(30px);
    }}
    </style>
    '''

    st.markdown(custom_css, unsafe_allow_html=True)

    hide_streamlit_style = """
            <style>
            /* Hide Streamlit header */
            header {visibility: hidden;}
            /* Hide Streamlit hamburger menu */
            #MainMenu {visibility: hidden;}
            </style>
            """

    st.markdown(hide_streamlit_style, unsafe_allow_html=True)