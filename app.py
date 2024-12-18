from flask import  Flask, render_template, request, redirect, url_for, session, jsonify, flash
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import re

app = Flask(__name__)
app.secret_key = 'your_secret_key'

STUDENT_DB_PATH = 'students.db'
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
 # Use Romanian locale
# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Dummy user credentials
users = {
    "user1": "password1",
    "user2": "password2"
}
USERS_DB_PATH = 'users.db'

def init_users_db():
    with sqlite3.connect(USERS_DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        email TEXT UNIQUE NOT NULL
                    )''')
        conn.commit()

# Initialize the users database
init_users_db()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Trebuie să fii conectat ca să vezi pagina.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_email(email):
    regex = '^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w+$'
    return re.search(regex, email)

def init_db():
    with sqlite3.connect(STUDENT_DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS students (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nume TEXT NOT NULL,
                        prenume TEXT NOT NULL,
                        facultatea TEXT,
                        specializarea TEXT,
                        an INTEGER CHECK(an > 0),
                        grupa TEXT,
                        data_nasterii DATE,
                        cnp TEXT UNIQUE CHECK(length(cnp) == 13),
                        numar_de_telefon TEXT UNIQUE CHECK(numar_de_telefon GLOB '[0-9]*'),
                        email TEXT UNIQUE,
                        adresa TEXT,
                        cetatenie TEXT,
                        etnie TEXT,
                        poza TEXT
                    )''')
        conn.commit()

@app.before_first_request
def initialize():
    init_db()

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        if not validate_email(email):
            return jsonify({"success": False, "message": "Formatul email-ului invalid"})

        password_hash = generate_password_hash(password)
        
        with sqlite3.connect(USERS_DB_PATH) as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE username = ? OR email = ?', (username, email))
            existing_user = c.fetchone()
            if existing_user:
                if existing_user[1] == username:
                    return jsonify({"success": False, "message": "Username-ul deja există"})
                if existing_user[3] == email:
                    return jsonify({"success": False, "message": "Email-ul deja există"})

            c.execute('INSERT INTO users (username, password, email) VALUES (?, ?, ?)', (username, password_hash, email))
            conn.commit()
            return jsonify({"success": True})

    return render_template('signup.html', title='Sign up')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Validate user credentials
        with sqlite3.connect(USERS_DB_PATH) as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
            user = c.fetchone()
            if user:
                session['username'] = username
                return jsonify({"success": True})
            else:
                return jsonify({"success": False, "message": "Invalid credentials"})

    return render_template('login.html', title='Login')

@app.route('/edit_student/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_student(id):
    if request.method == 'POST':
        name = request.form['nume']
        surname = request.form['prenume']
        faculty = request.form['facultatea']
        specialization = request.form['specializarea']
        year = request.form['an']
        group = request.form['grupa']
        birth_date = request.form['data_nasterii']
        cnp = request.form['cnp']
        phone_number = request.form['numar_de_telefon']
        email = request.form['email']
        address = request.form['adresa']
        citizenship = request.form['cetatenie']
        ethnicity = request.form['etnie']
        photo = request.files['poza'] if 'poza' in request.files else None

        errors = {}

        if len(cnp) != 13 or not cnp.isdigit():
            errors['cnp'] = 'CNP-ul trebuie să aibă exact 13 cifre și să fie format doar din cifre.'

        if photo and not allowed_file(photo.filename):
            errors['poza'] = 'Format de fișier invalid. Poza trebuie să fie în format PNG, JPG sau JPEG.'

        if errors:
            return jsonify({"success": False, "errors": errors})

        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            filename = None

        try:
            with sqlite3.connect(STUDENT_DB_PATH) as conn:
                conn.execute('PRAGMA foreign_keys = ON')
                c = conn.cursor()

                query = '''UPDATE students
                           SET nume=?, prenume=?, facultatea=?, specializarea=?, an=?, grupa=?, data_nasterii=?, cnp=?, numar_de_telefon=?, email=?, adresa=?, cetatenie=?, etnie=?'''
                params = [name, surname, faculty, specialization, year, group, birth_date, cnp, phone_number, email, address, citizenship, ethnicity]

                if filename:
                    query += ', poza=? WHERE id=?'
                    params.append(filename)
                    params.append(id)
                else:
                    query += ' WHERE id=?'
                    params.append(id)

                c.execute(query, params)
                conn.commit()
        except sqlite3.Error as e:
            return jsonify({"success": False, "errors": {'general': f'Error updating student: {str(e)}'}})

       

    conn = sqlite3.connect(STUDENT_DB_PATH)
    conn.execute('PRAGMA foreign_keys = ON')
    c = conn.cursor()
    c.execute('SELECT * FROM students WHERE id = ?', (id,))
    student = c.fetchone()
    conn.close()

    if student is None:
        return redirect(url_for('students'))

    student_dict = {
        'id': student[0],
        'nume': student[1],
        'prenume': student[2],
        'facultatea': student[3],
        'specializarea': student[4],
        'an': student[5],
        'grupa': student[6],
        'data_nasterii': student[7],
        'cnp': student[8],
        'numar_de_telefon': student[9],
        'email': student[10],
        'adresa': student[11],
        'cetatenie': student[12],
        'etnie': student[13],
        'poza': student[14]
    }

    return render_template('student_details.html', student=student_dict, title=f'{student_dict["nume"]} {student_dict["prenume"]} - Detalii student')



@app.route('/students', methods=['GET'])
@login_required
def students():
    search_field = request.args.get('search_field', 'none')
    query = request.args.get('query', '')
    sort_field = request.args.get('sort_field', 'nume')
    sort_order = request.args.get('sort_order', 'asc')
    page = int(request.args.get('page', 1))
    per_page = 10

    if sort_field not in ['nume', 'prenume']:
        sort_field = 'nume'
    if sort_order not in ['asc', 'desc']:
        sort_order = 'asc'

    conn = sqlite3.connect(STUDENT_DB_PATH)
    conn.execute('PRAGMA foreign_keys = ON')
    c = conn.cursor()

    if search_field == 'none':
        if query:
            search = f"%{query}%"
            c.execute(f'SELECT COUNT(*) FROM students WHERE nume LIKE ? OR prenume LIKE ?', (search, search))
            total = c.fetchone()[0]
            c.execute(f'SELECT id, nume, prenume, cnp FROM students WHERE nume LIKE ? OR prenume LIKE ? ORDER BY {sort_field} {sort_order} LIMIT ? OFFSET ?', (search, search, per_page, (page - 1) * per_page))
        else:
            c.execute('SELECT COUNT(*) FROM students')
            total = c.fetchone()[0]
            c.execute(f'SELECT id, nume, prenume, cnp FROM students ORDER BY {sort_field} {sort_order} LIMIT ? OFFSET ?', (per_page, (page - 1) * per_page))
    else:
        if query:
            search = f"%{query}%"
            sql_query_count = f"SELECT COUNT(*) FROM students WHERE {search_field} LIKE ?"
            c.execute(sql_query_count, (search,))
            total = c.fetchone()[0]
            sql_query = f"SELECT id, nume, prenume, cnp FROM students WHERE {search_field} LIKE ? ORDER BY {sort_field} {sort_order} LIMIT ? OFFSET ?"
            c.execute(sql_query, (search, per_page, (page - 1) * per_page))
        else:
            c.execute('SELECT COUNT(*) FROM students')
            total = c.fetchone()[0]
            c.execute(f'SELECT id, nume, prenume, cnp FROM students ORDER BY {sort_field} {sort_order} LIMIT ? OFFSET ?', (per_page, (page - 1) * per_page))

    students_data = c.fetchall()
    conn.close()

    total_pages = (total + per_page - 1) // per_page

    students = []
    for student in students_data:
        student_dict = {
            'id': student[0],
            'nume': student[1],
            'prenume': student[2],
            'cnp': student[3]
        }
        students.append(student_dict)

    # Pagination logic
    pagination = {
        'first': 1,
        'prev': max(1, page - 1),
        'current': page,
        'next': min(total_pages, page + 1),
        'last': total_pages,
        'total_pages': total_pages
    }

    if total_pages <= 5:
        pages = list(range(1, total_pages + 1))
    else:
        if page <= 3:
            pages = [1, 2, 3, 4, total_pages]
        elif page >= total_pages - 2:
            pages = [1, total_pages - 3, total_pages - 2, total_pages - 1, total_pages]
        else:
            pages = [1, page - 1, page, page + 1, total_pages]

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('_students_list.html', students=students)
    else:
        return render_template('students.html', students=students, title='Studenți', pagination=pagination, pages=pages, current_page=page, total_pages=total_pages, search_field=search_field, query=query, sort_field=sort_field, sort_order=sort_order)

@app.route('/student/<int:id>')
@login_required
def student_details(id):
    conn = sqlite3.connect(STUDENT_DB_PATH)
    conn.execute('PRAGMA foreign_keys = ON')
    c = conn.cursor()
    c.execute('SELECT * FROM students WHERE id = ?', (id,))
    student = c.fetchone()
    conn.close()

    if student is None:
        return redirect(url_for('students'))
    
    student_dict = {
        'id': student[0],
        'nume': student[1],
        'prenume': student[2],
        'facultatea': student[3],
        'specializarea': student[4],
        'an': student[5],
        'grupa': student[6],
        'data_nasterii': student[7],
        'cnp': student[8],
        'numar_de_telefon': student[9],
        'email': student[10],
        'adresa': student[11],
        'cetatenie': student[12],
        'etnie': student[13],
        'poza': student[14]
    }
    return render_template('student_details.html', student=student_dict, title=student[1]+' '+student[2], username=session['username'])

@app.route('/check_duplicate_student', methods=['POST'])
@login_required
def check_duplicate_student():
    data = request.get_json()

    cnp = data.get('cnp', '').strip()
    email = data.get('email', '').strip()
    phone_number = data.get('numar_de_telefon', '').strip()

    duplicates = []

    with sqlite3.connect(STUDENT_DB_PATH) as conn:
        c = conn.cursor()

        if cnp:
            c.execute('SELECT id FROM students WHERE cnp = ?', (cnp,))
            if c.fetchone():
                duplicates.append('cnp')

        if email:
            c.execute('SELECT id FROM students WHERE email = ?', (email,))
            if c.fetchone():
                duplicates.append('email')

        if phone_number:
            c.execute('SELECT id FROM students WHERE numar_de_telefon = ?', (phone_number,))
            if c.fetchone():
                duplicates.append('numar_de_telefon')

    if duplicates:
        return jsonify({"is_duplicate": True, "fields": duplicates})
    else:
        return jsonify({"is_duplicate": False})


@app.route('/add_student', methods=['GET', 'POST'])
@login_required
def add_student():
    if request.method == 'POST':
        name = request.form['nume']
        surname = request.form['prenume']
        faculty = request.form['facultatea']
        specialization = request.form['specializarea']
        year = request.form['an']
        group = request.form['grupa']
        birth_date = request.form['data_nasterii']
        cnp = request.form['cnp']
        phone_number = request.form['numar_de_telefon']
        email = request.form['email']
        address = request.form['adresa']
        citizenship = request.form['cetatenie']
        ethnicity = request.form['etnie']
        photo = request.files['poza'] if 'poza' in request.files else None

        errors = {}

        if len(cnp) != 13 or not cnp.isdigit():
            errors['cnp'] = 'CNP-ul trebuie să aibă exact 13 cifre și să fie format doar din cifre.'

        if photo and not allowed_file(photo.filename):
            errors['poza'] = 'Format de fișier invalid. Poza trebuie să fie în format PNG, JPG sau JPEG.'

        if errors:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"success": False, "errors": errors})
            else:
                for error in errors.values():
                    flash(error, 'error')
                return redirect(url_for('add_student'))

        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            filename = None

        try:
            with sqlite3.connect(STUDENT_DB_PATH) as conn:
                conn.execute('PRAGMA foreign_keys = ON')
                c = conn.cursor()

                query = '''INSERT INTO students (nume, prenume, facultatea, specializarea, an, grupa, data_nasterii, cnp, numar_de_telefon, email, adresa, cetatenie, etnie, poza)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
                params = [name, surname, faculty, specialization, year, group, birth_date, cnp, phone_number, email, address, citizenship, ethnicity, filename]

                c.execute(query, params)
                conn.commit()
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({"success": True})
                else:
                    return redirect(url_for('students'))
        except sqlite3.Error as e:
            error_message = f'Error adding student: {str(e)}'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"success": False, "errors": {'general': error_message}})
            else:
                flash(error_message, 'error')
                return redirect(url_for('add_student'))

    return render_template('add_student.html', title='Adaugă Student')


@app.route('/delete_student/<int:id>', methods=['POST'])
def delete_student(id):
    if 'username' not in session:
        return redirect(url_for('login'))

    try:
        with sqlite3.connect(STUDENT_DB_PATH) as conn:
            conn.execute('PRAGMA foreign_keys = ON')
            c = conn.cursor()
            c.execute('DELETE FROM students WHERE id = ?', (id,))
            conn.commit()
    except sqlite3.Error as e:
        return jsonify({"success": False, "message": str(e)})

    return redirect(url_for('students'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/session_status')
def session_status():
    if 'username' in session:
        return jsonify({"logged_in": True, "username": session['username']})
    return jsonify({"logged_in": False})

if __name__ == '__main__':
    app.run(debug=True)
