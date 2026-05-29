// Admin Dashboard JavaScript
// Handles authentication, data fetching, and UI interactions

const API_BASE = '/api/admin-panel';

let currentUser = null;
let currentPage = 'dashboard';
let registrationsTable = null;
let currentRegistrationId = null;
let currentEventId = null; // For filtering by event
let allEvents = []; // Cache of all events
let selectedRegistrations = []; // Track selected registration IDs for bulk operations
const SIDEBAR_STORAGE_KEY = 'gdta_admin_sidebar_collapsed';

function getErrorMessage(payload, fallback = 'Request failed') {
    if (!payload) return fallback;
    if (typeof payload === 'string') return payload;
    if (payload.error?.message) return payload.error.message;
    if (payload.message) return payload.message;
    if (typeof payload.error === 'string') return payload.error;
    return fallback;
}

function unwrapPayload(payload) {
    if (!payload || typeof payload !== 'object') return payload;
    if (Object.prototype.hasOwnProperty.call(payload, 'data')) {
        return payload.data;
    }
    return payload;
}

function extractList(payload, key) {
    const data = unwrapPayload(payload);
    if (Array.isArray(data)) return data;
    if (data && Array.isArray(data[key])) return data[key];
    return [];
}

function normalizeRole(role) {
    return String(role || '').trim().toUpperCase();
}

function toCountList(map, keyName) {
    if (!map || typeof map !== 'object') return [];
    return Object.entries(map).map(([key, count]) => ({ [keyName]: key, count }));
}

function normalizeStats(stats) {
    if (!stats || typeof stats !== 'object') {
        return {
            total: 0,
            by_status: { pending: 0, approved: 0 },
            by_country: [],
            by_role: [],
            today: 0,
            payment_summary: { paid: 0 }
        };
    }

    if (stats.total && stats.by_status) return stats;

    const total = stats.total_registrations ?? stats.total ?? 0;
    const byStatus = stats.status_breakdown || stats.by_status || {};
    const byCountry = stats.country_distribution
        ? toCountList(stats.country_distribution, 'country')
        : stats.by_country || [];
    const byRole = stats.role_distribution
        ? toCountList(stats.role_distribution, 'role')
        : stats.by_role || [];

    return {
        total,
        by_status: {
            pending: byStatus.pending || 0,
            approved: byStatus.approved || 0,
            rejected: byStatus.rejected || 0
        },
        by_country: byCountry,
        by_role: byRole,
        today: stats.today || 0,
        payment_summary: stats.payment_summary || { paid: 0 }
    };
}

function applySidebarState(isCollapsed) {
    document.body.classList.toggle('sidebar-collapsed', Boolean(isCollapsed));
}

function initSidebarState() {
    const collapsed = localStorage.getItem(SIDEBAR_STORAGE_KEY) === 'true';
    applySidebarState(collapsed);
}

function toggleSidebar() {
    const nextCollapsed = !document.body.classList.contains('sidebar-collapsed');
    localStorage.setItem(SIDEBAR_STORAGE_KEY, String(nextCollapsed));
    applySidebarState(nextCollapsed);
}

function getRequestedPageFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const page = params.get('page');
    const validPages = new Set([
        'dashboard',
        'registrations',
        'venues',
        'volunteers',
        'access-logs',
        'email',
        'email-templates',
        'export',
        'events',
        'admins'
    ]);
    return validPages.has(page) ? page : 'dashboard';
}

function getPaymentBadge(paymentStatus) {
    const normalized = String(paymentStatus || 'pending').toLowerCase();
    if (normalized === 'paid') {
        return '<span class="badge badge-payment-paid">Paid ✅</span>';
    }
    if (normalized === 'payment_link_created') {
        return '<span class="badge badge-payment-link">Link Created</span>';
    }
    if (normalized === 'payment_pending') {
        return '<span class="badge badge-payment-pending">Pending</span>';
    }
    return '<span class="badge badge-payment-pending">Pending</span>';
}

function getRegistrationStatusPill(status) {
    const normalized = String(status || 'pending').toLowerCase();
    return `<span class="registration-pill ${normalized}">${normalized}</span>`;
}

function getRegistrationPaymentPill(paymentStatus) {
    const normalized = String(paymentStatus || 'pending').toLowerCase();
    if (normalized === 'paid') {
        return '<span class="registration-pill payment-paid">Paid</span>';
    }
    if (normalized === 'payment_link_created') {
        return '<span class="registration-pill payment-link">Link Created</span>';
    }
    return '<span class="registration-pill payment-pending">Pending</span>';
}

// ========== AUTHENTICATION ==========

function showLogin() {
    $('#loginPage').removeClass('hidden');
    $('#dashboardPage').addClass('hidden');
}

function showDashboard() {
    $('#loginPage').addClass('hidden');
    $('#dashboardPage').removeClass('hidden');
    switchPage(getRequestedPageFromUrl());
}

function applyRoleBasedUI() {
    if (!currentUser) return;

    $('.admin_only').show();
    $('#eventSelectorContainer').show();

    if (currentUser.assigned_events && currentUser.assigned_events.length > 0) {
        currentEventId = currentUser.assigned_events[0];
    }

    $('.sidebar-brand h4').html('<i class="fas fa-chart-line me-2"></i><span class="brand-label">GDTA Admin</span>');
}

async function login(username, password) {
    try {
        const response = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ username, password })
        });
        
        const payload = await response.json();
        const data = unwrapPayload(payload);
        const user = data?.user || payload?.user || data;
        
        if (response.ok) {
            if (!user) {
                return { success: false, error: 'Login succeeded but user data is missing.' };
            }
            currentUser = user;

            updateUserInfo();
            applyRoleBasedUI();
            showDashboard();
            return { success: true };
        } else {
            return { success: false, error: getErrorMessage(payload, 'Invalid username or password') };
        }
    } catch (error) {
        console.error('Login error:', error);
        return { success: false, error: 'Login failed. Please try again.' };
    }
}

async function logout() {
    try {
        await fetch(`${API_BASE}/logout`, {
            method: 'POST',
            credentials: 'include'
        });
    } catch (error) {
        console.error('Logout error:', error);
    }
    
    currentUser = null;
    showLogin();
}

async function checkAuth() {
    try {
        const response = await fetch(`${API_BASE}/me`, {
            credentials: 'include'
        });

        if (!response.ok) {
            showLogin();
            return;
        }

        const payload = await response.json();
        const data = unwrapPayload(payload);
        const user = data?.user || payload?.user || data;
        if (!user) {
            showLogin();
            return;
        }

        currentUser = user;
        updateUserInfo();
        applyRoleBasedUI();
        showDashboard();
    } catch (error) {
        console.error('Auth check failed:', error);
        showLogin();
    }
}

function updateUserInfo() {
    if (currentUser) {
        $('#adminName').text(currentUser.name);
        $('#adminRole').text(currentUser.role.toUpperCase());
        $('#adminAvatar').text(currentUser.name.charAt(0).toUpperCase());
    }
}

// ========== NAVIGATION ==========

function switchPage(pageName) {
    currentPage = pageName;
    
    // Update sidebar
    $('.sidebar-menu a').removeClass('active');
    $(`.sidebar-menu a[data-page="${pageName}"]`).addClass('active');
    
    // Hide all views
    $('.page-view').addClass('hidden');
    
    // Show selected view
    $(`#${pageName}View`).removeClass('hidden');
    
    // Update page title in top bar
    const pageTitles = {
        'dashboard': 'Dashboard',
        'registrations': 'Registration Management',
        'venues': 'Venue Management',
        'volunteers': 'Volunteer Management',
        'access-logs': 'Access Logs',
        'email': 'Send Email',
        'email-templates': 'Email Templates',
        'export': 'Export Data',
        'events': 'Event Management',
        'admins': 'Admin Management'
    };
    $('#pageTitle').text(pageTitles[pageName] || 'Dashboard');
    
    // Load page data
    if (pageName === 'dashboard') {
        loadDashboard();
    } else if (pageName === 'registrations') {
        loadRegistrations();
    } else if (pageName === 'venues') {
        loadVenues();
    } else if (pageName === 'volunteers') {
        loadVolunteers();
    } else if (pageName === 'access-logs') {
        loadAccessLogs();
    } else if (pageName === 'email-templates') {
        loadEmailTemplates();
    } else if (pageName === 'events') {
        loadEvents();
    } else if (pageName === 'admins') {
        loadAdmins();
    }
}

// ========== DASHBOARD ==========

async function loadDashboard() {
    try {
        $('#dashboardTitle').html('<i class="fas fa-chart-line me-2"></i>Registration Dashboard');
        $('#dashboardSubtitle').text('Monitor and manage event registrations');
        
        let url = `${API_BASE}/stats`;
        if (currentEventId) url += `?event_id=${currentEventId}`;
        
        console.log('Loading dashboard with event ID:', currentEventId, 'URL:', url);
        
        const response = await fetch(url, {
            credentials: 'include'
        });

        if (response.status === 401) {
            showLogin();
            return;
        }
        
        const payload = await response.json();
        const stats = normalizeStats(unwrapPayload(payload));
        
        // Reset labels for regular admin
        $('#totalRegistrations').siblings('p').text('Total Registrations');
        $('#pendingRegistrations').siblings('p').text('Pending Review');
        $('#approvedRegistrations').siblings('p').text('Approved');
        $('#todayRegistrations').siblings('p').text('Today');
        
        // Update stat cards
        $('#totalRegistrations').text(stats.total || 0);
        $('#pendingRegistrations').text(stats.by_status?.pending || 0);
        $('#approvedRegistrations').text(stats.by_status?.approved || 0);
        $('#todayRegistrations').text((stats.payment_summary && typeof stats.payment_summary.paid !== 'undefined') ? stats.payment_summary.paid : (stats.today || 0));
        $('#todayRegistrations').siblings('p').text((stats.payment_summary && typeof stats.payment_summary.paid !== 'undefined') ? 'Payments Successful' : 'Today');
        
        // Update country stats
        let countryHtml = '<div class="list-group">';
        stats.by_country.forEach(item => {
            countryHtml += `
                <div class="list-group-item d-flex justify-content-between align-items-center">
                    ${item.country}
                    <span class="badge bg-primary rounded-pill">${item.count}</span>
                </div>
            `;
        });
        countryHtml += '</div>';
        $('#countryStats').html(countryHtml);
        $('#countryStats').siblings('h5').html('<i class="fas fa-globe me-2"></i>Top Countries');
        
        // Update role stats
        let roleHtml = '<div class="list-group">';
        stats.by_role.forEach(item => {
            roleHtml += `
                <div class="list-group-item d-flex justify-content-between align-items-center">
                    ${item.role}
                    <span class="badge bg-secondary rounded-pill">${item.count}</span>
                </div>
            `;
        });
        roleHtml += '</div>';
        $('#roleStats').html(roleHtml);
        $('#roleStats').siblings('h5').html('<i class="fas fa-user-tag me-2"></i>Roles Distribution');
        
        // Load check-in statistics
        await loadCheckInStats();
        
    } catch (error) {
        console.error('Failed to load dashboard:', error);
    }
}

// ========== CHECK-IN STATISTICS ==========

async function loadCheckInStats() {
    try {
        let url = `${API_BASE}/check-in/stats`;
        if (currentEventId) url += `?event_id=${currentEventId}`;
        
        const response = await fetch(url, { credentials: 'include' });
        const data = await response.json();
        
        if (response.ok && data.success) {
            $('#checkinStatCheckedIn').text(data.stats.checked_in);
            $('#checkinStatPending').text(data.stats.not_checked_in);
            $('#checkinStatPercentage').text(data.stats.percentage + '%');
            $('#checkinStatTotal').text(data.stats.total_approved);
        }
        
    } catch (error) {
        console.error('Failed to load check-in stats:', error);
        $('#checkinStatCheckedIn').text('-');
        $('#checkinStatPending').text('-');
        $('#checkinStatPercentage').text('-');
        $('#checkinStatTotal').text('-');
    }
}

// ========== REGISTRATIONS ==========

// Bulk Operations
function toggleSelectAll() {
    const checkbox = document.getElementById('selectAllCheckbox');
    const checkboxes = document.querySelectorAll('.registration-checkbox');
    
    checkboxes.forEach(cb => {
        cb.checked = checkbox.checked;
    });
    
    updateSelectedRegistrations();
}

function updateSelectedRegistrations() {
    selectedRegistrations = [];
    document.querySelectorAll('.registration-checkbox:checked').forEach(cb => {
        selectedRegistrations.push(cb.value);
    });
    
    updateSelectedCount();
    toggleBulkActionsPanel();
}

function updateSelectedCount() {
    document.getElementById('selectedCount').textContent = selectedRegistrations.length;
}

function toggleBulkActionsPanel() {
    const panel = document.getElementById('bulkActionsPanel');
    if (selectedRegistrations.length > 0) {
        panel.style.display = 'block';
    } else {
        panel.style.display = 'none';
    }
}

function clearSelection() {
    selectedRegistrations = [];
    document.getElementById('selectAllCheckbox').checked = false;
    document.querySelectorAll('.registration-checkbox').forEach(cb => {
        cb.checked = false;
    });
    updateSelectedCount();
    toggleBulkActionsPanel();
}

async function bulkApprove() {
    if (selectedRegistrations.length === 0) {
        alert('Please select at least one registration');
        return;
    }
    
    if (!confirm(`Approve ${selectedRegistrations.length} registration(s)?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/registrations/bulk/approve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ registration_ids: selectedRegistrations })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert(`Successfully approved ${data.approved} registration(s). Failed: ${data.failed}`);
            clearSelection();
            loadRegistrations();
        } else {
            alert(`Error: ${data.error}`);
        }
    } catch (error) {
        console.error('Bulk approve error:', error);
        alert('Failed to approve registrations');
    }
}

async function bulkReject() {
    if (selectedRegistrations.length === 0) {
        alert('Please select at least one registration');
        return;
    }
    
    if (!confirm(`Reject ${selectedRegistrations.length} registration(s)?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/registrations/bulk/reject`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ registration_ids: selectedRegistrations })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert(`Successfully rejected ${data.rejected} registration(s). Failed: ${data.failed}`);
            clearSelection();
            loadRegistrations();
        } else {
            alert(`Error: ${data.error}`);
        }
    } catch (error) {
        console.error('Bulk reject error:', error);
        alert('Failed to reject registrations');
    }
}

async function bulkSetPending() {
    if (selectedRegistrations.length === 0) {
        alert('Please select at least one registration');
        return;
    }
    
    if (!confirm(`Set ${selectedRegistrations.length} registration(s) to Pending?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/registrations/bulk/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ 
                registration_ids: selectedRegistrations,
                status: 'pending'
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert(`Successfully updated ${data.updated} registration(s) to Pending. Failed: ${data.failed}`);
            clearSelection();
            loadRegistrations();
        } else {
            alert(`Error: ${data.error}`);
        }
    } catch (error) {
        console.error('Bulk set pending error:', error);
        alert('Failed to update registrations');
    }
}

function bulkEmail() {
    if (selectedRegistrations.length === 0) {
        alert('Please select at least one registration');
        return;
    }
    
    // Update modal with selected count
    document.getElementById('bulkEmailCount').textContent = selectedRegistrations.length;
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('bulkEmailModal'));
    modal.show();
}

async function sendBulkEmail() {
    const mode = document.querySelector('input[name="emailMode"]:checked').value;
    let requestBody = {
        registration_ids: selectedRegistrations
    };
    
    if (mode === 'template') {
        const templateId = document.getElementById('templateSelect').value;
        if (!templateId) {
            alert('Please select a template');
            return;
        }
        requestBody.template_id = templateId;
    } else {
        const subject = document.getElementById('bulkEmailSubject').value.trim();
        const message = document.getElementById('bulkEmailMessage').value.trim();
        
        if (!subject || !message) {
            alert('Please enter both subject and message');
            return;
        }
        
        requestBody.subject = subject;
        requestBody.message = message;
    }
    
    const sendButton = document.getElementById('sendBulkEmailBtn');
    sendButton.disabled = true;
    sendButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Sending...';
    
    try {
        const response = await fetch(`${API_BASE}/registrations/bulk/email`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(requestBody)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert(`Successfully sent ${data.sent} email(s). Failed: ${data.failed}`);
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('bulkEmailModal'));
            modal.hide();
            
            // Reset form
            document.getElementById('bulkEmailSubject').value = '';
            document.getElementById('bulkEmailMessage').value = '';
            document.querySelector('input[name="emailMode"][value="custom"]').checked = true;
            toggleEmailMode('custom');
            
            clearSelection();
        } else {
            alert(`Error: ${data.error}`);
        }
    } catch (error) {
        console.error('Bulk email error:', error);
        alert('Failed to send emails');
    } finally {
        sendButton.disabled = false;
        sendButton.innerHTML = '<i class="fas fa-paper-plane me-2"></i>Send Email';
    }
}


async function loadRegistrations() {
    const status = $('#filterStatus').val();
    const country = $('#filterCountry').val();
    const search = $('#searchBox').val();
    
    // Advanced filters
    const dateFrom = $('#filterDateFrom').val();
    const dateTo = $('#filterDateTo').val();
    const updatedFrom = $('#filterUpdatedFrom').val();
    const updatedTo = $('#filterUpdatedTo').val();
    const statusMulti = $('#filterStatusMulti').val(); // Array
    const countryMulti = $('#filterCountryMulti').val(); // Array
    const gdtaMember = $('#filterGdtaMember').val();
    const regSource = $('#filterRegSource').val();
    const checkedIn = $('#filterCheckedIn').val();
    const paymentStatus = $('#filterPaymentStatus').val();
    
    try {
        let url = `${API_BASE}/registrations?`;
        if (currentEventId) url += `event_id=${currentEventId}&`;
        
        // Basic filters (backward compatibility)
        if (status) url += `status=${status}&`;
        if (country) url += `country=${country}&`;
        if (search) url += `search=${encodeURIComponent(search)}&`;
        
        // Advanced filters
        if (dateFrom) url += `date_from=${dateFrom}T00:00:00Z&`;
        if (dateTo) url += `date_to=${dateTo}T23:59:59Z&`;
        if (updatedFrom) url += `updated_from=${updatedFrom}T00:00:00Z&`;
        if (updatedTo) url += `updated_to=${updatedTo}T23:59:59Z&`;
        
        // Multi-select filters (use arrays if advanced filters are active, otherwise single values)
        if (statusMulti && statusMulti.length > 0) {
            url += `status=${statusMulti.join(',')}&`;
        }
        if (countryMulti && countryMulti.length > 0) {
            url += `country=${countryMulti.join(',')}&`;
        }
        
        if (gdtaMember) url += `is_gdta_member=${gdtaMember}&`;
        if (regSource) url += `registration_source=${regSource}&`;
        if (checkedIn) url += `checked_in=${checkedIn}&`;
        if (paymentStatus) url += `payment_status=${encodeURIComponent(paymentStatus)}&`;
        
        const response = await fetch(url, { credentials: 'include' });

        if (response.status === 401) {
            showLogin();
            return;
        }

        const payload = await response.json();
        const registrations = extractList(payload, 'registrations');
        
        displayRegistrations(registrations);
        updateCountryFilter(registrations);
        updateCountryMultiSelectFilter(registrations);
        updateActiveFiltersCount();
        
    } catch (error) {
        console.error('Failed to load registrations:', error);
    }
}

function displayRegistrations(registrations) {
    if (registrationsTable) {
        registrationsTable.destroy();
    }
    
    const tbody = $('#registrationsTable tbody');
    tbody.empty();

    if (!Array.isArray(registrations)) {
        registrations = [];
    }
    
    registrations.forEach(reg => {
        const statusBadge = getRegistrationStatusPill(reg.status);
        const paymentBadge = getRegistrationPaymentPill(reg.payment_status);
        const createdDate = new Date(reg.created_at).toLocaleDateString();
        const updatedDate = reg.updated_at ? new Date(reg.updated_at).toLocaleDateString() : createdDate;
        const uniqueId = reg.unique_id ? `<code class="text-primary">${reg.unique_id}</code>` : '<span class="text-muted">-</span>';
        const feeDisplay = (reg.fee_currency && reg.total_fee !== null && reg.total_fee !== undefined)
            ? (reg.fee_currency === 'USD' ? `$${reg.total_fee}` : `Rs.${reg.total_fee}`)
            : 'N/A';
        const safariRouteInline = reg.safari_route ? `<br><small class="text-muted">Safari: ${reg.safari_route}</small>` : '';
        
        // ID Card button - use smart endpoint that regenerates if needed
        let idCardButton = '';
        if (reg.id_card_generated && reg.unique_id) {
            // Use the smart view endpoint that will regenerate if file is missing
            const viewUrl = `${API_BASE}/id-card/view/${encodeURIComponent(reg.unique_id)}`;
            idCardButton = `
                <a href="${viewUrl}" target="_blank" class="btn btn-sm btn-success me-1" title="View/Download ID Card">
                    <i class="fas fa-id-card"></i>
                </a>`;
        } else if (reg.status === 'approved') {
            idCardButton = `
                <button class="btn btn-sm btn-warning me-1" onclick="generateIDCard('${reg.id}')" title="Generate ID Card">
                    <i class="fas fa-id-card-alt"></i>
                </button>`;
        } else {
            idCardButton = `
                <button class="btn btn-sm btn-secondary me-1" disabled title="Approve registration first">
                    <i class="fas fa-id-card"></i>
                </button>`;
        }
        
        tbody.append(`
            <tr>
                <td><input type="checkbox" class="registration-checkbox" value="${reg.id}" onchange="updateSelectedRegistrations()"></td>
                <td class="registration-id-cell">
                    <div class="registration-id-primary">${reg.id}</div>
                    <div class="registration-id-secondary">Created ${createdDate}</div>
                </td>
                <td>
                    <div class="registration-uid">${uniqueId}</div>
                    <div class="registration-id-secondary">Updated ${updatedDate}</div>
                </td>
                <td class="registration-person-cell">
                    <div class="registration-person-name">${reg.name || '-'}</div>
                    <div class="registration-person-email">${reg.title ? `${reg.title}. ` : ''}${reg.gender || ''}</div>
                </td>
                <td class="registration-person-cell">
                    <div class="registration-person-name">${reg.email || '-'}</div>
                    <div class="registration-person-email">${reg.registration_source || 'system'}</div>
                </td>
                <td>
                    <div class="registration-person-name">${reg.institution || '-'}</div>
                    <div class="registration-meta-line">${reg.state || 'State not provided'}</div>
                </td>
                <td>
                    <div class="registration-person-name">${reg.country || '-'}</div>
                    <div class="registration-meta-line">${reg.gdta_member === 'yes' ? 'GDTA Member' : 'Non-member'}</div>
                </td>
                <td class="registration-person-cell">
                    <div class="registration-person-name">${reg.role || '-'}</div>
                    <div class="registration-meta-line">Fee: ${feeDisplay}</div>
                    ${safariRouteInline}
                </td>
                <td>${statusBadge}</td>
                <td>${paymentBadge}</td>
                <td>
                    <div class="registration-person-name">${createdDate}</div>
                    <div class="registration-meta-line">${updatedDate !== createdDate ? `Updated ${updatedDate}` : 'No later updates'}</div>
                </td>
                <td>
                    <div class="registration-actions">
                    <button class="btn btn-sm btn-primary me-1" onclick="viewDetails('${reg.id}')" title="View Details">
                        <i class="fas fa-eye"></i>
                    </button>
                    ${idCardButton}
                    <button class="btn btn-sm btn-danger" onclick="deleteRegistration('${reg.id}', '${reg.name.replace(/'/g, "\\'")}')" title="Delete Registration">
                        <i class="fas fa-trash"></i>
                    </button>
                    </div>
                </td>
            </tr>
        `);
    });
    
    registrationsTable = $('#registrationsTable').DataTable({
        pageLength: 25,
        order: [[1, 'desc']], // Sort by ID column (now index 1 instead of 0)
        scrollX: true,
        autoWidth: false,
        columnDefs: [
            { orderable: false, targets: 0 } // Disable sorting on checkbox column
        ]
    });
    
    // Reset selection when table is reloaded
    clearSelection();
}

function updateCountryFilter(registrations) {
    const countries = [...new Set(registrations.map(r => r.country))].sort();
    const select = $('#filterCountry');
    const currentValue = select.val();
    
    select.empty();
    select.append('<option value="">All Countries</option>');
    
    countries.forEach(country => {
        select.append(`<option value="${country}">${country}</option>`);
    });
    
    if (currentValue) {
        select.val(currentValue);
    }
}

async function viewDetails(registrationId) {
    currentRegistrationId = registrationId;
    
    try {
        const response = await fetch(`${API_BASE}/registrations/${encodeURIComponent(registrationId)}`, {
            credentials: 'include'
        });
        
        const reg = await response.json();
        
        // Fetch ID card status
        const statusResponse = await fetch(`${API_BASE}/id-card/status/${encodeURIComponent(registrationId)}`, {
            credentials: 'include'
        });
        const cardStatus = statusResponse.ok ? await statusResponse.json() : null;
        
        let idCardStatusHtml = '';
        if (cardStatus && cardStatus.success) {
            const generatedDate = cardStatus.id_card_generated_at ? 
                new Date(cardStatus.id_card_generated_at).toLocaleString() : 'N/A';
            
            idCardStatusHtml = `
                <div class="col-12">
                    <div class="alert alert-info">
                        <h6><i class="fas fa-qrcode"></i> ID Card & QR Code Information</h6>
                        <div class="row g-2 mt-2">
                            <div class="col-md-6">
                                <strong>Unique ID:</strong> <code>${cardStatus.unique_id}</code>
                                <button class="btn btn-sm btn-outline-secondary ms-2" onclick="copyUniqueId('${cardStatus.unique_id}')">
                                    <i class="fas fa-copy"></i> Copy
                                </button>
                            </div>
                            <div class="col-md-6">
                                <strong>ID Card Generated:</strong> 
                                ${cardStatus.id_card_generated ? 
                                    '<span class="badge bg-success">Yes</span>' : 
                                    '<span class="badge bg-warning">Not Yet</span>'}
                            </div>
                            ${cardStatus.id_card_generated ? `
                                <div class="col-md-6">
                                    <strong>Generated At:</strong> ${generatedDate}
                                </div>
                                <div class="col-md-6">
                                    <strong>Can Regenerate:</strong> 
                                    ${cardStatus.can_generate ? 
                                        '<span class="badge bg-success">Yes</span>' : 
                                        '<span class="badge bg-danger">Needs Approval</span>'}
                                </div>
                            ` : ''}
                        </div>
                        <div class="mt-3">
                            ${cardStatus.id_card_generated && reg.unique_id ? 
                                `<a href="${API_BASE}/id-card/view/${encodeURIComponent(reg.unique_id)}" target="_blank" class="btn btn-sm btn-success me-2">
                                    <i class="fas fa-download"></i> View/Download ID Card
                                </a>` : ''
                            }
                            ${cardStatus.can_generate ? 
                                `<button class="btn btn-sm btn-primary" onclick="generateIDCardFromDetail('${registrationId}')">
                                    <i class="fas fa-id-card"></i> ${cardStatus.id_card_generated ? 'Regenerate' : 'Generate'} ID Card
                                </button>` : 
                                `<button class="btn btn-sm btn-warning" onclick="approveRegeneration('${registrationId}')">
                                    <i class="fas fa-unlock"></i> Approve Regeneration
                                </button>`
                            }
                        </div>
                    </div>
                </div>
            `;
        }
        
        const feeDisplay = (reg.fee_currency && reg.total_fee !== null && reg.total_fee !== undefined)
            ? (reg.fee_currency === 'USD' ? `$${reg.total_fee}` : `Rs.${reg.total_fee}`)
            : 'N/A';

        let html = `
            <div class="row g-3">
                ${idCardStatusHtml}
                <div class="col-md-6">
                    <strong>Name:</strong> ${reg.name}
                </div>
                <div class="col-md-6">
                    <strong>Email:</strong> ${reg.email}
                </div>
                <div class="col-md-6">
                    <strong>Institution:</strong> ${reg.institution}
                </div>
                <div class="col-md-6">
                    <strong>Role:</strong> ${reg.role}
                </div>
                <div class="col-md-6">
                    <strong>GDTA Member:</strong> ${reg.gdta_member}
                </div>
                <div class="col-md-6">
                    <strong>GDTA Affiliation:</strong> ${reg.gdta_affiliation || 'N/A'}
                </div>
                <div class="col-md-6">
                    <strong>Country:</strong> ${reg.country}
                </div>
                <div class="col-md-6">
                    <strong>State:</strong> ${reg.state || 'N/A'}
                </div>
                <div class="col-md-6">
                    <strong>Registered:</strong> ${new Date(reg.created_at).toLocaleString()}
                </div>
                <div class="col-md-6">
                    <strong>Source:</strong> ${reg.registration_source}
                </div>
                <div class="col-md-6">
                    <strong>Registration Category:</strong> ${reg.registration_category || 'N/A'}
                </div>
                <div class="col-md-6">
                    <strong>Total Fee:</strong> ${feeDisplay}
                </div>
                <div class="col-md-6">
                    <strong>Payment Status:</strong> ${getPaymentBadge(reg.payment_status)}
                </div>
                <div class="col-md-6">
                    <strong>Base Fee:</strong> ${reg.base_fee ? (reg.fee_currency === 'USD' ? `$${reg.base_fee}` : `Rs.${reg.base_fee}`) : 'N/A'}
                </div>
                <div class="col-md-6">
                    <strong>Payment Invoice ID:</strong> ${reg.payment_invoice_id || 'N/A'}
                </div>
                <div class="col-md-6">
                    <strong>Payment Provider:</strong> ${reg.payment_provider || 'N/A'}
                </div>
                <div class="col-md-6">
                    <strong>Payment Completed At:</strong> ${reg.payment_paid_at ? new Date(reg.payment_paid_at).toLocaleString() : 'N/A'}
                </div>
                <div class="col-md-6">
                    <strong>Add-ons:</strong>
                    Food/Acc ${reg.addon_food_accommodation_fee ? (reg.fee_currency === 'USD' ? `$${reg.addon_food_accommodation_fee}` : `Rs.${reg.addon_food_accommodation_fee}`) : '0'},
                    Safari ${reg.addon_safari_fee ? (reg.fee_currency === 'USD' ? `$${reg.addon_safari_fee}` : `Rs.${reg.addon_safari_fee}`) : '0'}
                </div>
                <div class="col-md-6">
                    <strong>Safari Route:</strong> ${reg.safari_route || 'N/A'}
                </div>
            </div>
        `;
        
        $('#detailContent').html(html);
        $('#detailStatus').val(reg.status);
        $('#detailNotes').val(reg.admin_notes || '');
        
        $('#detailModal').modal('show');
        
    } catch (error) {
        console.error('Failed to load details:', error);
        alert('Failed to load registration details');
    }
}

async function saveDetails() {
    const status = $('#detailStatus').val();
    const notes = $('#detailNotes').val();
    
    try {
        const response = await fetch(`${API_BASE}/registrations/${encodeURIComponent(currentRegistrationId)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ status, admin_notes: notes })
        });
        
        if (response.ok) {
            const data = await response.json();
            
            let message = 'Registration updated successfully';
            if (data.id_card_auto_generated) {
                message += '\n\n✅ ID Card has been automatically generated!';
            }
            
            alert(message);
            $('#detailModal').modal('hide');
            loadRegistrations();
        } else {
            alert('Failed to update registration');
        }
    } catch (error) {
        console.error('Failed to save details:', error);
        alert('Failed to save changes');
    }
}

async function deleteRegistration(registrationId, participantName) {
    if (!confirm(`⚠️ WARNING: Are you sure you want to permanently delete the registration for "${participantName}"?\n\nThis action cannot be undone!`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/registrations/${encodeURIComponent(registrationId)}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert('Registration deleted successfully');
            loadRegistrations();
            loadDashboard(); // Refresh stats
        } else {
            alert('Failed to delete registration: ' + data.error);
        }
    } catch (error) {
        console.error('Failed to delete registration:', error);
        alert('Failed to delete registration');
    }
}

async function copyUniqueId(uniqueId) {
    try {
        await navigator.clipboard.writeText(uniqueId);
        alert(`Unique ID "${uniqueId}" copied to clipboard!`);
    } catch (error) {
        console.error('Failed to copy:', error);
        // Fallback
        const textarea = document.createElement('textarea');
        textarea.value = uniqueId;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        alert(`Unique ID "${uniqueId}" copied!`);
    }
}

async function generateIDCardFromDetail(registrationId) {
    if (!confirm('Generate ID card for this participant?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/id-card/generate/${encodeURIComponent(registrationId)}`, {
            method: 'POST',
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert(`ID Card generated successfully!\nUnique ID: ${data.unique_id}\n\nDownloading...`);
            // Use the smart view endpoint that will regenerate if needed
            window.open(`${API_BASE}/id-card/view/${encodeURIComponent(data.unique_id)}`, '_blank');
            // Refresh the modal to show updated status
            viewDetails(registrationId);
        } else {
            if (data.code === 'ALREADY_GENERATED') {
                alert('ID card already generated for this participant. Please approve regeneration first.');
            } else {
                alert('Failed to generate ID card: ' + data.error);
            }
        }
    } catch (error) {
        console.error('Failed to generate ID card:', error);
        alert('Failed to generate ID card');
    }
}

async function approveRegeneration(registrationId) {
    const reason = prompt('Enter reason for regenerating ID card:', 'Lost/damaged card');
    
    if (!reason) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/id-card/approve-regenerate/${encodeURIComponent(registrationId)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ reason })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert('Regeneration approved! You can now generate the ID card again.');
            // Refresh the modal to show updated status
            viewDetails(registrationId);
        } else {
            alert('Failed to approve regeneration: ' + data.error);
        }
    } catch (error) {
        console.error('Failed to approve regeneration:', error);
        alert('Failed to approve regeneration');
    }
}

// ========== EMAIL ==========

let selectedRecipients = [];

async function loadRecipientsList() {
    try {
        let url = `${API_BASE}/registrations?limit=1000`;
        if (currentEventId) url += `&event_id=${currentEventId}`;
        
        const response = await fetch(url, {
            credentials: 'include'
        });
        
        const payload = await response.json();
        const registrations = extractList(payload, 'registrations');
        
        if (response.ok && registrations.length) {
            const html = registrations.map(reg => `
                <div class="form-check mb-2">
                    <input class="form-check-input recipient-checkbox" type="checkbox" 
                           value="${reg.id}" id="recipient-${reg.id}">
                    <label class="form-check-label" for="recipient-${reg.id}" style="font-size: 14px;">
                        <strong>${reg.name}</strong> (${reg.email})
                        <br>
                        <small class="text-muted">${reg.institution} | ${reg.country} | 
                        <span class="badge bg-${reg.status === 'approved' ? 'success' : 'warning'}">${reg.status}</span>
                        </small>
                    </label>
                </div>
            `).join('');
            
            $('#recipientsList').html(html || '<p class="text-muted text-center">No registrations found</p>');
            
            // Add change handler for checkboxes
            $('.recipient-checkbox').on('change', updateSelectedCount);
            updateSelectedCount();
        } else {
            $('#recipientsList').html('<p class="text-danger text-center">Failed to load registrations</p>');
        }
    } catch (error) {
        console.error('Failed to load recipients:', error);
        $('#recipientsList').html('<p class="text-danger text-center">Error loading registrations</p>');
    }
}

function updateSelectedCount() {
    selectedRecipients = $('.recipient-checkbox:checked').map(function() {
        return $(this).val(); // Keep as string (email address)
    }).get();
    $('#selectedCount').text(selectedRecipients.length);
}

function toggleCustomSelection() {
    const recipients = $('#emailRecipients').val();
    if (recipients === 'custom') {
        $('#customSelectionList').removeClass('hidden');
    } else {
        $('#customSelectionList').addClass('hidden');
        selectedRecipients = [];
    }
}

async function sendEmail() {
    const recipients = $('#emailRecipients').val();
    const subject = $('#emailSubject').val();
    const message = $('#emailMessage').val();
    const attachIDCard = $('#attachIDCard').is(':checked');
    
    if (!subject || !message) {
        alert('Please fill in subject and message');
        return;
    }
    
    // Check if custom selection with no recipients selected
    if (recipients === 'custom' && selectedRecipients.length === 0) {
        alert('Please select at least one recipient');
        return;
    }
    
    try {
        const body = {
            subject,
            message,
            attach_id_card: attachIDCard
        };
        
        if (recipients === 'custom') {
            body.registration_ids = selectedRecipients;
        } else if (recipients === 'all') {
            body.registration_ids = 'all';
        } else {
            body.filter = { status: recipients };
        }
        
        const response = await fetch(`${API_BASE}/email/send`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(body)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            let message = `Email sending completed!\n\nSent: ${data.sent}\nFailed: ${data.failed}\nTotal: ${data.total}`;
            
            if (attachIDCard) {
                message += '\n\nID cards were attached to all emails.';
            }
            
            if (data.failed_details && data.failed_details.length > 0) {
                message += '\n\nFailed emails:\n' + data.failed_details.slice(0, 5).join('\n');
                if (data.failed_details.length > 5) {
                    message += `\n... and ${data.failed_details.length - 5} more`;
                }
            }
            
            alert(message);
            $('#emailForm')[0].reset();
            $('#customSelectionList').addClass('hidden');
            selectedRecipients = [];
        } else {
            alert('Failed to send email: ' + data.error);
        }
    } catch (error) {
        console.error('Failed to send email:', error);
        alert('Failed to send email');
    }
}

// ========== EXPORT ==========

function exportData(dataType, format) {
    /**
     * Export data in various formats
     * @param {string} dataType - 'registrations', 'venues', or 'volunteers'
     * @param {string} format - 'csv', 'excel', or 'pdf'
     */
    let url = `${API_BASE}/export/${dataType}?format=${format}`;
    if (currentEventId) {
        url += `&event_id=${currentEventId}`;
    }
    
    // Show loading indicator
    const btn = event.target;
    const originalHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Generating...';
    
    // Trigger download
    window.location.href = url;
    
    // Reset button after a delay
    setTimeout(() => {
        btn.disabled = false;
        btn.innerHTML = originalHTML;
    }, 2000);
}

function exportIDCards(exportType, format) {
    /**
     * Export ID cards, badge lists, or QR codes
     * @param {string} exportType - 'bulk', 'badge-list', or 'qr-codes'
     * @param {string} format - 'csv' or 'excel' (not used for bulk)
     */
    let url = '';
    
    if (exportType === 'bulk') {
        // Bulk ID cards as ZIP
        url = `${API_BASE}/export/id-cards-bulk`;
    } else if (exportType === 'badge-list') {
        // Badge printing list
        url = `${API_BASE}/export/badge-list?format=${format}`;
    } else if (exportType === 'qr-codes') {
        // QR code list
        url = `${API_BASE}/export/qr-codes?format=${format}`;
    }
    
    if (currentEventId) {
        url += url.includes('?') ? '&' : '?';
        url += `event_id=${currentEventId}`;
    }
    
    // Show loading indicator
    const btn = event.target;
    const originalHTML = btn.innerHTML;
    btn.disabled = true;
    
    if (exportType === 'bulk') {
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Generating ID Cards...';
    } else {
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Generating...';
    }
    
    // Trigger download
    window.location.href = url;
    
    // Reset button after a delay (longer for bulk generation)
    const resetDelay = exportType === 'bulk' ? 5000 : 2000;
    setTimeout(() => {
        btn.disabled = false;
        btn.innerHTML = originalHTML;
    }, resetDelay);
}

// ========== VENUE MANAGEMENT ==========

let venuesTable = null;
let currentVenueId = null;

async function loadVenues() {
    try {
        let url = `${API_BASE}/venues`;
        if (currentEventId) url += `?event_id=${currentEventId}`;
        
        const response = await fetch(url, {
            credentials: 'include'
        });
        
        if (response.status === 401) {
            showLogin();
            return;
        }

        const payload = await response.json();
        const venues = extractList(payload, 'venues');
        
        if (response.ok) {
            displayVenues(venues);
            updateVenueFilter(venues);
        }
    } catch (error) {
        console.error('Failed to load venues:', error);
    }
}

function displayVenues(venues) {
    if (venuesTable) {
        venuesTable.destroy();
    }
    
    const tbody = $('#venuesTable tbody');
    tbody.empty();
    
    venues.forEach(venue => {
        const statusBadge = venue.is_active 
            ? '<span class="badge bg-success">Active</span>' 
            : '<span class="badge bg-danger">Inactive</span>';
        
        // Format access limit display
        const accessLimit = venue.access_limit || 'unlimited';
        let accessLimitBadge;
        if (accessLimit === 'unlimited') {
            accessLimitBadge = '<span class="badge bg-secondary">Unlimited</span>';
        } else if (accessLimit === 'once') {
            accessLimitBadge = '<span class="badge bg-warning">Once Only</span>';
        } else {
            accessLimitBadge = `<span class="badge bg-primary">${accessLimit}x</span>`;
        }
        
        tbody.append(`
            <tr>
                <td>${venue.name}</td>
                <td><span class="badge bg-info">${venue.venue_type}</span></td>
                <td>${venue.location || '-'}</td>
                <td>${venue.capacity || '-'}</td>
                <td>${accessLimitBadge}</td>
                <td>${statusBadge}</td>
                <td>${venue.created_by || '-'}</td>
                <td>
                    <button class="btn btn-sm btn-primary me-1" onclick="editVenue('${venue.id}')" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-info me-1" onclick="viewVenueStats('${venue.id}')" title="View Stats">
                        <i class="fas fa-chart-bar"></i>
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deleteVenue('${venue.id}', '${venue.name}')" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `);
    });
    
    venuesTable = $('#venuesTable').DataTable({
        pageLength: 15,
        order: [[0, 'asc']]
    });
}

async function editVenue(venueId) {
    try {
        const response = await fetch(`${API_BASE}/venues/${venueId}`, {
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (response.ok && data.venue) {
            const venue = data.venue;
            
            $('#venueModalTitle').text('Edit Venue');
            $('#venueId').val(venue.id);
            $('#venueName').val(venue.name);
            $('#venueType').val(venue.venue_type);
            $('#venueLocation').val(venue.location);
            $('#venueCapacity').val(venue.capacity);
            $('#venueDescription').val(venue.description);
            $('#venueAccessLimit').val(venue.access_limit || 'unlimited');
            $('#venueActive').prop('checked', venue.is_active);
            
            $('#venueModal').modal('show');
        }
    } catch (error) {
        console.error('Failed to load venue:', error);
        alert('Failed to load venue details');
    }
}

async function saveVenue() {
    const venueId = $('#venueId').val();
    const name = $('#venueName').val();
    const type = $('#venueType').val();
    const location = $('#venueLocation').val();
    const capacity = $('#venueCapacity').val();
    const description = $('#venueDescription').val();
    const accessLimit = $('#venueAccessLimit').val();
    const isActive = $('#venueActive').is(':checked');
    
    if (!name || !type) {
        alert('Please fill in required fields');
        return;
    }
    
    const data = {
        name,
        venue_type: type,
        location,
        capacity: capacity ? parseInt(capacity) : null,
        description,
        access_limit: accessLimit,
        is_active: isActive
    };
    
    try {
        const url = venueId ? `${API_BASE}/venues/${venueId}` : `${API_BASE}/venues`;
        const method = venueId ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert(venueId ? 'Venue updated successfully' : 'Venue created successfully');
            $('#venueModal').modal('hide');
            loadVenues();
        } else {
            alert('Failed to save venue: ' + result.error);
        }
    } catch (error) {
        console.error('Failed to save venue:', error);
        alert('Failed to save venue');
    }
}

async function deleteVenue(venueId, venueName) {
    if (!confirm(`Are you sure you want to delete venue "${venueName}"?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/venues/${venueId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert('Venue deleted successfully');
            loadVenues();
        } else {
            alert('Failed to delete venue: ' + data.error);
        }
    } catch (error) {
        console.error('Failed to delete venue:', error);
        alert('Failed to delete venue');
    }
}

async function viewVenueStats(venueId) {
    try {
        const response = await fetch(`${API_BASE}/venues/${venueId}/stats`, {
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (response.ok && data.stats) {
            const stats = data.stats;
            
            const modal = $('<div class="modal fade" tabindex="-1">').html(`
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Venue Access Statistics</h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row mb-4">
                                <div class="col-md-4">
                                    <div class="text-center">
                                        <h3 class="text-success">${stats.total_check_ins}</h3>
                                        <p class="text-muted">Total Check-ins</p>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <div class="text-center">
                                        <h3 class="text-danger">${stats.total_denied}</h3>
                                        <p class="text-muted">Access Denied</p>
                                    </div>
                                </div>
                                <div class="col-md-4">
                                    <div class="text-center">
                                        <h3 class="text-primary">${stats.unique_participants}</h3>
                                        <p class="text-muted">Unique Participants</p>
                                    </div>
                                </div>
                            </div>
                            
                            <h6>Recent Access Log (Last 20)</h6>
                            <div style="max-height: 300px; overflow-y: auto;">
                                <table class="table table-sm">
                                    <thead>
                                        <tr>
                                            <th>Time</th>
                                            <th>Participant</th>
                                            <th>Action</th>
                                            <th>Volunteer</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${stats.recent_logs.map(log => `
                                            <tr>
                                                <td>${new Date(log.timestamp).toLocaleString()}</td>
                                                <td>${log.participant_name}</td>
                                                <td><span class="badge bg-${log.action_type === 'check-in' ? 'success' : 'danger'}">${log.action_type}</span></td>
                                                <td>${log.scanned_by}</td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            `);
            
            modal.modal('show');
            modal.on('hidden.bs.modal', function() {
                modal.remove();
            });
        }
    } catch (error) {
        console.error('Failed to load venue stats:', error);
        alert('Failed to load venue statistics');
    }
}

function updateVenueFilter(venues) {
    const select = $('#filterVenue');
    select.empty();
    select.append('<option value="">All Venues</option>');
    
    venues.forEach(venue => {
        select.append(`<option value="${venue.id}">${venue.name}</option>`);
    });
}

// ========== ACCESS LOGS ==========

let accessLogsTable = null;

async function loadAccessLogs() {
    const venueId = $('#filterVenue').val();
    const actionType = $('#filterActionType').val();
    const limit = $('#filterLimit').val() || 100;
    
    try {
        let url = `${API_BASE}/access-logs?limit=${limit}`;
        if (currentEventId) url += `&event_id=${currentEventId}`;
        if (venueId) url += `&venue_id=${venueId}`;
        if (actionType) url += `&action_type=${actionType}`;
        
        const response = await fetch(url, {
            credentials: 'include'
        });
        
        if (response.status === 401) {
            showLogin();
            return;
        }

        const payload = await response.json();
        const logs = extractList(payload, 'logs');
        
        if (response.ok) {
            displayAccessLogs(logs);
            updateAccessStats(logs);
        }
    } catch (error) {
        console.error('Failed to load access logs:', error);
    }
}

function displayAccessLogs(logs) {
    if (accessLogsTable) {
        accessLogsTable.destroy();
    }
    
    const tbody = $('#accessLogsTable tbody');
    tbody.empty();
    
    logs.forEach(log => {
        const actionBadge = log.action_type === 'check-in' 
            ? '<span class="badge bg-success">Check-in</span>' 
            : '<span class="badge bg-danger">Denied</span>';
        
        const timestamp = new Date(log.timestamp).toLocaleString();
        
        tbody.append(`
            <tr>
                <td>${timestamp}</td>
                <td>${log.participant_name}</td>
                <td><small>${log.registration_email}</small></td>
                <td>${log.venue_name}</td>
                <td>${actionBadge}</td>
                <td>${log.scanned_by}</td>
                <td><small>${log.notes || '-'}</small></td>
            </tr>
        `);
    });
    
    accessLogsTable = $('#accessLogsTable').DataTable({
        pageLength: 25,
        order: [[0, 'desc']]
    });
}

function updateAccessStats(logs) {
    const checkIns = logs.filter(log => log.action_type === 'check-in').length;
    const denied = logs.filter(log => log.action_type === 'denied').length;
    const uniqueEmails = new Set(logs.filter(log => log.action_type === 'check-in').map(log => log.registration_email));
    
    $('#totalCheckIns').text(checkIns);
    $('#totalDenied').text(denied);
    $('#uniqueParticipants').text(uniqueEmails.size);
}

// ========== VOLUNTEER MANAGEMENT ==========

let volunteersTable = null;
let currentVolunteerUsername = null;
let allVenuesForSelection = [];

async function loadVolunteers() {
    try {
        let url = `${API_BASE}/volunteers`;
        if (currentEventId) url += `?event_id=${currentEventId}`;
        
        const response = await fetch(url, {
            credentials: 'include'
        });
        
        if (response.status === 401) {
            showLogin();
            return;
        }

        const payload = await response.json();
        const volunteers = extractList(payload, 'volunteers');
        
        if (response.ok) {
            displayVolunteers(volunteers);
        }
    } catch (error) {
        console.error('Failed to load volunteers:', error);
    }
}

function displayVolunteers(volunteers) {
    if (volunteersTable) {
        volunteersTable.destroy();
    }
    
    const tbody = $('#volunteersTable tbody');
    tbody.empty();
    
    volunteers.forEach(volunteer => {
        const statusBadge = volunteer.is_active 
            ? '<span class="badge bg-success">Active</span>' 
            : '<span class="badge bg-danger">Inactive</span>';
        
        const lastLogin = volunteer.last_login 
            ? new Date(volunteer.last_login).toLocaleString() 
            : 'Never';
        
        const assignedVenues = volunteer.assigned_venues && volunteer.assigned_venues.length > 0
            ? `<span class="badge bg-info">${volunteer.assigned_venues.length} venues</span>`
            : '<span class="text-muted">All venues</span>';
        
        tbody.append(`
            <tr>
                <td><strong>${volunteer.username}</strong></td>
                <td>${volunteer.name}</td>
                <td>${volunteer.email || '-'}</td>
                <td>${volunteer.phone || '-'}</td>
                <td>${assignedVenues}</td>
                <td>${statusBadge}</td>
                <td><small>${lastLogin}</small></td>
                <td>
                    <button class="btn btn-sm btn-primary me-1" onclick="editVolunteer('${volunteer.username}')" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deleteVolunteer('${volunteer.username}', '${volunteer.name.replace(/'/g, "\\'"  )}')" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `);
    });
    
    volunteersTable = $('#volunteersTable').DataTable({
        pageLength: 15,
        order: [[0, 'asc']]
    });
}

async function loadVenuesForSelection() {
    try {
        const response = await fetch(`${API_BASE}/venues`, {
            credentials: 'include'
        });
        
        if (response.status === 401) {
            showLogin();
            return;
        }

        const payload = await response.json();
        const venues = extractList(payload, 'venues');
        
        if (response.ok) {
            allVenuesForSelection = venues;
            displayVenueCheckboxes(venues, []);
        }
    } catch (error) {
        console.error('Failed to load venues for selection:', error);
    }
}

function displayVenueCheckboxes(venues, selectedVenues = []) {
    const container = $('#venueCheckboxes');
    
    if (venues.length === 0) {
        container.html('<p class="text-muted">No venues available</p>');
        return;
    }
    
    let html = '';
    venues.forEach(venue => {
        const isChecked = selectedVenues.includes(venue.id) ? 'checked' : '';
        html += `
            <div class="form-check mb-2">
                <input class="form-check-input venue-checkbox" type="checkbox" 
                       value="${venue.id}" id="venue-${venue.id}" ${isChecked}>
                <label class="form-check-label" for="venue-${venue.id}">
                    <strong>${venue.name}</strong>
                    <small class="text-muted">(${venue.venue_type})</small>
                </label>
            </div>
        `;
    });
    
    container.html(html);
}

async function editVolunteer(username) {
    try {
        const response = await fetch(`${API_BASE}/volunteers/${username}`, {
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (response.ok && data.volunteer) {
            const volunteer = data.volunteer;
            
            $('#volunteerModalTitle').text('Edit Volunteer');
            $('#volunteerIdOriginal').val(volunteer.username);
            $('#volunteerUsername').val(volunteer.username).prop('disabled', true);
            $('#volunteerName').val(volunteer.name);
            $('#volunteerEmail').val(volunteer.email);
            $('#volunteerPhone').val(volunteer.phone);
            $('#volunteerPassword').val('').prop('required', false);
            $('#passwordHint').text('(leave empty to keep current password)');
            $('#volunteerActive').prop('checked', volunteer.is_active);
            
            // Load venues and select assigned ones
            await loadVenuesForSelection();
            displayVenueCheckboxes(allVenuesForSelection, volunteer.assigned_venues || []);
            
            $('#volunteerModal').modal('show');
        }
    } catch (error) {
        console.error('Failed to load volunteer:', error);
        alert('Failed to load volunteer details');
    }
}

async function saveVolunteer() {
    const originalUsername = $('#volunteerIdOriginal').val();
    const username = $('#volunteerUsername').val().trim();
    const name = $('#volunteerName').val().trim();
    const email = $('#volunteerEmail').val().trim();
    const phone = $('#volunteerPhone').val().trim();
    const password = $('#volunteerPassword').val();
    const isActive = $('#volunteerActive').is(':checked');
    
    // Get selected venues
    const assignedVenues = $('.venue-checkbox:checked').map(function() {
        return $(this).val();
    }).get();
    
    if (!username || !name) {
        alert('Please fill in required fields (Username and Name)');
        return;
    }
    
    if (!originalUsername && !password) {
        alert('Password is required for new volunteers');
        return;
    }
    
    if (password && password.length < 6) {
        alert('Password must be at least 6 characters');
        return;
    }
    
    const data = {
        username,
        name,
        email,
        phone,
        assigned_venues: assignedVenues,
        is_active: isActive
    };
    
    if (password) {
        data.password = password;
    }
    
    try {
        const url = originalUsername ? `${API_BASE}/volunteers/${originalUsername}` : `${API_BASE}/volunteers`;
        const method = originalUsername ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert(originalUsername ? 'Volunteer updated successfully' : 'Volunteer created successfully');
            $('#volunteerModal').modal('hide');
            loadVolunteers();
        } else {
            alert('Failed to save volunteer: ' + result.error);
        }
    } catch (error) {
        console.error('Failed to save volunteer:', error);
        alert('Failed to save volunteer');
    }
}

async function deleteVolunteer(username, name) {
    if (!confirm(`Are you sure you want to delete volunteer "${name}" (${username})?\n\nThis will revoke their access to the QR scanner.`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/volunteers/${username}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert('Volunteer deleted successfully');
            loadVolunteers();
        } else {
            alert('Failed to delete volunteer: ' + data.error);
        }
    } catch (error) {
        console.error('Failed to delete volunteer:', error);
        alert('Failed to delete volunteer');
    }
}

// ========== EVENT HANDLERS ==========

$(document).ready(function() {
    initSidebarState();

    // Check if already logged in
    checkAuth();
    
    // Login form
    $('#loginForm').on('submit', async function(e) {
        e.preventDefault();
        
        const username = $('#username').val();
        const password = $('#password').val();
        
        const result = await login(username, password);
        
        if (result.success) {
            $('#loginError').addClass('hidden');
        } else {
            $('#loginError').text(getErrorMessage(result.error, 'Login failed')).removeClass('hidden');
        }
    });
    
    // Logout
    $('#logoutBtn').on('click', function(e) {
        e.preventDefault();
        logout();
    });

    $('#sidebarToggleBtn').on('click', function() {
        toggleSidebar();
    });
    
    // Navigation
    $('.sidebar-menu a[data-page]').on('click', function(e) {
        e.preventDefault();
        const page = $(this).data('page');
        switchPage(page);
    });
    
    // Filters
    $('#filterStatus, #filterCountry').on('change', loadRegistrations);
    $('#searchBox').on('input', debounce(loadRegistrations, 500));
    $('#refreshBtn').on('click', loadRegistrations);
    
    // Advanced filters - auto-apply on change
    $('#filterDateFrom, #filterDateTo, #filterUpdatedFrom, #filterUpdatedTo').on('change', applyAdvancedFilters);
    $('#filterStatusMulti, #filterCountryMulti').on('change', applyAdvancedFilters);
    $('#filterGdtaMember, #filterRegSource, #filterCheckedIn, #filterPaymentStatus').on('change', applyAdvancedFilters);
    
    // Save details
    $('#saveDetailsBtn').on('click', saveDetails);
    
    // Email form
    $('#emailForm').on('submit', function(e) {
        e.preventDefault();
        sendEmail();
    });
    
    // Email recipient selection
    $('#emailRecipients').on('change', toggleCustomSelection);
    $('#loadRecipientsBtn').on('click', loadRecipientsList);
    
    // Export - now using inline onclick handlers in HTML
    // Removed: $('#exportBtn').on('click', exportData);
    
    // Venue management
    $('#addVenueBtn').on('click', function() {
        $('#venueModalTitle').text('Add New Venue');
        $('#venueForm')[0].reset();
        $('#venueId').val('');
        $('#venueActive').prop('checked', true);
    });
    
    $('#saveVenueBtn').on('click', saveVenue);
    
    // Access logs
    $('#refreshLogsBtn').on('click', loadAccessLogs);
    $('#filterVenue, #filterActionType, #filterLimit').on('change', loadAccessLogs);
    
    // Volunteer management
    $('#addVolunteerBtn').on('click', function() {
        $('#volunteerModalTitle').text('Add New Volunteer');
        $('#volunteerForm')[0].reset();
        $('#volunteerIdOriginal').val('');
        $('#volunteerUsername').prop('disabled', false);
        $('#volunteerPassword').prop('required', true);
        $('#passwordHint').text('(required for new volunteers)');
        $('#volunteerActive').prop('checked', true);
        loadVenuesForSelection();
        $('#volunteerModal').modal('show');
    });
    
    $('#saveVolunteerBtn').on('click', saveVolunteer);
    
    // Password visibility toggle
    $('#togglePasswordBtn').on('click', function() {
        const passwordField = $('#volunteerPassword');
        const icon = $(this).find('i');
        
        if (passwordField.attr('type') === 'password') {
            passwordField.attr('type', 'text');
            icon.removeClass('fa-eye').addClass('fa-eye-slash');
        } else {
            passwordField.attr('type', 'password');
            icon.removeClass('fa-eye-slash').addClass('fa-eye');
        }
    });
    
    // ========== MULTI-EVENT SYSTEM ==========
    
    // Event selector change
    $('#eventSelector').on('change', function() {
        currentEventId = $(this).val() || null;
        console.log('Event selector changed to:', currentEventId, 'Event name:', $(this).find('option:selected').text());
        // Reload current page data with new event filter
        if (currentPage === 'registrations') {
            loadRegistrations();
        } else if (currentPage === 'venues') {
            loadVenues();
        } else if (currentPage === 'volunteers') {
            loadVolunteers();
        } else if (currentPage === 'access-logs') {
            loadAccessLogs();
        } else if (currentPage === 'dashboard') {
            loadDashboard();
        }
    });
    
    // Event management
    $('#addEventBtn').on('click', showCreateEventModal);
    $('#saveEventBtn').on('click', saveEvent);
    
    // Admin management
    $('#addAdminBtn').on('click', showCreateAdminModal);
    $('#saveAdminBtn').on('click', saveAdmin);
    
    // Admin role change - no-op (single role)
});

// ========== ID CARD GENERATION ==========

async function generateIDCard(registrationId) {
    if (!confirm('Generate ID card for this delegate?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/id-card/generate/${encodeURIComponent(registrationId)}`, {
            method: 'POST',
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            alert(`✅ ID Card generated successfully!\n\nUnique ID: ${data.unique_id}\n\nOpening card in new tab...`);
            
            // Use the smart view endpoint that will regenerate if needed
            window.open(`${API_BASE}/id-card/view/${encodeURIComponent(data.unique_id)}`, '_blank');
            
            // Reload the registrations table to update the button
            loadRegistrations();
            
        } else {
            if (data.code === 'ALREADY_GENERATED') {
                alert('ID card already generated. Please use the View button to download it, or approve regeneration in the details modal.');
            } else {
                alert('Failed to generate ID card: ' + (data.error || 'Unknown error'));
            }
        }
    } catch (error) {
        console.error('Failed to generate ID card:', error);
        alert('Failed to generate ID card');
    }
}

// Debounce helper
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// ========== EMAIL TEMPLATES ==========

let templatesTable = null;
let currentTemplateId = null;

async function loadEmailTemplates() {
    try {
        let url = `${API_BASE}/email-templates`;
        if (currentEventId) url += `?event_id=${currentEventId}`;
        
        const response = await fetch(url, { credentials: 'include' });
        if (response.status === 401) {
            showLogin();
            return;
        }
        const payload = await response.json();
        const templates = extractList(payload, 'templates');
        
        if (templatesTable) {
            templatesTable.destroy();
        }
        
        const tbody = $('#templatesTable tbody');
        tbody.empty();
        
        templates.forEach(template => {
            const statusBadge = template.is_active 
                ? '<span class="badge bg-success">Active</span>' 
                : '<span class="badge bg-secondary">Inactive</span>';
            
            const categoryBadge = {
                'welcome': 'info',
                'approval': 'success',
                'rejection': 'danger',
                'reminder': 'warning',
                'custom': 'secondary'
            }[template.category] || 'secondary';
            
            const variablesDisplay = template.variables && template.variables.length 
                ? template.variables.length + ' vars' 
                : 'None';
            
            tbody.append(`
                <tr>
                    <td><strong>${template.name}</strong></td>
                    <td><span class="badge bg-${categoryBadge}">${template.category}</span></td>
                    <td><small>${template.subject}</small></td>
                    <td>${variablesDisplay}</td>
                    <td>${statusBadge}</td>
                    <td>${new Date(template.created_at).toLocaleDateString()}</td>
                    <td>
                        <button class="btn btn-sm btn-info me-1" onclick="previewTemplate('${template.id}')" title="Preview">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-primary me-1" onclick="editTemplate('${template.id}')" title="Edit">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="deleteTemplate('${template.id}', '${template.name.replace(/'/g, "\\'")}')" title="Delete">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `);
        });
        
        templatesTable = $('#templatesTable').DataTable({
            pageLength: 25,
            order: [[5, 'desc']] // Sort by created date
        });
        
    } catch (error) {
        console.error('Failed to load templates:', error);
    }
}

function showCreateTemplateModal() {
    currentTemplateId = null;
    document.getElementById('templateModalTitle').innerHTML = '<i class="fas fa-file-alt me-2"></i>Create Email Template';
    document.getElementById('templateId').value = '';
    document.getElementById('templateName').value = '';
    document.getElementById('templateCategory').value = 'custom';
    document.getElementById('templateSubject').value = '';
    document.getElementById('templateBody').value = '';
    document.getElementById('templateActive').checked = true;
    
    const modal = new bootstrap.Modal(document.getElementById('templateModal'));
    modal.show();
}

async function editTemplate(templateId) {
    try {
        const response = await fetch(`${API_BASE}/email-templates/${templateId}`, {
            credentials: 'include'
        });
        if (response.status === 401) {
            showLogin();
            return;
        }
        const payload = await response.json();
        const data = unwrapPayload(payload) || {};
        const template = data.template || data;
        
        currentTemplateId = template.id;
        document.getElementById('templateModalTitle').innerHTML = '<i class="fas fa-file-alt me-2"></i>Edit Email Template';
        document.getElementById('templateId').value = template.id;
        document.getElementById('templateName').value =template.name;
        document.getElementById('templateCategory').value = template.category;
        document.getElementById('templateSubject').value = template.subject;
        document.getElementById('templateBody').value = template.body;
        document.getElementById('templateActive').checked = template.is_active;
        
        const modal = new bootstrap.Modal(document.getElementById('templateModal'));
        modal.show();
        
    } catch (error) {
        alert('Failed to load template');
    }
}

async function saveTemplate() {
    const templateId = document.getElementById('templateId').value;
    const name = document.getElementById('templateName').value.trim();
    const category = document.getElementById('templateCategory').value;
    const subject = document.getElementById('templateSubject').value.trim();
    const body = document.getElementById('templateBody').value.trim();
    const is_active = document.getElementById('templateActive').checked;
    
    if (!name || !subject || !body) {
        alert('Please fill in all required fields');
        return;
    }
    
    // Extract variables from subject and body
    const variables = new Set();
    const regex = /\{\{(\w+)\}\}/g;
    let match;
    
    while ((match = regex.exec(subject + body)) !== null) {
        variables.add(match[1]);
    }
    
    const templateData = {
        name: name,
        category: category,
        subject: subject,
        body: body,
        is_active: is_active,
        variables: Array.from(variables)
    };
    
    if (currentEventId) {
        templateData.event_id = currentEventId;
    }
    
    try {
        let response;
        if (templateId) {
            // Update existing template
            response = await fetch(`${API_BASE}/email-templates/${templateId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(templateData)
            });
        } else {
            // Create new template
            response = await fetch(`${API_BASE}/email-templates`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(templateData)
            });
        }
        
        const payload = await response.json();
        const data = unwrapPayload(payload);
        
        if (response.ok) {
            alert(data?.message || 'Template saved successfully');
            const modal = bootstrap.Modal.getInstance(document.getElementById('templateModal'));
            modal.hide();
            loadEmailTemplates();
        } else {
            alert(getErrorMessage(payload, 'Failed to save template'));
        }
        
    } catch (error) {
        alert('Failed to save template');
    }
}

async function deleteTemplate(templateId, templateName) {
    if (!confirm(`Delete template "${templateName}"?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/email-templates/${templateId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        const payload = await response.json();
        const data = unwrapPayload(payload);
        
        if (response.ok) {
            alert(data?.message || 'Template deleted');
            loadEmailTemplates();
        } else {
            alert(getErrorMessage(payload, 'Failed to delete template'));
        }
        
    } catch (error) {
        alert('Failed to delete template');
    }
}

async function previewTemplate(templateId) {
    try {
        const response = await fetch(`${API_BASE}/email-templates/${templateId}/preview`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({})
        });
        
        const payload = await response.json();
        const data = unwrapPayload(payload);
        
        if (response.ok) {
            const preview = data.preview || data;
            alert(`Preview:\n\nSubject: ${preview.subject}\n\nBody:\n${preview.body}`);
        } else {
            alert(getErrorMessage(payload, 'Failed to preview template'));
        }
        
    } catch (error) {
        alert('Failed to preview template');
    }
}

function copyVariable(varName) {
    const text = `{{${varName}}}`;
    navigator.clipboard.writeText(text).then(() => {
        // Show temporary feedback
        const originalText = event.target.textContent;
        event.target.textContent = 'Copied!';
        setTimeout(() => {
            event.target.textContent = originalText;
        }, 1000);
    });
}

function toggleEmailMode(mode) {
    if (mode === 'template') {
        document.getElementById('templateSelection').style.display = 'block';
        document.getElementById('bulkEmailForm').style.display = 'none';
        loadTemplatesForEmail();
    } else {
        document.getElementById('templateSelection').style.display = 'none';
        document.getElementById('bulkEmailForm').style.display = 'block';
    }
}

async function loadTemplatesForEmail() {
    try {
        const response = await fetch(`${API_BASE}/email-templates?is_active=true`, {
            credentials: 'include'
        });
        if (response.status === 401) {
            showLogin();
            return;
        }
        const payload = await response.json();
        const templates = extractList(payload, 'templates');
        
        const select = document.getElementById('templateSelect');
        select.innerHTML = '<option value="">-- Choose a template --</option>';
        
        templates.forEach(template => {
            const option = document.createElement('option');
            option.value = template.id;
            option.textContent = `${template.name} (${template.category})`;
            select.appendChild(option);
        });
        
    } catch (error) {
        console.error('Failed to load templates:', error);
    }
}

async function updateTemplatePreview() {
    const templateId = document.getElementById('templateSelect').value;
    const previewDiv = document.getElementById('templatePreview');
    
    if (!templateId) {
        previewDiv.classList.add('d-none');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/email-templates/${templateId}/preview`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({})
        });
        
        const payload = await response.json();
        const data = unwrapPayload(payload);
        
        if (response.ok) {
            const preview = data.preview || data;
            document.getElementById('previewSubject').textContent = preview.subject;
            document.getElementById('previewBody').textContent = preview.body;
            previewDiv.classList.remove('d-none');
        }
        
    } catch (error) {
        console.error('Failed to preview template:', error);
    }
}

// ========== MULTI-EVENT MANAGEMENT ==========

async function loadEventSelector() {
    try {
        const response = await fetch('/api/events/', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const payload = await response.json();
            allEvents = extractList(payload, 'events');
            
            console.log('Loaded events:', allEvents.length, allEvents);
            
            const selector = $('#eventSelector');
            selector.empty();
            selector.append('<option value="">All Events</option>');
            
            allEvents.forEach(event => {
                selector.append(`<option value="${event.id}">${event.name} (${event.year})</option>`);
            });
            
            // Set to first event if available
            if (allEvents.length > 0 && !currentEventId) {
                currentEventId = allEvents[0].id;
                selector.val(currentEventId);
                console.log('Set currentEventId to first event:', currentEventId, allEvents[0].name);
            }
        }
    } catch (error) {
        console.error('Failed to load events:', error);
    }
}

async function loadEvents() {
    try {
        const response = await fetch('/api/events/', {
            credentials: 'include'
        });
        
        if (response.ok) {
            const payload = await response.json();
            allEvents = extractList(payload, 'events');
            
            const tbody = $('#eventsTableBody');
            tbody.empty();
            
            if (allEvents.length === 0) {
                tbody.append(`
                    <tr>
                        <td colspan="7" class="text-center text-muted py-4">
                            <i class="bi bi-calendar-event"></i> No events created yet
                        </td>
                    </tr>
                `);
                return;
            }
            
            allEvents.forEach(event => {
                const statusBadge = event.is_active 
                    ? '<span class="badge bg-success">Active</span>' 
                    : '<span class="badge bg-secondary">Inactive</span>';
                
                const dates = event.start_date && event.end_date 
                    ? `${event.start_date} to ${event.end_date}` 
                    : 'Not set';
                
                tbody.append(`
                    <tr>
                        <td><strong>${event.name}</strong></td>
                        <td>${event.year}</td>
                        <td>${dates}</td>
                        <td>${event.location || '-'}</td>
                        <td>${statusBadge}</td>
                        <td>${new Date(event.created_at).toLocaleDateString()}</td>
                        <td>
                            <button class="btn btn-sm btn-accent" onclick="editEvent('${event.id}')">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button class="btn btn-sm btn-danger" onclick="deleteEvent('${event.id}')">
                                <i class="bi bi-trash"></i>
                            </button>
                        </td>
                    </tr>
                `);
            });
        }
    } catch (error) {
        console.error('Failed to load events:', error);
        alert('Failed to load events');
    }
}

function showCreateEventModal() {
    $('#eventModalTitle').text('Create New Event');
    $('#eventForm')[0].reset();
    $('#eventId').val('');
    $('#eventActive').prop('checked', true);
    
    const modal = new bootstrap.Modal($('#eventModal')[0]);
    modal.show();
}

function editEvent(eventId) {
    const event = allEvents.find(e => e.id === eventId);
    if (!event) return;
    
    $('#eventModalTitle').text('Edit Event');
    $('#eventId').val(event.id);
    $('#eventName').val(event.name);
    $('#eventYear').val(event.year);
    $('#eventStartDate').val(event.start_date || '');
    $('#eventEndDate').val(event.end_date || '');
    $('#eventLocation').val(event.location || '');
    $('#eventDescription').val(event.description || '');
    $('#eventActive').prop('checked', event.is_active);
    
    const modal = new bootstrap.Modal($('#eventModal')[0]);
    modal.show();
}

async function saveEvent() {
    const eventId = $('#eventId').val();
    const eventData = {
        name: $('#eventName').val().trim(),
        year: parseInt($('#eventYear').val()),
        start_date: $('#eventStartDate').val() || null,
        end_date: $('#eventEndDate').val() || null,
        location: $('#eventLocation').val().trim() || null,
        description: $('#eventDescription').val().trim() || null,
        is_active: $('#eventActive').is(':checked')
    };
    
    if (!eventData.name || !eventData.year) {
        alert('Please fill in required fields');
        return;
    }
    
    try {
        const url = eventId 
            ? `/api/events/${eventId}` 
            : '/api/events/';
        
        const method = eventId ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(eventData)
        });
        
        const payload = await response.json();
        const data = unwrapPayload(payload);
        
        if (response.ok) {
            alert(eventId ? 'Event updated successfully!' : 'Event created successfully!');
            bootstrap.Modal.getInstance($('#eventModal')[0]).hide();
            loadEvents();
            loadEventSelector(); // Update selector
        } else {
            alert(getErrorMessage(payload, 'Failed to save event'));
        }
    } catch (error) {
        console.error('Failed to save event:', error);
        alert('Failed to save event');
    }
}

async function deleteEvent(eventId) {
    const event = allEvents.find(e => e.id === eventId);
    if (!event) return;
    
    if (!confirm(`Are you sure you want to delete "${event.name}"?\n\nThis will NOT delete associated data (registrations, venues, etc) - they will remain linked to this event ID.`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/events/${eventId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        const payload = await response.json();
        const data = unwrapPayload(payload);
        
        if (response.ok) {
            alert('Event deleted successfully!');
            loadEvents();
            loadEventSelector();
        } else {
            alert(getErrorMessage(payload, 'Failed to delete event'));
        }
    } catch (error) {
        console.error('Failed to delete event:', error);
        alert('Failed to delete event');
    }
}

// ========== ADMIN MANAGEMENT ==========

let allAdmins = [];

async function loadAdmins() {
    try {
        const response = await fetch(`${API_BASE}/admins`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const payload = await response.json();
            allAdmins = extractList(payload, 'admins');
            
            const tbody = $('#adminsTableBody');
            tbody.empty();
            
            if (allAdmins.length === 0) {
                tbody.append(`
                    <tr>
                        <td colspan="6" class="text-center text-muted py-4">
                            <i class="bi bi-people"></i> No admins created yet
                        </td>
                    </tr>
                `);
                return;
            }
            
            allAdmins.forEach(admin => {
                const statusBadge = admin.is_active 
                    ? '<span class="badge bg-success">Active</span>' 
                    : '<span class="badge bg-secondary">Inactive</span>';
        
                const roleBadge = '<span class="badge bg-primary">Admin</span>';
        
                const eventsAssigned = admin.assigned_events && admin.assigned_events.length > 0
                    ? `${admin.assigned_events.length} event(s)`
                    : '<span class="text-muted">None</span>';
                
                tbody.append(`
                    <tr>
                        <td><strong>${admin.username}</strong></td>
                        <td>${admin.name}</td>
                        <td>${admin.email || '-'}</td>
                        <td>${roleBadge}</td>
                        <td>${eventsAssigned}</td>
                        <td>${statusBadge}</td>
                        <td>
                            <button class="btn btn-sm btn-accent" onclick="editAdmin('${admin.username}')">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button class="btn btn-sm btn-danger" onclick="deleteAdmin('${admin.username}')">
                                <i class="bi bi-trash"></i>
                            </button>
                        </td>
                    </tr>
                `);
            });
        }
    } catch (error) {
        console.error('Failed to load admins:', error);
        alert('Failed to load admins');
    }
}

async function showCreateAdminModal() {
    $('#adminModalTitle').text('Create New Admin');
    $('#adminForm')[0].reset();
    $('#adminIdOriginal').val('');
    $('#adminUsername').prop('disabled', false);
    $('#adminPassword').prop('required', true);
    $('#adminPasswordHint').text('(min 8 characters) *');
    $('#adminActive').prop('checked', true);
    $('#adminRole').val('admin').prop('disabled', true);
    
    // Load event checkboxes
    await loadEventCheckboxes([]);
    
    const modal = new bootstrap.Modal($('#adminModal')[0]);
    modal.show();
}

async function editAdmin(username) {
    const admin = allAdmins.find(a => a.username === username);
    if (!admin) return;
    
    $('#adminModalTitle').text('Edit Admin');
    $('#adminIdOriginal').val(admin.username);
    $('#adminUsername').val(admin.username);
    $('#adminUsername').prop('disabled', true); // Cannot change username
    $('#adminFullName').val(admin.name);
    $('#adminEmail').val(admin.email || '');
    $('#adminRole').val('admin').prop('disabled', true);
    $('#adminPassword').val('');
    $('#adminPassword').prop('required', false);
    $('#adminPasswordHint').text('(leave blank to keep current)');
    $('#adminActive').prop('checked', admin.is_active);
    
    // Load event checkboxes with current assignments
    await loadEventCheckboxes(admin.assigned_events || []);
    
    const modal = new bootstrap.Modal($('#adminModal')[0]);
    modal.show();
}

async function loadEventCheckboxes(selectedEventIds) {
    const container = $('#eventCheckboxes');
    container.empty();
    
    if (allEvents.length === 0) {
        // Try to load events if not already loaded
        await loadEventSelector();
    }
    
    if (allEvents.length === 0) {
        container.html('<p class="text-muted">No events available. Create an event first.</p>');
        return;
    }
    
    allEvents.forEach(event => {
        const checked = selectedEventIds.includes(event.id) ? 'checked' : '';
        container.append(`
            <div class="form-check">
                <input class="form-check-input event-checkbox" type="checkbox" value="${event.id}" id="event_${event.id}" ${checked}>
                <label class="form-check-label" for="event_${event.id}">
                    ${event.name} (${event.year})
                </label>
            </div>
        `);
    });
    
    // Show/hide event assignment based on role
    updateEventAssignmentVisibility();
}

function updateEventAssignmentVisibility() {
    $('#assignedEventsContainer').show();
}

function constrainAdminRoleOptions() {
    $('#adminRole').val('admin').prop('disabled', true);
}

async function saveAdmin() {
    const originalUsername = $('#adminIdOriginal').val();
    const isEdit = !!originalUsername;
    
    const adminData = {
        username: $('#adminUsername').val().trim(),
        name: $('#adminFullName').val().trim(),
        email: $('#adminEmail').val().trim() || null,
        role: 'admin',
        is_active: $('#adminActive').is(':checked')
    };
    
    // Add password if provided
    const password = $('#adminPassword').val();
    if (password) {
        adminData.password = password;
    } else if (!isEdit) {
        alert('Password is required for new admins');
        return;
    }
    
    // Add assigned events for regular admins
    adminData.assigned_events = [];
    $('.event-checkbox:checked').each(function() {
        adminData.assigned_events.push($(this).val());
    });
    
    if (adminData.assigned_events.length === 0) {
        alert('Please assign at least one event to this admin');
        return;
    }
    
    if (!adminData.username || !adminData.name) {
        alert('Please fill in required fields');
        return;
    }
    
    try {
        const url = isEdit 
            ? `${API_BASE}/admins/${originalUsername}` 
            : `${API_BASE}/admins`;
        
        const method = isEdit ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(adminData)
        });
        
        const payload = await response.json();
        const data = unwrapPayload(payload);
        
        if (response.ok) {
            alert(isEdit ? 'Admin updated successfully!' : 'Admin created successfully!');
            bootstrap.Modal.getInstance($('#adminModal')[0]).hide();
            loadAdmins();
        } else {
            alert(getErrorMessage(payload, 'Failed to save admin'));
        }
    } catch (error) {
        console.error('Failed to save admin:', error);
        alert('Failed to save admin');
    }
}

async function deleteAdmin(username) {
    const admin = allAdmins.find(a => a.username === username);
    if (!admin) return;
    
    if (!confirm(`Are you sure you want to delete admin "${admin.name}" (${username})?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/admins/${username}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        const payload = await response.json();
        const data = unwrapPayload(payload);
        
        if (response.ok) {
            alert('Admin deleted successfully!');
            loadAdmins();
        } else {
            alert(getErrorMessage(payload, 'Failed to delete admin'));
        }
    } catch (error) {
        console.error('Failed to delete admin:', error);
        alert('Failed to delete admin');
    }
}

// Make viewDetails available globally
window.viewDetails = viewDetails;
window.generateIDCard = generateIDCard;
window.deleteRegistration = deleteRegistration;
window.copyUniqueId = copyUniqueId;
window.generateIDCardFromDetail = generateIDCardFromDetail;
window.approveRegeneration = approveRegeneration;
window.editVenue = editVenue;
window.deleteVenue = deleteVenue;
window.viewVenueStats = viewVenueStats;
window.editVolunteer = editVolunteer;
window.deleteVolunteer = deleteVolunteer;

// Multi-event functions
window.showCreateEventModal = showCreateEventModal;
window.editEvent = editEvent;
window.deleteEvent = deleteEvent;
window.saveEvent = saveEvent;
window.showCreateAdminModal = showCreateAdminModal;
window.editAdmin = editAdmin;
window.deleteAdmin = deleteAdmin;
window.saveAdmin = saveAdmin;

// Email templates
window.showCreateTemplateModal = showCreateTemplateModal;
window.editTemplate = editTemplate;
window.saveTemplate = saveTemplate;
window.deleteTemplate = deleteTemplate;
window.previewTemplate = previewTemplate;
window.copyVariable = copyVariable;
window.toggleEmailMode = toggleEmailMode;
window.updateTemplatePreview = updateTemplatePreview;

// Advanced filters
window.toggleAdvancedFilters = toggleAdvancedFilters;
window.applyAdvancedFilters = applyAdvancedFilters;
window.resetAdvancedFilters = resetAdvancedFilters;
window.clearAllFilters = clearAllFilters;

// ========== ADVANCED FILTERS FUNCTIONS ==========

function toggleAdvancedFilters() {
    const panel = $('#advancedFiltersPanel');
    const icon = $('#advancedFiltersIcon');
    
    if (panel.is(':visible')) {
        panel.slideUp();
        icon.removeClass('fa-chevron-up').addClass('fa-chevron-down');
    } else {
        panel.slideDown();
        icon.removeClass('fa-chevron-down').addClass('fa-chevron-up');
    }
}

function applyAdvancedFilters() {
    // Blur the basic filters to prioritize advanced filters
    $('#filterStatus').val('');
    $('#filterCountry').val('');
    
    loadRegistrations();
}

function resetAdvancedFilters() {
    $('#filterDateFrom').val('');
    $('#filterDateTo').val('');
    $('#filterUpdatedFrom').val('');
    $('#filterUpdatedTo').val('');
    $('#filterStatusMulti').val([]);
    $('#filterCountryMulti').val([]);
    $('#filterGdtaMember').val('');
    $('#filterRegSource').val('');
    $('#filterCheckedIn').val('');
    $('#filterPaymentStatus').val('');
    
    loadRegistrations();
}

function clearAllFilters() {
    // Clear basic filters
    $('#filterStatus').val('');
    $('#filterCountry').val('');
    $('#searchBox').val('');
    
    // Clear advanced filters
    resetAdvancedFilters();
}

function updateCountryMultiSelectFilter(registrations) {
    const countries = new Set();
    registrations.forEach(reg => {
        if (reg.country) countries.add(reg.country);
    });
    
    const select = $('#filterCountryMulti');
    const currentValues = select.val() || [];
    
    select.empty();
    Array.from(countries).sort().forEach(country => {
        const option = $('<option></option>').val(country).text(country);
        if (currentValues.includes(country)) {
            option.prop('selected', true);
        }
        select.append(option);
    });
}

function updateActiveFiltersCount() {
    let count = 0;
    const countSpan = $('#activeFiltersCount');
    const clearBtn = $('#clearFiltersBtn');
    
    // Count active filters
    if ($('#filterStatus').val()) count++;
    if ($('#filterCountry').val()) count++;
    if ($('#searchBox').val()) count++;
    if ($('#filterDateFrom').val()) count++;
    if ($('#filterDateTo').val()) count++;
    if ($('#filterUpdatedFrom').val()) count++;
    if ($('#filterUpdatedTo').val()) count++;
    if ($('#filterStatusMulti').val()?.length > 0) count++;
    if ($('#filterCountryMulti').val()?.length > 0) count++;
    if ($('#filterGdtaMember').val()) count++;
    if ($('#filterRegSource').val()) count++;
    if ($('#filterCheckedIn').val()) count++;
    if ($('#filterPaymentStatus').val()) count++;
    
    if (count > 0) {
        countSpan.text(`${count} filter${count > 1 ? 's' : ''} active`);
        countSpan.show();
        clearBtn.show();
    } else {
        countSpan.hide();
        clearBtn.hide();
    }
}
