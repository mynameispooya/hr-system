import json
import os
import uuid
from datetime import datetime, timedelta
from functools import wraps
from flask import (Flask, Response, request, jsonify, session,
                   send_file, send_from_directory, redirect, url_for, abort)
from io import BytesIO

app = Flask(__name__, template_folder='.', static_folder='.')
app.secret_key = os.urandom(24).hex()
app.permanent_session_lifetime = timedelta(hours=8)

DATA_FILE = 'data.json'
ALLOWED_STATIC = {'style.css', 'app.js'}

# ═══════════════════════════════════════════
# سرو فایل‌های استاتیک از پوشه فعلی
# ═══════════════════════════════════════════
@app.route('/<path:filename>')
def serve_file(filename):
    if filename not in ALLOWED_STATIC:
        abort(404)
    return send_from_directory('.', filename)

# ═══════════════════════════════════════════
# مدیریت داده‌ها
# ═══════════════════════════════════════════
def load_data():
    if not os.path.exists(DATA_FILE):
        d = _default()
        save_data(d)
        return d
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        if os.path.exists(DATA_FILE):
            os.rename(DATA_FILE, DATA_FILE + '.bak')
        d = _default()
        save_data(d)
        return d

def _default():
    return {
        "admin": {"username": "admin", "password": "admin123"},
        "sections": {},
        "users": {},
        "transfers": [],
        "settlements": [],
        "notifications": [],
        "audit_log": []
    }

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_audit(data, action, username, details):
    data['audit_log'].insert(0, {
        'id': str(uuid.uuid4())[:8], 'action': action,
        'user': username, 'details': details,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    if len(data['audit_log']) > 2000:
        data['audit_log'] = data['audit_log'][:2000]

def add_notif(data, target_un, message, tid=None):
    data['notifications'].insert(0, {
        'id': str(uuid.uuid4())[:8], 'target_username': target_un,
        'message': message, 'read': False,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'transfer_id': tid
    })
    if len(data['notifications']) > 500:
        data['notifications'] = data['notifications'][:500]

def code_unique(data, code, exclude_id=None):
    for s in data['sections'].values():
        for e in s.get('employees', []):
            if e['code'] == code and e['id'] != exclude_id:
                return False
    for t in data['transfers']:
        if t['status'] == 'pending' and t['employee']['code'] == code:
            return False
    return True

def sec_name(data, sid):
    return data['sections'].get(sid, {}).get('name', 'نامشخص')

def owner_display(data, oid):
    if oid is None:
        return 'مدیر سیستم'
    u = data['users'].get(oid)
    return u['display_name'] if u else 'نامشخص'

def user_by_un(data, un):
    for uid, u in data['users'].items():
        if u['username'] == un:
            return uid, u
    return None, None

def username_by_id(data, uid):
    u = data['users'].get(uid)
    return u['username'] if u else None

# ═══════════════════════════════════════════
# دکوراتورها
# ═══════════════════════════════════════════
def login_required(f):
    @wraps(f)
    def d(*a, **kw):
        if 'username' not in session:
            return jsonify({'error': 'لطفاً ابتدا وارد شوید'}), 401
        return f(*a, **kw)
    return d

def admin_required(f):
    @wraps(f)
    def d(*a, **kw):
        if 'username' not in session:
            return jsonify({'error': 'لطفاً ابتدا وارد شوید'}), 401
        data = load_data()
        if session['username'] != data['admin']['username']:
            return jsonify({'error': 'دسترسی محدود است'}), 403
        return f(*a, **kw)
    return d

def can_manage(f):
    """فقط مالک بخش یا ادمین"""
    @wraps(f)
    def d(sid, *a, **kw):
        data = load_data()
        if sid not in data['sections']:
            return jsonify({'error': 'بخش یافت نشد'}), 404
        if session.get('role') == 'admin':
            return f(sid, *a, **kw)
        sec = data['sections'][sid]
        if sec.get('owner') != session.get('user_id'):
            return jsonify({'error': 'شما مالک این بخش نیستید'}), 403
        return f(sid, *a, **kw)
    return d

def can_accept_transfer(f):
    """فقط مالک بخش مقصد یا ادمین"""
    @wraps(f)
    def d(tid, *a, **kw):
        data = load_data()
        tr = next((t for t in data['transfers'] if t['id'] == tid), None)
        if not tr:
            return jsonify({'error': 'انتقال یافت نشد'}), 404
        if session.get('role') == 'admin':
            return f(tid, *a, **kw)
        sec = data['sections'].get(tr['to_section'])
        if not sec or sec.get('owner') != session.get('user_id'):
            return jsonify({'error': 'فقط مالک بخش مقصد می‌تواند تایید کند'}), 403
        return f(tid, *a, **kw)
    return d

# ═══════════════════════════════════════════
# صفحات
# ═══════════════════════════════════════════
@app.route('/')
def index():
    if 'username' not in session:
        return Response(open('login.html', encoding='utf-8').read(), mimetype='text/html')
    data = load_data()
    if session['username'] == data['admin']['username']:
        return redirect(url_for('admin_page'))
    return redirect(url_for('user_page'))

@app.route('/admin')
def admin_page():
    if 'username' not in session:
        return redirect(url_for('index'))
    data = load_data()
    if session['username'] != data['admin']['username']:
        return redirect(url_for('index'))
    return Response(open('admin.html', encoding='utf-8').read(), mimetype='text/html')

@app.route('/user')
def user_page():
    if 'username' not in session:
        return redirect(url_for('index'))
    data = load_data()
    if session['username'] == data['admin']['username']:
        return redirect(url_for('admin_page'))
    _, u = user_by_un(data, session['username'])
    if not u:
        session.clear()
        return redirect(url_for('index'))
    return Response(open('user.html', encoding='utf-8').read(), mimetype='text/html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ═══════════════════════════════════════════
# احراز هویت
# ═══════════════════════════════════════════
@app.route('/api/login', methods=['POST'])
def api_login():
    data = load_data()
    req = request.get_json()
    username = req.get('username', '').strip()
    password = req.get('password', '').strip()
    if not username or not password:
        return jsonify({'error': 'نام کاربری و کد ورود الزامی است'}), 400
    if username == data['admin']['username'] and password == data['admin']['password']:
        session.permanent = True
        session['username'] = username
        session['role'] = 'admin'
        return jsonify({'role': 'admin', 'redirect': '/admin'})
    for uid, u in data['users'].items():
        if u['username'] == username and u['password'] == password:
            session.permanent = True
            session['username'] = username
            session['role'] = 'user'
            session['user_id'] = uid
            return jsonify({'role': 'user', 'redirect': '/user'})
    return jsonify({'error': 'نام کاربری یا کد ورود اشتباه است'}), 401

@app.route('/api/me', methods=['GET'])
@login_required
def api_me():
    data = load_data()
    if session['username'] == data['admin']['username']:
        return jsonify({'role': 'admin', 'username': session['username'],
                        'display_name': 'مدیر سیستم', 'user_id': None})
    _, u = user_by_un(data, session['username'])
    if not u:
        return jsonify({'error': 'not found'}), 404
    return jsonify({
        'role': 'user', 'username': u['username'],
        'display_name': u.get('display_name', u['username']),
        'user_id': session.get('user_id')
    })

# ═══════════════════════════════════════════
# بخش‌ها
# ═══════════════════════════════════════════
@app.route('/api/sections', methods=['GET'])
@login_required
def api_get_sections():
    data = load_data()
    result = []
    for sid, s in data['sections'].items():
        result.append({
            'id': sid, 'name': s['name'],
            'employee_count': len(s.get('employees', [])),
            'owner': s.get('owner'),
            'owner_name': owner_display(data, s.get('owner'))
        })
    return jsonify(result)

@app.route('/api/sections', methods=['POST'])
@login_required
def api_create_section():
    data = load_data()
    name = request.get_json().get('name', '').strip()
    if not name:
        return jsonify({'error': 'نام بخش الزامی است'}), 400
    for s in data['sections'].values():
        if s['name'] == name:
            return jsonify({'error': 'بخشی با این نام وجود دارد'}), 400
    sid = str(uuid.uuid4())[:8]
    owner = None if session['role'] == 'admin' else session.get('user_id')
    data['sections'][sid] = {'name': name, 'employees': [], 'owner': owner}
    who = 'مدیر سیستم' if owner is None else session['username']
    add_audit(data, 'create_section', session['username'],
              f'بخش «{name}» ایجاد شد توسط {who}')
    save_data(data)
    return jsonify({'id': sid, 'name': name, 'employee_count': 0,
                    'owner': owner, 'owner_name': owner_display(data, owner)}), 201

@app.route('/api/sections/<sid>', methods=['DELETE'])
@login_required
@can_manage
def api_delete_section(sid):
    data = load_data()
    name = data['sections'][sid]['name']
    # کارکنان باقی‌مانده به تسویه منتقل می‌شوند
    for emp in data['sections'][sid].get('employees', []):
        data['settlements'].append({
            'id': str(uuid.uuid4())[:8], 'employee': dict(emp),
            'from_section': sid, 'from_section_name': name,
            'initiated_by': session['username'],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    # انتقال‌های معلق مربوطه رد می‌شوند
    for t in data['transfers']:
        if t['status'] == 'pending' and (t['from_section'] == sid or t['to_section'] == sid):
            t['status'] = 'rejected'
            if t['from_section'] != sid and t['from_section'] in data['sections']:
                data['sections'][t['from_section']]['employees'].append(t['employee'])
    del data['sections'][sid]
    add_audit(data, 'delete_section', session['username'],
              f'بخش «{name}» حذف شد (کارکنان به تسویه منتقل شدند)')
    save_data(data)
    return jsonify({'message': 'بخش حذف شد'})

@app.route('/api/sections/<sid>/owner', methods=['PUT'])
@admin_required
def api_change_owner(sid):
    data = load_data()
    if sid not in data['sections']:
        return jsonify({'error': 'بخش یافت نشد'}), 404
    new_owner = request.get_json().get('owner') or None
    if new_owner and new_owner not in data['users']:
        return jsonify({'error': 'کاربر یافت نشد'}), 404
    old_name = owner_display(data, data['sections'][sid].get('owner'))
    data['sections'][sid]['owner'] = new_owner
    new_name = owner_display(data, new_owner)
    add_audit(data, 'change_owner', session['username'],
              f'مالک بخش «{data["sections"][sid]["name"]}» از {old_name} به {new_name} تغییر کرد')
    save_data(data)
    return jsonify({'message': 'مالک تغییر کرد'})

@app.route('/api/sections/<sid>/employees', methods=['GET'])
@login_required
@can_manage
def api_get_employees(sid):
    data = load_data()
    return jsonify(data['sections'][sid].get('employees', []))

@app.route('/api/sections/<sid>/employees', methods=['POST'])
@login_required
@can_manage
def api_add_employees(sid):
    data = load_data()
    employees = request.get_json().get('employees', [])
    if not employees:
        return jsonify({'error': 'لیست خالی است'}), 400
    added, errors = [], []
    for emp in employees:
        name = emp.get('name', '').strip()
        family = emp.get('family', '').strip()
        code = emp.get('code', '').strip()
        if not name or not family or not code:
            errors.append(f'اطلاعات ناقص: {name} {family} {code}')
            continue
        if not code_unique(data, code):
            errors.append(f'کد پرسنلی تکراری: {code}')
            continue
        new_emp = {'id': str(uuid.uuid4())[:8], 'name': name, 'family': family, 'code': code}
        data['sections'][sid]['employees'].append(new_emp)
        added.append(new_emp)
    if added:
        sname = data['sections'][sid]['name']
        add_audit(data, 'add_employees', session['username'],
                  f'{len(added)} نفر به بخش «{sname}» اضافه شدند')
        save_data(data)
    return jsonify({'added': added, 'errors': errors})

@app.route('/api/sections/<sid>/employees/upload', methods=['POST'])
@login_required
@can_manage
def api_upload_employees(sid):
    data = load_data()
    if 'file' not in request.files:
        return jsonify({'error': 'فایلی انتخاب نشده'}), 400
    file = request.files['file']
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        return jsonify({'error': 'فقط فایل xlsx یا xls'}), 400
    try:
        import openpyxl
        wb = openpyxl.load_workbook(file, data_only=True)
        ws = wb.active
        headers = [str(c.value or '').strip() for c in ws[1]]
        name_c, family_c, code_c = None, None, None
        for i, h in enumerate(headers):
            hl = h.lower()
            if 'نام' in h and 'خانوادگی' not in hl and name_c is None:
                name_c = i
            elif 'خانوادگی' in h:
                family_c = i
            elif 'پرسنلی' in h or ('کد' in h and code_c is None):
                code_c = i
        if name_c is None: name_c = 0
        if family_c is None: family_c = 1
        if code_c is None: code_c = 2
        added, errors = [], []
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row or all(c is None for c in row):
                continue
            name = str(row[name_c] or '').strip()
            family = str(row[family_c] or '').strip()
            code = str(row[code_c] or '').strip()
            if not name and not family and not code:
                continue
            if not name or not family or not code:
                errors.append(f'ردیف {row_idx}: اطلاعات ناقص')
                continue
            if not code_unique(data, code):
                errors.append(f'ردیف {row_idx}: کد تکراری {code}')
                continue
            new_emp = {'id': str(uuid.uuid4())[:8], 'name': name, 'family': family, 'code': code}
            data['sections'][sid]['employees'].append(new_emp)
            added.append(new_emp)
        if added:
            sname = data['sections'][sid]['name']
            msg = f'{len(added)} نفر از فایل به بخش «{sname}» اضافه شدند'
            if errors:
                msg += f' ({len(errors)} خطا)'
            add_audit(data, 'upload_employees', session['username'], msg)
            save_data(data)
        return jsonify({'added': added, 'errors': errors})
    except Exception as e:
        return jsonify({'error': f'خطا در خواندن فایل: {str(e)}'}), 400

@app.route('/api/sections/<sid>/employees/<eid>', methods=['DELETE'])
@login_required
@can_manage
def api_delete_employee(sid, eid):
    data = load_data()
    emps = data['sections'][sid]['employees']
    emp = next((e for e in emps if e['id'] == eid), None)
    if not emp:
        return jsonify({'error': 'کارمند یافت نشد'}), 404
    emps.remove(emp)
    sname = data['sections'][sid]['name']
    add_audit(data, 'delete_employee', session['username'],
              f'«{emp["name"]} {emp["family"]}» (کد: {emp["code"]}) از بخش «{sname}» حذف شد')
    save_data(data)
    return jsonify({'message': 'حذف شد'})

@app.route('/api/sections/<sid>/export', methods=['GET'])
@login_required
@can_manage
def api_export_section(sid):
    data = load_data()
    sname = data['sections'][sid]['name']
    emps = data['sections'][sid].get('employees', [])
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sname[:31]
    ws.append(['نام', 'نام خانوادگی', 'کد پرسنلی'])
    for e in emps:
        ws.append([e['name'], e['family'], e['code']])
    for col in ws.columns:
        mx = 0
        cl = col[0].column_letter
        for cell in col:
            if cell.value:
                mx = max(mx, len(str(cell.value)))
        ws.column_dimensions[cl].width = max(mx + 4, 14)
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name=f'{sname}.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# ═══════════════════════════════════════════
# انتقال‌ها
# ═══════════════════════════════════════════
@app.route('/api/transfers', methods=['GET'])
@login_required
def api_get_transfers():
    data = load_data()
    if session['role'] != 'admin':
        my_secs = [sid for sid, s in data['sections'].items()
                    if s.get('owner') == session.get('user_id')]
        return jsonify([t for t in data['transfers']
                        if t['from_section'] in my_secs or t['to_section'] in my_secs])
    return jsonify(data['transfers'])

@app.route('/api/transfers', methods=['POST'])
@login_required
def api_create_transfer():
    data = load_data()
    req = request.get_json()
    eid = req.get('employee_id')
    from_s = req.get('from_section')
    to_s = req.get('to_section')
    if not eid or not from_s or not to_s:
        return jsonify({'error': 'اطلاعات ناقص'}), 400
    if from_s == to_s:
        return jsonify({'error': 'بخش مبدأ و مقصد یکسان است'}), 400
    if from_s not in data['sections'] or to_s not in data['sections']:
        return jsonify({'error': 'بخش یافت نشد'}), 404
    # بررسی دسترسی: مالک مبدأ یا ادمین
    if session['role'] != 'admin':
        sec = data['sections'][from_s]
        if sec.get('owner') != session.get('user_id'):
            return jsonify({'error': 'دسترسی محدود است'}), 403
    emps = data['sections'][from_s]['employees']
    emp = next((e for e in emps if e['id'] == eid), None)
    if not emp:
        return jsonify({'error': 'کارمند یافت نشد'}), 404

    from_name = data['sections'][from_s]['name']
    to_name = data['sections'][to_s]['name']
    emp_copy = dict(emp)

    # ادمین: انتقال مستقیم
    if session['role'] == 'admin':
        if not code_unique(data, emp['code'], exclude_emp_id=emp['id']):
            return jsonify({'error': f'کد پرسنلی {emp["code"]} در بخش مقصد تکراری است'}), 400
        emps.remove(emp)
        data['sections'][to_s]['employees'].append(emp_copy)
        transfer = {
            'id': str(uuid.uuid4())[:8], 'employee': emp_copy,
            'from_section': from_s, 'to_section': to_s,
            'status': 'completed', 'initiated_by': session['username'],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'completed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        data['transfers'].append(transfer)
        add_audit(data, 'transfer', session['username'],
                  f'«{emp["name"]} {emp["family"]}» (کد: {emp["code"]}) از «{from_name}» به «{to_name}» - مستقیم توسط مدیر')
        dest_un = username_by_id(data, data['sections'][to_s].get('owner'))
        if dest_un:
            add_notif(data, dest_un,
                      f'«{emp["name"]} {emp["family"]}» (کد: {emp["code"]}) توسط مدیر به بخش «{to_name}» اضافه شد',
                      transfer['id'])
        save_data(data)
        return jsonify(transfer)

    # کاربر: انتقال با تایید
    emps.remove(emp)
    transfer = {
        'id': str(uuid.uuid4())[:8], 'employee': emp_copy,
        'from_section': from_s, 'to_section': to_s,
        'status': 'pending', 'initiated_by': session['username'],
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    data['transfers'].append(transfer)
    add_audit(data, 'transfer_initiated', session['username'],
              f'درخواست انتقال «{emp["name"]} {emp["family"]}» (کد: {emp["code"]}) از «{from_name}» به «{to_name}»')
    dest_un = username_by_id(data, data['sections'][to_s].get('owner'))
    if dest_un:
        add_notif(data, dest_un,
                  f'درخواست انتقال: «{emp["name"]} {emp["family"]}» (کد: {emp["code"]}) منتظر تایید شماست',
                  transfer['id'])
    save_data(data)
    return jsonify(transfer)

@app.route('/api/transfers/<tid>/accept', methods=['POST'])
@login_required
@can_accept_transfer
def api_accept_transfer(tid):
    data = load_data()
    transfer = next((t for t in data['transfers'] if t['id'] == tid), None)
    if not transfer or transfer['status'] != 'pending':
        return jsonify({'error': 'این انتقال قبلاً پردازش شده'}), 400
    if not code_unique(data, transfer['employee']['code']):
        transfer['status'] = 'rejected'
        if transfer['from_section'] in data['sections']:
            data['sections'][transfer['from_section']]['employees'].append(transfer['employee'])
        add_audit(data, 'transfer_rejected', session['username'],
                  f'انتقال «{transfer["employee"]["name"]} {transfer["employee"]["family"]}» رد شد - کد پرسنلی تکراری')
        src_un = username_by_id(data, data['sections'].get(transfer['from_section'], {}).get('owner'))
        if src_un:
            add_notif(data, src_un,
                      f'درخواست انتقال «{transfer["employee"]["name"]} {transfer["employee"]["family"]}» رد شد - کد پرسنلی تکراری',
                      tid)
        save_data(data)
        return jsonify({'error': 'کد پرسنلی تکراری است. انتقال رد شد و کارمند به مبدأ بازگشت.'}), 400
    data['sections'][transfer['to_section']]['employees'].append(transfer['employee'])
    transfer['status'] = 'accepted'
    transfer['accepted_by'] = session['username']
    transfer['completed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    fn = sec_name(data, transfer['from_section'])
    tn = sec_name(data, transfer['to_section'])
    add_audit(data, 'transfer_accepted', session['username'],
              f'«{transfer["employee"]["name"]} {transfer["employee"]["family"]}» (کد: {transfer["employee"]["code"]}) از «{fn}» به «{tn}» پذیرفته شد')
    src_un = username_by_id(data, data['sections'].get(transfer['from_section'], {}).get('owner'))
    if src_un:
        add_notif(data, src_un,
                  f'«{transfer["employee"]["name"]} {transfer["employee"]["family"]}» (کد: {transfer["employee"]["code"]}) توسط بخش «{tn}» پذیرفته شد',
                  tid)
    save_data(data)
    return jsonify(transfer)

@app.route('/api/transfers/<tid>/reject', methods=['POST'])
@login_required
@can_accept_transfer
def api_reject_transfer(tid):
    data = load_data()
    transfer = next((t for t in data['transfers'] if t['id'] == tid), None)
    if not transfer or transfer['status'] != 'pending':
        return jsonify({'error': 'این انتقال قبلاً پردازش شده'}), 400
    if transfer['from_section'] in data['sections']:
        data['sections'][transfer['from_section']]['employees'].append(transfer['employee'])
    transfer['status'] = 'rejected'
    transfer['rejected_by'] = session['username']
    transfer['completed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    add_audit(data, 'transfer_rejected', session['username'],
              f'انتقال «{transfer["employee"]["name"]} {transfer["employee"]["family"]}» (کد: {transfer["employee"]["code"]}) رد شد')
    src_un = username_by_id(data, data['sections'].get(transfer['from_section'], {}).get('owner'))
    if src_un:
        add_notif(data, src_un,
                  f'درخواست انتقال «{transfer["employee"]["name"]} {transfer["employee"]["family"]}» رد شد',
                  tid)
    save_data(data)
    return jsonify(transfer)

# ═══════════════════════════════════════════
# تسویه‌ها
# ═══════════════════════════════════════════
@app.route('/api/settlements', methods=['GET'])
@login_required
def api_get_settlements():
    data = load_data()
    return jsonify(data.get('settlements', []))

@app.route('/api/settlements', methods=['POST'])
@login_required
def api_create_settlement():
    data = load_data()
    req = request.get_json()
    eid = req.get('employee_id')
    from_s = req.get('from_section')
    if not eid or not from_s:
        return jsonify({'error': 'اطلاعات ناقص'}), 400
    if from_s not in data['sections']:
        return jsonify({'error': 'بخش یافت نشد'}), 404
    if session['role'] != 'admin':
        sec = data['sections'][from_s]
        if sec.get('owner') != session.get('user_id'):
            return jsonify({'error': 'دسترسی محدود است'}), 403
    emps = data['sections'][from_s]['employees']
    emp = next((e for e in emps if e['id'] == eid), None)
    if not emp:
        return jsonify({'error': 'کارمند یافت نشد'}), 404
    emps.remove(emp)
    sname = data['sections'][from_s]['name']
    settlement = {
        'id': str(uuid.uuid4())[:8], 'employee': dict(emp),
        'from_section': from_s, 'from_section_name': sname,
        'initiated_by': session['username'],
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    data['settlements'].append(settlement)
    add_audit(data, 'settlement', session['username'],
              f'«{emp["name"]} {emp["family"]}» (کد: {emp["code"]}) از بخش «{sname}» به تسویه منتقل شد')
    save_data(data)
    return jsonify(settlement)

@app.route('/api/settlements/export', methods=['GET'])
@admin_required
def api_export_settlements():
    data = load_data()
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'تسویه'
    ws.append(['نام', 'نام خانوادگی', 'کد پرسنلی', 'بخش مبدأ', 'تاریخ تسویه', 'توسط'])
    for s in data.get('settlements', []):
        ws.append([s['employee']['name'], s['employee']['family'],
                   s['employee']['code'], s['from_section_name'],
                   s['timestamp'], s['initiated_by']])
    for col in ws.columns:
        mx = 0
        cl = col[0].column_letter
        for cell in col:
            if cell.value:
                mx = max(mx, len(str(cell.value)))
        ws.column_dimensions[cl].width = max(mx + 4, 14)
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name='settlements.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# ═══════════════════════════════════════════
# کاربران (فقط ادمین)
# ═══════════════════════════════════════════
@app.route('/api/users', methods=['GET'])
@admin_required
def api_get_users():
    data = load_data()
    return jsonify([{
        'id': uid, 'username': u['username'],
        'display_name': u.get('display_name', ''),
        'section_count': len([s for s in data['sections'].values()
                              if s.get('owner') == uid])
    } for uid, u in data['users'].items()])

@app.route('/api/users', methods=['POST'])
@admin_required
def api_create_user():
    data = load_data()
    req = request.get_json()
    username = req.get('username', '').strip()
    password = req.get('password', '').strip()
    display_name = req.get('display_name', '').strip()
    if not username or not password:
        return jsonify({'error': 'نام کاربری و کد ورود الزامی است'}), 400
    if len(password) < 3:
        return jsonify({'error': 'کد ورود حداقل ۳ کاراکتر'}), 400
    if username == data['admin']['username']:
        return jsonify({'error': 'این نام کاربری رزرو شده'}), 400
    for u in data['users'].values():
        if u['username'] == username:
            return jsonify({'error': 'نام کاربری تکراری'}), 400
    uid = str(uuid.uuid4())[:8]
    data['users'][uid] = {
        'username': username, 'password': password,
        'display_name': display_name or username
    }
    add_audit(data, 'create_user', session['username'],
              f'کاربر «{display_name or username}» ({username}) ایجاد شد')
    save_data(data)
    return jsonify({'id': uid, 'username': username,
                    'display_name': display_name or username}), 201

@app.route('/api/users/<uid>', methods=['PUT'])
@admin_required
def api_update_user(uid):
    data = load_data()
    if uid not in data['users']:
        return jsonify({'error': 'کاربر یافت نشد'}), 404
    req = request.get_json()
    u = data['users'][uid]
    if 'password' in req and req['password'].strip():
        if len(req['password'].strip()) < 3:
            return jsonify({'error': 'کد ورود حداقل ۳ کاراکتر'}), 400
        u['password'] = req['password'].strip()
    if 'display_name' in req:
        u['display_name'] = req['display_name'].strip() or u['username']
    add_audit(data, 'update_user', session['username'],
              f'اطلاعات کاربر «{u["display_name"]}» ({u["username"]}) ویرایش شد')
    save_data(data)
    return jsonify({'id': uid, 'username': u['username'],
                    'display_name': u['display_name']})

@app.route('/api/users/<uid>', methods=['DELETE'])
@admin_required
def api_delete_user(uid):
    data = load_data()
    if uid not in data['users']:
        return jsonify({'error': 'کاربر یافت نشد'}), 404
    u = data['users'][uid]
    # بخش‌های این کاربر به ادمین منتقل می‌شود
    for s in data['sections'].values():
        if s.get('owner') == uid:
            s['owner'] = None
    add_audit(data, 'delete_user', session['username'],
              f'کاربر «{u["display_name"]}» ({u["username"]}) حذف شد - بخش‌ها به مدیر منتقل شدند')
    del data['users'][uid]
    save_data(data)
    return jsonify({'message': 'کاربر حذف شد'})

# ═══════════════════════════════════════════
# اعلان‌ها
# ═══════════════════════════════════════════
@app.route('/api/notifications', methods=['GET'])
@login_required
def api_get_notifications():
    data = load_data()
    return jsonify([n for n in data.get('notifications', [])
                    if n['target_username'] == session['username']])

@app.route('/api/notifications/<nid>/read', methods=['POST'])
@login_required
def api_read_notif(nid):
    data = load_data()
    for n in data.get('notifications', []):
        if n['id'] == nid and n['target_username'] == session['username']:
            n['read'] = True
            save_data(data)
            return jsonify({'message': 'ok'})
    return jsonify({'error': 'not found'}), 404

@app.route('/api/notifications/read-all', methods=['POST'])
@login_required
def api_read_all_notifs():
    data = load_data()
    for n in data.get('notifications', []):
        if n['target_username'] == session['username']:
            n['read'] = True
    save_data(data)
    return jsonify({'message': 'ok'})

# ═══════════════════════════════════════════
# گزارش تغییرات
# ═══════════════════════════════════════════
@app.route('/api/audit-log', methods=['GET'])
@admin_required
def api_get_audit():
    data = load_data()
    return jsonify(data.get('audit_log', []))

@app.route('/api/audit-log/export', methods=['GET'])
@admin_required
def api_export_audit():
    data = load_data()
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'گزارش تغییرات'
    ws.append(['ردیف', 'تاریخ و ساعت', 'عملیات', 'کاربر', 'جزئیات'])
    for i, log in enumerate(data.get('audit_log', []), 1):
        ws.append([i, log['timestamp'], log['action'], log['user'], log['details']])
    for col in ws.columns:
        mx = 0
        cl = col[0].column_letter
        for cell in col:
            if cell.value:
                mx = max(mx, len(str(cell.value)))
        ws.column_dimensions[cl].width = max(mx + 4, 14)
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name='audit_log.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# ═══════════════════════════════════════════
# تغییر رمز مدیر
# ═══════════════════════════════════════════
@app.route('/api/admin/change-password', methods=['POST'])
@admin_required
def api_change_pw():
    data = load_data()
    req = request.get_json()
    old_pw = req.get('old_password', '')
    new_pw = req.get('new_password', '').strip()
    if old_pw != data['admin']['password']:
        return jsonify({'error': 'کد ورود فعلی اشتباه است'}), 400
    if not new_pw or len(new_pw) < 3:
        return jsonify({'error': 'کد ورود جدید حداقل ۳ کاراکتر'}), 400
    data['admin']['password'] = new_pw
    add_audit(data, 'change_password', session['username'], 'تغییر کد ورود مدیر')
    save_data(data)
    return jsonify({'message': 'تغییر کرد'})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
