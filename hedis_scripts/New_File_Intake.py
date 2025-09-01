import warnings
warnings.filterwarnings("ignore")
import openai
import streamlit as st
import base64
from PIL import Image
import io
import pandas as pd
from pathlib import Path
#from google.api_core.client_options import ClientOptions
#from google.cloud import documentai
import os
from typing import List, Sequence
import tempfile
from os.path import splitext, basename, getmtime, join, exists
from datetime import datetime
import pandas as pd
import pyodbc
from streamlit_js_eval import streamlit_js_eval 
import time
import re
from dotenv import load_dotenv
import uuid
from hedis_openai import start_extration_and_DbInsertion_process, test_function, batch_start_extration_and_DbInsertion_process
from utils import database
from utils.spec_modal_utils import load_measure_spec, render_spec_modal#syn:added for spec module
import streamlit_extras.switch_page_button  as page_switcher
#from htmlTemplates import cbp_html_template
import logging
import shutil
import json
import threading
import ast


measure_names=['BCS','BPD','CBP','CCS','COL','EED','HBD','LSD','PPC']


#st.write(f"Screen width is {streamlit_js_eval(js_expression='screen.width',key="SCR")}")
#st.write(f"Screen width is {streamlit_js_eval(js_expressions='screen.width',key = 'SCR')}")

# # Load variables from .env file
load_dotenv()

# Set API key for OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")


SCRIPT='New_FIle_Intake'
current_timestamp=datetime.now()
timestamp=current_timestamp.strftime("%m_%d_%Y") #_%H_%M_%S

confidence_score_json_path="temp_files\\confidence_score.json"
batch_status_json_path="temp_files\\batch_files_status.json"

batch_file_name='BATCH_FILE.pdf'

#Ak
root_dir=os.getcwd()
temp_files_path=os.path.join(root_dir,'temp_files')
uploaded_files_path=os.path.join(root_dir,'uploaded_files')

if not  os.path.exists(temp_files_path):
    os.makedirs(temp_files_path)

if not  os.path.exists(uploaded_files_path):
    os.makedirs(uploaded_files_path)

#AK
if 'hedis_openai' not in st.session_state:
    st.session_state.hedis_openai = False

if 'single_done' not in st.session_state:
    st.session_state.single_done = False

if 'load_single_page' not in st.session_state:
    st.session_state.load_single_page = True

if 'page_loaded' not in st.session_state:
    st.session_state['page_loaded'] = False

if 'MY' not in st.session_state:
    st.session_state['MY'] = 1234

if 'summary_flag' not in st.session_state:
    st.session_state['summary_flag'] = False                                          

if 'batch_processing' not in st.session_state:
    st.session_state['batch_processing'] = 'not_started'

#AK
output_excel_file_path= "temp_files\\output.xlsx"


if 'excel_file' not in st.session_state:
    st.session_state['excel_file'] = None

# Clear Streamlit cache to ensure pages are reloaded
st.cache_data.clear()
st.cache_resource.clear()


# Set the page configuration

# Set the page configuration
st.set_page_config(layout="wide", page_title="HEDISAbstrator.AI")
st.markdown(
    """
    <style>
    /* UI Import Google Fonts for better typography */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* UI Global font and base styles */
    .stApp {
        font-family: 'Inter', sans-serif;
        background: linear-gradient(135deg, #FFFFFF 0%, #FFFFFF 100%);
        min-height: 100vh;
    }
    
    /* UI Main content area with glassmorphism effect */
    .main .block-container {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
        padding: 2rem;
        margin-top: 2rem;
    }
    
    /* UI Enhanced user greeting container */
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
    }
    
    /* UI Enhanced user greeting with animation */
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
    
    /* UI Enhanced title with gradient and animation */
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
    
    /* UI Title animation */
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
    .text {
        color: #fb4e0b;
        font-size:50px;
        font-weight: bold;
        font-style: italic;
    }
    .small-header {
        font-size: 18px;
        font-weight: bold;
        color: #000000;
        padding-top: 50px;
        padding-bottom: 5px;
        text-align: left;
        z-index: 9999;
        #top: 0;
    }
    .review-button {
        background-color: #f0f0f0; /* Matches Streamlit's default button background */
        color: #000000; /* Matches Streamlit's default button text color */
        padding: 5px 15px;
        border-radius: 5px;
        font-weight: bold;
        cursor: pointer;
        text-decoration: none;
        border: 1px solid #cccccc; /* Adds a subtle border similar to Streamlit buttons */
        position: absolute;
        top: 0;
        right: 0;
    }
    .review-button:hover {
        background-color: #e0e0e0; /* Subtle hover effect similar to Streamlit buttons */
        color: #000000;
    }
    .modal {
        display: none;
        position: fixed;
        top: 30%;
        left: 65%;
        background-color: white;
        border: 1px solid #ccc;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        z-index: 10001;
        width: 500px;
        min-width: 300px;
        min-height: 200px;
        resize: both;
        overflow: auto;
    }
    .modal-header {
        background-color: #f1f1f1;
        padding: 10px;
        border-bottom: 1px solid #ddd;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .modal-content {
        padding: 20px;
        max-height: 70vh;
        overflow-y: auto;
    }
    .modal.show {
        display: block;
    }
    .info-icon {
        width: 20px;
        height: 20px;
        margin-left: 10px;
        cursor: pointer;
        vertical-align: middle;
        background: none;
        border: none;
        padding: 0;
    }
    .info-icon:hover {
        opacity: 0.7;
    }
    .inline-info-button {
        display: inline-block;
        background: none;
        border: none;
        cursor: pointer;
        font-size: 16px;
        margin-left: 5px;
        vertical-align: middle;
        padding: 0;
    }
    .inline-info-button:hover {
        opacity: 0.7;
    }
    .measure-header {
        display: flex;
        align-items: center;
    }
    details {
        margin-bottom: 10px;
    }
    summary {
        font-weight: bold;
        cursor: pointer;
        padding: 5px;
        background-color: #f9f9f9;
        border: 1px solid #ddd;
    }
    </style>
    """,
    unsafe_allow_html=True
)


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
)

# Header
st.markdown("""
    <div class="title">
        <span class="left">HEDISAbstractor.AI</span>
        <span class="right">EXL</span>
    </div>
    """, unsafe_allow_html=True)

#AK
def set_logging(root_dir):

    print('Initiate logging ...')
    log_file_name="HEDIS_"+timestamp+".txt"
    logs_path=os.path.join(root_dir,'LOGS')
    logs_full_path=f"{logs_path}\\{log_file_name}"

    print(f"LOG: {logs_path}")

    os.makedirs(logs_path, exist_ok=True)

    # Remove existing handlers (important in Streamlit)
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    file_handler = logging.FileHandler(logs_full_path, mode='a')
    console_handler = logging.StreamHandler()

    file_handler.setLevel(logging.INFO)
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])

    logging.info("Logging to both file and console.")


#AK
def get_uploaded_pdf_path(uploaded_file, batch=False):

    # Create a temporary file to save the uploaded PDF -- this is needed to get the location of file; file location is needed for convert_pdf function to convert pdf into JPG 
    if batch:
        actual_file_name=batch_file_name
    else:
        actual_file_name=uploaded_file.name

    save_path = os.path.join(uploaded_files_path, actual_file_name)

    # Save uploaded file to that path
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # st.success(f"Temp File saved at: `{os.path.abspath(save_path)}`")

    return save_path, actual_file_name

def display_pdf(uploaded_file):
    pdf_data = uploaded_file.read()
    base64_pdf = base64.b64encode(pdf_data).decode('utf-8')
    pdf_display = f'<embed src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf">'
    st.markdown(pdf_display, unsafe_allow_html=True)

def generic_info(filepath):  
    df = pd.read_excel(filepath, sheet_name=None)
    generic = df.get("memberinfo").head()
    return generic.iloc[[0][-3:]] if generic is not None else pd.DataFrame()

def reset_checkboxes():
    streamlit_js_eval(js_expressions="parent.window.location.reload()")
    # for key in st.session_state:
    #     if 'checkbox' in key:
    #         st.session_state[key] = False

# Database connection using environment variables
def create_connection():
    cnxn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server_name};"
        f"DATABASE={database_name};"
        f"Trusted_Connection=yes;"
    )
    try:
        cnxn = pyodbc.connect(cnxn_str)
        return cnxn, cnxn.cursor()
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None, None
    

# Function to create database connection
# def create_connection():
#     cnxn_str = (
#                 "Driver={ODBC Driver 17 for SQL Server};"
#                 "Server=LAPTOP-AG7RJLSV\\SQLEXPRESS;"
#                 "Database=demo;"
#                 "Trusted_Connection=yes;"
#             )
#     try:
#         cnxn = pyodbc.connect(cnxn_str)
#         cursor = cnxn.cursor()
#     except Exception as e:
#         st.error(f"Database connection error: {e}")
    
#     return cursor 

# def create_connection():
#     return pyodbc.connect(
#                 "Driver={ODBC Driver 17 for SQL Server};"
#                 "Server=LAPTOP-AG7RJLSV\\SQLEXPRESS;"
#                 "Database=EXL;"
#                 "Trusted_Connection=yes;"
#             )

def extract_member_id(filename):
    name_part = filename.replace(".pdf", "")
    digits = ''.join(filter(str.isdigit, name_part))
    return digits[-4:] if len(digits) >= 4 else 0

def get_auto_select_measures(filename, available_measures):
    member_id = extract_member_id(filename)
    if member_id is not None : #and member_id.isdigit()
        # cursor = create_connection()
        engine=database.get_db_connection(server_name,database_name)
        if engine:
            # Check if member_id exists in the gap table
            # query = f"SELECT member_id, BCS_GAP, COL_GAP, BPD_GAP, CBP_GAP, HBD_GAP, EED_GAP, IMA_GAP, CCS_GAP FROM gap WHERE member_id = {member_id}"
            # cursor.execute(query, (member_id,))
            # row = cursor.fetchone()
            tag, row=database.run_query(engine,member_id,table_name='gap')

            if row and tag == 'normal':
                # st.write("Member already exists.")
                pass
            elif tag == 'not_present':
                st.write("No matching record found in the gap table. Selecting all available measures.")
            
            if row:
                n_flags= filter(lambda k: row[k] == 'N', row)
                n_flag_measures=list(map(lambda x:x.replace('_GAP',''), n_flags))

                y_flags= filter(lambda k: row[k] == 'Y', row)
                y_flag_measures=list(map(lambda x:x.replace('_GAP',''), y_flags))

                if n_flag_measures:
                    # st.write(f"Measures with 'N' value: {', '.join(n_flag_measures)}")
                    pass

                # if 'IMA' in n_flag_measures:
                #     n_flag_measures.remove('IMA')   

                n_flag_measures_final = [measure for measure in n_flag_measures if measure in available_measures]
                return n_flag_measures_final,y_flag_measures, 'Member compliant for'  # Return measures with 'N' values
            else:
                return [], "New member"
    else:
        st.write(f"Invalid member_id extracted from filename: {filename}")
    return [], "New member"
# [NEW] Added new function to automatically select measures based on database GAP table#till here

def list_measures_with_y(filename, available_measures):
    member_id = extract_member_id(filename)
    measures_with_y = []
    if member_id is not None:  #AK not needed- and member_id.isdigit()
        conn, cursor = create_connection()
        if cursor:
            try:
                query = f"SELECT member_id, BCS_GAP, COL_GAP, BPD_GAP, CBP_GAP, HBD_GAP, EED_GAP, IMA_GAP, CCS_GAP,LSD_GAP,PPC_GAP FROM gap WHERE member_id = {member_id}"
                print(query)
                cursor.execute(query)
                row = cursor.fetchone()
                if row:
                    all_measures = measure_names
                    for idx, measure in enumerate(all_measures):
                        if row[idx + 1] == 'Y' and measure in available_measures:
                            measures_with_y.append(measure)
                return measures_with_y
            finally:
                cursor.close()
                conn.close()
    return measures_with_y

def update_selected_boxes():
    st.session_state['selected_boxes'] = st.session_state.get(st.session_state['multiselect_key'], [])


def check_member_exists(member_id):
    engine=database.get_db_connection(server_name,database_name) 
    if engine:
        is_present=database.is_member_present(engine,member_id, table_name='memberinfo',file_name=None)
    else:
        is_present=0
    
    return is_present

def update_selected_boxes():
    st.session_state['selected_boxes'] = st.session_state.get(st.session_state['multiselect_key'], [])

def clean_up():
    #CLEANUP 
    extracted_images_output_path = "output_pdf_images"  # Directory for converted images
    if os.path.exists(extracted_images_output_path):
        shutil.rmtree(extracted_images_output_path)

#SYND
def fetch_compliance_status(member_id, measures):
    """
    Fetch the raw remark value for each measure from the database.
    
    Args:
        member_id (str): The member ID to query.
        measures (list): List of measure names (e.g., ['BCS', 'CBP']).
    
    Returns:
        dict: A dictionary mapping each measure to its raw remark value.
    """
    compliance_status_dict = {}
    if member_id is None or not member_id.isdigit():
        return {measure: "None" for measure in measures}

    # Convert member_id to int to match database schema
    try:
        member_id_int = int(member_id)
    except ValueError:
        return {measure: "None" for measure in measures}

    # Map each measure to its corresponding Remark column
    remark_columns = {
        'BCS': 'Remark_BCS',
        'CBP': 'Remark_CBP',
        'HBD': 'Remark_HBD',
        'COL': 'Remark_COL',
        'BPD': 'Remark_BPD',
        'EED': 'Remark_EED',
        'CCS': 'Remark_CCS'
    }

    conn, cursor = create_connection()
    if not cursor:
        return {measure: "None" for measure in measures}

    try:
        for measure in measures:
            remark_column = remark_columns.get(measure)
            if not remark_column:
                compliance_status_dict[measure] = "None"
                continue

            query = f"SELECT {remark_column} FROM {measure} WHERE Member_id = ? and is_active=1" #Ak added is_active
            cursor.execute(query, (member_id_int,))
            row = cursor.fetchone()
            if row is None:
                compliance_status_dict[measure] = "None"
            elif row[0] is None or str(row[0]).strip() == "":
                compliance_status_dict[measure] = "None"
            else:
                raw_remarks = str(row[0])
                compliance_status_dict[measure] = raw_remarks
    except Exception as e:
        compliance_status_dict = {measure: "None" for measure in measures}
    finally:
        cursor.close()
        conn.close()
    
    return compliance_status_dict

def get_confidence_score():
    with open(confidence_score_json_path,'r') as f:
        data= json.load(f)
    
    return data
#syn:add this for dynmic spec loading
# def load_measure_spec(measurement_year: int, measure_name: str) -> str:
#     base_spec_dir = "C:/Users/asif/Documents/hedis_openapi/spec"
    
#     spec_file_path = os.path.join(
#         base_spec_dir,
#         str(measurement_year),
#         "html",
#         f"{measure_name.lower()}.html"
#     )
    
#     if os.path.exists(spec_file_path):
#         try:
#             with open(spec_file_path, 'r', encoding='utf-8') as file:
#                 html_content = file.read()
#             return html_content
#         except Exception as e:
#             return f"<p>Error loading specification: {str(e)}</p>"
#     else:
#         return f"<p>No specification found for measure {measure_name} in measurement year {measurement_year}.</p>"



def single_page():
    st.write('')
    st.write('')
    st.markdown('<h3 class="small-header">Upload and Extract Center</h1>', unsafe_allow_html=True)
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    measurement_year = st.selectbox('**Measurement Year:**', [2024]) #AK #AYU DEMO #After 27-05 chamge#Syn:

    st.session_state['MY']=measurement_year

    logging.info(SCRIPT+"-single_page(): %r", f"Measurement Year selected: {measurement_year}")

    st.session_state.uploaded_files = st.file_uploader('**Upload a PDF and Process it using GenAI:**', type=["pdf"])

    if st.session_state.uploaded_files is not None:
        st.write("Uploaded File:", st.session_state.uploaded_files.name)
        
        with st.expander("View PDF"):
            display_pdf(st.session_state.uploaded_files)
    
        file_name = st.session_state.uploaded_files.name
        member_id = extract_member_id(file_name)

        logging.info(SCRIPT+"-single_page(): %r", f"file_name: {file_name}, member_id: {member_id}")

        

        # sheet_names = pd.ExcelFile(st.session_state['excel_file']).sheet_names
        sheet_names=measure_names
        print(f"SHEET_NAMES: {sheet_names}")
        logging.info(SCRIPT+"-single_page(): %r", f"SHEET_NAMES: {sheet_names}")

        Col_list = list(sheet_names)
        #Ak
        if 'memberinfo' in Col_list:
            Col_list.remove('memberinfo') ## Col_list=Col_list[1:]

        if 'selected_boxes' not in st.session_state:
            st.session_state['selected_boxes'] = []
        if 'last_uploaded_file' not in st.session_state:
            st.session_state['last_uploaded_file'] = None
        if 'multiselect_key' not in st.session_state:
            st.session_state['multiselect_key'] = str(uuid.uuid4())
        if 'show_modal' not in st.session_state:
            st.session_state['show_modal'] = False
        if 'submitted' not in st.session_state:
            st.session_state['submitted'] = False
        if 'current_measure' not in st.session_state:
            st.session_state['current_measure'] = None
        if 'compliant_measures' not in st.session_state:
            st.session_state['compliant_measures'] = []
        

        #SYNDRELLA
        if st.session_state['last_uploaded_file'] != file_name:
            auto_selected,y_flag_measures, status_message = get_auto_select_measures(file_name, Col_list)
            measures_with_y = [i for i in y_flag_measures if i != 'IMA'] #list_measures_with_y(file_name, Col_list)
            print(f"measures_with_y:{measures_with_y}")
            st.session_state['selected_boxes'] = auto_selected
            st.session_state['last_uploaded_file'] = file_name
            st.session_state['multiselect_key'] = str(uuid.uuid4())
            if auto_selected or measures_with_y:
                st.session_state['compliant_measures'] = measures_with_y  # Set compliant measures to those with 'Y'

        # Display auto-selected and compliant measures
        #OLD
        # if st.session_state['selected_boxes']:
        #     st.info(f"Member is not compliant for measures: {', '.join(st.session_state['selected_boxes'])}")
        # if st.session_state['compliant_measures']:
        #     st.info(f"Member compliant for: {', '.join(st.session_state['compliant_measures'])}")

        #NEW
        if st.session_state['selected_boxes']:
            message=f"Member is non-compliant for measures: {', '.join(st.session_state['selected_boxes'])}.  \nMember is compliant for measures: {', '.join(st.session_state['compliant_measures'])}"
            st.info(message)

        #add summarization option
        # Col_list= ['Generate Summary']+ Col_list

        selected_boxes = st.multiselect(
            "Select one or more options:",
            Col_list,
            default=st.session_state['selected_boxes'],
            key=st.session_state['multiselect_key'],
            on_change=update_selected_boxes
        )
        st.session_state['selected_boxes'] = selected_boxes

        # Select all logic
        all_options = st.checkbox("Select all Measures", key="select_all")
        if all_options:
            selected_boxes = Col_list
            st.session_state['selected_boxes'] = Col_list

        submit, reset, _ = st.columns([2, 2, 10])

        with submit:
            submit_button = st.button('**Submit**')
            if submit_button and st.session_state.uploaded_files is not None and selected_boxes:
                st.session_state['submitted'] = True
                clean_up()
        
        with reset:
            if st.button('**Reset Page**'):
                reset_checkboxes()

        if st.session_state.get('submitted', False):
            if st.session_state.uploaded_files is not None and selected_boxes:
                with st.spinner('Processing...'):
                    if not st.session_state.hedis_openai:
                        st.session_state.hedis_openai = True
                        file_path, actual_file_name = get_uploaded_pdf_path(st.session_state.uploaded_files)
                        message_placeholder = st.empty()
                        message_placeholder.info('Process started. Please wait to complete.')
                        time.sleep(2)
                        logging.info(SCRIPT+"-single_page(): %r", f"Running start_extration_and_DbInsertion_process from hedis_openai.py")
                        start_extration_and_DbInsertion_process(st, file_path, actual_file_name, message_placeholder, selected_boxes,measurement_year)
                        test_function()
                        # st.success("GenAI process completed.")

                        time.sleep(45) #UNCOMMENT THIS: DEMO
                        #DEMO

                        message_placeholder.success('Process completed.')
                # st.success('Processing complete!')
                st.markdown("#### Member Info and Measures Data")

                #AK                    
                sheets_dict = pd.read_excel(output_excel_file_path, sheet_name=None)

                #SYND
                # Fetch compliance status (raw remarks)
                compliance_status_dict = fetch_compliance_status(member_id, selected_boxes)#syn add this to display comp


                selected_boxes = ["Member Info"] + selected_boxes
                # filtered_selected_boxes=[i for i in selected_boxes if i != 'Generate Summary']
                # tabs = st.tabs(filtered_selected_boxes)

                tabs = st.tabs(selected_boxes)
                
                member_name = "Unknown"
                for tab, sheet_name in zip(tabs, selected_boxes):
                    #we don't need summarization tab in New_file_intake
                    if  "Generate Summary" in sheet_name:
                        continue
                    with tab:
                        if sheet_name == "Member Info":
                            with st.expander("", expanded=True):
                                st.markdown("##### Member Info")
                                df_member = sheets_dict.get('memberinfo', pd.DataFrame())
                                df_member = df_member.replace({float('nan'): 'None'})
                                member_info = df_member.head(1)
                                member_info_pivot = member_info.T.reset_index()
                                member_info_pivot.columns = ['Attribute', 'Value']
                                member_info_pivot['Value'] = member_info_pivot['Value'].astype(str)
                                st.dataframe(member_info_pivot.set_index('Attribute'), use_container_width=True, height=300)
                                name_row = member_info_pivot[member_info_pivot['Attribute'].str.contains('Name', case=False, na=False)]
                                if not name_row.empty:
                                    member_name = name_row['Value'].iloc[0]
                                else:
                                    st.warning("No 'Name' attribute found in Member Info.")
                                    member_name = "Unknown"
                        else:
                            col1, col2 = st.columns([0.95, 0.05])
                            with col1:
                                #st.markdown(f"**Measure: {sheet_name}**")
                                #SYND:add this to  Display the raw remark value after "Compliance Status"
                                remark = compliance_status_dict.get(sheet_name, 'None')
                                st.markdown(
                                    f'<p><strong>Disposition Status:</strong> {remark}</p>',
                                    unsafe_allow_html=True
                                )

                                score_dict = get_confidence_score()
                                value=score_dict.get(sheet_name, '-')
                                st.markdown(
                                    f'<p><strong>Confidence Score:</strong> {value}</p>',
                                    unsafe_allow_html=True
                                )
                            with col2:
                                #SYN
                                # # print(f"show_modal1: {st.session_state['show_modal']}")
                                # if st.button("ℹ️", key=f"info_{sheet_name}", help=f"View {sheet_name} specifications"):
                                #     st.session_state['show_modal'] = not st.session_state['show_modal']
                                #     # print(f"show_modal2: {st.session_state['show_modal']}")
                                #     # st.session_state['current_measure'] = sheet_name if st.session_state['show_modal'] else None
                                #     st.session_state['current_measure'] = sheet_name
                                #     # print(f"current_measure3: {st.session_state['current_measure']}")

                                # AYU-- Modified button to toggle modal and set current measure
                                if st.button("ℹ️", key=f"info_{sheet_name}", help=f"View {sheet_name} specifications"):
                                    if st.session_state['current_measure'] == sheet_name and st.session_state['show_modal']:
                                        st.session_state['show_modal'] = False
                                        st.session_state['current_measure'] = None
                                    else:
                                        st.session_state['show_modal'] = True
                                        st.session_state['current_measure'] = sheet_name
                                

                            
                            # syn:Rendering modal using spec_modal_utils.render_spec_modal when the info button is clicked
                            if st.session_state.get('current_measure') == sheet_name and st.session_state['show_modal']:
                                html_content = load_measure_spec(st.session_state['MY'], sheet_name)
                                render_spec_modal(sheet_name, html_content)
                            
                            with st.expander(f"Details for {sheet_name}", expanded=True):
                                df_measure = sheets_dict.get(sheet_name, pd.DataFrame())
                                df_measure = df_measure.replace({float('nan'): 'None'})
                                measure_info_pivot = df_measure.T.reset_index()
                                measure_info_pivot.columns = ['Attribute', 'Value']
                                measure_info_pivot['Value'] = measure_info_pivot['Value'].astype(str)
                                st.dataframe(measure_info_pivot.set_index('Attribute'), use_container_width=True, height=300)
                
                #st.write(f"Member ID: {member_id}, Member Name: {member_name}")
                review_btn, summary_btn , _ = st.columns([2, 2, 8])

                with review_btn:
                    if member_name != "Unknown" and member_id is not None:
                        if check_member_exists(member_id):
                            if st.button("Review Member", key="review_member_button"):
                                st.session_state['member_name'] = member_name
                                st.session_state['member_id'] = member_id
                                st.switch_page("pages/2_ReviewMember.py")
                                #page_switcher.switch_page("ReviewMember")
                        else:
                            st.error(f"Member ID {member_id} does not exist in the memberinfo table.")
                            st.button("Review Member", disabled=True, key="review_member_disabled")
                    else:
                                                                                                  
                        st.button("Review Member", disabled=True, key="review_member_disabled")
                     
                                                                                           
                        if member_name == "Unknown":
                            st.warning("No valid member name found in the data. Ensure 'Name' is an attribute in the Member Info.")
                        if member_id is None:
                            st.warning("No valid member ID extracted from the filename.")
                
                # with summary_btn:
                #     if "Generate Summary"  in selected_boxes:
                #             if st.button("View Summary", key="member_summary_button"):
                #                 page_switcher.switch_page("Summarization")
                #             else:
                #                 st.button("View Summary", disabled=True, key="member_summary_disabled")
                #     else:  
                #         st.button("View Summary", disabled=True, key="member_summary_disabled") 
               
                # if "Generate Summary"  not in selected_boxes:
                #     st.info(f"Generate Summary option not selected. No summarization available for {file_name}")  
                with summary_btn:
                    if st.button("View Summary", key="member_summary_button"):
                        #page_switcher.switch_page("Summarization")
                        st.switch_page("pages/5_Summarization.py")
                        

            else:
                st.error("Please select at least one measure.")
        else:
            if st.session_state.uploaded_files is None:
                st.error("Please Select File")
    st.session_state.single_done=True

def pdf_to_base64(pdf_path):
    with open(pdf_path, "rb") as pdf_file:
        encoded_pdf = base64.b64encode(pdf_file.read()).decode()
    return encoded_pdf

def run_in_background(folder_path,selected_pdf_names,message_placeholder,selected_boxes,measurement_year):

    for pdf_file in selected_pdf_names:
        process='Batch Processing'
        update_batch_status(file_name=pdf_file, status='Running')
        logging.info(SCRIPT+"--BATCH PROCESSING: %r", f"Processing file {pdf_file}")
        actual_file_name=Path(pdf_file).name
        # message_placeholder.info(f"Processing {actual_file_name}")
        print(f"log_batch: {actual_file_name}")
        # message_placeholder.warning("DELAY...")
        print("log_ak_batch_delay... 20 secs")
        time.sleep(20)
        batch_start_extration_and_DbInsertion_process( folder_path, actual_file_name, selected_boxes,measurement_year,process)

        update_batch_status(file_name=pdf_file, status='Completed')


def create_batch_status(selected_pdf_names):
    batch_file_status={i:'Not Started' for i in selected_pdf_names}

    # batch_file_status['reload_batch_page']='Running'
    batch_file_status=str(batch_file_status)

    with open (batch_status_json_path,'w') as f:
         json.dump(batch_file_status, f, indent=4)

def update_batch_status(file_name, status, stop=False):

    if os.path.exists(batch_status_json_path):
        with open(batch_status_json_path, 'r') as f:
            existing_data = json.load(f)
            existing_data=ast.literal_eval(existing_data)
    else:
        existing_data = {}

    new_status={file_name:status}
    existing_data.update(new_status)

    with open(batch_status_json_path,'w') as f:
        json.dump(str(existing_data), f)


def force_stop_batch_process():

    if os.path.exists(batch_status_json_path):
        with open(batch_status_json_path, 'r') as f:
            existing_data = json.load(f)
            existing_data=ast.literal_eval(existing_data)
    else:
        existing_data = {}

    #update all files to complet-- force stop
    new_status={file_name:'Completed' for file_name, status in existing_data.items()} #force stop
    # new_status['force_stop']='True'
    existing_data.update(new_status)

    with open(batch_status_json_path,'w') as f:
        json.dump(str(existing_data), f)


def get_batch_status():

    if os.path.exists(batch_status_json_path):
        with open(batch_status_json_path, 'r') as f:
            all_files_status = json.load(f)
            all_files_status=ast.literal_eval(all_files_status)
    else:
        all_files_status = {}

    any_file_running =[file for file,status in all_files_status.items() if status.strip().lower() == 'running' ]

    return all_files_status, len(any_file_running)>0




# Batch Processing Page
def batch_page():
    import sys
    # Initialize session state variables
    if "uploaded_files" not in st.session_state:
        st.session_state["uploaded_files"] = []
    if "selected_pdf_names" not in st.session_state:
        st.session_state["selected_pdf_names"] = []
    if "show_measures" not in st.session_state:
        st.session_state["show_measures"] = False
    if "measures_selected" not in st.session_state:
        st.session_state["measures_selected"] = False
    if "folder_path" not in st.session_state:
        st.session_state["folder_path"] = ''

    if 'batch_thread' not in st.session_state:
        st.session_state['batch_thread'] = None
        st.session_state['batch_status'] = "Not started"

    # Header
    st.markdown(" ")
    st.markdown('<h3 class="small-header">Upload and Extract Center for Batch Processing</h3>', unsafe_allow_html=True)
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # Measurement year selection
    measurement_year = st.selectbox('**Measurement Year:**', [2024])

    # Select folder path
    folder_path = st.text_input('Enter Folder Path:', value='/path/to/your/folder')
    st.session_state["folder_path"] = folder_path

    # Button to load all PDF files from the folder
    if st.button('Load PDFs from Folder'):
        if folder_path and os.path.exists(folder_path):
            pdf_files = [f for f in os.listdir(folder_path) if f.endswith('.pdf')]
            # pdf_files=pdf_files[:1]
            if pdf_files:
                st.session_state["uploaded_files"] = []
                st.session_state["selected_pdf_names"] = [Path(pdf).name for pdf in pdf_files]

                # for pdf_file in pdf_files:
                #     file_path = os.path.join(folder_path, pdf_file)
                #     with open(file_path, 'rb') as f:
                #         file_bytes = f.read()
                #         file_buffer = io.BytesIO(file_bytes)
                #         st.session_state["uploaded_files"].append((pdf_file, file_buffer))

                
                st.success(f"{len(pdf_files)} PDF file(s) loaded successfully.")
                st.session_state["show_measures"] = True


            else:
                st.warning("No PDF files found in the folder.")
        else:
            st.error("Invalid folder path. Please check the path and try again.")

    # Display Measures section only after PDFs are loaded
    print(f"show_measure: {st.session_state['show_measures']}")
    if st.session_state["show_measures"]:
        Col_list =measure_names #['memberinfo'] + measure_names
        selected_boxes = st.multiselect("Select one or more Measures:", Col_list)
        all_options = st.checkbox("Select all Measures")
        if all_options:
            selected_boxes = Col_list

    submit, reset, _ = st.columns([2, 2, 10])

    with submit:
        submit_button = st.button('**Submit**')

        if submit_button:
            if selected_boxes:
                with st.spinner('Processing ...'):
                    st.session_state['batch_processing'] = 'running'
                    try:
                        message_placeholder=st.empty()

                        create_batch_status(st.session_state['selected_pdf_names'])

                        if st.session_state['batch_thread'] is None or not st.session_state['batch_thread'].is_alive():
                            st.session_state['batch_thread'] = threading.Thread(target=run_in_background, args=(st.session_state["folder_path"],st.session_state["selected_pdf_names"] ,message_placeholder,selected_boxes,measurement_year), daemon=True)
                            st.session_state['batch_thread'].start()
                        else:
                            st.warning("Batch processing is already running.")
                        # st.write(st.session_state['batch_status'])

                        # run_in_background(st.session_state["folder_path"],st.session_state["selected_pdf_names"] ,message_placeholder,selected_boxes,measurement_year)


                        message_placeholder.info(f"Batch Processing started for  {len(st.session_state['selected_pdf_names'])} files. ")
                        time.sleep(2)
                        message_placeholder.info(f"Moving to status window. ")
                        time.sleep(2)
                        st.rerun()
                        # message_placeholder.success(f"All {len(st.session_state['selected_pdf_names'])} files processed successfully")

                        # logging.info(SCRIPT+"--BATCH PROCESSING: %r", f"Processed file {pdf_file}")
                        st.session_state['batch_processing']='completed'
                    except Exception as e:
                        st.error(f"An error occurred while fetching data: {e}")
            else:
                st.error("Please select at least one measure.")

    # Fetch and display data from the database in tab format
    # if st.session_state["measures_selected"]:
    #     selected_measures = st.session_state["selected_measures"]

    #     if selected_measures:  # Ensure there are selected measures
    #         tabs = st.tabs(selected_measures.keys())

    #         for tab, measure in zip(tabs, selected_measures.keys()):
    #             with tab:
    #                 st.markdown(f"#### {measure}")
    #                 data = selected_measures[measure]
    #                 if not data.empty:
    #                     # Add a clickable button for each PDF file
    #                     # data["PDF_File"] = data["PDF_File"].apply(
    #                     # lambda x: f'<a href="file:///{os.path.join(st.session_state["folder_path"], x)}" target="_blank">{x}</a>')
    #                     # Download the PDF File
    #                     # data["PDF_File"] = data["PDF_File"].str.strip().apply(
    #                     # lambda x: f"""
    #                     # <form action="data:application/pdf;base64,{base64.b64encode(open(os.path.join(st.session_state['folder_path'], x), 'rb').read()).decode()}" 
    #                     # method="get" target="_blank" style="display: inline;">
    #                     # <button type="submit" style="border: none; background: none; color: blue; cursor: pointer; text-decoration: underline;">{x}</button>
    #                     # </form>
    #                     #  """
    #                     #  )
    #                     #data["PDF_File"] = data["PDF_File"].str.strip()
                        

    #                     def create_download_link(file_name):
    #                         file_path = os.path.join(st.session_state["folder_path"], file_name)
    #                         if os.path.exists(file_path):
    #                             with open(file_path, "rb") as f:
    #                                 file_data = f.read()
    #                             b64_file_data = base64.b64encode(file_data).decode()
    #                             download_button = f"""
    #                                               <a href="data:application/pdf;base64,{b64_file_data}" 
    #                                                download="{file_name}">
    #                                               <button style="border: none; background: none; color: blue; 
    #                                               cursor: pointer; text-decoration: underline;">
    #                                              {file_name}
    #                                              </button>
    #                                                </a>
    #                                                """
    #                             return download_button
    #                         else:
    #                             return f"File {file_name} not found."
    #                     data["PDF_File"] = data["PDF_File"].apply(create_download_link)
                        
    #                     # Convert DataFrame to HTML with clickable links
    #                     table_html = data.to_html(escape=False, index=False)
    #                     table_html = re.sub(r"\n+", " ", table_html).strip()
    #                     # Apply CSS for scrollable container
    #                     styled_table = f"""
    #                                         <style>
    #                                             table {{
    #                                                 width: auto !important;
    #                                                 border-collapse: collapse;
    #                                             }}
    #                                             th {{
    #                                                 background-color: #f2f2f2;
    #                                                 text-align: center !important;  /* Center align column headers */
    #                                                 padding: 10px;
    #                                             }}
    #                                             td {{
    #                                                 padding: 10px;
    #                                                 white-space: nowrap;  /* Prevents text wrapping */
    #                                                 text-align: left;
    #                                             }}
    #                                             table, th, td {{
    #                                                 border: 1px solid #ddd;  /* Add border for better readability */
    #                                             }}
    #                                         </style>
    #                                         <div style="overflow-x: auto; max-width: 100%;">
    #                                             {table_html}
    #                                         </div>
    #                                         """
    #                     # Display data with buttons     
    #                     st.write(styled_table, unsafe_allow_html=True)
    #                 else:
    #                     st.warning(f"No data found for measure: {measure}")
    #     else:
    #         st.warning("No measures were selected or no data returned for selected measures.")

    # Reset button
    with reset:
        if st.button('**Reset Page**'):
            st.session_state.clear()
            st.rerun()

def show_status_table(all_files_status):
    file_names=all_files_status.keys()
    files_status=all_files_status.values()
    data={"File":file_names,  "Status":files_status}
    df=pd.DataFrame(data)
    st.dataframe(df)

# Display Sidebar with Batch Processing Enabled
def display_sidebar():
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Select a page:", ["Single Processing","Batch Processing"])#, "Batch Processing"

    if page == "Single Processing":
        single_page()
        
        #Navigate to Review member page
        # Only show the button if processing is done
        # if st.session_state.single_done:
        #     if st.button("Review Member"):
        #         switch_page("review member")
                
    elif page == "Batch Processing":

        # if  st.session_state['batch_processing'] == 'running':
        #     print(f"Log_ak_batch: Already running {st.session_state['batch_processing']}")
        #     #quickfix -- padding only
        #     st.markdown("""
        #         <div style="width: 20%; padding: 25px; border: 1px solid white; background-color: white;"></div>
        #         """, unsafe_allow_html=True)
        #     st.info("Batch Processing is already running.")
        # else:
        #     print(f"Log_ak_batch: Triggered first time {st.session_state['batch_processing']}")
        #     batch_page()

        all_files_status, any_file_running= get_batch_status()

        # reload_batch_page=all_files_status['reload_batch_page'].lower() == 'false'

        print(f"\n all_files_status: {all_files_status}")

        if any_file_running:
            print(f"Log_ak_batch2: Already running ")
            #quickfix -- padding only
            st.markdown("""
                <div style="width: 20%; padding: 25px; border: 1px solid white; background-color: white;"></div>
                """, unsafe_allow_html=True)
            st.info("Batch Processing is already running.")

            show_status_table(all_files_status)

            refresh_btn, stop_btn , _ = st.columns([2, 2, 8])

            with refresh_btn:
                if st.button("Refresh Status", type='primary'):
                    # show_status_table(all_files_status)
                    print('Refresh') #:)

            with stop_btn: #force stop the  batch processing, by setting the file status to Competed in batch_files_status.json
                if st.button("Stop Batch Processing", type='primary'):
                    # show_status_table(all_files_status)
                    print('Stop Batch Processing') #:)
                    force_stop_batch_process()
                    st.rerun()
                

        else:
            print(f"Log_ak_batch3: Triggered first time")
            # show_status_table(all_files_status)
            batch_page()

# Main function to display content based on sidebar selection
def main():
    display_sidebar()

if __name__ == "__main__":

    # if os.path.exists(batch_status_json_path):
    #     os.remove(batch_status_json_path)

    set_logging(root_dir)

    logging.info(SCRIPT+": %r", f"HEDIS process started...")

    logging.info(SCRIPT+": %r", f"LOADING ENV VARIABLES...")
    load_dotenv()   
    #required for databse
    server_name = os.getenv('HEDIS_SERVER')
    database_name = os.getenv('HEDIS_DATABASE')

    # print(os.environ)
    # # import sys
    # # sys.exit()
    logging.info(SCRIPT+": %r", f"ENV VARIABLES; Server= {server_name}, database= {database_name}")

    # Validate environment variables
    if not server_name or not database_name:
        logging.info(SCRIPT+": %r", f"Please set HEDIS_SERVER and HEDIS_DATABASE must be set in the .env file.")
        st.error("Please set HEDIS_SERVER and HEDIS_DATABASE must be set in the .env file.")
        st.stop()

    main()
