/**
 * 管理员面板 - 用户管理与幽灵登录
 */

let users = [];
let currentUserId = null;
let resetPasswordUserId = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    if (window.lucide) {
        window.lucide.createIcons();
    }
    loadUsers();
    loadRetention();
    
    // 监听保留天数变化，更新提示
    var retentionInput = document.getElementById('retentionInput');
    if (retentionInput) {
        retentionInput.addEventListener('input', updateRetentionHint);
    }
});

/**
 * 获取当前幽灵登录的用户 ID（从 localStorage 读取）
 */
function getImpersonateUserId() {
    try {
        return localStorage.getItem('impersonate_user_id') || null;
    } catch(e) { return null; }
}

/**
 * 发起带 impersonation 参数的 fetch 请求
 */
function adminFetch(url, options = {}) {
    var impersonateId = getImpersonateUserId();
    var sep = url.includes('?') ? '&' : '?';
    var finalUrl = url + (impersonateId ? sep + 'impersonate_user_id=' + encodeURIComponent(impersonateId) : '');
    // 确保携带 Cookie（iframe 环境下需显式指定）
    options.credentials = options.credentials || 'include';
    // 同时附加请求头（双保险）
    var headers = options.headers || {};
    if (impersonateId) {
        if (headers instanceof Headers) {
            headers.set('X-Impersonate-User-Id', impersonateId);
        } else {
            headers['X-Impersonate-User-Id'] = impersonateId;
        }
    }
    options.headers = headers;
    return fetch(finalUrl, options);
}

/**
 * 加载用户列表
 */
async function loadUsers() {
    var tbody = document.getElementById('userTableBody');
    if (tbody) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty-row" data-i18n="admin.loadingUsers">加载中...</td></tr>';
        if (window.StudioI18n) window.StudioI18n.apply();
    }
    
    try {
        var res = await adminFetch('/api/admin/users');
        var data;
        try { data = await res.json(); } catch(e) { data = {}; }
        if (!res.ok) {
            throw new Error(data.detail || ('HTTP ' + res.status));
        }
        users = Array.isArray(data) ? data : [];
        renderUsers();
    } catch (e) {
        console.error('加载用户列表失败:', e);
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="6" class="empty-row error-row">加载失败：' + escapeHtml(e.message || e) + '</td></tr>';
        }
    }
}

/**
 * 渲染用户列表
 */
function renderUsers() {
    var tbody = document.getElementById('userTableBody');
    var countDesc = document.getElementById('userCountDesc');
    
    if (!tbody) return;
    
    if (!users.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty-row" data-i18n="admin.noUsers">暂无用户</td></tr>';
        if (window.StudioI18n) window.StudioI18n.apply();
        if (countDesc) countDesc.textContent = '共 0 位用户';
        return;
    }
    
    if (countDesc) {
        countDesc.textContent = '共 ' + users.length + ' 位用户';
    }
    
    var impersonateId = getImpersonateUserId();
    var isEn = window.StudioI18n?.lang?.() === 'en';
    
    tbody.innerHTML = users.map(function(user) {
        var isImpersonating = impersonateId === user.id;
        var roleLabel = user.is_admin
            ? (isEn ? 'Admin' : '管理员')
            : (isEn ? 'User' : '普通用户');
        var roleClass = user.is_admin ? 'role-admin' : 'role-user';
        var statusLabel = user.is_active
            ? (isEn ? 'Active' : '已启用')
            : (isEn ? 'Disabled' : '已禁用');
        var statusClass = user.is_active ? 'status-active' : 'status-disabled';
        var toggleLabel = user.is_active
            ? (isEn ? 'Disable' : '禁用')
            : (isEn ? 'Enable' : '启用');
        var impersonateLabel = isImpersonating
            ? (isEn ? 'Exit' : '退出')
            : (isEn ? 'Impersonate' : '幽灵登录');
        
        return '<tr class="' + (isImpersonating ? 'impersonating-row' : '') + '">' +
            '<td>' +
                '<div class="user-cell">' +
                    '<div class="user-avatar">' + (user.display_name || user.username).charAt(0).toUpperCase() + '</div>' +
                    '<div class="user-info">' +
                        '<div class="user-name">' + escapeHtml(user.username) + '</div>' +
                    '</div>' +
                '</div>' +
            '</td>' +
            '<td>' + escapeHtml(user.display_name || user.username) + '</td>' +
            '<td><span class="role-badge ' + roleClass + '">' + roleLabel + '</span></td>' +
            '<td><span class="status-badge ' + statusClass + '">' + statusLabel + '</span></td>' +
            '<td class="date-cell">' + formatDate(user.created_at) + '</td>' +
            '<td class="actions-cell">' +
                '<button class="row-btn ghost-btn" type="button" onclick="impersonateUser(\'' + user.id + '\')" title="' + (isEn ? 'Impersonate' : '幽灵登录') + '">' +
                    '<i data-lucide="' + (isImpersonating ? 'user-x' : 'user-check') + '" class="w-4 h-4"></i>' +
                    '<span>' + impersonateLabel + '</span>' +
                '</button>' +
                '<button class="row-btn" type="button" onclick="openResetPasswordModal(\'' + user.id + '\',\'' + escapeHtml(user.username) + '\')" title="' + (isEn ? 'Reset Password' : '重置密码') + '">' +
                    '<i data-lucide="key" class="w-4 h-4"></i>' +
                    '<span data-i18n="admin.resetPassword">重置密码</span>' +
                '</button>' +
                '<button class="row-btn danger-row-btn" type="button" onclick="toggleUserStatus(\'' + user.id + '\',' + !user.is_active + ')" title="' + toggleLabel + '">' +
                    '<i data-lucide="' + (user.is_active ? 'user-x' : 'user-check') + '" class="w-4 h-4"></i>' +
                    '<span>' + toggleLabel + '</span>' +
                '</button>' +
            '</td>' +
        '</tr>';
    }).join('');
    
    if (window.lucide) {
        window.lucide.createIcons();
    }
}

/**
 * 幽灵登录：以指定用户身份进入系统
 */
async function impersonateUser(userId) {
    var user = users.find(function(u) { return u.id === userId; });
    if (!user) return;
    
    var currentImpersonateId = getImpersonateUserId();
    var isEn = window.StudioI18n?.lang?.() === 'en';
    
    // 如果正在模拟该用户，则退出模拟
    if (currentImpersonateId === userId) {
        exitImpersonation();
        return;
    }
    
    // 确认提示
    var confirmMsg = isEn
        ? 'Are you sure you want to enter the system as "' + user.username + '"? All operations will be performed as this user.'
        : '确定要以「' + user.username + '」的身份进入系统吗？进入后所有操作将以该用户身份执行。';
    if (!confirm(confirmMsg)) return;
    
    try {
        // 设置 localStorage，主框架会监听并同步
        localStorage.setItem('impersonate_user_id', userId);
        localStorage.setItem('impersonate_user_name', user.username || user.display_name);
        
        // 通知父框架
        if (window.parent !== window) {
            try {
                window.parent.postMessage({ type: 'impersonate-start', userId: userId, userName: user.username || user.display_name }, '*');
            } catch(e) {}
        }
        
        // 刷新列表显示状态
        renderUsers();
        
        showStatus(isEn ? 'Impersonation started' : '已进入幽灵模式', 'ok');
    } catch(e) {
        console.error('幽灵登录失败:', e);
        showStatus((isEn ? 'Failed: ' : '失败：') + (e.message || e), 'error');
    }
}

/**
 * 退出幽灵登录
 */
function exitImpersonation() {
    try {
        localStorage.removeItem('impersonate_user_id');
        localStorage.removeItem('impersonate_user_name');
        
        // 通知父框架
        if (window.parent !== window) {
            try {
                window.parent.postMessage({ type: 'impersonate-end' }, '*');
            } catch(e) {}
        }
        
        renderUsers();
        var isEn = window.StudioI18n?.lang?.() === 'en';
        showStatus(isEn ? 'Exited impersonation' : '已退出幽灵模式', 'ok');
    } catch(e) {
        console.error('退出幽灵登录失败:', e);
    }
}

/**
 * 打开重置密码弹窗
 */
function openResetPasswordModal(userId, username) {
    resetPasswordUserId = userId;
    var modal = document.getElementById('resetPasswordModal');
    var title = document.getElementById('resetPasswordTitle');
    var input = document.getElementById('newPasswordInput');
    if (title) {
        var isEn = window.StudioI18n?.lang?.() === 'en';
        title.textContent = isEn
            ? 'Reset password for ' + username
            : '重置「' + username + '」的密码';
    }
    if (input) input.value = '';
    if (modal) modal.hidden = false;
    if (input) input.focus();
}

/**
 * 关闭重置密码弹窗
 */
function closeResetPasswordModal() {
    resetPasswordUserId = null;
    var modal = document.getElementById('resetPasswordModal');
    if (modal) modal.hidden = true;
}

/**
 * 确认重置密码
 */
async function confirmResetPassword() {
    if (!resetPasswordUserId) return;
    
    var input = document.getElementById('newPasswordInput');
    var newPassword = input ? input.value.trim() : '';
    var isEn = window.StudioI18n?.lang?.() === 'en';
    
    if (!newPassword || newPassword.length < 4 || newPassword.length > 50) {
        alert(isEn ? 'Password must be 4-50 characters' : '密码长度必须在 4-50 位之间');
        return;
    }
    
    try {
        var res = await adminFetch('/api/admin/users/' + resetPasswordUserId + '/reset-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ new_password: newPassword })
        });
        
        var data = await res.json();
        if (!res.ok) throw new Error(data.detail || (isEn ? 'Failed' : '失败'));
        
        showStatus(isEn ? 'Password reset successful' : '密码重置成功', 'ok');
        closeResetPasswordModal();
    } catch(e) {
        console.error('重置密码失败:', e);
        showStatus((isEn ? 'Failed: ' : '失败：') + (e.message || e), 'error');
    }
}

/**
 * 切换用户状态（启用/禁用）
 */
async function toggleUserStatus(userId, isActive) {
    var isEn = window.StudioI18n?.lang?.() === 'en';
    var confirmMsg = isActive
        ? (isEn ? 'Enable this user?' : '确定要启用该用户吗？')
        : (isEn ? 'Disable this user?' : '确定要禁用该用户吗？');
    
    if (!confirm(confirmMsg)) return;
    
    try {
        var res = await adminFetch('/api/admin/users/' + userId + '/status', {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_active: isActive })
        });
        
        var data = await res.json();
        if (!res.ok) throw new Error(data.detail || (isEn ? 'Failed' : '失败'));
        
        showStatus(isEn ? 'User status updated' : '用户状态已更新', 'ok');
        loadUsers();
    } catch(e) {
        console.error('切换用户状态失败:', e);
        showStatus((isEn ? 'Failed: ' : '失败：') + (e.message || e), 'error');
    }
}

/**
 * 加载数据保留天数配置
 */
async function loadRetention() {
    try {
        var res = await adminFetch('/api/admin/config/retention');
        if (!res.ok) return;
        var data = await res.json();
        var input = document.getElementById('retentionInput');
        if (input && typeof data.days === 'number') {
            input.value = data.days;
            updateRetentionHint();
        }
    } catch(e) {
        console.error('加载保留天数配置失败:', e);
    }
}

/**
 * 更新保留天数提示文字
 */
function updateRetentionHint() {
    var input = document.getElementById('retentionInput');
    var hint = document.getElementById('retentionHint');
    if (!input || !hint) return;
    
    var days = parseInt(input.value) || 0;
    var isEn = window.StudioI18n?.lang?.() === 'en';
    hint.textContent = days === 0
        ? (isEn ? 'Permanent' : '永久保留')
        : (isEn ? days + ' days' : days + ' 天');
}

/**
 * 保存数据保留天数配置
 */
async function saveRetention() {
    var input = document.getElementById('retentionInput');
    var days = parseInt(input?.value) || 0;
    var isEn = window.StudioI18n?.lang?.() === 'en';
    
    try {
        var res = await adminFetch('/api/admin/config/retention', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ days: days })
        });
        
        var data = await res.json();
        if (!res.ok) throw new Error(data.detail || (isEn ? 'Failed' : '失败'));
        
        showStatus(isEn ? 'Settings saved' : '保存成功', 'ok');
    } catch(e) {
        console.error('保存保留天数失败:', e);
        showStatus((isEn ? 'Failed: ' : '失败：') + (e.message || e), 'error');
    }
}

/**
 * 显示状态提示
 */
function showStatus(message, type) {
    var statusEl = document.getElementById('status');
    if (!statusEl) return;
    
    statusEl.textContent = message;
    statusEl.className = 'status ' + (type || '');
    
    clearTimeout(showStatus._timer);
    showStatus._timer = setTimeout(function() {
        statusEl.className = 'status';
    }, 3000);
}

/**
 * HTML 转义
 */
function escapeHtml(text) {
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * 格式化日期
 */
function formatDate(dateStr) {
    if (!dateStr) return '-';
    try {
        var d = new Date(dateStr);
        if (isNaN(d.getTime())) return dateStr;
        var y = d.getFullYear();
        var m = String(d.getMonth() + 1).padStart(2, '0');
        var day = String(d.getDate()).padStart(2, '0');
        var hh = String(d.getHours()).padStart(2, '0');
        var mm = String(d.getMinutes()).padStart(2, '0');
        return y + '-' + m + '-' + day + ' ' + hh + ':' + mm;
    } catch(e) {
        return dateStr;
    }
}

// 监听来自父窗口的消息
window.addEventListener('message', function(event) {
    if (!event.data) return;
    if (event.data.type === 'impersonate-start' || event.data.type === 'impersonate-end') {
        renderUsers();
    }
});

// 监听 localStorage 变化（同步跨 iframe 状态）
window.addEventListener('storage', function(e) {
    if (e.key === 'impersonate_user_id') {
        renderUsers();
    }
});
