// script.js

// ============================================================================
// GLOBAL STATE
// ============================================================================
const state = {
    currentUser: null,
    currentSection: null,
    sections: [],
    employees: [],
    pendingTransfers: [],
    myPendingTransfers: [],
    transferHistory: [],
    settlements: [],
    users: [],
    logs: [],
    announcements: [],
    isLoading: false
};

// ============================================================================
// API HELPER
// ============================================================================
const api = {
    async request(url, options = {}) {
        try {
            const response = await fetch(url, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'خطایی رخ داد');
            }

            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },

    async get(url) {
        return this.request(url, { method: 'GET' });
    },

    async post(url, data) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async put(url, data) {
        return this.request(url, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    async delete(url) {
        return this.request(url, { method: 'DELETE' });
    },

    async upload(url, formData) {
        try {
            const response = await fetch(url, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'خطایی رخ داد');
            }

            return data;
        } catch (error) {
            console.error('Upload Error:', error);
            throw error;
        }
    }
};

// ============================================================================
// UI HELPERS
// ============================================================================
const ui = {
    showLoading() {
        state.isLoading = true;
        const overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.innerHTML = '<div class="spinner"></div>';
        document.body.appendChild(overlay);
    },

    hideLoading() {
        state.isLoading = false;
        const overlay = document.getElementById('loading-overlay');
        if (overlay) overlay.remove();
    },

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(() => toast.classList.add('show'), 10);
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },

    showModal(title, content, onConfirm = null) {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>${title}</h3>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">${content}</div>
                ${onConfirm ? `
                    <div class="modal-footer">
                        <button class="btn btn-secondary modal-cancel">انصراف</button>
                        <button class="btn btn-primary modal-confirm">تأیید</button>
                    </div>
                ` : ''}
            </div>
        `;

        document.body.appendChild(modal);
        setTimeout(() => modal.classList.add('show'), 10);

        const close = () => {
            modal.classList.remove('show');
            setTimeout(() => modal.remove(), 300);
        };

        modal.querySelector('.modal-close').onclick = close;
        if (onConfirm) {
            modal.querySelector('.modal-cancel').onclick = close;
            modal.querySelector('.modal-confirm').onclick = () => {
                onConfirm();
                close();
            };
        }

        modal.onclick = (e) => {
            if (e.target === modal) close();
        };

        return modal;
    },

    showConfirmDialog(message, onConfirm) {
        this.showModal('تأیید', `<p>${message}</p>`, onConfirm);
    },

    showPromptDialog(title, fields, onSubmit) {
        let html = '<form id="prompt-form">';
        fields.forEach(field => {
            html += `
                <div class="form-group">
                    <label>${field.label}</label>
                    ${field.type === 'select' ? `
                        <select name="${field.name}" ${field.required ? 'required' : ''}>
                            <option value="">انتخاب کنید</option>
                            ${field.options.map(opt => `<option value="${opt.value}">${opt.label}</option>`).join('')}
                        </select>
                    ` : `
                        <input type="${field.type || 'text'}" name="${field.name}" 
                               ${field.required ? 'required' : ''} 
                               ${field.placeholder ? `placeholder="${field.placeholder}"` : ''}>
                    `}
                </div>
            `;
        });
        html += '</form>';

        const modal = this.showModal(title, html, () => {
            const form = document.getElementById('prompt-form');
            const formData = new FormData(form);
            const data = {};
            for (let [key, value] of formData.entries()) {
                data[key] = value;
            }
            onSubmit(data);
        });

        return modal;
    }
};

// ============================================================================
// AUTH FUNCTIONS
// ============================================================================
async function login(username, password) {
    try {
        ui.showLoading();
        const data = await api.post('/api/login', { username, password });
        state.currentUser = data.user;
        ui.showToast('ورود موفق', 'success');
        await loadDashboard();
    } catch (error) {
        ui.showToast(error.message, 'error');
    } finally {
        ui.hideLoading();
    }
}

async function logout() {
    try {
        ui.showLoading();
        await api.post('/api/logout');
        state.currentUser = null;
        window.location.href = '/login';
    } catch (error) {
        ui.showToast(error.message, 'error');
        ui.hideLoading();
    }
}

async function checkAuth() {
    try {
        const data = await api.get('/api/me');
        state.currentUser = data;
        return true;
    } catch (error) {
        return false;
    }
}

// ============================================================================
// DASHBOARD FUNCTIONS
// ============================================================================
async function loadDashboard() {
    try {
        ui.showLoading();
        await Promise.all([
            loadSections(),
            loadAnnouncements(),
            loadPendingTransfers()
        ]);
        renderDashboard();
    } catch (error) {
        ui.showToast(error.message, 'error');
    } finally {
        ui.hideLoading();
    }
}

async function loadSections() {
    const data = await api.get('/api/sections');
    state.sections = data.sections;
}

async function loadAnnouncements() {
    const data = await api.get('/api/announcements');
    state.announcements = data.announcements;
}

async function loadPendingTransfers() {
    const [pending, myPending] = await Promise.all([
        api.get('/api/transfers/pending'),
        api.get('/api/transfers/my-pending')
    ]);
    state.pendingTransfers = pending.transfers;
    state.myPendingTransfers = myPending.transfers;
}

function renderDashboard() {
    renderSidebar();
    renderMainContent();
    renderAnnouncements();
}

function renderSidebar() {
    const sidebar = document.getElementById('sidebar');
    const isAdmin = state.currentUser.role === 'admin';

    let html = `
        <div class="user-info">
            <div class="user-avatar">${state.currentUser.username[0].toUpperCase()}</div>
            <div class="user-details">
                <div class="user-name">${state.currentUser.username}</div>
                <div class="user-role">${isAdmin ? 'مدیر سیستم' : 'کاربر'}</div>
            </div>
        </div>
        <nav class="sidebar-nav">
            <a href="#" class="nav-item active" data-view="sections">
                <span class="nav-icon">📁</span>
                <span>بخش‌ها</span>
            </a>
    `;

    if (state.myPendingTransfers.length > 0) {
        html += `
            <a href="#" class="nav-item" data-view="pending-transfers">
                <span class="nav-icon">⏳</span>
                <span>انتقال‌های در انتظار</span>
                <span class="badge">${state.myPendingTransfers.length}</span>
            </a>
        `;
    }

    if (isAdmin) {
        html += `
            <a href="#" class="nav-item" data-view="users">
                <span class="nav-icon">👥</span>
                <span>مدیریت کاربران</span>
            </a>
            <a href="#" class="nav-item" data-view="logs">
                <span class="nav-icon">📊</span>
                <span>لاگ فعالیت‌ها</span>
            </a>
        `;
    }

    html += `
            <a href="#" class="nav-item" data-view="settlements">
                <span class="nav-icon">🔴</span>
                <span>تسویه‌ها</span>
            </a>
            <a href="#" class="nav-item" data-view="transfer-history">
                <span class="nav-icon">📤</span>
                <span>تاریخچه انتقال‌ها</span>
            </a>
        </nav>
        <div class="sidebar-footer">
            <a href="#" class="nav-item" id="change-password-btn">
                <span class="nav-icon">🔐</span>
                <span>تغییر رمز عبور</span>
            </a>
            <a href="#" class="nav-item" id="logout-btn">
                <span class="nav-icon">🚪</span>
                <span>خروج</span>
            </a>
        </div>
    `;

    sidebar.innerHTML = html;

    // Event listeners
    document.querySelectorAll('.nav-item[data-view]').forEach(item => {
        item.onclick = (e) => {
            e.preventDefault();
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            const view = item.dataset.view;
            renderView(view);
        };
    });

    document.getElementById('logout-btn').onclick = (e) => {
        e.preventDefault();
        logout();
    };

    document.getElementById('change-password-btn').onclick = (e) => {
        e.preventDefault();
        showChangePasswordModal();
    };
}

function renderMainContent() {
    renderView('sections');
}

async function renderView(view) {
    const content = document.getElementById('main-content');

    switch (view) {
        case 'sections':
            await renderSectionsView(content);
            break;
        case 'pending-transfers':
            await renderPendingTransfersView(content);
            break;
        case 'users':
            await renderUsersView(content);
            break;
        case 'logs':
            await renderLogsView(content);
            break;
        case 'settlements':
            await renderSettlementsView(content);
            break;
        case 'transfer-history':
            await renderTransferHistoryView(content);
            break;
    }
}

async function renderSectionsView(content) {
    let html = `
        <div class="view-header">
            <h2>بخش‌ها</h2>
            <button class="btn btn-primary" id="create-section-btn">+ ایجاد بخش جدید</button>
        </div>
        <div class="sections-grid">
    `;

    if (state.sections.length === 0) {
        html += '<div class="empty-state">هیچ بخشی وجود ندارد. اولین بخش را ایجاد کنید.</div>';
    } else {
        state.sections.forEach(section => {
            html += `
                <div class="section-card" data-section="${section.name}">
                    <div class="section-header">
                        <h3>${section.name}</h3>
                        <div class="section-actions">
                            <button class="btn-icon" onclick="exportSection('${section.name}')" title="خروجی اکسل">📥</button>
                            <button class="btn-icon" onclick="deleteSection('${section.name}')" title="حذف بخش">🗑️</button>
                        </div>
                    </div>
                    <div class="section-stats">
                        <div class="stat">
                            <span class="stat-value">${section.employee_count}</span>
                            <span class="stat-label">کارمند</span>
                        </div>
                    </div>
                    <button class="btn btn-secondary btn-block" onclick="viewSection('${section.name}')">
                        مشاهده کارکنان
                    </button>
                </div>
            `;
        });
    }

    html += '</div>';
    content.innerHTML = html;

    document.getElementById('create-section-btn').onclick = showCreateSectionModal;
}

async function renderPendingTransfersView(content) {
    let html = `
        <div class="view-header">
            <h2>انتقال‌های در انتظار تأیید</h2>
        </div>
    `;

    if (state.myPendingTransfers.length === 0) {
        html += '<div class="empty-state">هیچ انتقال در انتظاری وجود ندارد.</div>';
    } else {
        html += '<div class="transfers-list">';
        state.myPendingTransfers.forEach(transfer => {
            html += `
                <div class="transfer-card">
                    <div class="transfer-info">
                        <div class="transfer-name">${transfer.first_name} ${transfer.last_name}</div>
                        <div class="transfer-code">کد پرسنلی: ${transfer.personnel_code}</div>
                        <div class="transfer-details">
                            از <strong>${transfer.from_section}</strong> به <strong>${transfer.to_section}</strong>
                        </div>
                        <div class="transfer-meta">
                            درخواست توسط: ${transfer.requested_by} | 
                            تاریخ: ${new Date(transfer.requested_at).toLocaleString('fa-IR')}
                        </div>
                    </div>
                    <div class="transfer-actions">
                        <button class="btn btn-success" onclick="approveTransfer('${transfer.id}')">
                            ✓ تأیید و انتقال
                        </button>
                        <button class="btn btn-danger" onclick="rejectTransfer('${transfer.id}')">
                            ✗ رد درخواست
                        </button>
                    </div>
                </div>
            `;
        });
        html += '</div>';
    }

    content.innerHTML = html;
}

async function renderUsersView(content) {
    if (state.currentUser.role !== 'admin') {
        content.innerHTML = '<div class="empty-state">دسترسی غیرمجاز</div>';
        return;
    }

    try {
        const data = await api.get('/api/users');
        state.users = data.users;

        let html = `
            <div class="view-header">
                <h2>مدیریت کاربران</h2>
                <button class="btn btn-primary" id="create-user-btn">+ ایجاد کاربر جدید</button>
            </div>
            <div class="users-table">
                <table>
                    <thead>
                        <tr>
                            <th>نام کاربری</th>
                            <th>نقش</th>
                            <th>بخش‌های دسترسی</th>
                            <th>تاریخ ایجاد</th>
                            <th>عملیات</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        state.users.forEach(user => {
            html += `
                <tr>
                    <td>${user.username}</td>
                    <td><span class="badge badge-${user.role}">${user.role === 'admin' ? 'مدیر' : 'کاربر'}</span></td>
                    <td>${user.sections.join(', ') || 'همه بخش‌ها'}</td>
                    <td>${new Date(user.created_at).toLocaleString('fa-IR')}</td>
                    <td>
                        <button class="btn-icon" onclick="editUser('${user.username}')" title="ویرایش">✏️</button>
                        ${user.username !== 'admin' && user.username !== state.currentUser.username ? `
                            <button class="btn-icon" onclick="deleteUser('${user.username}')" title="حذف">🗑️</button>
                        ` : ''}
                    </td>
                </tr>
            `;
        });

        html += `
                    </tbody>
                </table>
            </div>
        `;

        content.innerHTML = html;

        document.getElementById('create-user-btn').onclick = showCreateUserModal;
    } catch (error) {
        ui.showToast(error.message, 'error');
    }
}

async function renderLogsView(content) {
    if (state.currentUser.role !== 'admin') {
        content.innerHTML = '<div class="empty-state">دسترسی غیرمجاز</div>';
        return;
    }

    try {
        const data = await api.get('/api/logs?per_page=100');
        state.logs = data.logs;

        let html = `
            <div class="view-header">
                <h2>لاگ فعالیت‌ها</h2>
                <button class="btn btn-primary" onclick="exportLogs()">📥 خروجی اکسل</button>
            </div>
            <div class="logs-table">
                <table>
                    <thead>
                        <tr>
                            <th>تاریخ و زمان</th>
                            <th>کاربر</th>
                            <th>عملیات</th>
                            <th>جزئیات</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        state.logs.forEach(log => {
            html += `
                <tr>
                    <td>${new Date(log.timestamp).toLocaleString('fa-IR')}</td>
                    <td>${log.user}</td>
                    <td><span class="badge">${log.action}</span></td>
                    <td>${log.details}</td>
                </tr>
            `;
        });

        html += `
                    </tbody>
                </table>
            </div>
        `;

        content.innerHTML = html;
    } catch (error) {
        ui.showToast(error.message, 'error');
    }
}

async function renderSettlementsView(content) {
    try {
        const data = await api.get('/api/settlements');
        state.settlements = data.settlements;

        let html = `
            <div class="view-header">
                <h2>تسویه‌ها</h2>
            </div>
        `;

        if (state.settlements.length === 0) {
            html += '<div class="empty-state">هیچ تسویه‌ای ثبت نشده است.</div>';
        } else {
            html += '<div class="settlements-list">';
            state.settlements.forEach(settlement => {
                html += `
                    <div class="settlement-card">
                        <div class="settlement-info">
                            <div class="settlement-name">${settlement.first_name} ${settlement.last_name}</div>
                            <div class="settlement-code">کد پرسنلی: ${settlement.personnel_code}</div>
                            <div class="settlement-details">
                                از بخش: <strong>${settlement.from_section}</strong>
                            </div>
                            <div class="settlement-meta">
                                تسویه توسط: ${settlement.settled_by} | 
                                تاریخ: ${new Date(settlement.settled_at).toLocaleString('fa-IR')}
                            </div>
                            ${settlement.notes ? `<div class="settlement-notes">یادداشت: ${settlement.notes}</div>` : ''}
                        </div>
                    </div>
                `;
            });
            html += '</div>';
        }

        content.innerHTML = html;
    } catch (error) {
        ui.showToast(error.message, 'error');
    }
}

async function renderTransferHistoryView(content) {
    try {
        const data = await api.get('/api/transfers/history');
        state.transferHistory = data.transfers;

        let html = `
            <div class="view-header">
                <h2>تاریخچه انتقال‌ها</h2>
            </div>
        `;

        if (state.transferHistory.length === 0) {
            html += '<div class="empty-state">هیچ انتقالی ثبت نشده است.</div>';
        } else {
            html += '<div class="transfers-list">';
            state.transferHistory.forEach(transfer => {
                const statusClass = transfer.status === 'approved' ? 'success' : 'danger';
                const statusText = transfer.status === 'approved' ? 'تأیید شده' : 'رد شده';
                
                html += `
                    <div class="transfer-card">
                        <div class="transfer-info">
                            <div class="transfer-name">${transfer.first_name} ${transfer.last_name}</div>
                            <div class="transfer-code">کد پرسنلی: ${transfer.personnel_code}</div>
                            <div class="transfer-details">
                                از <strong>${transfer.from_section}</strong> به <strong>${transfer.to_section}</strong>
                            </div>
                            <div class="transfer-meta">
                                وضعیت: <span class="badge badge-${statusClass}">${statusText}</span> |
                                درخواست توسط: ${transfer.requested_by} |
                                ${transfer.approved_by ? `تأیید توسط: ${transfer.approved_by}` : `رد توسط: ${transfer.rejected_by}`}
                            </div>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
        }

        content.innerHTML = html;
    } catch (error) {
        ui.showToast(error.message, 'error');
    }
}

function renderAnnouncements() {
    const container = document.getElementById('announcements-container');
    if (!container || state.announcements.length === 0) return;

    let html = '';
    state.announcements.slice(0, 5).forEach(ann => {
        const icon = ann.type === 'transfer' ? '✅' : ann.type === 'settlement' ? '🔴' : 'ℹ️';
        html += `
            <div class="announcement-item announcement-${ann.type}">
                <span class="announcement-icon">${icon}</span>
                <span class="announcement-text">${ann.message}</span>
                <span class="announcement-time">${new Date(ann.timestamp).toLocaleString('fa-IR')}</span>
            </div>
        `;
    });

    container.innerHTML = html;
}

// ============================================================================
// SECTION FUNCTIONS
// ============================================================================
function showCreateSectionModal() {
    ui.showPromptDialog('ایجاد بخش جدید', [
        { name: 'name', label: 'نام بخش', required: true, placeholder: 'مثال: تولید آلبالو' }
    ], async (data) => {
        try {
            ui.showLoading();
            await api.post('/api/sections', data);
            ui.showToast('بخش با موفقیت ایجاد شد', 'success');
            await loadDashboard();
        } catch (error) {
            ui.showToast(error.message, 'error');
        } finally {
            ui.hideLoading();
        }
    });
}

async function deleteSection(sectionName) {
    ui.showConfirmDialog(`آیا از حذف بخش "${sectionName}" مطمئن هستید؟ تمام کارکنان این بخش حذف خواهند شد.`, async () => {
        try {
            ui.showLoading();
            await api.delete(`/api/sections/${sectionName}`);
            ui.showToast('بخش با موفقیت حذف شد', 'success');
            await loadDashboard();
        } catch (error) {
            ui.showToast(error.message, 'error');
        } finally {
            ui.hideLoading();
        }
    });
}

async function viewSection(sectionName) {
    state.currentSection = sectionName;
    
    try {
        ui.showLoading();
        const data = await api.get(`/api/sections/${sectionName}/employees`);
        state.employees = data.employees;
        renderSectionDetail(sectionName);
    } catch (error) {
        ui.showToast(error.message, 'error');
    } finally {
        ui.hideLoading();
    }
}

function renderSectionDetail(sectionName) {
    const content = document.getElementById('main-content');

    let html = `
        <div class="view-header">
            <div>
                <button class="btn btn-secondary" onclick="renderView('sections')">← بازگشت</button>
                <h2 style="display: inline-block; margin-right: 1rem;">${sectionName}</h2>
            </div>
            <div class="header-actions">
                <button class="btn btn-primary" onclick="showAddEmployeeModal()">+ افزودن کارمند</button>
                <button class="btn btn-secondary" onclick="showUploadExcelModal()">📤 آپلود اکسل</button>
                <button class="btn btn-secondary" onclick="exportSection('${sectionName}')">📥 خروجی اکسل</button>
            </div>
        </div>
        <div class="employees-table">
            <table>
                <thead>
                    <tr>
                        <th>ردیف</th>
                        <th>کد پرسنلی</th>
                        <th>نام</th>
                        <th>نام خانوادگی</th>
                        <th>عملیات</th>
                    </tr>
                </thead>
                <tbody>
    `;

    if (state.employees.length === 0) {
        html += '<tr><td colspan="5" class="empty-state">هیچ کارمندی در این بخش وجود ندارد.</td></tr>';
    } else {
        state.employees.forEach((emp, idx) => {
            html += `
                <tr draggable="true" data-code="${emp.personnel_code}" class="draggable-row">
                    <td>${idx + 1}</td>
                    <td>${emp.personnel_code}</td>
                    <td>${emp.first_name}</td>
                    <td>${emp.last_name}</td>
                    <td>
                        <button class="btn-icon" onclick="transferEmployee('${emp.personnel_code}')" title="انتقال">📤</button>
                        <button class="btn-icon" onclick="settleEmployee('${emp.personnel_code}')" title="تسویه">🔴</button>
                        <button class="btn-icon" onclick="deleteEmployee('${emp.personnel_code}')" title="حذف">🗑️</button>
                    </td>
                </tr>
            `;
        });
    }

    html += `
                </tbody>
            </table>
        </div>
    `;

    content.innerHTML = html;

    // Setup drag and drop
    setupDragAndDrop();
}

function setupDragAndDrop() {
    const rows = document.querySelectorAll('.draggable-row');
    
    rows.forEach(row => {
        row.addEventListener('dragstart', (e) => {
            e.dataTransfer.setData('text/plain', row.dataset.code);
            row.classList.add('dragging');
        });

        row.addEventListener('dragend', () => {
            row.classList.remove('dragging');
        });
    });
}

function showAddEmployeeModal() {
    ui.showPromptDialog('افزودن کارمند جدید', [
        { name: 'personnel_code', label: 'کد پرسنلی', required: true },
        { name: 'first_name', label: 'نام', required: true },
        { name: 'last_name', label: 'نام خانوادگی', required: true }
    ], async (data) => {
        try {
            ui.showLoading();
            await api.post(`/api/sections/${state.currentSection}/employees`, data);
            ui.showToast('کارمند با موفقیت اضافه شد', 'success');
            await viewSection(state.currentSection);
        } catch (error) {
            ui.showToast(error.message, 'error');
        } finally {
            ui.hideLoading();
        }
    });
}

function showUploadExcelModal() {
    const modal = ui.showModal('آپلود فایل اکسل', `
        <form id="upload-form">
            <div class="form-group">
                <label>فایل اکسل (.xlsx, .xls)</label>
                <input type="file" id="excel-file" accept=".xlsx,.xls" required>
                <small class="form-hint">فایل باید دارای ستون‌های: نام، نام خانوادگی، کد پرسنلی باشد</small>
            </div>
        </form>
    `, async () => {
        const fileInput = document.getElementById('excel-file');
        if (!fileInput.files[0]) {
            ui.showToast('لطفاً یک فایل انتخاب کنید', 'error');
            return;
        }

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);

        try {
            ui.showLoading();
            const result = await api.upload(`/api/sections/${state.currentSection}/upload`, formData);
            ui.showToast(result.message, 'success');
            
            if (result.skipped_count > 0 || result.error_count > 0) {
                let details = '';
                if (result.skipped_count > 0) details += `${result.skipped_count} مورد تکراری رد شد. `;
                if (result.error_count > 0) details += `${result.error_count} خطا رخ داد.`;
                ui.showToast(details, 'warning');
            }
            
            await viewSection(state.currentSection);
        } catch (error) {
            ui.showToast(error.message, 'error');
        } finally {
            ui.hideLoading();
        }
    });
}

async function deleteEmployee(personnelCode) {
    ui.showConfirmDialog(`آیا از حذف کارمند با کد "${personnelCode}" مطمئن هستید؟`, async () => {
        try {
            ui.showLoading();
            await api.delete(`/api/sections/${state.currentSection}/employees/${personnelCode}`);
            ui.showToast('کارمند با موفقیت حذف شد', 'success');
            await viewSection(state.currentSection);
        } catch (error) {
            ui.showToast(error.message, 'error');
        } finally {
            ui.hideLoading();
        }
    });
}

function transferEmployee(personnelCode) {
    const employee = state.employees.find(e => e.personnel_code === personnelCode);
    if (!employee) return;

    const sectionOptions = state.sections
        .filter(s => s.name !== state.currentSection)
        .map(s => ({ value: s.name, label: s.name }));

    if (sectionOptions.length === 0) {
        ui.showToast('هیچ بخش دیگری برای انتقال وجود ندارد', 'error');
        return;
    }

    ui.showPromptDialog(`انتقال ${employee.first_name} ${employee.last_name}`, [
        { 
            name: 'to_section', 
            label: 'بخش مقصد', 
            type: 'select', 
            required: true,
            options: sectionOptions
        }
    ], async (data) => {
        try {
            ui.showLoading();
            await api.post('/api/transfers', {
                personnel_code: personnelCode,
                to_section: data.to_section
            });
            ui.showToast('درخواست انتقال با موفقیت ثبت شد', 'success');
            await loadPendingTransfers();
            renderSidebar();
        } catch (error) {
            ui.showToast(error.message, 'error');
        } finally {
            ui.hideLoading();
        }
    });
}

function settleEmployee(personnelCode) {
    const employee = state.employees.find(e => e.personnel_code === personnelCode);
    if (!employee) return;

    ui.showPromptDialog(`تسویه حساب ${employee.first_name} ${employee.last_name}`, [
        { name: 'notes', label: 'یادداشت (اختیاری)', placeholder: 'دلیل تسویه...' }
    ], async (data) => {
        try {
            ui.showLoading();
            await api.post('/api/settlements', {
                personnel_code: personnelCode,
                notes: data.notes
            });
            ui.showToast('تسویه حساب با موفقیت انجام شد', 'success');
            await viewSection(state.currentSection);
        } catch (error) {
            ui.showToast(error.message, 'error');
        } finally {
            ui.hideLoading();
        }
    });
}

async function exportSection(sectionName) {
    try {
        ui.showLoading();
        window.location.href = `/api/sections/${sectionName}/export`;
        ui.showToast('فایل اکسل در حال دانلود...', 'success');
    } catch (error) {
        ui.showToast(error.message, 'error');
    } finally {
        ui.hideLoading();
    }
}

// ============================================================================
// TRANSFER FUNCTIONS
// ============================================================================
async function approveTransfer(transferId) {
    ui.showConfirmDialog('آیا از تأیید و انجام این انتقال مطمئن هستید؟', async () => {
        try {
            ui.showLoading();
            await api.post(`/api/transfers/${transferId}/approve`);
            ui.showToast('انتقال با موفقیت تأیید و انجام شد', 'success');
            await loadDashboard();
        } catch (error) {
            ui.showToast(error.message, 'error');
        } finally {
            ui.hideLoading();
        }
    });
}

async function rejectTransfer(transferId) {
    ui.showPromptDialog('رد درخواست انتقال', [
        { name: 'reason', label: 'دلیل رد (اختیاری)', placeholder: 'دلیل رد درخواست...' }
    ], async (data) => {
        try {
            ui.showLoading();
            await api.post(`/api/transfers/${transferId}/reject`, { reason: data.reason });
            ui.showToast('درخواست انتقال رد شد', 'success');
            await loadDashboard();
        } catch (error) {
            ui.showToast(error.message, 'error');
        } finally {
            ui.hideLoading();
        }
    });
}

// ============================================================================
// USER MANAGEMENT FUNCTIONS
// ============================================================================
function showCreateUserModal() {
    const sectionOptions = state.sections.map(s => ({ value: s.name, label: s.name }));

    const modal = ui.showPromptDialog('ایجاد کاربر جدید', [
        { name: 'username', label: 'نام کاربری', required: true },
        { name: 'password', label: 'رمز عبور', type: 'password', required: true },
        { 
            name: 'role', 
            label: 'نقش', 
            type: 'select', 
            required: true,
            options: [
                { value: 'user', label: 'کاربر' },
                { value: 'admin', label: 'مدیر' }
            ]
        },
        {
            name: 'sections',
            label: 'بخش‌های دسترسی (برای مدیر خالی بگذارید)',
            type: 'select',
            options: sectionOptions
        }
    ], async (data) => {
        try {
            ui.showLoading();
            const sections = data.sections ? [data.sections] : [];
            await api.post('/api/users', {
                ...data,
                sections
            });
            ui.showToast('کاربر با موفقیت ایجاد شد', 'success');
            await renderView('users');
        } catch (error) {
            ui.showToast(error.message, 'error');
        } finally {
            ui.hideLoading();
        }
    });
}

async function editUser(username) {
    const user = state.users.find(u => u.username === username);
    if (!user) return;

    const sectionOptions = state.sections.map(s => ({ 
        value: s.name, 
        label: s.name,
        selected: user.sections.includes(s.name)
    }));

    ui.showPromptDialog(`ویرایش کاربر ${username}`, [
        { name: 'password', label: 'رمز عبور جدید (خالی بگذارید اگر نمی‌خواهید تغییر دهید)', type: 'password' },
        { 
            name: 'role', 
            label: 'نقش', 
            type: 'select', 
            required: true,
            options: [
                { value: 'user', label: 'کاربر' },
                { value: 'admin', label: 'مدیر' }
            ]
        },
        {
            name: 'sections',
            label: 'بخش‌های دسترسی',
            type: 'select',
            options: sectionOptions
        }
    ], async (data) => {
        try {
            ui.showLoading();
            const updateData = {
                role: data.role,
                sections: data.sections ? [data.sections] : []
            };
            if (data.password) updateData.password = data.password;
            
            await api.put(`/api/users/${username}`, updateData);
            ui.showToast('کاربر با موفقیت ویرایش شد', 'success');
            await renderView('users');
        } catch (error) {
            ui.showToast(error.message, 'error');
        } finally {
            ui.hideLoading();
        }
    });
}

async function deleteUser(username) {
    ui.showConfirmDialog(`آیا از حذف کاربر "${username}" مطمئن هستید؟`, async () => {
        try {
            ui.showLoading();
            await api.delete(`/api/users/${username}`);
            ui.showToast('کاربر با موفقیت حذف شد', 'success');
            await renderView('users');
        } catch (error) {
            ui.showToast(error.message, 'error');
        } finally {
            ui.hideLoading();
        }
    });
}

// ============================================================================
// LOG FUNCTIONS
// ============================================================================
async function exportLogs() {
    try {
        ui.showLoading();
        window.location.href = '/api/logs/export';
        ui.showToast('فایل اکسل در حال دانلود...', 'success');
    } catch (error) {
        ui.showToast(error.message, 'error');
    } finally {
        ui.hideLoading();
    }
}

// ============================================================================
// PASSWORD CHANGE
// ============================================================================
function showChangePasswordModal() {
    ui.showPromptDialog('تغییر رمز عبور', [
        { name: 'current_password', label: 'رمز عبور فعلی', type: 'password', required: true },
        { name: 'new_password', label: 'رمز عبور جدید', type: 'password', required: true },
        { name: 'confirm_password', label: 'تکرار رمز عبور جدید', type: 'password', required: true }
    ], async (data) => {
        if (data.new_password !== data.confirm_password) {
            ui.showToast('رمز عبور جدید و تکرار آن یکسان نیستند', 'error');
            return;
        }

        try {
            ui.showLoading();
            await api.post('/api/change-password', {
                current_password: data.current_password,
                new_password: data.new_password
            });
            ui.showToast('رمز عبور با موفقیت تغییر کرد', 'success');
        } catch (error) {
            ui.showToast(error.message, 'error');
        } finally {
            ui.hideLoading();
        }
    });
}

// ============================================================================
// INITIALIZATION
// ============================================================================
document.addEventListener('DOMContentLoaded', async () => {
    // Check if on login page
    if (window.location.pathname === '/login' || window.location.pathname === '/') {
        const loginForm = document.getElementById('login-form');
        if (loginForm) {
            loginForm.onsubmit = async (e) => {
                e.preventDefault();
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                await login(username, password);
            };
        }
        return;
    }

    // Check authentication
    const isAuthenticated = await checkAuth();
    if (!isAuthenticated) {
        window.location.href = '/login';
        return;
    }

    // Load dashboard
    await loadDashboard();

    // Refresh announcements every 30 seconds
    setInterval(async () => {
        await loadAnnouncements();
        renderAnnouncements();
    }, 30000);
});

// Export functions for global access
window.login = login;
window.logout = logout;
window.viewSection = viewSection;
window.deleteSection = deleteSection;
window.exportSection = exportSection;
window.deleteEmployee = deleteEmployee;
window.transferEmployee = transferEmployee;
window.settleEmployee = settleEmployee;
window.approveTransfer = approveTransfer;
window.rejectTransfer = rejectTransfer;
window.editUser = editUser;
window.deleteUser = deleteUser;
window.exportLogs = exportLogs;
window.showAddEmployeeModal = showAddEmployeeModal;
window.showUploadExcelModal = showUploadExcelModal;
window.renderView = renderView;
