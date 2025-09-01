import streamlit as st
from typing import Union
import json
import os
import fitz
import time
from hedis_openai import prepare_data_for_summarization

st.set_page_config(layout="wide",page_title="HEDISAbstrator.AI")

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
            width: 76%; 
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
        Hi, Ayush
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



file_name = (
    st.session_state.uploaded_files.name
    if st.session_state.get("uploaded_files") and hasattr(st.session_state.uploaded_files, "name")
    else "NOT_FOUND"
)
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
    st.image(img, caption=f"Page {page_number + 1}", use_column_width=True)

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

def handle_exceptions(st,error_message):
        
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


def add_bot():
    st.markdown("""
        <style>
        .chatbot-button {
            position: fixed;
            bottom: 30px;
            right: 30px;
            z-index: 10000;
            background-color: #fb4e0b;
            color: white;
            border: none;
            border-radius: 50px;
            padding: 14px 20px;
            font-size: 16px;
            font-weight: bold;
            box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.2);
            cursor: pointer;
        }

        .chatbot-button:hover {
            background-color: #d8430c;
        }
        </style>

        <script>
        const streamlitChatBotClick = () => {
            const streamlitEvent = new CustomEvent("chatbotButtonClicked");
            window.dispatchEvent(streamlitEvent);
        };
        </script>

        <button class="chatbot-button" onclick="streamlitChatBotClick()" title="Work in progress">💬 HEDIS AI Bot</button>
    """, unsafe_allow_html=True)

    # event listener
    chatbot_button_clicked = st.experimental_get_query_params().get("chatbot", ["false"])[0] == "true"

    # JS to send URL param to Streamlit
    st.markdown("""
        <script>
        window.addEventListener("chatbotButtonClicked", function() {
            const url = new URL(window.location);
            url.searchParams.set("chatbot", "true");
            window.location.href = url.toString();
        });
        </script>
    """, unsafe_allow_html=True)

    # Display chatbot UI if button clicked
    if chatbot_button_clicked:
        print("Clicked")
        with st.sidebar:
            st.markdown("## 🤖 HEDIS AI Bot")
            user_input = st.text_input("Ask a question:")
            if user_input:
                st.markdown(f"**Bot:** You asked _{user_input}_ — here's a placeholder response.")


def load_new_file_for_summarization():

    #quickfix -- padding only
    st.markdown("""
        <div style="width: 20%; padding: 25px; border: 1px solid white; background-color: white;"></div>
        """, unsafe_allow_html=True)

    st.session_state.uploaded_files = st.file_uploader('**Upload a PDF for summarization:**', type=["pdf"])

    if st.session_state.uploaded_files is not None:
        # st.write("Uploaded File:", st.session_state.uploaded_files.name)    
        saved_pdf_path, file_name =get_uploaded_pdf_path(st.session_state.uploaded_files)

        generate_summarization(file_name)

        return saved_pdf_path,file_name
    else:
        return 'None','None'

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

    #----------------------- TABS section END--------------------------


if file_name == "NOT_FOUND":
    #show_summarization_via_search_box()
    # file_name= get_summarization_file() #drop down
     
    print("test_log")
    saved_path, file_name= load_new_file_for_summarization()
    if file_name != 'None':
        with st.spinner('Processing...'):
            time.sleep(6)
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
    show_tabs_and_pdf(file_name)



add_bot()