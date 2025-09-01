import streamlit as st
from typing import Union
import json
import os
import logging
from hedis_openai import get_bot_response


SCRIPT='SUMMARIZATION.py'

st.set_page_config(layout="wide",page_title="HEDISAbstrator.AI")

st.markdown("""
    <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        h1 {
            font-size: 2.8rem !important;
        }
        .section-header {
            font-size: 1.9rem !important;
            font-weight: 700;
            margin-top: .5rem;
            margin-bottom: .1rem;
            color: #1f4e79;
        }
        .stMarkdown, .markdown-text-container, .element-container {
            font-size: 1.1rem !important;
            margin-bottom: 0.2rem !important;
            padding-bottom: 0.1rem !important;
        }
        ul {
            padding-left: 1.2rem;
            margin-top: 0.2rem !important;
            margin-bottom: 0.2rem !important;
        }
        li {
            font-size: 1.15rem !important;
            margin-bottom: 0.1rem !important;
            line-height: 1.2 !important;
        }
        hr {
            margin-top: 0.3rem !important;
            margin-bottom: 0.3rem !important;
        }
        .stExpanderHeader {
            font-size: 1.1rem !important;
        }
        .user-greeting-container {
            position: fixed; 
            top: 40px; 
            right: 0; 
            background-color: white; 
            display: flex; 
            justify-content: flex-end; 
            align-items: center; 
            padding: 10px 20px; 
            z-index: 1000; 
            width: 100%; 
            box-sizing: border-box; 
        }
        .user-greeting {
            display: flex;
            align-items: center;
            font-size: 16px;
            font-weight: bold;
            color: black;
            margin-right: 80px;
        }
        .user-greeting img {
            width: 20px;
            height: 20px;
            margin-right: 10px;
        }
        .title {
            font-size: 30px;
            font-weight: bold;
            color: white;
            padding-top: 7px;
            padding-bottom: 7px;
            padding-right: 20px;
            padding-left: 20px;
            text-align: center;
            background-color: #fb4e0b;
            position: fixed;
            width: 70.50%; 
            top: 80px;
            z-index: 9999;
        }
        .left {
            float: left;
        }
        .right {
            float: right;
        }  
        .text {
            color: #fb4e0b;
            font-size: 50px;
            font-weight: bold;
            font-style: italic;
        }
        .small-header {
            font-size: 18px;
            font-weight: bold;
            color: #000000;
            padding-top: 30px;
            padding-bottom: 5px;
            text-align: left;
            z-index: 9999;
        }
    </style>
""", unsafe_allow_html=True)

# Displaying the icon and "Hi, user" message in the top-right corner --------------Newly Added-----------
st.markdown(
    """
    <div class="user-greeting-container">
    <div class="user-greeting">
        <img src="https://img.icons8.com/ios/452/user-male-circle.png" alt="user icon" />
        Hi, Akeel
    </div>
</div>
    """,
    unsafe_allow_html=True
)#------Till Here-----------------

# Header
st.markdown("""
    <div class="title">
        <span class="left">HEDISAbstrator.AI</span>
        <span class="right">EXL</span>
    </div>
    """, unsafe_allow_html=True)


summarization_file_path="temp_files\\{}_{}_content.txt"
folder_path="temp_files\\"

def render_section(data: Union[dict, list, str], level=0):
  
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                with st.expander(f"📂 {key}"):
                    render_section(value, level + 1)
            else:
                st.markdown(f"<ul><li><strong>{key}:</strong> {value}</li></ul>", unsafe_allow_html=True)

    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                with st.container():
                    st.markdown("---")
                    render_section(item, level + 1)
            else:
                st.markdown(f"- {item}")
    else:
        st.markdown(f"{data}")

def load_content(summarization_file,selected_file):
    with open(summarization_file,'r') as f:
        summary_data=f.read()

        summary_data=summary_data.replace("```",'').replace('json','')

    summary = json.loads(summary_data)

    selected_file =selected_file if selected_file.endswith('.pdf') else selected_file+'.pdf'
    st.markdown(f"<p style='font-size: 1.3rem; font-weight: 400;'>File Name: {selected_file}</p>", unsafe_allow_html=True)

    # Summary Sections
    for section, content in summary.items():
        if section == 'Conclusion':
            content=[content]

        st.markdown(f"<div class='section-header'>🔹 {section}</div>", unsafe_allow_html=True)
        render_section(content)

def show_summarizarion(file_name,measure='summarize'):
    prefix=file_name.replace('.pdf','')
    summarization_file=summarization_file_path.format(prefix, measure)

    #quickfix -- padding only
    st.markdown("""
        <div style="width: 20%; padding: 25px; border: 1px solid white; background-color: #f9f9f9;"></div>
        """, unsafe_allow_html=True)

    load_content(summarization_file,file_name)
    
def show_summarization_via_search_box(measure='summarize'):
    file_suffix='_summarize_content.txt'
    all_files = os.listdir(folder_path)
    summarize_files = [f for f in all_files if "summarize" in f.lower()]

    summarize_files=[i.replace(file_suffix,'') for i in summarize_files]

    summarize_files=["-- Select a file --"] + summarize_files

    st.markdown("<p style='font-size: 1.3rem; font-weight: 600;'>Select a file to view summary</p>", unsafe_allow_html=True)
    if summarize_files:
      selected_file = st.selectbox("", summarize_files)

      if selected_file != "-- Select a file --":
        try:
            prefix=selected_file
            summarization_file=summarization_file_path.format(prefix, measure)
            load_content(summarization_file,selected_file)
            return selected_file
        except Exception as e:
            st.error(f"Error in loading summary of file: {selected_file}")
      else:
          st.info("Please select a file to continue.")
          return 'None'

def show_messages():
    for msg in st.session_state.messages:
        sender = "Hedis AI" if msg["role"] == "Hedis AI" else "You"
        st.markdown(
                    f"""
                    <p style='font-size:16px; font-family:Arial, sans-serif;'>
                        <b>{sender}:</b> {msg['text']}
                    </p>
                    """,
                    unsafe_allow_html=True )


def show_bot(file_name):
    print(f"file_name={file_name}")
        
    #Initialize Session State 
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "Hedis AI", "text": "Hello! How can I assist you?"}]

    st.markdown("""
        <style>
            .chat-popup {
                position: fixed;
                bottom: 20px;
                right: 30px;
                border: 1px solid #ccc;
                background-color: white;
                width: 300px;
                z-index: 100;
                border-radius: 10px;
                box-shadow: 0 0 10px rgba(0,0,0,0.2);
            }
            .chat-header {
                background-color: #fb4e0b;
                color: white;
                padding: 10px;
                font-weight: bold;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
            .chat-body {
                max-height: 300px;
                overflow-y: auto;
                padding: 10px;
                font-size: 14px;
            }
            .chat-footer {
                padding: 10px;
                border-top: 1px solid #ccc;
            }
            .chat-footer input[type="text"] {
                width: 100%;
                padding: 8px;
                box-sizing: border-box;
            }
        </style>
    """, unsafe_allow_html=True)

    # Chat UI
    # st.markdown('<div class="chat-popup visible" id="chat-panel">', unsafe_allow_html=True)
    st.markdown('<div class="chat-header">HEDIS Chatbot</div>', unsafe_allow_html=True)
    st.markdown('<div class="chat-body">', unsafe_allow_html=True)

    # Display chat messages
    show_messages()

    st.markdown('</div>', unsafe_allow_html=True)

    # Input and Submit form
    with st.form(key="chat_form", clear_on_submit=True):
        user_quesion = st.text_input("Type your question...", label_visibility="collapsed")
        submitted = st.form_submit_button("Send")

    # Process submission
    if submitted and user_quesion:
        # Append user message
        st.session_state.messages.append({"role": "user", "text": user_quesion})

        with st.spinner("Processing"):
            try:
                #openai prompt logic
                bot_response, confidence_score = get_bot_response(user_quesion,file_name) #E.g file_name= Linda_Test_Record_2420.pdf
                st.session_state.messages.append({"role": "Hedis AI", "text": bot_response})
            except Exception as e:
                print(e)
                logging.info(SCRIPT+" %r", f"ERROR: {e}")
                st.session_state.messages.append({"role": "Hedis AI", "text": "Try again later."})
                st.info("Try again later.")

        # show_messages()
        st.experimental_rerun()

    else:
        if file_name=='None':
            st.info("Please select a file from above section for a Hedis AI bot.")

    if file_name != 'None' and not submitted:
        st.info("Please type your question and press send to get a response from the Hedis AI bot.")

    # Close the chat box
    st.markdown('</div>', unsafe_allow_html=True)



file_name = (
    st.session_state.uploaded_files.name
    if st.session_state.get("uploaded_files") and hasattr(st.session_state.uploaded_files, "name")
    else "NOT_FOUND"
)
print(f"AK: {file_name}")
if file_name == "NOT_FOUND":
    file_name_dd=show_summarization_via_search_box()
    if  file_name_dd != 'None':
        show_bot(file_name_dd)
else:
    show_summarizarion(file_name)

    show_bot(file_name)


    



