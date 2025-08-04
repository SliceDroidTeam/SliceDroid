/**
 * Events Module - Centralized event handling and setup
 */

/**
 * Setup all application event listeners
 */
function setupEventListeners() {
    // Timeline zoom controls
    $('#zoom-in').off('click').on('click', zoomIn);
    $('#zoom-out').off('click').on('click', zoomOut);
    $('#reset-zoom').off('click').on('click', resetZoom);

    // Data loading
    $('#load-data-btn').off('click').on('click', loadAllData);

    // Advanced analytics
    $('#load-analytics-btn').off('click').on('click', loadAdvancedAnalytics);
    $('#apply-analytics-config').off('click').on('click', loadAdvancedAnalyticsWithConfig);

    // Network analysis
    $('#load-network-btn').off('click').on('click', loadNetworkAnalysis);
    
    // Process analysis
    $('#load-process-btn').off('click').on('click', loadProcessAnalysis);

    // Navigation tabs
    $('.nav-tabs a').off('click').on('click', function(e) {
        e.preventDefault();
        $(this).tab('show');
    });

    // Dynamic form handlers
    setupDynamicFormHandlers();

    console.log('Event listeners setup completed');
}

/**
 * Setup dynamic form handlers for analytics configuration
 */
function setupDynamicFormHandlers() {
    // Analytics configuration form
    $('#analytics-form').off('submit').on('submit', function(e) {
        e.preventDefault();
        loadAdvancedAnalyticsWithConfig();
    });

    // Network analysis form
    $('#network-form').off('submit').on('submit', function(e) {
        e.preventDefault();
        loadNetworkAnalysis();
    });

    // Process analysis form
    $('#process-form').off('submit').on('submit', function(e) {
        e.preventDefault();
        loadProcessAnalysis();
    });

    // Input validation
    $('#analytics-window-size').on('input', function() {
        const value = parseInt($(this).val());
        const overlap = parseInt($('#analytics-overlap').val());
        
        if (value < 100 || value > 10000) {
            $(this).addClass('is-invalid');
            $('#analytics-window-size-feedback').text('Window size must be between 100 and 10000');
        } else if (overlap >= value) {
            $(this).addClass('is-invalid');
            $('#analytics-window-size-feedback').text('Window size must be greater than overlap');
        } else {
            $(this).removeClass('is-invalid');
        }
    });

    $('#analytics-overlap').on('input', function() {
        const value = parseInt($(this).val());
        const windowSize = parseInt($('#analytics-window-size').val());
        
        if (value < 0 || value >= windowSize) {
            $(this).addClass('is-invalid');
            $('#analytics-overlap-feedback').text('Overlap must be between 0 and less than window size');
        } else {
            $(this).removeClass('is-invalid');
        }
    });
}

/**
 * Setup keyboard shortcuts
 */
function setupKeyboardShortcuts() {
    $(document).keydown(function(e) {
        // Only trigger shortcuts when not in input fields
        if ($(e.target).is('input, textarea, select')) {
            return;
        }

        switch(e.key) {
            case 'r':
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    loadAllData();
                }
                break;
            case '1':
                if (e.altKey) {
                    e.preventDefault();
                    $('a[href="#timeline-tab"]').tab('show');
                }
                break;
            case '2':
                if (e.altKey) {
                    e.preventDefault();
                    $('a[href="#analytics-tab"]').tab('show');
                }
                break;
            case '3':
                if (e.altKey) {
                    e.preventDefault();
                    $('a[href="#network-tab"]').tab('show');
                }
                break;
            case '4':
                if (e.altKey) {
                    e.preventDefault();
                    $('a[href="#process-tab"]').tab('show');
                }
                break;
            case 'Escape':
                // Close any open modals or dropdowns
                $('.modal').modal('hide');
                $('.dropdown-menu').removeClass('show');
                break;
        }
    });

    console.log('Keyboard shortcuts setup completed');
}

/**
 * Setup responsive event handlers
 */
function setupResponsiveHandlers() {
    // Handle window resize
    let resizeTimeout;
    $(window).on('resize', function() {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(function() {
            // Re-render charts that need responsive updates
            if (timelineData && timelineData.length > 0) {
                renderTimeline();
            }
            
            if (behaviorTimelineData && behaviorTimelineData.windows) {
                renderBehaviorTimelineChart();
            }
        }, 250);
    });

    // Handle tab visibility changes
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden) {
            // Page became visible again - refresh any time-sensitive data
            console.log('Page became visible - checking for data updates');
        }
    });

    console.log('Responsive handlers setup completed');
}

/**
 * Setup accessibility features
 */
function setupAccessibilityFeatures() {
    // Add focus indicators for chart elements
    $(document).on('focus', '.chart-element', function() {
        $(this).addClass('chart-focused');
    });

    $(document).on('blur', '.chart-element', function() {
        $(this).removeClass('chart-focused');
    });

    // Announce important status changes to screen readers
    function announceToScreenReader(message) {
        const announcement = $('<div>').attr({
            'aria-live': 'polite',
            'aria-atomic': 'true',
            'class': 'sr-only'
        }).text(message);
        
        $('body').append(announcement);
        setTimeout(() => announcement.remove(), 1000);
    }

    // Example usage in status updates
    window.announceToScreenReader = announceToScreenReader;

    console.log('Accessibility features setup completed');
}

/**
 * Setup error handling for events
 */
function setupErrorHandling() {
    // Global error handler for AJAX requests
    $(document).ajaxError(function(event, jqXHR, ajaxSettings, thrownError) {
        console.error('AJAX Error:', {
            url: ajaxSettings.url,
            status: jqXHR.status,
            error: thrownError,
            response: jqXHR.responseText
        });

        // Show user-friendly error message
        if (jqXHR.status === 0) {
            showToast('Connection lost. Please check your network connection.', 'error');
        } else if (jqXHR.status >= 500) {
            showToast('Server error occurred. Please try again later.', 'error');
        } else if (jqXHR.status === 404) {
            showToast('Requested resource not found.', 'error');
        }
    });

    // Global error handler for JavaScript errors
    window.addEventListener('error', function(event) {
        console.error('JavaScript Error:', {
            message: event.message,
            filename: event.filename,
            lineno: event.lineno,
            colno: event.colno,
            error: event.error
        });

        // Don't show toast for every JS error to avoid spam
        // Just log it for debugging
    });

    // Promise rejection handler
    window.addEventListener('unhandledrejection', function(event) {
        console.error('Unhandled Promise Rejection:', event.reason);
        event.preventDefault(); // Prevent default browser handling
    });

    console.log('Error handling setup completed');
}

/**
 * Initialize all event systems
 */
function initializeEventSystems() {
    setupEventListeners();
    setupKeyboardShortcuts();
    setupResponsiveHandlers();
    setupAccessibilityFeatures();
    setupErrorHandling();
    
    console.log('All event systems initialized');
}

// Missing zoom and control functions
function zoomIn() {
    console.log('Zoom in triggered');
    // Implementation for timeline/chart zoom in
    if (window.currentChart && typeof window.currentChart.zoomIn === 'function') {
        window.currentChart.zoomIn();
    }
}

function zoomOut() {
    console.log('Zoom out triggered');
    // Implementation for timeline/chart zoom out
    if (window.currentChart && typeof window.currentChart.zoomOut === 'function') {
        window.currentChart.zoomOut();
    }
}

function resetZoom() {
    console.log('Reset zoom triggered');
    // Implementation for timeline/chart zoom reset
    if (window.currentChart && typeof window.currentChart.resetZoom === 'function') {
        window.currentChart.resetZoom();
    }
}

function loadAdvancedAnalytics() {
    console.log('Loading advanced analytics...');
    if (window.loadAdvancedAnalyticsData) {
        window.loadAdvancedAnalyticsData();
    } else {
        console.warn('loadAdvancedAnalyticsData function not available');
    }
}

function loadAdvancedAnalyticsWithConfig() {
    console.log('Loading advanced analytics with config...');
    const windowSize = $('#analytics-window-size').val() || 1000;
    const overlap = $('#analytics-overlap').val() || 200;
    const targetPid = $('#analytics-target-pid').val() || '';
    
    if (window.loadAdvancedAnalyticsData) {
        window.loadAdvancedAnalyticsData({ windowSize, overlap, targetPid });
    } else {
        console.warn('loadAdvancedAnalyticsData function not available');
    }
}

// Export key functions globally
window.initializeEventSystems = initializeEventSystems;
window.setupEventListeners = setupEventListeners;
window.zoomIn = zoomIn;
window.zoomOut = zoomOut;
window.resetZoom = resetZoom;
window.loadAdvancedAnalytics = loadAdvancedAnalytics;
window.loadAdvancedAnalyticsWithConfig = loadAdvancedAnalyticsWithConfig;