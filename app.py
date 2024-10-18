from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
import os
from flask_migrate import Migrate
import uuid
import string
import random
from werkzeug.security import generate_password_hash
from flask import request, redirect, url_for, flash, render_template


app = Flask(__name__)
app.secret_key = 'supersecretkey'
login_manager = LoginManager()
login_manager.init_app(app)

# Store users and events in memory (for now)
users = {}
events_by_user = {}

from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
    if user_id in users:
        return User(id=user_id)
    return None

@app.route('/')
def home():
    return "Hello, World!"



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Fetch the user by email
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password')
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    user_events = Event.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', events=user_events)



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

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    unique_id = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(120), unique=True, nullable=False)  # Using email as the unique login field
    password = db.Column(db.String(255), nullable=False)
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



# Function to generate a random unique ID with 15 characters
def generate_unique_id():
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(15))

@app.route('/register', methods=['GET', 'POST'])
def register():
    try:
        if request.method == 'POST':
            email = request.form['email']
            username = request.form['username']
            password = request.form['password']
            full_name = request.form['full_name']
            phone_number = request.form['phone_number']
            business_name = request.form['business_name']
            website_url = request.form.get('website_url')
            vat_number = request.form.get('vat_number')
            stripe_connect_id = request.form['stripe_connect_id']

            # Check if the email already exists
            user = User.query.filter_by(email=email).first()
            if user:
                return render_template('register.html', error="Email already in use, please contact us on 0330 043 6608")

            # Generate a unique ID for the user
            unique_id = generate_unique_id()

            # Hash the password for security
            hashed_password = generate_password_hash(password)

            # Create the new user
            new_user = User(
                unique_id=unique_id,
                username=username,
                email=email,
                password=hashed_password,
                full_name=full_name,
                phone_number=phone_number,
                business_name=business_name,
                website_url=website_url,
                vat_number=vat_number,
                stripe_connect_id=stripe_connect_id
            )

            # Add the new user to the database
            db.session.add(new_user)
            db.session.commit()

            flash('Account created successfully! Please log in.')
            return redirect(url_for('login'))

    except Exception as e:
        # Print the actual error to the logs
        print(f"Error during registration: {str(e)}")
        return f"An error occurred during registration: {str(e)}"

    return render_template('register.html')


@app.route('/create_event', methods=['GET', 'POST'])
@login_required
def create_event():
    if request.method == 'POST':
        name = request.form['name']
        date = request.form['date']
        location = request.form['location']
        description = request.form['description']
        start_time = request.form['start_time']
        end_time = request.form['end_time']
        ticket_quantity = request.form['ticket_quantity']
        ticket_price = request.form['ticket_price']
        event_image = request.form['event_image']

        # Create a new event, linked to the current logged-in user
        new_event = Event(
            name=name,
            date=date,
            location=location,
            description=description,
            start_time=start_time,
            end_time=end_time,
            ticket_quantity=ticket_quantity,
            ticket_price=ticket_price,
            event_image=event_image,
            user_id=current_user.id
        )

        # Add the new event to the database
        db.session.add(new_event)
        db.session.commit()

        flash('Event created successfully!')
        return redirect(url_for('dashboard'))

    return render_template('create_event.html')


if __name__ == "__main__":
    app.run(debug=True)


@app.route('/reset_db')
def reset_db():
    try:
        # Drop all tables and recreate them
        db.drop_all()  # This deletes all the tables
        db.create_all()  # This recreates the tables based on the models
        return "Database reset and tables recreated!"
    except Exception as e:
        return f"An error occurred during reset: {str(e)}"
