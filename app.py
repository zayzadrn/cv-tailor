import os
import os
import fitz
import resend
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import Flask, render_template, request, redirect, url_for, flash, session
from anthropic import Anthropic
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from authlib.integrations.flask_client import OAuth
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime
from sqlalchemy import text

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cvtailor.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['PREFERRED_URL_SCHEME'] = 'https'

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[]
)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])

oauth = OAuth(app)

google = oauth.register(
    name="google",
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile"
    }
)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    password = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    google_id = db.Column(db.String(200), nullable=True)
    pending_email = db.Column(db.String(150), nullable=True)

    analyses = db.relationship(
        "Analysis",
        backref="user",
        lazy=True
    )


class Analysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_title = db.Column(db.String(200))
    match_score = db.Column(db.String(10))
    result = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )


with app.app_context():

    db.create_all()

    migrations = [
        ("google_id", "VARCHAR(200)"),
        ("pending_email", "VARCHAR(150)")
    ]

    for column, column_type in migrations:
        try:
            db.session.execute(
                text(
                    f"ALTER TABLE user ADD COLUMN {column} {column_type}"
                )
            )
            db.session.commit()
            print(f"Added column: {column}")

        except Exception:
            db.session.rollback()


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except Exception as e:
        print("User loader error:", e)
        return None


def extract_text_from_pdf(pdf_file):
    pdf_bytes = pdf_file.read()

    doc = fitz.open(
        stream=pdf_bytes,
        filetype="pdf"
    )

    text_content = ""

    for page in doc:
        text_content += page.get_text()

    doc.close()

    return text_content


def send_email_verification(user, new_email):

    token = serializer.dumps(
        {
            "user_id": user.id,
            "new_email": new_email
        },
        salt="email-change"
    )

    verify_url = url_for(
        "verify_email_change",
        token=token,
        _external=True
    )

    api_key = os.environ.get("RESEND_API_KEY")

    if not api_key:
        print("RESEND_API_KEY not found")
        return False

    resend.api_key = api_key

    try:

        response = resend.Emails.send({

            "from": "CVTailor <onboarding@resend.dev>",

            "to": new_email,

            "subject": "Confirm your new email — CVTailor",

            "text": f"""Hi {user.name},

You requested to change your email address on CVTailor.

Click the link below to confirm your new email:

{verify_url}

This link expires in one hour.

If you didn't request this, simply ignore this email.

CVTailor Team
"""
        })

        print("Resend response:", response)

        return True

    except Exception as e:

        print("Resend error:", e)

        db.session.rollback()

        return False


@app.route("/health")
def health():
    return "OK", 200


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/auth/google")
def google_auth():

    redirect_uri = url_for(
        "google_callback",
        _external=True,
        _scheme="https"
    )

    return google.authorize_redirect(redirect_uri)


@app.route("/auth/google/callback")
def google_callback():

    try:
        token = google.authorize_access_token()

        userinfo = token.get("userinfo")

        if not userinfo:
            userinfo = google.get("userinfo").json()

        google_id = userinfo["sub"]
        email = userinfo["email"]
        name = userinfo.get("name", email.split("@")[0])

        # 1. Try find user by Google ID
        user = User.query.filter_by(google_id=google_id).first()

        # 2. If not found, try email
        if not user:
            user = User.query.filter_by(email=email).first()

            # If user exists but no google_id, link it
            if user and not user.google_id:
                user.google_id = google_id
                db.session.commit()

        # 3. If still no user, create new one
        if not user:
            user = User(
                email=email,
                name=name,
                google_id=google_id
            )
            db.session.add(user)
            db.session.commit()

        login_user(user)

        return redirect(url_for("index"))

    except Exception as e:
        import traceback
        traceback.print_exc()

        flash(f"Google login failed: {str(e)}", "error")

        return redirect(url_for("login"))
@app.route("/signup", methods=["GET", "POST"])
def signup():

    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":

        email = request.form.get("email").strip().lower()
        name = request.form.get("name").strip()
        password = request.form.get("password")
        confirm = request.form.get("confirm_password")

        if password != confirm:
            flash("Passwords do not match.", "error")
            return redirect(url_for("signup"))

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return redirect(url_for("signup"))

        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "error")
            return redirect(url_for("signup"))

        hashed = bcrypt.generate_password_hash(password).decode("utf-8")

        user = User(
            email=email,
            name=name,
            password=hashed
        )

        db.session.add(user)
        db.session.commit()

        login_user(user)

        return redirect(url_for("index"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":

        email = request.form.get("email").strip().lower()
        password = request.form.get("password")

        user = User.query.filter_by(
            email=email
        ).first()

        if (
            user
            and user.password
            and bcrypt.check_password_hash(
                user.password,
                password
            )
        ):
            login_user(user)
            return redirect(url_for("index"))

        flash("Incorrect email or password.", "error")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/history")
@login_required
def history():

    analyses = (
        Analysis.query
        .filter_by(user_id=current_user.id)
        .order_by(Analysis.created_at.desc())
        .all()
    )

    return render_template(
        "history.html",
        analyses=analyses
    )


@app.route("/history/<int:id>")
@login_required
def view_analysis(id):
    analysis = Analysis.query.get_or_404(id)

    if analysis.user_id != current_user.id:
        flash('Analysis not found.', 'error')
        return redirect(url_for('history'))

    return render_template('result.html', result=analysis.result)


@app.route('/history/<int:id>/delete', methods=['POST'])
@login_required
def delete_analysis(id):
    analysis = Analysis.query.get_or_404(id)

    if analysis.user_id != current_user.id:
        flash('Analysis not found.', 'error')
        return redirect(url_for('history'))

    db.session.delete(analysis)
    db.session.commit()

    flash('Analysis deleted.', 'success')
    return redirect(url_for('history'))


@app.route('/account')
@login_required
def account():
    analyses = Analysis.query.filter_by(user_id=current_user.id).all()
    return render_template('account.html', total=len(analyses))


@app.route('/account/update', methods=['POST'])
@login_required
def update_account():
    action = request.form.get('action')

    if action == 'update_name':
        name = request.form.get('name', '').strip()

        if not name:
            flash('Name cannot be empty.', 'error')
            return redirect(url_for('account'))

        current_user.name = name
        db.session.commit()

        flash('Name updated successfully.', 'success')

    elif action == 'change_email':
        new_email = request.form.get('new_email', '').strip().lower()
        confirm_email = request.form.get('confirm_email', '').strip().lower()
        password = request.form.get('password', '')

        if not current_user.password:
            flash('Google login accounts cannot change email here.', 'error')
            return redirect(url_for('account'))

        if not bcrypt.check_password_hash(current_user.password, password):
            flash('Incorrect password.', 'error')
            return redirect(url_for('account'))

        if new_email != confirm_email:
            flash('Email addresses do not match.', 'error')
            return redirect(url_for('account'))

        if new_email == current_user.email:
            flash('That is already your current email.', 'error')
            return redirect(url_for('account'))

        if User.query.filter_by(email=new_email).first():
            flash('That email is already used by another account.', 'error')
            return redirect(url_for('account'))

        current_user.pending_email = new_email
        db.session.commit()

        if send_email_verification(current_user, new_email):
            flash(f'Verification email sent to {new_email}.', 'success')
        else:
            flash('Failed to send verification email.', 'error')

    elif action == 'change_password':
        current_pw = request.form.get('current_password')
        new_pw = request.form.get('new_password')
        confirm_pw = request.form.get('confirm_password')

        if not current_user.password:
            flash('Google login accounts cannot change password here yet.', 'error')
            return redirect(url_for('account'))

        if not bcrypt.check_password_hash(current_user.password, current_pw):
            flash('Current password is incorrect.', 'error')
            return redirect(url_for('account'))

        if new_pw != confirm_pw:
            flash('New passwords do not match.', 'error')
            return redirect(url_for('account'))

        if len(new_pw) < 8:
            flash('Password must be at least 8 characters.', 'error')
            return redirect(url_for('account'))

        current_user.password = bcrypt.generate_password_hash(new_pw).decode('utf-8')
        db.session.commit()

        flash('Password changed successfully.', 'success')

    elif action == 'delete_account':
        Analysis.query.filter_by(user_id=current_user.id).delete()

        db.session.delete(current_user)
        db.session.commit()

        logout_user()

        flash('Account deleted successfully.', 'success')
        return redirect(url_for('index'))

    return redirect(url_for('account'))


@app.route('/verify-email/<token>')
def verify_email_change(token):
    try:
        data = serializer.loads(
            token,
            salt='email-change',
            max_age=3600
        )

        user = db.session.get(User, data['user_id'])

        if (
            user
            and hasattr(user, 'pending_email')
            and user.pending_email == data['new_email']
        ):
            user.email = user.pending_email
            user.pending_email = None

            db.session.commit()

            flash('Email address updated successfully!', 'success')

            if current_user.is_authenticated:
                return redirect(url_for('account'))

            return redirect(url_for('login'))

        flash('Verification link is invalid.', 'error')

    except Exception as e:
        print(f"Email verification error: {e}")
        flash('Verification link is invalid or has expired.', 'error')

    return redirect(url_for('index'))

@app.route('/analyse', methods=['POST'])
@login_required
@limiter.limit("5 per hour")
def analyse():
    job_description = request.form['job_description']
    tone = request.form.get('tone', 'professional')

    cv_text = ""
    if 'cv' in request.files and request.files['cv'].filename:
        cv_text = extract_text_from_pdf(request.files['cv'])
    elif request.form.get('cv_text'):
        cv_text = request.form.get('cv_text')

    tone_instructions = {
        'professional': 'Write in a formal, professional tone.',
        'friendly': 'Write in a warm, friendly and approachable tone.',
        'bold': 'Write in a bold, confident and assertive tone that stands out.'
    }

    import time
    from concurrent.futures import ThreadPoolExecutor

    prompt1 = f"""You are a world-class career strategist. Be brutally honest, specific and analytical — never generic.

Analyse this CV against the job description. Use EXACTLY these headings in EXACTLY this order:

JOB TITLE
Write only the exact job title on one line.

MATCH SCORE
Write only a number followed by %. Be harsh and realistic — average is 35%. Example: 35%

EXECUTIVE SUMMARY
Write 3 sentences: what this candidate is, their biggest relevant strength, their biggest gap for this role.

QUICK WINS
- Write exactly 4 specific actionable fixes the candidate can do this week. Each bullet starts with a dash, under 20 words.

STRENGTHS
- Write exactly 3 genuine strengths matching the job description. Format "Title: explanation with CV evidence". Each starts with a dash.

MISSING SKILLS
- List every missing skill, tool or requirement from the job description. Each starts with a dash, 2-5 words.

CRITICAL GAPS
- Write exactly 2 dealbreaker gaps that would likely cause rejection. Each starts with a dash and explains why it matters.

CV:
{cv_text}

JOB DESCRIPTION:
{job_description}

CRITICAL: Use ONLY the exact headings above. MATCH SCORE line must contain ONLY a number and %."""

    prompt2 = f"""You are a world-class career strategist. Be specific and tailored — never generic.

Based on this CV and job description, write EXACTLY these sections in EXACTLY this order:

IMPROVED BULLETS
- Rewrite exactly 3 weak CV bullets to be stronger with measurable results. Format "ORIGINAL: [x] → IMPROVED: [y]". Each starts with a dash.

ATS KEYWORDS
- List exactly 8 exact keywords from the job description the CV must include to pass ATS screening. Each starts with a dash.

LINKEDIN SUMMARY
Write 3-4 sentences for a LinkedIn summary specific to this role and CV. No generic phrases.

COVER LETTER
{tone_instructions[tone]} Write a complete, specific cover letter for this role referencing real CV details and job requirements. No clichés. About 250 words.

CV:
{cv_text}

JOB DESCRIPTION:
{job_description}

CRITICAL: Use ONLY the exact headings above."""

    def call_claude(prompt, max_tokens, label):
        start = time.time()
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        print(f"{label} finished in {time.time() - start:.2f}s")
        return message.content[0].text

    try:
        overall_start = time.time()

        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(call_claude, prompt1, 1400, "Call 1")
            future2 = executor.submit(call_claude, prompt2, 1600, "Call 2")

            part1 = future1.result()
            part2 = future2.result()

        print(f"Both calls finished in {time.time() - overall_start:.2f}s total")

        result = part1.strip() + "\n\n" + part2.strip()

    except Exception as e:
        print(f"Claude error: {e}")
        flash("AI analysis failed. Please try again.", "error")
        return redirect(url_for('index'))

    job_title = "Unknown Role"
    match_score = "0%"
    lines = result.splitlines()
    in_title_section = False
    in_score_section = False

    for line in lines:
        stripped = line.strip()
        if stripped.upper() == 'JOB TITLE':
            in_title_section = True
            in_score_section = False
            continue
        if stripped.upper() == 'MATCH SCORE':
            in_score_section = True
            in_title_section = False
            continue
        if stripped.upper() in ['EXECUTIVE SUMMARY', 'QUICK WINS', 'STRENGTHS', 'MISSING SKILLS', 'CRITICAL GAPS', 'IMPROVED BULLETS', 'ATS KEYWORDS', 'LINKEDIN SUMMARY', 'COVER LETTER']:
            in_title_section = False
            in_score_section = False
            continue
        if in_title_section and stripped and job_title == "Unknown Role":
            job_title = stripped
            in_title_section = False
        if in_score_section and stripped:
            import re
            score_match = re.search(r'(\d+)\s*%', stripped)
            if score_match:
                match_score = score_match.group(1) + '%'
                in_score_section = False

    analysis = Analysis(
        job_title=job_title,
        match_score=match_score,
        result=result,
        user_id=current_user.id
    )
    db.session.add(analysis)
    db.session.commit()

    return render_template('result.html', result=result)

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


@app.route('/terms')
def terms():
    return render_template('terms.html')


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    db.session.rollback()
    return render_template('404.html'), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)