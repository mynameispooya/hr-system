import json, os, uuid
from datetime import datetime, timedelta
from functools import wraps
from flask import (Flask, Response, request, jsonify,
                   session, send_file, redirect, url_for)
from io import BytesIO

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()
app.permanent_session_lifetime = timedelta(hours=8)

DATA_FILE = 'data.json'

# ═══════════════════════════════════════════════════════════════
# مدیریت داده‌ها
# ═══════════════════════════════════════════════════════════════

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

def owner_name(data, oid):
    if oid is None:
        return 'مدیر سیستم'
    u = data['users'].get(oid)
    return u['display_name'] if u else 'نامشخص'

def user_by_un(data, un):
    for uid, u in data['users'].items():
        if u['username'] == un:
            return uid, u
    return None, None

def owner_of_section(data, sid):
    s = data['sections'].get(sid)
    if not s:
        return None
    return s.get('owner')

# ═══════════════════════════════════════════════════════════════
# دکوراتورها
# ═══════════════════════════════════════════════════════════════

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

def can_manage_section(f):
    """بررسی اینکه آیا کاربر می‌تواند بخش را مدیریت کند"""
    @wraps(f)
    def d(sid, *a, **kw):
        data = load_data()
        if sid not in data['sections']:
            return jsonify({'error': 'بخش یافت نشد'}), 404
        if session['role'] == 'admin':
            return f(sid, *a, **kw)
        s = data['sections'][sid]
        if s.get('owner') != session.get('user_id'):
            return jsonify({'error': 'دسترسی محدود است'}), 403
        return f(sid, *a, **kw)
    return d

# ═══════════════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════════════

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700;800;900&display=swap');
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
--bg0:#080b16;--bg1:#0f1225;--bg2:#161a33;--bg3:#1c2144;--bgH:#232849;
--ac:#00e5a0;--acH:#00cc8e;--acD:rgba(0,229,160,.08);--acB:rgba(0,229,160,.3);
--dn:#ff4757;--dnH:#e8384a;--dnD:rgba(255,71,87,.08);--dnB:rgba(255,71,87,.3);
--wn:#ffa502;--wnD:rgba(255,165,2,.08);--wnB:rgba(255,165,2,.3);
--inf:#3b82f6;--infD:rgba(59,130,246,.08);--infB:rgba(59,130,246,.3);
--t1:#e8eaf6;--t2:#7c82a1;--t3:#4a4f6a;
--bd:#232849;--bdL:#2d3360;
--r:12px;--rs:8px;--rx:6px;
--sh:0 4px 24px rgba(0,0,0,.3);--shL:0 8px 40px rgba(0,0,0,.5);
--tr:.2s ease;--ff:'Vazirmatn',sans-serif
}
html{font-size:14px;direction:rtl}
body{font-family:var(--ff);background:var(--bg0);color:var(--t1);min-height:100vh;line-height:1.7;-webkit-font-smoothing:antialiased}
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:var(--bg1)}
::-webkit-scrollbar-thumb{background:var(--bdL);border-radius:3px}
a{color:var(--ac);text-decoration:none}a:hover{color:var(--acH)}
input,select,textarea{font-family:var(--ff);font-size:.93rem;padding:10px 14px;background:var(--bg1);border:1px solid var(--bd);border-radius:var(--rs);color:var(--t1);outline:none;transition:border-color var(--tr),box-shadow var(--tr);width:100%}
input:focus,select:focus,textarea:focus{border-color:var(--ac);box-shadow:0 0 0 3px var(--acD)}
input::placeholder{color:var(--t3)}
select{cursor:pointer;appearance:none;padding-left:36px;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='%237c82a1' viewBox='0 0 16 16'%3E%3Cpath d='M1.5 5.5l6.5 6 6.5-6'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:left 12px center}
input[type="file"]{padding:8px;cursor:pointer}
input[type="file"]::file-selector-button{font-family:var(--ff);padding:6px 16px;margin-left:12px;background:var(--bg3);border:1px solid var(--bdL);border-radius:var(--rx);color:var(--t2);cursor:pointer;transition:all var(--tr)}
input[type="file"]::file-selector-button:hover{background:var(--bgH);color:var(--t1)}
.btn{display:inline-flex;align-items:center;gap:6px;font-family:var(--ff);font-size:.9rem;font-weight:500;padding:9px 20px;border:none;border-radius:var(--rs);cursor:pointer;transition:all var(--tr);white-space:nowrap}
.btn:active{transform:scale(.97)}
.btn-p{background:var(--ac);color:#080b16}.btn-p:hover{background:var(--acH);box-shadow:0 0 20px rgba(0,229,160,.2)}
.btn-d{background:var(--dn);color:#fff}.btn-d:hover{background:var(--dnH);box-shadow:0 0 20px rgba(255,71,87,.2)}
.btn-g{background:transparent;color:var(--t2);border:1px solid var(--bd)}.btn-g:hover{background:var(--bgH);color:var(--t1);border-color:var(--bdL)}
.btn-sm{padding:6px 12px;font-size:.82rem}.btn-ic{padding:7px 9px}
.btn:disabled{opacity:.4;cursor:not-allowed;pointer-events:none}
.card{background:var(--bg2);border:1px solid var(--bd);border-radius:var(--r);padding:24px;transition:border-color var(--tr)}.card:hover{border-color:var(--bdL)}
.tw{overflow-x:auto;border-radius:var(--rs);border:1px solid var(--bd)}
table{width:100%;border-collapse:collapse}
th{background:var(--bg3);color:var(--t2);font-weight:600;font-size:.82rem;text-align:right;padding:12px 16px;border-bottom:1px solid var(--bd);position:sticky;top:0;z-index:1}
td{padding:11px 16px;border-bottom:1px solid var(--bd);font-size:.9rem;vertical-align:middle}
tr:last-child td{border-bottom:none}tr:hover td{background:var(--bgH)}
tr[draggable="true"]{cursor:grab}tr[draggable="true"]:active{cursor:grabbing}
tr.dragging{opacity:.4}tr.drag-over td{background:var(--acD);box-shadow:inset 0 0 0 1px var(--acB)}
.es{text-align:center;padding:48px 24px;color:var(--t3)}.es .ei{font-size:3rem;margin-bottom:12px;opacity:.4}
.badge{display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:20px;font-size:.78rem;font-weight:600}
.b-pen{background:var(--wnD);color:var(--wn);border:1px solid var(--wnB)}
.b-acc,.b-com{background:var(--acD);color:var(--ac);border:1px solid var(--acB)}
.b-rej{background:var(--dnD);color:var(--dn);border:1px solid var(--dnB)}
.header{display:flex;align-items:center;justify-content:space-between;padding:0 24px;height:64px;background:var(--bg1);border-bottom:1px solid var(--bd);position:sticky;top:0;z-index:100}
.hlogo{display:flex;align-items:center;gap:10px;font-weight:700;font-size:1.05rem}
.hlogo .lb{width:34px;height:34px;background:var(--ac);border-radius:var(--rs);display:flex;align-items:center;justify-content:center;color:#080b16;font-weight:900;font-size:1.1rem}
.hacts{display:flex;align-items:center;gap:12px}
.huser{color:var(--t2);font-size:.88rem}
.nbtn{position:relative;background:none;border:none;color:var(--t2);cursor:pointer;padding:8px;border-radius:var(--rs);transition:all var(--tr);font-size:1.2rem}
.nbtn:hover{background:var(--bgH);color:var(--t1)}
.nbdg{position:absolute;top:2px;left:2px;width:18px;height:18px;background:var(--dn);color:#fff;font-size:.65rem;font-weight:700;border-radius:50%;display:flex;align-items:center;justify-content:center;border:2px solid var(--bg1)}
.ndd{position:absolute;top:calc(100% + 8px);left:0;width:360px;max-height:420px;overflow-y:auto;background:var(--bg2);border:1px solid var(--bd);border-radius:var(--r);box-shadow:var(--shL);display:none;z-index:200}
.ndd.show{display:block;animation:fsd .2s ease}
.nddh{display:flex;justify-content:space-between;align-items:center;padding:14px 16px;border-bottom:1px solid var(--bd)}
.nddh h4{font-size:.9rem;font-weight:600}
.ni{padding:12px 16px;border-bottom:1px solid var(--bd);font-size:.85rem;color:var(--t2);transition:background var(--tr);cursor:pointer}
.ni:hover{background:var(--bgH)}.ni.ur{background:var(--acD);border-right:3px solid var(--ac)}
.ni .nt{font-size:.75rem;color:var(--t3);margin-top:4px;display:block}
.ne{padding:32px;text-align:center;color:var(--t3);font-size:.88rem}
.layout{display:flex;min-height:calc(100vh - 64px)}
.sidebar{width:240px;min-width:240px;background:var(--bg1);border-left:1px solid var(--bd);padding:16px 0;display:flex;flex-direction:column}
.snav{flex:1;padding:0 8px}
.si{display:flex;align-items:center;gap:10px;padding:10px 16px;border-radius:var(--rs);color:var(--t2);cursor:pointer;transition:all var(--tr);font-size:.9rem;font-weight:500;margin-bottom:2px;border:none;background:none;width:100%;text-align:right;font-family:var(--ff)}
.si:hover{background:var(--bgH);color:var(--t1)}
.si.active{background:var(--acD);color:var(--ac);border:1px solid var(--acB)}
.si .ii{font-size:1.1rem;width:22px;text-align:center}
.sft{padding:8px;border-top:1px solid var(--bd);margin-top:8px}
.main{flex:1;padding:24px;overflow-y:auto;max-height:calc(100vh - 64px)}
.page{display:none;animation:fi .3s ease}.page.active{display:block}
.pt{font-size:1.4rem;font-weight:700;margin-bottom:20px}
.sg{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px;margin-bottom:28px}
.sc{background:var(--bg2);border:1px solid var(--bd);border-radius:var(--r);padding:20px;display:flex;flex-direction:column;gap:8px;transition:border-color var(--tr),transform var(--tr)}
.sc:hover{border-color:var(--bdL);transform:translateY(-2px)}
.sl{font-size:.82rem;color:var(--t3);font-weight:500}
.sv{font-size:1.8rem;font-weight:800}
.sv.a1{color:var(--ac)}.sv.w1{color:var(--wn)}.sv.d1{color:var(--dn)}.sv.i1{color:var(--inf)}
.tb{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:16px}
.tb .sb{position:relative;flex:1;min-width:200px;max-width:320px}
.tb .sb input{padding-right:38px}
.tb .sb .sic{position:absolute;right:12px;top:50%;transform:translateY(-50%);color:var(--t3);font-size:.95rem;pointer-events:none}
.tb-sp{flex:1}
.sec-g{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}
.secc{background:var(--bg2);border:1px solid var(--bd);border-radius:var(--r);padding:20px;cursor:pointer;transition:all var(--tr);position:relative}
.secc:hover{border-color:var(--acB);transform:translateY(-2px);box-shadow:0 4px 20px rgba(0,229,160,.08)}
.secc .sn{font-weight:700;font-size:1rem;margin-bottom:6px}
.secc .scn{color:var(--t3);font-size:.85rem}.secc .scn span{color:var(--ac);font-weight:700}
.secc .sow{color:var(--t3);font-size:.78rem;margin-top:4px}
.secc .xsec{position:absolute;top:12px;left:12px;background:none;border:none;color:var(--t3);cursor:pointer;padding:4px;border-radius:4px;transition:all var(--tr);font-size:1rem}
.secc .xsec:hover{color:var(--dn);background:var(--dnD)}
.dzs{display:flex;gap:14px;margin-top:20px}
.dz{flex:1;border:2px dashed var(--bdL);border-radius:var(--r);padding:28px 20px;text-align:center;transition:all var(--tr);color:var(--t3);min-height:100px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px}
.dz .di{font-size:2rem;opacity:.5}.dz .dl{font-size:.9rem;font-weight:500}.dz .dh{font-size:.78rem;opacity:.6}
.dz.da{border-color:var(--ac);background:var(--acD);color:var(--ac)}.dz.da .di{opacity:1}
.dz.sz.da{border-color:var(--wn);background:var(--wnD);color:var(--wn)}
.mo{position:fixed;inset:0;background:rgba(0,0,0,.65);backdrop-filter:blur(4px);display:none;align-items:center;justify-content:center;z-index:500;padding:24px}
.mo.active{display:flex;animation:fi .2s ease}
.md{background:var(--bg2);border:1px solid var(--bd);border-radius:var(--r);width:100%;max-width:520px;max-height:85vh;overflow-y:auto;box-shadow:var(--shL);animation:si .25s ease}
.mh{display:flex;justify-content:space-between;align-items:center;padding:20px 24px;border-bottom:1px solid var(--bd)}
.mh h3{font-size:1.1rem;font-weight:700}
.mx{background:none;border:none;color:var(--t3);cursor:pointer;font-size:1.3rem;padding:4px;border-radius:4px;transition:all var(--tr);line-height:1}
.mx:hover{color:var(--t1);background:var(--bgH)}
.mb{padding:24px}.mf{padding:16px 24px;border-top:1px solid var(--bd);display:flex;gap:10px;justify-content:flex-start}
.fg{margin-bottom:16px}.fl{display:block;font-size:.85rem;font-weight:600;color:var(--t2);margin-bottom:6px}
.fr{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.fh{font-size:.78rem;color:var(--t3);margin-top:4px}
.fe{font-size:.82rem;color:var(--dn);margin-top:4px}
#tc{position:fixed;top:80px;left:24px;z-index:9999;display:flex;flex-direction:column;gap:8px;max-width:380px}
.ts{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 16px;border-radius:var(--rs);font-size:.88rem;box-shadow:var(--shL);transform:translateX(-120%);transition:transform .3s ease;border:1px solid var(--bd)}
.ts.show{transform:translateX(0)}
.ts-s{background:var(--bg2);border-color:var(--acB);color:var(--ac)}
.ts-e{background:var(--bg2);border-color:var(--dnB);color:var(--dn)}
.ts-w{background:var(--bg2);border-color:var(--wnB);color:var(--wn)}
.ts button{background:none;border:none;color:inherit;cursor:pointer;font-size:1.1rem;padding:0;opacity:.6;transition:opacity var(--tr)}.ts button:hover{opacity:1}
.pc{background:var(--bg3);border:1px solid var(--wnB);border-radius:var(--rs);padding:16px;margin-bottom:10px;animation:fi .3s ease}
.pc .pch{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.pc .pn{font-weight:600}.pc .pk{color:var(--t3);font-size:.82rem}
.pc .pf{font-size:.82rem;color:var(--t2);margin-bottom:10px}
.pc .pa{display:flex;gap:8px}
.li{display:flex;gap:14px;padding:14px 0;border-bottom:1px solid var(--bd);font-size:.88rem;align-items:flex-start}
.li:last-child{border-bottom:none}
.lt{color:var(--t3);font-size:.78rem;white-space:nowrap;min-width:130px}
.la{color:var(--ac);font-weight:600;white-space:nowrap;min-width:130px}
.ld{color:var(--t2);flex:1}.lu{color:var(--inf);white-space:nowrap}
.lp{min-height:100vh;display:flex;align-items:center;justify-content:center;background:var(--bg0);position:relative;overflow:hidden}
.lbg{position:absolute;inset:0;background:radial-gradient(ellipse 600px 400px at 20% 30%,rgba(0,229,160,.06) 0%,transparent 70%),radial-gradient(ellipse 500px 500px at 80% 70%,rgba(59,130,246,.05) 0%,transparent 70%),var(--bg0)}
.lc{position:relative;width:100%;max-width:400px;padding:40px;background:var(--bg2);border:1px solid var(--bd);border-radius:var(--r);box-shadow:var(--shL);animation:si .4s ease}
.llo{text-align:center;margin-bottom:32px}
.llo .lbx{width:56px;height:56px;background:var(--ac);border-radius:var(--r);display:inline-flex;align-items:center;justify-content:center;color:#080b16;font-weight:900;font-size:1.5rem;margin-bottom:14px}
.llo h1{font-size:1.2rem;font-weight:700}.llo p{color:var(--t3);font-size:.85rem;margin-top:4px}
.le{background:var(--dnD);border:1px solid var(--dnB);color:var(--dn);padding:10px 14px;border-radius:var(--rs);font-size:.85rem;margin-bottom:16px;display:none}
.le.show{display:block;animation:fi .2s ease}
.spin{width:28px;height:28px;border:3px solid var(--bd);border-top-color:var(--ac);border-radius:50%;animation:sp .8s linear infinite;margin:40px auto}
@keyframes fi{from{opacity:0}to{opacity:1}}
@keyframes fsd{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:translateY(0)}}
@keyframes si{from{opacity:0;transform:scale(.95)}to{opacity:1;transform:scale(1)}}
@keyframes sp{to{transform:rotate(360deg)}}
@media(max-width:900px){.sidebar{width:60px;min-width:60px}.si span:not(.ii){display:none}.si{justify-content:center;padding:10px}.si .ii{margin:0}.ndd{width:300px;left:-100px}}
@media(max-width:600px){.main{padding:16px}.sg{grid-template-columns:1fr 1fr}.fr{grid-template-columns:1fr}.dzs{flex-direction:column}.header{padding:0 12px}.lc{margin:16px;padding:28px}}
"""

# ═══════════════════════════════════════════════════════════════
# JS مشترک
# ═══════════════════════════════════════════════════════════════

JS_COMMON = """
const A={async g(u){const r=await fetch(u);const d=await r.json();if(!r.ok)throw new Error(d.error||'خطایی رخ داد');return d},async p(u,b){const r=await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});const d=await r.json();if(!r.ok)throw new Error(d.error||'خطایی رخ داد');return d},async u(u,b){const r=await fetch(u,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)});const d=await r.json();if(!r.ok)throw new Error(d.error||'خطایی رخ داد');return d},async d(u){const r=await fetch(u,{method:'DELETE'});const d=await r.json();if(!r.ok)throw new Error(d.error||'خطایی رخ داد');return d},async up(u,f){const r=await fetch(u,{method:'POST',body:f});const d=await r.json();if(!r.ok)throw new Error(d.error||'خطایی رخ داد');return d}};
function toast(m,t='s'){const c=document.getElementById('tc');if(!c)return;const e=document.createElement('div');e.className='ts ts-'+t;e.innerHTML='<span>'+m+'</span><button onclick="this.parentElement.remove()">&times;</button>';c.appendChild(e);requestAnimationFrame(()=>e.classList.add('show'));setTimeout(()=>{e.classList.remove('show');setTimeout(()=>e.remove(),300)},4500)}
function om(id){const m=document.getElementById(id);if(m){m.classList.add('active');document.body.style.overflow='hidden'}}
function cm(id){const m=document.getElementById(id);if(m){m.classList.remove('active');document.body.style.overflow=''}}
function al(a){const m={create_section:'ایجاد بخش',delete_section:'حذف بخش',add_employees:'افزودن کارکنان',upload_employees:'آپلود اکسل',delete_employee:'حذف کارمند',transfer:'انتقال مستقیم',transfer_initiated:'درخواست انتقال',transfer_accepted:'پذیرش انتقال',transfer_rejected:'رد انتقال',settlement:'تسویه',create_user:'ایجاد کاربر',update_user:'ویرایش کاربر',delete_user:'حذف کاربر',change_password:'تغییر رمز',change_owner:'تغییر مالک بخش'};return m[a]||a}
function sl(s){const m={pending:'در انتظار تایید',accepted:'پذیرفته شده',rejected:'رد شده',completed:'تکمیل شده'};return m[s]||s}
function sc(s){const m={pending:'pen',accepted:'acc',rejected:'rej',completed:'com'};return m[s]||s}
document.addEventListener('click',e=>{if(e.target.classList.contains('mo')){e.target.classList.remove('active');document.body.style.overflow=''}});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){document.querySelectorAll('.mo.active').forEach(m=>m.classList.remove('active'));document.body.style.overflow=''}});
"""

# ═══════════════════════════════════════════════════════════════
# HTML صفحه ورود
# ═══════════════════════════════════════════════════════════════

HTML_LOGIN = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>ورود - سیستم مدیریت منابع انسانی</title>
<style>""" + CSS + """</style>
</head>
<body>
<div class="lp"><div class="lbg"></div>
<div class="lc">
<div class="llo"><div class="lbx">HR</div><h1>سیستم مدیریت منابع انسانی</h1><p>برای ورود نام کاربری و کد ورود خود را وارد کنید</p></div>
<div id="le" class="le"></div>
<form id="lf" onsubmit="hl(event)">
<div class="fg"><label class="fl">نام کاربری</label><input type="text" id="lu" placeholder="نام کاربری" autocomplete="username" required></div>
<div class="fg"><label class="fl">کد ورود</label><input type="password" id="lpw" placeholder="کد ورود" autocomplete="current-password" required></div>
<button type="submit" class="btn btn-p" style="width:100%;justify-content:center;margin-top:8px" id="lbtn">ورود به سیستم</button>
</form>
</div></div>
<div id="tc"></div>
<script>""" + JS_COMMON + """
async function hl(e){e.preventDefault();const b=document.getElementById('lbtn'),er=document.getElementById('le');er.classList.remove('show');b.disabled=true;b.textContent='در حال ورود...';try{const r=await A.p('/api/login',{username:document.getElementById('lu').value.trim(),password:document.getElementById('lpw').value.trim()});window.location.href=r.redirect}catch(err){er.textContent=err.message;er.classList.add('show');b.disabled=false;b.textContent='ورود به سیستم'}}
document.getElementById('lu').focus();
</script></body></html>"""

# ═══════════════════════════════════════════════════════════════
# HTML صفحه مدیر
# ═══════════════════════════════════════════════════════════════

HTML_ADMIN = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>مدیریت - سیستم منابع انسانی</title>
<style>""" + CSS + """</style>
</head>
<body>
<header class="header">
<div class="hlogo"><div class="lb">HR</div><span>پنل مدیریت</span></div>
<div class="hacts">
<span class="huser">مدیر سیستم</span>
<div style="position:relative">
<button class="nbtn" onclick="tn()" id="nt">&#x1F514;<span class="nbdg" id="nc" style="display:none">0</span></button>
<div class="ndd" id="nd"><div class="nddh"><h4>اعلان‌ها</h4><button class="btn btn-g btn-sm" onclick="mra()">خواندن همه</button></div><div id="nl"><div class="ne">اعلانی وجود ندارد</div></div></div>
</div>
<a href="/logout" class="btn btn-g btn-sm">خروج</a>
</div></header>
<div class="layout">
<aside class="sidebar">
<nav class="snav">
<button class="si active" data-p="ov" onclick="sp('ov')"><span class="ii">&#x1F4CA;</span><span>نمای کلی</span></button>
<button class="si" data-p="sec" onclick="sp('sec')"><span class="ii">&#x1F3E2;</span><span>بخش‌ها</span></button>
<button class="si" data-p="usr" onclick="sp('usr')"><span class="ii">&#x1F465;</span><span>کاربران</span></button>
<button class="si" data-p="trn" onclick="sp('trn')"><span class="ii">&#x1F504;</span><span>انتقال‌ها</span></button>
<button class="si" data-p="stl" onclick="sp('stl')"><span class="ii">&#x1F4B0;</span><span>تسویه‌ها</span></button>
<button class="si" data-p="aud" onclick="sp('aud')"><span class="ii">&#x1F4DD;</span><span>گزارش تغییرات</span></button>
</nav>
<div class="sft"><button class="si" onclick="om('mpw')"><span class="ii">&#x1F511;</span><span>تغییر کد ورود</span></button></div>
</aside>
<main class="main" id="mc">
<div id="p-ov" class="page active"></div>
<div id="p-sec" class="page"></div>
<div id="p-sd" class="page"></div>
<div id="p-usr" class="page"></div>
<div id="p-trn" class="page"></div>
<div id="p-stl" class="page"></div>
<div id="p-aud" class="page"></div>
</main></div>

<div class="mo" id="msec"><div class="md"><div class="mh"><h3>ایجاد بخش جدید</h3><button class="mx" onclick="cm('msec')">&times;</button></div><div class="mb"><div class="fg"><label class="fl">نام بخش</label><input type="text" id="sni" placeholder="مثلاً: تولید آلبالو"></div></div><div class="mf"><button class="btn btn-p" onclick="cs()">ایجاد</button><button class="btn btn-g" onclick="cm('msec')">انصراف</button></div></div></div>

<div class="mo" id="memp"><div class="md"><div class="mh"><h3>افزودن کارمند</h3><button class="mx" onclick="cm('memp')">&times;</button></div><div class="mb"><div id="erows"></div><button class="btn btn-g btn-sm" onclick="aer()" style="margin-top:8px">+ افزودن ردیف</button></div><div class="mf"><button class="btn btn-p" onclick="se()">ذخیره</button><button class="btn btn-g" onclick="cm('memp')">انصراف</button></div></div></div>

<div class="mo" id="mup"><div class="md"><div class="mh"><h3>آپلود فایل اکسل</h3><button class="mx" onclick="cm('mup')">&times;</button></div><div class="mb"><p class="fh" style="margin-bottom:12px">فایل باید شامل ستون‌های «نام»، «نام خانوادگی» و «کد پرسنلی» باشد.</p><input type="file" id="efile" accept=".xlsx,.xls"></div><div class="mf"><button class="btn btn-p" onclick="ue()">آپلود</button><button class="btn btn-g" onclick="cm('mup')">انصراف</button></div></div></div>

<div class="mo" id="mtr"><div class="md"><div class="mh"><h3>انتقال کارمند</h3><button class="mx" onclick="cm('mtr')">&times;</button></div><div class="mb"><p id="tei" style="margin-bottom:14px;font-weight:600"></p><div class="fg"><label class="fl">بخش مقصد</label><select id="tdes"></select></div></div><div class="mf"><button class="btn btn-p" onclick="ct()">انجام انتقال</button><button class="btn btn-g" onclick="cm('mtr')">انصراف</button></div></div></div>

<div class="mo" id="musr"><div class="md"><div class="mh"><h3 id="mut">ایجاد کاربر</h3><button class="mx" onclick="cm('musr')">&times;</button></div><div class="mb">
<input type="hidden" id="euid">
<div class="fg"><label class="fl">نام کاربری</label><input type="text" id="uun" placeholder="نام کاربری برای ورود"></div>
<div class="fg"><label class="fl">کد ورود</label><input type="password" id="upw" placeholder="کد ورود"><p class="fh" id="pwh">حداقل ۳ کاراکتر</p></div>
<div class="fg"><label class="fl">نام نمایشی</label><input type="text" id="udn" placeholder="مثلاً: مسئول بخش آلبالو"></div>
</div><div class="mf"><button class="btn btn-p" onclick="su()">ذخیره</button><button class="btn btn-g" onclick="cm('musr')">انصراف</button></div></div></div>

<div class="mo" id="mow"><div class="md"><div class="mh"><h3>تغییر مالک بخش</h3><button class="mx" onclick="cm('mow')">&times;</button></div><div class="mb"><div class="fg"><label class="fl">مالک جدید</label><select id="ownsel"></select></div></div><div class="mf"><button class="btn btn-p" onclick="co()">تغییر</button><button class="btn btn-g" onclick="cm('mow')">انصراف</button></div></div></div>

<div class="mo" id="mpw"><div class="md"><div class="mh"><h3>تغییر کد ورود مدیر</h3><button class="mx" onclick="cm('mpw')">&times;</button></div><div class="mb"><div class="fg"><label class="fl">کد ورود فعلی</label><input type="password" id="opw"></div><div class="fg"><label class="fl">کد ورود جدید</label><input type="password" id="npw"></div></div><div class="mf"><button class="btn btn-p" onclick="cpw()">تغییر</button><button class="btn btn-g" onclick="cm('mpw')">انصراف</button></div></div></div>

<div class="mo" id="mcf"><div class="md" style="max-width:400px"><div class="mh"><h3>تایید عملیات</h3><button class="mx" onclick="cm('mcf')">&times;</button></div><div class="mb"><p id="cfm"></p></div><div class="mf"><button class="btn btn-d" id="cfb">تایید</button><button class="btn btn-g" onclick="cm('mcf')">انصراف</button></div></div></div>

<div id="tc"></div>
<script>""" + JS_COMMON + """
let S={sections:[],selSec:null,employees:[],users:[],transfers:[],settlements:[],auditLog:[],notifications:[],cp:'ov',trEid:null,sq:''};
async function init(){try{await Promise.all([ls(),lu(),lt(),lst(),la(),ln()]);rp()}catch(e){toast(e.message,'e')}}
async function ls(){S.sections=await A.g('/api/sections')}
async function lu(){S.users=await A.g('/api/users')}
async function lt(){S.transfers=await A.g('/api/transfers')}
async function lst(){S.settlements=await A.g('/api/settlements')}
async function la(){S.auditLog=await A.g('/api/audit-log')}
async function ln(){S.notifications=await A.g('/api/notifications');const u=S.notifications.filter(n=>!n.read).length;const b=document.getElementById('nc');if(u>0){b.style.display='flex';b.textContent=u>9?'9+':u}else{b.style.display='none'}rnl()}
function sp(p){S.cp=p;if(p!=='sd')S.selSec=null;document.querySelectorAll('.si[data-p]').forEach(e=>e.classList.toggle('active',e.dataset.p===p));document.querySelectorAll('.page').forEach(e=>e.classList.remove('active'));const t=document.getElementById('p-'+p);if(t)t.classList.add('active');rp()}
function rp(){const m={ov:rov,sec:rsec,sd:rsd,usr:rusr,trn:rtrn,stl:rstl,aud:raud};(m[S.cp]||rov)()}

function rov(){
const te=S.sections.reduce((s,x)=>s+x.employee_count,0),pn=S.transfers.filter(t=>t.status==='pending').length;
document.getElementById('p-ov').innerHTML=`<h2 class="pt">نمای کلی</h2>
<div class="sg">
<div class="sc"><span class="sl">تعداد بخش‌ها</span><span class="sv a1">${S.sections.length}</span></div>
<div class="sc"><span class="sl">کل کارکنان</span><span class="sv i1">${te}</span></div>
<div class="sc"><span class="sl">انتقال‌های در انتظار</span><span class="sv w1">${pn}</span></div>
<div class="sc"><span class="sl">تسویه‌ها</span><span class="sv d1">${S.settlements.length}</span></div>
<div class="sc"><span class="sl">کاربران</span><span class="sv">${S.users.length}</span></div>
</div>
 ${pn>0?`<div class="card" style="border-color:var(--wnB);margin-bottom:20px"><h3 style="color:var(--wn);margin-bottom:12px;font-size:.95rem">انتقال‌های در انتظار تایید</h3>${S.transfers.filter(t=>t.status==='pending').map(t=>`<div class="pc"><div class="pch"><span class="pn">${t.employee.name} ${t.employee.family}</span><span class="pk">کد: ${t.employee.code}</span></div><div class="pf">از: ${sn(t.from_section)} ← به: ${sn(t.to_section)} | توسط: ${t.initiated_by}</div><div class="pa"><button class="btn btn-p btn-sm" onclick="at('${t.id}')">پذیرش</button><button class="btn btn-d btn-sm" onclick="rt('${t.id}')">رد</button></div></div>`).join('')}</div>`:''}
<div class="card"><h3 style="margin-bottom:14px;font-size:.95rem">آخرین فعالیت‌ها</h3>${S.auditLog.length===0?'<p style="color:var(--t3)">فعالیتی ثبت نشده</p>':S.auditLog.slice(0,8).map(l=>`<div class="li"><span class="lt">${l.timestamp}</span><span class="la">${al(l.action)}</span><span class="lu">${l.user}</span><span class="ld">${l.details}</span></div>`).join('')}</div>`}

function rsec(){
document.getElementById('p-sec').innerHTML=`<div class="tb"><h2 class="pt" style="margin-bottom:0">بخش‌ها</h2><div class="tb-sp"></div><button class="btn btn-p" onclick="om('msec');document.getElementById('sni').focus()">+ ایجاد بخش</button></div>
 ${S.sections.length===0?'<div class="es"><div class="ei">&#x1F3E2;</div><p>بخشی ایجاد نشده است</p></div>':`<div class="sec-g">${S.sections.map(s=>`<div class="secc" onclick="osd('${s.id}')"><button class="xsec" onclick="event.stopPropagation();cds('${s.id}','${s.name}')">&times;</button><div class="sn">${s.name}</div><div class="scn"><span>${s.employee_count}</span> نفر</div><div class="sow">مالک: ${s.owner_name||'مدیر سیستم'}</div></div>`).join('')}</div>`}`}

async function cs(){const n=document.getElementById('sni').value.trim();if(!n)return toast('نام بخش را وارد کنید','e');try{await A.p('/api/sections',{name:n});toast('بخش ایجاد شد');cm('msec');document.getElementById('sni').value='';await ls();rp()}catch(e){toast(e.message,'e')}}
function cds(id,nm){document.getElementById('cfm').textContent='آیا از حذف بخش «'+nm+'» اطمینان دارید؟';document.getElementById('cfb').onclick=async()=>{try{await A.d('/api/sections/'+id);toast('بخش حذف شد');cm('mcf');await ls();await lu();await lt();rp()}catch(e){toast(e.message,'e')}};om('mcf')}

async function osd(sid){S.selSec=sid;S.employees=await A.g('/api/sections/'+sid+'/employees');S.sq='';document.querySelectorAll('.si[data-p]').forEach(e=>e.classList.remove('active'));document.querySelectorAll('.page').forEach(e=>e.classList.remove('active'));document.getElementById('p-sd').classList.add('active');S.cp='sd';rsd()}

function rsd(){
const sec=S.sections.find(s=>s.id===S.selSec);if(!sec)return sp('sec');
const q=S.sq.toLowerCase(),f=q?S.employees.filter(e=>e.name.includes(q)||e.family.includes(q)||e.code.includes(q)):S.employees;
const other=S.sections.filter(s=>s.id!==S.selSec);
document.getElementById('p-sd').innerHTML=`<div class="tb"><button class="btn btn-g btn-sm" onclick="sp('sec')">&#x2190; بازگشت</button><div class="tb-sp"></div>
<button class="btn btn-g btn-sm" onclick="owm('${S.selSec}')">&#x1F464; تغییر مالک</button>
<button class="btn btn-g btn-sm" onclick="window.open('/api/sections/${S.selSec}/export','_blank')">&#x1F4E5; خروجی اکسل</button>
<button class="btn btn-g btn-sm" onclick="om('mup')">&#x1F4C1; آپلود اکسل</button>
<button class="btn btn-p btn-sm" onclick="oae()">+ افزودن کارمند</button></div>
<h2 class="pt">${sec.name} <span style="font-size:.85rem;color:var(--t3);font-weight:400">(${f.length} نفر)</span></h2>
<div class="tb"><div class="sb"><span class="sic">&#x1F50D;</span><input type="text" placeholder="جستجو..." value="${S.sq}" oninput="S.sq=this.value;rsd()"></div></div>
 ${f.length===0?'<div class="es"><div class="ei">&#x1F464;</div><p>کارمندی وجود ندارد</p></div>':`<div class="tw" style="margin-bottom:16px"><table><thead><tr><th>ردیف</th><th>نام</th><th>نام خانوادگی</th><th>کد پرسنلی</th><th>عملیات</th></tr></thead><tbody>${f.map((e,i)=>`<tr draggable="true" data-eid="${e.id}" ondragstart="ds(ev,'${e.id}','${e.name} ${e.family}','${e.code}')" ondragend="de(ev)"><td>${i+1}</td><td>${e.name}</td><td>${e.family}</td><td style="font-weight:600;direction:ltr;text-align:right">${e.code}</td><td><button class="btn btn-d btn-sm btn-ic" onclick="cde('${e.id}','${e.name} ${e.family}')" title="حذف">&times;</button></td></tr>`).join('')}</tbody></table></div>`}
 ${other.length>0?`<div class="dzs"><div class="dz" ondragover="ev.preventDefault();this.classList.add('da')" ondragleave="this.classList.remove('da')" ondrop="dt(ev)"><span class="di">&#x1F504;</span><span class="dl">انتقال به بخش دیگر</span><span class="dh">کارمند را اینجا رها کنید</span></div><div class="dz sz" ondragover="ev.preventDefault();this.classList.add('da')" ondragleave="this.classList.remove('da')" ondrop="dsel(ev)"><span class="di">&#x1F4B0;</span><span class="dl">انتقال به تسویه</span><span class="dh">کارمند را اینجا رها کنید</span></div></div>`:''}`}

function oae(){document.getElementById('erows').innerHTML='';aer();aer();aer();om('memp')}
function aer(){const c=document.getElementById('erows'),d=document.createElement('div');d.className='fr';d.style.marginBottom='8px';d.innerHTML=`<input type="text" placeholder="نام" class="en"><input type="text" placeholder="نام خانوادگی" class="ef"><input type="text" placeholder="کد پرسنلی" class="ec" style="direction:ltr;text-align:right"><button class="btn btn-g btn-sm btn-ic" onclick="this.parentElement.remove()">&times;</button>`;c.appendChild(d)}
async function se(){const rows=document.querySelectorAll('#erows .fr'),emps=[];rows.forEach(r=>{const n=r.querySelector('.en').value.trim(),f=r.querySelector('.ef').value.trim(),c=r.querySelector('.ec').value.trim();if(n||f||c)emps.push({name:n,family:f,code:c})});if(!emps.length)return toast('حداقل یک کارمند وارد کنید','e');try{const res=await A.p('/api/sections/'+S.selSec+'/employees',{employees:emps});cm('memp');if(res.errors.length)toast(res.added.length+' اضافه شد، '+res.errors.length+' خطا','w');else toast(res.added.length+' نفر اضافه شد');await ls();S.employees=await A.g('/api/sections/'+S.selSec+'/employees');rsd()}catch(e){toast(e.message,'e')}}
async function ue(){const f=document.getElementById('efile').files[0];if(!f)return toast('فایلی انتخاب نشده','e');const fd=new FormData();fd.append('file',f);try{const res=await A.up('/api/sections/'+S.selSec+'/employees/upload',fd);cm('mup');document.getElementById('efile').value='';if(res.errors.length)toast(res.added.length+' اضافه شد، '+res.errors.length+' خطا','w');else toast(res.added.length+' نفر اضافه شد');await ls();S.employees=await A.g('/api/sections/'+S.selSec+'/employees');rsd()}catch(e){toast(e.message,'e')}}
function cde(id,nm){document.getElementById('cfm').textContent='آیا از حذف «'+nm+'» اطمینان دارید؟';document.getElementById('cfb').onclick=async()=>{try{await A.d('/api/sections/'+S.selSec+'/employees/'+id);toast('حذف شد');cm('mcf');await ls();S.employees=await A.g('/api/sections/'+S.selSec+'/employees');rsd()}catch(e){toast(e.message,'e')}};om('mcf')}

let dEid=null,dEnm='',dEcd='';
function ds(e,id,nm,cd){dEid=id;dEnm=nm;dEcd=cd;e.dataTransfer.effectAllowed='move';e.target.classList.add('dragging')}
function de(e){e.target.classList.remove('dragging');document.querySelectorAll('.dz').forEach(z=>z.classList.remove('da'))}
function dt(e){e.preventDefault();e.currentTarget.classList.remove('da');if(!dEid)return;const o=S.sections.filter(s=>s.id!==S.selSec);if(!o.length)return toast('بخش مقصدی وجود ندارد','e');S.trEid=dEid;document.getElementById('tei').textContent=dEnm+' (کد: '+dEcd+')';document.getElementById('tdes').innerHTML=o.map(s=>`<option value="${s.id}">${s.name}</option>`).join('');om('mtr')}
function dsel(e){e.preventDefault();e.currentTarget.classList.remove('da');if(!dEid)return;document.getElementById('cfm').textContent='آیا از انتقال «'+dEnm+'» به تسویه اطمینان دارید؟';document.getElementById('cfb').onclick=async()=>{try{await A.p('/api/settlements',{employee_id:dEid,from_section:S.selSec});toast('به تسویه منتقل شد');cm('mcf');await ls();await lst();S.employees=await A.g('/api/sections/'+S.selSec+'/employees');rsd()}catch(e){toast(e.message,'e')}};om('mcf')}
async function ct(){const d=document.getElementById('tdes').value;if(!d)return toast('بخش مقصد را انتخاب کنید','e');try{await A.p('/api/transfers',{employee_id:S.trEid,from_section:S.selSec,to_section:d});toast('انتقال انجام شد');cm('mtr');await ls();await lt();await ln();S.employees=await A.g('/api/sections/'+S.selSec+'/employees');rsd()}catch(e){toast(e.message,'e')}}

function owm(sid){const sel=document.getElementById('ownsel');sel.innerHTML='<option value="">مدیر سیستم</option>'+S.users.map(u=>`<option value="${u.id}">${u.display_name} (${u.username})</option>`).join('');const sec=S.sections.find(s=>s.id===sid);sel.value=sec&&sec.owner?sec.owner:'';om('mow');document.getElementById('ownsel').dataset.sid=sid}
async function co(){const sid=document.getElementById('ownsel').dataset.sid;const ow=document.getElementById('ownsel').value||null;try{await A.u('/api/sections/'+sid+'/owner',{owner:ow});toast('مالک تغییر کرد');cm('mow');await ls();rp()}catch(e){toast(e.message,'e')}}

function rusr(){
document.getElementById('p-usr').innerHTML=`<div class="tb"><h2 class="pt" style="margin-bottom:0">کاربران</h2><div class="tb-sp"></div><button class="btn btn-p" onclick="oum()">+ ایجاد کاربر</button></div>
 ${S.users.length===0?'<div class="es"><div class="ei">&#x1F465;</div><p>کاربری ایجاد نشده</p></div>':`<div class="tw"><table><thead><tr><th>نام کاربری</th><th>نام نمایشی</th><th>بخش‌های تحت مدیریت</th><th>عملیات</th></tr></thead><tbody>${S.users.map(u=>{const secs=S.sections.filter(s=>s.owner===u.id).map(s=>s.name);return`<tr><td style="direction:ltr;text-align:right">${u.username}</td><td>${u.display_name}</td><td>${secs.length?secs.join('، '):'<span style="color:var(--t3)">--</span>'}</td><td><button class="btn btn-g btn-sm" onclick="eu('${u.id}')">ویرایش</button><button class="btn btn-d btn-sm" onclick="cdu('${u.id}','${u.display_name}')">حذف</button></td></tr>`}).join('')}</tbody></table></div>`}`}

function oum(){document.getElementById('mut').textContent='ایجاد کاربر';document.getElementById('euid').value='';document.getElementById('uun').value='';document.getElementById('uun').disabled=false;document.getElementById('upw').value='';document.getElementById('udn').value='';document.getElementById('pwh').textContent='حداقل ۳ کاراکتر';om('musr')}
function eu(id){document.getElementById('mut').textContent='ویرایش کاربر';document.getElementById('euid').value=id;const u=S.users.find(x=>x.id===id);if(u){document.getElementById('uun').value=u.username;document.getElementById('uun').disabled=true;document.getElementById('upw').value='';document.getElementById('udn').value=u.display_name;document.getElementById('pwh').textContent='خالی بگذارید برای بدون تغییر'}om('musr')}
async function su(){const eid=document.getElementById('euid').value,un=document.getElementById('uun').value.trim(),pw=document.getElementById('upw').value.trim(),dn=document.getElementById('udn').value.trim();if(!un)return toast('نام کاربری الزامی است','e');if(!eid&&!pw)return toast('کد ورود الزامی است','e');try{if(eid){const b={display_name:dn};if(pw)b.password=pw;await A.u('/api/users/'+eid,b);toast('ویرایش شد')}else{await A.p('/api/users',{username:un,password:pw,display_name:dn});toast('کاربر ایجاد شد')}cm('musr');await lu();rp()}catch(e){toast(e.message,'e')}}
function cdu(id,nm){document.getElementById('cfm').textContent='آیا از حذف کاربر «'+nm+'» اطمینان دارید؟ بخش‌های تحت مدیریت او به مدیر سیستم منتقل می‌شود.';document.getElementById('cfb').onclick=async()=>{try{await A.d('/api/users/'+id);toast('حذف شد');cm('mcf');await lu();await ls();rp()}catch(e){toast(e.message,'e')}};om('mcf')}

function rtrn(){const el=document.getElementById('p-trn'),fv=el.querySelector('.tf')?.value||'all',fl=fv==='all'?S.transfers:S.transfers.filter(t=>t.status===fv);
el.innerHTML=`<div class="tb"><h2 class="pt" style="margin-bottom:0">انتقال‌ها</h2><div class="tb-sp"></div><select class="tf" onchange="rtrn()" style="width:auto"><option value="all" ${fv==='all'?'selected':''}>همه</option><option value="pending" ${fv==='pending'?'selected':''}>در انتظار</option><option value="accepted" ${fv==='accepted'?'selected':''}>پذیرفته شده</option><option value="completed" ${fv==='completed'?'selected':''}>تکمیل شده</option><option value="rejected" ${fv==='rejected'?'selected':''}>رد شده</option></select></div>
 ${fl.length===0?'<div class="es"><div class="ei">&#x1F504;</div><p>انتقالی یافت نشد</p></div>':`<div class="tw"><table><thead><tr><th>کارمند</th><th>کد پرسنلی</th><th>از بخش</th><th>به بخش</th><th>وضعیت</th><th>توسط</th><th>تاریخ</th><th>عملیات</th></tr></thead><tbody>${fl.map(t=>`<tr><td>${t.employee.name} ${t.employee.family}</td><td style="direction:ltr;text-align:right">${t.employee.code}</td><td>${sn(t.from_section)}</td><td>${sn(t.to_section)}</td><td><span class="badge b-${sc(t.status)}">${sl(t.status)}</span></td><td>${t.initiated_by}</td><td style="font-size:.82rem;color:var(--t3);white-space:nowrap">${t.timestamp}</td><td>${t.status==='pending'?`<button class="btn btn-p btn-sm" onclick="at('${t.id}')">پذیرش</button><button class="btn btn-d btn-sm" onclick="rt('${t.id}')">رد</button>`:'-'}</td></tr>`).join('')}</tbody></table></div>`}`}

async function at(tid){try{await A.p('/api/transfers/'+tid+'/accept',{});toast('پذیرفته شد');await ls();await lt();await ln();rp()}catch(e){toast(e.message,'e')}}
async function rt(tid){try{await A.p('/api/transfers/'+tid+'/reject',{});toast('رد شد');await ls();await lt();await ln();rp()}catch(e){toast(e.message,'e')}}

function rstl(){document.getElementById('p-stl').innerHTML=`<div class="tb"><h2 class="pt" style="margin-bottom:0">تسویه‌ها</h2><div class="tb-sp"></div><button class="btn btn-g btn-sm" onclick="window.open('/api/settlements/export','_blank')">&#x1F4E5; خروجی اکسل</button></div>
 ${S.settlements.length===0?'<div class="es"><div class="ei">&#x1F4B0;</div><p>تسویه‌ای ثبت نشده</p></div>':`<div class="tw"><table><thead><tr><th>کارمند</th><th>کد پرسنلی</th><th>بخش مبدأ</th><th>توسط</th><th>تاریخ</th></tr></thead><tbody>${S.settlements.map(s=>`<tr><td>${s.employee.name} ${s.employee.family}</td><td style="direction:ltr;text-align:right">${s.employee.code}</td><td>${s.from_section_name}</td><td>${s.initiated_by}</td><td style="font-size:.82rem;color:var(--t3);white-space:nowrap">${s.timestamp}</td></tr>`).join('')}</tbody></table></div>`}`}

function raud(){document.getElementById('p-aud').innerHTML=`<div class="tb"><h2 class="pt" style="margin-bottom:0">گزارش تغییرات</h2><div class="tb-sp"></div><button class="btn btn-g btn-sm" onclick="window.open('/api/audit-log/export','_blank')">&#x1F4E5; خروجی اکسل</button></div>
 ${S.auditLog.length===0?'<div class="es"><div class="ei">&#x1F4DD;</div><p>فعالیتی ثبت نشده</p></div>':`<div class="card">${S.auditLog.map(l=>`<div class="li"><span class="lt">${l.timestamp}</span><span class="la">${al(l.action)}</span><span class="lu">${l.user}</span><span class="ld">${l.details}</span></div>`).join('')}</div>`}`}

function tn(){document.getElementById('nd').classList.toggle('show')}
function rnl(){const el=document.getElementById('nl');if(!S.notifications.length){el.innerHTML='<div class="ne">اعلانی وجود ندارد</div>';return}el.innerHTML=S.notifications.slice(0,20).map(n=>`<div class="ni ${n.read?'':'ur'}" onclick="mr('${n.id}')">${n.message}<span class="nt">${n.timestamp}</span></div>`).join('')}
async function mr(nid){try{await A.p('/api/notifications/'+nid+'/read',{});await ln()}catch(e){}}
async function mra(){try{await A.p('/api/notifications/read-all',{});await ln();toast('خوانده شد')}catch(e){}}
async function cpw(){const o=document.getElementById('opw').value,n=document.getElementById('npw').value.trim();if(!o||!n)return toast('هر دو فیلد الزامی است','e');try{await A.p('/api/admin/change-password',{old_password:o,new_password:n});toast('تغییر کرد');cm('mpw');document.getElementById('opw').value='';document.getElementById('npw').value=''}catch(e){toast(e.message,'e')}}
function sn(sid){const s=S.sections.find(x=>x.id===sid);return s?s.name:(sid||'نامشخص')}
document.addEventListener('click',e=>{const dd=document.getElementById('nd'),btn=document.getElementById('nt');if(dd&&!dd.contains(e.target)&&!btn.contains(e.target))dd.classList.remove('show')});
document.addEventListener('DOMContentLoaded',init);
</script></body></html>"""

# ═══════════════════════════════════════════════════════════════
# HTML صفحه کاربر (مسئول)
# ═══════════════════════════════════════════════════════════════

HTML_USER = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>پنل کاربر - سیستم منابع انسانی</title>
<style>""" + CSS + """</style>
</head>
<body>
<header class="header">
<div class="hlogo"><div class="lb">HR</div><span id="hsn">پنل کاربر</span></div>
<div class="hacts">
<span class="huser" id="hun"></span>
<div style="position:relative">
<button class="nbtn" onclick="tn()" id="nt">&#x1F514;<span class="nbdg" id="nc" style="display:none">0</span></button>
<div class="ndd" id="nd"><div class="nddh"><h4>اعلان‌ها</h4><button class="btn btn-g btn-sm" onclick="mra()">خواندن همه</button></div><div id="nl"><div class="ne">اعلانی وجود ندارد</div></div></div>
</div>
<a href="/logout" class="btn btn-g btn-sm">خروج</a>
</div></header>
<main class="main"><div id="ar"><div class="spin"></div></div></main>

<div class="mo" id="msec"><div class="md"><div class="mh"><h3>ایجاد بخش جدید</h3><button class="mx" onclick="cm('msec')">&times;</button></div><div class="mb"><div class="fg"><label class="fl">نام بخش</label><input type="text" id="sni" placeholder="مثلاً: تولید آلبالو"></div></div><div class="mf"><button class="btn btn-p" onclick="cs()">ایجاد</button><button class="btn btn-g" onclick="cm('msec')">انصراف</button></div></div></div>

<div class="mo" id="memp"><div class="md"><div class="mh"><h3>افزودن کارمند</h3><button class="mx" onclick="cm('memp')">&times;</button></div><div class="mb"><div id="erows"></div><button class="btn btn-g btn-sm" onclick="aer()" style="margin-top:8px">+ افزودن ردیف</button></div><div class="mf"><button class="btn btn-p" onclick="se()">ذخیره</button><button class="btn btn-g" onclick="cm('memp')">انصراف</button></div></div></div>

<div class="mo" id="mup"><div class="md"><div class="mh"><h3>آپلود فایل اکسل</h3><button class="mx" onclick="cm('mup')">&times;</button></div><div class="mb"><p class="fh" style="margin-bottom:12px">فایل باید شامل ستون‌های «نام»، «نام خانوادگی» و «کد پرسنلی» باشد.</p><input type="file" id="efile" accept=".xlsx,.xls"></div><div class="mf"><button class="btn btn-p" onclick="ue()">آپلود</button><button class="btn btn-g" onclick="cm('mup')">انصراف</button></div></div></div>

<div class="mo" id="mtr"><div class="md"><div class="mh"><h3>انتقال کارمند</h3><button class="mx" onclick="cm('mtr')">&times;</button></div><div class="mb"><p id="tei" style="margin-bottom:14px;font-weight:600"></p><div class="fg"><label class="fl">بخش مقصد</label><select id="tdes"></select></div><p class="fh" style="color:var(--wn);margin-top:8px">توجه: پس از ارسال، کارمند منتظر تایید مسئول بخش مقصد خواهد بود.</p></div><div class="mf"><button class="btn btn-p" onclick="ct()">ارسال درخواست</button><button class="btn btn-g" onclick="cm('mtr')">انصراف</button></div></div></div>

<div class="mo" id="mcf"><div class="md" style="max-width:400px"><div class="mh"><h3>تایید عملیات</h3><button class="mx" onclick="cm('mcf')">&times;</button></div><div class="mb"><p id="cfm"></p></div><div class="mf"><button class="btn btn-d" id="cfb">تایید</button><button class="btn btn-g" onclick="cm('mcf')">انصراف</button></div></div></div>

<div id="tc"></div>
<script>""" + JS_COMMON + """
let S={me:null,uid:null,sections:[],mySections:[],selSec:null,employees:[],transfers:[],notifications:[],sq:'',trEid:null};

async function init(){try{S.me=await A.g('/api/me');S.uid=S.me.user_id;document.getElementById('hsn').textContent='پنل '+S.me.display_name;document.getElementById('hun').textContent=S.me.display_name;await Promise.all([ls(),lt(),ln()]);S.mySections=S.sections.filter(s=>s.owner===S.uid);if(!S.mySections.length){rns();return}rv()}catch(e){document.getElementById('ar').innerHTML='<p style="color:var(--dn);text-align:center;padding:40px">'+e.message+'</p>'}}
async function ls(){S.sections=await A.g('/api/sections')}
async function lt(){S.transfers=await A.g('/api/transfers')}
async function ln(){S.notifications=await A.g('/api/notifications');const u=S.notifications.filter(n=>!n.read).length;const b=document.getElementById('nc');if(u>0){b.style.display='flex';b.textContent=u>9?'9+':u}else{b.style.display='none'}rnl()}

function rns(){document.getElementById('ar').innerHTML=`<div style="text-align:center;padding:80px 24px"><div style="font-size:3.5rem;margin-bottom:16px;opacity:.3">&#x1F3E2;</div><h2 style="margin-bottom:12px">بخشی ایجاد نشده است</h2><p style="color:var(--t3);margin-bottom:24px">شما هنوز بخشی ایجاد نکرده‌اید. اولین بخش خود را بسازید.</p><button class="btn btn-p" onclick="om('msec');document.getElementById('sni').focus()" style="margin:0 auto">+ ایجاد اولین بخش</button></div>`}

function rv(){
const pi=S.transfers.filter(t=>t.status==='pending'&&S.mySections.some(s=>s.id===t.to_section));
const po=S.transfers.filter(t=>t.status==='pending'&&S.mySections.some(s=>s.id===t.from_section));
const te=S.mySections.reduce((s,x)=>s+x.employee_count,0);
document.getElementById('ar').innerHTML=`<div style="max-width:1200px;margin:0 auto">
<div class="sg">
<div class="sc"><span class="sl">بخش‌های من</span><span class="sv a1">${S.mySections.length}</span></div>
<div class="sc"><span class="sl">کل کارکنان</span><span class="sv i1">${te}</span></div>
<div class="sc"><span class="sl">درخواست دریافتی</span><span class="sv w1">${pi.length}</span></div>
<div class="sc"><span class="sl">درخواست ارسالی</span><span class="sv">${po.length}</span></div>
</div>
 ${pi.length>0?`<div class="card" style="border-color:var(--wnB);margin-bottom:20px"><h3 style="color:var(--wn);margin-bottom:12px;font-size:.95rem">درخواست‌های انتقال دریافتی (نیاز به تایید شما)</h3>${pi.map(t=>`<div class="pc"><div class="pch"><span class="pn">${t.employee.name} ${t.employee.family}</span><span class="pk">کد: ${t.employee.code}</span></div><div class="pf">از: ${sn(t.from_section)} | توسط: ${t.initiated_by} | ${t.timestamp}</div><div class="pa"><button class="btn btn-p btn-sm" onclick="at('${t.id}')">پذیرش</button><button class="btn btn-d btn-sm" onclick="rt('${t.id}')">رد</button></div></div>`).join('')}</div>`:''}
<div class="tb"><h2 class="pt" style="margin-bottom:0">بخش‌های من</h2><div class="tb-sp"></div><button class="btn btn-p" onclick="om('msec');document.getElementById('sni').focus()">+ ایجاد بخش</button></div>
<div class="sec-g">${S.mySections.map(s=>`<div class="secc" onclick="osd('${s.id}')"><button class="xsec" onclick="event.stopPropagation();cds('${s.id}','${s.name}')">&times;</button><div class="sn">${s.name}</div><div class="scn"><span>${s.employee_count}</span> نفر</div></div>`).join('')}</div>
 ${po.length>0?`<h2 class="pt" style="margin-top:28px">درخواست‌های ارسالی در انتظار</h2><div class="card">${po.map(t=>`<div class="pc" style="border-color:var(--infB)"><div class="pch"><span class="pn">${t.employee.name} ${t.employee.family}</span><span class="badge b-pen">در انتظار</span></div><div class="pf">به: ${sn(t.to_section)} | ${t.timestamp}</div></div>`).join('')}</div>`:''}
</div>`}

async function cs(){const n=document.getElementById('sni').value.trim();if(!n)return toast('نام بخش را وارد کنید','e');try{await A.p('/api/sections',{name:n});toast('بخش ایجاد شد');cm('msec');document.getElementById('sni').value='';await ls();S.mySections=S.sections.filter(s=>s.owner===S.uid);rv()}catch(e){toast(e.message,'e')}}
function cds(id,nm){document.getElementById('cfm').textContent='آیا از حذف بخش «'+nm+'» اطمینان دارید؟ کارکنان منتقل‌نشده به تسویه منتقل می‌شوند.';document.getElementById('cfb').onclick=async()=>{try{await A.d('/api/sections/'+id);toast('بخش حذف شد');cm('mcf');await ls();await lt();S.mySections=S.sections.filter(s=>s.owner===S.uid);rv()}catch(e){toast(e.message,'e')}};om('mcf')}

async function osd(sid){S.selSec=sid;S.employees=await A.g('/api/sections/'+sid+'/employees');S.sq='';rsd()}

function rsd(){
const sec=S.mySections.find(s=>s.id===S.selSec);if(!sec)return rv();
const q=S.sq.toLowerCase(),f=q?S.employees.filter(e=>e.name.includes(q)||e.family.includes(q)||e.code.includes(q)):S.employees;
const other=S.sections.filter(s=>s.id!==S.selSec);
document.getElementById('ar').innerHTML=`<div style="max-width:1200px;margin:0 auto">
<div class="tb"><button class="btn btn-g btn-sm" onclick="rv()">&#x2190; بازگشت به بخش‌ها</button><div class="tb-sp"></div>
<button class="btn btn-g btn-sm" onclick="window.open('/api/sections/${S.selSec}/export','_blank')">&#x1F4E5; خروجی اکسل</button>
<button class="btn btn-g btn-sm" onclick="om('mup')">&#x1F4C1; آپلود اکسل</button>
<button class="btn btn-p btn-sm" onclick="oae()">+ افزودن کارمند</button></div>
<h2 class="pt">${sec.name} <span style="font-size:.85rem;color:var(--t3);font-weight:400">(${f.length} نفر)</span></h2>
<div class="tb"><div class="sb"><span class="sic">&#x1F50D;</span><input type="text" placeholder="جستجو..." value="${S.sq}" oninput="S.sq=this.value;rsd()"></div></div>
 ${f.length===0?'<div class="es"><div class="ei">&#x1F464;</div><p>کارمندی وجود ندارد</p></div>':`<div class="tw" style="margin-bottom:16px"><table><thead><tr><th>ردیف</th><th>نام</th><th>نام خانوادگی</th><th>کد پرسنلی</th><th>عملیات</th></tr></thead><tbody>${f.map((e,i)=>`<tr draggable="true" ondragstart="ds(ev,'${e.id}','${e.name} ${e.family}','${e.code}')" ondragend="de(ev)"><td>${i+1}</td><td>${e.name}</td><td>${e.family}</td><td style="font-weight:600;direction:ltr;text-align:right">${e.code}</td><td><button class="btn btn-g btn-sm" onclick="stm('${e.id}','${e.name} ${e.family}','${e.code}')" title="انتقال">&#x1F504;</button><button class="btn btn-g btn-sm" onclick="stl('${e.id}','${e.name} ${e.family}')" title="تسویه" style="color:var(--wn)">&#x1F4B0;</button><button class="btn btn-d btn-sm btn-ic" onclick="cde('${e.id}','${e.name} ${e.family}')" title="حذف">&times;</button></td></tr>`).join('')}</tbody></table></div>`}
 ${other.length>0?`<div class="dzs"><div class="dz" ondragover="ev.preventDefault();this.classList.add('da')" ondragleave="this.classList.remove('da')" ondrop="dt(ev)"><span class="di">&#x1F504;</span><span class="dl">انتقال به بخش دیگر</span><span class="dh">کارمند را بکشید و رها کنید</span></div><div class="dz sz" ondragover="ev.preventDefault();this.classList.add('da')" ondragleave="this.classList.remove('da')" ondrop="dsel(ev)"><span class="di">&#x1F4B0;</span><span class="dl">انتقال به تسویه</span><span class="dh">کارمند را بکشید و رها کنید</span></div></div>`:''}
</div>`}

function oae(){document.getElementById('erows').innerHTML='';aer();aer();aer();om('memp')}
function aer(){const c=document.getElementById('erows'),d=document.createElement('div');d.className='fr';d.style.marginBottom='8px';d.innerHTML=`<input type="text" placeholder="نام" class="en"><input type="text" placeholder="نام خانوادگی" class="ef"><input type="text" placeholder="کد پرسنلی" class="ec" style="direction:ltr;text-align:right"><button class="btn btn-g btn-sm btn-ic" onclick="this.parentElement.remove()">&times;</button>`;c.appendChild(d)}
async function se(){const rows=document.querySelectorAll('#erows .fr'),emps=[];rows.forEach(r=>{const n=r.querySelector('.en').value.trim(),f=r.querySelector('.ef').value.trim(),c=r.querySelector('.ec').value.trim();if(n||f||c)emps.push({name:n,family:f,code:c})});if(!emps.length)return toast('حداقل یک کارمند وارد کنید','e');try{const res=await A.p('/api/sections/'+S.selSec+'/employees',{employees:emps});cm('memp');if(res.errors.length)toast(res.added.length+' اضافه شد، '+res.errors.length+' خطا','w');else toast(res.added.length+' نفر اضافه شد');await ls();S.mySections=S.sections.filter(s=>s.owner===S.uid);S.employees=await A.g('/api/sections/'+S.selSec+'/employees');rsd()}catch(e){toast(e.message,'e')}}
async function ue(){const f=document.getElementById('efile').files[0];if(!f)return toast('فایلی انتخاب نشده','e');const fd=new FormData();fd.append('file',f);try{const res=await A.up('/api/sections/'+S.selSec+'/employees/upload',fd);cm('mup');document.getElementById('efile').value='';if(res.errors.length)toast(res.added.length+' اضافه شد، '+res.errors.length+' خطا','w');else toast(res.added.length+' نفر اضافه شد');await ls();S.mySections=S.sections.filter(s=>s.owner===S.uid);S.employees=await A.g('/api/sections/'+S.selSec+'/employees');rsd()}catch(e){toast(e.message,'e')}}
function cde(id,nm){document.getElementById('cfm').textContent='آیا از حذف «'+nm+'» اطمینان دارید؟';document.getElementById('cfb').onclick=async()=>{try{await A.d('/api/sections/'+S.selSec+'/employees/'+id);toast('حذف شد');cm('mcf');await ls();S.mySections=S.sections.filter(s=>s.owner===S.uid);S.employees=await A.g('/api/sections/'+S.selSec+'/employees');rsd()}catch(e){toast(e.message,'e')}};om('mcf')}

let dEid=null,dEnm='',dEcd='';
function ds(e,id,nm,cd){dEid=id;dEnm=nm;dEcd=cd;e.dataTransfer.effectAllowed='move';e.target.classList.add('dragging')}
function de(e){e.target.classList.remove('dragging');document.querySelectorAll('.dz').forEach(z=>z.classList.remove('da'))}
function dt(e){e.preventDefault();e.currentTarget.classList.remove('da');if(!dEid)return;stm(dEid,dEnm,dEcd)}
function dsel(e){e.preventDefault();e.currentTarget.classList.remove('da');if(!dEid)return;stl(dEid,dEnm)}
function stm(id,nm,cd){const other=S.sections.filter(s=>s.id!==S.selSec);if(!other.length)return toast('بخش مقصدی وجود ندارد','e');S.trEid=id;document.getElementById('tei').textContent=nm+' (کد: '+cd+')';document.getElementById('tdes').innerHTML=other.map(s=>`<option value="${s.id}">${s.name}</option>`).join('');om('mtr')}
function stl(id,nm){document.getElementById('cfm').textContent='آیا از انتقال «'+nm+'» به تسویه اطمینان دارید؟';document.getElementById('cfb').onclick=async()=>{try{await A.p('/api/settlements',{employee_id:id,from_section:S.selSec});toast('به تسویه منتقل شد');cm('mcf');await ls();S.mySections=S.sections.filter(s=>s.owner===S.uid);S.employees=await A.g('/api/sections/'+S.selSec+'/employees');rsd()}catch(e){toast(e.message,'e')}};om('mcf')}
async function ct(){const d=document.getElementById('tdes').value;if(!d)return toast('بخش مقصد را انتخاب کنید','e');try{await A.p('/api/transfers',{employee_id:S.trEid,from_section:S.selSec,to_section:d});toast('درخواست انتقال ارسال شد');cm('mtr');await ls();await lt();await ln();S.mySections=S.sections.filter(s=>s.owner===S.uid);S.employees=await A.g('/api/sections/'+S.selSec+'/employees');rsd()}catch(e){toast(e.message,'e')}}

async function at(tid){try{await A.p('/api/transfers/'+tid+'/accept',{});toast('پذیرفته شد');await ls();await lt();await ln();S.mySections=S.sections.filter(s=>s.owner===S.uid);if(S.selSec)S.employees=await A.g('/api/sections/'+S.selSec+'/employees');S.selSec?rsd():rv()}catch(e){toast(e.message,'e')}}
async function rt(tid){try{await A.p('/api/transfers/'+tid+'/reject',{});toast('رد شد');await ls();await lt();await ln();S.mySections=S.sections.filter(s=>s.owner===S.uid);if(S.selSec)S.employees=await A.g('/api/sections/'+S.selSec+'/employees');S.selSec?rsd():rv()}catch(e){toast(e.message,'e')}}

function tn(){document.getElementById('nd').classList.toggle('show')}
function rnl(){const el=document.getElementById('nl');if(!S.notifications.length){el.innerHTML='<div class="ne">اعلانی وجود ندارد</div>';return}el.innerHTML=S.notifications.slice(0,20).map(n=>`<div class="ni ${n.read?'':'ur'}" onclick="mr('${n.id}')">${n.message}<span class="nt">${n.timestamp}</span></div>`).join('')}
async function mr(nid){try{await A.p('/api/notifications/'+nid+'/read',{});await ln()}catch(e){}}
async function mra(){try{await A.p('/api/notifications/read-all',{});await ln();toast('خوانده شد')}catch(e){}}
function sn(sid){const s=S.sections.find(x=>x.id===sid);return s?s.name:(sid||'نامشخص')}
document.addEventListener('click',e=>{const dd=document.getElementById('nd'),btn=document.getElementById('nt');if(dd&&!dd.contains(e.target)&&!btn.contains(e.target))dd.classList.remove('show')});
document.addEventListener('DOMContentLoaded',init);
</script></body></html>"""

# ═══════════════════════════════════════════════════════════════
# مسیرها
# ═══════════════════════════════════════════════════════════════

@app.route('/')
def index():
    if 'username' not in session:
        return Response(HTML_LOGIN, mimetype='text/html')
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
    return Response(HTML_ADMIN, mimetype='text/html')

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
    return Response(HTML_USER, mimetype='text/html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- احراز هویت ---

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
    return jsonify({'error': 'نام کاربری یا کد ورود اش
