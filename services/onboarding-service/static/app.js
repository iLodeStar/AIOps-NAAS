/* AIOps Onboarding Service JavaScript */

document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert.classList.contains('show')) {
                alert.classList.remove('show');
                setTimeout(() => alert.remove(), 150);
            }
        }, 5000);
    });
    
    // Form validation
    const forms = document.querySelectorAll('form[novalidate]');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
    
    // Confirmation dialogs
    const confirmButtons = document.querySelectorAll('[data-confirm]');
    confirmButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            const message = button.getAttribute('data-confirm');
            if (!confirm(message)) {
                event.preventDefault();
            }
        });
    });
    
    // Auto-refresh for status updates
    if (window.location.pathname.includes('/requests/')) {
        setInterval(() => {
            // Check if page is visible
            if (!document.hidden) {
                fetch(window.location.href, {
                    headers: {
                        'Accept': 'text/html'
                    }
                })
                .then(response => {
                    if (response.ok) {
                        // Update page if status changed
                        // Simple implementation: reload if response differs
                        // In production, you might want more sophisticated updates
                    }
                })
                .catch(error => {
                    console.log('Auto-refresh failed:', error);
                });
            }
        }, 30000); // Check every 30 seconds
    }
});

// Utility functions
function showLoading(element) {
    element.classList.add('loading');
    element.innerHTML += ' <span class="spinner-border spinner-border-sm" role="status"></span>';
}

function hideLoading(element) {
    element.classList.remove('loading');
    const spinner = element.querySelector('.spinner-border');
    if (spinner) {
        spinner.remove();
    }
}

function showNotification(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    const container = document.querySelector('.container');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (alertDiv.classList.contains('show')) {
                alertDiv.classList.remove('show');
                setTimeout(() => alertDiv.remove(), 150);
            }
        }, 5000);
    }
}

// API helpers
async function apiCall(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include'
    };
    
    const response = await fetch(url, { ...defaultOptions, ...options });
    
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(error.detail || 'Request failed');
    }
    
    return await response.json();
}

// Quick approval functions (if needed for AJAX)
async function quickApprove(requestId, role, decision, comments = '') {
    try {
        const response = await apiCall(`/api/requests/${requestId}/approve`, {
            method: 'POST',
            body: JSON.stringify({
                role: role,
                decision: decision,
                comments: comments
            })
        });
        
        showNotification(`Request ${decision} as ${role}`, decision === 'approved' ? 'success' : 'warning');
        
        // Reload page to show updated status
        setTimeout(() => window.location.reload(), 1000);
        
        return response;
    } catch (error) {
        showNotification(`Error: ${error.message}`, 'danger');
        throw error;
    }
}