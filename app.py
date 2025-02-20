import random
import os
from flask import Flask, render_template, request, redirect, make_response, flash, jsonify
from pymongo import MongoClient
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from datetime import datetime
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)

app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])

bcrypt = Bcrypt(app)
socketio = SocketIO(app, cors_allowed_origins="*")

client = MongoClient('localhost', 27017)
db = client['wad']

online_users = set()

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        sessionid = request.cookies.get('sessionid', "")
        session = db.sessions.find_one({'sessionid': sessionid})
        
        if session is not None:
            return redirect('/profile')
        else:
            return render_template('login.html')
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = db.users.find_one({'username': username})
        
        if user and bcrypt.check_password_hash(user['password'], password):
            sessionid = str(random.randint(10**10, 10**20))
            db.sessions.insert_one({
                'sessionid': sessionid,
                'user': user
            })
            resp = make_response(redirect('/profile'))
            resp.set_cookie('sessionid', sessionid)
            return resp
        else:
            flash('Invalid username or password')
            return render_template('login.html')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash('Username and password cannot be empty')
            return redirect('/signup')

        user = db.users.find_one({'username': username})
        if user:
            flash('Email is already exist')
            return redirect('/signup')
        
        else:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            db.users.insert_one({
                'username': username,
                'password': hashed_password,
                'avatar': "default-avatar.png",
                'firstname': "",
                'lastname': "",
                'email': "",
                'address': "",
                'hobbies': "",
                'job': "",
                'skill': ""
            })
            
            sessionid = str(random.randint(10**10, 10**20))
            db.sessions.insert_one({
                'sessionid': sessionid,
                'user': db.users.find_one({'username': username})
            })
            resp = make_response(redirect('/update-profile'))
            resp.set_cookie('sessionid', sessionid)
            return resp
    # return render_template("signup.html")

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    sessionid = request.cookies.get('sessionid', "")
    session = db.sessions.find_one({'sessionid': sessionid})
    # print(session)
    if request.method == 'GET':
        if session is None:
            return redirect('/')
        else:
            # print(session)
            username = session['user']['username']
            user = db.users.find_one({'username': username})
            firstname, lastname, avatar, email, address, hobbies, job, skill = (
                user[key] for key in ["firstname", "lastname", "avatar", "email", "address", "hobbies", "job", "skill"]
            )
            return render_template('profile.html', 
                                   username=username, 
                                   firstname=firstname, 
                                   lastname=lastname,
                                   avatar=avatar,
                                   email=email, address=address, hobbies=hobbies,
                                   job=job, skill=skill
                                )
    
    if request.method == 'POST':
        username = session['user']['username']

        firstname = request.form['firstname']
        lastname = request.form['lastname']
        db.users.update_one(
            {'username': username},
            {
                '$set': {
                    'firstname': firstname,
                    'lastname': lastname
                }
            }
        )
        resp = make_response(redirect('/profile'))
        return resp
    
        
@app.route('/logout')
def logout():
    sessionid = request.cookies.get('sessionid', "")
    db.sessions.find_one_and_delete({'sessionid': sessionid})
    return redirect('/')


@app.route('/update-profile', methods=['GET', 'POST'])
def update_profile():
    sessionid = request.cookies.get('sessionid', "")
    session = db.sessions.find_one({'sessionid': sessionid})
    if request.method == 'GET':
        if session:
            username = session['user']['username']
            user = db.users.find_one({'username': username})
            firstname, lastname, avatar, email, address, hobbies, job, skill = (
                user[key] for key in ["firstname", "lastname", "avatar", "email", "address", "hobbies", "job", "skill"]
            )
            return render_template("update-profile.html",
                                    username=username, 
                                    firstname=firstname, 
                                    lastname=lastname,
                                    avatar=avatar,
                                    email=email, address=address, hobbies=hobbies,
                                    job=job, skill=skill
                                )
        else:
            return redirect('/')
    else:
        username = session['user']['username']
        user = db.users.find_one({'username': username})

        new_firstname = request.form.get('firstname', '')
        new_lastname = request.form.get('lastname', '')
        new_email = request.form.get('email', '')
        new_address = request.form.get('address', '')
        new_hobbies = request.form.get('hobbies', '')
        new_job = request.form.get('job', '')
        new_skill = request.form.get('skill', '')

        update_fields = {}

        if new_firstname:
            update_fields['firstname'] = new_firstname
        if new_lastname:
            update_fields['lastname'] = new_lastname
        if new_email:
            update_fields['email'] = new_email
        if new_address:
            update_fields['address'] = new_address
        if new_hobbies:
            update_fields['hobbies'] = new_hobbies
        if new_job:
            update_fields['job'] = new_job
        if new_skill:
            update_fields['skill'] = new_skill

        if update_fields:
            db.users.update_one(
                {'username': username},
                {'$set': update_fields}
            )
        flash("Profile information update successfully")
        return redirect('/update-profile')

@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    sessionid = request.cookies.get('sessionid', "")
    session = db.sessions.find_one({'sessionid': sessionid})

    if session:
        username = session['user']['username']
        user = db.users.find_one({'username': username})
        firstname, lastname, avatar, job = (
            user[key] for key in ["firstname", "lastname", "avatar", "job"]
        )
        if request.method == "GET":
            return render_template("pass_change.html",
                                        username=username, 
                                        firstname=firstname, 
                                        lastname=lastname,
                                        avatar=avatar,
                                        job=job
                                    )
        else:
            password, new_password, replay_new_pass = (
                request.form[key] for key in ["password", "new-password", "replay-new-pass"]
            )
            old_password = user["password"]
            if bcrypt.check_password_hash(old_password, password):
                if new_password == replay_new_pass:
                    hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
                    db.users.update_one(
                        {'username': username},
                        {
                            '$set': {
                            'password': hashed_password
                        }
                        }
                    )
                    flash("Change password successfully")
                    return redirect('/change-password')
                
                else:
                    flash("Password confirmation doesn't match")
                    return redirect('/change-password')
            else:
                flash("Old password isn't correct")
                return redirect('/change-password')
    else:
        return redirect('/')

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload-image', methods=['POST'])
def upload_image():
    sessionid = request.cookies.get('sessionid', "")
    session = db.sessions.find_one({'sessionid': sessionid})
    username = session['user']['username']
    if request.method == 'POST':
        image = request.files['image']    
        if not image:
            flash("No file part")
            return redirect('/profile')
        if not image.filename:
            flash("No selected file")
            return redirect('/profile') 
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            db.users.update_one(
                {'username' : username},
                {
                    '$set' : {
                        'avatar' : filename,
                    }
                }
            )
            flash("Image uploaded successfully")
            return redirect('/profile')

@socketio.on('new_user')
def new_user(data):
    username = data.get("username")
    # print(f"Người dùng mới đăng ký: {username}")

    emit('notify_new_user', {'message': f'User {username} just registered!'}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
    # app.run(host='localhost', port=5000, debug=True)