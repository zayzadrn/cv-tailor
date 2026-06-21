CVTailor — AI-Powered CV & Job Application Tool

Upload your CV and a job description. Get an instant AI match score, skills gap analysis, rewritten CV bullets, a tailored cover letter, and a LinkedIn summary — all powered by Claude AI.



What It Does
CVTailor analyses your CV against any job description and gives you:


Match Score — a percentage showing how well your CV fits the role, with a visual score indicator
Strengths — 3 things in your CV that align well with the job
Missing Skills — key gaps shown as visual tags so you can see exactly what to work on
Improved CV Bullets — AI rewrites your existing bullet points to better match the job description
Quick Wins — 3 immediate actions you can take to boost your chances
LinkedIn Summary — an optimised LinkedIn summary tailored to the role
Cover Letter — a full tailored cover letter in your chosen tone (Professional, Friendly, or Bold)
PDF Export — download your full analysis report as a PDF


Screenshots

coming soon..


Tech Stack
LayerTechnologyBackendPython, FlaskAIAnthropic Claude APIPDF ParsingPyMuPDF (fitz)FrontendHTML, CSS, JavaScriptTemplatingJinja2StorageCSV / SQLite (in progress)DeploymentRailway

Features

Upload CV as PDF or paste as plain text
Paste any job description
Choose cover letter tone: Professional, Friendly, or Bold
AI thinking animation with step-by-step progress indicators
Visual match score circle (colour coded: green/amber/red)
Missing skills displayed as visual tags
One-click copy for cover letter and LinkedIn summary
Download full analysis as PDF report
Clean, modern UI — no signup required


Getting Started
Prerequisites

Python 3.12+
An Anthropic API key (get one here)

Installation

Clone the repository:

bashgit clone https://github.com/yourusername/cv-tailor.git
cd cv-tailor

Create and activate a virtual environment:

bashpython3 -m venv venv
source venv/bin/activate

Install dependencies:

bashpip install flask anthropic pymupdf python-dotenv

Create a .env file in the root directory:

ANTHROPIC_API_KEY=your_api_key_here

Run the app:

bashpython3 app.py

Open your browser and go to http://127.0.0.1:5000


Project Structure
cv-tailor/
├── app.py                 # Flask application and routes
├── templates/
│   ├── index.html         # Upload page
│   └── result.html        # Results page
├── static/
│   └── style.css          # Styling
├── .env                   # API keys (not committed to Git)
├── .gitignore             # Ignores .env and venv
└── README.md

Roadmap

 CV upload (PDF and text)
 AI match score with visual indicator
 Skills gap analysis
 CV bullet rewriter
 Cover letter generator
 LinkedIn summary generator
 PDF report download
 Cover letter tone selector
 AI thinking animation
 Analysis history (SQLite)
 User authentication
 Deployment to Railway


What I Learned Building This
This project taught me:

Building a full-stack web application with Flask
Integrating third-party AI APIs (Anthropic Claude)
Handling file uploads and PDF text extraction
Structuring prompts to get reliable, structured AI output
Frontend development with HTML, CSS, and JavaScript
Environment variable management and security best practices


Author
Osman Zadran
Aspiring Python Developer | Currently building real projects to break into tech
GitHub · LinkedIn

License
MIT License — feel free to use this project as inspiration for your own.
