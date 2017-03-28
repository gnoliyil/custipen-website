# -*- coding: utf-8 -*-

import os
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
        render_template, flash, make_response, jsonify

import datetime
import random
from hashlib import sha1
from captcha.image import ImageCaptcha
from string import letters

UPLOAD_FOLDER = './uploads/'

app = Flask(__name__)
app.config.from_object(__name__)

# load default config and overwrite config from an env var
app.config.update({
        'DATABASE': os.path.join(app.root_path, 'users.db'), 
        'SECRET_KEY': 'development key', 
        'USERNAME': 'admin', 
        'PASSWORD': 'default',
        'UPLOAD_FOLDER': UPLOAD_FOLDER
})
app.config.from_envvar('FLASKR_SETTINGS', silent=True)

def make_dicts(cursor, row):
    return dict((cursor.description[idx][0], value)
                for idx, value in enumerate(row))

def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = make_dicts
    return rv

def get_db():
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db()

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()



# views

@app.route('/')
def home():
    return render_template('index.html', active="index")

@app.route('/travel/')
def travel():
    return render_template('travel.html', active="travel")

@app.route('/program/')
def program():
    return render_template('program.html', active="program")

@app.route('/committee/')
def committee():
    return render_template('committee.html', active="committee")

@app.route('/photos/<page>')
def photos(page=1):
    db = get_db()
    cur = db.execute('SELECT url, caption, upload_time FROM photos ORDER BY \'order\''
                    ' OFFSET ? LIMIT ?', ((page - 1)*20, 20))
    entries = cur.fetchall()
    return render_template('photos.html', active="photos",
                           page=page, entries=entries)

@app.route('/register/')
def register():
    if request.method == "POST":
        # update form
        form = request.form

        # check captcha
        captcha = request.form['captcha']
        answer = session['chars']
        correct = (answer and
                   ''.join(answer).capitalize() == request.args.get('ans').capitalize()) \
                  and 1 or 0
        if not correct:
            return render_template('register.html', action='register', error_msg='Captcha error')

        # check if the user exists
        db = get_db()
        cur = db.execute('SELECT * FROM users WHERE email = ?', (form['email'], ))
        if cur.fetchone():
            return render_template('register.html', active='register',
                                   error_msg='This email has been already registered, '
                                             'please log-in to modify your information.')
        else:
            if request.files:
                file = request.files['talk_file']

                if not file.name.endswith('.pdf') or file.size > 5000 * 1024:
                    return render_template('register.html', active=register,
                                   error_msg='Please upload PDF file less than 5MB.')

                basename = form['first_name'] + '_' + form['last_name'] + '_' + form['talk_title']
                basename = filter(lambda x: x.isalnum() or x == '_', basename)
                filename = basename + '.pdf'

                talk_url = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(talk_url)
            else:
                talk_url = ''
            cur = db.execute(
                'INSERT INTO users(first_name, last_name, email, institution, '
                'address, arrival_time, departure_time, is_talk, talk_title, talk_url, '
                'is_visa, visa_fullname, visa_citizenship, visa_gender, visa_passport_id, '
                'visa_dob, visa_relation, visa_dep_fullname, visa_dep_citizenship, '
                'visa_dep_gender, visa_dep_passport_id, visa_dep_dob, submit_time, '
                'password_hash) VALUES '
                '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?,'
                ' ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,'
                ' ?, ?, ?, ?); ',
                (
                    form['first_name'], form['last_name'], form['email'],
                    form['institution'], form['address'], form['arrival_time'],
                    form['departure_time'], form['is_talk'], form['talk_title'],
                    talk_url, form['is_visa'], form['visa_fullname'], form['visa_citizenship'],
                    form['visa_gender'], form['visa_passport_id'], form['visa_dob'], form['visa_relation'],
                    form['visa_dep_fullname'], form['visa_dep_citizenship'], form['visa_dep_gender'],
                    form['visa_dep_passport_id'], form['visa_dep_dob'], datetime.datetime.now().isoformat(),
                    ''
                )
            )
            cur.commit()

            session['logged_in'] = cur.lastrowid
            return redirect(url_for('home'))
    else:
        return render_template('register.html', active='register')


@app.route('/edit/')
def edit():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == "POST":
        # update form
        form = request.form

        user_id = session['logged_in']

        # check captcha
        captcha = request.form['captcha']
        answer = session['chars']
        correct = (answer and
                   ''.join(answer).capitalize() == request.args.get('ans').capitalize()) \
                  and 1 or 0
        if not correct:
            return render_template('edit.html', action='edit', error_msg='Captcha error')


        if form['is_file_update'] and request.files:
            file = request.files['talk_file']

            if not file.name.endswith('.pdf') or file.size > 5000 * 1024:
                return render_template('edit.html', active='edit',
                                       error_msg='Please upload PDF file less than 5MB.')

            basename = form['first_name'] + '_' + form['last_name'] + '_' + form['talk_title']
            basename = filter(lambda x: x.isalnum() or x == '_', basename)
            filename = basename + '.pdf'

            talk_url = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(talk_url)
        else:
            talk_url = ''

        db = get_db()
        cur = db.execute(
            'UPDATE users SET first_name = ?, last_name = ?, email = ?, institution = ?, '
            'address = ?, arrival_time = ?, departure_time = ?, is_talk = ?, talk_title = ?, '
            'talk_url = ?, is_visa = ?, visa_fullname = ?, visa_citizenship = ?, visa_gender = ?, '
            'visa_passport_id = ?, visa_dob = ?, visa_relation = ?, visa_dep_fullname = ?, '
            'visa_dep_citizenship = ?, visa_dep_gender = ?, visa_dep_passport_id = ?, '
            'visa_dep_dob = ?, submit_time = ?, password_hash = ? WHERE id = ?; ',
            (
                form['first_name'], form['last_name'], form['email'],
                form['institution'], form['address'], form['arrival_time'],
                form['departure_time'], form['is_talk'], form['talk_title'],
                talk_url, form['is_visa'], form['visa_fullname'], form['visa_citizenship'],
                form['visa_gender'], form['visa_passport_id'], form['visa_dob'], form['visa_relation'],
                form['visa_dep_fullname'], form['visa_dep_citizenship'], form['visa_dep_gender'],
                form['visa_dep_passport_id'], form['visa_dep_dob'], datetime.datetime.now().isoformat(),
                '', user_id
            )
        )
        cur.commit()
    else:
        return render_template('edit.html', active='edit')


@app.route('/captcha/get')
def captcha():
    image = ImageCaptcha(width=90, font_sizes=(40,))
    letters = 'abcdefhjklmnpqrstuvwxyz2345678'
    chars = random.sample(letters, 4)
    data = image.generate(chars).getvalue()
    session['chars'] = chars

    response = make_response(data)
    response.headers['Content-Type'] = 'image/png'
    return response


@app.route('/captcha/check')
def captcha_check():
    answer = session['chars']
    correct = (answer and
               ''.join(answer).capitalize() == request.args.get('ans').capitalize()) \
        and 1 or 0

    response = jsonify({'result': correct})
    return response


@app.route('/login/')
def login():
    if session.get('logged_in'):
        return redirect(url_for('home'))
    else:
        if request.method == 'POST':
            first_name = request.form['first-name'].strip().capitalize()
            last_name  = request.form['last-name'].strip().capitalize()
            dob   = request.form['dob']

            # check captcha
            captcha = request.form['captcha']
            answer = session['chars']
            correct = (answer and
                       ''.join(answer).capitalize() == request.args.get('ans').capitalize()) \
                    and 1 or 0
            if not correct:
                return render_template('login.html', error_msg='Captcha error')

            db = get_db()
            cur = db.execute('SELECT id FROM users WHERE '
                             'UPPER(first_name) = ? AND '
                             'UPPER(last_name)  = ? AND '
                             'dob = ?;', (first_name, last_name, dob))
            line = cur.fetchone()
            if line:
                session['logged_in'] = line['id']
            else:
                return render_template('login.html', error_msg='Name or birthday error')
        else:
            return render_template('login.html')


@app.route('/logout/')
def logout():
    session.pop('logged_in')
    return redirect(url_for('home'))

