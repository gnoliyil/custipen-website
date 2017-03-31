# -*- coding: utf-8 -*-

import os
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
        render_template, flash, make_response, jsonify, send_from_directory
import datetime
import random
import re
from hashlib import sha1
from smtplib import SMTP
from email.mime.text import MIMEText
from email.Utils import formatdate

from captcha.image import ImageCaptcha
from thumbnail import Thumbnail
from pagination import Pagination
import config

app = Flask(__name__)
app.config.from_object(__name__)

# load default config and overwrite config from an env var
app.config.from_envvar('FLASKR_SETTINGS', silent=True)
app.config.from_object(config.AppConfig)
thumb = Thumbnail(app)


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
    return g.sqlite_db

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

@app.route('/accommodation/')
def accommodation():
    return render_template('accommodation.html', active="accommodation")

@app.route('/program/')
def program():
    return render_template('program.html', active="program")

@app.route('/committee/')
def committee():
    return render_template('committee.html', active="committee")

@app.route('/presentations/')
def presentations():
    return render_template('presentations.html', active="presentations")


PHOTO_PER_PAGE = 18


@app.route('/photos/', defaults={'page': 1})
@app.route('/photos/<int:page>/')
def photos(page):
    db = get_db()
    count = db.execute('SELECT COUNT(*) as cnt FROM photo;').fetchone()['cnt']
    cur = db.execute('SELECT url, caption FROM photo ORDER BY `order`'
                     'LIMIT ? OFFSET ?', (PHOTO_PER_PAGE, (page - 1) * PHOTO_PER_PAGE))
    entries = cur.fetchall()

    pagination = Pagination(page, PHOTO_PER_PAGE, count)
    return render_template('photos.html', active="photos",
                           pagination=pagination, entries=entries)


@app.route('/register/', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        # update form
        form = request.form

        # check captcha
        captcha = request.form['auth_code']
        answer = session['chars']
        correct = (answer and
                   ''.join(answer).capitalize() == captcha.capitalize()) \
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
            if request.files['talk_file']:
                file = request.files['talk_file']
                
                if file.filename:
                    if (not file.filename.endswith('.pdf')):
                        return render_template('register.html', active=register,
                                       error_msg='Please upload PDF file less than 5MB.')

                    basename = form['first_name'] + '_' + form['last_name'] + '_' + form['talk_title']
                    basename = filter(lambda x: x.isalnum() or x == '_', basename)
                    filename = basename + '.pdf'

                    talk_url = os.path.join(app.config['PROJECT_ROOT'], app.config['UPLOAD_FOLDER'], filename)
                    file.save(talk_url)
                else:
                    filename = talk_url = ''
            else:
                filename = talk_url = ''

            cur = db.execute(
                'INSERT INTO users (first_name, last_name, email, institution, dob, address, '
                'arrival_time, departure_time, is_talk, talk_title, talk_url, '
                'submit_time) values (?,?,?,?,?,?,?,?,?,?,?,?)',
                (
                    form['first_name'], form['last_name'], form['email'],
                    form['institution'], form['dob'], form['address'], form['arrival_time'],
                    form['departure_time'], int(form['is_talk']), form['talk_title'],
                    filename, 
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
            db.commit()
            
	    try:
                smtp = SMTP()
                smtp.connect('smtp.163.com', 25)
                smtp.login('custipen@163.com', 'custipen1')
        
                from_addr = 'custipen@163.com'
                to_addr = form['email']
                subj = 'CUSTIPEN Workshop Registration Acknowledgement'
                date = datetime.datetime.now().strftime( " %H:%M" )
                message_text = """
Dear {} {}:
This email is to acknowledge that we received your registration for the 2017 CUSTIPEN workshop at Huzhou, 2017.
Your password is {}. 
We are looking forward to seeing you in the workshop.
If you have any questions, please contact us.

Best wishes,
On behalf of the local organization group

Scientific Secretary: Junchen Pei(custipen@pku.edu.cn)
""".format(form['first_name'], form['last_name'], form['dob'])
                msg = MIMEText(message_text)
                msg['Subject'] = subj
                msg['Date'] = formatdate(localtime=True)
                msg['From'] = from_addr
                msg['To'] = to_addr
                smtp.sendmail(from_addr, to_addr, msg.as_string())

	        smtp.quit()
            except:
	        pass

            session['logged_in'] = cur.lastrowid
            return redirect(url_for('home'))
    else:
        return render_template('register.html', active='register')


@app.route('/edit/', methods=['GET', 'POST'])
def edit():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == "POST":
        # update form
        form = request.form

        user_id = session['logged_in']

        # check captcha
        captcha = request.form['auth_code']
        answer = session['chars']
        correct = (answer and
                   ''.join(answer).capitalize() == captcha.capitalize()) \
                  and 1 or 0
        if not correct:
            return render_template('edit.html', action='edit', error_msg='Captcha error')


        if form['is_new_file'] and request.files:
            file = request.files['talk_file']
            
            if file.filename:
                if not file.name.endswith('.pdf') or file.size > 5000 * 1024:
                    return render_template('edit.html', active='edit',
                                           error_msg='Please upload PDF file less than 5MB.')

                basename = form['first_name'] + '_' + form['last_name'] + '_' + form['talk_title']
                basename = filter(lambda x: x.isalnum() or x == '_', basename)
                filename = basename + '.pdf'

                talk_url = os.path.join(app.config['PROJECT_ROOT'], app.config['UPLOAD_FOLDER'], filename)
                file.save(talk_url)
            
                db = get_db()
                cur = db.execute('UPDATE users SET talk_url = ?', (filename, ))
                cur.commit()

        db = get_db()
        cur = db.execute(
            'UPDATE users SET first_name = ?, last_name = ?, email = ?, institution = ?, '
            'address = ?, arrival_time = ?, departure_time = ?, is_talk = ?, talk_title = ?, '
            'submit_time = ? WHERE id = ?; ',
            (
                form['first_name'], form['last_name'], form['email'],
                form['institution'], form['address'], form['arrival_time'],
                form['departure_time'], form['is_talk'], form['talk_title'],
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                user_id
            )
        )
        db.commit()

        if form['dob']:
            cur = db.execute('UPDATE users SET dob=? WHERE id=?', (form['dob'], user_id))
            db.commit()
    	
        return redirect(url_for('edit'))
    else:
        user_id = session['logged_in']
        db = get_db()
        cur = db.execute('SELECT * from users WHERE id=?', (user_id, ))
        entry = cur.fetchone()
        return render_template('edit.html', active='edit', entry=entry)


@app.route('/captcha/get/')
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


@app.route('/login/', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('home'))
    else:
        if request.method == 'POST':
            first_name = request.form['first_name'].strip().upper()
            last_name  = request.form['last_name'].strip().upper()
            dob   = request.form['dob']

            # check captcha
            captcha = request.form['auth_code']
            answer = session['chars']
            correct = (answer and
                       ''.join(answer).capitalize() == captcha.capitalize()) \
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
                return redirect(url_for('home'))
            else:
                return render_template('login.html', error_msg='Name or birthday error')
        else:
            return render_template('login.html')

@app.route('/logout/')
def logout():
    session.pop('logged_in')
    return redirect(url_for('home'))

@app.route('/participants/')
def participants():
    db = get_db()
    cur = db.execute('SELECT first_name, last_name, institution FROM users')
    entries = cur.fetchall()
    return render_template('participants.html', entries=entries, enumerate=enumerate)


@app.route('/admin/login', methods=['POST', 'GET'])
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('user_info'))
    else:
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']

            # check captcha
            captcha = request.form['auth_code']
            answer = session['chars']
            correct = (answer and
                       ''.join(answer).capitalize() == captcha.capitalize()) \
                      and 1 or 0
            if not correct:
                return render_template('admin/login.html', error_msg='Captcha error')

            if username == app.config['USERNAME'] and \
               password == app.config['PASSWORD']:
                session['admin_logged_in'] = 1
                return redirect(url_for('user_info'))
            else:
                return render_template('admin/login.html', error_msg='Username or password error')
        else:
            return render_template('admin/login.html')


@app.route('/admin/logout/')
def admin_logout():
    if session.get('admin_logged_in'):
        session.pop('admin_logged_in')
    return redirect(url_for('home'))


USER_INFO_PER_PAGE = 20
@app.route('/admin/users/page/<int:page>')
@app.route('/admin/users/', defaults={'page': 1})
@app.route('/admin/', defaults={'page': 1})
def user_info(page):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    db = get_db()
    cur = db.execute('SELECT count(id) FROM USERS;')
    count = int(cur.fetchone()['count(id)'])

    cur = db.execute('SELECT * FROM users LIMIT ? OFFSET ?;',
                     (USER_INFO_PER_PAGE, (page - 1)* USER_INFO_PER_PAGE))
    entries = cur.fetchall()
    pagination = Pagination(page, USER_INFO_PER_PAGE, count)
    return render_template('admin/user.html', entries=entries, pagination=pagination)

#@app.route('/admin/export-csv/')

@app.route('/admin/user/delete/<id>/')
def user_delete(id):
    db = get_db()
    cur = db.execute('DELETE FROM users WHERE id=?', (id,))
    db.commit()
    return redirect(url_for('user_info'))


@app.route('/admin/edit-gallery/')
def edit_gallery():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    db = get_db()
    cur = db.execute('SELECT p.id, p.url, p.caption, (SELECT COUNT(*) from photo b WHERE b."order" <= p."order" ) '
                     'as idx from photo p ORDER BY "order"')
    entries = cur.fetchall()
    return render_template('admin/edit-gallery.html', active='edit-gallery', entries=entries)


@app.route('/admin/photo/delete/<id>')
def photo_delete(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    db = get_db()
    cur = db.execute('SELECT * FROM photo WHERE id=?', (id, ))
    img_name = cur.fetchone()['url']
    cur = db.execute('DELETE FROM photo WHERE id=?', (id, ))
    db.commit()
    os.remove(os.path.join(app.config['PROJECT_ROOT'], app.config['UPLOAD_FOLDER'], img_name))
    return redirect(url_for('edit_gallery'))


@app.route('/admin/photo/upload/', methods=['POST'])
def photo_upload():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    form = request.form
    if request.files:
        print request.files['image_file']

        file = request.files['image_file']

        try:
            fileext = re.findall(r'(\.[^\.]+)', file.filename)[-1]
        except:
            fileext = '.jpg'
        basename = datetime.datetime.now().strftime('%Y%m%d%H%M%S') + str(random.randint(10, 99))
        filename = basename + fileext

        image_url = os.path.join(app.config['PROJECT_ROOT'], app.config['UPLOAD_FOLDER'], 'images', filename) 
        db_image_url = os.path.join('images', filename) 
        file.save(image_url) 

    else:
        return redirect(url_for('edit_gallery'))

    db = get_db()
    cur = db.execute('INSERT INTO photo(url, caption, update_time) VALUES (?, ?, ?)',
                     (db_image_url, form['caption'], datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    db.commit()
    rowid = cur.lastrowid
    cur = db.execute('UPDATE photo SET `order`=? WHERE id=?', (rowid, rowid))
    db.commit()
    return redirect(url_for('edit_gallery'))


@app.route('/admin/photo/move-up/<id>/')
def photo_move_up(id):
    db = get_db()
    cur = db.execute('SELECT `order` FROM photo WHERE id=?', (id,))
    this_order = cur.fetchone()['order']
    cur = db.execute('SELECT id, `order` FROM photo WHERE `order` < ? ORDER BY `order` DESC LIMIT 1', (this_order,))
    dic = cur.fetchone()
    prev_id, prev_order = dic['id'], dic['order']
    cur = db.execute('UPDATE photo SET `order`=? WHERE id=?', (this_order, prev_id))
    cur = db.execute('UPDATE photo SET `order`=? WHERE id=?', (prev_order, id))
    db.commit()
    return redirect(url_for('edit_gallery'))


@app.route('/admin/photo/move-down/<id>/')
def photo_move_down(id):
    db = get_db()
    cur = db.execute('SELECT `order` FROM photo WHERE id=?', (id,))
    this_order = cur.fetchone()['order']
    cur = db.execute('SELECT id, `order` FROM photo WHERE `order` > ? ORDER BY `order` LIMIT 1', (this_order,))
    dic = cur.fetchone()
    next_id, next_order = dic['id'], dic['order']
    cur = db.execute('UPDATE photo SET `order`=? WHERE id=?', (this_order, next_id))
    cur = db.execute('UPDATE photo SET `order`=? WHERE id=?', (next_order, id))
    db.commit()
    return redirect(url_for('edit_gallery'))

@app.route('/admin/user/edit/<int:id>/', methods=['GET', 'POST'])
def user_edit(id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    if request.method == "POST":
        # update form
        form = request.form

        user_id = id

        if form['is_new_file'] and request.files:
            file = request.files['talk_file']
            
            if file.filename:
                if not file.name.endswith('.pdf') or file.size > 5000 * 1024:
                    return render_template('edit.html', active='edit',
                                           error_msg='Please upload PDF file less than 5MB.')

                basename = form['first_name'] + '_' + form['last_name'] + '_' + form['talk_title']
                basename = filter(lambda x: x.isalnum() or x == '_', basename)
                filename = basename + '.pdf'

                talk_url = os.path.join(app.config['PROJECT_ROOT'], app.config['UPLOAD_FOLDER'], filename)
                file.save(talk_url)
            
                db = get_db()
                cur = db.execute('UPDATE users SET talk_url = ?', (filename, ))
                cur.commit()

        db = get_db()
        cur = db.execute(
            'UPDATE users SET first_name = ?, last_name = ?, email = ?, institution = ?, '
            'address = ?, arrival_time = ?, departure_time = ?, is_talk = ?, talk_title = ?, '
            'submit_time = ? WHERE id = ?; ',
            (
                form['first_name'], form['last_name'], form['email'],
                form['institution'], form['address'], form['arrival_time'],
                form['departure_time'], form['is_talk'], form['talk_title'],
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                user_id
            )
        )
        db.commit()

        if form['dob']:
            cur = db.execute('UPDATE users SET dob=? WHERE id=?', (form['dob'], user_id))
            db.commit()
    	
        return redirect(url_for('user_info'))
    else:
        user_id = id
        db = get_db()
        cur = db.execute('SELECT * from users WHERE id=?', (user_id, ))
        entry = cur.fetchone()
        return render_template('admin/user_edit.html', user_id=user_id, active='user_info', entry=entry)


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)
