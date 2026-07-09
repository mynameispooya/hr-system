/* ===== ابزارهای مشترک ===== */
var A = {
    g: function(u) {
        return fetch(u).then(function(r) { return r.json() }).then(function(d) {
            if (!d.error) return d; throw new Error(d.error);
        });
    },
    p: function(u, b) {
        return fetch(u, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(b) }).then(function(r) { return r.json() }).then(function(d) {
            if (!d.error) return d; throw new Error(d.error);
        });
    },
    u: function(u, b) {
        return fetch(u, { method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(b) }).then(function(r) { return r.json() }).then(function(d) {
            if (!d.error) return d; throw new Error(d.error);
        });
    },
    d: function(u) {
        return fetch(u, { method: 'DELETE' }).then(function(r) { return r.json() }).then(function(d) {
            if (!d.error) return d; throw new Error(d.error);
        });
    },
    up: function(u, f) {
        return fetch(u, { method: 'POST', body: f }).then(function(r) { return r.json() }).then(function(d) {
            if (!d.error) return d; throw new Error(d.error);
        });
    }
};

function toast(m, t) {
    t = t || 's';
    var c = document.getElementById('tc');
    if (!c) return;
    var e = document.createElement('div');
    e.className = 'ts ts-' + t;
    e.innerHTML = '<span>' + m + '</span><button onclick="this.parentElement.remove()">&times;</button>';
    c.appendChild(e);
    setTimeout(function() { e.classList.add('show') }, 10);
    setTimeout(function() { e.classList.remove('show'); setTimeout(function() { e.remove() }, 300) }, 4500);
}

function om(id) {
    var m = document.getElementById(id);
    if (m) { m.classList.add('active'); document.body.style.overflow = 'hidden'; }
}
function cm(id) {
    var m = document.getElementById(id);
    if (m) { m.classList.remove('active'); document.body.style.overflow = ''; }
}

function al(a) {
    var m = { create_section:'ایجاد بخش', delete_section:'حذف بخش', add_employees:'افزودن کارکنان',
        upload_employees:'آپلود اکسل', delete_employee:'حذف کارمند', transfer:'انتقال مستقیم',
        transfer_initiated:'درخواست انتقال', transfer_accepted:'پذیرش انتقال', transfer_rejected:'رد انتقال',
        settlement:'تسویه', create_user:'ایجاد کاربر', update_user:'ویرایش کاربر',
        delete_user:'حذف کاربر', change_password:'تغییر رمز', change_owner:'تغییر مالک بخش' };
    return m[a] || a;
}
function sl(s) {
    var m = { pending:'در انتظار تایید', accepted:'پذیرفته شده', rejected:'رد شده', completed:'تکمیل شده' };
    return m[s] || s;
}
function sc(s) {
    var m = { pending:'pen', accepted:'acc', rejected:'rej', completed:'com' };
    return m[s] || s;
}

document.addEventListener('click', function(e) {
    if (e.target.classList.contains('mo')) { e.target.classList.remove('active'); document.body.style.overflow = ''; }
});
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        document.querySelectorAll('.mo.active').forEach(function(m) { m.classList.remove('active'); });
        document.body.style.overflow = '';
    }
});
