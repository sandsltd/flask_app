from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager
from app.models import User  # Assuming you have a models.py with User defined

# Create a blueprint for authentication
auth_blueprint = Blueprint('auth', __name__)

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Login route
@auth_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # Query the database for the user
        user = User.query.filter_by(email=email).first()
        
        # Check if user exists and password is correct
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('events.dashboard'))  # Redirect to the dashboard after login
        else:
            flash('Invalid email or password')  # Display error message if login fails
    return render_template('login.html')  # Render the login page

# Logout route
@auth_blueprint.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))  # Redirect to the login page after logging out

# Register route
@auth_blueprint.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
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
        
        # Check if user already exists
        user = User.query.filter_by(email=email).first()
        if user:
            flash("Email already in use")
            return render_template('register.html', error="Email already in use")
        
        # Generate hashed password
        hashed_password = generate_password_hash(password, method='sha256')

        # Create a new user
        new_user = User(
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
            postcode=postcode
        )

        # Add and commit the new user to the database
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully! Please log in.')
        return redirect(url_for('auth.login'))  # Redirect to login page after successful registration
    
    return render_template('register.html')  # Render the registration page
