from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
import os
from flask_migrate import Migrate
import uuid

app = Flask(__name__)
app.secret_key = 'supersecretkey'
login_manager = LoginManager()
login_manager.init_app(app)

# Store users and events in memory (for now)
users = {}
events_by_user = {}

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    if user_id in users:
        return User(id=user_id)
    return None

@app.route('/')
def home():
    return "Hello, World!"

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users:
            flash('Username already exists!')
        else:
            hashed_password = generate_password_hash(password)
            users[username] = {'password': hashed_password}
            events_by_user[username] = []  # Each user gets their own event list
            flash('Registration successful! You can now log in.')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and check_password_hash(users[username]['password'], password):
            user = User(id=username)
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    user_events = Event.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', events=user_events)


@app.route('/create_event', methods=['GET', 'POST'])
@login_required
def create_event():
    if request.method == 'POST':
        event_name = request.form['event_name']
        event_date = request.form['event_date']
        new_event = Event(name=event_name, date=event_date, user_id=current_user.id)
        db.session.add(new_event)
        db.session.commit()
        flash('Event created successfully!')
        return redirect(url_for('dashboard'))
    return render_template('create_event.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unique_id = db.Column(db.String(36), unique=True, default=str(uuid.uuid4()))  # New unique_id column
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    business_name = db.Column(db.String(120), nullable=False)
    website_url = db.Column(db.String(200), nullable=True)  # Optional
    vat_number = db.Column(db.String(50), nullable=True)    # Optional
    stripe_connect_id = db.Column(db.String(120), nullable=False)

    events = db.relationship('Event', backref='user', lazy=True)


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    start_time = db.Column(db.String(50), nullable=False)
    end_time = db.Column(db.String(50), nullable=False)
    ticket_quantity = db.Column(db.Integer, nullable=False)
    ticket_price = db.Column(db.Float, nullable=False)
    event_image = db.Column(db.String(300), nullable=True)  # Image URL

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)



@app.route('/init_db')

@app.route('/reset_db')
def reset_db():
    db.drop_all()  # This will drop all tables in the database
    db.create_all()  # This will create all tables with the new models
    return "Database reset and tables created!"