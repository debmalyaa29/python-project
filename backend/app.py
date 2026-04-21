import os
import requests as http_requests
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
from flask_cors import CORS
from flask_mail import Mail, Message
from dotenv import load_dotenv
from sqlalchemy import func
from datetime import datetime, timedelta
import cloudinary
import cloudinary.uploader

from database import db
from models import User, Issue, Vote

load_dotenv()

app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))

# Database config
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///' + os.path.join(basedir, 'civicfix.db'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Mail config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = f"CivicFix <{os.getenv('MAIL_USERNAME')}>"

db.init_app(app)
mail = Mail(app)

# Cloudinary config
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', role='admin')
        admin.set_password('adminpass')
        db.session.add(admin)
        db.session.commit()

# ─── Points & Badge Logic ────────────────────────────────────────────────────

POINTS_FOR_REPORT = 10
POINTS_FOR_VOTE_RECEIVED = 2
POINTS_FOR_ISSUE_FIXED = 25

def update_badge(user):
    if user.points >= 100:
        user.badge = '🏅 City Hero'
    elif user.points >= 50:
        user.badge = '⭐ Active Citizen'
    elif user.points >= 20:
        user.badge = '🔍 Reporter'
    else:
        user.badge = '🌱 Newcomer'
    db.session.commit()

# ─── Email Helper ─────────────────────────────────────────────────────────────

def send_status_email(email, name, issue, old_status, new_status):
    status_colors = {
        'Reported': '#EF4444', 'Under Review': '#F59E0B',
        'In Progress': '#3B82F6', 'Fixed': '#10B981'
    }
    color = status_colors.get(new_status, '#6B7280')
    try:
        msg = Message(
            subject=f"CivicFix: Your issue '{issue.title}' status updated!",
            recipients=[email]
        )
        msg.html = f"""
        <div style="font-family:Inter,sans-serif;max-width:600px;margin:auto;padding:24px;background:#f9fafb;border-radius:12px;">
          <h2 style="color:#0F172A;">🛠️ CivicFix Update</h2>
          <p>Hi <b>{name}</b>, your reported issue has been updated!</p>
          <div style="background:white;border-radius:8px;padding:16px;margin:16px 0;border-left:4px solid {color};">
            <h3 style="margin:0">{issue.title}</h3>
            <p style="color:#6B7280;">{issue.location_text}</p>
            <p><b>Status changed:</b> {old_status} → <span style="color:{color};font-weight:bold;">{new_status}</span></p>
          </div>
          <p>Thank you for making your city better! 🏙️</p>
          <small style="color:#9CA3AF;">— The CivicFix Team</small>
        </div>
        """
        mail.send(msg)
    except Exception as e:
        print(f"[Mail Error] {e}")  # Don't break the flow if email fails

# ─── Context Processor ────────────────────────────────────────────────────────

@app.context_processor
def inject_global_stats():
    total = Issue.query.count()
    fixed = Issue.query.filter_by(status='Fixed').count()
    pending = Issue.query.filter(Issue.status.in_(['Reported', 'Under Review', 'In Progress'])).count()
    return dict(stats={'total_reported': total, 'fixed_issues': fixed, 'pending_issues': pending})

# ─── Auth Routes ─────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('index'))
        flash('Invalid credentials. Please try again.', 'error')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email', '').strip() or None
        role = request.form.get('role', 'citizen')

        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return redirect(url_for('register'))

        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# ─── Main Dashboard ───────────────────────────────────────────────────────────

@app.route('/')
def index():
    status_filter = request.args.get('status')
    category_filter = request.args.get('category')
    query = Issue.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if category_filter:
        query = query.filter_by(category=category_filter)
    issues = query.order_by(Issue.created_at.desc()).all()
    return render_template('index.html', issues=issues)

# ─── GPS Route ────────────────────────────────────────────────────────────────

@app.route('/reverse-geocode')
def reverse_geocode():
    lat = request.args.get('lat')
    lng = request.args.get('lng')
    if not lat or not lng:
        return jsonify({'error': 'Missing coordinates'}), 400
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json"
        headers = {"User-Agent": "CivicFix/1.0"}
        res = http_requests.get(url, headers=headers, timeout=5).json()
        address = res.get("display_name", f"{lat}, {lng}")
        return jsonify({'address': address})
    except Exception as e:
        return jsonify({'address': f'{lat}, {lng}'}), 200

# ─── Issue Routes ─────────────────────────────────────────────────────────────

@app.route('/report', methods=['GET', 'POST'])
def report_issue():
    if 'user_id' not in session:
        flash('Please log in to report an issue.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title')
        category = request.form.get('category')
        location_text = request.form.get('location_text')
        description = request.form.get('description')
        latitude = request.form.get('latitude') or None
        longitude = request.form.get('longitude') or None
        image_file = request.files.get('image')

        if not all([title, category, location_text, description]):
            flash('Missing required fields.', 'error')
            return redirect(url_for('report_issue'))

        image_url = None
        if image_file and image_file.filename != '':
            try:
                upload_result = cloudinary.uploader.upload(image_file)
                image_url = upload_result.get('secure_url')
            except Exception as e:
                flash(f'Image upload failed: {str(e)}', 'error')
                return redirect(url_for('report_issue'))

        issue = Issue(
            title=title, description=description, category=category,
            location_text=location_text, image_url=image_url,
            latitude=float(latitude) if latitude else None,
            longitude=float(longitude) if longitude else None,
            citizen_id=session['user_id']
        )
        db.session.add(issue)

        # Award points to reporter
        reporter = User.query.get(session['user_id'])
        reporter.points += POINTS_FOR_REPORT
        update_badge(reporter)

        db.session.commit()
        flash('Thank you! Your issue has been reported. +10 points earned!', 'success')
        return redirect(url_for('index'))

    return render_template('report.html')


@app.route('/my_issues')
def my_issues():
    if 'user_id' not in session:
        flash('Please log in to view your issues.', 'error')
        return redirect(url_for('login'))
    issues = Issue.query.filter_by(citizen_id=session['user_id']).order_by(Issue.created_at.desc()).all()
    return render_template('my_issues.html', issues=issues)


# ─── Vote Route ───────────────────────────────────────────────────────────────

@app.route('/issues/<int:issue_id>/vote', methods=['POST'])
def vote_issue(issue_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized. Please login.'}), 401

    user_id = session['user_id']
    issue = Issue.query.get(issue_id)
    if not issue:
        return jsonify({'error': 'Issue not found'}), 404

    existing_vote = Vote.query.filter_by(issue_id=issue_id, user_id=user_id).first()
    issue_owner = User.query.get(issue.citizen_id)

    if existing_vote:
        db.session.delete(existing_vote)
        # Remove vote points from issue owner
        if issue_owner and issue_owner.points >= POINTS_FOR_VOTE_RECEIVED:
            issue_owner.points -= POINTS_FOR_VOTE_RECEIVED
            update_badge(issue_owner)
        db.session.commit()
        return jsonify({'message': 'Vote removed', 'issue': issue.to_dict()}), 200

    new_vote = Vote(issue_id=issue_id, user_id=user_id)
    db.session.add(new_vote)
    # Award points to issue owner for receiving a vote
    if issue_owner:
        issue_owner.points += POINTS_FOR_VOTE_RECEIVED
        update_badge(issue_owner)
    db.session.commit()
    return jsonify({'message': 'Vote cast', 'issue': issue.to_dict()}), 201

# ─── Admin Routes ─────────────────────────────────────────────────────────────

@app.route('/admin')
def admin_panel():
    if session.get('role') != 'admin':
        flash('Access Denied. You must be an administrator.', 'error')
        return redirect(url_for('index'))
    issues = Issue.query.order_by(Issue.created_at.desc()).all()
    return render_template('admin.html', issues=issues)


@app.route('/admin/issue/<int:issue_id>/status', methods=['POST'])
def update_status(issue_id):
    if session.get('role') != 'admin':
        flash('Access Denied.', 'error')
        return redirect(url_for('index'))

    issue = Issue.query.get(issue_id)
    if not issue:
        flash('Issue not found.', 'error')
        return redirect(url_for('admin_panel'))

    old_status = issue.status
    new_status = request.form.get('status')

    if new_status in ['Reported', 'Under Review', 'In Progress', 'Fixed']:
        issue.status = new_status

        # Award extra points if issue marked Fixed
        if new_status == 'Fixed' and old_status != 'Fixed':
            reporter = User.query.get(issue.citizen_id)
            if reporter:
                reporter.points += POINTS_FOR_ISSUE_FIXED
                update_badge(reporter)

        db.session.commit()

        # Send email notification
        reporter = User.query.get(issue.citizen_id)
        if reporter and reporter.email:
            send_status_email(reporter.email, reporter.username, issue, old_status, new_status)

        flash(f'Issue #{issue.id} updated to "{new_status}".', 'success')

    return redirect(url_for('admin_panel'))


@app.route('/admin/analytics')
def analytics():
    if session.get('role') != 'admin':
        flash('Access Denied.', 'error')
        return redirect(url_for('index'))

    by_category = db.session.query(Issue.category, func.count(Issue.id)).group_by(Issue.category).all()
    by_status = db.session.query(Issue.status, func.count(Issue.id)).group_by(Issue.status).all()

    seven_days = []
    for i in range(6, -1, -1):
        day = datetime.utcnow() - timedelta(days=i)
        count = Issue.query.filter(func.date(Issue.created_at) == day.date()).count()
        seven_days.append({"date": day.strftime("%b %d"), "count": count})

    fixed_issues = Issue.query.filter_by(status='Fixed').all()
    avg_days = 0
    if fixed_issues:
        total_days = sum((datetime.utcnow() - i.created_at).days for i in fixed_issues)
        avg_days = round(total_days / len(fixed_issues), 1)

    # Top category
    top_category = max(by_category, key=lambda x: x[1])[0] if by_category else 'N/A'

    return render_template('analytics.html',
        by_category=by_category,
        by_status=by_status,
        seven_days=seven_days,
        avg_days=avg_days,
        total_issues=Issue.query.count(),
        fixed_count=len(fixed_issues),
        top_category=top_category
    )

# ─── Leaderboard ──────────────────────────────────────────────────────────────

@app.route('/leaderboard')
def leaderboard():
    top_users = User.query.filter_by(role='citizen').order_by(User.points.desc()).limit(10).all()
    total_citizens = User.query.filter_by(role='citizen').count()
    user_rank = None
    current_user_points = 0

    if session.get('user_id'):
        all_citizens = User.query.filter_by(role='citizen').order_by(User.points.desc()).all()
        for i, u in enumerate(all_citizens):
            if u.id == session['user_id']:
                user_rank = i + 1
                current_user_points = u.points
                break

    return render_template('leaderboard.html',
        top_users=top_users,
        user_rank=user_rank,
        total_citizens=total_citizens,
        current_user_points=current_user_points
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)
