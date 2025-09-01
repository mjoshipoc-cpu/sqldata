css = '''
<style>
.chat-message {
    padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1rem; display: flex
}
.chat-message.user {
    background-color: #2b313e
}
.chat-message.bot {
    background-color: #475063
}
.chat-message .avatar {
  width: 20%;
}
.chat-message .avatar img {
  max-width: 78px;
  max-height: 78px;
  border-radius: 50%;
  object-fit: cover;
}
.chat-message .message {
  width: 80%;
  padding: 0 1.5rem;
  color: #fff;
}
'''

bot_template = '''
<div class="chat-message bot">
    <div class="avatar">
        <img src="C:\\Users\\user\Documents\\ask-multiple-pdfs-main\\assets\\bot.PNG" style="max-height: 78px; max-width: 78px; border-radius: 50%; object-fit: cover;">
    </div>
    <div class="message">{{MSG}}</div>
</div>
'''

user_template = '''
<div class="chat-message user">
    <div class="avatar">
        <img src="C:\\Users\\user\\Documents\\ask-multiple-pdfs-main\\assets\\user.png">
    </div>    
    <div class="message">{{MSG}}</div>
</div>
'''


def cbp_html_template(sheet_name):
    return f"""
    <div id="modal-{sheet_name}" class="modal show">
        <div class="modal-header">
            <span>{sheet_name} Details</span>
        </div>
        <div class="modal-content">
            <strong>Measure Name:</strong> {sheet_name} (Controlling High Blood Pressure)<br><br>
            <details>
                <summary>Description</summary>
                <p>Percentage of members 18–85 years of age who had a diagnosis of hypertension (HTN) and whose blood pressure was adequately controlled during the measurement year.</p>
            </details>
            <details>
                <summary>Eligibility Criteria</summary>
                <ul>
                    <li>Age: 18–85 years as of December 31 of the measurement year.</li>
                    <li>Diagnosis: At least one outpatient visit with a diagnosis of hypertension on or before June 30 of the measurement year.</li>
                    <li>Continuous Enrollment: Required for 12 months prior to December 31 of the measurement year.</li>
                    <li>Allowable Gap: Up to 45 days in the continuous enrollment period.</li>
                </ul>
            </details>
            <details>
                <summary>Numerator (Compliant Members)</summary>
                <p>Blood pressure controlled based on age:</p>
                <ul>
                    <li>18–59 years: BP < 140/90 mmHg.</li>
                    <li>60–85 years with diabetes: BP < 140/90 mmHg.</li>
                    <li>60–85 years without diabetes: BP < 150/90 mmHg.</li>
                </ul>
            </details>
            <details>
                <summary>Exclusion Criteria</summary>
                <ul>
                    <li>Enrolled in hospice or palliative care.</li>
                    <li>End-stage renal disease (ESRD).</li>
                    <li>Pregnancy during the measurement year.</li>
                    <li>Advanced illness and frailty in Medicare members.</li>
                </ul>
            </details>
        </div>
    </div>
    """