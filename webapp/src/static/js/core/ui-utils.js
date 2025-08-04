/**
 * UI Utilities Module - Common UI functions and status management
 */

/**
 * Show loading indicator for a specific section
 */
function showSectionLoading(sectionId, message = 'Loading...') {
    const section = document.getElementById(sectionId);
    if (section) {
        section.innerHTML = `
            <div class="d-flex justify-content-center align-items-center p-4">
                <div class="spinner-border text-primary me-3" role="status">
                    <span class="sr-only">Loading...</span>
                </div>
                <span>${message}</span>
            </div>
        `;
    }
}

/**
 * Show error message in a section
 */
function showError(message, sectionId = null) {
    const errorHtml = `
        <div class="alert alert-danger" role="alert">
            <i class="fas fa-exclamation-triangle me-2"></i>
            ${message}
        </div>
    `;
    
    if (sectionId) {
        const section = document.getElementById(sectionId);
        if (section) {
            section.innerHTML = errorHtml;
        }
    } else {
        console.error(message);
    }
}

/**
 * Update application status indicator
 */
function updateAppStatus(status, message) {
    const statusIndicator = document.getElementById('app-status');
    const statusMessage = document.getElementById('status-message');
    
    if (statusIndicator && statusMessage) {
        // Remove existing status classes
        statusIndicator.className = statusIndicator.className.replace(/\b(text-success|text-warning|text-danger)\b/g, '');
        
        // Add appropriate status class
        switch (status) {
            case 'success':
                statusIndicator.classList.add('text-success');
                break;
            case 'warning':
                statusIndicator.classList.add('text-warning');
                break;
            case 'error':
                statusIndicator.classList.add('text-danger');
                break;
            default:
                break;
        }
        
        statusMessage.textContent = message;
    }
}

/**
 * Show toast notification
 */
function showToast(message, type = 'success') {
    // Create toast element if it doesn't exist
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '1050';
        document.body.appendChild(toastContainer);
    }
    
    const toastId = 'toast-' + Date.now();
    const toast = document.createElement('div');
    toast.id = toastId;
    toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    // Initialize and show the toast
    const bsToast = new bootstrap.Toast(toast, {
        autohide: true,
        delay: 3000
    });
    bsToast.show();
    
    // Remove toast element after it's hidden
    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}

/**
 * Create loading spinner HTML
 */
function createLoadingSpinner(message = 'Loading...') {
    return `
        <div class="d-flex justify-content-center align-items-center p-4">
            <div class="spinner-border text-primary me-3" role="status">
                <span class="sr-only">Loading...</span>
            </div>
            <span>${message}</span>
        </div>
    `;
}

/**
 * Create empty state HTML
 */
function createEmptyState(message = 'No data available', icon = 'fas fa-info-circle') {
    return `
        <div class="text-center p-4 text-muted">
            <i class="${icon} fa-2x mb-3"></i>
            <p>${message}</p>
        </div>
    `;
}