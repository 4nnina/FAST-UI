from flask import Flask, render_template, request, redirect, url_for, json, jsonify, session
import subprocess, shutil, glob, os, sys, sqlite3, bcrypt

app = Flask(__name__)
app.secret_key = "chiave123"

@app.route('/update_users', methods=['POST'])
def update_users():
    try:
        data = request.get_json()
        print("DATA RECEIVED AS REQUESTED BY AN ADMINISTRATOR:", data)
        users = data['users']
        conn = get_db_connection()
        c = conn.cursor()
        
        for user in users:
            c.execute('''
                UPDATE users
                SET maxImp = ?, maxNot = ?
                WHERE id = ?
            ''', (user['maxImpossible'], user['maxUndesired'], user['id']))

        for user in users:
            if int(user['maxUndesired']) < 10:
                c.execute('DELETE FROM slot WHERE id = ? AND peso = ?', (user['id'], 'not'))
            
            if int(user['maxImpossible']) < 10:
                c.execute('DELETE FROM slot WHERE id = ? AND peso = ?', (user['id'], 'NOT'))

        conn.commit()
        conn.close()

        return jsonify({"status": "OK"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def get_db_connection():
    conn = sqlite3.connect('database.sqlite3') 
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/delete_users', methods=['POST'])
def delete_users():
    users_ids = json.loads(request.form['usersIDs'])

    conn = get_db_connection()
    c = conn.cursor()
    print("ID OF USERS TO BE REMOVED RECEIVED FROM THE ADMINISTRATOR", users_ids)

    for id in users_ids:
        c.execute('DELETE FROM slot WHERE id = ?', (id,))
        c.execute('DELETE FROM users WHERE id = ?', (id,))

    conn.commit()
    conn.close()
    return 'Users successfully deleted', 200

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    username = session.get('username')
    new_reg = session.get('new_reg')
    print("LOGGED OUT. OLD USERNAME ", username)

    session.clear()
    if username:
        session['old_usr'] = username
    if new_reg:
        session['new_reg'] = new_reg
    
    return redirect(url_for('login'))

def check_username(username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT password, id FROM users WHERE username = ?", (username, ))
    res = c.fetchone()
    conn.commit()
    conn.close()
    return res

def check_user(username, password):
    res = check_username(username)

    if res:
        pw_hashed = res[0]
        if bcrypt.checkpw(password.encode('utf-8'), pw_hashed):
            return [res[1]]
        
    return None

@app.route('/login.html', methods=['GET', 'POST'])
def login():
    session['errore_login'] = False

    if request.method == 'POST':
        session['username'] = request.form['username'].strip()
        password = request.form['password']
        res = check_user(session['username'], password)
        if res:
            session['id_usr'] = res[0]
            if session['id_usr'] == 0:
                return redirect(url_for('admin'))
            else:
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("SELECT maxNot, maxImp FROM users WHERE id = ?", (session['id_usr'],))
                res = c.fetchone()
                session['maxNot'], session['maxImp'] = res
                return redirect(url_for('index'))
        else:
            session['errore_login'] = True
            session['old_usr'] = session['username']
            return render_template('login.html') 
    
    return render_template('login.html')

@app.route('/', methods=['GET', 'POST'])
def index():
    conn = get_db_connection()
    c = conn.cursor()
    session.pop('new_reg', None)

    if (not session.get('username')) or (session.get('id_usr') == None):
        return redirect(url_for('login'))
    
    if session.get('username') == 'admin':
        return redirect(url_for('admin'))

    c.execute("SELECT giorno, ora_inizio, peso FROM slot WHERE id = ?", (session['id_usr'],))
    res = c.fetchall()
    schedule = {day: {} for day in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']}

    for entry in res:
        giorno, ora, peso = entry
        schedule[giorno][ora] = peso

    return render_template('index.html', schedule=schedule, res=res)

@app.route('/save_table', methods=['POST'])
def save():
    with sqlite3.connect('database.sqlite3') as conn:
        c = conn.cursor()
        
        orari = json.loads(request.form['orari'])
        preferenze = json.loads(request.form['prefs'])
        giorni = json.loads(request.form['giorni'])
        
        ore = ['8:30', '9:30', '10:30', '11:30', '12:30', '13:30', '14:30', '15:30', '16:30', '17:30', '18:30', '19:30']
        c.execute('DELETE FROM slot WHERE id = ?', (session.get('id_usr'),))
        for hri, pref, dd in zip(orari, preferenze, giorni):
            c.execute('''INSERT INTO slot (id, giorno, ora_inizio, ora_fine, peso) VALUES (?, ?, ?, ?, ?)''', (session['id_usr'], dd, hri, ore[ore.index(hri)+1], pref,))
            
    return 'Table saved successfully', 200

@app.route('/admin')
def admin():
    conn = get_db_connection()
    c = conn.cursor()
    
    if(session.get('username') != 'admin'):
        return redirect(url_for('index'))

    c.execute("SELECT id, username, password, maxImp, maxNot FROM users WHERE id != 0")
    users = c.fetchall()
    conn.close()

    conn = get_db_connection()
    c = conn.cursor()

    c.execute("SELECT * FROM slot")
    slot = c.fetchall()
    conn.close()

    slot_list = [list(row) for row in slot]

    slot_json = json.dumps(slot_list)

    schedule = {}

    for entry in slot:
        user_id, giorno, ora_inizio, ora_fine, peso = entry

        if user_id not in schedule:
            schedule[user_id] = {day: {} for day in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']}

        schedule[user_id][giorno][ora_inizio] = {'fine': ora_fine, 'peso': peso}


    return render_template('admin.html', users=users, slot = slot, slot_json = slot_json, schedule = schedule)

@app.route('/register', methods=['GET', 'POST'])
def register():
    session.pop('errore_reg_pw', False)
    session.pop('errore_reg_usr_dup', False)

    if request.method == 'POST':
        session['new_username'] = request.form['username'].strip()
        password = request.form['pw1']
        password_confirm = request.form['pw2']
        
        if password != password_confirm:
            session['errore_reg_pw'] = True
            return render_template('register.html')
        
        if check_username(session['new_username']):
            session['errore_reg_usr_dup'] = True
            return render_template('register.html')
        
        add_user(session['new_username'], password)
        
        if session.get('old_usr'):
            session['old_usr'] = session['new_username']
        session.pop('new_username', None)
        
        return redirect(url_for('login'))
    
    return render_template('register.html')

def add_user(username, password, maxImpossible=10, maxUndesired=10):
    conn = get_db_connection()
    c = conn.cursor()

    """
    existing_ids = c.fetchall()
    
    new_id = 0
    for i in range(len(existing_ids)):
        if existing_ids[i][0] != new_id:
            break
        new_id += 1
    """

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    c.execute(
        "INSERT INTO users (username, password, maxImp, maxNot) VALUES (?, ?, ?, ?)", 
        (username, hashed_password, maxImpossible, maxUndesired)
    )
    c.execute("SELECT id FROM users WHERE username = ?", (username,))
    res = c.fetchone()

    conn.commit()
    conn.close()
    #set_table_default_NOT(res[0])
    session['new_reg'] = True

"""
def set_table_default_NOT(id_usr):
    conn = get_db_connection()
    c = conn.cursor()

    giorni = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
    for x in range(5):
        c.execute("INSERT INTO slot (id, giorno, ora_inizio, ora_fine, peso) VALUES (?, ?, '12:30', '13:30', 'NOT')", (id_usr, giorni[x],))
        c.execute("INSERT INTO slot (id, giorno, ora_inizio, ora_fine, peso) VALUES (?, ?, '13:30',  '14:30', 'NOT')", (id_usr, giorni[x],))
    
    conn.commit()
    conn.close()
"""

@app.route('/run_optimization', methods=['POST'])
def run_optimization():
    try:
        base_dir = os.path.join(os.getcwd())
        output_dir = os.path.join(base_dir,'..','..', "university_schedules")
        main_script_path = os.path.join(base_dir,'..','..', "src", "main.py")
        
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        os.makedirs(output_dir, exist_ok=True)

        process = subprocess.Popen(
            [sys.executable, main_script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=os.environ.copy(),
            cwd=os.path.dirname(main_script_path)
        )
        stdout, stderr = process.communicate(timeout=60000)
        
        if process.returncode == 0:
            files_created = len(os.listdir(output_dir))
            return jsonify({
                "status": "success",
                "message": "Optimization completed!",
                "files_created": files_created,
                "output": stdout
            }), 200
        else:
            return jsonify({
                "status": "error",
                "error": stderr,
                "output": stdout
            }), 500

    except subprocess.TimeoutExpired:
        process.kill()
        return jsonify({
            "status": "error", 
            "error": "Timeout after 16 hours"
        }), 500
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/get_json_files', methods=['GET'])
def get_json_files():

    base_dir = os.path.join(os.getcwd())
    output_dir = os.path.join(base_dir,'..','..',"university_schedules")
    files = sorted(glob.glob(os.path.join(output_dir, 'fairness_data_*.json')))
    
    result = []
    for file in files:
        try:
            with open(file, 'r') as f:
                content = json.load(f)
                result.append({
                    'filename': os.path.basename(file),
                    'content': content,
                    'timestamp': os.path.getmtime(file)
                })
        except Exception as e:
            print(f"Error reading {file}: {str(e)}")
    
    return jsonify(result)

@app.route('/check_new_files', methods=['GET'])
def check_new_files():
    base_dir = os.path.join(os.getcwd())
    output_dir = os.path.join(base_dir,'..','..', "university_schedules")
    files = sorted(glob.glob(os.path.join(output_dir, 'fairness_data_*.json')))

    result = []
    for file in files:
        result.append({
            'filename': os.path.basename(file),
            'timestamp': os.path.getmtime(file)
        })
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
