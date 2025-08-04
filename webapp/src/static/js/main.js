/**
 * Main Application Entry Point - Modular Version
 * 
 * This is the new modular version of main.js that imports focused modules
 * instead of having everything in one massive file.
 */

// Global state variables
let timelineData = [];
let behaviorTimelineData = [];
let behaviorZoomLevel = 1;
let securityData = {};
let networkData = {};
let processData = {};

// DOM ready initialization
$(document).ready(function() {
    console.log('Initializing modular SliceDroid application...');
    
    // Wait for all core functions to be available
    waitForCoreFunctions().then(function() {
        console.log('Core functions available, proceeding with initialization');
        
        // Initialize UI first
        initializeUI();
        
        updateAppStatus('loading', 'Loading...');

        // Initialize modules in correct order
        initializeUIModule().then(function() {
            console.log('UI Module ready, initializing other modules...');
            
            // Load configuration first, then setup
            loadConfiguration().then(function() {
                updateAppStatus('success', 'System Ready');
                setupMainEventListeners();
                initializeUploadFunctionality();
                initializeAppSelection();
                
                console.log('Application initialized successfully');
            }).catch(function(error) {
                console.error('Failed to load configuration:', error);
                updateAppStatus('warning', 'Fallback Mode');
                
                // Use fallback configuration
                setFallbackConfiguration();
                setupMainEventListeners();
                initializeUploadFunctionality();
                initializeAppSelection();
                
                console.log('Application initialized with fallback configuration');
            });
        }).catch(function(error) {
            console.error('Failed to initialize UI Module:', error);
            updateAppStatus('error', 'Initialization Failed');
        });
    });
});

/**
 * Wait for core functions to be available
 */
function waitForCoreFunctions() {
    return new Promise((resolve, reject) => {
        let attempts = 0;
        const maxAttempts = 50; // 5 seconds max wait
        
        const checkFunctions = () => {
            attempts++;
            
            // Check if all core functions are available
            const requiredFunctions = [
                'updateAppStatus',
                'showToast', 
                'showSectionLoading',
                'showError',
                'createEmptyState',
                'setTimelineData'
            ];
            
            const missing = requiredFunctions.filter(func => typeof window[func] !== 'function');
            
            if (missing.length === 0) {
                console.log('All core functions are available');
                resolve();
            } else if (attempts >= maxAttempts) {
                console.warn('Timeout waiting for core functions:', missing);
                reject(new Error('Timeout waiting for core functions'));
            } else {
                setTimeout(checkFunctions, 100);
            }
        };
        
        checkFunctions();
    });
}

/**
 * Setup main application event listeners
 */
function setupMainEventListeners() {
    // Initialize event systems (this will handle all event setup)
    if (window.initializeEventSystems) {
        window.initializeEventSystems();
    } else {
        console.warn('initializeEventSystems not available');
    }
}

/**
 * Initialize UI components
 */
function initializeUI() {
    // Initialize Bootstrap tooltips
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
    
    console.log('UI components initialized');
}

/**
 * Initialize UI Module with proper dependency order
 */
function initializeUIModule() {
    return new Promise((resolve, reject) => {
        try {
            if (window.uiModule) {
                uiModule.init();
                console.log('UI Module initialized');
                resolve();
            } else {
                console.warn('UIModule not available, retrying...');
                setTimeout(() => {
                    if (window.uiModule) {
                        uiModule.init();
                        console.log('UI Module initialized (delayed)');
                        resolve();
                    } else {
                        reject(new Error('UIModule failed to load'));
                    }
                }, 1000);
            }
        } catch (error) {
            console.error('Failed to initialize UI Module:', error);
            reject(error);
        }
    });
}

/**
 * Initialize upload functionality with error handling
 */
function initializeUploadFunctionality() {
    try {
        if (window.uploadModule) {
            uploadModule.init();
            console.log('Upload functionality initialized via UploadModule');
        } else {
            console.warn('UploadModule not available, retrying in 1 second...');
            setTimeout(() => {
                if (window.uploadModule) {
                    uploadModule.init();
                    console.log('Upload functionality initialized via UploadModule (delayed)');
                } else {
                    console.error('UploadModule failed to load');
                }
            }, 1000);
        }
    } catch (error) {
        console.error('Failed to initialize upload functionality:', error);
        showToast('Upload functionality unavailable', 'warning');
    }
}

/**
 * Initialize app selection functionality with error handling
 */
function initializeAppSelection() {
    try {
        if (window.appSelectionModule) {
            appSelectionModule.init();
            console.log('App selection functionality initialized via AppSelectionModule');
        } else {
            console.warn('AppSelectionModule not available, retrying in 1 second...');
            setTimeout(() => {
                if (window.appSelectionModule) {
                    appSelectionModule.init();
                    console.log('App selection functionality initialized via AppSelectionModule (delayed)');
                } else {
                    console.error('AppSelectionModule failed to load');
                }
            }, 1000);
        }
    } catch (error) {
        console.error('Failed to initialize app selection functionality:', error);
        showToast('App selection functionality unavailable', 'warning');
    }
}


// Global function exports - these will be overridden when the actual functions load
// This ensures that calls don't fail even if the functions aren't available yet

// Core function wrappers with fallback behavior
window.setTimelineData = function(data) {
    if (typeof setTimelineData === 'function') {
        return setTimelineData(data);
    } else {
        console.warn('setTimelineData function not yet available, data will be stored');
        window._pendingTimelineData = data;
    }
};

window.updateAppStatus = function(status, message) {
    if (window.uiModule && typeof window.uiModule.updateAppStatus === 'function') {
        return window.uiModule.updateAppStatus(status, message);
    } else {
        console.log(`Status: ${status} - ${message}`);
    }
};

window.showToast = function(message, type = 'info') {
    if (window.uiModule && typeof window.uiModule.showToast === 'function') {
        return window.uiModule.showToast(message, type);
    } else {
        console.log(`Toast: [${type.toUpperCase()}] ${message}`);
    }
};

window.showSectionLoading = function(sectionId, message = 'Loading...') {
    if (window.uiModule && typeof window.uiModule.showLoading === 'function') {
        return window.uiModule.showLoading(message, sectionId);
    } else {
        const section = document.getElementById(sectionId);
        if (section) {
            section.innerHTML = `<div class="text-center p-3">${message}</div>`;
        }
    }
};

window.showError = function(message, sectionId = null) {
    console.error(message);
    if (sectionId) {
        const section = document.getElementById(sectionId);
        if (section) {
            section.innerHTML = `<div class="alert alert-danger">${message}</div>`;
        }
    }
    if (window.uiModule && typeof window.uiModule.showToast === 'function') {
        window.uiModule.showToast(message, 'error');
    }
};

window.createEmptyState = function(message = 'No data available') {
    return `<div class="text-center text-muted p-4">${message}</div>`;
};

// Functions are now properly routed to UIModule - no more overrides needed

console.log('Main modular application script loaded');