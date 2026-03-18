// ========== GLOBAL VARIABLES ==========

const API_BASE = '/api/admin';
let currentUser = null;
let currentEventId = null;
let allEvents = [];
let allAdmins = [];
let eventsTable = null;
let adminsTable = null;
let eventAdminsTable = null;

// ========== AUTHENTICATION ==========

async function login(username, password) {
    try {
        const response = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Check if user is super admin
            if (data.user.role !== 'super_admin') {
                return { success: false, error: 'Access denied. Super admin privileges required.' };
            }
            
            currentUser = data.user;
            updateUserInfo();
            showDashboard();
            return { success: true };
        } else {
            return { success: false, error: data.error };
        }
    } catch (error) {
        console.error('Login error:', error);
        return { success: false, error: 'Connection failed' };
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
    sessionStorage.clear();
    window.location.reload();
}

async function checkAuth() {
    try {
        const response = await fetch(`${API_BASE}/me`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            
            // Verify super admin role
            if (data.user.role !== 'super_admin') {
                // Redirect regular admin to their dashboard
                window.location.href = '/static/admin-dashboard.html';
                return;
            }
            
            currentUser = data.user;
            updateUserInfo();
            showDashboard();
        } else {
            showLogin();
        }
    } catch (error) {
        showLogin();
    }
}

function updateUserInfo() {
    if (currentUser) {
        $('#adminName').text(currentUser.name);
        $('#adminAvatar').text(currentUser.name.charAt(0).toUpperCase());
    }
}

function showLogin() {
    $('#loginPage').show();
    $('#dashboardContainer').hide();
}

function showDashboard() {
    $('#loginPage').hide();
    $('#dashboardContainer').show();
    loadEvents();
}

// ========== NAVIGATION ==========

function switchPage(pageName) {
    $('.page-view').removeClass('active');
    $(`#${pageName}View`).addClass('active');
    
    $('.sidebar-nav a').removeClass('active');
    $(`.sidebar-nav a[data-page="${pageName}"]`).addClass('active');
    
    // Update page title
    const titles = {
        'events': 'Event Management',
        'admins': 'Admin Users',
        'eventDetails': 'Event Details'
    };
    $('#pageTitle').text(titles[pageName] || '');
    
    // Load data based on page
    if (pageName === 'events') {
        loadEvents();
    } else if (pageName === 'admins') {
        loadAdmins();
    }
}

function backToEvents() {
    currentEventId = null;
    switchPage('events');
}

// ========== EVENTS MANAGEMENT ==========

async function loadEvents() {
    try {
        $('#eventsLoadingState').show();
        $('#eventsEmptyState').hide();
        $('#eventsList').empty();
        
        const response = await fetch('/api/superadmin/events', {
            credentials: 'include'
        });
        
        const data = await response.json();
        allEvents = data.events || [];
        
        $('#eventsLoadingState').hide();
        
        if (allEvents.length === 0) {
            $('#eventsEmptyState').show();
        } else {
            displayEvents(allEvents);
        }
        
    } catch (error) {
        console.error('Failed to load events:', error);
        $('#eventsLoadingState').hide();
        $('#eventsEmptyState').show();
    }
}

function displayEvents(events) {
    const container = $('#eventsList');
    container.empty();
    
    events.forEach(event => {
        const startDate = event.start_date ? new Date(event.start_date).toLocaleDateString() : 'TBD';
        const endDate = event.end_date ? new Date(event.end_date).toLocaleDateString() : 'TBD';
        
        const statusBadge = event.is_active 
            ? '<span class="badge bg-success">Active</span>' 
            : '<span class="badge bg-secondary">Inactive</span>';
        
        const card = $(`
            <div class="col-md-6">
                <div class="event-card" onclick="viewEventDetails('${event.id}')">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h4>${event.name}</h4>
                        ${statusBadge}
                    </div>
                    <p class="text-muted mb-2">
                        <i class="fas fa-calendar me-2"></i>${startDate} - ${endDate}
                    </p>
                    ${event.location ? `<p class="text-muted mb-2"><i class="fas fa-map-marker-alt me-2"></i>${event.location}</p>` : ''}
                    ${event.description ? `<p class="mb-0">${event.description}</p>` : ''}
                    <hr>
                    <div class="d-flex justify-content-between text-muted small">
                        <span><i class="fas fa-calendar me-1"></i>${event.year}</span>
                        <span><i class="fas fa-hashtag me-1"></i>${event.event_id || 'No ID'}</span>
                    </div>
                </div>
            </div>
        `);
        
        container.append(card);
    });
}

async function viewEventDetails(eventId) {
    currentEventId = eventId;
    const event = allEvents.find(e => e.id === eventId);
    
    if (!event) return;
    
    $('#eventDetailsTitle').text(event.name);
    
    // Display event info
    const startDate = new Date(event.start_date).toLocaleDateString();
    const endDate = new Date(event.end_date).toLocaleDateString();
    
    $('#eventInfoDetails').html(`
        <div class="row">
            <div class="col-md-6 mb-3">
                <strong>Event ID:</strong><br>
                <code>${event.event_id || 'Not set'}</code>
            </div>
            <div class="col-md-6 mb-3">
                <strong>Name:</strong><br>
                ${event.name}
            </div>
            <div class="col-md-6 mb-3">
                <strong>Year:</strong><br>
                ${event.year}
            </div>
            <div class="col-md-6 mb-3">
                <strong>Start Date:</strong><br>
                ${startDate}
            </div>
            <div class="col-md-6 mb-3">
                <strong>End Date:</strong><br>
                ${endDate}
            </div>
            ${event.location ? `
            <div class="col-md-6 mb-3">
                <strong>Location:</strong><br>
                ${event.location}
            </div>
            ` : ''}
            <div class="col-md-6 mb-3">
                <strong>Status:</strong><br>
                <span class="badge ${event.is_active ? 'bg-success' : 'bg-secondary'}">${event.is_active ? 'Active' : 'Inactive'}</span>
            </div>
            ${event.description ? `
            <div class="col-12 mb-3">
                <strong>Description:</strong><br>
                ${event.description}
            </div>
            ` : ''}
        </div>
    `);
    
    // Load statistics (use event_id if available, otherwise use doc id)
    const eventIdentifier = event.event_id || event.id;
    await loadEventStats(eventIdentifier);
    
    // Load assigned admins
    await loadEventAdmins(eventIdentifier);
    
    switchPage('eventDetails');
}

async function loadEventStats(eventId) {
    try {
        // Get event object (search by both id and event_id)
        const event = allEvents.find(e => e.id === eventId || e.event_id === eventId);
        if (!event) {
            console.error('Event not found:', eventId);
            return;
        }
        
        // Use event.event_id for filtering registrations (this matches the registrations' event_id field)
        const filterEventId = event.event_id || event.id;
        console.log('Loading stats for event:', event.name, 'filterEventId:', filterEventId);
        
        const regResponse = await fetch(`${API_BASE}/registrations?event_id=${filterEventId}`, {
            credentials: 'include'
        });
        
        if (!regResponse.ok) {
            const errorData = await regResponse.json();
            console.error('Failed to fetch registrations:', regResponse.status, errorData);
            
            if (regResponse.status === 401) {
                // Session expired, redirect to login
                alert('Your session has expired. Please login again.');
                showLogin();
                return;
            }
            
            $('#statRegistrations').text('0');
            $('#statApproved').text('0');
            $('#statPending').text('0');
            return;
        }
        
        const regData = await regResponse.json();
        console.log('Registration response:', regData);
        const registrations = regData.registrations || [];
        console.log('Total registrations found:', registrations.length);
        
        $('#statRegistrations').text(registrations.length);
        $('#statApproved').text(registrations.filter(r => r.status === 'approved').length);
        $('#statPending').text(registrations.filter(r => r.status === 'pending').length);
        
        // Count admins assigned to this event (using event.id as admins are assigned by Firebase doc ID)
        const adminsAssigned = allAdmins.filter(admin => 
            admin.role === 'admin' && admin.assigned_events && admin.assigned_events.includes(event.id)
        );
        $('#statAdmins').text(adminsAssigned.length);
        
    } catch (error) {
        console.error('Failed to load event stats:', error);
    }
}

async function loadEventAdmins(eventId) {
    try {
        // Get event object (search by both id and event_id)
        const event = allEvents.find(e => e.id === eventId || e.event_id === eventId);
        if (!event) return;
        
        // Get all admins
        if (allAdmins.length === 0) {
            const response = await fetch('/api/superadmin/admins', {
                credentials: 'include'
            });
            const data = await response.json();
            allAdmins = data.admins || [];
        }
        
        // Filter admins assigned to this event (using event.id)
        const eventAdmins = allAdmins.filter(admin => 
            admin.role === 'admin' && admin.assigned_events && admin.assigned_events.includes(event.id)
        );
        
        // Display in table
        if (eventAdminsTable) {
            eventAdminsTable.destroy();
        }
        
        const tbody = $('#eventAdminsTable tbody');
        tbody.empty();
        
        if (eventAdmins.length === 0) {
            tbody.append(`
                <tr>
                    <td colspan="6" class="text-center text-muted">No admins assigned to this event</td>
                </tr>
            `);
        } else {
            eventAdmins.forEach(admin => {
                const lastLogin = admin.last_login ? new Date(admin.last_login).toLocaleString() : 'Never';
                const statusBadge = admin.is_active 
                    ? '<span class="badge badge-active">Active</span>' 
                    : '<span class="badge badge-inactive">Inactive</span>';
                
                tbody.append(`
                    <tr>
                        <td>${admin.name}</td>
                        <td>${admin.username}</td>
                        <td>${admin.email}</td>
                        <td>${statusBadge}</td>
                        <td>${lastLogin}</td>
                        <td>
                            <button class="btn btn-sm btn-danger" onclick="unassignAdminFromEvent('${admin.id}', '${eventId}')">
                                <i class="fas fa-times me-1"></i>Unassign
                            </button>
                        </td>
                    </tr>
                `);
            });
        }
        
        if (eventAdmins.length > 0) {
            eventAdminsTable = $('#eventAdminsTable').DataTable({
                order: [[0, 'asc']],
                pageLength: 10
            });
        }
        
    } catch (error) {
        console.error('Failed to load event admins:', error);
    }
}

function showCreateEventModal() {
    $('#eventModalTitle').text('Create Event');
    $('#eventForm')[0].reset();
    $('#eventId').val('');
    $('#eventEventId').prop('disabled', false);
    new bootstrap.Modal($('#eventModal')).show();
}

function editCurrentEvent() {
    const event = allEvents.find(e => e.id === currentEventId);
    if (!event) return;
    
    $('#eventModalTitle').text('Edit Event');
    $('#eventId').val(event.id);
    $('#eventEventId').val(event.event_id || '');
    $('#eventName').val(event.name);
    $('#eventYear').val(event.year);
    $('#eventStartDate').val(event.start_date || '');
    $('#eventEndDate').val(event.end_date || '');
    $('#eventLocation').val(event.location || '');
    $('#eventDescription').val(event.description || '');
    $('#eventActive').prop('checked', event.is_active);
    
    new bootstrap.Modal($('#eventModal')).show();
}

async function saveEvent() {
    const eventId = $('#eventId').val();
    const eventData = {
        event_id: $('#eventEventId').val(),
        name: $('#eventName').val(),
        year: parseInt($('#eventYear').val()),
        start_date: $('#eventStartDate').val() || null,
        end_date: $('#eventEndDate').val() || null,
        location: $('#eventLocation').val() || null,
        description: $('#eventDescription').val() || null,
        is_active: $('#eventActive').is(':checked')
    };
    
    // Validation
    if (!eventData.event_id || !eventData.name || !eventData.year) {
        alert('Please fill in required fields (Event ID, name, and year)');
        return;
    }
    
    try {
        const url = eventId ? `/api/superadmin/events/${eventId}` : '/api/superadmin/events';
        const method = eventId ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(eventData)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            bootstrap.Modal.getInstance($('#eventModal')).hide();
            loadEvents();
            alert(eventId ? 'Event updated successfully!' : 'Event created successfully!');
        } else {
            alert('Error: ' + (data.error || 'Failed to save event'));
        }
    } catch (error) {
        console.error('Failed to save event:', error);
        alert('Failed to save event');
    }
}

async function deleteCurrentEvent() {
    if (!currentEventId) return;
    
    const event = allEvents.find(e => e.id === currentEventId);
    if (!event) return;
    
    if (!confirm(`Are you sure you want to delete "${event.name}"?\\n\\nThis will NOT delete registrations, but admins will lose access.`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/superadmin/events/${currentEventId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (response.ok) {
            alert('Event deleted successfully!');
            backToEvents();
        } else {
            const data = await response.json();
            alert('Error: ' + (data.error || 'Failed to delete event'));
        }
    } catch (error) {
        console.error('Failed to delete event:', error);
        alert('Failed to delete event');
    }
}

async function showAssignAdminModal() {
    try {
        // Load all admins if not already loaded
        if (allAdmins.length === 0) {
            const response = await fetch('/api/superadmin/admins', {
                credentials: 'include'
            });
            const data = await response.json();
            allAdmins = data.admins || [];
        }
        
        // Get current event
        const event = allEvents.find(e => e.id === currentEventId);
        if (!event) return;
        
        // Filter admins not assigned to this event (using event.id)
        const availableAdmins = allAdmins.filter(admin => 
            admin.role === 'admin' && (!admin.assigned_events || !admin.assigned_events.includes(event.id))
        );
        
        const select = $('#assignAdminSelect');
        select.empty();
        select.append('<option value="">Choose admin...</option>');
        
        availableAdmins.forEach(admin => {
            select.append(`<option value="${admin.id}">${admin.name} (${admin.username})</option>`);
        });
        
        new bootstrap.Modal($('#assignAdminModal')).show();
        
    } catch (error) {
        console.error('Failed to load admins:', error);
        alert('Failed to load admins');
    }
}

async function assignAdminToEvent() {
    const adminId = $('#assignAdminSelect').val();
    if (!adminId) {
        alert('Please select an admin');
        return;
    }
    
    const event = allEvents.find(e => e.id === currentEventId);
    if (!event) return;
    
    try {
        // Get admin details
        const admin = allAdmins.find(a => a.id === adminId);
        if (!admin) return;
        
        // Update admin's assigned events (using event.id)
        const assignedEvents = admin.assigned_events || [];
        if (!assignedEvents.includes(event.id)) {
            assignedEvents.push(event.id);
        }
        
        const response = await fetch(`/api/superadmin/admins/${adminId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                ...admin,
                assigned_events: assignedEvents
            })
        });
        
        if (response.ok) {
            bootstrap.Modal.getInstance($('#assignAdminModal')).hide();
            // Reload admins list
            allAdmins = [];
            await loadEventAdmins(event.id);
            await loadEventStats(event.id);
            alert('Admin assigned successfully!');
        } else {
            const data = await response.json();
            alert('Error: ' + (data.error || 'Failed to assign admin'));
        }
    } catch (error) {
        console.error('Failed to assign admin:', error);
        alert('Failed to assign admin');
    }
}

async function unassignAdminFromEvent(adminId, eventId) {
    if (!confirm('Are you sure you want to unassign this admin from this event?')) {
        return;
    }
    
    try {
        const admin = allAdmins.find(a => a.id === adminId);
        if (!admin) return;
        
        // Remove event from admin's assigned events
        const assignedEvents = (admin.assigned_events || []).filter(eid => eid !== eventId);
        
        const response = await fetch(`/api/superadmin/admins/${adminId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                ...admin,
                assigned_events: assignedEvents
            })
        });
        
        if (response.ok) {
            // Reload admins list
            allAdmins = [];
            await loadEventAdmins(eventId);
            await loadEventStats(eventId);
            alert('Admin unassigned successfully!');
        } else {
            const data = await response.json();
            alert('Error: ' + (data.error || 'Failed to unassign admin'));
        }
    } catch (error) {
        console.error('Failed to unassign admin:', error);
        alert('Failed to unassign admin');
    }
}

// ========== ADMINS MANAGEMENT ==========

async function loadAdmins() {
    try {
        const response = await fetch('/api/superadmin/admins', {
            credentials: 'include'
        });
        
        const data = await response.json();
        allAdmins = data.admins || [];
        
        displayAdmins(allAdmins);
        
    } catch (error) {
        console.error('Failed to load admins:', error);
    }
}

function displayAdmins(admins) {
    if (adminsTable) {
        adminsTable.destroy();
    }
    
    const tbody = $('#adminsTable tbody');
    tbody.empty();
    
    admins.forEach(admin => {
        const roleBadge = admin.role === 'super_admin'
            ? '<span class="badge badge-super-admin">Super Admin</span>'
            : '<span class="badge badge-admin">Admin</span>';
        
        const statusBadge = admin.is_active 
            ? '<span class="badge badge-active">Active</span>' 
            : '<span class="badge badge-inactive">Inactive</span>';
        
        const eventsList = admin.role === 'super_admin' 
            ? '<span class="text-muted">All Events</span>' 
            : (admin.assigned_events && admin.assigned_events.length > 0 
                ? admin.assigned_events.join(', ') 
                : '<span class="text-muted">None</span>');
        
        const lastLogin = admin.last_login ? new Date(admin.last_login).toLocaleString() : 'Never';
        
        const actions = admin.role === 'super_admin'
            ? '<span class="text-muted">Protected</span>'
            : `
                <button class="btn btn-sm btn-primary me-1" onclick="editAdmin('${admin.id}')">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-danger" onclick="deleteAdmin('${admin.id}', '${admin.name.replace(/'/g, "\\'")}')">
                    <i class="fas fa-trash"></i>
                </button>
            `;
        
        tbody.append(`
            <tr>
                <td>${admin.name}</td>
                <td>${admin.username}</td>
                <td>${admin.email}</td>
                <td>${roleBadge}</td>
                <td><small>${eventsList}</small></td>
                <td>${statusBadge}</td>
                <td><small>${lastLogin}</small></td>
                <td>${actions}</td>
            </tr>
        `);
    });
    
    adminsTable = $('#adminsTable').DataTable({
        order: [[0, 'asc']],
        pageLength: 25
    });
}

async function showCreateAdminModal() {
    $('#adminModalTitle').text('Create Admin');
    $('#adminForm')[0].reset();
    $('#adminId').val('');
    $('#adminUsername').prop('disabled', false);
    $('#adminPassword').prop('required', true);
    $('#passwordHelp').hide();
    
    // Load events for assignment
    await loadEventsForAdminForm();
    
    new bootstrap.Modal($('#adminModal')).show();
}

async function editAdmin(adminId) {
    const admin = allAdmins.find(a => a.id === adminId);
    if (!admin) return;
    
    $('#adminModalTitle').text('Edit Admin');
    $('#adminId').val(admin.id);
    $('#adminUsername').val(admin.username).prop('disabled', true);
    $('#adminNameField').val(admin.name);
    $('#adminEmail').val(admin.email);
    $('#adminPassword').val('').prop('required', false);
    $('#adminStatus').val(admin.is_active ? 'true' : 'false');
    $('#passwordHelp').show();
    
    // Load events and select assigned ones
    await loadEventsForAdminForm();
    $('#adminAssignedEvents').val(admin.assigned_events || []);
    
    new bootstrap.Modal($('#adminModal')).show();
}

async function loadEventsForAdminForm() {
    try {
        if (allEvents.length === 0) {
            const response = await fetch('/api/superadmin/events', {
                credentials: 'include'
            });
            const data = await response.json();
            allEvents = data.events || [];
        }
        
        const select = $('#adminAssignedEvents');
        select.empty();
        
        allEvents.forEach(event => {
            select.append(`<option value="${event.id}">${event.name} (${event.year})</option>`);
        });
        
    } catch (error) {
        console.error('Failed to load events:', error);
    }
}

async function saveAdmin() {
    const adminId = $('#adminId').val();
    const password = $('#adminPassword').val();
    
    // Validation
    if (!adminId && !password) {
        alert('Password is required for new admin');
        return;
    }
    
    const adminData = {
        username: $('#adminUsername').val(),
        name: $('#adminNameField').val(),
        email: $('#adminEmail').val(),
        role: 'admin',
        assigned_events: $('#adminAssignedEvents').val() || [],
        is_active: $('#adminStatus').val() === 'true'
    };
    
    if (password) {
        adminData.password = password;
    }
    
    try {
        const url = adminId ? `/api/superadmin/admins/${adminId}` : '/api/superadmin/admins';
        const method = adminId ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(adminData)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            bootstrap.Modal.getInstance($('#adminModal')).hide();
            loadAdmins();
            alert(adminId ? 'Admin updated successfully!' : 'Admin created successfully!');
        } else {
            alert('Error: ' + (data.error || 'Failed to save admin'));
        }
    } catch (error) {
        console.error('Failed to save admin:', error);
        alert('Failed to save admin');
    }
}

async function deleteAdmin(adminId, adminName) {
    if (!confirm(`Are you sure you want to delete admin "${adminName}"?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/superadmin/admins/${adminId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (response.ok) {
            loadAdmins();
            alert('Admin deleted successfully!');
        } else {
            const data = await response.json();
            alert('Error: ' + (data.error || 'Failed to delete admin'));
        }
    } catch (error) {
        console.error('Failed to delete admin:', error);
        alert('Failed to delete admin');
    }
}

// ========== INITIALIZATION ==========

$(document).ready(function() {
    // Login form
    $('#loginForm').on('submit', async function(e) {
        e.preventDefault();
        
        const username = $('#username').val();
        const password = $('#password').val();
        
        const result = await login(username, password);
        
        if (result.success) {
            $('#loginError').addClass('d-none');
        } else {
            $('#loginError').text(result.error).removeClass('d-none');
        }
    });
    
    // Navigation
    $('.sidebar-nav a').on('click', function(e) {
        e.preventDefault();
        const page = $(this).data('page');
        switchPage(page);
    });
    
    // Check authentication on load
    checkAuth();
});

// Export functions to window for onclick handlers
window.logout = logout;
window.viewEventDetails = viewEventDetails;
window.backToEvents = backToEvents;
window.showCreateEventModal = showCreateEventModal;
window.editCurrentEvent = editCurrentEvent;
window.saveEvent = saveEvent;
window.deleteCurrentEvent = deleteCurrentEvent;
window.showAssignAdminModal = showAssignAdminModal;
window.assignAdminToEvent = assignAdminToEvent;
window.unassignAdminFromEvent = unassignAdminFromEvent;
window.showCreateAdminModal = showCreateAdminModal;
window.editAdmin = editAdmin;
window.saveAdmin = saveAdmin;
window.deleteAdmin = deleteAdmin;
