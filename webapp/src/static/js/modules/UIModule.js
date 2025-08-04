/**
 * UIModule - Modern UI utilities and interactions
 * Migrated from legacy ui.js with improvements
 */
class UIModule {
    constructor() {
        this.sidebarCollapsed = false;
        this.initialized = false;
        this.toastContainer = null;
    }
    
    /**
     * Initialize the UI module
     */
    init() {
        if (this.initialized) return;
        
        try {
            // Check dependencies
            if (!this.checkDependencies()) {
                throw new Error('UIModule dependencies not satisfied');
            }
            
            this.setupFilterToggle();
            this.setupSidebar();
            this.setupToastContainer();
            this.setupTooltips();
            this.setupGlobalEventListeners();
            this.initialized = true;
            
            console.log('UIModule initialized successfully');
        } catch (error) {
            console.error('Failed to initialize UIModule:', error);
            this.initialized = false;
            throw error;
        }
    }
    
    /**
     * Check module dependencies
     */
    checkDependencies() {
        const required = [
            { name: 'jQuery', check: () => typeof $ !== 'undefined' },
            { name: 'Bootstrap', check: () => typeof bootstrap !== 'undefined' },
            { name: 'DOM', check: () => document.readyState !== 'loading' }
        ];
        
        const missing = required.filter(dep => !dep.check());
        
        if (missing.length > 0) {
            console.warn('UIModule missing dependencies:', missing.map(d => d.name));
            return false;
        }
        
        return true;
    }
    
    /**
     * Setup filter toggle functionality
     */
    setupFilterToggle() {
        const filtersContent = document.getElementById('filters-content');
        if (!filtersContent) return;
        
        filtersContent.addEventListener('hidden.bs.collapse', () => {
            const icon = document.getElementById('filter-toggle-icon');
            if (icon) icon.className = 'fas fa-chevron-down';
        });
        
        filtersContent.addEventListener('shown.bs.collapse', () => {
            const icon = document.getElementById('filter-toggle-icon');
            if (icon) icon.className = 'fas fa-chevron-up';
        });
    }
    
    /**
     * Setup sidebar functionality
     */
    setupSidebar() {
        // Sidebar toggle button
        $('#sidebar-toggle').off('click.ui').on('click.ui', () => {
            this.toggleSidebar();
        });
        
        // Fixed sidebar toggle button (appears when sidebar is hidden)
        $('#sidebar-toggle-fixed').off('click.ui').on('click.ui', () => {
            this.toggleSidebar();
        });
    }
    
    /**
     * Toggle sidebar collapse/expand
     */
    toggleSidebar() {
        const collapsedView = document.querySelector('.collapsed-view');
        const fullView = document.querySelector('.full-view');
        const sidebar = document.querySelector('.filters-sidebar');
        const sidebarColumn = document.getElementById('sidebar-column');
        const mainContent = document.getElementById('main-content');
        const fixedToggle = document.getElementById('sidebar-toggle-fixed');
        
        if (!sidebar || !sidebarColumn || !mainContent) return;
        
        if (this.sidebarCollapsed) {
            // Expanding sidebar
            this.expandSidebar(sidebarColumn, mainContent, sidebar, collapsedView, fullView, fixedToggle);
        } else {
            // Collapsing sidebar
            this.collapseSidebar(sidebarColumn, mainContent, sidebar, collapsedView, fullView, fixedToggle);
        }
    }
    
    /**
     * Expand sidebar
     */
    expandSidebar(sidebarColumn, mainContent, sidebar, collapsedView, fullView, fixedToggle) {
        // Change layout first
        sidebarColumn.className = 'col-md-3';
        mainContent.className = 'col-md-9 main-content';
        
        // Hide fixed toggle button
        if (fixedToggle) {
            fixedToggle.classList.add('d-none');
        }
        
        // Show content with delay
        setTimeout(() => {
            sidebar.classList.remove('collapsed');
            if (collapsedView) collapsedView.style.display = 'none';
            if (fullView) fullView.style.display = 'block';
        }, 50);
        
        this.sidebarCollapsed = false;
        this.emitEvent('sidebarExpanded');
    }
    
    /**
     * Collapse sidebar
     */
    collapseSidebar(sidebarColumn, mainContent, sidebar, collapsedView, fullView, fixedToggle) {
        // Hide content first
        if (collapsedView) collapsedView.style.display = 'block';
        if (fullView) fullView.style.display = 'none';
        sidebar.classList.add('collapsed');
        
        // Change layout with delay
        setTimeout(() => {
            sidebarColumn.className = 'col-md-1';
            mainContent.className = 'col-md-11 main-content';
            
            // Don't show fixed toggle button
            if (fixedToggle) {
                fixedToggle.classList.add('d-none');
            }
        }, 50);
        
        this.sidebarCollapsed = true;
        this.emitEvent('sidebarCollapsed');
    }
    
    /**
     * Setup toast container
     */
    setupToastContainer() {
        // Create toast container if it doesn't exist
        if (!document.getElementById('toast-container')) {
            this.toastContainer = document.createElement('div');
            this.toastContainer.id = 'toast-container';
            this.toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            this.toastContainer.style.zIndex = '9999';
            document.body.appendChild(this.toastContainer);
        } else {
            this.toastContainer = document.getElementById('toast-container');
        }
    }
    
    /**
     * Setup Bootstrap tooltips
     */
    setupTooltips() {
        // Initialize tooltips
        if (window.bootstrap && bootstrap.Tooltip) {
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
        }
        
        // Initialize popovers
        if (window.bootstrap && bootstrap.Popover) {
            const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
            popoverTriggerList.map(function (popoverTriggerEl) {
                return new bootstrap.Popover(popoverTriggerEl);
            });
        }
    }
    
    /**
     * Setup global event listeners
     */
    setupGlobalEventListeners() {
        // Handle window resize for responsive behavior
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                this.handleWindowResize();
            }, 250);
        });
        
        // Handle keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            this.handleKeyboardShortcuts(e);
        });
    }
    
    /**
     * Handle window resize
     */
    handleWindowResize() {
        // Auto-collapse sidebar on small screens
        if (window.innerWidth < 768 && !this.sidebarCollapsed) {
            this.toggleSidebar();
        }
        
        // Emit resize event
        this.emitEvent('windowResized', {
            width: window.innerWidth,
            height: window.innerHeight
        });
    }
    
    /**
     * Handle keyboard shortcuts
     */
    handleKeyboardShortcuts(e) {
        // Don't trigger shortcuts when typing in inputs
        if (e.target.matches('input, textarea, select')) return;
        
        // Ctrl/Cmd + B: Toggle sidebar
        if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
            e.preventDefault();
            this.toggleSidebar();
        }
        
        // Escape: Close modals and dropdowns
        if (e.key === 'Escape') {
            $('.modal').modal('hide');
            $('.dropdown-menu').removeClass('show');
        }
    }
    
    /**
     * Show toast notification
     */
    showToast(message, type = 'info', duration = 5000) {
        if (!this.toastContainer) {
            console.warn('Toast container not initialized');
            return;
        }
        
        const toastId = 'toast-' + Date.now();
        const iconMap = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle', 
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };
        
        const colorMap = {
            success: 'success',
            error: 'danger',
            warning: 'warning',
            info: 'primary'
        };
        
        const toastHTML = `
            <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="toast-header">
                    <i class="${iconMap[type]} text-${colorMap[type]} me-2"></i>
                    <strong class="me-auto">SliceDroid</strong>
                    <small class="text-muted">now</small>
                    <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
                <div class="toast-body">
                    ${message}
                </div>
            </div>
        `;
        
        this.toastContainer.insertAdjacentHTML('beforeend', toastHTML);
        
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement, {
            delay: duration
        });
        
        toast.show();
        
        // Remove from DOM after hiding
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
        
        return toast;
    }
    
    /**
     * Show loading overlay
     */
    showLoading(message = 'Loading...', target = null) {
        const loadingHTML = `
            <div class="loading-overlay d-flex align-items-center justify-content-center">
                <div class="text-center">
                    <div class="spinner-border text-primary mb-3" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <div class="text-muted">${message}</div>
                </div>
            </div>
        `;
        
        if (target) {
            const targetElement = typeof target === 'string' ? document.getElementById(target) : target;
            if (targetElement) {
                targetElement.style.position = 'relative';
                targetElement.insertAdjacentHTML('beforeend', loadingHTML);
            }
        } else {
            // Full page loading
            if (!document.getElementById('global-loading')) {
                const globalLoading = document.createElement('div');
                globalLoading.id = 'global-loading';
                globalLoading.className = 'position-fixed top-0 start-0 w-100 h-100';
                globalLoading.style.zIndex = '9998';
                globalLoading.style.backgroundColor = 'rgba(0,0,0,0.5)';
                globalLoading.innerHTML = loadingHTML;
                document.body.appendChild(globalLoading);
            }
        }
    }
    
    /**
     * Hide loading overlay
     */
    hideLoading(target = null) {
        if (target) {
            const targetElement = typeof target === 'string' ? document.getElementById(target) : target;
            if (targetElement) {
                const loadingOverlay = targetElement.querySelector('.loading-overlay');
                if (loadingOverlay) {
                    loadingOverlay.remove();
                }
            }
        } else {
            // Hide global loading
            const globalLoading = document.getElementById('global-loading');
            if (globalLoading) {
                globalLoading.remove();
            }
        }
    }
    
    /**
     * Update app status in header
     */
    updateAppStatus(status, message) {
        const statusElement = document.getElementById('app-status');
        if (!statusElement) return;
        
        // Remove existing status classes
        statusElement.classList.remove('status-ready', 'status-loading', 'status-error', 'status-success');
        
        // Add new status class
        statusElement.classList.add(`status-${status}`);
        
        // Update content
        const iconMap = {
            ready: 'fas fa-check-circle',
            loading: 'fas fa-spinner fa-spin',
            error: 'fas fa-exclamation-circle',
            success: 'fas fa-check-circle'
        };
        
        statusElement.innerHTML = `
            <i class="${iconMap[status]}"></i>
            <span>${message}</span>
        `;
    }
    
    /**
     * Scroll to element smoothly
     */
    scrollTo(target, offset = 0) {
        const element = typeof target === 'string' ? document.querySelector(target) : target;
        if (!element) return;
        
        const elementPosition = element.getBoundingClientRect().top + window.pageYOffset;
        const offsetPosition = elementPosition - offset;
        
        window.scrollTo({
            top: offsetPosition,
            behavior: 'smooth'
        });
    }
    
    /**
     * Emit custom event
     */
    emitEvent(eventName, detail = {}) {
        const event = new CustomEvent(eventName, { detail });
        document.dispatchEvent(event);
    }
    
    /**
     * Get sidebar state
     */
    isSidebarCollapsed() {
        return this.sidebarCollapsed;
    }
    
    /**
     * Force sidebar state
     */
    setSidebarState(collapsed) {
        if (collapsed !== this.sidebarCollapsed) {
            this.toggleSidebar();
        }
    }
    
    /**
     * Cleanup and destroy
     */
    destroy() {
        // Remove event listeners
        $('#sidebar-toggle').off('.ui');
        $('#sidebar-toggle-fixed').off('.ui');
        
        // Remove toast container
        if (this.toastContainer && this.toastContainer.parentNode) {
            this.toastContainer.parentNode.removeChild(this.toastContainer);
        }
        
        this.initialized = false;
        console.log('UIModule destroyed');
    }
}

// Create global instance
const uiModule = new UIModule();

// Don't auto-initialize - let main.js handle initialization order
// This prevents race conditions with other modules

// Export global functions for backward compatibility
window.showToast = (message, type, duration) => uiModule.showToast(message, type, duration);
window.showLoading = (message, target) => uiModule.showLoading(message, target);
window.hideLoading = (target) => uiModule.hideLoading(target);
window.updateAppStatus = (status, message) => uiModule.updateAppStatus(status, message);
window.toggleSidebar = () => uiModule.toggleSidebar();

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { UIModule, uiModule };
} else {
    window.UIModule = UIModule;
    window.uiModule = uiModule;
}

console.log('UIModule loaded (waiting for initialization)');