from flask import Flask, jsonify, render_template, request, url_for, flash, redirect, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime
import openai
import os
from models import *
from generate_flashcards import generate_questions_and_answers
import utilities

# Initialize the OpenAI API client in order to generate flashcards from txt files:
openai.api_key = os.getenv("api_key")

# create an instance of the Flask class and assigns it to the variable app
app = Flask(__name__, static_url_path='/static', static_folder='static')

# Set a secret key
app.secret_key = 'my_secret_key'

# Initialize the LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return session.query(User).get(int(user_id))


@app.route('/')
def home():
    return redirect(url_for('login'))


# User Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Validate the input
        if not username or not password:
            flash('Both username and password are required.', 'danger')
            return redirect(url_for('register'))

        existing_user = session.query(User).filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('register'))

        # Create a new user
        user = User(username=username, password=password)
        session.add(user)
        session.commit()

        # Retrieve the user's ID
        user_id = user.id

        # Create a default folders for the user
        default_folder = Folder(name='Default Folder', color='blue', user=user_id)
        session.add(default_folder)
        revision_folder = Folder(name='Revise This', color='Red', user=user_id)
        session.add(revision_folder)
        session.commit()

        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


# User Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Validate the input
        if not username or not password:
            flash('Both username and password are required.', 'danger')
            return redirect(url_for('login'))

        user = session.query(User).filter_by(username=username).first()
        if not user or not user.check_password(password):
            flash('Login failed. Please check your username and password.', 'danger')
            return redirect(url_for('login'))

        # Log in the user
        login_user(user)
        flash('Login successful!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('login.html')


# User Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


# Dashboard (Requires login)
@app.route('/dashboard')
@login_required
def dashboard():
    folders = current_user.folders

    # Calculate the sum of scores and count the number of folders with a valid score
    valid_scores = [folder.latest_score for folder in folders if folder.latest_score != -1]
    total_score = sum(valid_scores)
    valid_folder_count = len(valid_scores)

    # Calculate the average score
    overall_score = total_score / valid_folder_count if valid_folder_count > 0 else -1

    # Display the user's points on the dashboard
    user_points = current_user.points

    return render_template('dashboard.html', folders=folders, overall_score=overall_score, user_points=user_points)


# Create Flashcard
@app.route('/create_flashcard', methods=['POST'])
@login_required
def create_flashcard():
    folder_id = request.form['folder_id']
    question = request.form['question']
    answer = request.form['answer']

    if not folder_id:
        # If no folder was chosen, set folder_id to the Default Folder of the current user
        default_folder = session.query(Folder).filter_by(user_id=current_user.id, name='Default Folder').first()
        folder_id = default_folder.id if default_folder else None

    if folder_id:
        flashcard = Flashcard(folder_id=folder_id, question=question, answer=answer)
        session.add(flashcard)
        session.commit()
        flash('Flashcard created successfully!', 'success')

    return redirect(url_for('dashboard'))


# Create Folder
@app.route('/create_folder', methods=['POST'])
@login_required
def create_folder():
    name = request.form['name']
    color = request.form['color']

    folder = Folder(name=name, color=color, user=current_user.id, full_access=True)
    session.add(folder)
    session.commit()
    flash('Folder created successfully!', 'success')
    return redirect(url_for('dashboard'))


# Calculate Exam Date
@app.route('/calculate_exam_date', methods=['POST'])
@login_required
def calculate_exam_date():
    try:
        exam_date = request.form['exam_date']
        exam_date = datetime.strptime(exam_date, '%Y-%m-%d')
        days_left = (exam_date - datetime.now()).days + 1
        return jsonify({'days_left': days_left})
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400


@app.route('/folder/<int:folder_id>', methods=['GET'])
@login_required
def view_folder(folder_id):
    # Fetch the folder by folder_id and its flashcards
    folder = session.query(Folder).get(folder_id)
    flashcards_in_folder = folder.flashcards if folder else []

    if folder:
        return render_template('folder.html', folder=folder, flashcards=flashcards_in_folder)
    else:
        flash("Folder not found.", "danger")
        abort(404)  # Raise a 404 error


@app.route('/study_flashcards/<int:folder_id>', methods=['GET'])
@login_required
def study_flashcards(folder_id):
    # Fetch the folder by folder_id and its flashcards
    folder, flashcards_to_study = utilities.get_folder_and_flashcards(folder_id, session)

    if flashcards_to_study:
        flashcards_data = utilities.fetch_flashcards_data(flashcards_to_study)
        return render_template('study_flashcards.html', flashcards_data=flashcards_data, folder=folder)
    else:
        flash("No flashcards to study.", "info")
        return redirect(url_for('view_folder', folder_id=folder.id))


@app.route('/quiz_flashcards/<int:folder_id>', methods=['GET'])
@login_required
def quiz_flashcards(folder_id):
    # Fetch the folder by folder_id and its flashcards
    folder, flashcards_to_quiz = utilities.get_folder_and_flashcards(folder_id, session)

    # Find the "Revise This" folder
    if current_user:
        revise_this_folder_query = (
            session.query(Folder.id)
                .filter(Folder.user_id == current_user.id, Folder.name == "Revise This")
                .first()
        )
        revise_this_folder = revise_this_folder_query[0] if revise_this_folder_query else None
    else:
        revise_this_folder = None

    if flashcards_to_quiz:
        flashcards_data = utilities.fetch_flashcards_data(flashcards_to_quiz)
        return render_template('quiz_flashcards.html', flashcards_data=flashcards_data, folder=folder_id,
                               revise_this_folder=revise_this_folder)
    else:
        flash("No flashcards to quiz in this folder.", "info")
        return redirect(url_for('view_folder', folder_id=folder.id))


@app.route('/add_flashcard_to_folder', methods=['POST'])
@login_required
def add_flashcard_to_folder():
    try:
        folder_id = int(request.form['folder_id'])
        question = request.form['question']
        answer = request.form['answer']

        # Check if the user has permission to add flashcards to this folder
        folder = session.query(Folder).filter_by(id=folder_id, user=current_user).first()
        if not folder:
            flash('Folder not found or you do not have permission to add flashcards to it.', 'danger')
            abort(400)

        flashcard = Flashcard(folder_id=folder_id, question=question, answer=answer)
        session.add(flashcard)
        session.commit()

        return jsonify({'message': 'Flashcard added successfully.'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/delete_flashcard/<int:flashcard_id>', methods=['POST'])
@login_required
def delete_flashcard(flashcard_id):
    try:
        # Fetch the flashcard by ID
        flashcard = session.query(Flashcard).get(flashcard_id)

        if not flashcard:
            flash('Flashcard not found.', 'danger')
            return redirect(url_for('view_folder', folder_id=flashcard.folder.id))

        # Check if the user has permission to delete the flashcard
        if flashcard.folder.user != current_user:
            flash('You do not have permission to delete this flashcard.', 'danger')
            return redirect(url_for('view_folder', folder_id=flashcard.folder.id))

        # Delete the flashcard
        session.delete(flashcard)
        session.commit()

        flash('Flashcard deleted successfully.', 'success')
        return redirect(url_for('view_folder', folder_id=flashcard.folder.id))

    except Exception as e:
        flash('An error occurred while deleting the flashcard.', 'danger')
        return redirect(url_for('view_folder', folder_id=flashcard.folder.id))


@app.route('/generate_flashcards', methods=['POST'])
@login_required
def create_folder_and_flashcards():
    try:
        # Get folder name, color, and text from the form data
        folder_name = request.form['folder_name']
        folder_color = request.form['folder_color']
        text = request.form['text']

        # Create a new folder
        user_id = current_user.id
        new_folder = Folder(name=folder_name, color=folder_color, user=user_id, full_access=True)
        session.add(new_folder)
        session.commit()

        # Generate flashcards from the provided text
        flashcards_data = generate_questions_and_answers(text)

        # Create flashcards and associate them with the new folder
        for question, answer in flashcards_data:
            flashcard = Flashcard(folder_id=new_folder.id, question=question, answer=answer)
            session.add(flashcard)

        session.commit()

        flash("Folder and flashcards created successfully.", 'success')
        return redirect(url_for('dashboard'))

    except Exception as e:
        flash(str(e), 'danger')
        abort(500)  # Raise a 500 error


@app.route('/change_folder_color/<int:folder_id>', methods=['POST'])
@login_required
def change_folder_color(folder_id):
    new_color = request.form.get('new_color')

    # Fetch the folder by folder_id
    folder = session.query(Folder).get(folder_id)

    if folder:
        # Check if the folder belongs to the current user
        if folder.user_id == current_user.id:
            # Update the folder's color
            folder.color = new_color
            session.commit()
            flash("folder's color changed successfully.", "success")
        else:
            flash("You are not authorized to change the color of this folder.", "danger")
    else:
        flash("Folder not found.", "danger")
        abort(404)  # Raise a 404 error

    return redirect(url_for('view_folder', folder_id=folder.id))


@app.route('/delete_folder/<int:folder_id>', methods=['POST'])
@login_required
def delete_folder(folder_id):
    # Fetch the folder by folder_id
    folder = session.query(Folder).get(folder_id)

    if folder:
        # Check if the folder belongs to the current user
        if folder.user_id == current_user.id:
            # Check if the folder is not one of the default or "Revise This" folders
            if folder.full_access is True:
                # Delete the folder and its associated flashcards
                flashcards_to_delete = folder.flashcards  # Get associated flashcards
                for flashcard in flashcards_to_delete:
                    session.delete(flashcard)
                session.delete(folder)
                session.commit()
                flash("Folder deleted successfully.", "success")
            else:
                flash("You cannot delete this folders.", "info")
        else:
            flash("You are not authorized to delete this folder.", "danger")
    else:
        flash("Folder not found.", "danger")
        abort(404)  # Raise a 404 error

    return redirect(url_for('dashboard'))


@app.route('/change_folder_name/<int:folder_id>', methods=['POST'])
@login_required
def change_folder_name(folder_id):
    # Fetch the folder by folder_id
    folder = session.query(Folder).get(folder_id)

    if folder:
        # Check if the folder belongs to the current user and is not "Revise This" or default
        if folder.user_id == current_user.id:
            if folder.full_access is True:
                new_name = request.form.get('new_name')

                # Check if a new name is provided
                if new_name:
                    folder.name = new_name
                    session.commit()
                    flash("folder's name changed successfully.", "success")
            else:
                flash("You cannot change the name of the default or 'Revise This' folders.", "info")
        else:
            flash("You are not authorized to change the name of this folder.", "danger")
    else:
        flash("Folder not found.", "danger")
        abort(404)  # Raise a 404 error

    return redirect(url_for('view_folder', folder_id=folder.id))


@app.route('/submit_exam_results', methods=['POST'])
@login_required
def submit_exam_results():
    try:
        grade = float(request.form['grade'])
        new_points = int(request.form.get('points', 0))
        folder_id = request.form['folder_id']

        # Update the 'latest_score' of the folder
        folder = session.query(Folder).filter_by(id=folder_id).first()
        if folder:
            folder.latest_score = grade
        # Update the points of the current user
        current_user.points += new_points

        session.commit()

        return jsonify({'message': 'Exam results submitted and points updated successfully'})

    except Exception as e:
        flash(str(e), 'danger')
        abort(500)  # Raise a 500 error


@app.route('/update_flashcard_attempts', methods=['POST'])
@login_required
def update_flashcard_attempts():
    try:
        flashcard_id = request.form.get('flashcard_id')
        attempts = request.form.get('attempts')

        # Fetch the flashcard by ID
        flashcard = session.query(Flashcard).filter_by(id=flashcard_id).first()

        if flashcard:
            # Update the attempts attribute
            flashcard.attempts = attempts
            session.commit()

            return 'Flashcard attempts updated successfully', 200
        else:
            return 'Flashcard not found', 404
    except Exception as e:
        flash(str(e), 'danger')
        abort(500)  # Raise a 500 error


# A handler for 404 errors
@app.errorhandler(404)
def page_not_found(error):
    return render_template('not_found.html'), 404


# A handler for 500 errors
@app.errorhandler(500)
def internal_server_error(error):
    return render_template('internal_error.html'), 500


if __name__ == '__main__':
    app.run(debug=True)
