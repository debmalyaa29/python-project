import datetime
from database import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='citizen') # citizen, admin

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role
        }

class Issue(db.Model):
    __tablename__ = 'issues'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False) # Pothole, Manhole, Flooding, Other
    status = db.Column(db.String(50), nullable=False, default='Reported') # Reported, Under Review, In Progress, Fixed
    image_url = db.Column(db.String(255), nullable=True)
    location_text = db.Column(db.String(255), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    citizen_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    citizen = db.relationship('User', backref=db.backref('issues', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'status': self.status,
            'image_url': self.image_url,
            'location_text': self.location_text,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'created_at': self.created_at.isoformat(),
            'citizen_id': self.citizen_id,
            'citizen_username': self.citizen.username if self.citizen else None,
            'votes': Vote.query.filter_by(issue_id=self.id).count()
        }

class Vote(db.Model):
    __tablename__ = 'votes'
    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey('issues.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    issue = db.relationship('Issue', backref=db.backref('vote_records', lazy=True, cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('vote_records', lazy=True, cascade='all, delete-orphan'))
