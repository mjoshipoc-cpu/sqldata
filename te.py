I am reaching out to inquire whether you have any resources available to support the HEDIS DQME initiative. We are currently seeking one onsite resource and two offshore resources to assist with this effort.
Please let me know if you require any additional information or clarification regarding this requirement.
 
Position Summary
Seeking a HEDIS & Quality Measures Analyst / Data Engineer to support Digital Quality Measures Engine (DQME) initiatives, HEDIS measure development, Supplemental CQL analysis, FHIR-based data processing, and reporting modernization efforts. This hybrid role combines healthcare quality measure analysis with hands-on data engineering, testing, validation, and automation. Responsibilities include measure analysis, data validation, output reconciliation, testing, healthcare data processing, and development of SQL/Python solutions to support quality measurement and modernization initiatives.
Required Skills
Minimum 3+ years of Healthcare Data Engineering, Healthcare Analytics, Quality Measurement, or Healthcare Reporting experience
Strong SQL development and data analysis skills
Python development experience
Experience with GCP, Big Query, or other cloud platforms
Understanding of healthcare data including claims, membership, provider, and clinical data
Experience with data validation, reconciliation, testing, and troubleshooting
Strong analytical, problem-solving, and communication skills
Preferred Skills
HEDIS or healthcare quality measures experience
Exposure to HL7 FHIR concepts and healthcare interoperability
Exposure to Clinical Quality Language (CQL)
Experience supporting data quality and testing initiatives
Experience working in Agile delivery environments
Responsibilities
Support HEDIS, Supplemental CQL, and quality measure analysis activities.
Perform data validation, reconciliation, testing, and root cause analysis
Analyze measure outputs and supporting evidence
Develop SQL and Python solutions to automate data processing, validation, and reporting activities
Support FHIR mapping and healthcare data transformation initiatives
Document findings, issues, data flows, and business requirements
Support modernization efforts related to quality measurement and healthcare reporting
Nice-to-Have Certifications
Google Cloud Associate Cloud Engineer
Healthcare Informatics Certification
HL7 FHIR Fundamentals Training
Ideal Candidate
A motivated healthcare data professional with strong SQL and Python skills who can quickly learn HEDIS, CQL, FHIR, and DQME concepts while supporting measure development, testing, and modernization initiatives.



 Project: Quality Reporting Tool
Environment : ASP. Net(MVC),C#, SQL Server 2017,SSIS, Power BI ,GitHub Enterprise
Project overview: It is web based one-stop shop reporting solution  built for the HEDIS team that houses more than 50 business reports including Gap In Care/DARTH Reports. It is a self-service tool with a user base of more than 100.The tool has modules to request new report requests, generate ad hoc reports and user maintenance.
Roles & Responsibilities : 
Create & maintain documents defining project scope, requirements, wireframes, change sets, client feedback, constraints and dependencies.
Worked on the creation of DevOps pipeline for the code repository maintenance and deployment.
Requirement discussion with client as well team on best possible technical solutions with feasibility and time constraints.
Worked on designing modular tasks to be assigned to all team members to target delivery dates
Developed use cases and designed wireframes for the front end.
Developed the SQL tables architectural design, backend Stored Procs in SQL Server and ETL Applications in SSIS
Tidal Scheduling of reports with automated email notifications and delivery of reports.
Creation of test plans and documentation of all the deliverables
Pitched the client for adding the BI feature by creating report visualizations in Power BI. 


Project: HEDIS Abstractor.ai- Automated HEDIS Clinical Data Extraction Pipeline
Environment:  Snowflake Cortex AI, Claude Sonnet 4.5, Snowflake AI_PARSE_DOCUMENT, Snowflake Cortex Vector Search, SQL, YAML
Project overview: HEDISAbstractor.ai is an automated healthcare data processing pipeline built on Snowflake Cortex AI that analyzes Electronic Medical Records (EMRs) to evaluate patient compliance with various HEDIS quality measures. The pipeline uses a RAG (Retrieval-Augmented Generation) architecture — embedding parsed EMR text into a vector store and retrieving only the most relevant clinical sections per measure before LLM extraction — to transform unstructured EMR PDF documents into validated, structured HEDIS measure outcomes at scale.
Roles & Responsibilities:
Built an automated PDF ingestion pipeline to detect new EMR files from a Snowflake stage and extract text using Snowflake's AI_PARSE_DOCUMENT.
Implemented a RAG architecture — chunking and embedding parsed EMR text using Snowflake Cortex Vector Search to enable semantic retrieval of relevant clinical sections per HEDIS measure, reducing prompt size and improving extraction accuracy.
Designed measure-specific LLM prompts, grounded in retrieved evidence chunks, to extract structured clinical information from unstructured EMR documents across multiple HEDIS measures.
 Implemented ICD code extraction to identify diagnosed conditions and map relevant codes from clinical documentation.
 Generated structured JSON summaries of patient demographics, diagnoses, medications, and other clinical details.
 Built a secondary LLM-based validation layer producing confidence scores and an evidence matrix linking extracted data back to the retrieved source chunks for auditability.
 Designed idempotent upsert logic in Snowflake tables to prevent duplicate records during reprocessing.

Project: SDOH-Aware Care Outreach Insight Tool
Environment: SQL Server, Python, XGBoost, scikit-learn, Power BI, Snowflake Cortex AI
Project overview: A GenAI-assisted tool that flags members with care gaps (leveraging existing HEDIS Gap-in-Care logic) alongside Social Determinants of Health (SDOH) risk factors — such as transportation access, housing instability, and food insecurity — sourced from public SDOH datasets. An XGBoost model generates a Basic Risk Score (clinical/utilization features) and a Full Risk Score (clinical + SDOH factors), and the LLM layer converts this combined risk data into a plain-English, care-manager-ready outreach recommendation for each member.
Roles & Responsibilities:
Sourced and joined publicly available SDOH indicators with existing Gap-in-Care SQL data at the member/geography level.
Built SQL views combining clinical risk flags with SDOH risk scores for a unified member risk profile.
Built an XGBoost  classification model to generate Basic Score (clinical only) and Full Score (clinical + SDOH) risk predictions, evaluated using AUC/ F1score.
Analyzed feature weightage to identify top clinical and SDOH drivers contributing to member risk.
Designed prompt templates to generate a short, actionable outreach summary per member/cohort using an LLM API.
Added a human-review step so care managers approve/edit AI-generated summaries before outreach.
Visualized combined clinical + SDOH risk (Basic vs. Full Score) in Power BI, with drill-down by geography and measure.
