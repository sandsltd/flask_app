from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import DefaultQuestion  # Ensure DefaultQuestion model is defined

# Create a blueprint for managing default questions
manage_questions_blueprint = Blueprint('manage_questions', __name__)

# Route for managing default questions
@manage_questions_blueprint.route('/manage-default-questions', methods=['GET', 'POST'])
@login_required
def manage_default_questions():
    if request.method == 'POST':
        # Get all the questions from the form
        questions = request.form.getlist('questions[]')
        terms_link = request.form.get('terms_link')  # Get the terms and conditions link

        # Delete existing default questions for this user
        DefaultQuestion.query.filter_by(user_id=current_user.id).delete()

        # Add the new questions
        for question in questions:
            if question.strip():  # Avoid adding empty questions
                new_question = DefaultQuestion(user_id=current_user.id, question=question)
                db.session.add(new_question)

        # Update the user's terms and conditions link if provided
        current_user.terms = terms_link

        # Commit changes to the database
        db.session.commit()

        flash('Default questions and Terms and Conditions updated successfully!')

        # Redirect to the same page to show the updated list
        return redirect(url_for('manage_questions.manage_default_questions'))

    # Retrieve current default questions for the user
    default_questions = DefaultQuestion.query.filter_by(user_id=current_user.id).all()

    return render_template('manage_default_questions.html', questions=default_questions, user=current_user)
