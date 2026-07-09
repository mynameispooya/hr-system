/* ================================================================
   app.js — کتابخانه مشترک جاوااسکریپت
   ================================================================ */

/* ═══════════════════════════════════════════════════════════════
   بخش ۱ — رفع باگ Drag & Drop در HTML قدیمی
   inline handler ها از ev استفاده کرده‌اند که تعریف‌نشده است.
   این قطعه کد ev را به event واقعی متصل می‌کند.
   TODO: حذف شود وقتی HTML فایل‌ها به‌روز شدند.
   ═══════════════════════════════════════════════════════════════ */
try {
    Object.defineProperty(window, 'ev', {
        get: function () { return window.event; },
        configurable: true
    });
} catch (e) { /* نادیده بگیر */ }


/* ═══════════════════════════════════════════════════════════════
   بخش ۲ — کلاینت API
   ═══════════════════════════════════════════════════════════════ */
var A = {
    g: function (u) {
        return fetch(u).then(function (r) { return r.json(); }).then(function (d) {
            if (d.error) throw new Error(d.error);
            return d;
        });
    },
    p: function (u, b) {
        return fetch(u, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(b)
        }).then(function (r) { return r.json(); }).then(function (d) {
            if (d.error) throw new Error(d.error);
            return d;
        });
    },
    u: function (u, b) {
        return fetch(u, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(b)
        }).then(function (r) { return r.json(); }).then(function (d) {
            if (d.error) throw new Error(d.error);
            return d;
        });
    },
    d: function (u) {
        return fetch(u, { method: 'DELETE' }).then(function (r) { return r.json(); }).then(function (d) {
            if (d.error) throw new Error(d.error);
            return d;
        });
    },
    up: function (u, f) {
        return fetch(u, { method: 'POST', body: f }).then(function (r) { return r.json(); }).then(function (d) {
            if (d.error) throw new Error(d.error);
            return d;
        });
    }
};


/* ═══════════════════════════════════════════════════════════════
   بخش ۳ — توست اعلان
   ═══════════════════════════════════════════════════════════════ */
function toast(m, t) {
    t = t || 's';
    var c = document.getElementById('tc');
    if (!c) return;
    var el = document.createElement('div');
    el.className = 'ts ts-' + t;
    el.innerHTML = '<span>' + m + '</span>' +
        '<button onclick="this.parentElement.remove()">&times;</button>';
    c.appendChild(el);
    setTimeout(function () { el.classList.add('show'); }, 10);
    setTimeout(function () {
        el.classList.remove('show');
        setTimeout(function () { el.remove(); }, 300);
    }, 4500);
}


/* ═══════════════════════════════════════════════════════════════
   بخش ۴ — مودال (باز / بسته)
   ═══════════════════════════════════════════════════════════════ */
function om(id) {
    var m = document.getElementById(id);
    if (m) { m.classList.add('active'); document.body.style.overflow = 'hidden'; }
}

function cm(id) {
    var m = document.getElementById(id);
    if (m) { m.classList.remove('active'); document.body.style.overflow = ''; }
}


/* ═══════════════════════════════════════════════════════════════
   بخش ۵ — برچسب‌ها
   ═══════════════════════════════════════════════════════════════ */

/** برچسب عملیات (برای گزارش تغییرات) */
function al(a) {
    var m = {
        create_section: 'ایجاد بخش', delete_section: 'حذف بخش',
        add_employees: 'افزودن کارکنان', upload_employees: 'آپلود اکسل',
        delete_employee: 'حذف کارمند', transfer: 'انتقال مستقیم',
        transfer_initiated: 'درخواست انتقال', transfer_accepted: 'پذیرش انتقال',
        transfer_rejected: 'رد انتقال', settlement: 'تسویه',
        create_user: 'ایجاد کاربر', update_user: 'ویرایش کاربر',
        delete_user: 'حذف کاربر', change_password: 'تغییر رمز',
        change_owner: 'تغییر مالک بخش'
    };
    return m[a] || a;
}

/** برچسب وضعیت انتقال */
function sl(s) {
    var m = {
        pending: 'در انتظار تایید', accepted: 'پذیرفته شده',
        rejected: 'رد شده', completed: 'تکمیل شده'
    };
    return m[s] || s;
}

/** کلاس CSS وضعیت انتقال */
function sc(s) {
    var m = { pending: 'pen', accepted: 'acc', rejected: 'rej', completed: 'com' };
    return m[s] || s;
}

/** برچسب اقدام تاریخچه */
function hl(a) {
    var m = {
        initiated: 'ایجاد درخواست', accepted: 'پذیرفته شد',
        rejected: 'رد شد', 're-accepted': 'باز-پذیرش',
        're-rejected': 'باز-رد', completed: 'تکمیل (مدیر)'
    };
    return m[a] || a;
}

/** رنگ اقدام تاریخچه */
function hc(a) {
    var m = {
        initiated: 'var(--t3)', accepted: 'var(--ac)',
        rejected: 'var(--dn)', 're-accepted': 'var(--ac)',
        're-rejected': 'var(--wn)', completed: 'var(--inf)'
    };
    return m[a] || 'var(--t3)';
}


/* ═══════════════════════════════════════════════════════════════
   بخش ۶ — Drag & Drop
   ═══════════════════════════════════════════════════════════════ */
var _drag = { id: null, name: '', code: '' };

/** شروع کشیدن — توسط inline ondragstart فراخوانی می‌شود */
function ds(e, id, nm, cd) {
    e = e || window.event;
    if (!e) return;
    _drag.id = id;
    _drag.name = nm;
    _drag.code = cd;
    if (e.dataTransfer) {
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', id);
    }
    var tr = e.target.closest ? e.target.closest('tr') : null;
    if (tr) tr.classList.add('dragging');
}

/** پایان کشیدن — توسط inline ondragend فراخوانی می‌شود */
function de(e) {
    e = e || window.event;
    if (e && e.target) {
        var tr = e.target.closest ? e.target.closest('tr') : null;
        if (tr) tr.classList.remove('dragging');
    }
    document.querySelectorAll('.dz').forEach(function (z) { z.classList.remove('da'); });
}

/** رها کردن روی منطقه انتقال — توسط inline ondrop فراخوانی می‌شود */
function dt(e) {
    e = e || window.event;
    if (e) e.preventDefault();
    if (e && e.currentTarget) e.currentTarget.classList.remove('da');
    if (!_drag.id) return;
    stm(_drag.id, _drag.name, _drag.code);
    _drag = { id: null, name: '', code: '' };
}

/** رها کردن روی منطقه تسویه — توسط inline ondrop فراخوانی می‌شود */
function dsel(e) {
    e = e || window.event;
    if (e) e.preventDefault();
    if (e && e.currentTarget) e.currentTarget.classList.remove('da');
    if (!_drag.id) return;
    stl(_drag.id, _drag.name);
    _drag = { id: null, name: '', code: '' };
}

/* ── Event Delegation — پشتیبان برای Drop Zones ──
   حتی اگر inline handler ها خطا دهند، این delegation کار می‌کند.
   از capture phase استفاده شده تا قبل از inline handler ها اجرا شود. */
document.addEventListener('dragover', function (e) {
    var dz = e.target.closest ? e.target.closest('.dz') : null;
    if (dz) { e.preventDefault(); dz.classList.add('da'); }
}, true);

document.addEventListener('dragleave', function (e) {
    var dz = e.target.closest ? e.target.closest('.dz') : null;
    if (dz && !dz.contains(e.relatedTarget)) dz.classList.remove('da');
}, true);

document.addEventListener('drop', function (e) {
    var dz = e.target.closest ? e.target.closest('.dz') : null;
    if (dz) {
        e.preventDefault();
        e.stopPropagation();
        dz.classList.remove('da');
        if (!_drag.id) return;
        if (dz.classList.contains('sz')) {
            stl(_drag.id, _drag.name);
        } else {
            stm(_drag.id, _drag.name, _drag.code);
        }
        _drag = { id: null, name: '', code: '' };
    }
}, true);


/* ═══════════════════════════════════════════════════════════════
   بخش ۷ — جستجوی بدون قطع شدن (رفع باگ شماره ۳)
   ═══════════════════════════════════════════════════════════════
   نحوه استفاده در HTML:
   به‌جای:  oninput="S.sq=this.value;rsd()"
   بنویسید: oninput="S.sq=this.value;safeRender(rsd)"
   ---------------------------------------------------------------- */
function safeRender(renderFn) {
    var input = document.querySelector('.sb input');
    var state = null;
    if (input) {
        state = {
            value: input.value,
            start: input.selectionStart,
            end: input.selectionEnd
        };
    }
    renderFn();
    if (state) {
        setTimeout(function () {
            var ni = document.querySelector('.sb input');
            if (ni) {
                ni.value = state.value;
                ni.focus();
                try { ni.setSelectionRange(state.start, state.end); } catch (ex) { /* نادیده بگیر */ }
            }
        }, 5);
    }
}


/* ═══════════════════════════════════════════════════════════════
   بخش ۸ — دکمه‌های عملیات انتقال (با پشتیبانی باز-پذیرش / باز-رد)
   نحوه استفاده در HTML:
   در جایگاه عملیات انتقال بنویسید:  + trBtns(t)
   ---------------------------------------------------------------- */
function trBtns(t) {
    if (t.status === 'pending') {
        return '<button class="btn btn-p btn-sm" onclick="at(\'' + t.id + '\')">پذیرش</button>' +
            '<button class="btn btn-d btn-sm" onclick="rt(\'' + t.id + '\')">رد</button>';
    }
    if (t.status === 'rejected') {
        return '<button class="btn btn-p btn-sm" onclick="at(\'' + t.id + '\')">پذیرش مجدد</button>' +
            '<span style="color:var(--t3);font-size:.78rem;margin-right:6px">— قبلاً رد شده</span>';
    }
    if (t.status === 'accepted') {
        return '<button class="btn btn-d btn-sm" onclick="rt(\'' + t.id + '\')">باز-رد</button>' +
            '<span style="color:var(--ac);font-size:.78rem;margin-right:6px">— قبلاً پذیرفته شده</span>';
    }
    if (t.status === 'completed') {
        return '<span style="color:var(--inf);font-size:.78rem">انجام شده توسط مدیر</span>';
    }
    return '-';
}


/* ═══════════════════════════════════════════════════════════════
   بخش ۹ — رندر تاریخچه انتقال
   نحوه استفاده در HTML:
   بعد از رندر هر ردیف انتقال اضافه کنید:  + trHist(t.history)
   ---------------------------------------------------------------- */
function trHist(history) {
    if (!history || !history.length) return '';
    var h = '<div style="margin-top:8px;padding-top:8px;border-top:1px dashed var(--bd);font-size:.78rem;color:var(--t3)">';
    h += '<strong style="color:var(--t2)">تاریخچه:</strong><br>';
    for (var i = 0; i < history.length; i++) {
        var item = history[i];
        h += '<span style="color:' + hc(item.action) + '">● ' + hl(item.action) + '</span>';
        h += '  <span style="direction:ltr;display:inline-block;margin:0 4px">' + item.at + '</span>';
        h += '  توسط ' + item.by;
        if (item.detail) h += ' — ' + item.detail;
        h += '<br>';
    }
    h += '</div>';
    return h;
}


/* ═══════════════════════════════════════════════════════════════
   بخش ۱۰ — کارکنان: افزودن دستی
   ═══════════════════════════════════════════════════════════════ */
function oae() {
    document.getElementById('erows').innerHTML = '';
    aer(); aer(); aer();
    om('memp');
}

function aer() {
    var c = document.getElementById('erows');
    var d = document.createElement('div');
    d.className = 'fr';
    d.style.marginBottom = '8px';
    d.innerHTML =
        '<input type="text" placeholder="نام" class="en">' +
        '<input type="text" placeholder="نام خانوادگی" class="ef">' +
        '<input type="text" placeholder="کد پرسنلی" class="ec" style="direction:ltr;text-align:right">' +
        '<button class="btn btn-g btn-sm btn-ic" onclick="this.parentElement.remove()" title="حذف ردیف">&times;</button>';
    c.appendChild(d);
}

async function se() {
    var rows = document.querySelectorAll('#erows .fr');
    var emps = [];
    rows.forEach(function (r) {
        var n = r.querySelector('.en').value.trim();
        var f = r.querySelector('.ef').value.trim();
        var c = r.querySelector('.ec').value.trim();
        if (n || f || c) emps.push({ name: n, family: f, code: c });
    });
    if (!emps.length) return toast('حداقل یک کارمند وارد کنید', 'e');
    try {
        var res = await A.p('/api/sections/' + S.selSec + '/employees', { employees: emps });
        cm('memp');
        if (res.errors.length)
            toast(res.added.length + ' اضافه شد، ' + res.errors.length + ' خطا', 'w');
        else
            toast(res.added.length + ' نفر اضافه شد');
        await ls();
        S.employees = await A.g('/api/sections/' + S.selSec + '/employees');
        safeRender(rsd);
    } catch (e) { toast(e.message, 'e'); }
}


/* ═══════════════════════════════════════════════════════════════
   بخش ۱۱ — آپلود اکسل
   ═══════════════════════════════════════════════════════════════ */
async function ue() {
    var f = document.getElementById('efile').files[0];
    if (!f) return toast('فایلی انتخاب نشده', 'e');
    var fd = new FormData();
    fd.append('file', f);
    try {
        var res = await A.up('/api/sections/' + S.selSec + '/employees/upload', fd);
        cm('mup');
        document.getElementById('efile').value = '';
        if (res.errors.length)
            toast(res.added.length + ' اضافه شد، ' + res.errors.length + ' خطا', 'w');
        else
            toast(res.added.length + ' نفر اضافه شد');
        await ls();
        S.employees = await A.g('/api/sections/' + S.selSec + '/employees');
        safeRender(rsd);
    } catch (e) { toast(e.message, 'e'); }
}


/* ═══════════════════════════════════════════════════════════════
   بخش ۱۲ — حذف کارمند
   ═══════════════════════════════════════════════════════════════ */
function cde(id, nm) {
    document.getElementById('cfm').textContent = 'آیا از حذف «' + nm + '» اطمینان دارید؟';
    document.getElementById('cfb').onclick = async function () {
        try {
            await A.d('/api/sections/' + S.selSec + '/employees/' + id);
            toast('حذف شد');
            cm('mcf');
            await ls();
            S.employees = await A.g('/api/sections/' + S.selSec + '/employees');
            safeRender(rsd);
        } catch (e) { toast(e.message, 'e'); }
    };
    om('mcf');
}


/* ═══════════════════════════════════════════════════════════════
   بخش ۱۳ — انتقال کارمند (دکمه)
   ═══════════════════════════════════════════════════════════════ */
function stm(id, nm, cd) {
    var other = S.sections.filter(function (s) { return s.id !== S.selSec; });
    if (!other.length) return toast('بخش مقصدی وجود ندارد', 'e');
    S.trEid = id;
    document.getElementById('tei').textContent = nm + ' (کد: ' + cd + ')';
    document.getElementById('tdes').innerHTML = other.map(function (s) {
        return '<option value="' + s.id + '">' + s.name + '</option>';
    }).join('');
    om('mtr');
}

async function ct() {
    var d = document.getElementById('tdes').value;
    if (!d) return toast('بخش مقصد را انتخاب کنید', 'e');
    try {
        await A.p('/api/transfers', {
            employee_id: S.trEid, from_section: S.selSec, to_section: d
        });
        toast('درخواست انتقال ارسال شد');
        cm('mtr');
        await ls(); await lt(); await ln();
        S.employees = await A.g('/api/sections/' + S.selSec + '/employees');
        safeRender(rsd);
    } catch (e) { toast(e.message, 'e'); }
}


/* ═══════════════════════════════════════════════════════════════
   بخش ۱۴ — تسویه کارمند (دکمه)
   ═══════════════════════════════════════════════════════════════ */
function stl(id, nm) {
    document.getElementById('cfm').textContent = 'آیا از انتقال «' + nm + '» به تسویه اطمینان دارید؟';
    document.getElementById('cfb').onclick = async function () {
        try {
            await A.p('/api/settlements', { employee_id: id, from_section: S.selSec });
            toast('به تسویه منتقل شد');
            cm('mcf');
            await ls();
            S.employees = await A.g('/api/sections/' + S.selSec + '/employees');
            safeRender(rsd);
        } catch (e) { toast(e.message, 'e'); }
    };
    om('mcf');
}


/* ═══════════════════════════════════════════════════════════════
   بخش ۱۵ — اعلان‌ها
   ═══════════════════════════════════════════════════════════════ */
function tn() {
    document.getElementById('nd').classList.toggle('show');
}

function rnl() {
    var el = document.getElementById('nl');
    if (!S.notifications.length) {
        el.innerHTML = '<div class="ne">اعلانی وجود ندارد</div>';
        return;
    }
    var html = '';
    for (var i = 0; i < Math.min(S.notifications.length, 20); i++) {
        var n = S.notifications[i];
        html += '<div class="ni ' + (n.read ? '' : 'ur') + '" onclick="mr(\'' + n.id + '\')">' +
            n.message + '<span class="nt">' + n.timestamp + '</span></div>';
    }
    el.innerHTML = html;
}

async function mr(nid) {
    try { await A.p('/api/notifications/' + nid + '/read', {}); await ln(); } catch (e) { /* نادیده بگیر */ }
}

async function mra() {
    try { await A.p('/api/notifications/read-all', {}); await ln(); toast('خوانده شد'); } catch (e) { /* نادیده بگیر */ }
}


/* ═══════════════════════════════════════════════════════════════
   بخش ۱۶ — تابع کمکی نام بخش
   ═══════════════════════════════════════════════════════════════ */
function sn(sid) {
    for (var i = 0; i < S.sections.length; i++) {
        if (S.sections[i].id === sid) return S.sections[i].name;
    }
    return sid || 'نامشخص';
}


/* ═══════════════════════════════════════════════════════════════
   بخش ۱۷ — رویدادهای سراسری
   ═══════════════════════════════════════════════════════════════ */
document.addEventListener('click', function (e) {
    /* بستن مودال با کلیک روی overlay */
    if (e.target.classList.contains('mo')) {
        e.target.classList.remove('active');
        document.body.style.overflow = '';
    }
    /* بستن dropdown اعلان با کلیک بیرون */
    var dd = document.getElementById('nd');
    var btn = document.getElementById('nt');
    if (dd && btn && !dd.contains(e.target) && !btn.contains(e.target)) {
        dd.classList.remove('show');
    }
});

document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
        document.querySelectorAll('.mo.active').forEach(function (m) {
            m.classList.remove('active');
        });
        document.body.style.overflow = '';
    }
});
