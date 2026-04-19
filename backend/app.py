import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
from flask_cors import CORS
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

from database import db
from models import User, Issue, Vote

load_dotenv()

app = Flask(__name__)
CORS(app)
app.secret_key = os.urandom(24) # Required for flash messages and secure sessions

# Database config
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'civicfix.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Cloudinary config
cloudinary.config(
  cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME'),
  api_key = os.getenv('CLOUDINARY_API_KEY'),
  api_secret = os.getenv('CLOUDINARY_API_SECRET')
)

with app.app_context():
    db.create_all()

    # Ensure admin user
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', role='admin')
        admin.set_password('adminpass')
        db.session.add(admin)
        db.session.commit()

# --- Context Processors ---
@app.context_processor
def inject_global_stats():
    total = Issue.query.count()
    fixed = Issue.query.filter_by(status='Fixed').count()
    pending = Issue.query.filter(Issue.status.in_(['Reported', 'Under Review', 'In Progress'])).count()
    stats = {
        'total_reported': total,
        'fixed_issues': fixed,
        'pending_issues': pending
    }
    return dict(stats=stats)

# --- Routes ---

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
    
    # We pass the objects directly
    return render_template('index.html', issues=issues)


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
        role = request.form.get('role', 'citizen')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return redirect(url_for('register'))
            
        user = User(username=username, role=role)
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
            title=title,
            description=description,
            category=category,
            location_text=location_text,
            image_url=image_url,
            citizen_id=session['user_id']
        )
        db.session.add(issue)
        db.session.commit()
        
        flash('Thank you! Your issue has been successfully reported.', 'success')
        return redirect(url_for('index'))
        
    return render_template('report.html')


@app.route('/my_issues')
def my_issues():
    if 'user_id' not in session:
        flash('Please log in to view your issues.', 'error')
        return redirect(url_for('login'))
        
    issues = Issue.query.filter_by(citizen_id=session['user_id']).order_by(Issue.created_at.desc()).all()
    return render_template('my_issues.html', issues=issues)


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
        
    new_status = request.form.get('status')
    if new_status in ['Reported', 'Under Review', 'In Progress', 'Fixed']:
        issue.status = new_status
        db.session.commit()
        flash(f'Issue {issue.id} status updated to {new_status}.', 'success')
        
    return redirect(url_for('admin_panel'))


# Asynchronous API Route for Voting
@app.route('/issues/<int:issue_id>/vote', methods=['POST'])
def vote_issue(issue_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized. Please login.'}), 401
        
    user_id = session['user_id']
    issue = Issue.query.get(issue_id)
    
    if not issue:
        return jsonify({'error': 'Issue not found'}), 404
        
    existing_vote = Vote.query.filter_by(issue_id=issue_id, user_id=user_id).first()
    
    if existing_vote:
        db.session.delete(existing_vote)
        db.session.commit()
        return jsonify({'message': 'Vote removed', 'issue': issue.to_dict()}), 200
        
    new_vote = Vote(issue_id=issue_id, user_id=user_id)
    db.session.add(new_vote)
    db.session.commit()
    
    return jsonify({'message': 'Vote cast', 'issue': issue.to_dict()}), 201

if __name__ == '__main__':
    app.run(debug=True, port=5000)
