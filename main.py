from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import pymysql.cursors, os
from pymysql import escape_string as thwart
from werkzeug import generate_password_hash, check_password_hash
from wtforms import Form
from werkzeug.utils import secure_filename

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(APP_ROOT, 'static/uploads')
ALLOWED_EXTENSIONS = set(['pdf', 'ppt', 'pptx', 'docx', 'doc'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['SECRET_KEY'] = 'secret'

# Connect to the database
connection = pymysql.connect(host='localhost',
                             user='root',
                             password='',
                             db='resumedeft',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)

@app.route('/')
def index():
	if 'email' in session:
		return redirect(url_for('dashboard'))
	return render_template('index.html')

@app.route('/dashboard')
def dashboard():
	if not 'email' in session:
		return redirect(url_for('index'))
	with connection.cursor() as cur:
		cur.execute("SELECT filename FROM resume WHERE email=(%s)",thwart(session['email']))
		filenames = cur.fetchall()
	connection.commit()
	return render_template('dashboard.html', filenames=filenames)

@app.route('/signup',methods=['POST'])
def signup():
	name = request.form['name']
	email = request.form['email']
	password = generate_password_hash(request.form['password'])
	if not name or not email or not request.form['password']:
		flash('All fields are required')
		return redirect(url_for('index'))
	with connection.cursor() as cur:
		cur.execute("INSERT INTO users (name, email, password) VALUES (%s,%s,%s)",(thwart(name),thwart(email),thwart(password)))
	connection.commit()
	session['email'] = request.form['email']
	session['name'] = request.form['name']
	return redirect(url_for('dashboard'))

@app.route('/login',methods=['POST'])
def login():
	email = request.form['email']
	password = request.form['password']
	if not password or not email:
		flash('All fields are required')
		return redirect(url_for('index'))
	with connection.cursor() as cur:
		cur.execute("SELECT name, password FROM users WHERE email=(%s)",thwart(email))
		data = cur.fetchone()
		passkey = data['password']
		name = data['name']
	connection.commit()
	if check_password_hash(passkey, password):
		session['email'] = request.form['email']
		session['name'] = name
		return redirect(url_for('dashboard'))

	return redirect(url_for('index'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload():
    # check if the post request has the file part
    if 'file' not in request.files:
        flash('Please select a file to Upload!', 'error')
        return redirect(url_for('dashboard'))

    file = request.files['file']
    # if user does not select file, browser submits an empty part without filename
    if file.filename == '':
        flash('Please select a file to Upload!', 'error')
        return redirect(url_for('dashboard'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        with connection.cursor() as cur:
        	cur.execute("INSERT INTO resume (email, filename) VALUES (%s,%s)",(thwart(session['email']),thwart(filename)))
        connection.commit()
        flash('Your Resume has been Uploaded', 'success')
        return redirect(url_for('dashboard'))
    else:
    	flash('Only PDF, PPT and DOC files is accepted', 'error')
    	return redirect(url_for('dashboard'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/logout',methods=['GET'])
def logout():
	session.clear()
	return redirect(url_for('index'))

@app.errorhandler(404)
def Not_Found(e):
	return render_template('404.html'), 404

if __name__ == '__main__':
    app.run()