from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
import os
from flask_migrate import Migrate
import uuid
import string
import random
import stripe
from flask_cors import CORS
import json
from flask import request, redirect, url_for, render_template, flash
from urllib.parse import urlparse
from datetime import datetime, timezone
import json
import pandas as pd
from io import BytesIO
from flask import make_response
import re
from uuid import uuid4
from apscheduler.schedulers.background import BackgroundScheduler
import math
from flask_mail import Mail, Message
import urllib.parse
from flask import Response
from markupsafe import escape
from markupsafe import Markup
from itsdangerous import URLSafeTimedSerializer
from flask import current_app
from dotenv import load_dotenv
import qrcode
from io import BytesIO
from flask import send_file
from PIL import Image
import base64
from sqlalchemy import func
from requests.auth import HTTPBasicAuth
import requests
from werkzeug.utils import secure_filename
import boto3
from botocore.exceptions import NoCredentialsError
from werkzeug.utils import send_from_directory
from sqlalchemy.sql import text


load_dotenv()

app = Flask(__name__)

# Enable CORS for all routes and origins
CORS(app)  # This will allow all origins by default, but you can restrict it if needed.

# Load environment variables for S3 configuration
S3_BUCKET_NAME = os.getenv('AWS_S3_BUCKET_NAME')
S3_REGION = os.getenv('AWS_REGION')

# Initialize the S3 client
s3 = boto3.client(
    's3',
    region_name=S3_REGION,
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)

# Set your Stripe secret key from the environment variable
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

app.secret_key = 'supersecretkey'
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Add this line to specify
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

# Update the database URL configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

print("Database URI:", app.config['SQLALCHEMY_DATABASE_URI'])

# Configuration for Flask-Mail
app.config['MAIL_SERVER'] = 'mail.ticketrush.io'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')  # Your email here (from Render)
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')  # Your password here (from Render)
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')  # Default sender email
# Configure upload limits and paths
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024  # 5 MB limit
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
# Set the upload folder in the configuration
# Load environment variables for WordPress credentials
WORDPRESS_API_URL = 'https://ticketrush.io/wp-json/wp/v2/media'
WORDPRESS_USER = os.getenv('WP-USER')
WORDPRESS_PASSWORD = os.getenv('WP-PASSWORD')

mail = Mail(app)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    unique_id = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    business_name = db.Column(db.String(120), nullable=False)
    website_url = db.Column(db.String(200), nullable=True)  # Optional
    vat_number = db.Column(db.String(50), nullable=True)  # Optional
    stripe_connect_id = db.Column(db.String(120), nullable=True)
    onboarding_status = db.Column(db.String(20), default="pending")  # Onboarding status
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # Add created_at timestamp
    first_login = db.Column(db.String(1), nullable=True)
    business_logo_url = db.Column(db.String(255), nullable=True)

    # Address fields
    house_name_or_number = db.Column(db.String(255), nullable=False)
    street = db.Column(db.String(255), nullable=False)
    locality = db.Column(db.String(255), nullable=True)
    town = db.Column(db.String(100), nullable=False)
    postcode = db.Column(db.String(20), nullable=False)

    terms = db.Column(db.String(255), nullable=True)  # Changed from False to True

    # Default flat_rate set to 0.01
    flat_rate = db.Column(db.Float, nullable=True, default=0.01)  # Flat rate with default value

    # Optional promotional fields
    promo_rate = db.Column(db.Float, nullable=True)  # Promotional rate
    promo_rate_date_end = db.Column(db.Date, nullable=True)
    is_admin = db.Column(db.Boolean, default=False)

    events = db.relationship('Event', backref='user', lazy=True)
    

    # Token generation for password reset
    def get_reset_token(self, expires_sec=3600):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return s.dumps(self.id, salt='password-reset-salt')

    # Token verification for password reset
    @staticmethod
    def verify_reset_token(token, expires_sec=3600):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token, salt='password-reset-salt', max_age=expires_sec)
        except:
            return None
        return User.query.get(user_id)

# Event model
class Event(db.Model):
    __tablename__ = 'event'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    start_time = db.Column(db.String(50), nullable=False)
    end_time = db.Column(db.String(50), nullable=False)
    
    
    # Custom questions
    custom_question_1 = db.Column(db.String(255), nullable=True)
    custom_question_2 = db.Column(db.String(255), nullable=True)
    custom_question_3 = db.Column(db.String(255), nullable=True)
    custom_question_4 = db.Column(db.String(255), nullable=True)
    custom_question_5 = db.Column(db.String(255), nullable=True)
    custom_question_6 = db.Column(db.String(255), nullable=True)
    custom_question_7 = db.Column(db.String(255), nullable=True)
    custom_question_8 = db.Column(db.String(255), nullable=True)
    custom_question_9 = db.Column(db.String(255), nullable=True)
    custom_question_10 = db.Column(db.String(255), nullable=True)


    # Foreign key relationship to User
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationship to TicketType
    ticket_types = db.relationship('TicketType', back_populates='event', cascade='all, delete-orphan')
    ticket_quantity = db.Column(db.Integer, nullable=True)  # Total event capacity
    enforce_individual_ticket_limits = db.Column(db.Boolean, default=True)
    image_url = db.Column(db.String(255), nullable=True)  # To store the image file path
    discount_rules = db.relationship('DiscountRule', backref='event', lazy=True)

class Attendee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(255), nullable=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id', ondelete='CASCADE'), nullable=False)
    ticket_answers = db.Column(db.Text, nullable=False)
    billing_details = db.Column(db.Text, nullable=True)
    stripe_charge_id = db.Column(db.String(255), nullable=True)
    payment_status = db.Column(db.String(50), nullable=False, default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    full_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    phone_number = db.Column(db.String(50), nullable=False)
    tickets_purchased = db.Column(db.Integer, nullable=False)
    ticket_price_at_purchase = db.Column(db.Float, nullable=False)
    ticket_number = db.Column(db.String(20), unique=True, nullable=True)  # New ticket_number column
    qr_image_path = db.Column(db.String(255), nullable=True)
    checked_in = db.Column(db.Boolean, default=False)
    check_in_time = db.Column(db.DateTime)

    ticket_type_id = db.Column(db.Integer, db.ForeignKey('ticket_type.id'), nullable=False)
    
    # Relationship to TicketType
    ticket_type = db.relationship('TicketType', backref=db.backref('attendees', lazy=True))
    
    # Relationship to the Event model
    event = db.relationship('Event', backref=db.backref('attendees', passive_deletes=True))

    @property
    def ticket_answers_dict(self):
        if not hasattr(self, '_ticket_answers_dict'):
            if self.ticket_answers:
                try:
                    self._ticket_answers_dict = json.loads(self.ticket_answers)
                except json.JSONDecodeError:
                    self._ticket_answers_dict = {}
            else:
                self._ticket_answers_dict = {}
        return self._ticket_answers_dict

    @property
    def billing_details_dict(self):
        if not hasattr(self, '_billing_details_dict'):
            if self.billing_details:
                try:
                    self._billing_details_dict = json.loads(self.billing_details)
                except json.JSONDecodeError:
                    self._billing_details_dict = {}
            else:
                self._billing_details_dict = {}
        return self._billing_details_dict


class DefaultQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question = db.Column(db.String(255), nullable=False)

class TicketType(db.Model):
    __tablename__ = 'ticket_type'
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=True)  # Allowing NULLs now

    # Relationship back to Event
    event = db.relationship('Event', back_populates='ticket_types')

# Add this with your other models
class DiscountRule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    discount_type = db.Column(db.String(20), nullable=False)  # 'bulk', 'early_bird', 'promo_code'
    discount_percent = db.Column(db.Float, nullable=False)
    
    # Bulk purchase fields
    min_tickets = db.Column(db.Integer)
    apply_to = db.Column(db.String(20))  # 'all' or 'additional'
    
    # Early bird fields
    valid_until = db.Column(db.DateTime)
    max_early_bird_tickets = db.Column(db.Integer)
    
    # Promo code fields
    promo_code = db.Column(db.String(50))
    max_uses = db.Column(db.Integer)
    uses_count = db.Column(db.Integer, default=0)
    
    def calculate_discount(self, quantity, original_price, promo_code=None):
        """
        Calculate the discount amount based on the rule type and conditions.
        
        Args:
            quantity (int): Number of tickets being purchased
            original_price (float): Original price per ticket
            promo_code (str, optional): Promo code provided by customer
            
        Returns:
            float: Discount amount to be applied
        """
        if self.discount_type == 'bulk' and quantity >= self.min_tickets:
            if self.apply_to == 'all':
                return (original_price * quantity) * (self.discount_percent / 100)
            else:  # 'additional'
                return (original_price * (quantity - 1)) * (self.discount_percent / 100)
                
        elif self.discount_type == 'early_bird' and datetime.utcnow() < self.valid_until:
            if not self.max_early_bird_tickets or self.max_early_bird_tickets >= quantity:
                return (original_price * quantity) * (self.discount_percent / 100)
            
        elif (self.discount_type == 'promo_code' and 
              promo_code == self.promo_code and 
              (not self.max_uses or self.uses_count < self.max_uses)):
            return (original_price * quantity) * (self.discount_percent / 100)
        
        return 0

# Generate a random unique ID with 15 characters
def generate_unique_id():
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(15))

# User Loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return redirect(url_for('login'))

from datetime import datetime, timedelta

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Find the user by email
        user = User.query.filter_by(email=email).first()

        if user:
            # Check if the provided password is correct
            if check_password_hash(user.password, password):
                # Check if the user has completed Stripe onboarding
                if user.onboarding_status == "complete":
                    # Check if this is the user's first login
                    if user.first_login == "N":
                        user.first_login = "Y"  # Update to indicate first login completed
                        db.session.commit()
                        # Flash the welcome message with links, using Markup to render HTML
                        flash(
                            Markup(
                                "Welcome to TicketRush! 🎉 <br> "
                                "We're excited to have you here! It looks like it's your first time logging in, so we recommend starting with our "
                                "<a href='https://ticketrush.io/tutorials' target='_blank'>First-Time User Guide</a> "
                                "to get the most out of TicketRush. <br><br>"
                                "Before creating your first event, take a moment to personalise your "
                                "<a href='https://bookings.ticketrush.io/manage-default-questions'>Account Settings</a> so your events are customised just the way you like. <br><br>"
                            ),
                            "success"
                        )

                    # Log the user in
                    login_user(user)
                    flash('Logged in successfully!', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    # Show message if onboarding is incomplete
                    flash('It looks like you have recently attempted to register but not completed the Stripe setup. Please complete the process before logging in.', 'warning')
                    return render_template('login.html')  # Stay on the login page
            else:
                flash('Invalid email or password', 'danger')
        else:
            flash('Email not found. Please register first.', 'warning')

    return render_template('login.html')



@app.route('/dashboard')
@login_required
def dashboard():
    filter_value = request.args.get('filter', 'upcoming')  # Set 'upcoming' as the default filter
    user_events = Event.query.filter_by(user_id=current_user.id).all()

    # Helper function to convert string dates to datetime for comparison
    def str_to_date(date_str):
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')  # Adjust the format if your date strings differ
        except ValueError:
            return None

    # Filter and sort events based on the filter value
    if filter_value == 'upcoming':
        user_events = [event for event in user_events if str_to_date(event.date) and str_to_date(event.date) >= datetime.now()]
    elif filter_value == 'past':
        user_events = [event for event in user_events if str_to_date(event.date) and str_to_date(event.date) < datetime.now()]

    # Sort events by date
    user_events.sort(key=lambda event: str_to_date(event.date) or datetime.max)

    total_tickets_sold = 0
    total_revenue = 0

    event_data = []
    for event in user_events:
        # Calculate total tickets sold and revenue for the event
        succeeded_attendees = Attendee.query.filter_by(event_id=event.id, payment_status='succeeded').all()
        tickets_sold = len(succeeded_attendees)

        # Adjust total ticket quantity calculation based on enforcement setting
        if event.enforce_individual_ticket_limits:
            total_ticket_quantity = sum([ticket_type.quantity or 0 for ticket_type in event.ticket_types])
        else:
            total_ticket_quantity = event.ticket_quantity or 0

        # Calculate tickets sold and remaining per ticket type
        ticket_breakdown = []
        for ticket_type in event.ticket_types:
            # Count the number of attendees for this ticket type
            tickets_sold_type = Attendee.query.filter_by(
                event_id=event.id,
                ticket_type_id=ticket_type.id,
                payment_status='succeeded'
            ).count()
            if event.enforce_individual_ticket_limits:
                tickets_remaining_type = (ticket_type.quantity or 0) - tickets_sold_type
                total_quantity = ticket_type.quantity
            else:
                # When individual limits are not enforced, total_quantity is the event's total capacity
                tickets_remaining_type = (total_ticket_quantity or 0) - tickets_sold
                total_quantity = total_ticket_quantity

            ticket_breakdown.append({
                'name': ticket_type.name,
                'price': ticket_type.price,
                'tickets_sold': tickets_sold_type,
                'tickets_remaining': tickets_remaining_type,
                'total_quantity': total_quantity
            })

        # Calculate overall tickets remaining
        tickets_remaining = total_ticket_quantity - tickets_sold

        # Calculate total revenue for the event
        event_revenue = sum([attendee.ticket_price_at_purchase for attendee in succeeded_attendees])

        total_tickets_sold += tickets_sold
        total_revenue += event_revenue

        event_date = str_to_date(event.date) if event.date else None
        event_status = "Upcoming" if event_date and event_date >= datetime.now() else "Past"

        # Add discount rules
        discount_rules = DiscountRule.query.filter_by(event_id=event.id).all()
        discount_rules_data = [{
            'discount_type': rule.discount_type,
            'discount_percent': rule.discount_percent,
            'min_tickets': rule.min_tickets if rule.discount_type == 'bulk' else None,
            'apply_to': rule.apply_to if rule.discount_type == 'bulk' else None,
            'valid_until': rule.valid_until if rule.discount_type == 'early_bird' else None,
            'max_tickets': rule.max_early_bird_tickets if rule.discount_type == 'early_bird' else None,
            'code': rule.promo_code if rule.discount_type == 'promo_code' else None,
            'max_uses': rule.max_uses if rule.discount_type == 'promo_code' else None,
            'uses_left': rule.max_uses - rule.uses_count if rule.discount_type == 'promo_code' else None
        } for rule in discount_rules]

        event_data.append({
            'name': event.name,
            'date': event.date,
            'location': event.location,
            'description': event.description,
            'start_time': event.start_time,  # Already a string, no need for strftime
            'end_time': event.end_time,      # Already a string, no need for strftime
            'tickets_sold': tickets_sold,
            'ticket_quantity': total_ticket_quantity,
            'tickets_remaining': tickets_remaining,
            'total_revenue': event_revenue,
            'status': event_status,
            'id': event.id,
            'ticket_breakdown': ticket_breakdown,
            'enforce_individual_ticket_limits': event.enforce_individual_ticket_limits,
            'discount_rules': discount_rules_data
        })

    return render_template('dashboard.html', 
                           events=event_data, 
                           total_revenue=total_revenue, 
                           total_tickets_sold=total_tickets_sold, 
                           user=current_user)



@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    try:
        if request.method == 'POST':
            # Collect user data from the form
            email = request.form['email']
            password = request.form['password']
            first_name = request.form['first_name']
            last_name = request.form['last_name']
            phone_number = request.form['phone_number']
            business_name = request.form['business_name']
            website_url = request.form.get('website_url', '')  # Optional
            vat_number = request.form.get('vat_number', '')  # Optional
            house_name_or_number = request.form['house_name_or_number']
            street = request.form['street']
            locality = request.form.get('locality', '')  # Optional
            town = request.form['town']
            postcode = request.form['postcode']

            # Check if user already exists with the same email
            existing_user = User.query.filter_by(email=email).first()

            if existing_user:
                if existing_user.onboarding_status == "pending":
                    # If a pending user is found, delete their old entry
                    db.session.delete(existing_user)
                    db.session.commit()
                    flash('Previous registration found with incomplete onboarding. Re-registering...', 'info')
                else:
                    # If the user exists and completed onboarding, don't allow re-registration
                    return render_template('register.html', error="Email already in use and completed onboarding.")
            
            # If no user or the old pending user has been deleted, proceed with creating a new one
            unique_id = generate_unique_id()
            hashed_password = generate_password_hash(password)

            new_user = User(
                unique_id=unique_id,
                email=email,
                password=hashed_password,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                business_name=business_name,
                website_url=website_url,
                vat_number=vat_number,
                house_name_or_number=house_name_or_number,
                street=street,
                locality=locality,
                town=town,
                postcode=postcode,
                stripe_connect_id=None,
                onboarding_status="pending",
                created_at=datetime.now(timezone.utc),
                first_login="N"  # Set first_login to "N" upon registration
            )

            db.session.add(new_user)
            db.session.commit()

            # Create the user's Stripe Connect account
            stripe_account = stripe.Account.create(
                type="standard",
                country="GB",
                email=email,
            )

            # Create the Account Link for onboarding
            account_link = stripe.AccountLink.create(
                account=stripe_account.id,
                refresh_url=url_for('stripe_onboarding_refresh', _external=True),
                return_url=url_for('stripe_onboarding_complete', account=stripe_account.id, user_id=new_user.id, _external=True),
                type='account_onboarding',
            )

            # Redirect the user to complete Stripe onboarding
            return redirect(account_link.url)

    except Exception as e:
        print(f"Error during registration: {str(e)}")
        return render_template('register.html', error="An error occurred during registration.")

    return render_template('register.html')




def get_next_date(current_date, pattern):
                if pattern == 'daily':
                    return current_date + timedelta(days=1)
                elif pattern == 'weekly':
                    return current_date + timedelta(weeks=1)
                elif pattern == 'monthly':
                    # Properly handle month increments, accounting for year changes and varying month lengths
                    month = current_date.month
                    year = current_date.year
                    if month == 12:
                        month = 1
                        year += 1
                    else:
                        month += 1
                    # Handle day overflow (e.g., February 30th)
                    day = min(current_date.day, [31,
                        29 if (year % 4 == 0 and not year % 100 == 0) or (year % 400 == 0) else 28,
                        31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month-1])
                    return datetime(year, month, day)
                return current_date  # No recurrence



@app.route('/create_event', methods=['GET', 'POST'])
@login_required
def create_event():
    if request.method == 'POST':
        try:
            # ------------------------------
            # 1. Collect and Validate Form Data
            # ------------------------------
            
            # Basic event details
            name = request.form.get('name', '').strip()
            date_str = request.form.get('date', '').strip()
            start_time = request.form.get('start_time', '').strip()
            end_time = request.form.get('end_time', '').strip()
            location = request.form.get('location', '').strip()
            description = request.form.get('description', '').strip()

            # Validate basic event details
            if not all([name, date_str, start_time, end_time, location, description]):
                flash('Please fill in all required fields for the event.', 'danger')
                return redirect(url_for('create_event'))

            # Validate event date
            try:
                event_date = datetime.strptime(date_str, '%Y-%m-%d')
                today = datetime.now().date()
                
                if event_date.date() < today:
                    flash('Event date cannot be in the past.', 'danger')
                    return redirect(url_for('create_event'))
            except ValueError:
                flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
                return redirect(url_for('create_event'))

            # Validate event times
            try:
                start_datetime = datetime.strptime(start_time, '%H:%M')
                end_datetime = datetime.strptime(end_time, '%H:%M')
                
                if end_datetime <= start_datetime:
                    flash('End time must be after start time.', 'danger')
                    return redirect(url_for('create_event'))

                # If event is today, check if start time hasn't already passed
                if event_date.date() == today:
                    current_time = datetime.now().time()
                    if start_datetime.time() < current_time:
                        flash('For events today, start time must be in the future.', 'danger')
                        return redirect(url_for('create_event'))

            except ValueError:
                flash('Invalid time format. Please use HH:MM.', 'danger')
                return redirect(url_for('create_event'))

            # Handle recurrence details
            recurrence = request.form.get('recurrence', 'none')  # Default to 'none'
            occurrences_str = request.form.get('occurrences', '1')  # Get as string

            # Handle recurrence details
            recurrence = request.form.get('recurrence', 'none')  # Default to 'none'
            occurrences_str = request.form.get('occurrences', '1')  # Get as string

            if recurrence != 'none':
                try:
                    occurrences = int(occurrences_str)
                    if occurrences < 1:
                        flash('Number of occurrences must be at least 1.', 'danger')
                        return redirect(url_for('create_event'))
                    elif occurrences > 100:
                        flash('Number of occurrences cannot exceed 100.', 'danger')
                        return redirect(url_for('create_event'))
                except ValueError:
                    flash('Invalid number of occurrences. Please enter a valid integer.', 'danger')
                    return redirect(url_for('create_event'))
            else:
                occurrences = 1  # Default to 1 if no recurrence

            # Enforce individual ticket limits
            enforce_limits = request.form.get('enforce_individual_ticket_limits') == 'on'  # Changed this line
            total_capacity = None  # Default to None
            if not enforce_limits:
                # Only check total capacity if using event capacity strategy
                total_capacity_str = request.form.get('total_ticket_quantity', '').strip()
                if total_capacity_str:
                    try:
                        total_capacity = int(total_capacity_str)
                        if total_capacity < 1:
                            flash('Total ticket quantity must be a positive integer.', 'danger')
                            return redirect(url_for('create_event'))
                    except ValueError:
                        flash('Invalid total capacity value.', 'danger')
                        return redirect(url_for('create_event'))
                else:
                    flash('Total capacity is required when not using individual limits.', 'danger')
                    return redirect(url_for('create_event'))

            print(f"Enforce limits: {enforce_limits}")  # Debug print
            print(f"Total capacity: {total_capacity}")  # Debug print

            # Process ticket types
            ticket_names = request.form.getlist('ticket_name[]')
            ticket_prices = request.form.getlist('ticket_price[]')
            ticket_quantities = request.form.getlist('ticket_quantity[]')

            # Debug prints
            print(f"Ticket names received: {ticket_names}")
            print(f"Ticket prices received: {ticket_prices}")
            print(f"Ticket quantities received: {ticket_quantities}")

            # Ensure at least one ticket type is provided
            if not ticket_names or not any(ticket_names):
                flash('Please provide at least one ticket type.', 'danger')
                return redirect(url_for('create_event'))
        


            # Capture custom questions for the event
            custom_questions = []
            for i in range(1, 11):
                question = request.form.get(f'custom_question_{i}')
                if question and question.strip():  # Only add non-empty questions
                    custom_questions.append(question.strip())

            print(f"Captured custom questions: {custom_questions}")  # Debug print

            # Fetch default questions from the database
            default_questions = DefaultQuestion.query.filter_by(user_id=current_user.id).all()
            default_question_texts = [dq.question for dq in default_questions]

            # ------------------------------
            # 2. Define Date Increment Based on Recurrence
            # ------------------------------
            
            

            # ------------------------------
            # 3. Handle Image Upload
            # ------------------------------
            

            image_url = None
            event_image = request.files.get('event_image')
            if event_image and event_image.filename != '':
                image_url = upload_to_s3(event_image, "event-logos")  # Specify the folder prefix here
                if not image_url:
                    flash("Failed to upload event image to S3", "danger")
                    return redirect(url_for('create_event'))

            # ------------------------------
            # 4. Create Each Event Occurrence
            # ------------------------------
            
            current_date = event_date  # This is already a datetime object from your validation
            for i in range(occurrences):
                # Create event instance with custom and default questions
                event = Event(
                    user_id=current_user.id,
                    name=name,
                    date=current_date.strftime('%Y-%m-%d'),  # Store as string
                    start_time=start_time,
                    end_time=end_time,
                    location=location,
                    description=description,
                    image_url=image_url,
                    enforce_individual_ticket_limits=enforce_limits,
                    ticket_quantity=total_capacity,
                    custom_question_1=custom_questions[0] if len(custom_questions) > 0 else None,
                    custom_question_2=custom_questions[1] if len(custom_questions) > 1 else None,
                    custom_question_3=custom_questions[2] if len(custom_questions) > 2 else None,
                    custom_question_4=custom_questions[3] if len(custom_questions) > 3 else None,
                    custom_question_5=custom_questions[4] if len(custom_questions) > 4 else None,
                    custom_question_6=custom_questions[5] if len(custom_questions) > 5 else None,
                    custom_question_7=custom_questions[6] if len(custom_questions) > 6 else None,
                    custom_question_8=custom_questions[7] if len(custom_questions) > 7 else None,
                    custom_question_9=custom_questions[8] if len(custom_questions) > 8 else None,
                    custom_question_10=custom_questions[9] if len(custom_questions) > 9 else None
                    )
                

                # Add custom questions to event
                # ... (custom questions code) ...

                db.session.add(event)
                db.session.flush()  # Get the event ID

                # Add ticket types for this event
                for t_name, t_price, t_quantity in zip(ticket_names, ticket_prices, ticket_quantities):
                    if t_name and t_price:
                        try:
                            quantity = None
                            if enforce_limits:
                                quantity = int(t_quantity) if t_quantity else None
                            
                            print(f"Creating ticket type: {t_name} - £{t_price} - Qty: {quantity}")  # Debug print

                            ticket_type = TicketType(
                                event_id=event.id,
                                name=t_name.strip(),
                                price=float(t_price),
                                quantity=quantity
                            )
                            db.session.add(ticket_type)
                        except ValueError as e:
                            print(f"Error creating ticket type: {str(e)}")  # Debug print
                            flash('Invalid ticket price or quantity.', 'danger')
                            db.session.rollback()
                            return redirect(url_for('create_event'))
                # Process discount rules
                print("\n=== Starting Discount Rules Processing ===")
                discount_types = request.form.getlist('discount_types[]')
                print(f"Found discount types: {discount_types}")

                for i, discount_type in enumerate(discount_types):
                    try:
                        # Create base discount rule
                        discount_rule = DiscountRule(
                            event_id=event.id,
                            discount_type=discount_type
                        )

                        # Handle specific discount type fields
                        if discount_type == 'promo_code':
                            discount_rule.promo_code = request.form.getlist('promo_code[]')[i]
                            discount_rule.discount_percent = float(request.form.getlist('promo_discount[]')[i])
                            discount_rule.max_uses = int(request.form.getlist('max_uses[]')[i])
                            discount_rule.uses_count = 0
                            print(f"Added promo code rule: {discount_rule.promo_code}, {discount_rule.discount_percent}%")

                        elif discount_type == 'early_bird':
                            discount_rule.discount_percent = float(request.form.getlist('early_bird_discount_percent[]')[i])
                            valid_until = request.form.getlist('valid_until[]')[i]
                            discount_rule.valid_until = datetime.strptime(valid_until, '%Y-%m-%dT%H:%M')
                            discount_rule.max_early_bird_tickets = int(request.form.getlist('max_early_bird_tickets[]')[i])
                            print(f"Added early bird rule: {discount_rule.discount_percent}%, valid until {discount_rule.valid_until}")

                        elif discount_type == 'bulk':
                            discount_rule.discount_percent = float(request.form.getlist('discount_percent[]')[i])
                            discount_rule.min_tickets = int(request.form.getlist('min_tickets[]')[i])
                            discount_rule.apply_to = request.form.getlist('apply_to[]')[i]
                            print(f"Added bulk discount rule: {discount_rule.discount_percent}%, min tickets: {discount_rule.min_tickets}")

                        # Add the rule to the session
                        db.session.add(discount_rule)
                        print(f"Added discount rule to session: {discount_rule.__dict__}")

                    except (ValueError, IndexError) as e:
                        print(f"Error processing discount rule: {str(e)}")
                        continue

                # Commit all changes
                print("\nCommitting all changes to database...")
                db.session.commit()
                print("Successfully committed changes!")
                print("=== Finished Discount Rules Processing ===\n")

                # Update current_date for next recurrence
                if i < occurrences - 1:
                    current_date = get_next_date(current_date, recurrence)

            flash(f'Event "{name}" created successfully!', 'success')
            return redirect(url_for('dashboard'))

        except Exception as e:
            print(f"\nCRITICAL ERROR in create_event:")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print("Full form data:")
            for key in request.form:
                print(f"- {key}: {request.form.getlist(key)}")
            
            db.session.rollback()
            flash('An unexpected error occurred while creating the event. Please try again.', 'danger')
            return redirect(url_for('create_event'))

    # Fetch and pass default questions for display in form
    default_questions = DefaultQuestion.query.filter_by(user_id=current_user.id).all()
    return render_template('create_event.html', default_questions=default_questions)




"""

@app.route('/reset_db')
def reset_db():
    try:
        db.drop_all()
        db.create_all()
        return "Database reset and tables recreated!"
    except Exception as e:
        return f"An error occurred during reset: {str(e)}"

"""
from markupsafe import escape

from datetime import datetime

@app.route('/embed/<unique_id>')
def embed_events(unique_id):
    try:
        # Find the user
        user = User.query.filter_by(unique_id=unique_id).first()
        if not user:
            print(f"User not found for unique_id: {unique_id}")
            return "document.write(`<div id='ticketrush-embed'><p>User not found</p></div>`);"

        # Get user events
        user_events = Event.query.filter_by(user_id=user.id).all()
        if not user_events:
            print(f"No events found for user: {user.id}")
            return "document.write(`<div id='ticketrush-embed'><p>No upcoming events available.</p></div>`);"

        # Filter future events with proper error handling
        future_events = []
        current_date = datetime.now().date()
        
        def parse_date(date_str):
            """Try multiple date formats to parse the date string"""
            formats = [
                '%Y-%m-%d',  # 2024-01-10
                '%y-%m-%d',  # 24-01-10
                '%d-%m-%y',  # 10-01-24
                '%d-%m-%Y',  # 10-01-2024
                '%Y/%m/%d',  # 2024/01/10
                '%d/%m/%Y',  # 10/01/2024
                '%m-%d-%y',  # 01-10-24
                '%m-%d-%Y'   # 01-10-2024
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
            
            # If no format matches, raise an error
            raise ValueError(f"Unable to parse date: {date_str}")

        for event in user_events:
            try:
                # Try to parse the date with our helper function
                event_date = parse_date(event.date)
                if event_date >= current_date:
                    # Store the parsed date for later use
                    event.parsed_date = event_date
                    future_events.append(event)
            except (ValueError, TypeError) as e:
                print(f"Error parsing date for event {event.id}: {e}")
                continue

        # Sort events by parsed date
        future_events.sort(key=lambda x: getattr(x, 'parsed_date', datetime.max.date()))

        # Begin constructing the HTML with modern styling
        events_html = '''
        <style>
            #ticketrush-embed * {
                box-sizing: border-box;
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                margin: 0;
                padding: 0;
            }
            
            #ticketrush-embed {
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 20px;
            }
            
            .event-card {
                background: white;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                overflow: hidden;
                transition: transform 0.2s, box-shadow 0.2s;
                height: 100%;
                display: flex;
                flex-direction: column;
            }
            
            .event-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 8px 12px rgba(0, 0, 0, 0.15);
            }
            
            .event-image {
                width: 100%;
                height: 160px;
                background-size: cover;
                background-position: center;
                background-color: #f5f5f5;
            }
            
            .event-content {
                padding: 20px;
                flex-grow: 1;
                display: flex;
                flex-direction: column;
            }
            
            .event-title {
                font-size: 1.25rem;
                font-weight: 600;
                color: #1a1a1a;
                margin-bottom: 12px;
                line-height: 1.4;
            }
            
            .event-details {
                color: #4a5568;
                font-size: 0.95rem;
                line-height: 1.6;
                margin-bottom: 20px;
            }
            
            .event-meta {
                display: flex;
                align-items: center;
                gap: 8px;
                margin-bottom: 8px;
                color: #666;
                font-size: 0.9rem;
            }
            
            .event-meta i {
                color: #ff0000;
                width: 16px;
            }
            
            .price-tag {
                background: #fff8f8;
                color: #ff0000;
                padding: 4px 12px;
                border-radius: 20px;
                font-weight: 500;
                display: inline-block;
                margin-top: 8px;
            }
            
            .book-button {
                background-color: #ff0000;
                color: white;
                padding: 12px 24px;
                text-decoration: none;
                border-radius: 8px;
                font-weight: 500;
                text-align: center;
                transition: background-color 0.2s;
                margin-top: auto;
            }
            
            .book-button:hover {
                background-color: #e60000;
            }
            
            .sold-out {
                background-color: #e2e8f0;
                color: #64748b;
                cursor: not-allowed;
            }
            
            .sold-out:hover {
                background-color: #e2e8f0;
            }
            
            .powered-by {
                grid-column: 1 / -1;
                text-align: center;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #eee;
                color: #666;
                font-size: 0.8rem;
            }
            
            .powered-by a {
                color: #ff0000;
                text-decoration: none;
            }
            
            @media (max-width: 768px) {
                #ticketrush-embed {
                    grid-template-columns: 1fr;
                    padding: 15px;
                }
            }
        </style>
        
        <!-- Font Awesome for icons -->
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        
        <div id="ticketrush-embed">
        '''

        if not future_events:
            events_html += '''
                <div style="grid-column: 1 / -1; text-align: center; padding: 40px;">
                    <i class="fas fa-calendar-times" style="font-size: 48px; color: #ccc; margin-bottom: 20px;"></i>
                    <p style="color: #666;">No upcoming events available.</p>
                </div>
            '''
        else:
            for event in future_events:
                try:
                    # Calculate tickets sold
                    succeeded_attendees = Attendee.query.filter_by(
                        event_id=event.id, 
                        payment_status='succeeded'
                    ).all()
                    tickets_sold = sum(attendee.tickets_purchased for attendee in succeeded_attendees)

                    # Calculate tickets available
                    if event.ticket_quantity is not None:
                        tickets_available = event.ticket_quantity - tickets_sold
                    else:
                        tickets_available = "Unlimited"

                    # Format date using the previously parsed date
                    formatted_date = event.parsed_date.strftime('%A %d %B %Y')

                    # Get ticket types
                    ticket_types = TicketType.query.filter_by(event_id=event.id).all()
                    ticket_info = "Free" if not ticket_types else "<br>".join(
                        f"{escape(tt.name)}: {'Free' if tt.price == 0 else f'£{tt.price:.2f}'}"
                        for tt in ticket_types
                    )

                    events_html += f'''
                    <div class="event-card">
                        <div class="event-image" style="background-image: url('{escape(event.image_url or 'https://via.placeholder.com/400x200')}')"></div>
                        <div class="event-content">
                            <h3 class="event-title">{escape(event.name)}</h3>
                            
                            <div class="event-meta">
                                <i class="far fa-calendar-alt"></i>  <!-- Changed to calendar-alt -->
                                <span>{formatted_date}</span>
                            </div>
                            
                            <div class="event-meta">
                                <i class="far fa-clock"></i>  <!-- Already a clock, but keeping for consistency -->
                                <span>{event.start_time} - {event.end_time}</span>
                            </div>
                            
                            <div class="event-meta">
                                <i class="fas fa-map-pin"></i>  <!-- Changed to map-pin -->
                                <span>{escape(event.location)}</span>
                            </div>
                            
                            <div class="price-tag">
                                {ticket_info}
                            </div>
                    '''

                    if tickets_available == "Unlimited" or tickets_available > 0:
                        events_html += f'''
                            <a href="https://bookings.ticketrush.io/purchase/{event.id}" 
                               class="book-button" target="_blank">
                               <i class="fas fa-arrow-right"></i> Book Now  <!-- Changed to arrow-right -->
                            </a>
                        '''
                    else:
                        events_html += '''
                            <span class="book-button sold-out">
                                <i class="fas fa-ban"></i> Sold Out
                            </span>
                        '''

                    events_html += '''
                        </div>
                    </div>
                    '''

                except Exception as e:
                    print(f"Error processing event {event.id}: {e}")
                    continue

        events_html += '''
            <div class="powered-by">
                Powered by <a href="https://www.ticketrush.io" target="_blank">TicketRush</a>
            </div>
        </div>
        '''

        # Return JavaScript
        response = f"document.write(`{events_html}`);"
        return Response(response, mimetype='application/javascript')

    except Exception as e:
        print(f"Unexpected error in embed_events: {e}")
        return "document.write(`<div id='ticketrush-embed'><p>Error loading events</p></div>`);"

@app.route('/cancel')
def cancel():
    return "Payment canceled. You can try again."


@app.route('/manage-default-questions', methods=['GET', 'POST'])
@login_required
def manage_default_questions():
    user = User.query.get(current_user.id)

    if request.method == 'POST':
        try:
            # Collect form data for user profile updates
            first_name = request.form.get('first_name').strip()
            last_name = request.form.get('last_name').strip()
            phone_number = request.form.get('phone_number').strip()
            business_name = request.form.get('business_name').strip()
            website_url = request.form.get('website_url', '').strip()
            vat_number = request.form.get('vat_number', '').strip()
            house_name_or_number = request.form.get('house_name_or_number').strip()
            street = request.form.get('street').strip()
            locality = request.form.get('locality', '').strip()
            town = request.form.get('town').strip()
            postcode = request.form.get('postcode').strip()
            terms_link = request.form.get('terms_link', '').strip()

            # Update user information
            user.first_name = first_name
            user.last_name = last_name
            user.phone_number = phone_number
            user.business_name = business_name
            user.vat_number = vat_number
            user.house_name_or_number = house_name_or_number
            user.street = street
            user.locality = locality
            user.town = town
            user.postcode = postcode

            # Process website URL
            if website_url:
                if not re.match(r'^https?://', website_url):
                    website_url = 'https://' + website_url
                user.website_url = website_url
            else:
                user.website_url = None

            # Process terms link
            if terms_link.lower() == 'none' or not terms_link:
                user.terms = 'none'
            else:
                if not re.match(r'^https?://', terms_link):
                    terms_link = 'https://' + terms_link
                user.terms = terms_link

            if request.method == 'POST':
                # Handle the logo file upload
                logo_file = request.files.get('business_logo')
                logo_url = None

                if logo_file:
                    print(f"Received file: {logo_file.filename}")

                    if allowed_file(logo_file.filename):
                        # Upload the file to S3 and save the URL
                        logo_url = upload_to_s3(logo_file, "business-logos")
                        
                        if logo_url:
                            # Update the user's business logo URL in the database
                            current_user.business_logo_url = logo_url
                            db.session.add(current_user)
                            db.session.commit()
                            flash("Business logo uploaded successfully!", "success")
                        else:
                            flash("There was an error uploading your business logo to S3. Please try again.", "danger")
                    else:
                        print("File type not allowed.")
                        flash('Unsupported file type for business logo. Please upload a PNG, JPG, JPEG, or GIF image.', 'danger')
                else:
                    print("No file received for 'business_logo'.")

            # Process default questions
            questions = request.form.getlist('questions[]')
            existing_questions = DefaultQuestion.query.filter_by(user_id=user.id).all()

            # Update existing questions
            for i, question_text in enumerate(questions):
                question_text = question_text.strip()
                if i < len(existing_questions):
                    existing_questions[i].question = question_text
                else:
                    if question_text:
                        new_question = DefaultQuestion(user_id=user.id, question=question_text)
                        db.session.add(new_question)

            # Remove extra questions if fewer are submitted
            if len(questions) < len(existing_questions):
                for q in existing_questions[len(questions):]:
                    db.session.delete(q)

            # Commit changes to the database
            db.session.commit()
            flash('Account settings successfully updated.', 'success')
            return redirect(url_for('dashboard'))

        except Exception as e:
            db.session.rollback()
            print(f"Error during POST request: {e}")
            flash('An error occurred while updating your account settings. Please try again.', 'danger')

    # GET request - render the form
    questions = DefaultQuestion.query.filter_by(user_id=user.id).all()
    return render_template('manage_default_questions.html', user=user, questions=questions)



def calculate_total_charge_and_booking_fee(n_tickets, ticket_price_gbp):
    # Constants
    platform_fee_per_ticket_pence = 30  # Platform fee: 30p per ticket
    stripe_percent_fee = 0.014          # Stripe percentage fee (1.4%)
    stripe_fixed_fee_pence = 20         # Fixed Stripe fee per transaction (20p)

    # Calculate the ticket price in pence
    total_ticket_price_pence = int(n_tickets * ticket_price_gbp * 100)

    # Calculate the platform fee (30p per ticket)
    total_platform_fee_pence = platform_fee_per_ticket_pence * n_tickets

    # Calculate the subtotal (ticket price + platform fee)
    subtotal_before_stripe = total_ticket_price_pence + total_platform_fee_pence

    # Calculate the Stripe fee (1.4% of subtotal + 20p)
    stripe_fee_pence = int(subtotal_before_stripe * stripe_percent_fee) + stripe_fixed_fee_pence

    # Calculate total charge to the buyer, including Stripe fee
    total_charge_pence = subtotal_before_stripe + stripe_fee_pence

    # Round up and return the total charge to the buyer and platform fee
    return int(math.ceil(total_charge_pence)), int(math.ceil(total_platform_fee_pence))



@app.route('/purchase/<int:event_id>', methods=['GET', 'POST'])
@app.route('/purchase/<int:event_id>/<string:promo_code>', methods=['GET', 'POST'])
def purchase(event_id, promo_code=None):
    try:
        event = Event.query.get_or_404(event_id)
        organizer = User.query.get(event.user_id)
        
        # Assign the business logo URL to logo_url
        organizer.logo_url = organizer.business_logo_url
        # Initialize variables
        attendees = []
        total_amount = 0  # Total amount in pence
        line_items = []
        booking_fee_pence = 0  # Initialize booking fee
        total_tickets_requested = 0
        total_tickets_sold = 0  # Initialize to 0

        # Collect custom questions from event
        custom_questions = []
        for i in range(1, 11):
            question_text = getattr(event, f'custom_question_{i}')
            if question_text:
                custom_questions.append({
                    'id': f'custom_{i}',
                    'question_text': question_text,
                    'question_type': 'text',
                    'required': True  # Adjust based on your requirements
                })

        # Collect default questions from organizer
        default_questions_query = DefaultQuestion.query.filter_by(user_id=organizer.id).order_by(DefaultQuestion.id).all()
        default_questions = [{
            'id': f'default_{dq.id}',
            'question_text': dq.question,
            'question_type': 'text',
            'required': True  # Adjust based on your requirements
        } for dq in default_questions_query]

        # Combine all questions
        all_questions = default_questions + custom_questions

        # Fetch ticket types
        ticket_types = event.ticket_types
        
        if request.method == 'POST':
            try:
                session_id = str(uuid4())
                full_name = request.form.get('full_name')
                email = request.form.get('email')
                phone_number = request.form.get('phone_number')

                # Validate required fields
                if not all([full_name, email, phone_number]):
                    flash('Please fill in all required fields.')
                    return redirect(url_for('purchase', event_id=event_id))

                if organizer.terms and organizer.terms.lower() != 'none':
                    if not request.form.get('accept_organizer_terms'):
                        flash("You must accept the event organizer's Terms and Conditions.")
                        return redirect(url_for('purchase', event_id=event_id))

                if not request.form.get('accept_platform_terms'):
                    flash("You must accept the platform's Terms and Conditions.")
                    return redirect(url_for('purchase', event_id=event_id))

                # Initialize variables
                attendees = []
                total_amount = 0  # Total amount in pence
                line_items = []
                booking_fee_pence = 0  # Initialize booking fee
                total_tickets_requested = 0

                # Collect custom questions from event
                custom_questions = []
                for i in range(1, 11):
                    question = getattr(event, f'custom_question_{i}')
                    if question:  # Only add non-empty questions
                        custom_questions.append({
                            'id': i,
                            'question_text': question,
                            'question_type': 'text',  # Default to text type
                            'required': True  # Default to required
                        })

                # Collect default questions from organizer
                default_questions = DefaultQuestion.query.filter_by(user_id=organizer.id).all()
                default_questions = [{
                    'id': q.id,
                    'question_text': q.question,
                    'question_type': 'text',  # Default to text type
                    'required': True  # Default to required
                } for q in default_questions]

                # Collect quantities for each ticket type
                quantities = {}
                for ticket_type in ticket_types:
                    quantity_str = request.form.get(f'quantity_{ticket_type.id}', '0')
                    quantity = int(quantity_str)
                    quantities[ticket_type.id] = quantity
                    if quantity > 0:
                        total_tickets_requested += quantity

                        if event.enforce_individual_ticket_limits and ticket_type.quantity is not None:
                            # Check if requested quantity exceeds available tickets for this type
                            tickets_sold_type = Attendee.query.filter_by(
                                event_id=event.id,
                                ticket_type_id=ticket_type.id,
                                payment_status='succeeded'
                            ).count()
                            tickets_remaining = ticket_type.quantity - tickets_sold_type
                            if quantity > tickets_remaining:
                                flash(f"Cannot purchase {quantity} tickets for {ticket_type.name}. Only {tickets_remaining} tickets are available.")
                                return redirect(url_for('purchase', event_id=event_id))
                        else:
                            # Will check total capacity later
                            pass

                # If individual ticket limits are not enforced, check total event capacity
                if not event.enforce_individual_ticket_limits:
                    total_tickets_sold = db.session.query(
                        func.sum(Attendee.tickets_purchased)
                    ).filter_by(event_id=event.id, payment_status='succeeded').scalar() or 0
                    tickets_available = event.ticket_quantity - total_tickets_sold
                    if total_tickets_requested > tickets_available:
                        flash(f"Cannot purchase {total_tickets_requested} tickets. Only {tickets_available} tickets are available.")
                        return redirect(url_for('purchase', event_id=event_id))
                else:
                    # When individual ticket limits are enforced, tickets_available isn't used in the same way
                    tickets_available = None  # Or handle accordingly

                # Collect custom questions
                questions = all_questions
                attendee_answers = {}

                # Collect answers for each ticket
                for ticket_type in ticket_types:
                    quantity = quantities[ticket_type.id]
                    for i in range(quantity):
                        answers = {}
                        for q_index, question in enumerate(questions):
                            answer_key = f'ticket_{ticket_type.id}_{i}_question_{q_index}'
                            answer = request.form.get(answer_key)
                            if not answer:
                                flash(f'Please answer all questions for {ticket_type.name} Ticket {i + 1}.')
                                return redirect(url_for('purchase', event_id=event_id))
                            answers[question] = answer
                        attendee_answers[(ticket_type.id, i)] = answers

                # Create Attendee entries and calculate amounts
                for ticket_type in ticket_types:
                    quantity = quantities[ticket_type.id]
                    if quantity > 0:
                        for i in range(quantity):
                            ticket_number = generate_unique_ticket_number()
                            answers = attendee_answers.get((ticket_type.id, i), {})

                            attendee = Attendee(
                                event_id=event.id,
                                ticket_type_id=ticket_type.id,
                                ticket_answers=json.dumps(answers),
                                payment_status='pending',
                                full_name=full_name,
                                email=email,
                                phone_number=phone_number,
                                tickets_purchased=1,
                                ticket_price_at_purchase=ticket_type.price,
                                session_id=session_id,
                                created_at=datetime.now(timezone.utc),
                                ticket_number=ticket_number
                            )
                            db.session.add(attendee)
                            attendees.append(attendee)

                # Collect custom questions from event
                custom_questions = []
                for i in range(1, 11):
                    question = getattr(event, f'custom_question_{i}')
                    if question:  # Only add non-empty questions
                        custom_questions.append({
                            'id': i,
                            'question_text': question,
                            'question_type': 'text',  # Default to text type
                            'required': True  # Default to required
                        })

                # Collect default questions from organizer
                default_questions_query = DefaultQuestion.query.filter_by(user_id=organizer.id).all()
                default_questions = [{
                    'id': q.id,
                    'question_text': q.question,
                    'question_type': 'text',  # Default to text type
                    'required': True  # Default to required
                } for q in default_questions_query]
            

                # Get promo code from form and initialize active_promo
                submitted_promo_code = request.form.get('promo_code')
                active_promo = None
                discount_rules = DiscountRule.query.filter_by(event_id=event_id).all()

                if submitted_promo_code:
                    # Find matching promo code discount rule
                    active_promo = DiscountRule.query.filter_by(
                        event_id=event_id,
                        discount_type='promo_code',
                        promo_code=submitted_promo_code
                    ).first()

                # Calculate base amount (in pence)
                print("\n=== PAYMENT CALCULATION DETAILS ===")
                print("Calculating base amount for tickets:")
                base_amount = 0
                total_tickets = 0
                for ticket_type_id, quantity in quantities.items():
                    if quantity > 0:
                        ticket_type = next(tt for tt in ticket_types if tt.id == ticket_type_id)
                        ticket_total = ticket_type.price * quantity * 100
                        print(f"- {ticket_type.name}: {quantity} x £{ticket_type.price:.2f} = £{ticket_total/100:.2f}")
                        base_amount += ticket_total
                        total_tickets += quantity  # Add this line
                print(f"Base amount before discounts: £{base_amount/100:.2f}")

                # Apply discount
                discount_amount = 0
                if active_promo:
                    print(f"\nApplying promo code discount:")
                    print(f"- Discount percentage: {active_promo.discount_percent}%")
                    discount_amount = base_amount * (active_promo.discount_percent / 100)
                    print(f"- Promo code discount amount: £{discount_amount/100:.2f}")
                else:
                    # Check other discount rules only if no promo code is active
                    print("\nChecking other discount rules:")
                    discount_rules = DiscountRule.query.filter_by(event_id=event_id).all()
                    
                    for rule in discount_rules:
                        if rule.discount_type != 'promo_code':  # Skip promo code rules
                            current_discount = 0
                            print(f"\nEvaluating {rule.discount_type} discount rule:")
                            print(f"- Discount percentage: {rule.discount_percent}%")
                            
                            if rule.discount_type == 'early_bird':
                                # Existing early bird logic
                                if rule.valid_until and datetime.now() < rule.valid_until:
                                    if not rule.max_early_bird_tickets or total_tickets <= rule.max_early_bird_tickets:
                                        current_discount = base_amount * (rule.discount_percent / 100)
                            
                            elif rule.discount_type == 'bulk' and total_tickets >= rule.min_tickets:
                                # Existing bulk discount logic
                                if rule.apply_to == 'all':
                                    current_discount = base_amount * (rule.discount_percent / 100)
                                else:  # 'additional'
                                    per_ticket_amount = base_amount / total_tickets
                                    additional_tickets = total_tickets - 1
                                    current_discount = (per_ticket_amount * additional_tickets) * (rule.discount_percent / 100)
                            
                            # Keep the highest discount
                            if current_discount > discount_amount:
                                discount_amount = current_discount

                # Apply the discount
                total_amount_pence = int(base_amount - discount_amount)
                print(f"\nAmount after discounts: £{total_amount_pence/100:.2f}")

                # Calculate fees
                print("\nCalculating fees:")
                booking_fee_pence = 30 * total_tickets  # 30p per ticket
                print(f"- Base booking fee: {total_tickets} tickets × 30p = £{booking_fee_pence/100:.2f}")

                subtotal_before_stripe = total_amount_pence + booking_fee_pence
                print(f"- Subtotal before Stripe fee: £{subtotal_before_stripe/100:.2f}")

                stripe_fee_pence = int(subtotal_before_stripe * 0.014) + 20  # 1.4% + 20p
                print(f"- Stripe fee: 1.4% + 20p = £{stripe_fee_pence/100:.2f}")

                total_booking_fee_pence = booking_fee_pence + stripe_fee_pence
                print(f"- Total booking fee: £{total_booking_fee_pence/100:.2f}")

                # Adjust platform fee to cover Stripe's processing cut
                adjusted_platform_fee = int(booking_fee_pence / 0.971)  # Adjust for Stripe's cut
                print(f"- Adjusted platform fee: £{adjusted_platform_fee/100:.2f}")

                # Final charge amount
                total_charge_pence = total_amount_pence + total_booking_fee_pence
                print(f"\nFinal charge amount: £{total_charge_pence/100:.2f}")
                print("=== END PAYMENT CALCULATION ===\n")

                if not attendees:
                    print("No attendees found - redirecting back to purchase page")
                    flash('Please select at least one ticket.')
                    return redirect(url_for('purchase', event_id=event_id))

                db.session.commit()

                # Handle free tickets
                if total_amount_pence == 0:
                    for attendee in attendees:
                        attendee.payment_status = 'succeeded'  # Mark as paid for free tickets
                    db.session.commit()

                    # Set up billing details for the confirmation email
                    billing_details = {'name': full_name, 'email': email, 'phone': phone_number}

                    # Send confirmation emails for free tickets
                    send_confirmation_email_to_attendee(attendees, billing_details)
                    send_confirmation_email_to_organizer(organizer, attendees, billing_details, event)

                    flash('Your free ticket(s) have been booked successfully!')
                    return redirect(url_for('success', session_id=session_id))

                else:
                    # Convert quantities dictionary to use string keys
                    quantities_for_stripe = {
                        str(ticket_type_id): quantity 
                        for ticket_type_id, quantity in quantities.items()
                    }

                    # Prepare ticket and attendee data for Stripe metadata
                    ticket_data = {
                        'quantities': quantities_for_stripe,
                        'total_tickets': total_tickets_requested,
                        'total_amount': total_amount_pence
                    }

                    attendee_data = {
                        'full_name': full_name,
                        'email': email,
                        'phone_number': phone_number,
                        'answers': {
                            str(k): v for k, v in attendee_answers.items()
                        }
                    }

                    # Initialize line_items with individual tickets and separate booking fee line item
                    line_items = []
                    
                    print(f"\nCreating Stripe line items:")
                    
                    # Handle bulk discount for 'additional' tickets differently
                    for rule in discount_rules:
                        if (rule.discount_type == 'bulk' and 
                            total_tickets >= rule.min_tickets and 
                            rule.apply_to == 'additional'):
                        
                            print(f"Processing bulk discount for additional tickets:")
                            print(f"- Discount percentage: {rule.discount_percent}%")
                            
                            for ticket_type_id, quantity in quantities.items():
                                ticket_type = next((t for t in ticket_types if t.id == ticket_type_id), None)
                                if ticket_type and quantity > 0:
                                    # Add first ticket at full price
                                    print(f"- Adding 1 x {ticket_type.name} at full price: £{ticket_type.price:.2f}")
                                    line_items.append({
                                        'price_data': {
                                            'currency': 'gbp',
                                            'unit_amount': int(ticket_type.price * 100),
                                            'product_data': {
                                                'name': f"{ticket_type.name} for {event.name} - Full Price",
                                            },
                                        },
                                        'quantity': 1,
                                    })
                                    
                                    # Add remaining tickets at discounted price if any
                                    if quantity > 1:
                                        discounted_price = ticket_type.price * (1 - rule.discount_percent / 100)
                                        print(f"- Adding {quantity-1} x {ticket_type.name} at discounted price: £{discounted_price:.2f}")
                                        line_items.append({
                                            'price_data': {
                                                'currency': 'gbp',
                                                'unit_amount': int(discounted_price * 100),
                                                'product_data': {
                                                    'name': f"{ticket_type.name} for {event.name} - {rule.discount_percent}% Additional",
                                                },
                                            },
                                            'quantity': quantity - 1,
                                        })
                        else:
                            # Handle other discount types or no discount
                            for ticket_type_id, quantity in quantities.items():
                                ticket_type = next((t for t in ticket_types if t.id == ticket_type_id), None)
                                if ticket_type and quantity > 0:
                                    final_price = (total_amount_pence / total_tickets) / 100
                                    print(f"- Adding {quantity} x {ticket_type.name} at £{final_price:.2f} each")
                                    line_items.append({
                                        'price_data': {
                                            'currency': 'gbp',
                                            'unit_amount': int(final_price * 100),
                                            'product_data': {
                                                'name': f"{ticket_type.name} for {event.name}",
                                            },
                                        },
                                        'quantity': quantity,
                                    })

                    # Add the booking fee line item
                    print(f"- Adding booking fee: £{total_booking_fee_pence/100:.2f}")
                    line_items.append({
                        'price_data': {
                            'currency': 'gbp',
                            'product_data': {'name': 'Booking, handling, and processing fee'},
                            'unit_amount': total_booking_fee_pence,
                        },
                        'quantity': 1,
                    })

                    print("\nFinal line items breakdown:")
                    for item in line_items:
                        print(f"- {item['price_data']['product_data']['name']}: "
                              f"£{item['price_data']['unit_amount']/100:.2f} × {item['quantity']}")
                    print(f"Total charge: £{total_charge_pence/100:.2f}\n")

                    # Create Stripe checkout session
                    checkout_session = stripe.checkout.Session.create(
                        payment_method_types=['card'],
                        line_items=line_items,
                        mode='payment',
                        success_url=url_for('success', session_id=session_id, _external=True),
                        cancel_url=url_for('cancel', _external=True),
                        metadata={
                            'session_id': session_id,
                            'promo_code': submitted_promo_code if submitted_promo_code else None,  # Changed from active_promo
                            'discount_amount': str(discount_amount) if discount_amount > 0 else None
                        },
                        payment_intent_data={
                            'application_fee_amount': adjusted_platform_fee,
                            'on_behalf_of': organizer.stripe_connect_id,
                            'transfer_data': {
                                'destination': organizer.stripe_connect_id,
                            },
                        },
                        billing_address_collection='required',
                        customer_email=email
                    )

                    return redirect(checkout_session.url)

            except Exception as e:
                app.logger.error(f"Error creating checkout session: {str(e)}")
                flash('An error occurred while processing your payment. Please try again.', 'error')
                return redirect(url_for('purchase', event_id=event_id))

        else:
            # Get active discount rules
            discount_rules = DiscountRule.query.filter_by(event_id=event_id).all()
            active_discount = None
            
            for rule in discount_rules:
                if rule.discount_type == 'early_bird':
                    if rule.valid_until and datetime.now() < rule.valid_until:
                        active_discount = {
                            'type': 'early_bird',
                            'percentage': rule.discount_percent,
                            'valid_until': rule.valid_until.isoformat(),
                            'max_tickets': rule.max_early_bird_tickets
                        }
                        break
                elif rule.discount_type == 'bulk':
                    active_discount = {
                        'type': 'bulk',
                        'percentage': rule.discount_percent,
                        'minTickets': rule.min_tickets,
                        'apply_to': rule.apply_to
                    }
                    break
                elif rule.discount_type == 'promo_code':
                    active_discount = {
                        'type': 'promo_code',
                        'percentage': rule.discount_percent
                    }
                    break

            platform_terms_link = 'https://ticketrush.io/wp-content/uploads/2024/10/TicketRush-Terms-of-Service-25th-October-2024.pdf'
            organizer_terms_link = organizer.terms if organizer.terms and organizer.terms.lower() != 'none' else None

            # Calculate tickets available for total capacity events
            if not event.enforce_individual_ticket_limits:
                total_tickets_sold = db.session.query(
                    func.sum(Attendee.tickets_purchased)
                ).filter_by(event_id=event.id, payment_status='succeeded').scalar() or 0
                tickets_available = event.ticket_quantity - total_tickets_sold
            else:
                tickets_available = None

            # Get promo code from form (though on GET request, this will be None)
            submitted_promo_code = request.form.get('promo_code')
            active_promo = None

            if submitted_promo_code:
                # Find matching promo code discount rule
                active_promo = DiscountRule.query.filter_by(
                    event_id=event_id,
                    discount_type='promo_code',
                    promo_code=submitted_promo_code
                ).first()

            # Collect custom questions from event
            custom_questions = []
            for i in range(1, 11):
                question_text = getattr(event, f'custom_question_{i}')
                if question_text:
                    custom_questions.append({
                        'id': f'custom_{i}',
                        'question_text': question_text,
                        'question_type': 'text',
                        'required': True  # Adjust as needed
                    })

            # Collect default questions from organizer
            default_questions_query = DefaultQuestion.query.filter_by(user_id=organizer.id).order_by(DefaultQuestion.id).all()
            default_questions = [{
                'id': f'default_{dq.id}',
                'question_text': dq.question,
                'question_type': 'text',
                'required': True  # Adjust as needed
            } for dq in default_questions_query]

            # Combine all questions
            all_questions = default_questions + custom_questions

            # Print questions for debugging
            print("Questions being passed to template:", all_questions)

            return render_template(
                'purchase.html',
                event=event,
                organizer=organizer,
                questions=all_questions,
                organizer_terms_link=organizer_terms_link,
                platform_terms_link=platform_terms_link,
                ticket_types=ticket_types,
                enforce_individual_ticket_limits=event.enforce_individual_ticket_limits,
                tickets_available=tickets_available,
                discount_config=active_discount
            )
                                
        

    except Exception as e:
        app.logger.error(f"Error in purchase route: {str(e)}")
        flash('An error occurred. Please try again.', 'error')
        return redirect(url_for('dashboard'))




@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    print("Webhook received")
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
        print(f"Webhook event constructed: {event['type']}")
    except ValueError as e:
        # Invalid payload
        print(f"Invalid payload: {e}")
        return '', 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print(f"Invalid signature: {e}")
        return '', 400

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        print("Handling checkout.session.completed event")
        handle_checkout_session(session)
    else:
        print(f"Unhandled event type: {event['type']}")

    return '', 200




# Route to generate ICS file
@app.route('/download_ics/<int:event_id>')
def download_ics(event_id):
    event = Event.query.get_or_404(event_id)
    organizer = User.query.get(event.user_id)

    # Prepare ICS file content
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Your Company//NONSGML Event//EN
BEGIN:VEVENT
UID:{event.id}@your-platform.com
DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}
DTSTART:{event.date.replace('-', '')}T{event.start_time.replace(':', '')}00Z
DTEND:{event.date.replace('-', '')}T{event.end_time.replace(':', '')}00Z
SUMMARY:{event.name}
DESCRIPTION:{event.description}
LOCATION:{event.location}
END:VEVENT
END:VCALENDAR
"""

    # Return the ICS file as a download
    return Response(ics_content, mimetype='text/calendar', headers={
        'Content-Disposition': f'attachment; filename={event.name}.ics'
    })

def send_confirmation_email_to_attendee(attendees, billing_details):
    try:
        # Ensure attendees list is not empty
        if not attendees:
            print("No attendees provided to send confirmation email.")
            return

        # Use the first attendee to gather common details
        first_attendee = attendees[0]

        # Fetch event and organizer details
        event = Event.query.get(first_attendee.event_id)
        organizer = User.query.get(event.user_id)

        # Calculate total tickets and total price
        total_tickets = sum(attendee.tickets_purchased for attendee in attendees)
        total_price = sum(attendee.ticket_price_at_purchase * attendee.tickets_purchased for attendee in attendees)

        # Generate calendar links
        start_time = event.start_time.replace(':', '')
        end_time = event.end_time.replace(':', '')
        event_date = event.date.replace('-', '')
        google_calendar_url = (
            f"https://www.google.com/calendar/render?"
            f"&text={urllib.parse.quote(event.name)}"
            f"&dates={event_date}T{start_time}Z/{event_date}T{end_time}Z"
            f"&details=Event+at+{urllib.parse.quote(event.location)}"
            f"&location={urllib.parse.quote(event.location)}"
            f"&sf=true&output=xml"
        )
        ics_file_url = url_for('download_ics', event_id=event.id, _external=True)

        # Organizer details section
        organizer_details = f"""
        <p>
            <strong>Business:</strong> {organizer.business_name}<br>
            <strong>Website:</strong> <a href="{organizer.website_url or '#'}" style="color: #ff0000;">{organizer.website_url or 'No website provided'}</a><br>
        """
        if organizer.terms and organizer.terms.lower() != 'none':
            organizer_details += f"""
            <strong>Organiser's Terms:</strong> <a href="{organizer.terms}" style="color: #ff0000;">{organizer.terms}</a>
            """
        organizer_details += "</p>"

        # Generate QR codes for each ticket and label by ticket type
        qr_code_images = []
        for attendee in attendees:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(attendee.ticket_number)
            qr.make(fit=True)
            
            # Create QR code image
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64 for email embedding
            buffer = BytesIO()
            qr_img.save(buffer, format="PNG")
            qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
            
            ticket_type_label = attendee.ticket_type.name if attendee.ticket_type else "General Admission"
            qr_code_images.append((ticket_type_label, qr_base64))

        # Construct email body with QR codes and details
        body = f"""
        <html>
        <body style="background-color: #ffffff; color: #000000; font-family: Arial, sans-serif; padding: 20px;">
            <div style="text-align: center; margin-bottom: 20px;">
                <img src="http://ticketrush.io/wp-content/uploads/2024/10/TicketRush-Logo.png" alt="Ticket Rush Logo" style="max-width: 200px;">
            </div>

            <h2 style="color: #ff0000;">Hello {first_attendee.full_name},</h2>
            <p>Thank you for purchasing tickets for the event <strong>'{event.name}'</strong>. Below are your details:</p>

            <hr style="border: 1px solid #ff0000;">
            <h3 style="color: #ff0000;">Event Information:</h3>
            <p>
                <strong>Event:</strong> {event.name}<br>
                <strong>Date:</strong> {event.date}<br>
                <strong>Time:</strong> {event.start_time} - {event.end_time}<br>
                <strong>Location:</strong> {event.location}
            </p>

            <h3 style="color: #ff0000;">Your Details:</h3>
            <p>
                <strong>Full Name:</strong> {first_attendee.full_name}<br>
                <strong>Email:</strong> {first_attendee.email}<br>
                <strong>Phone Number:</strong> {first_attendee.phone_number}<br>
                <strong>Ticket Quantity:</strong> {total_tickets}<br>
                <strong>Amount Paid:</strong> £{total_price:.2f}<br>
                <strong>Billing Address:</strong> {billing_details.get('address', {}).get('line1')}, {billing_details.get('address', {}).get('city')}
            </p>

            <hr style="border: 1px solid #ff0000;">
            <h3 style="color: #ff0000;">Add to Calendar:</h3>
            <div style="margin-bottom: 20px;">
                <a href="{ics_file_url}" style="display: inline-block; background-color: #ff0000; color: #ffffff; padding: 10px 15px; text-decoration: none; border-radius: 5px;">Apple/iOS Calendar</a>
                <a href="{google_calendar_url}" style="display: inline-block; background-color: #ff0000; color: #ffffff; padding: 10px 15px; text-decoration: none; border-radius: 5px;">Google Calendar</a>
            </div>

            <hr style="border: 1px solid #ff0000;">
            <h3 style="color: #ff0000;">Your QR Code(s) for Event Entry:</h3>
            <p>Please present the following QR code(s) at the event entrance:</p>
            <div style="display: flex; flex-wrap: wrap;">
        """

        # Add each QR code image to the email body with the ticket type label
        for label, qr_base64 in qr_code_images:
            body += f"""
            <div style="text-align: center; margin: 10px;">
                <p><strong>{label}</strong></p>
                <img src="data:image/png;base64,{qr_base64}" alt="QR Code" style="width: 150px; height: 150px;">
            </div>
            """

        # Finish the email body
        body += f"""
            </div>
            <hr style="border: 1px solid #ff0000;">
            <h3 style="color: #ff0000;">Organiser Details:</h3>
            {organizer_details}

            <hr style="border: 1px solid #ff0000;">
            <h3 style="color: #ff0000;">Need Help?</h3>
            <p>
                For questions about the event, reach out directly to {organizer.business_name} at <a href="mailto:{organizer.email}" style="color: #ff0000;">{organizer.email}</a>.
            </p>

            <p style="color: #ff0000;"><strong>Powered by TicketRush</strong></p>
        </body>
        </html>
        """

        # Send the email
        msg = Message(
            subject=f"Your Ticket Confirmation for {event.name}",
            recipients=[first_attendee.email],
            body=body,
            html=body  # HTML body for rich content
        )
        mail.send(msg)
        print(f"Confirmation email sent to attendee {first_attendee.email}.")

    except Exception as e:
        print(f"Failed to send confirmation email to attendee. Error: {str(e)}")


def send_confirmation_email_to_organizer(organizer, attendees, billing_details, event):
    try:
        # Collect attendee details, including custom/default questions and answers
        attendee_info = ""
        for attendee in attendees:
            # Load custom questions and answers
            answers = json.loads(attendee.ticket_answers) if attendee.ticket_answers else {}
            question_answer_pairs = "".join([f"<strong>{question}:</strong> {answer}<br>" for question, answer in answers.items()])

            # Add attendee details to the email
            attendee_info += f"""
            <p>
                <strong>Name:</strong> {attendee.full_name}<br>
                <strong>Email:</strong> {attendee.email}<br>
                <strong>Phone:</strong> {attendee.phone_number}<br>
                <strong>Ticket Quantity:</strong> {attendee.tickets_purchased}<br>
                <strong>Total Amount Paid:</strong> £{attendee.ticket_price_at_purchase * attendee.tickets_purchased:.2f}<br>
                {question_answer_pairs}
            </p>
            <hr style="border: 1px solid #ff0000;">
            """

        # Prepare the subject line
        subject = f"New Ticket Purchase for Your Event '{event.name}'"

        # Placeholder for the dashboard link
        dashboard_link = "https://bookings.ticketrush.io/login"  # Replace with actual dashboard link

        # Prepare the email body with the same inline CSS and logo as the attendee email
        body = f"""
        <html>
        <body style="background-color: #ffffff; color: #000000; font-family: Arial, sans-serif; padding: 20px;">
            <!-- Include Logo -->
            <div style="text-align: center; margin-bottom: 20px;">
                <img src="http://ticketrush.io/wp-content/uploads/2024/10/TicketRush-Logo.png" alt="Ticket Rush Logo" style="max-width: 200px;">
            </div>

            <h2 style="color: #ff0000;">Hello {organizer.first_name},</h2>

            <p>You've received new ticket purchases for your event <strong>'{event.name}'</strong>. Here are the details:</p>

            <hr style="border: 1px solid #ff0000;">
            
            <h3 style="color: #ff0000;">Event Information:</h3>
            <p>
                <strong>Event:</strong> {event.name}<br>
                <strong>Date:</strong> {event.date}<br>
                <strong>Time:</strong> {event.start_time} - {event.end_time}<br>
                <strong>Location:</strong> {event.location}
            </p>

            <h3 style="color: #ff0000;">Attendee Details:</h3>
            {attendee_info}

            <hr style="border: 1px solid #ff0000;">
            
            <h3 style="color: #ff0000;">View This Booking:</h3>
            <div style="margin-bottom: 20px;">
                <a href="{dashboard_link}" style="display: inline-block; background-color: #ff0000; color: #ffffff; padding: 10px 15px; text-decoration: none; border-radius: 5px;">View in Your Dashboard</a>
            </div>
            
            <hr style="border: 1px solid #ff0000;">
            
            <!-- Support Section -->
            <h3 style="color: #ff0000;">Need Help?</h3>
            <p>
                If you have any questions or need assistance, feel free to reach out to TicketRush support at 
                <a href="mailto:support@ticketrush.co.uk" style="color: #ff0000;">support@ticketrush.co.uk</a>.
            </p>

            <hr style="border: 1px solid #ff0000;">
            
            <p style="color: #ff0000;"><strong>Powered by TicketRush</strong></p>
        </body>
        </html>
        """

        # Create and send the email using Flask-Mail
        msg = Message(
            subject=subject,
            recipients=[organizer.email],
            body=body,
            html=body  # Render the email as HTML to support links and styling
        )
        mail.send(msg)
        print(f"Confirmation email sent to organizer {organizer.email}.")

    except Exception as e:
        print(f"Failed to send confirmation email to organizer {organizer.email}. Error: {str(e)}")



        # Create and send the email using Flask-Mail
        msg = Message(
            subject=subject,
            recipients=[organizer.email],
            body=body,
            html=body  # Render the email as HTML to support links and styling
        )
        mail.send(msg)
        print(f"Confirmation email sent to organizer {organizer.email}.")

    except Exception as e:
        print(f"Failed to send confirmation email to organizer {organizer.email}. Error: {str(e)}")


# Update handle_checkout_session to generate QR codes
def handle_checkout_session(session):
    session_id = session.get('metadata', {}).get('session_id')
    if not session_id:
        print("No session ID found in metadata.")
        return

    # Retrieve all attendees for this session ID
    attendees = Attendee.query.filter_by(session_id=session_id).all()

    if not attendees:
        print(f"No attendees found for session ID {session_id}.")
        return

    # Retrieve the PaymentIntent and charge details
    payment_intent_id = session.get('payment_intent')
    payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id, expand=['latest_charge'])
    charge = payment_intent.latest_charge

    # Extract billing details
    billing_details = charge.billing_details
    if billing_details is None:
        print("No billing details found for this session.")
        return

    # Update attendee records
    for attendee in attendees:
        attendee.billing_details = json.dumps(billing_details)
        attendee.stripe_charge_id = charge.id
        attendee.payment_status = 'succeeded'
        
        # Generate ticket number if it is None
        if attendee.ticket_number is None:
            attendee.ticket_number = generate_unique_ticket_number()

    db.session.commit()  # Commit all updates after the loop

    try:
        # Send confirmation emails
        send_confirmation_email_to_attendee(attendees, billing_details)
        event = Event.query.get(attendees[0].event_id)
        organizer = User.query.get(event.user_id)
        if organizer:
            send_confirmation_email_to_organizer(organizer, attendees, billing_details, event)
    except Exception as e:
        print(f"Error sending confirmation emails: {str(e)}")
        # Don't raise the exception - we still want to acknowledge the webhook



from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime

@app.route('/view_attendees/<int:event_id>')
@login_required
def view_attendees(event_id):
    event = Event.query.get_or_404(event_id)

    # Ensure the user has permission to view the attendees
    if event.user_id != current_user.id:
        flash("You don't have permission to view the attendees for this event.")
        return redirect(url_for('dashboard'))

    # Fetch default and custom questions
    user = User.query.get(event.user_id)
    default_questions = DefaultQuestion.query.filter_by(user_id=user.id).all()
    default_question_texts = [dq.question for dq in default_questions]

    custom_questions = []
    for i in range(1, 11):  # Loop through 10 possible custom questions
        question = getattr(event, f'custom_question_{i}')
        if question:
            custom_questions.append(question)

    all_questions = default_question_texts + custom_questions

    # Fetch only attendees with successful payments
    attendees = Attendee.query.filter_by(
        event_id=event_id,
        payment_status='succeeded'
    ).all()

    # Initialize ticket type data and total tickets sold
    ticket_types = event.ticket_types
    ticket_type_data = {}
    tickets_sold_total = 0  # Total tickets sold across all types

    if event.enforce_individual_ticket_limits:
        # When individual ticket type limits are enforced
        for ticket_type in ticket_types:
            tickets_sold_type = Attendee.query.filter_by(
                event_id=event.id,
                ticket_type_id=ticket_type.id,
                payment_status='succeeded'  # Only count succeeded payments
            ).count()
            tickets_remaining_type = (ticket_type.quantity or 0) - tickets_sold_type
            tickets_sold_total += tickets_sold_type

            ticket_type_data[ticket_type.id] = {
                'name': ticket_type.name,
                'price': ticket_type.price,
                'quantity': ticket_type.quantity,
                'tickets_sold': tickets_sold_type,
                'tickets_remaining': tickets_remaining_type
            }
        total_quantity = sum(
            tt.quantity for tt in ticket_types if tt.quantity is not None
        )
        tickets_available = total_quantity - tickets_sold_total

    else:
        # When total event capacity is enforced
        for ticket_type in ticket_types:
            tickets_sold_type = Attendee.query.filter_by(
                event_id=event.id,
                ticket_type_id=ticket_type.id,
                payment_status='succeeded'  # Only count succeeded payments
            ).count()
            tickets_sold_total += tickets_sold_type

            ticket_type_data[ticket_type.id] = {
                'name': ticket_type.name,
                'price': ticket_type.price,
                'quantity': "N/A",  # Indicate not applicable
                'tickets_sold': tickets_sold_type,
                'tickets_remaining': None  # Do not calculate remaining
            }
        total_quantity = event.ticket_quantity
        tickets_available = total_quantity - tickets_sold_total

    # Format the event date as dd-mm-yyyy
    event_date = datetime.strptime(event.date, '%Y-%m-%d').strftime('%d-%m-%Y')

    return render_template(
        'view_attendees.html',
        event=event,
        attendees=attendees,
        questions=all_questions,
        tickets_sold=tickets_sold_total,
        tickets_available=tickets_available,
        total_quantity=total_quantity,
        event_date=event_date,
        ticket_type_data=ticket_type_data  # Pass ticket type data to template
    )






@app.route('/delete_event/<int:event_id>', methods=['POST'])
@login_required
def delete_event(event_id):
    try:
        event = Event.query.get_or_404(event_id)

        # Check if current user owns the event
        if event.user_id != current_user.id:
            flash("You do not have permission to delete this event.", "error")
            return redirect(url_for('dashboard'))

        # Delete all attendees associated with the event first
        Attendee.query.filter_by(event_id=event_id).delete()
        
        # Delete all ticket types associated with the event
        TicketType.query.filter_by(event_id=event_id).delete()
        
        # Delete all discount rules associated with the event
        DiscountRule.query.filter_by(event_id=event_id).delete()
        
        # Finally delete the event
        db.session.delete(event)
        db.session.commit()
        
        flash('Event and all associated data deleted successfully!')
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        print(f"Error deleting event: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/edit_event/<int:event_id>', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    event = Event.query.get_or_404(event_id)
    
    if event.user_id != current_user.id:
        flash('You do not have permission to edit this event.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            # Handle image upload
            if 'event_image' in request.files:
                file = request.files['event_image']
                if file and file.filename:
                    # Generate a secure filename
                    filename = secure_filename(file.filename)
                    # Create a unique filename to avoid conflicts
                    unique_filename = f"{uuid.uuid4()}_{filename}"
                    
                    # Save the file
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(file_path)
                    
                    # Update the event's image URL
                    event.image_url = url_for('static', filename=f'uploads/{unique_filename}')

            # Update event details from form fields
            event.name = request.form.get('name')
            event.date = request.form.get('date')
            event.start_time = request.form.get('start_time')
            event.end_time = request.form.get('end_time')
            event.location = request.form.get('location')
            event.description = request.form.get('description')

            # Set tickets_sold for each ticket_type before processing
            for ticket_type in event.ticket_types:
                tickets_sold = db.session.query(func.sum(Attendee.tickets_purchased))\
                    .filter(Attendee.ticket_type_id == ticket_type.id)\
                    .filter(Attendee.payment_status == 'succeeded')\
                    .scalar() or 0
                ticket_type.tickets_sold = tickets_sold

            # Update existing ticket types
            for ticket_type in event.ticket_types:
                # Get form field names
                name_field = f'name_{ticket_type.id}'
                price_field = f'price_{ticket_type.id}'
                quantity_field = f'quantity_{ticket_type.id}'

                if name_field in request.form and price_field in request.form:
                    # Update ticket type details
                    ticket_type.name = request.form.get(name_field)
                    ticket_type.price = float(request.form.get(price_field))
                    if event.enforce_individual_ticket_limits:
                        if quantity_field in request.form:
                            ticket_type.quantity = int(request.form.get(quantity_field))
                        else:
                            ticket_type.quantity = None
                    else:
                        ticket_type.quantity = None  # Set to None when individual limits are not enforced
                else:
                    # Handle removal of ticket types
                    if ticket_type.tickets_sold == 0:
                        db.session.delete(ticket_type)
                    else:
                        flash(f"Cannot delete ticket type '{ticket_type.name}' as it has sales.", 'warning')

            # Handle new ticket types
            new_names = request.form.getlist('new_ticket_name[]')
            new_prices = request.form.getlist('new_ticket_price[]')
            new_quantities = request.form.getlist('new_ticket_quantity[]') if event.enforce_individual_ticket_limits else []

            for i in range(len(new_names)):
                name = new_names[i].strip()
                price = new_prices[i].strip()
                quantity = new_quantities[i].strip() if new_quantities else None

                if name and price:
                    new_ticket = TicketType(
                        event_id=event_id,
                        name=name,
                        price=float(price),
                        quantity=int(quantity) if quantity else None
                    )
                    db.session.add(new_ticket)

            # Update event total capacity if not using individual limits
            if not event.enforce_individual_ticket_limits:
                total_ticket_quantity = request.form.get('total_ticket_quantity')
                event.ticket_quantity = int(total_ticket_quantity) if total_ticket_quantity else None

            # Update custom questions
            for i in range(1, 11):
                question_key = f'custom_question_{i}'
                question_value = request.form.get(question_key)
                setattr(event, question_key, question_value)

            # **Handle Discount Rules**

            # First, delete existing discount rules for the event
            DiscountRule.query.filter_by(event_id=event_id).delete()

            # Retrieve discount rule data from form
            discount_types = request.form.getlist('discount_type[]')

            for i in range(len(discount_types)):
                discount_type = discount_types[i]
                if discount_type == 'bulk':
                    min_tickets_list = request.form.getlist('min_tickets[]')
                    bulk_discount_list = request.form.getlist('bulk_discount[]')
                    apply_to_list = request.form.getlist('apply_to[]')

                    min_tickets = min_tickets_list[i] if i < len(min_tickets_list) else None
                    discount_percent = bulk_discount_list[i] if i < len(bulk_discount_list) else None
                    apply_to = apply_to_list[i] if i < len(apply_to_list) else None

                    if min_tickets and discount_percent and apply_to:
                        new_rule = DiscountRule(
                            event_id=event_id,
                            discount_type='bulk',
                            discount_percent=float(discount_percent),
                            min_tickets=int(min_tickets),
                            apply_to=apply_to
                        )
                        db.session.add(new_rule)

                elif discount_type == 'early_bird':
                    valid_until_list = request.form.getlist('valid_until[]')
                    early_bird_discount_percent_list = request.form.getlist('early_bird_discount_percent[]')
                    max_tickets_list = request.form.getlist('max_early_bird_tickets[]')

                    valid_until_str = valid_until_list[i] if i < len(valid_until_list) else None
                    discount_percent = early_bird_discount_percent_list[i] if i < len(early_bird_discount_percent_list) else None
                    max_tickets = max_tickets_list[i] if i < len(max_tickets_list) else None

                    valid_until = datetime.strptime(valid_until_str, '%Y-%m-%dT%H:%M') if valid_until_str else None

                    if discount_percent and max_tickets:
                        new_rule = DiscountRule(
                            event_id=event_id,
                            discount_type='early_bird',
                            discount_percent=float(discount_percent),
                            valid_until=valid_until,
                            max_early_bird_tickets=int(max_tickets)
                        )
                        db.session.add(new_rule)

                elif discount_type == 'promo_code':
                    promo_code_list = request.form.getlist('promo_code[]')
                    promo_discount_list = request.form.getlist('promo_discount[]')
                    max_uses_list = request.form.getlist('max_uses[]')

                    promo_code = promo_code_list[i] if i < len(promo_code_list) else None
                    discount_percent = promo_discount_list[i] if i < len(promo_discount_list) else None
                    max_uses = max_uses_list[i] if i < len(max_uses_list) else None

                    if promo_code and discount_percent and max_uses:
                        new_rule = DiscountRule(
                            event_id=event_id,
                            discount_type='promo_code',
                            discount_percent=float(discount_percent),
                            promo_code=promo_code,
                            max_uses=int(max_uses)
                        )
                        db.session.add(new_rule)

            # Commit changes to the database
            db.session.commit()
            flash('Event updated successfully!', 'success')
            return redirect(url_for('dashboard'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error updating event: {str(e)}', 'danger')
            return redirect(url_for('edit_event', event_id=event_id))

    # GET request handling
    total_tickets_sold = db.session.query(func.sum(Attendee.tickets_purchased))\
        .filter(Attendee.event_id == event_id)\
        .filter(Attendee.payment_status == 'succeeded')\
        .scalar() or 0

    ticket_types = TicketType.query.filter_by(event_id=event_id).all()
    
    for ticket_type in ticket_types:
        tickets_sold = db.session.query(func.sum(Attendee.tickets_purchased))\
            .filter(Attendee.ticket_type_id == ticket_type.id)\
            .filter(Attendee.payment_status == 'succeeded')\
            .scalar() or 0
        ticket_type.tickets_sold = tickets_sold

    if event.enforce_individual_ticket_limits:
        ticket_types_with_limits = ticket_types
        ticket_types_no_limits = []
    else:
        ticket_types_with_limits = []
        ticket_types_no_limits = ticket_types

    custom_questions = {}
    for i in range(1, 11):
        question_key = f'custom_question_{i}'
        custom_questions[question_key] = getattr(event, question_key, '')

    # Retrieve existing discount rules
    discount_rules = DiscountRule.query.filter_by(event_id=event_id).all()
    event.discount_rules = discount_rules  # Attach to event object for easy access in template

    return render_template(
        'edit_event.html',
        event=event,
        ticket_types=ticket_types,
        ticket_types_with_limits=ticket_types_with_limits,
        ticket_types_no_limits=ticket_types_no_limits,
        total_tickets_sold=total_tickets_sold,
        custom_questions=custom_questions
    )

@app.route('/delete_attendee/<int:attendee_id>', methods=['POST'])
@login_required
def delete_attendee(attendee_id):
    attendee = Attendee.query.get_or_404(attendee_id)

    # Ensure the user has permission to delete the attendee
    event = Event.query.get(attendee.event_id)
    if event.user_id != current_user.id:
        flash("You don't have permission to delete this attendee.")
        return redirect(url_for('dashboard'))

    # Delete the attendee
    db.session.delete(attendee)
    db.session.commit()

    flash('Attendee deleted successfully, and ticket availability updated!')
    return redirect(url_for('view_attendees', event_id=event.id))


@app.route('/edit_attendee/<int:attendee_id>', methods=['GET', 'POST'])
@login_required
def edit_attendee(attendee_id):
    attendee = Attendee.query.get_or_404(attendee_id)

    # Ensure the user has permission to edit the attendee
    event = Event.query.get(attendee.event_id)
    if event.user_id != current_user.id:
        flash("You don't have permission to edit this attendee.")
        return redirect(url_for('dashboard'))

    # Load ticket answers
    ticket_answers = json.loads(attendee.ticket_answers) if attendee.ticket_answers else {}

    if request.method == 'POST':
        # Update attendee details
        attendee.full_name = request.form['full_name']
        attendee.email = request.form['email']
        attendee.phone_number = request.form['phone_number']

        # Update ticket answers
        updated_ticket_answers = {}
        for question in ticket_answers:
            answer_key = f'answer_{question}'
            updated_ticket_answers[question] = request.form.get(answer_key, '')

        # Save the updated ticket answers as JSON
        attendee.ticket_answers = json.dumps(updated_ticket_answers)

        # Commit changes
        db.session.commit()
        flash('Attendee details and ticket answers updated successfully!')
        return redirect(url_for('view_attendees', event_id=event.id))

    return render_template('edit_attendee.html', attendee=attendee, ticket_answers=ticket_answers)

@app.route('/add_attendee/<int:event_id>', methods=['GET', 'POST'])
@login_required
def add_attendee(event_id):
    event = Event.query.get_or_404(event_id)
    
    if event.user_id != current_user.id:
        flash("You don't have permission to add attendees to this event.")
        return redirect(url_for('dashboard'))

    # Get ticket types for the event
    ticket_types = TicketType.query.filter_by(event_id=event_id).all()
    
    # Get questions
    user = User.query.get(event.user_id)
    default_questions = DefaultQuestion.query.filter_by(user_id=user.id).all()
    default_question_texts = [dq.question for dq in default_questions]
    
    custom_questions = []
    for i in range(1, 11):
        question = getattr(event, f'custom_question_{i}')
        if question:
            custom_questions.append(question)
    
    all_questions = default_question_texts + custom_questions

    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone_number = request.form.get('phone_number')
        ticket_type_id = request.form.get('ticket_type')
        number_of_tickets = int(request.form.get('number_of_tickets', 1))

        # Collect answers for each ticket
        ticket_answers = []
        for ticket_num in range(1, number_of_tickets + 1):
            answers = {}
            for q_index, question in enumerate(all_questions, 1):
                answer = request.form.get(f'ticket_{ticket_num}_question_{q_index}')
                if not answer:
                    flash(f'Please answer all questions for Ticket #{ticket_num}')
                    return redirect(url_for('add_attendee', event_id=event_id))
                answers[question] = answer
            ticket_answers.append(answers)

        # Create attendee record
        ticket_type = TicketType.query.get(ticket_type_id)
        ticket_number = generate_unique_ticket_number()

        attendee = Attendee(
            event_id=event_id,
            ticket_type_id=ticket_type_id,
            full_name=full_name,
            email=email,
            phone_number=phone_number,
            tickets_purchased=number_of_tickets,
            ticket_price_at_purchase=ticket_type.price,
            payment_status='succeeded',
            session_id='MANUAL_ENTRY',
            ticket_answers=json.dumps(ticket_answers),
            ticket_number=ticket_number,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(attendee)
        db.session.commit()

        flash(f"Attendee added successfully with ticket number: {ticket_number}")
        return redirect(url_for('view_attendees', event_id=event_id))

    return render_template('add_attendee.html', 
                         event=event, 
                         questions=all_questions,
                         ticket_types=ticket_types)


def send_email_to_organizer(attendee):
    try:
        event = Event.query.get(attendee.event_id)
        organizer = User.query.get(event.user_id)

        # Prepare email content
        subject = f"New Attendee Added to Your Event: {event.name}"
        body = f"""
        Hello {organizer.business_name},

        A new attendee has been added to your event '{event.name}'.

        Attendee Details:
        Full Name: {attendee.full_name}
        Email: {attendee.email}
        Phone Number: {attendee.phone_number}
        Tickets Purchased: {attendee.tickets_purchased}

        You can view all attendees here: {url_for('view_attendees', event_id=event.id, _external=True)}

        Best regards,
        TicketRush Team
        """

        msg = Message(
            subject=subject,
            recipients=[organizer.email],
            body=body
        )
        mail.send(msg)
        print(f"Notification email sent to organizer {organizer.email}.")
    except Exception as e:
        print(f"Failed to send email to organizer {organizer.email}. Error: {str(e)}")


@app.route('/export_attendees/<int:event_id>')
@login_required
def export_attendees(event_id):
    event = Event.query.get_or_404(event_id)

    # Ensure the user has permission to export the attendees
    if event.user_id != current_user.id:
        flash("You don't have permission to export the attendees for this event.")
        return redirect(url_for('dashboard'))

    # Fetch only attendees with successful payments
    attendees = Attendee.query.filter_by(
        event_id=event_id,
        payment_status='succeeded'
    ).all()

    # Prepare data for export
    data = []
    for attendee in attendees:
        attendee_data = {
            'Full Name': attendee.full_name,
            'Email': attendee.email,
            'Phone Number': attendee.phone_number,
            'Tickets Purchased': attendee.tickets_purchased,
            'Ticket Price': attendee.ticket_price_at_purchase,
            'Billing Details': attendee.billing_details,
            'Ticket Answers': json.loads(attendee.ticket_answers) if attendee.ticket_answers else {},
            'Check-in Status': 'Checked In' if getattr(attendee, 'checked_in', False) else 'Not Checked In',
            'Check-in Time': getattr(attendee, 'check_in_time', None)
        }
        data.append(attendee_data)

    # Create a DataFrame using pandas
    df = pd.DataFrame(data)

    # Convert the 'Ticket Answers' dictionary into separate columns
    ticket_answers_df = pd.json_normalize(df['Ticket Answers'])
    df = pd.concat([df.drop(columns='Ticket Answers'), ticket_answers_df], axis=1)

    # Generate the file name using the event name and date
    event_name_clean = re.sub(r'\W+', '_', event.name)  # Replace spaces and special characters with underscores
    event_date = event.date.replace('-', '_')  # Replace dashes with underscores in the date
    file_name = f"attendees_{event_name_clean}_{event_date}.xlsx"

    # Generate the Excel file in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Attendees')

    output.seek(0)

    # Return the Excel file as a response
    response = make_response(output.read())
    response.headers['Content-Disposition'] = f'attachment; filename={file_name}'
    response.headers['Content-type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return response

@app.route('/stripe_onboarding_complete')
def stripe_onboarding_complete():
    # Get the account ID and user ID from the query parameters
    account_id = request.args.get('account')
    user_id = request.args.get('user_id')

    # Debug logs to track what's being received
    print(f"Received user_id: {user_id}")
    print(f"Received account_id: {account_id}")

    # Check if both account_id and user_id are present
    if account_id and user_id:
        # Fetch the user from the database by user_id
        user = User.query.get(user_id)
        if user:
            print(f"User found: {user.email}")

            # Save the Stripe account ID to the user's row
            user.stripe_connect_id = account_id
            db.session.commit()  # Commit changes to the database
            print(f"Stripe Connect ID {account_id} saved for user {user.email}")

            # Fetch the account details from Stripe to check onboarding status
            try:
                stripe_account = stripe.Account.retrieve(account_id)
                # Update the onboarding status based on the Stripe account details
                onboarding_status = "complete" if stripe_account.details_submitted else "pending"
                user.onboarding_status = onboarding_status
                db.session.commit()  # Commit the updated onboarding status to the database
                print(f"Onboarding status updated to {onboarding_status} for user {user.email}")

                # Send welcome email if onboarding is complete
                if onboarding_status == "complete":
                    send_welcome_email(user)
                    flash("Stripe onboarding complete! A welcome email has been sent.", "success")

            except Exception as e:
                print(f"Error fetching account details from Stripe: {str(e)}")
                flash('Error verifying Stripe onboarding status. Please try again later.')

            # Redirect to login page after onboarding
            return redirect(url_for('login'))
        else:
            print("User not found.")
            flash('User not found.')
            return redirect(url_for('register'))
    else:
        print("Stripe onboarding failed: Missing account_id or user_id.")
        flash('Stripe onboarding failed. Please try again.')
        return redirect(url_for('register'))





@app.route('/stripe_onboarding_refresh')
def stripe_onboarding_refresh():
    # Optionally, provide logic here to regenerate the onboarding link
    flash('Please complete the onboarding process.')
    return redirect(url_for('register'))

##

@app.template_filter('datetimeformat')
def datetimeformat(value):
    if value:
        if isinstance(value, str):
            # If it's a string, parse it first
            return datetime.strptime(value, '%Y-%m-%d').strftime('%d-%m-%Y')
        else:
            # If it's already a datetime object, just format it
            return value.strftime('%d-%m-%Y')
    return ""

from flask import render_template, request, redirect, url_for
import qrcode
import base64
from io import BytesIO

@app.route('/success')
def success():
    session_id = request.args.get('session_id')
    if not session_id:
        return "Invalid session. Unable to retrieve booking details.", 400

    # Fetch the attendee(s) associated with this session_id
    attendees = Attendee.query.filter_by(session_id=session_id, payment_status='succeeded').all()
    if not attendees:
        return "No booking found for this session.", 404

    # Assuming all attendees are for the same event
    event = Event.query.get(attendees[0].event_id)
    organizer = User.query.get(event.user_id)

    # Calculate total tickets purchased
    total_tickets = len(attendees)

    # Generate QR codes for each ticket
    qr_codes = []
    for attendee in attendees:
        qr_data = attendee.ticket_number  # Data for QR code (the unique ticket number)
        qr_img = qrcode.make(qr_data)

        # Convert the QR code image to base64 to embed in HTML
        buffer = BytesIO()
        qr_img.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        qr_codes.append(qr_base64)  # Append each QR code to the list

    # Prepare data to pass to the template
    context = {
        'event': event,
        'organizer': organizer,
        'attendee': attendees[0],  # Assumes buyer's details are the same
        'total_tickets': total_tickets,
        'qr_codes': qr_codes  # Pass the list of QR codes as base64 strings
    }

    return render_template('success.html', **context)



def send_welcome_email(user):
    try:
        msg = Message(
            subject="Welcome to TicketRush!",
            sender="no-reply@ticketrush.io",
            recipients=[user.email]
        )
        msg.html = f"""
        <html>
        <body style="background-color: #ffffff; color: #333333; font-family: Arial, sans-serif; padding: 20px;">
            <div style="text-align: center; margin-bottom: 20px;">
                <img src="http://ticketrush.io/wp-content/uploads/2024/10/TicketRush-Logo.png" alt="TicketRush Logo" style="max-width: 200px;">
            </div>
            <h2 style="color: #ff0000;">Welcome to TicketRush, {user.first_name}!</h2>
            <p>We're thrilled to have you on board! Since you've joined TicketRush, you're all set to start creating memorable events with our simple and secure ticketing platform.</p>
            <p><strong>Access Your Dashboard:</strong> <a href="https://bookings.ticketrush.io/manage_default_questions" style="color: #ff0000;" target="_blank">Login Here</a></p>
            <p>To help you get started, take a look at our <a href="https://www.ticketrush.io/support" style="color: #ff0000;" target="_blank">Tutorials Page</a>. It's full of tips to make the most out of your TicketRush experience.</p>
            <p>We can't wait to see the incredible events you create!</p>
            <p>Happy Ticketing!<br>— The TicketRush Team</p>
        </body>
        </html>
        """
        mail.send(msg)
        print("Welcome email sent successfully!")
    except Exception as e:
        print(f"Failed to send welcome email: {str(e)}")

@app.route('/reset_request', methods=['GET', 'POST'])
def reset_request():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            send_reset_email(user)
            flash('An email has been sent with instructions to reset your password.', 'info')
        else:
            flash('If an account with that email exists, a reset link has been sent.', 'info')
        return redirect(url_for('login'))

    return render_template('reset_request.html')

def send_reset_email(user):
    """
    Sends a password reset email with a secure token link.
    :param user: User object containing email and token generation method.
    """
    # Generate a token for password reset
    token = user.get_reset_token()

    try:
        # Create the reset email message
        msg = Message(
            subject="Password Reset Request",
            sender=app.config['MAIL_DEFAULT_SENDER'],  # Use the default sender from config
            recipients=[user.email]
        )

        # HTML version of the email body
        msg.html = f"""
        <html>
        <body style="background-color: #ffffff; color: #333333; font-family: Arial, sans-serif; padding: 20px;">
            <!-- TicketRush Logo -->
            <div style="text-align: center; margin-bottom: 20px;">
                <img src="https://ticketrush.io/wp-content/uploads/2024/10/logo_T-1.png" alt="TicketRush Logo" style="max-width: 200px;">
            </div>

            <!-- Reset Password Heading -->
            <h2 style="color: #ff0000;">Password Reset Request</h2>
            <p>
                Hi {user.first_name},<br>
                We received a request to reset your password. Click the button below to reset your password. If you did not request this, please ignore this email.
            </p>

            <!-- Reset Password Button -->
            <div style="text-align: center; margin: 20px 0;">
                <a href="{url_for('reset_password', token=token, _external=True)}" style="display: inline-block; background-color: #ff0000; color: #ffffff; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    Reset Password
                </a>
            </div>

            <p>
                Alternatively, you can copy and paste the following URL into your browser:
                <br><a href="{url_for('reset_password', token=token, _external=True)}" style="color: #ff0000;">{url_for('reset_password', token=token, _external=True)}</a>
            </p>

            <!-- Footer Section -->
            <hr style="border: 1px solid #ff0000;">
            <p style="font-size: 0.9em; color: #666666;">
                <strong>Need Assistance?</strong> Contact our support team at 
                <a href="mailto:support@ticketrush.io" style="color: #ff0000;">support@ticketrush.io</a>.
            </p>
        </body>
        </html>
        """

        # Plain-text version of the email body
        msg.body = f"""Hi {user.first_name},

We received a request to reset your password. To reset your password, visit the following link:
{url_for('reset_password', token=token, _external=True)}

If you did not make this request, you can ignore this email, and no changes will be made.

Need Assistance? Contact our support team at support@ticketrush.io.
"""

        # Send the email
        mail.send(msg)
        print("Password reset email sent successfully!")

    except Exception as e:
        print(f"Failed to send password reset email: {str(e)}")


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.verify_reset_token(token)
    if not user:
        flash('The token is invalid or has expired.', 'warning')
        return redirect(url_for('reset_request'))

    if request.method == 'POST':
        password = request.form.get('password')
        user.password = generate_password_hash(password)
        db.session.commit()

        # Send a confirmation email after successful reset
        send_password_reset_confirmation(user)

        flash('Your password has been updated!', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html')



def send_password_reset_confirmation(user):
    """
    Sends a confirmation email to the user after a successful password reset.
    :param user: User object containing email and other user details.
    """
    try:
        msg = Message(
            subject="Your Password Has Been Reset",
            sender=app.config['MAIL_DEFAULT_SENDER'],
            recipients=[user.email]
        )

        # HTML version of the email body
        msg.html = f"""
        <html>
        <body style="background-color: #ffffff; color: #333333; font-family: Arial, sans-serif; padding: 20px;">
            <!-- TicketRush Logo -->
            <div style="text-align: center; margin-bottom: 20px;">
                <img src="http://ticketrush.io/wp-content/uploads/2024/10/TicketRush-Logo.png" alt="TicketRush Logo" style="max-width: 200px;">
            </div>

            <!-- Confirmation Message -->
            <h2 style="color: #ff0000;">Password Reset Successful</h2>
            <p>
                Hi {user.first_name},<br>
                Your password has been successfully reset. You can now log in using your new password.
            </p>

            <p>
                If you did not request this change, please contact our support team immediately at 
                <a href="mailto:support@ticketrush.io" style="color: #ff0000;">support@ticketrush.io</a>.
            </p>

            <hr style="border: 1px solid #ff0000;">
            <p style="font-size: 0.9em; color: #666666;">
                Thanks for using TicketRush!<br>
                — The TicketRush Team
            </p>
        </body>
        </html>
        """

        # Plain-text version of the email body
        msg.body = f"""Hi {user.first_name},

Your password has been successfully reset. You can now log in using your new password.

If you did not request this change, please contact our support team immediately at support@ticketrush.io.

Thanks for using TicketRush!
— The TicketRush Team
"""

        # Send the email
        mail.send(msg)
        print("Password reset confirmation email sent successfully!")

    except Exception as e:
        print(f"Failed to send password reset confirmation email: {str(e)}")


@app.route('/create_webpage/<int:event_id>')
@login_required
def create_webpage(event_id):
    # Query the database for the event by its ID
    event = Event.query.get_or_404(event_id)

    # Render the create_webpage template with the event details
    return render_template('create_webpage.html', event=event)

# In app.py

@app.route('/submit_webpage_request/<int:event_id>', methods=['POST'])
def submit_webpage_request(event_id):
    event = Event.query.get(event_id)

    # Get files and additional information from the form
    business_logo = request.files.get('business_logo')
    event_picture = request.files.get('event_picture')
    additional_text = request.form.get('additional_text')

    # Prepare the email content
    subject = f"New Webpage Request for Event: {event.name}"
    body = f"""
    A new webpage request has been submitted for the event "{event.name}".\n
    Event details:
    Name: {event.name}
    Date: {event.date}
    Location: {event.location}
    Description: {event.description}
    Start Time: {event.start_time}
    End Time: {event.end_time}
    
    Additional text from user:
    {additional_text}
    """

    # Prepare the email
    msg = Message(
        subject=subject,
        recipients=["support@ticketrush.io"],
        body=body
    )

    # Attach files to the email if they exist
    if business_logo:
        msg.attach(
            filename=business_logo.filename,
            content_type=business_logo.content_type,
            data=business_logo.read()
        )

    if event_picture:
        msg.attach(
            filename=event_picture.filename,
            content_type=event_picture.content_type,
            data=event_picture.read()
        )

    try:
        # Send the email
        mail.send(msg)
        flash("Your webpage request has been submitted. Please allow up to 48 hours for processing.", "success")
        return redirect(url_for('dashboard'))

    except Exception as e:
        print(f"Error sending email: {str(e)}")
        flash("There was an error processing your request. Please try again later.", "error")
        return redirect(url_for('create_webpage', event_id=event_id))


def send_webpage_request_email(event, additional_text, attachments):
    try:
        subject = f"New Webpage Request for Event: {event.name}"
        body = f"""
        <html>
        <body>
            <h2>New Webpage Request Submitted</h2>
            <p>A new webpage request has been submitted for the following event:</p>
            <h3>Event Details:</h3>
            <p>
                <strong>Name:</strong> {event.name}<br>
                <strong>Date:</strong> {event.date}<br>
                <strong>Location:</strong> {event.location}<br>
                <strong>Description:</strong> {event.description}<br>
                <strong>Start Time:</strong> {event.start_time}<br>
                <strong>End Time:</strong> {event.end_time}<br>
                <strong>Additional Text:</strong> {additional_text or 'N/A'}
            </p>
            <p>Please ensure this request is processed within 48 hours.</p>
            <p><strong>TicketRush Support Team</strong></p>
        </body>
        </html>
        """

        # Create and send the email
        msg = Message(
            subject=subject,
            recipients=["support@ticketrush.io"],
            body=body,
            html=body
        )

        # Attach files to the email
        for attachment in attachments:
            with open(attachment, 'rb') as f:
                msg.attach(os.path.basename(attachment), "image/*", f.read())

        mail.send(msg)
        print(f"Webpage request email sent for event '{event.name}' to support@ticketrush.io.")
        
    except Exception as e:
        print(f"Failed to send webpage request email. Error: {str(e)}")
    finally:
        # Optionally, clean up files if stored temporarily
        for filepath in attachments:
            os.remove(filepath)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_unique_ticket_number():
    characters = string.ascii_uppercase + string.digits
    while True:
        ticket_number = ''.join(random.choice(characters) for _ in range(20))
        existing_ticket = Attendee.query.filter_by(ticket_number=ticket_number).first()
        if not existing_ticket:
            return ticket_number




@app.route('/resend_ticket/<int:attendee_id>', methods=['POST'])
@login_required
def resend_ticket(attendee_id):
    attendee = Attendee.query.get_or_404(attendee_id)
    event = Event.query.get(attendee.event_id)

    # Ensure the user has permission to resend tickets
    if event.user_id != current_user.id:
        flash("You don't have permission to resend tickets for this attendee.")
        return redirect(url_for('dashboard'))

    # Fetch organizer and billing details
    organizer = User.query.get(event.user_id)
    billing_details = json.loads(attendee.billing_details) if attendee.billing_details else {}

    # Resend the confirmation email
    send_confirmation_email_to_attendee([attendee], billing_details)

    flash(f"Ticket has been resent to {attendee.email}.")
    return redirect(url_for('view_attendees', event_id=event.id))



def upload_to_s3(file, folder_prefix="event-logos"):
    unique_suffix = uuid.uuid4().hex
    filename = f"{unique_suffix}_{secure_filename(file.filename)}"
    s3_filename = f"{folder_prefix}/{filename}"

    try:
        # Remove the "ACL" parameter
        s3.upload_fileobj(
            file,
            S3_BUCKET_NAME,
            s3_filename,
            ExtraArgs={"ContentType": file.content_type}  # Only specify ContentType
        )
        return f"https://{S3_BUCKET_NAME}.s3.{os.getenv('AWS_REGION')}.amazonaws.com/{s3_filename}"
    except NoCredentialsError:
        print("S3 credentials not available")
        return None

@app.route('/event/<int:event_id>/scanner')
def start_event_scanner(event_id):
    event = Event.query.get_or_404(event_id)
    
    # Get all attendees for this event
    attendees = Attendee.query.filter_by(
        event_id=event_id,
        payment_status='succeeded'
    ).all()
    
    # Calculate statistics
    total_attendees = len(attendees)
    checked_in = sum(1 for a in attendees if getattr(a, 'checked_in', False))
    
    # Get ticket types if using individual limits
    if event.enforce_individual_ticket_limits:
        event.ticket_types = TicketType.query.filter_by(event_id=event_id).all()
    
    return render_template('event_scanner.html',
                             event=event,
                             total_attendees=total_attendees,
                             checked_in=checked_in)

@app.route('/api/check-in/<int:event_id>', methods=['POST'])
@login_required
def check_in_attendee(event_id):
    event = Event.query.get_or_404(event_id)
    
    # Check if user owns this event
    if event.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    ticket_number = request.json.get('ticket_number')
    if not ticket_number:
        return jsonify({'error': 'No ticket number provided'}), 400
        
    attendee = Attendee.query.filter_by(
        event_id=event_id,
        ticket_number=ticket_number,
        payment_status='succeeded'
    ).first()
    
    if not attendee:
        return jsonify({
            'status': 'error',
            'message': 'Invalid ticket'
        }), 404
        
    if getattr(attendee, 'checked_in', False):
        return jsonify({
            'status': 'warning',
            'message': 'Already checked in',
            'attendee': {
                'name': attendee.full_name,
                'check_in_time': attendee.check_in_time.strftime('%H:%M:%S'),
                'ticket_type': attendee.ticket_type.name
            }
        })
    
    # Update check-in status
    attendee.checked_in = True
    attendee.check_in_time = datetime.now()
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Check-in successful',
        'attendee': {
            'name': attendee.full_name,
            'ticket_type': attendee.ticket_type.name
        },
        'stats': {
            'total_checked_in': Attendee.query.filter_by(
                event_id=event_id,
                checked_in=True
            ).count(),
            'total_attendees': Attendee.query.filter_by(
                event_id=event_id,
                payment_status='succeeded'
            ).count()
        }
    })

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/verify_promo_code', methods=['POST'])
def verify_promo_code():
    try:
        data = request.get_json()
        event_id = data.get('event_id')
        promo_code = data.get('promo_code')

        if not event_id or not promo_code:
            return jsonify({
                'valid': False,
                'message': 'Missing event ID or promo code'
            })

        # Find the discount rule for this promo code
        discount_rule = DiscountRule.query.filter_by(
            event_id=event_id,
            discount_type='promo_code',
            promo_code=promo_code
        ).first()

        if not discount_rule:
            return jsonify({
                'valid': False,
                'message': 'Invalid promo code'
            })

        # Check if the promo code has reached its maximum uses
        if discount_rule.max_uses and discount_rule.uses_count >= discount_rule.max_uses:
            return jsonify({
                'valid': False,
                'message': 'This promo code has expired'
            })

        # Return success with discount percentage
        return jsonify({
            'valid': True,
            'discount': discount_rule.discount_percent
        })

    except Exception as e:
        print(f"Error verifying promo code: {str(e)}")
        return jsonify({
            'valid': False,
            'message': 'Error checking promo code'
        }), 500


@app.route('/reset_sequences', methods=['POST'])
@login_required
def reset_sequences():
    try:
        # Ensure only admin users can access this route
        if not current_user.is_admin:
            return "Unauthorized", 403

        with db.engine.connect() as connection:
            result = connection.execute(
                text("SELECT setval('event_id_seq', COALESCE((SELECT MAX(id) FROM event), 1))")
            )
        return "Sequences reset successfully"
    except Exception as e:
        app.logger.error(f"Error resetting sequences: {str(e)}")
        return f"Error resetting sequences: {str(e)}", 500

    
if __name__ == "__main__":
    app.run(debug=True)


    