import streamlit as st
from typing import Union
import json
import os
import fitz
import time
from hedis_openai import prepare_data_for_summarization,get_bot_response
import logging

SCRIPT='SUMMARIZATION.py'

st.set_page_config(layout="wide",page_title="HEDISAbstractor.AI")

if 'page_number' not in st.session_state:
    st.session_state['page_number'] = 1

if "uploaded_files" not in st.session_state:
    st.session_state["uploaded_files"] = []

root_dir=os.getcwd()
uploaded_files_path=os.path.join(root_dir,'uploaded_files')

if not  os.path.exists(uploaded_files_path):
    os.makedirs(uploaded_files_path)

file_path_extracted_summarization="temp_files\\{}_{}_content.txt"

# st.markdown("""
#     <style>
#         .block-container {
#             padding-top: 2rem;
#             padding-bottom: 2rem;
#         }
#         h1 {
#             font-size: 2.8rem !important;
#         }
#         .section-header {
#             font-size: 1.9rem !important;
#             font-weight: 700;
#             margin-top: .5rem;
#             margin-bottom: .1rem;
#             color: #1f4e79;
#         }
#         .stMarkdown, .markdown-text-container, .element-container {
#             font-size: 1.1rem !important;
#         }
#         ul {
#             padding-left: 1.2rem;
#         }
#        li {
#             font-size: 1.15rem !important;
#             margin-bottom: 0.3rem;
#             line-height: 1;
#         }
#         .stExpanderHeader {
#             font-size: 1.1rem !important;
#         }
#         .user-greeting-container {
#         position: fixed; 
#         top: 40px; 
#         right: 0; 
#         background-color: white; 
#         display: flex; 
#         justify-content: flex-end; 
#         align-items: center; 
#         padding: 10px 20px; 
#         z-index: 1000; 
#         width: 100%; 
#         box-sizing: border-box; 
#     }
#     .user-greeting {
#         display: flex;
#         align-items: center;
#         #justify-content: fixed-end; /* Align to the right */
#         #padding: 10px 20px; /* Spacing for the text and icon */
#         font-size: 16px;
#         font-weight: bold;
#         color: black;
#         margin-right: 80px;
#     }
#     .user-greeting img {
#         width: 20px;
#         height: 20px;
#         margin-right: 10px; /* Space between the icon and text */
#     }
#     .title {
#         font-size: 30px;
#         font-weight: bold;
#         color: white;
#         padding-top: 7px;
#         padding-bottom: 7px;
#         padding-right: 20px;
#         padding-left: 20px;
#         text-align: center;
#         background-color: #fb4e0b;
#         position: fixed; /* Make the title fixed at the top */
#         width: 70.50%; 
#         top: 80px;
#         z-index: 9999; /* Keep it above other elements */
#         #top: 0;
#     }
    
#     .left {
#         float: left;
#     }
#     .right {
#         float: right;

#     }  
#     .text {
#         color: #fb4e0b;
#         font-size:50px;
#         font-weight: bold;
#         font-style: italic;
#     }
#     .small-header {
#         font-size: 18px;
#         font-weight: bold;
#         color: #000000;
#         padding-top: 30px;
#         padding-bottom: 5px;
#         text-align: left;
#         z-index: 9999;
#         #top: 0;
#     }
#     </style>
# """, unsafe_allow_html=True)
st.markdown(
    """
    <style>
    /* UI Changes Import Google Fonts for better typography */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* UI Changes Global font and base styles */
    .stApp {
        font-family: 'Inter', sans-serif;
        background: linear-gradient(135deg, #FFFFFF 0%, #FFFFFF 100%);
        min-height: 100vh;
    }
    
    /* UI Changes Main content area with glassmorphism effect */
    .main .block-container {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
        padding: 2rem;
        margin-top: 2rem;
    }
    
    /* UI Changes Enhanced user greeting container */
    .user-greeting-container {
        position: fixed; 
        top: 0px;
        height: 80px;
        right: 0; 
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        display: flex; 
        justify-content: flex-end; 
        align-items: center; 
        padding: 15px 25px;
        z-index: 1000; 
        width: 100%; 
        box-sizing: border-box;
        border-bottom: 1px solid rgba(251, 78, 11, 0.1);
    }
    
    /* UI Changes Enhanced user greeting with animation */
    .user-greeting {
        display: flex;
        align-items: center;
        font-size: 16px;
        font-weight: 600;
        color: #333;
        margin-right: 80px;
        transition: all 0.3s ease;
        padding: 8px 16px;
        border-radius: 25px;
        background: linear-gradient(45deg, #fb4e0b, #ff6b35);
        color: white;
        box-shadow: 0 4px 15px rgba(251, 78, 11, 0.3);
    }
    
    .user-greeting:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(251, 78, 11, 0.4);
    }
    
    .user-greeting img {
        width: 24px;
        height: 24px;
        margin-right: 12px;
        filter: brightness(0) invert(1);
    }
    
    /* UI Changes Enhanced title with gradient and animation */
    .title {
        font-size: 32px;
        font-weight: 700;
        color: white;
        padding: 10px;
        text-align: center;
        background: linear-gradient(135deg, #fb4e0b 0%, #ff6b35 100%);
        position: fixed;
        width: 78%;
        top: 82px;
        z-index: 9999;
        border-radius: 0 0 20px 20px;
        box-shadow: 0 8px 32px rgba(251, 78, 11, 0.4);
        backdrop-filter: blur(5px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        animation: slideDown 0.6s ease-out;
    }
    
    /* UI Changes Title animation */
    @keyframes slideDown {
        from {
            opacity: 0;
            transform: translateY(-50px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .left {
        float: left;
    }
    .right {
        float: right;
    }
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
        Hi, Ayush
    </div>
</div>
    """,
    unsafe_allow_html=True
)#------Till Here-----------------

# Header
st.markdown("""
    <div class="title">
        <span class="left">HEDISAbstractor.AI</span>
        <span class="right">EXL</span>
    </div>
    """, unsafe_allow_html=True)



file_name = (
    st.session_state.uploaded_files.name
    if st.session_state.get("uploaded_files") and hasattr(st.session_state.uploaded_files, "name")
    else "NOT_FOUND"
)

#---AYU ADDED for Data repository page navigation
# Creating session state for file name which is getting from Data Repository page. 
#  SO, if user is navigating from Data Repository page, file name will be available in session state else 
#  the above logic will be used to get the file name while navigating from New File Intake page."""

if file_name == "NOT_FOUND" or file_name is None:
    file_name = st.session_state["files_name"] if st.session_state.get("files_name") else "NOT_FOUND"

summarization_file_path="temp_files\\{}_{}_content.txt"
folder_path="temp_files\\"

def render_section(data: Union[dict, list, str], level=0):
    indent = "&nbsp;" * 0 * level  # 4 non-breaking spaces per level

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                st.markdown(f"{indent}<h5>    🔘 {key}</h5>", unsafe_allow_html=True)
                st.markdown(f"{indent}<hr>", unsafe_allow_html=True)
                render_section(value, level + 1)
            else:
                st.markdown(f"{indent}<ul><li><strong>{key}:</strong> {value}</li></ul>", unsafe_allow_html=True)

    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                with st.container():
                    st.markdown(f"{indent}<hr>", unsafe_allow_html=True)
                    render_section(item, level + 1)
            else:
                st.markdown(f"{indent}- {item}", unsafe_allow_html=True)
    else:
        st.markdown(f"{indent}{data}", unsafe_allow_html=True)

def load_content(summarization_file,selected_file):
    with open(summarization_file,'r') as f:
        summary_data=f.read()

        summary_data=summary_data.replace("```",'').replace('json','')

    summary = json.loads(summary_data)

    selected_file =selected_file if selected_file.endswith('.pdf') else selected_file+'.pdf'
    st.markdown(f"<p style='font-size: 1.3rem; font-weight: 400;'>File Name: {selected_file}</p>", unsafe_allow_html=True)

    # Summary Sections
    for section, content in summary.items():
        if section == 'Conclusion' or 'Page' in section :
            continue #content=[content]

        st.markdown(f"<div class='section-header'>🔹 {section}</div>", unsafe_allow_html=True)
        render_section(content)

def load_conclusion_content(file_name,measure='summarize'):

    prefix=file_name.replace('.pdf','')
    summarization_file=summarization_file_path.format(prefix, measure)

    with open(summarization_file,'r') as f:
        summary_data=f.read()

        summary_data=summary_data.replace("```",'').replace('json','')

    summary = json.loads(summary_data)

    file_name =file_name if file_name.endswith('.pdf') else file_name+'.pdf'
    st.markdown(f"<p style='font-size: 1.3rem; font-weight: 400;'>File Name: {file_name}</p>", unsafe_allow_html=True)

    # Summary Sections
    for section, content in summary.items():
        if section == 'Conclusion':
            content=[content]
            st.markdown(f"<div class='section-header'>🔹 {section}</div>", unsafe_allow_html=True)
            render_section(content)       

    if  'Conclusion' not in summary:
        st.info("Conclusion not present.")

def load_pages_summary_content(file_name,measure='summarize'):

    pdf_page_number=st.session_state['page_number']
    json_page_key= f"Page{pdf_page_number}"

    prefix=file_name.replace('.pdf','')
    summarization_file=summarization_file_path.format(prefix, measure)

    with open(summarization_file,'r') as f:
        summary_data=f.read()

        summary_data=summary_data.replace("```",'').replace('json','')

    summary = json.loads(summary_data)

    file_name =file_name if file_name.endswith('.pdf') else file_name+'.pdf'
    st.markdown(f"<p style='font-size: 1.3rem; font-weight: 400;'>File Name: {file_name}</p>", unsafe_allow_html=True)

    # Summary Sections
    for section, content in summary.items():
        if  section == json_page_key:
            content=[content]
            st.markdown(f"<div class='section-header'>🔹 {section}</div>", unsafe_allow_html=True)
            render_section(content)       

    # if  'Page' not in summary:
    #     st.info("Page wise summary not available.")


def show_summarizarion(file_name,measure='summarize'):
    prefix=file_name.replace('.pdf','')
    summarization_file=summarization_file_path.format(prefix, measure)

    #quickfix -- padding only
    # st.markdown("""
    #     <div style="width: 20%; padding: 25px; border: 1px solid white; background-color: #f9f9f9;"></div>
    #     """, unsafe_allow_html=True)

    load_content(summarization_file,file_name)
    
def get_summarization_file(measure='summarize'):
    file_suffix='_summarize_content.txt'
    all_files = os.listdir(folder_path)
    summarize_files = [f for f in all_files if "summarize" in f.lower()]

    summarize_files=[i.replace(file_suffix,'') for i in summarize_files]

    summarize_files=["-- Select a file --"] + summarize_files

    st.markdown("<p style='font-size: 1.3rem; font-weight: 600;'>Select a file to view summary</p>", unsafe_allow_html=True)
    if summarize_files:
      selected_file = st.selectbox("", summarize_files)

      if selected_file != "-- Select a file --":
        return selected_file
      else:
          st.info("Please select a file to continue.")
          return 'None'

def display_pdf_page(page_number, pdf_document):
    page = pdf_document[page_number]
    pix = page.get_pixmap()
    img = pix.tobytes("png")
    st.image(img, caption=f"Page {page_number + 1}", use_container_width=True)

def get_pdf_location(selected_file_name):
    selected_file_name=selected_file_name.strip()
    selected_file_name=selected_file_name if selected_file_name.endswith('.pdf') else selected_file_name+'.pdf'

    pdf_location=f'uploaded_files\\{selected_file_name}'
    
    return pdf_location

def get_uploaded_pdf_path(uploaded_file):

    # Create a temporary file to save the uploaded PDF -- this is needed to get the location of file; file location is needed for convert_pdf function to convert pdf into JPG 
    actual_file_name=uploaded_file.name
    # save_file_name='file_to_be_processed.pdf'
    # save_path = os.path.join(temp_files_path, save_file_name)

    save_path = os.path.join(uploaded_files_path, actual_file_name)

    # Save uploaded file to that path
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # st.success(f"Temp File saved at: `{os.path.abspath(save_path)}`")

    return save_path, actual_file_name

def generate_summarization(file_name):
    prefix=file_name.replace('.pdf','')
    summarize_file=file_path_extracted_summarization.format(prefix, 'summarize')
    
    if not os.path.exists(summarize_file):
        read_from_local=False
        prepare_data_for_summarization(file_name, read_from_local)

def handle_exceptions(st,error_message,file_type=''):
        
        #APIConnectionError: Error communicating with OpenAI: ('Connection aborted.', ConnectionResetError(10054, 'An existing connection was forcibly closed by the remote host', None, 10054, None))
        if 'ConnectionResetError' in error_message:
            st.error("Connection Error: An existing connection was forcibly closed by the remote host")
            # st.stop()


        #openai.error.AuthenticationError: No API key provided
        if 'AuthenticationError: No API key provided' in error_message:
            st.error("AuthenticationError: No API key provided")
            # st.stop()

        #openai.error.RateLimitError: You exceeded your current quota, please check your plan and billing details.  
        if 'openai.error.RateLimitError: You exceeded your current quota' in error_message:
            st.error("RateLimitError: You exceeded your current quota.")
            # st.stop()  

        #FileNotFoundError: [Errno 2] No such file or directory: 
        if 'FileNotFoundError' in error_message:
            st.error(f"{file_type} not available. Please generate the summarization.")

def load_new_file_for_summarization():

    #quickfix -- padding only
    st.markdown("""
        <div style="width: 20%; padding: 25px; border: 1px solid white; background-color: white;"></div>
        """, unsafe_allow_html=True)

    st.session_state.uploaded_files = st.file_uploader('**Upload a PDF for summarization:**', type=["pdf"])

    if st.session_state.uploaded_files is not None:
        with st.spinner('Processing...'):
            time.sleep(6)
        # st.write("Uploaded File:", st.session_state.uploaded_files.name)    
        saved_pdf_path, file_name =get_uploaded_pdf_path(st.session_state.uploaded_files)

        generate_summarization(file_name)

        return saved_pdf_path,file_name
    else:
        return 'None','None'

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

    st.markdown("""
    <style>
    /* Style the whole expander container */
    .stExpander {
        border: 1px solid #fb4e0b;
        border-radius: 10px;
        overflow: hidden;
        margin-bottom: 1rem;
    }

    /* Style the header container */
    .streamlit-expanderHeader {
        background-color: #fb4e0b;
        color: white !important;
        padding: 10px;
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
        transition: background-color 0.3s ease;
    }

    /* Make the header text bold */
    .streamlit-expanderHeader > div > span {
        font-weight: 700 !important;
    }

    /* On hover, keep the text white */
    .streamlit-expanderHeader:hover {
        background-color: #e34700;
        color: white !important;
    }

    .streamlit-expanderHeader:hover span {
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)
        
    with st.expander("💬 HEDIS AI Bot",expanded=True):   
        print("Expanded")
        #Initialize Session State 
        if "messages" not in st.session_state:
            st.session_state.messages = [{"role": "Hedis AI", "text": "Hello! How can I assist you?"}]

        # Chat UI
        # st.markdown('<div class="chat-popup visible" id="chat-panel">', unsafe_allow_html=True)
        # st.markdown('<div class="chat-header">HEDIS Chatbot</div>', unsafe_allow_html=True)
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
                    # time.sleep(3)
                    # a=2/0  
                    bot_response, confidence_score = get_bot_response(user_quesion,file_name) #E.g file_name= Linda_Test_Record_2420.pdf
                    st.session_state.messages.append({"role": "Hedis AI", "text": bot_response})
                except Exception as e:
                    print(e)
                    logging.info(SCRIPT+" %r", f"ERROR: {e}")
                    st.session_state.messages.append({"role": "Hedis AI", "text": "Try again later."})
                    st.info("Try again later.")

            # show_messages()
            # st.experimental_rerun()
            st.rerun()
            
        else:
            if file_name=='None':
                st.info("Please select a file from above section for a Hedis AI bot.")

        if  submitted and  len(user_quesion.strip())<5:
            st.warning("Please type your question and press send to get a response from the Hedis AI bot.")

        # Close the chat box
        st.markdown('</div>', unsafe_allow_html=True)


def show_tabs_and_pdf(selected_file_name):
    tabs_section, pdf_section=st.columns([0.5, 0.5], gap="large")

    # st.button("BUTTON", key="info", help="Hedis AI Bot")

    #=======================PDF section START ============================
    pdf_location= get_pdf_location(selected_file_name)
    if pdf_location and os.path.exists(pdf_location):
                pdf_document = fitz.open(pdf_location)
                with pdf_section:
                    with st.container():
                        st.markdown('<div class="page-input-container">', unsafe_allow_html=True)
                        #quickfix -- padding only
                        st.markdown("""
                            <div style="width: 20%; padding: 25px; border: 1px solid white; background-color: white;"></div>
                            """, unsafe_allow_html=True)

                        print(f"LOG_AK1:{st.session_state['page_number']}")
                        page_input = st.number_input(
                            "Enter page number",
                            min_value=1,
                            max_value=len(pdf_document),
                            value=st.session_state['page_number'],
                            key="page_input"
                        )
                        print(f"LOG_AK2:{page_input}")
                        if page_input != st.session_state['page_number']:
                            st.session_state['page_number'] = page_input
                        st.markdown('</div>', unsafe_allow_html=True)
                        print(f"LOG_AK3:{st.session_state['page_number']}")
                        display_pdf_page(st.session_state['page_number'] - 1, pdf_document)

    else:
        with pdf_section:
            with st.container(): #height=775, border=True
                st.warning("PDF file not found or inaccessible.", icon="⚠️")
    #=======================PDF section END ============================


    #----------------------- TABS section START--------------------------
    available_tabs = ['Page Wise Summary', 'Segmented Summary', 'Conclusion']

    try:
        
        with tabs_section:
            #quickfix -- padding only
            st.markdown("""
                <div style="width: 20%; padding: 25px; border: 1px solid white; background-color: white;"></div>
                """, unsafe_allow_html=True)
            
            tabs = st.tabs(available_tabs)

            # Page Wise Summary
            with tabs[0]:
                load_pages_summary_content(file_name)

            #segmanted summary
            with tabs[1]:
                show_summarizarion(file_name)
            with tabs[2]:
                load_conclusion_content(file_name)
    except Exception as e:
        error_message=str(e)
        msg= "EXCEPTION: ", type(e).__name__, '----',error_message
        # print(msg)

        handle_exceptions(st,error_message=msg, file_type='Summarization')

    #----------------------- TABS section END--------------------------


if file_name == "NOT_FOUND":
    #show_summarization_via_search_box()
    # file_name= get_summarization_file() #drop down
    # print("test_log")
    saved_path, file_name= load_new_file_for_summarization()
    if file_name != 'None':
        # with st.spinner('Test Processing...'):
        #     time.sleep(6)
        show_bot(file_name)
        show_tabs_and_pdf(file_name)
else:

    #quickfix -- padding only
    st.markdown("""
        <div style="width: 20%; padding: 25px; border: 1px solid white; background-color: white;"></div>
        """, unsafe_allow_html=True)

    temp = st.file_uploader('**Upload a PDF for summarization:**', type=["pdf"])
    if temp is not None:
        file_name= temp.name
    #st.session_state.uploaded_files
#   show_summarizarion(file_name)
    show_bot(file_name)
    show_tabs_and_pdf(file_name)

#  #quickfix -- padding only
# st.markdown("""
#     <div style="width: 20%; padding: 25px; border: 1px solid white; background-color: white;"></div>
#     """, unsafe_allow_html=True)
# with st.popover("Open popover"):
#     st.markdown("Hello World 👋")
#     name = st.text_input("What's your name?")
# st.write(name)

# add_bot()