/**
 * Configuration Module - Handles app configuration and initialization
 */

// Global configuration object
let appConfig = {};
let eventColors = {};

/**
 * Load app configuration from server
 */
function loadConfiguration() {
    console.log('Loading configuration...');
    return $.ajax({
        url: '/api/system/config',
        method: 'GET',
        timeout: 10000,
        dataType: 'json'
    })
    .done(function(config) {
        console.log('Configuration loaded successfully:', config);
        appConfig = config;
        eventColors = config.event_categories || {};
    })
    .fail(function(jqXHR, textStatus, errorThrown) {
        console.error('Failed to load configuration:', textStatus, errorThrown, jqXHR);
    });
}

/**
 * Fallback configuration if server config fails
 */
function setFallbackConfiguration() {
    eventColors = {
        'read': '#28a745',
        'write': '#007bff',
        'ioctl': '#6f42c1',
        'binder': '#fd7e14',
        'network': '#17a2b8',
        'other': '#6c757d'
    };
    appConfig = {
        timeline_max_events: 1000,
        default_zoom: 1.0,
        top_devices: 10,
        top_events: 10
    };
}

/**
 * Get current app configuration
 */
function getAppConfig() {
    return appConfig;
}

/**
 * Get event colors configuration
 */
function getEventColors() {
    return eventColors;
}

// Export key functions globally
window.loadConfiguration = loadConfiguration;
window.setFallbackConfiguration = setFallbackConfiguration;
window.getAppConfig = getAppConfig;
window.getEventColors = getEventColors;