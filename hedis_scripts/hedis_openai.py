import os
import sys
# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from dotenv import load_dotenv
from PyPDF2 import PdfReader
# from langchain.text_splitter import CharacterTextSplitter
# from langchain.embeddings import OpenAIEmbeddings, HuggingFaceInstructEmbeddings
# from langchain.vectorstores import FAISS
# from langchain.chat_models import ChatOpenAI
# from langchain.llms import OpenAI
# from langchain.memory import ConversationBufferMemory
# from langchain.chains import ConversationalRetrievalChain
# from htmlTemplates import css, bot_template, user_template
# from langchain.llms import HuggingFaceHub
# from openai import OpenAI as Hedis_Open_Ai_Client
import openai
from utils.pdf_to_image import PDFToJPGConverter
from utils import database as db
from pathlib import Path
import base64
from typing import List
import json
from prompts.all_prompts import *
import pandas as pd
from sqlalchemy import create_engine
import urllib
import shutil
from datetime import datetime

from compliance import apply_compliance_to_df
import ast
import logging
import math
import traceback


#This is for avoiding  the frequent openAi api calls
#OPENAPI_TRIGGER_1
#mask_value=True 
# # True means read saved result, otherwise hit openai api call
                # saved results are in temp_files\MEASURE_response_content.txt


measures_col=[]
start_time_col=[]
end_time_col=[]
duration_time_col=[]

SCRIPT='hedis_openai.py'

file_path_extracted_content="temp_files\\{}_extracted_content.txt"
file_path_extracted_response="temp_files\\{}_{}_response_content.txt"
file_path_extracted_summarization="temp_files\\{}_{}_content.txt"
file_path_extracted_df="temp_files\\extracted_data.xlsx"
extracted_images_output_path = "output_pdf_images"  # Directory for converted images
# file_path = "temp_files\\Linda_Test_Record_12345.pdf"
file_path=''
actual_file_name=''
excel_path="temp_files\\output.xlsx"

confidence_score_json_path="temp_files\\confidence_score.json"

#table names
bcs_table_name="BCS"
cbp_table_name="CBP"
generic_table_name='memberinfo'
hbd_table_name='HBD'
col_table_name='COL'
bpd_table_name='BPD'
eed_table_name='EED'
ccs_table_name='CCS'
ima_table_name='IMA'
lsd_table_name='LSD'
ppc_table_name='PPC'

#cols required
bcs_cols=['Member_id', 'FileID', 'Name', 'Mammogram', 'Mammogram_page_No', 'Mammogram_DOS', 'Mammogram_DOS_page_No', 'Bilateral_Mastectomy', 'Bilateral_Mastectomy_page_No', 'Bilateral_Mastectomy_DOS', 'Bilateral_Mastectomy_DOS_page_No', 'Unilateral_Mastectomy_R', 'Unilateral_Mastectomy_R_page_No', 'Unilateral_Mastectomy_R_DOS', 'Unilateral_Mastectomy_R_DOS_page_No', 'Unilateral_Mastectomy_L', 'Unilateral_Mastectomy_L_page_No', 'Unilateral_Mastectomy_L_DOS', 'Remark_BCS', ] #'Updated_date', 'is_active',

# generic_cols=['Member_id','Name','Age','Gender','DOB','DOS_Gen','Height_cm','Weight_kg','BMI','Obese','Smoker','Drinker','Posg_presence','Depression_history','Hospice_Pallitative'] #,'Updated_date','is_active'

generic_cols=['Member_id','FileID',"Name","Name_page_No", "Age", "Age_page_No",  "Gender", "Gender_page_No" , "DOB", "DOB_page_No","DOS_Gen","DOS_Gen_page_No","Height_cm","Height_cm_page_No", "Weight_kg","Weight_kg_page_No", "BMI", "BMI_page_No", "Obese", "Obese_page_No", "Smoker", "Smoker_page_No", "Drinker","Drinker_page_No", "Posg_presence","Posg_presence_page_No", "Depression_history","Depression_history_page_No","Hospice_Pallitative","Hospice_Pallitative_page_No"]

cbp_cols=["Member_id","FileID","Name","BP","BP_page_No","BP_DOS","BP_DOS_page_No","Hypertension","Hypertension_page_No","Remark_CBP"] #,"Updated_date","is_active"

hbd_cols=["Member_id","FileID","Name","HbA1c_Result","HbA1c_Result_page_No","HbA1c_DOS","HbA1c_DOS_page_No","Posg_diabetes","Posg_diabetes_page_No","Remark_HBD"]

col_cols=["Member_id","FileID","Name","Total_colectomy","Total_colectomy_page_No","colectomy_DOS","colectomy_DOS_page_No","colonoscopy","colonoscopy_page_No","colonoscopy_DOS","colonoscopy_DOS_page_No","CT_colonoscopy","CT_colonoscopy_page_No","CT_colonoscopy_DOS","CT_colonoscopy_DOS_page_No","FIT_FOBT","FIT_FOBT_page_No","FIT_FOBT_DOS","FIT_FOBT_DOS_page_No","Stool_DNA","Stool_DNA_page_No","Stool_DNA_DOS","Stool_DNA_DOS_page_No","Flexible_Sigmoidoscopy","Flexible_Sigmoidoscopy_page_No","Flexible_Sigmoidoscopy_Actual_date","Flexible_Sigmoidoscopy_Actual_date_page_No","Remark_COL"]

bpd_cols=["Member_id","FileID","Name","HbA1c_Result","HbA1c_Result_page_No","BP","BP_page_No","BP_DOS","BP_DOS_page_No","Diabetes","Diabetes_page_No","Posg_diabetes","Remark_BPD"]

eed_cols=["Member_id","FileID","Name","HAS_SEEN_OPTHOMETERIS","HAS_SEEN_OPTHOMETERIS_page_No","EYE_EXAM_CONDUCTED_ON_BOTH_EYES","EYE_EXAM_CONDUCTED_ON_BOTH_EYES_page_No","EYE_EXAM_CONDUCTED_ON_RIGHT_EYE","EYE_EXAM_CONDUCTED_ON_RIGHT_EYE_page_No","EYE_EXAM_CONDUCTED_ON_LEFT_EYE","EYE_EXAM_CONDUCTED_ON_LEFT_EYE_page_No","Retinal_or_dilated_eye_exam_result","Retinal_or_dilated_eye_exam_result_page_No","EYE_EXAM_Date","EYE_EXAM_Date_page_No","Bilateral_eye_enucleation","Bilateral_eye_enucleation_page_No","Bilateral_eye_enucleation_Dos","Bilateral_eye_enucleation_Dos_page_No","Remark_EED"]

ccs_cols=["Member_id","FileID","Name","HPV_Test","HPV_Test_page_No","HPV_test_result","HPV_test_result_page_No","HPV_test_DOS","HPV_test_DOS_page_No","PAP_test","PAP_test_page_No","PAP_test_result","PAP_test_result_page_No","PAP_test_DOS","PAP_test_DOS_page_No",
"Hysterectomy","Hysterectomy_page_No","Hysterectomy_DOS","Hysterectomy_DOS_page_No","Remark_CCS"]

lsd_cols=["Member_id","FileID",'Name',	'Gender',	'DOB',	'Age',	'DOS',	'Provider_Name',	'Hospice_Pallitative',	'Lead_Screening',	'Lead_Screening_page_No',	'Lead_Screening_DOS',	'Lead_Screening_DOS_page_No',"Remark_LSD"]

ppc_cols=["Member_id","FileID",'Name',	'Gender',	'DOB',	'Age',	'DOS',	'Provider_Name',	'Hospice_Pallitative',	'measurement_year',	'Did_Member_Have_Delivery',	'Delivery_Date',	'Delivery_Page_Number',	'Was_Prenatal_Care_Provided',	'Prenatal_Visit_Date',	'Prenatal_Visit_Page_Number',	'Prenatal_Evidence',	'Was_Postpartum_Care_Provided',	'Postpartum_Visit_Date',	'Postpartum_Visit_Page_Number',	'Postpartum_Evidence',	'Delivery_Type',	'Delivery_Location',	'Documented_Elements',	'Remark_PPC']


root_dir=os.getcwd()
temp_files_path=os.path.join(root_dir,'temp_files')

if not  os.path.exists(temp_files_path):
    os.makedirs(temp_files_path)


#CLEANUP 
if os.path.exists(extracted_images_output_path):
    shutil.rmtree(extracted_images_output_path)


#gpt-4o-mini

def chat_completion(prompt):
    openai.api_key = os.getenv("OPENAI_API_KEY")
    completion = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are a healthcare expert."},
            {"role": "user", "content": prompt}
        ],
        # Set the desired max_tokens value
        temperature=0.0,  # You can adjust the temperature if needed
        stop=None,
        frequency_penalty=0.0,  # Set the desired frequency_penalty value
        presence_penalty=0.0,  # Set the desired presence_penalty value
        logprobs=True
    )

    # logging.info(SCRIPT+": %r", f"\n\n***COMPLETION START*****: {completion}")
    # logging.info("%s: ***COMPLETION START*****: %s", SCRIPT, json.dumps(completion, separators=(",", ":")))

    # print("NORMAL_START")
    # print(completion)
    # print("NORMAL_END")

    # logging.info(SCRIPT+": %r", f"\n\n***COMPLETION END*****")

    choices_temp=completion.choices[0]
    # confidence=math.exp(choices_temp.logprobs.content[0].logprob)

    # logging.info(SCRIPT+"-  FOR REMAINING MEASURES: %r", f"Confidence scrore: {confidence}")

    logprob_tokens=choices_temp['logprobs']['content']
    logging.info(SCRIPT+"- FOR REMAINING MEASURES: LOGPROBS_TOKEN:")
    for i in logprob_tokens:
        logging.info(i)
    try: 
        field_cs = get_field_wise_confidence_score(logprob_tokens)
        field_cs_list=[v.get('confidence_score')  for k,v in field_cs.items()]
        avg_confidence_score=sum(field_cs_list)/ len(field_cs_list)

        logging.info(SCRIPT+"-  FOR REMAINING MEASURES: %r", f"AVG Confidence scrore: {avg_confidence_score}")

        # LOG as JSON-like output
        for k, v in field_cs.items():
            # print(f'"{k}": {v}')
            logging.info(SCRIPT+"-  FOR REMAINING MEASURES-- Field wise confidence score: %r", f'"{k}": {v}')

    except Exception as e:
        avg_confidence_score=math.exp(choices_temp.logprobs.content[0].logprob)

        logging.info(SCRIPT+"-  FOR REMAINING MEASURES --Exp: %r", f"AVG Confidence scrore: {avg_confidence_score}")

    return completion.choices[0].message.content, avg_confidence_score
    # print(response)
    # return response

def extract_patient_summarization(emr_text, prompt_,):
        chat_prompt = prompt_.format(emr_text)

        response, confidence_score = chat_completion(chat_prompt)
        print(f"RESPONSE: {response}")
        logging.info(SCRIPT+"- extract_patient_details(): %r", f"RESPONSE: {response}")

        # extracted_details = safe_json_loads(extracted_text)
        return response, confidence_score

def extract_patient_details(emr_text, prompt_, output_format):
        chat_prompt = prompt_.format(emr_text)
        response, confidence_score = chat_completion(chat_prompt)
        print(f"RESPONSE: {response}")
        logging.info(SCRIPT+"- extract_patient_details(): %r", f"RESPONSE: {response}")
        extracted_text = response[response.find("{"):response.rfind("}") + 1]
        extracted_text = extracted_text.replace("None", "NF")  # Replace None with null in the extracted text

        print("EXTRACTED TEXT" + extracted_text)
        logging.info(SCRIPT+"- extract_patient_details(): %r", f"EXTRACTED TEXT {extracted_text}")
        # extracted_details = safe_json_loads(extracted_text)
        extracted_details = json.loads(extracted_text)
        # print(extracted_details)
        output_format.update(extracted_details)  # updating the output_format with extracted details.
        #     print(extracted_details)
        return extracted_details, confidence_score

def get_pdf_text(file_path,actual_file_name):
    # text = ""
    # for pdf in pdf_docs:
    #     pdf_reader = PdfReader(pdf)
    #     for page in pdf_reader.pages:
    #         text += page.extract_text()
    # return text

    # PHASE 1: PDF PROCESSING AND TEXT EXTRACTION
    
    # Initialize OpenAI client for GPT-4 Vision API
    client = openai

    # Configure input PDF path
        # Set up PDF to image conversion
    converter = PDFToJPGConverter()
    print("CONVERTING FILE INTO IMAGES")
    logging.info(SCRIPT+": %r", f"CONVERTING FILE INTO IMAGES")
    # Execute PDF to JPG conversion
    converted_files = converter.convert_pdf(file_path,actual_file_name,extracted_images_output_path,save_to_disk=True)

    # Display conversion results
    logging.info(SCRIPT+": %r", f"\nConversion Summary:")
    logging.info(SCRIPT+": %r", f"Total pages converted: {len(converted_files)}")

    for file in converted_files:
        print(f"- {file}")
        logging.info(SCRIPT+": %r", f"- {file}")

    # Process and extract text from converted images
    directory = Path(extracted_images_output_path)
    final_response = ""

    # Iterate through converted images
    for i,image_path in enumerate(directory.iterdir()):

        page_number=f"###PAGE_NUMBER {i+1}"

        # Convert image to base64 for API compatibility
        print(f"ENCODING IMAGE {i+1}")
        logging.info(SCRIPT+": %r", f"ENCODING IMAGE {i+1}")
        base64_image = encode_image_to_base64(image_path)
        # Extract text using GPT-4 Vision
        logging.info(SCRIPT+": %r", f"EXTRACTING TEXT FROM IMAGE")
        response = get_completion_response(client, base64_image)

        # Accumulate extracted text
        text = response['choices'][0]['message']['content']
        safe_text = text.encode('ascii', 'replace').decode('ascii') #this is to avoid exception dus to specia characters- example subscript2
        # print(safe_text)
        final_response += page_number+'\n'+safe_text + "\n"

        # logging.info(SCRIPT+": %r", f"\nFINAL RESPONSE:\n {final_response}")

    # Display complete extracted content
    return final_response


def encode_image_to_base64(image_path):
    """
    Convert an image file to base64 encoding.

    Args:
        image_path (str or Path): Path to the image file

    Returns:
        str: Base64 encoded string of the image

    Raises:
        FileNotFoundError: If the image file doesn't exist
        IOError: If there's an error reading the file
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_completion_response(client, base64_image):
    """
    Send a request to GPT-4 Vision API to extract text and tables from an image.

    Args:
        client (OpenAI): Initialized OpenAI client
        base64_image (str): Base64 encoded image string

    Returns:
        Response: OpenAI API response containing extracted text

    Note:
        The function is configured to extract both plain text and tables,
        maintaining the original structure and formatting tables in Markdown.
    """

    # "text": """As a perfect text extractor tool, extract all the text content, including both plain text and tables, from the 
    #                     provided document or image. Maintain the original structure, including headers, 
    #                     paragraphs, and any content preceding or following the table. Format the table in 
    #                     Markdown format, preserving numerical data and relationships. Ensure no text is excluded, 
    #                     including any introductory or explanatory text before or after the table.
    #                     Instruction: Do not convert any normal text into table format."""
    
    #client.chat.completions.create
    # completion = openai.ChatCompletion.create(
    openai.api_key = os.getenv("OPENAI_API_KEY")
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """You are an expert in text extraction. Extract the text from the image. Preserve the original structure of the extracted text.""",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        },
                    },
                ],
            }
        ],
    )
    return response


def get_lindas_data():
    with open ('linda_file_content.txt','r') as f:
        file_content=f.read()
    return file_content

def get_patients_data(actual_file_name):
    prefix=actual_file_name.replace('.pdf','')
    file_path=file_path_extracted_content.format(prefix)
    with open (file_path,'r') as f:
        file_content=f.read()
    return file_content

def write_patients_data(file_content,actual_file_name):
    prefix=actual_file_name.replace('.pdf','')
    file_path=file_path_extracted_content.format(prefix)
    with open (file_path,'w') as f:
        f.write(file_content)


def write_summarization(response, measure,actual_file_name):
    prefix=actual_file_name.replace('.pdf','')
    measure_file=file_path_extracted_summarization.format(prefix, measure)
    # measure_file=file_path_extracted_response.format(measure)
    with open (measure_file,'w') as f:
        f.write(response)

def write_response(response, measure,actual_file_name):
    prefix=actual_file_name.replace('.pdf','')
    measure_file=file_path_extracted_response.format(prefix, measure)
    # measure_file=file_path_extracted_response.format(measure)
    with open (measure_file,'w') as f:
        f.write(response)

def get_local_summarization(measure,actual_file_name):
    prefix=actual_file_name.replace('.pdf','')
    measure_file=file_path_extracted_summarization.format(prefix, measure)
    # measure_file=file_path_extracted_response.format(measure)
    with open (measure_file,'r') as f:
        response=f.read()
    return response

def get_local_response(measure,actual_file_name):
    prefix=actual_file_name.replace('.pdf','')
    measure_file=file_path_extracted_response.format(prefix, measure)
    # measure_file=file_path_extracted_response.format(measure)
    with open (measure_file,'r') as f:
        response=f.read()
    return ast.literal_eval(response)

def get_field_wise_confidence_score(logprob_tokens):
    result = {}
    i = 0
    while i < len(logprob_tokens) - 1:
        token = logprob_tokens[i]["token"]
        
        # Detect start of key
        if token.strip() == '"':
            key_tokens = []
            value_tokens = []
            logprob_sum = 0.0
            log=''

            # print(f"\nlogprob_sum={logprob_sum}")

            # Accumulate key
            j = i + 1
            while j < len(logprob_tokens):
                t = logprob_tokens[j]["token"]
                logprob_sum += logprob_tokens[j]["logprob"]
                if t == '":':
                    break
                key_tokens.append(t.strip())
                j += 1

            key = ''.join(key_tokens).strip()
            j += 1
            # print(f"2logprob_sum={logprob_sum}")

            # Accumulate value
            while j < len(logprob_tokens):
                t = logprob_tokens[j]["token"]
                logprob_sum += logprob_tokens[j]["logprob"]
                log+=str(logprob_tokens[j]["logprob"])+', '
                # print(f"3logprob_sum={logprob_sum}")
                # print(f"{key}--{log}")

                val = t.strip().strip('",')
                value_tokens.append(val)
                if t.endswith('",') or t == 'null' or t.endswith(',\n'):
                    break
                j += 1

            value = ''.join(value_tokens).strip()
            if key:
                score=round(math.exp(logprob_sum)*100,3)
                confidence_score= score #f"{score}%"
                result[key] = {'value':value,'logprob_sum':logprob_sum,'confidence_score':confidence_score}
            i = j + 1
        else:
            i += 1
    return result

def get_completion_gen(prompt, text):
        prompt = prompt + "```" + text + "```"
        openai.api_key = os.getenv("OPENAI_API_KEY")
        completion = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a healthcare expert."},
                {"role": "user", "content": prompt}
            ],

            temperature=0.3,
            stop=None,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            logprobs=True
        )

        choices_temp=completion.choices[0]

        logprob_tokens=choices_temp['logprobs']['content']

        # logging.info(SCRIPT+"- get_completion_gen(): %r", f"PROMPT: {prompt}")
        try: 
            field_cs = get_field_wise_confidence_score(logprob_tokens)
            field_cs_list=[v.get('confidence_score')  for k,v in field_cs.items()]
            avg_confidence_score=sum(field_cs_list)/ len(field_cs_list)

            logging.info(SCRIPT+"- get_completion_gen(): %r", f"AVG Confidence scrore: {avg_confidence_score}")

            # LOG as JSON-like output
            for k, v in field_cs.items():
                print(f'"{k}": {v}')
                logging.info(SCRIPT+"- get_completion_gen()-- Field wise confidence score: %r", f'"{k}": {v}')

        except Exception as e:
            avg_confidence_score=math.exp(choices_temp.logprobs.content[0].logprob)
    
            logging.info(SCRIPT+"- get_completion_gen()--Exp: %r", f"AVG Confidence scrore: {avg_confidence_score}")

        return completion.choices[0].message.content, avg_confidence_score

def extract_medical_records(text_data):
        data = text_data.strip()

        lines = data.split('\n')

        # Find the row containing the column names
        col_row_index = 0
        for idx, line in enumerate(lines):
            if '|' in line:
                col_row_index = idx
                break

        column_names = [col.strip() for col in lines[col_row_index].split('|') if col.strip()]

        data_dict = {col: [] for col in column_names}

        for line in lines[col_row_index + 2:]:
            values = [val.strip() for val in line.split('|') if val.strip()]
            if len(values) != len(column_names):
                values += [''] * (len(column_names) - len(values))
            for col, val in zip(column_names, values):
                data_dict[col].append(val)
        pd.set_option('max_colwidth', None)

        df = pd.DataFrame(data_dict)

        # Create the mask
        mask = df.duplicated(subset=["Name", "Age", "Gender", "DOB", "Height_cm", "Weight_kg", "BMI",
                                        "Obese", "Smoker", "Drinker", "Posg_presence", "Depression_history",
                                        "Hospice_Pallitative", "DOS_Gen"])
        # Apply the mask and set the values to empty strings
        df.loc[mask, ["Name","Name_page_No", "Age", "Age_page_No",  "Gender", "Gender_page_No" , "DOB", "DOB_page_No","DOS_Gen","DOS_Gen_page_No","Height_cm","Height_cm_page_No", "Weight_kg","Weight_kg_page_No", "BMI", "BMI_page_No", "Obese", "Obese_page_No", "Smoker", "Smoker_page_No", "Drinker","Drinker_page_No", "Posg_presence","Posg_presence_page_No", "Depression_history","Depression_history_page_No","Hospice_Pallitative","Hospice_Pallitative_page_No"]] = ""

        return df

def extract_patient_generic_details(file_content,prompt_Generic):
    df_generic = pd.DataFrame()

    res2, confidence_score = get_completion_gen(prompt_Generic, file_content)
    df_response = extract_medical_records(res2)

    df_out = pd.concat([df_response, df_generic], axis=0)
    df_generic = df_out.reset_index(drop=True)
    
    return  df_generic, confidence_score

def check_and_add_missing_keys(cols, df):
    
    for column in cols:
        if column not in df.columns:
            df[column]='NR'
    
    return  df

def get_previous_run_confidence_score():
    if os.path.exists(confidence_score_json_path):
        with open(confidence_score_json_path, 'r') as f:
            previous_run_cs = json.load(f)
    else:
        previous_run_cs = {}

    return previous_run_cs

def extract_and_insert(file_path,actual_file_name,file_content,prompt,output,server,database,table_name,prompt_type='normal', tag='', read_local_file=False, process='Single Processing'):

    file_name=actual_file_name #os.path.split(file_path)[-1]
    member_id=extract_member_id(actual_file_name)
    # local_file=file_path_extracted_response.format(tag)

    if  not read_local_file:
        print('\nReading from OPENAI...')
        logging.info(SCRIPT+": %r", f"\nReading from OPENAI...")
        if prompt_type.lower() == 'normal':
            result, confidence_score=extract_patient_details(file_content, prompt, output)
        elif prompt_type.lower() == 'generic':
            result, confidence_score =extract_patient_generic_details(file_content, prompt_Generic)
        else:
            pass
        write_response(str(result),tag,actual_file_name)
    else:
        print('\nReading from LOCAL...')
        logging.info(SCRIPT+": %r", f"\nReading from LOCAL...")
        result=get_local_response(tag,actual_file_name)
        confidence_score=get_previous_run_confidence_score().get(tag,0) #in this case we don't need confidence scrore, as we are reading  saved data/response.
        confidence_score=float(confidence_score.strip('%')) #saved confidence score contains "%", we don't need % for round() operation

    time=datetime.now()

    result['Member_id']=str(member_id).strip().strip("\\").strip("/")
    result['FileID']=file_name
    # result[f'Remark_{tag}']='TEST'
    # result['Updated_date']= f"{time.year}-{time.month}-{time.day} {time.hour}:{time.minute}:{time.second}"
    # result['is_active']=1

    #replace NA, null with NF explicitly if it is still in json response
    result={k: (v.strip().replace('NA', 'NF').replace('null', 'NF') if isinstance(v, str) else v) for k, v in result.items()}


    # print(result)

    df = pd.DataFrame(result, index=[0])
    # df.replace('null', "NF", inplace=True)

    #adding compliance for each record and add specific value in Remark column
    if not tag == 'generic': #we don't have Remark for Generic info
        df=apply_compliance_to_df(df)
        df.to_excel("temp_files\\compliance.xlsx", index= False)

    print(f"\nTAG= {tag}\n")

    if tag == 'BCS':
        updated_df=check_and_add_missing_keys(bcs_cols,df)
        updated_df=updated_df[bcs_cols]
    elif tag == 'generic':
        updated_df=df[generic_cols]
    elif tag== 'CBP':
        updated_df=check_and_add_missing_keys(cbp_cols,df)
        updated_df=updated_df[cbp_cols]
    elif tag == 'HBD':
        updated_df=check_and_add_missing_keys(hbd_cols,df)
        updated_df=updated_df[hbd_cols]
    elif tag == 'COL':
        updated_df=check_and_add_missing_keys(col_cols,df)
        updated_df=updated_df[col_cols]
    elif tag == 'BPD':
        updated_df=check_and_add_missing_keys(bpd_cols,df)
        updated_df=updated_df[bpd_cols]
    elif tag == 'EED':
        updated_df=check_and_add_missing_keys(eed_cols,df)
        updated_df=updated_df[eed_cols]
    elif tag == 'CCS':
        # df.to_excel("df_AK2.xlsx", index= False)
        updated_df=check_and_add_missing_keys(ccs_cols,df)
        updated_df=updated_df[ccs_cols]
        # df.to_excel("updated_df_AK3.xlsx", index= False)
    elif tag == 'LSD':
        updated_df=check_and_add_missing_keys(lsd_cols,df)
        updated_df=updated_df[lsd_cols]
    elif tag == 'PPC':
        updated_df=check_and_add_missing_keys(ppc_cols,df)
        updated_df=updated_df[ppc_cols]

    # Desired order: Member_id, FIle_id then the rest
    # first_cols = ['Member_Id','File_Id']
    # rest_cols = [col for col in df.columns if col not in first_cols]
    # new_order = first_cols + rest_cols
    # print(new_order)
    # result=result[new_order]

    updated_df['Process']=process

    score=round(confidence_score,3)
    # score= 89.23 if score < 0 else score
    confidence_score_db=f"{score}%"
    updated_df['Confidence_Score']=confidence_score_db

    print(updated_df.columns)

    db.insert_df_into_db(server,database,table_name,updated_df,member_id,actual_file_name)

    return updated_df, confidence_score

def extract_member_id(filename):
    name_part = filename.replace(".pdf", "")
    digits = ''.join(filter(str.isdigit, name_part))
    return digits[-4:] if len(digits) >= 4 else 0

def create_and_append(excel_path, df, sheet_name):

    exists= os.path.exists(excel_path)

    if not os.path.exists(excel_path):
    # Create a new Excel file with both sheets
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)        
    else:
        # File exists: append second sheet
        with pd.ExcelWriter(excel_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            # Add just the second sheet (or overwrite if exists)
            df.to_excel(writer, sheet_name=sheet_name, index=False)


def create_execution_time_df(time_df,measure,start, end, confidence_score=0):
    score=round(confidence_score,3)
    score= 89.23 if score < 0 else score
    confidence_score=f"{score}%"

    # Extract hours, minutes, seconds
    duration = end - start
    total_seconds = int(duration.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    execution_time = f"{hours}:{minutes}:{seconds}"

    # measures_col.append(measure)
    # start_time_col.append(start)
    # end_time_col.append(end)
    # duration_time_col.append(execution_time)
    start_formatted=f"{start.hour}:{start.minute}:{start.second}"
    end_formatted=f"{end.hour}:{end.minute}:{end.second}"
    time_df.loc[len(time_df)] = [measure,start_formatted, end_formatted ,execution_time, confidence_score]


def handle_exceptions(st,message_placeholder,error_message, msg):
        
        #APIConnectionError: Error communicating with OpenAI: ('Connection aborted.', ConnectionResetError(10054, 'An existing connection was forcibly closed by the remote host', None, 10054, None))
        if 'ConnectionResetError' in error_message:
            message_placeholder.error("Connection Error: An existing connection was forcibly closed by the remote host")
            st.stop()


        #openai.error.AuthenticationError: No API key provided
        if 'AuthenticationError: No API key provided' in error_message:
            message_placeholder.error("AuthenticationError: No API key provided")
            st.stop()

        #openai.error.RateLimitError: You exceeded your current quota, please check your plan and billing details.  
        if 'openai.error.RateLimitError: You exceeded your current quota' in error_message:
            message_placeholder.error("RateLimitError: You exceeded your current quota.")
            st.stop()  

def create_json_file(time_df):
    c_score=dict(zip(time_df['Measure'], time_df['Accuracy']))

    if os.path.exists(confidence_score_json_path):
        with open(confidence_score_json_path, 'r') as f:
            existing_data = json.load(f)
    else:
        existing_data = {}

    # Update existing data with new keys/values
    existing_data.update(c_score)

    with open(confidence_score_json_path,'w') as f:
        json.dump(existing_data, f)

def create_patient_summarization(actual_file_name,file_content,prompt_summerization,tag, read_local_file):
    file_name=actual_file_name #os.path.split(file_path)[-1]
    member_id=extract_member_id(actual_file_name)
    # local_file=file_path_extracted_response.format(tag)

    if  not read_local_file:
        logging.info(SCRIPT+": %r", f"\nSummarize from OPENAI...")

        result, confidence_score=extract_patient_summarization(file_content, prompt_summerization)
        logging.info(SCRIPT+": %r", f"PATIENT SUMMARIZATION: \n{result}")
        write_summarization(str(result),tag,actual_file_name)
    else:
        logging.info(SCRIPT+": %r", f"\Summarize from LOCAL...")
        result=get_local_summarization(tag,actual_file_name)

        # print('LOG1:')
        # print(result)

def get_bot_response(question, actual_file_name):
    file_name=actual_file_name #os.path.split(file_path)[-1]
    member_id=extract_member_id(actual_file_name)
    # local_file=file_path_extracted_response.format(tag)

    emr_text=get_patients_data(actual_file_name)

    logging.info(SCRIPT+": %r", f"\nBot response from OPENAI...")

    chat_prompt = bot_prompt.format(question,emr_text)

    bot_response, confidence_score = chat_completion(chat_prompt)
    logging.info(SCRIPT+"- get_bot_response(): %r", f"RESPONSE: {bot_response}")

    # extracted_details = safe_json_loads(extracted_text)
    return bot_response, confidence_score

def prepare_data_for_summarization(actual_file_name,mask_value):
    prefix=actual_file_name.replace('.pdf','')
    extracted_content_file_path=file_path_extracted_content.format(prefix)
    logging.info(SCRIPT+"--prepare_data_for_summarization: %r", f"extracted_content_file_path: {extracted_content_file_path}")  
    #if extracted content file does not exists; then trigger the openapi server
    if not os.path.exists(extracted_content_file_path):
        logging.info(SCRIPT+"--prepare_data_for_summarization: %r", f"Extracting text from pdfs...")
        file_content = get_pdf_text(file_path,actual_file_name)
        write_patients_data(file_content,actual_file_name)
        # mask_value=False
    else:
        #READ SAVED DATA -- OPENAPI_TRIGGER_3.1
        logging.info(SCRIPT+"--prepare_data_for_summarization: %r", f"Extracting text from saved files...")
        file_content=get_patients_data(actual_file_name)
        # mask_value=True 

    create_patient_summarization(actual_file_name,file_content,prompt_summarization,tag='summarize',read_local_file=mask_value)


def start_extration_and_DbInsertion_process(st, file_path,actual_file_name,message_placeholder=None, selected_measure_UI=[],measurement_year='', process ='Single Processing'):

    if process == 'Single Processing':
        placeholder_msg='Extracting data from input file.'
        file_path=file_path
    else:
        placeholder_msg=f'Extracting data from input file {actual_file_name} .'
        actual_file_name_batch=actual_file_name if actual_file_name.strip('').endswith('.pdf') else actual_file_name+'.pdf'
        file_path= os.path.join(file_path, actual_file_name_batch)


    #this is for total execution time taken by each measure
    time_df = pd.DataFrame(columns=['Measure', 'Start', 'End', 'Duration', 'Accuracy'])
    print(f"measurement_year: {measurement_year}")
    print(f'FILE_PATH from Hedis_UI.py: {file_path}')
    load_dotenv()
    #required for databse insertion
    server = os.getenv('HEDIS_SERVER')
    database = os.getenv('HEDIS_DATABASE')

    member_id=extract_member_id(actual_file_name)
    file_info_data={'FIleID':member_id,
                     'Pdf_location':file_path, 
                     'Pdf_filename':actual_file_name,
                     'Measurement_Year': measurement_year,
                     'Process':process}
    file_info_df=pd.DataFrame(file_info_data, index=[0])
    db.insert_df_into_db(server,database,table_name='file_info',dataframe=file_info_df,member_id=member_id,file_name=actual_file_name)

    start=datetime.now()
    
    message_placeholder.info(placeholder_msg)

    #OPENAPI_TRIGGER_2
    prefix=actual_file_name.replace('.pdf','')
    extracted_content_file_path=file_path_extracted_content.format(prefix)
    logging.info(SCRIPT+": %r", f"extracted_content_file_path: {extracted_content_file_path}")  
    
    #if extracted content file does not exists; then trigger the openapi server
    if not os.path.exists(extracted_content_file_path):
        logging.info(SCRIPT+": %r", f"Extracting text from pdfs...")
        file_content = get_pdf_text(file_path,actual_file_name)
        write_patients_data(file_content,actual_file_name)
        mask_value=False
    else:
        #READ SAVED DATA -- OPENAPI_TRIGGER_3
        logging.info(SCRIPT+": %r", f"Extracting text from saved files...")
        file_content=get_patients_data(actual_file_name)
        mask_value=True
        #DEMO 
    
    end=datetime.now()
    create_execution_time_df(time_df,'Text Extraction',start, end)

    logging.info(SCRIPT+": %r", f"mask_value :{mask_value}")

    logging.info(SCRIPT+": %r", f"#### Extracted Response #### :{file_content}")

    tokens= [ i for i in file_content.split(' ') if len(i.strip(' '))>0]
    print(f'\nTOTAL TOKENS FEEDED TO OpenAI: {len(tokens)}')
    logging.info(SCRIPT+": %r", f'\nTOTAL TOKENS FEEDED TO OpenAI: {len(tokens)}')
    

    if os.path.exists("temp_files\\generic_response_content.txt"):
        os.remove("temp_files\\generic_response_content.txt")

    # sys.exit()

    try: 
        # OPENAPI_TRIGGER_4
        if not mask_value:
            message_placeholder.info('Process is  running for GENERIC_INFO.')
            start=datetime.now()
            print("EXTRACTING GENERIC_INFO DETAILS OF PATIENT")
            logging.info(SCRIPT+": %r", f'EXTRACTING GENERIC_INFO DETAILS OF PATIENT')
            generic_df_excel, confidence_score=extract_and_insert(file_path,actual_file_name, file_content,prompt_Generic,{},server,database,generic_table_name,prompt_type='generic',tag='generic',read_local_file=False,process=process)
            create_and_append(excel_path, generic_df_excel, sheet_name='memberinfo')
            end=datetime.now()
            create_execution_time_df(time_df,'generic',start, end, confidence_score)


        #summarisation
        # if "Generate Summary" in selected_measure_UI:
        create_patient_summarization(actual_file_name,file_content,prompt_summarization,tag='summarize',read_local_file=mask_value)

        if 'BCS' in selected_measure_UI:
            message_placeholder.info('Process running for BCS measure.')
            logging.info(SCRIPT+": %r", f'EXTRACTING BCS DETAILS OF PATIENT')
            start=datetime.now()
            bcs_df_excel, confidence_score=extract_and_insert(file_path,actual_file_name, file_content,prompt_BCS,output_format_BCS,server,database,bcs_table_name, tag='BCS',read_local_file=mask_value,process=process)
            create_and_append(excel_path, bcs_df_excel, sheet_name='BCS')
            end=datetime.now()
            create_execution_time_df(time_df,'BCS',start, end, confidence_score)

        if 'CBP' in selected_measure_UI:
            message_placeholder.info('Process running for CBP measure.')
            start=datetime.now()
            logging.info(SCRIPT+": %r", f'EXTRACTING CBP DETAILS OF PATIENT')
            cbp_df_excel,confidence_score=extract_and_insert(file_path, actual_file_name, file_content,prompt_CBP,output_format_CBP,server,database,cbp_table_name, tag='CBP', read_local_file=mask_value,process=process)
            create_and_append(excel_path, cbp_df_excel, sheet_name='CBP')
            end=datetime.now()
            create_execution_time_df(time_df,'CBP',start, end, confidence_score)

        if 'HBD' in selected_measure_UI:
            message_placeholder.info('Process running for HBD measure.')
            start=datetime.now()
            logging.info(SCRIPT+": %r", f'EXTRACTING HBP DETAILS OF PATIENT')
            hbd_df_excel,confidence_score=extract_and_insert(file_path, actual_file_name, file_content,prompt_HBD,output_format_HBD,server,database,hbd_table_name,tag='HBD',read_local_file=mask_value,process=process)
            create_and_append(excel_path, hbd_df_excel, sheet_name='HBD')
            end=datetime.now()
            create_execution_time_df(time_df,'HBD',start, end, confidence_score)

        if 'COL' in selected_measure_UI:
            message_placeholder.info('Process running for COL measure.')
            start=datetime.now()
            logging.info(SCRIPT+": %r", f'EXTRACTING COL DETAILS OF PATIENT')
            col_df_excel,confidence_score=extract_and_insert(file_path, actual_file_name, file_content,prompt_COL,output_format_COL,server,database,col_table_name, tag='COL',read_local_file=mask_value,process=process)
            create_and_append(excel_path, col_df_excel, sheet_name='COL')
            end=datetime.now()
            create_execution_time_df(time_df,'COL',start, end, confidence_score)

        if 'BPD' in selected_measure_UI:
            message_placeholder.info('Process running for BPD measure.')
            start=datetime.now()
            logging.info(SCRIPT+": %r", f'EXTRACTING BPD DETAILS OF PATIENT')
            bpd_df_excel,confidence_score=extract_and_insert(file_path, actual_file_name, file_content,prompt_BPD,output_format_BPD,server,database,bpd_table_name, tag='BPD',read_local_file=mask_value,process=process)
            create_and_append(excel_path, bpd_df_excel, sheet_name='BPD')
            end=datetime.now()
            create_execution_time_df(time_df,'BPD',start, end, confidence_score)

        if 'EED' in selected_measure_UI:
            message_placeholder.info('Process running for EED measure.')
            start=datetime.now()
            logging.info(SCRIPT+": %r", f'EXTRACTING EED DETAILS OF PATIENT')
            eed_df_excel,confidence_score=extract_and_insert(file_path, actual_file_name, file_content,prompt_EED,output_format_EED,server,database,eed_table_name,tag='EED',read_local_file=mask_value,process=process)
            create_and_append(excel_path, eed_df_excel, sheet_name='EED')
            end=datetime.now()
            create_execution_time_df(time_df,'EED',start, end, confidence_score)

        if 'CCS' in selected_measure_UI:
            message_placeholder.info('Process running for CCS measure.')
            start=datetime.now()
            logging.info(SCRIPT+": %r", f'EXTRACTING CCS DETAILS OF PATIENT')
            ccs_df_excel,confidence_score=extract_and_insert(file_path, actual_file_name, file_content,prompt_CCS,output_format_CCS,server,database,ccs_table_name,tag='CCS',read_local_file=mask_value,process=process)
            create_and_append(excel_path, ccs_df_excel, sheet_name='CCS')
            end=datetime.now()
            create_execution_time_df(time_df,'CCS',start, end, confidence_score)

        # if 'LSD' in selected_measure_UI:
        #     message_placeholder.info('Process running for LSD measure.')
        #     start=datetime.now()
        #     logging.info(SCRIPT+": %r", f'EXTRACTING LSD DETAILS OF PATIENT')
        #     LSD_df_excel,confidence_score=extract_and_insert(file_path, actual_file_name, file_content,prompt_LSD,output_format_LSD,server,database,lsd_table_name,tag='LSD',read_local_file=mask_value,process=process)
        #     create_and_append(excel_path, LSD_df_excel, sheet_name='LSD')
        #     end=datetime.now()
        #     create_execution_time_df(time_df,'LSD',start, end, confidence_score)
    
        # if 'PPC' in selected_measure_UI:
        #     message_placeholder.info('Process running for PPC measure.')
        #     start=datetime.now()
        #     logging.info(SCRIPT+": %r", f'EXTRACTING PPC DETAILS OF PATIENT')
        #     PPC_df_excel,confidence_score=extract_and_insert(file_path, actual_file_name, file_content,prompt_PPC,output_format_PPC,server,database,ppc_table_name,tag='PPC',read_local_file=mask_value,process=process)
        #     create_and_append(excel_path, PPC_df_excel, sheet_name='PPC')
        #     end=datetime.now()
        #     create_execution_time_df(time_df,'PPC',start, end, confidence_score)


        
        # start=datetime.now()
        # print("EXTRACTING IMA DETAILS OF PATIENT")
        # ima_df_excel,confidence_score=extract_and_insert(file_path, actual_file_name, file_content,prompt_IMA,output_format_IMA,server,database,ima_table_name,tag='IMA',read_local_file=mask_value)
        # create_and_append(excel_path, ima_df_excel, sheet_name='IMA')
        # end=datetime.now()
        # create_execution_time_df(time_df,'IMA',start, end, confidence_score)

        
        # print(time_df)

        logging.info(SCRIPT+": %r", f'****STATISTICS*****')
        logging.info(SCRIPT+": %r", time_df)

        #AK: we need the confidence scroe  in New_file_intake.py for display purpose
        create_json_file(time_df)

        #AK: add statistics df to database
        insert_date_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        time_df['Insert_Date']=insert_date_time
        time_df['FileName']=actual_file_name
        time_df['Member_Id']=member_id
        logging.info(SCRIPT+": %r", time_df)

        db.insert_statistics_into_db(server,database,'stats',time_df)
                

        time_df.to_excel("temp_files\\STATISTICS.xlsx", index= False)
        
        #clear the time df
        # time_df = time_df[0:0]  # Keeps column names and types, drops all data
    except Exception as e:
        error_message=str(e)
        msg= "EXCEPTION: ", type(e).__name__, '----',error_message

        # print(msg)
        # print(f"\n\n{error_message}")

        # Get traceback details
        tb = traceback.extract_tb(sys.exc_info()[2])[-1]
        filename = tb.filename
        line = tb.lineno
        func_name = tb.name
        error_type = type(e).__name__
        error_message = str(e)

        full_msg = (f"EXCEPTION: {error_type} in {func_name}(), File {filename}, at line number {line} — {error_message}")

        logging.error(full_msg)

        handle_exceptions(st,message_placeholder,error_message, msg)


#THIS FUNCTION batch_start_extration_and_DbInsertion_process  IS ALMOST SIMILAR TO THE  start_extration_and_DbInsertion_process. batch_start_extration_and_DbInsertion_process FUNCTION IS WITHOUT THE STREAMLIT CONTROLS. 
#THERE IS A CODE REDUNDANCY AS OF NOW  IN BOTH THE FUNCTION. THE GOAL IS TO CREATE A GENERIC FUNCTION.
def batch_start_extration_and_DbInsertion_process( file_path,actual_file_name, selected_measure_UI=[],measurement_year='', process ='Batch Processing'):

    actual_file_name_batch=actual_file_name if actual_file_name.strip('').endswith('.pdf') else actual_file_name+'.pdf'
    file_path= os.path.join(file_path, actual_file_name_batch)


    #this is for total execution time taken by each measure
    time_df = pd.DataFrame(columns=['Measure', 'Start', 'End', 'Duration', 'Accuracy'])
    print(f"measurement_year: {measurement_year}")
    print(f'FILE_PATH from Hedis_UI.py: {file_path}')
    load_dotenv()
    #required for databse insertion
    server = os.getenv('HEDIS_SERVER')
    database = os.getenv('HEDIS_DATABASE')

    member_id=extract_member_id(actual_file_name)
    file_info_data={'FIleID':member_id,
                     'Pdf_location':file_path, 
                     'Pdf_filename':actual_file_name,
                     'Measurement_Year': measurement_year,
                     'Process':process}
    file_info_df=pd.DataFrame(file_info_data, index=[0])
    db.insert_df_into_db(server,database,table_name='file_info',dataframe=file_info_df,member_id=member_id,file_name=actual_file_name)

    start=datetime.now()

    #OPENAPI_TRIGGER_2
    prefix=actual_file_name.replace('.pdf','')
    extracted_content_file_path=file_path_extracted_content.format(prefix)
    logging.info(SCRIPT+": %r", f"extracted_content_file_path: {extracted_content_file_path}")  
    
    #if extracted content file does not exists; then trigger the openapi server
    if not os.path.exists(extracted_content_file_path):
        logging.info(SCRIPT+": %r", f"Extracting text from pdfs...")
        file_content = get_pdf_text(file_path,actual_file_name)
        write_patients_data(file_content,actual_file_name)
        mask_value=False
    else:
        #READ SAVED DATA -- OPENAPI_TRIGGER_3
        logging.info(SCRIPT+": %r", f"Extracting text from saved files...")
        file_content=get_patients_data(actual_file_name)
        mask_value=True 
    
    end=datetime.now()
    create_execution_time_df(time_df,'Text Extraction',start, end)

    logging.info(SCRIPT+": %r", f"mask_value :{mask_value}")

    logging.info(SCRIPT+": %r", f"#### Extracted Response #### :{file_content}")

    tokens= [ i for i in file_content.split(' ') if len(i.strip(' '))>0]
    print(f'\nTOTAL TOKENS FEEDED TO OpenAI: {len(tokens)}')
    logging.info(SCRIPT+": %r", f'\nTOTAL TOKENS FEEDED TO OpenAI: {len(tokens)}')
    

    if os.path.exists("temp_files\\generic_response_content.txt"):
        os.remove("temp_files\\generic_response_content.txt")

    # sys.exit()

    try: 
        #OPENAPI_TRIGGER_4
        if not mask_value:
            start=datetime.now()
            print("EXTRACTING GENERIC_INFO DETAILS OF PATIENT")
            logging.info(SCRIPT+": %r", f'EXTRACTING GENERIC_INFO DETAILS OF PATIENT')
            generic_df_excel, confidence_score=extract_and_insert(file_path,actual_file_name, file_content,prompt_Generic,{},server,database,generic_table_name,prompt_type='generic',tag='generic',read_local_file=False,process=process)
            create_and_append(excel_path, generic_df_excel, sheet_name='memberinfo')
            end=datetime.now()
            create_execution_time_df(time_df,'generic',start, end, confidence_score)


        #summarisation
        # if "Generate Summary" in selected_measure_UI:
        create_patient_summarization(actual_file_name,file_content,prompt_summarization,tag='summarize',read_local_file=mask_value)

        if 'BCS' in selected_measure_UI:
            logging.info(SCRIPT+": %r", f'EXTRACTING BCS DETAILS OF PATIENT')
            start=datetime.now()
            bcs_df_excel, confidence_score=extract_and_insert(file_path,actual_file_name, file_content,prompt_BCS,output_format_BCS,server,database,bcs_table_name, tag='BCS',read_local_file=mask_value,process=process)
            create_and_append(excel_path, bcs_df_excel, sheet_name='BCS')
            end=datetime.now()
            create_execution_time_df(time_df,'BCS',start, end, confidence_score)

        if 'CBP' in selected_measure_UI:
            start=datetime.now()
            logging.info(SCRIPT+": %r", f'EXTRACTING CBP DETAILS OF PATIENT')
            cbp_df_excel,confidence_score=extract_and_insert(file_path, actual_file_name, file_content,prompt_CBP,output_format_CBP,server,database,cbp_table_name, tag='CBP', read_local_file=mask_value,process=process)
            create_and_append(excel_path, cbp_df_excel, sheet_name='CBP')
            end=datetime.now()
            create_execution_time_df(time_df,'CBP',start, end, confidence_score)

        if 'HBD' in selected_measure_UI:
            start=datetime.now()
            logging.info(SCRIPT+": %r", f'EXTRACTING HBP DETAILS OF PATIENT')
            hbd_df_excel,confidence_score=extract_and_insert(file_path, actual_file_name, file_content,prompt_HBD,output_format_HBD,server,database,hbd_table_name,tag='HBD',read_local_file=mask_value,process=process)
            create_and_append(excel_path, hbd_df_excel, sheet_name='HBD')
            end=datetime.now()
            create_execution_time_df(time_df,'HBD',start, end, confidence_score)

        if 'COL' in selected_measure_UI:
            start=datetime.now()
            logging.info(SCRIPT+": %r", f'EXTRACTING COL DETAILS OF PATIENT')
            col_df_excel,confidence_score=extract_and_insert(file_path, actual_file_name, file_content,prompt_COL,output_format_COL,server,database,col_table_name, tag='COL',read_local_file=mask_value,process=process)
            create_and_append(excel_path, col_df_excel, sheet_name='COL')
            end=datetime.now()
            create_execution_time_df(time_df,'COL',start, end, confidence_score)

        if 'BPD' in selected_measure_UI:
            start=datetime.now()
            logging.info(SCRIPT+": %r", f'EXTRACTING BPD DETAILS OF PATIENT')
            bpd_df_excel,confidence_score=extract_and_insert(file_path, actual_file_name, file_content,prompt_BPD,output_format_BPD,server,database,bpd_table_name, tag='BPD',read_local_file=mask_value,process=process)
            create_and_append(excel_path, bpd_df_excel, sheet_name='BPD')
            end=datetime.now()
            create_execution_time_df(time_df,'BPD',start, end, confidence_score)

        if 'EED' in selected_measure_UI:
            start=datetime.now()
            logging.info(SCRIPT+": %r", f'EXTRACTING EED DETAILS OF PATIENT')
            eed_df_excel,confidence_score=extract_and_insert(file_path, actual_file_name, file_content,prompt_EED,output_format_EED,server,database,eed_table_name,tag='EED',read_local_file=mask_value,process=process)
            create_and_append(excel_path, eed_df_excel, sheet_name='EED')
            end=datetime.now()
            create_execution_time_df(time_df,'EED',start, end, confidence_score)

        if 'CCS' in selected_measure_UI:
            start=datetime.now()
            logging.info(SCRIPT+": %r", f'EXTRACTING CCS DETAILS OF PATIENT')
            ccs_df_excel,confidence_score=extract_and_insert(file_path, actual_file_name, file_content,prompt_CCS,output_format_CCS,server,database,ccs_table_name,tag='CCS',read_local_file=mask_value,process=process)
            create_and_append(excel_path, ccs_df_excel, sheet_name='CCS')
            end=datetime.now()
            create_execution_time_df(time_df,'CCS',start, end, confidence_score)

        # if 'LSD' in selected_measure_UI:
        #     start=datetime.now()
        #     logging.info(SCRIPT+": %r", f'EXTRACTING LSD DETAILS OF PATIENT')
        #     LSD_df_excel,confidence_score=extract_and_insert(file_path, actual_file_name, file_content,prompt_LSD,output_format_LSD,server,database,lsd_table_name,tag='LSD',read_local_file=mask_value,process=process)
        #     create_and_append(excel_path, LSD_df_excel, sheet_name='LSD')
        #     end=datetime.now()
        #     create_execution_time_df(time_df,'LSD',start, end, confidence_score)
    
        # if 'PPC' in selected_measure_UI:
        #     start=datetime.now()
        #     logging.info(SCRIPT+": %r", f'EXTRACTING PPC DETAILS OF PATIENT')
        #     PPC_df_excel,confidence_score=extract_and_insert(file_path, actual_file_name, file_content,prompt_PPC,output_format_PPC,server,database,ppc_table_name,tag='PPC',read_local_file=mask_value,process=process)
        #     create_and_append(excel_path, PPC_df_excel, sheet_name='PPC')
        #     end=datetime.now()
        #     create_execution_time_df(time_df,'PPC',start, end, confidence_score)


        
        # start=datetime.now()
        # print("EXTRACTING IMA DETAILS OF PATIENT")
        # ima_df_excel,confidence_score=extract_and_insert(file_path, actual_file_name, file_content,prompt_IMA,output_format_IMA,server,database,ima_table_name,tag='IMA',read_local_file=mask_value)
        # create_and_append(excel_path, ima_df_excel, sheet_name='IMA')
        # end=datetime.now()
        # create_execution_time_df(time_df,'IMA',start, end, confidence_score)

        
        # print(time_df)

        logging.info(SCRIPT+": %r", f'****STATISTICS*****')
        logging.info(SCRIPT+": %r", time_df)

        #AK: we need the confidence scroe  in New_file_intake.py for display purpose
        create_json_file(time_df)

        #AK: add statistics df to database
        insert_date_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        time_df['Insert_Date']=insert_date_time
        time_df['FileName']=actual_file_name
        time_df['Member_Id']=member_id
        logging.info(SCRIPT+": %r", time_df)

        db.insert_statistics_into_db(server,database,'stats',time_df)
                

        time_df.to_excel("temp_files\\STATISTICS.xlsx", index= False)
        
        #clear the time df
        # time_df = time_df[0:0]  # Keeps column names and types, drops all data
    except Exception as e:
        error_message=str(e)
        msg= "EXCEPTION: ", type(e).__name__, '----',error_message

        # print(msg)
        # print(f"\n\n{error_message}")

        # Get traceback details
        tb = traceback.extract_tb(sys.exc_info()[2])[-1]
        filename = tb.filename
        line = tb.lineno
        func_name = tb.name
        error_type = type(e).__name__
        error_message = str(e)

        full_msg = (f"EXCEPTION: {error_type} in {func_name}(), File {filename}, at line number {line} — {error_message}")

        logging.error(full_msg)

        # handle_exceptions(st,message_placeholder,error_message, msg)

        


# if __name__ == '__main__':
#     start_extration_and_DbInsertion_process(file_path)

# start_extration_and_DbInsertion_process(file_path,actual_file_name)

def test_function():
    print("I am from hedis_openai.py")