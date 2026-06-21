CVTailor

AI-powered CV and job-match analysis. Upload your CV and a job description, and get an instant match score, skills gap analysis, rewritten bullet points, ATS keyword suggestions, and a tailored cover letter — all generated in under a minute.

🔗 Live app: cv-tailor-production-e361.up.railway.app


Screenshots

Login/Signup

![alt text](<Screenshot 2026-06-21 at 18.27.54.png>)


Homepage

![alt text](<Screenshot 2026-06-20 at 17.56.38.png>)
![alt text](<Screenshot 2026-06-20 at 17.33.56.png>)
![alt text](<Screenshot 2026-06-20 at 17.34.19.png>)

Results
![alt text](<Screenshot 2026-06-20 at 17.56.03.png>)
![alt text](<Screenshot 2026-06-20 at 17.56.15.png>)
![alt text](<Screenshot 2026-06-20 at 17.56.25.png>)




Features


Match Score — an honest, weighted score showing how well a CV fits a specific job description
Executive Summary — a concise AI-written overview of fit, strengths, and gaps
Critical Gaps & Quick Wins — the dealbreaker issues to fix first, plus fast actionable improvements
Missing Skills & ATS Keywords — the exact terms a CV is missing that applicant tracking systems scan for
Improved Bullet Points — before-and-after rewrites of weak CV bullets, tailored to the role
LinkedIn Summary — a ready-to-use profile summary written for the specific job
Tailored Cover Letter — a complete cover letter in a chosen tone (professional, friendly, or bold)
PDF Export — download the full analysis as a formatted PDF
Accounts & History — sign up with email or Google to save and revisit past analyses
Secure authentication — email/password with verification, or Google OAuth



Tech Stack

LayerTechnologyBackendPython, FlaskAIAnthropic API (Claude)PDF parsingPyMuPDFDatabaseSQLite + SQLAlchemyAuthFlask-Login, Authlib (Google OAuth)EmailResendHostingRailwayFrontendHTML, CSS, vanilla JavaScript


How It Works


The user uploads a CV (PDF or pasted text) and pastes a job description.
The backend extracts CV text using PyMuPDF.
Two sequential calls to the Anthropic API analyse the CV against the job description — split into two calls to keep response times fast and reliable:

Call 1 generates the job title, match score, executive summary, quick wins, strengths, and critical gaps.
Call 2 generates improved bullet points, ATS keywords, a LinkedIn summary, and a tailored cover letter.



Results are parsed, stored against the user's account (if logged in), and rendered on the results page.
Users can export the full analysis as a PDF.



Running Locally

bashgit clone https://github.com/zayzadrn/cv-tailor.git
cd cv-tailor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

Create a .env file in the project root with the following:

ANTHROPIC_API_KEY=your_anthropic_api_key
RESEND_API_KEY=your_resend_api_key
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
SECRET_KEY=your_flask_secret_key

Then run:

bashpython app.py

The app will be available at http://127.0.0.1:5001.


Deployment

This app is deployed on Railway. The Procfile runs:

web: gunicorn app:app --timeout 120 --workers 2

Environment variables (API keys, OAuth credentials, PREFERRED_URL_SCHEME=https) are set in the Railway project's Variables tab. A /health endpoint is included for Railway's health checks.


License

This project is for personal and portfolio use.