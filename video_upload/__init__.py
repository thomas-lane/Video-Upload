from flask import Flask, render_template, request, flash, redirect, url_for, send_from_directory, session, g
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
from video_upload.db import get_db
import os
import secrets
import datetime
import ffmpy
import functools

def create_app(test_config=None):
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'e01b4a031afd5cb903dc395dd66aa14d'
    app.config['UPLOAD_FOLDER'] = os.path.dirname(os.path.realpath(__file__)) + '\\static\\video_uploads'
    app.config['DATABASE'] = os.path.join(app.instance_path, 'videos.db')

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from . import db
    db.init_app(app)

    def get_videos():
        db = get_db()
        return db.execute('''
            SELECT v.id, title, created
            FROM video v
            ORDER BY created DESC
        ''')

    @app.route('/')
    def index():
        return render_template('index.html', videos=get_videos())

    @app.route('/upload', methods=['GET', 'POST'])
    def upload():
        if request.method == 'POST':
            if 'file' not in request.files:
                flash('No file')
                return redirect(url_for('index'))

            file = request.files['file']

            if file.filename == '':
                flash('No file selected')
                return redirect(url_for('index'))

            if file:
                # Save the file
                filename = secure_filename(file.filename)
                name = secrets.token_hex(6)
                title, ext = os.path.splitext(filename)

                file_path = os.path.join(app.config['UPLOAD_FOLDER'], name + ext)

                file.save(file_path)

                if ext[1:].lower() not in ['mp4']:
                    if ext[1:].lower() == 'mov':
                        # Convert mov to mp4
                        ff = ffmpy.FFmpeg(
                            inputs={file_path: None},
                            outputs={os.path.join(app.config['UPLOAD_FOLDER'], name + '.' + 'mp4'): None}
                        )
                        ff.run()
                        ext = '.mp4'
                    else:
                        flash('Incompatible file type')
                        return redirect(url_for('upload'))
                


                # Insert data into the database
                db = get_db()
                db.execute('INSERT INTO video (id, ext, title) VALUES (?, ?, ?)', (name, ext[1:], title))
                db.commit()

                flash('Uploaded video')
                return redirect(url_for('view', id=name))
            
        return render_template('upload.html')

    @app.route('/view', methods=['GET', 'POST'])
    def view():
        if request.method == 'POST':
            if g.user == 'admin':
                db = get_db()
                if 'save' in request.form:
                    # Change the title if the save button is pressed
                    title = request.form['title']
                    db.execute('UPDATE video SET title=? WHERE id=?', (title,request.args.get('id')))
                    db.commit()
                elif 'delete' in request.form:
                    # Remove the video from the database if the delete button is pressed
                    db.execute('DELETE FROM video WHERE id=?', (request.args.get('id'),))
                    db.commit()
                    flash('Video deleted.')
                    return redirect(url_for('index'))
                return redirect(url_for('view', id=request.args.get('id')))


        video = get_db().execute('SELECT id, ext, title, created FROM video WHERE id=?', (request.args.get('id'),)).fetchone()
        if video is None:
            flash('That video does not exist.')
            return redirect(url_for('index'))

        return render_template('view.html', title='View', video=video)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            # The hash is the password 'qwerty' hashed. Probably didn't need to be hashed but oh well.
            if request.form['username'] == 'admin' and check_password_hash('pbkdf2:sha256:150000$F6vAWBGC$c9532e73b8dc5cd9b2f985ec393586def767bb43f7c616f66ff0f838fe6d06b5', request.form['password']):
                session.clear()
                session['username'] = 'admin'
                flash('You have been logged in as admin.')
                return redirect(url_for('index'))
            else:
                flash('Incorrect username or password.')
                return redirect(url_for('login'))
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        session.clear()
        flash('You have been logged out.')
        return redirect(url_for('index'))

    @app.before_request
    def load_user():
        g.user = session.get('username')

    return app