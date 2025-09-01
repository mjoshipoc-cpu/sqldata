
import pandas as pd
import streamlit as st
import pyodbc
import base64
import datetime
import io

#UI
st.set_page_config(layout="wide",page_title="HEDISAbstrator.AI")

st.markdown(
    """
    <style>
    .title {
        font-size: 30px;
        font-weight: bold;
        color: white;
        padding-top: 10px;
        padding-bottom: 55px;
        padding-right: 20px;
        padding-left: 20px;
        text-align: center;
        background-color: #fb4e0b;
        # border-top: 10px solid #fb4e0b;
        # border-bottom: 10px solid #fb4e0b;
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
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    f"""
    <div class="title">
        <span class="left">HEDISAbstrator.AI</span>
        <span class="right">EXL</span>
        <div class="text">  </div>
    </div>
    """,
    unsafe_allow_html=True
)



def display_pdf(file_path):
    # Opening the file from the file path
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode("utf-8")
        # Embedding the PDF in HTML
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="550" height="1425" type="application/pdf"></iframe>'
        # Displaying the file
        st.markdown(pdf_display, unsafe_allow_html=True)

def create_pdf_link(pdf_path):
    with open(pdf_path, "rb") as pdf_file:
        base64_pdf = base64.b64encode(pdf_file.read()).decode('utf-8')
    pdf_href = f'<a href="data:application/pdf;base64,{base64_pdf}" target="_blank">Open PDF</a>'
    return pdf_href
    
def create_pdf_download_link(pdf_path):
    with open(pdf_path, "rb") as pdf_file:
        base64_pdf = base64.b64encode(pdf_file.read()).decode('utf-8')
    st.download_button(
        label="Open PDF",
        data=base64.b64decode(base64_pdf),
        file_name="document.pdf",
        mime="application/pdf"
    )

# Streamlit app

# Function to create database connection
def create_connection():
    return pyodbc.connect('DRIVER={SQL Server};'
                          'SERVER=LAPTOP-AG7RJLSV\\SQLEXPRESS;'
                          'DATABASE=EXL;'
                          'Trusted_Connection=yes;')

# Function to get data from the database
def getdata(member_id,table):
    conn = create_connection()
    query = f"SELECT * FROM {table} WHERE Member_id = '{member_id}'"  
    return pd.read_sql(query, conn)

# Function to update data in the database
def update(index, column, value,table):
    conn = create_connection()
    cursor = conn.cursor()
    query = f"UPDATE {table} SET {column} = ? WHERE Member_id = ?" 
    cursor.execute(query, (value, index))
    conn.commit()

    

# Function to update data in the database
def update_data(member_id, updates,table):
    conn = create_connection()
    cursor = conn.cursor()
    for column, value in updates.items():
        query = f"UPDATE {table} SET {column} = ? WHERE Member_id = ?"  # Assuming 'bsc' is the table name
        cursor.execute(query, (value, member_id))
    conn.commit()

def display_pdf(file_path):
    # Opening the file from the file path
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode("utf-8")
        # Embedding the PDF in HTML
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="550" height="1425" type="application/pdf"></iframe>'
        # Displaying the file
        st.markdown(pdf_display, unsafe_allow_html=True)

def create_pdf_link(pdf_path):
    with open(pdf_path, "rb") as pdf_file:
        base64_pdf = base64.b64encode(pdf_file.read()).decode('utf-8')
    pdf_href = f'<a href="data:application/pdf;base64,{base64_pdf}" target="_blank">Open PDF</a>'
    return pdf_href

def lookup_pdf_location(member_id):
    try:
        member_id = int(member_id)  # Convert input to integer
        conn = create_connection()
        query = f"SELECT FileID FROM memberinfo WHERE member_id = {member_id}"
        result1 = pd.read_sql(query, conn)
        if not result1.empty:
            file_id = result1.iloc[0]['FileID']
            query = f"SELECT concat(Pdf_location,'\\',Pdf_filename) as loc FROM file_info WHERE FileID = '{file_id}'"
            result = pd.read_sql(query, conn)
            conn.close()
            if not result.empty:
                return result.iloc[0]['loc']
    except ValueError:
        pass
    return None




# Path to your local PDF file
local_pdf_path = 'IMA_1.pdf'

# Streamlit app
st.title('')

st.write('Please enter the Member ID and select the Edit button to update the data. To download the data associated with the Member ID, click the Export button.')
#st.write('Click on Export button to download the related data to Member ID')
# Search Member ID
st.write('')
search_member_id = st.text_input('**Search Member ID**',label_visibility="visible",
        disabled=False,
        placeholder= "Enter Member ID",
    )

def export():
    if search_member_id:
        # Query data from memberinfo table
        memberinfo_data = getdata(search_member_id,'memberinfo')
        # Query data from bcs table
        
        bcs_data = getdata(search_member_id,'bcs')
        cbp_data = getdata(search_member_id,'cbp')
        hbd_data = getdata(search_member_id,'hbd')
        ccs_data = getdata(search_member_id,'ccs')
        ima_data = getdata(search_member_id,'ima')
        col_data = getdata(search_member_id,'col')
        eed_data = getdata(search_member_id,'eed')
        bpd_data = getdata(search_member_id,'bpd')
        # Create a new Excel file
        with pd.ExcelWriter('member_data.xlsx') as writer:
            # Write data to different sheets
            memberinfo_data.to_excel(writer, sheet_name='memberinfo', index=False)
            bcs_data.to_excel(writer, sheet_name='BCS', index=False)
            cbp_data.to_excel(writer, sheet_name='CBP', index=False)
            hbd_data.to_excel(writer, sheet_name='HBD', index=False)
            ccs_data.to_excel(writer, sheet_name='CCS', index=False)
            ima_data.to_excel(writer, sheet_name='IMA', index=False)
            col_data.to_excel(writer, sheet_name='COL', index=False)
            eed_data.to_excel(writer, sheet_name='EED', index=False)
            bpd_data.to_excel(writer, sheet_name='BPD', index=False)
        # Download link for the Excel file
        with open('member_data.xlsx', 'rb') as file:
            st.download_button(label='Download File',
                                data=file,
                                file_name='member_data.xlsx',
                                mime='application/vnd.ms-excel')
    else:
        st.error('Please enter a Member ID.')
    
    




if search_member_id:
    data = getdata(search_member_id,"memberinfo")
    if not data.empty:
        columns = list(data.columns)
        st.write("**Search Results:**")
        for i, row in data.iterrows():
            cols = st.columns(7)
            cols[0].write(row['Member_id'])
            cols[1].write(row['FileID'])
            cols[2].write(row['Name'])
            cols[3].write(row['Gender'])
            cols[4].write(row['DOB'])
            if cols[5].button("Edit", key=row['Member_id']):
                st.session_state['edit_index'] = row['Member_id']
            if cols[6].button("Export", key=row['FileID']):
                st.session_state['export_index'] = row['Member_id']
                export()

        st.title('')
        # Check if a row is selected for editing
        if 'edit_index' in st.session_state:
            # Get the row data to be edited
            row_to_edit = data[data['Member_id'] == st.session_state['edit_index']].iloc[0]
            left_column, right_column = st.columns([0.5, 0.5],gap="large")
            with left_column:
            # Create a form for editing
                with st.form("edit_form"):

                    tabs = st.tabs(["**General**","**BCS**", "**CBP**", "**HBD**", "**CCS**","**IMA**","**COL**","**EED**","**BPD**"])
                    with tabs[0]:
                        updated_values = {}
                        for col in columns:
                            updated_values[col] = st.text_input(f"**{col}**", value=str(row_to_edit[col]))
                            #updated_values[col] = st.text_input(f"Edit {col}", value=str(row_to_edit[col]),key=f"edit_{col}") 
                        
                    with tabs[1]:
                        data1 = getdata(search_member_id,"bcs")
                        if not data1.empty:
                            updated_bcs = {}
                            for col in data1.columns:
                                #updated_values[col] = st.text_input(f"Edit {col}", value=str(data.at[0, col]))
                                updated_bcs[col] = st.text_input(f"**{col}**", value=str(data1.at[0, col]), key=f"edit_{col}")    
                    with tabs[2]:
                        data2 = getdata(search_member_id,"cbp")
                        if not data2.empty:
                            updated_cbp = {}
                            for col in data2.columns:
                                #updated_values[col] = st.text_input(f"Edit {col}", value=str(data.at[0, col]))
                                updated_cbp[col] = st.text_input(f"**{col}**", value=str(data2.at[0, col]), key=f"edit2_{col}")    
                    with tabs[3]:
                        data3 = getdata(search_member_id,"HBD")
                        if not data3.empty:
                            updated_hbd = {}
                            for col in data3.columns:
                                #updated_values[col] = st.text_input(f"Edit {col}", value=str(data.at[0, col]))
                                updated_hbd[col] = st.text_input(f"**{col}**", value=str(data3.at[0, col]), key=f"edit3_{col}")    
                    with tabs[4]:
                        data4 = getdata(search_member_id,"ccs")
                        if not data4.empty:
                            updated_ccs = {}
                            for col in data4.columns:
                                #updated_values[col] = st.text_input(f"Edit {col}", value=str(data.at[0, col]))
                                updated_ccs[col] = st.text_input(f"**{col}**", value=str(data4.at[0, col]), key=f"edit4_{col}")    
                    
                    with tabs[5]:
                        data5 = getdata(search_member_id,"ima")
                        if not data5.empty:
                            updated_ima = {}
                            for col in data5.columns:
                                #updated_values[col] = st.text_input(f"Edit {col}", value=str(data.at[0, col]))
                                updated_ima[col] = st.text_input(f"**{col}**", value=str(data5.at[0, col]), key=f"edit5_{col}")    
                    
                    with tabs[6]:
                        data6 = getdata(search_member_id,"col")
                        if not data6.empty:
                            updated_col = {}
                            for col in data6.columns:
                                updated_col[col] = st.text_input(f"**{col}**", value=str(data6.at[0, col]), key=f"edit6_{col}")    
                    
                    # with tabs[7]:
                    #     data7 = getdata(search_member_id,"eed")
                    #     if not data7.empty:
                    #         updated_eed = {}
                    #         for col in data7.columns:
                    #             updated_eed[col] = st.text_input(f"**{col}**", value=str(data7.at[0, col]), key=f"edit7_{col}")    
                    
                    # with tabs[8]:
                    #     data8 = getdata(search_member_id,"bpd")
                    #     if not data8.empty:
                    #         updated_bpd = {}
                    #         for col in data8.columns:
                    #             updated_bpd[col] = st.text_input(f"**{col}**", value=str(data8.at[0, col]), key=f"edit8_{col}")    
                                      
                    submit_button = st.form_submit_button("**Submit Changes**")
                    if submit_button:
                        # Update the database with the new values
                        for col, val in updated_values.items():
                            update(st.session_state['edit_index'], col, val,"memberinfo")
                        update_data(search_member_id, updated_bcs,'bcs')
                        update_data(search_member_id, updated_cbp,'cbp')
                        update_data(search_member_id, updated_hbd,'hbd')
                        update_data(search_member_id, updated_ccs,'ccs')
                        update_data(search_member_id, updated_ima,'ima')
                        update_data(search_member_id, updated_col,'col')
                        # update_data(search_member_id, updated_eed,'eed')
                        # update_data(search_member_id, updated_bpd,'bpd')
                        #data1 = getdata(search_member_id,"bcs")
                        #del st.session_state['edit_index']
                        st.success('Data updated successfully!')
    

            with right_column:
                pdf_location = lookup_pdf_location(search_member_id)
                pdf_location=pdf_location.replace('\\','/')
                create_pdf_download_link(pdf_location)
                display_pdf(pdf_location)
            
    else:
        st.error("No data found for the provided Member ID.")