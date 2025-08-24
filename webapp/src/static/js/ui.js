// UI utilities for SliceDroid
// Handles tooltips, toasts, sidebar, filter toggles and other UI interactions

// Handle filter toggle
function initializeFilterToggle() {
    const filtersContent = document.getElementById('filters-content');
    if (filtersContent) {
        filtersContent.addEventListener('hidden.bs.collapse', function () {
            const icon = document.getElementById('filter-toggle-icon');
            if (icon) icon.className = 'fas fa-chevron-down';
        });

        filtersContent.addEventListener('shown.bs.collapse', function () {
            const icon = document.getElementById('filter-toggle-icon');
            if (icon) icon.className = 'fas fa-chevron-up';
        });
    }
}

// Sidebar functionality
let sidebarCollapsed = false;

function toggleSidebar() {
    const collapsedView = document.querySelector('.collapsed-view');
    const fullView = document.querySelector('.full-view');
    const sidebar = document.querySelector('.filters-sidebar');
    const sidebarColumn = document.getElementById('sidebar-column');
    const mainContent = document.getElementById('main-content');

    if (sidebarCollapsed) {
        // Expanding: Change layout first, then show content
        sidebarColumn.className = 'col-md-3';
        mainContent.className = 'col-md-9 main-content';

        // Small delay to let layout settle, then show content
        setTimeout(() => {
            sidebar.classList.remove('collapsed');
            collapsedView.style.display = 'none';
            fullView.style.display = 'block';
        }, 50);

        sidebarCollapsed = false;
    } else {
        // Collapsing: Hide content first, then change layout
        collapsedView.style.display = 'block';
        fullView.style.display = 'none';
        sidebar.classList.add('collapsed');

        // Small delay to let content hide, then change layout
        setTimeout(() => {
            sidebarColumn.className = 'col-md-1';
            mainContent.className = 'col-md-11 main-content';
        }, 50);

        sidebarCollapsed = true;
    }
}

function initializeSidebarToggle() {
    const sidebarToggle = document.getElementById('sidebar-toggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', toggleSidebar);
    }
}

function initializeTimelineControls() {
    // Behavior Timeline zoom controls
    const behaviorZoomInBtn = document.getElementById('behavior-zoom-in');
    const behaviorZoomOutBtn = document.getElementById('behavior-zoom-out');
    const behaviorResetZoomBtn = document.getElementById('behavior-reset-zoom');
    
    if (behaviorZoomInBtn) {
        behaviorZoomInBtn.addEventListener('click', () => {
            if (typeof behaviorZoomIn === 'function') behaviorZoomIn();
        });
    }
    if (behaviorZoomOutBtn) {
        behaviorZoomOutBtn.addEventListener('click', () => {
            if (typeof behaviorZoomOut === 'function') behaviorZoomOut();
        });
    }
    if (behaviorResetZoomBtn) {
        behaviorResetZoomBtn.addEventListener('click', () => {
            if (typeof behaviorResetZoom === 'function') behaviorResetZoom();
        });
    }
}

// Toast notification system
function showToast(title, message, type = 'info') {
    // Create toast HTML
    const toastId = 'toast-' + Date.now();
    const bgClass = type === 'success' ? 'bg-success' : type === 'error' ? 'bg-danger' : 'bg-info';
    
    const toastHtml = `
        <div id="${toastId}" class="toast align-items-center text-white ${bgClass} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    <strong>${title}</strong><br>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    
    // Add to page if toast container doesn't exist
    if (!document.getElementById('toast-container')) {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }
    
    // Add toast to container
    const container = document.getElementById('toast-container');
    container.innerHTML += toastHtml;
    
    // Show toast
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: type === 'error' ? 5000 : 3000
    });
    toast.show();
    
    // Remove from DOM after hiding
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

// Initialize tooltips
function initializeTooltips() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Progress bar helper
function updateProgressBar(progress) {
    const progressBar = document.getElementById('progress-bar');
    const progressPercentage = document.getElementById('progress-percentage');

    if (progressBar) {
        progressBar.style.width = progress + '%';
    }
    if (progressPercentage) {
        progressPercentage.textContent = progress + '%';
    }
}

// Security tooltip utilities
function showSecurityTooltip(event, d) {
    // Create tooltip
    const tooltip = d3.select("body").append("div")
        .attr("class", "chart-tooltip")
        .style("position", "absolute")
        .style("background", "rgba(0,0,0,0.9)")
        .style("color", "white")
        .style("padding", "8px 12px")
        .style("border-radius", "4px")
        .style("font-size", "12px")
        .style("pointer-events", "none")
        .style("z-index", "1000")
        .style("opacity", 0);

    const time = new Date(d.timestamp * 1000).toLocaleString();
    tooltip.html(`<strong>${d.event_type}</strong><br>Time: ${time}<br>Severity: ${d.severity || 'low'}<br>Process: ${d.process || 'unknown'}`)
        .style("left", (event.pageX + 10) + "px")
        .style("top", (event.pageY - 10) + "px")
        .transition().duration(200).style("opacity", 1);
}

function hideSecurityTooltip() {
    d3.selectAll(".chart-tooltip").remove();
}

// Update app status indicator
function updateAppStatus(type, message) {
    const statusEl = $('#app-status');
    const iconMap = {
        'loading': 'fas fa-spinner fa-spin',
        'success': 'fas fa-check-circle', 
        'warning': 'fas fa-exclamation-triangle',
        'error': 'fas fa-times-circle'
    };
    const classMap = {
        'loading': 'status-loading',
        'success': 'status-ready',
        'warning': 'status-warning',
        'error': 'status-error'
    };
    
    statusEl.removeClass('status-ready status-loading status-warning status-error')
           .addClass(classMap[type] || 'status-ready');
    statusEl.html(`<i class="${iconMap[type] || 'fas fa-question'}"></i> <span>${message}</span>`);
}

// Initialize all UI functionality
function initializeUI() {
    initializeFilterToggle();
    initializeSidebarToggle();
    initializeTimelineControls();
    initializeTooltips();
}

// Make functions globally available
window.showToast = showToast;
window.updateProgressBar = updateProgressBar;
window.showSecurityTooltip = showSecurityTooltip;
window.hideSecurityTooltip = hideSecurityTooltip;
window.toggleSidebar = toggleSidebar;
window.updateAppStatus = updateAppStatus;
window.initializeUI = initializeUI;