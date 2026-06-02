import os
import fitz
from flask import Flask, render_template, request, redirect, url_for, flash
from anthropic import Anthropic
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cvtailor.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
client = Anthropic()

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    analyses = db.relationship('Analysis', backref='user', lazy=True)

class Analysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_title = db.Column(db.String(200))
    match_score = db.Column(db.String(10))
    result = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def extract_text_from_pdf(pdf_file):
    pdf_bytes = pdf_file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

# Routes
@app.route('/health')
def health():
    return 'OK', 200

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email').strip().lower()
        name = request.form.get('name').strip()
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')

        if password != confirm:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('signup'))
        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'error')
            return redirect(url_for('signup'))
        if User.query.filter_by(email=email).first():
            flash('An account with that email already exists.', 'error')
            return redirect(url_for('signup'))

        hashed = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(email=email, name=name, password=hashed)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('index'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Incorrect email or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/history')
@login_required
def history():
    analyses = Analysis.query.filter_by(user_id=current_user.id).order_by(Analysis.created_at.desc()).all()
    return render_template('history.html', analyses=analyses)

@app.route('/history/<int:id>')
@login_required
def view_analysis(id):
    analysis = Analysis.query.get_or_404(id)
    if analysis.user_id != current_user.id:
        return redirect(url_for('history'))
    return render_template('result.html', result=analysis.result)

@app.route('/history/<int:id>/delete', methods=['POST'])
@login_required
def delete_analysis(id):
    analysis = Analysis.query.get_or_404(id)
    if analysis.user_id == current_user.id:
        db.session.delete(analysis)
        db.session.commit()
    return redirect(url_for('history'))

@app.route('/analyse', methods=['POST'])
@login_required
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

    job_title = "Unknown Role"
    match_score = "0%"
    lines = result.split('\n')
    for i, line in enumerate(lines):
        stripped = line.strip()
        if '%' in stripped and len(stripped) < 10:
            match_score = stripped
        if stripped and len(stripped) < 100 and not stripped.startswith('-') and 'JOB TITLE' not in stripped.upper() and job_title == "Unknown Role":
            job_title = stripped

    analysis = Analysis(
        job_title=job_title,
        match_score=match_score,
        result=result,
        user_id=current_user.id
    )
    db.session.add(analysis)
    db.session.commit()

    return render_template('result.html', result=result)

@app.route('/account')
@login_required
def account():
    analyses = Analysis.query.filter_by(user_id=current_user.id).all()
    return render_template('account.html', total=len(analyses))

@app.route('/account/update', methods=['POST'])
@login_required
def update_account():
    action = request.form.get('action')

    if action == 'update_profile':
    name = request.form.get('name', '').strip()
    new_email = request.form.get('email', '').strip().lower()
    
    if not name:
        flash('Name cannot be empty.', 'error')
        return redirect(url_for('account'))
    
    if not new_email:
        flash('Email cannot be empty.', 'error')
        return redirect(url_for('account'))
    
    if new_email != current_user.email:
        existing = User.query.filter_by(email=new_email).first()
        if existing:
            flash('That email is already used by another account.', 'error')
            return redirect(url_for('account'))
        current_user.email = new_email
    
    current_user.name = name
    db.session.commit()
    flash('Profile updated successfully.', 'success')

    elif action == 'change_password':
        current_pw = request.form.get('current_password')
        new_pw = request.form.get('new_password')
        confirm_pw = request.form.get('confirm_password')
        if not bcrypt.check_password_hash(current_user.password, current_pw):
            flash('Current password is incorrect.', 'error')
            return redirect(url_for('account'))
        if new_pw != confirm_pw:
            flash('New passwords do not match.', 'error')
            return redirect(url_for('account'))
        if len(new_pw) < 8:
            flash('New password must be at least 8 characters.', 'error')
            return redirect(url_for('account'))
        current_user.password = bcrypt.generate_password_hash(new_pw).decode('utf-8')
        db.session.commit()
        flash('Password changed successfully.', 'success')

    elif action == 'delete_account':
        Analysis.query.filter_by(user_id=current_user.id).delete()
        db.session.delete(current_user)
        db.session.commit()
        logout_user()
        return redirect(url_for('index'))

    return redirect(url_for('account'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('404.html'), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)