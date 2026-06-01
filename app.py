import os
import fitz
from flask import Flask, render_template, request
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def extract_text_from_pdf(pdf_file):
    pdf_bytes = pdf_file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyse', methods=['POST'])
def analyse():
    job_description = request.form['job_description']
    tone = request.form.get('tone', 'professional')

    cv_text = ""
    if 'cv' in request.files and request.files['cv'].filename != '':
        cv_text = extract_text_from_pdf(request.files['cv'])
    elif request.form.get('cv_text'):
        cv_text = request.form.get('cv_text')

    tone_instructions = {
        'professional': 'Write in a formal, professional tone.',
        'friendly': 'Write in a warm, friendly and approachable tone.',
        'bold': 'Write in a bold, confident and assertive tone that stands out.'
    }

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        messages=[
            {
                "role": "user",
                "content": f"""You are a professional career coach and CV expert.

Analyse this CV against the job description. You MUST use EXACTLY these section headings in EXACTLY this order, with nothing else before or after each heading:

JOB TITLE
Write only the job title on one line.

MATCH SCORE
Write only the percentage on one line, e.g. 45%

QUICK WINS
- Write exactly 3 bullet points, each under 15 words, starting with a dash.

STRENGTHS
- Write exactly 3 bullet points in format "Title: explanation", starting with a dash.

MISSING SKILLS
- Write each missing skill as a short tag (2-5 words max), one per line, starting with a dash.

IMPROVED BULLETS
- Write exactly 3 improved CV bullet points only. Do not include the original bullets. Each starts with a dash and is one sentence.

LINKEDIN SUMMARY
Write 3-4 sentences for a LinkedIn summary. No bullet points.

COVER LETTER
{tone_instructions[tone]} Write a full cover letter. No extra notes or advice after the letter.

CV:
{cv_text}

JOB DESCRIPTION:
{job_description}

IMPORTANT: Use ONLY the section headings listed above. Do not add any other text, notes, or sections outside of these headings."""
            }
        ]
    )

    result = message.content[0].text
    return render_template('result.html', result=result)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)