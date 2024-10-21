from flask import Blueprint, flash, redirect, url_for
from flask_login import login_required
from app import db

# Create a blueprint for admin functions
admin_blueprint = Blueprint('admin', __name__)

# Route to reset the database
@admin_blueprint.route('/reset_db')
@login_required  # You may want to replace this with a custom admin check
def reset_db():
    try:
        # Drop all the tables
        db.drop_all()
        
        # Recreate all the tables
        db.create_all()
        
        # Provide feedback to the admin user
        flash('Database reset and tables recreated successfully!', 'success')
        
    except Exception as e:
        # In case of an error, show a failure message
        flash(f'An error occurred while resetting the database: {str(e)}', 'danger')
    
    # Redirect back to the home page or dashboard after reset
    return redirect(url_for('home'))  # Change 'home' to your desired redirection route
