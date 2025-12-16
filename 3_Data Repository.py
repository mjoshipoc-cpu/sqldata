Below is a **single executive slide** you can paste directly into PPT.
It is concise, security-focused, and **CVS / payer / InfoSec friendly**.

---

## PHI Security & Governance for LLM-Based EMR Processing

**Executive Overview (CVS-Aligned)**

### The Challenge

Using LLMs on EMR data introduces potential PHI exposure risk if not properly governed.

---

### Our Security & Governance Approach

**1. Minimum Necessary PHI Exposure**

* Full EMRs are stored only within a governed Databricks environment
* Prior to LLM use, content is **pre-processed and scoped**
* Only **measure-relevant text segments** (e.g., labs, diagnoses) are sent to the LLM

**2. Secure & Controlled LLM Usage**

* LLM used for **inference only** (no training, no retention of customer data)
* Encrypted transmission (TLS 1.2+)
* Strict, version-controlled prompts for **structured extraction only** (JSON output)

**3. Strong Data Governance**

* Unity Catalog–based access control (least privilege)
* Encryption at rest and in transit
* Role-based access for ingestion, processing, review, and analytics

**4. Human-in-the-Loop Oversight**

* AI outputs are reviewed via a secure Streamlit application
* Authorized users can edit, approve, or reject results
* Full audit trail of all reviewer actions

**5. Auditability & Lineage**

* End-to-end traceability: File → Text → LLM Output → Final Measure
* Evidence preservation (page numbers, source text)
* Prompt version, model version, and run metadata captured

---

### Executive Assurance

> This architecture enables AI-driven efficiency while maintaining payer-grade PHI security, regulatory compliance, and full auditability—aligned with HIPAA and CVS security expectations.

---

If you want next, I can:

* Convert this into a **visual diagram slide**
* Add a **Risk → Control → Mitigation** table beneath it
* Tailor wording exactly to **CVS InfoSec questionnaire language**
