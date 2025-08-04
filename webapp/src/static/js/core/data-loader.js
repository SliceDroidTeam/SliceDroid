/**
 * Data Loader Module - Handles all API data loading operations
 */

/**
 * Load all application data
 */
function loadAllData() {
    console.log('Loading all data...');
    
    // Show loading indicators
    showSectionLoading('timeline-section', 'Loading timeline data...');
    showSectionLoading('device-stats-section', 'Loading device statistics...');
    showSectionLoading('event-stats-section', 'Loading event statistics...');
    showSectionLoading('device-chart-section', 'Loading device chart...');
    showSectionLoading('event-chart-section', 'Loading event chart...');
    
    // Load data in parallel
    Promise.all([
        loadTimelineData(),
        loadDeviceStats(),
        loadEventStats(),
        loadDevicePieChart(),
        loadEventPieChart()
    ]).then(function() {
        updateAppStatus('success', 'All data loaded successfully');
        console.log('All data loaded successfully');
    }).catch(function(error) {
        console.error('Error loading data:', error);
        updateAppStatus('error', 'Error loading data');
        showError('Failed to load application data. Please try refreshing the page.');
    });
}

/**
 * Set timeline data programmatically
 */
function setTimelineData(data) {
    if (!data || !Array.isArray(data)) {
        console.warn('setTimelineData: Invalid data provided');
        timelineData = [];
        return;
    }
    
    console.log('Setting timeline data:', data.length, 'events');
    timelineData = data;
    
    // Render timeline if container exists
    if (document.getElementById('timeline-container')) {
        renderTimeline();
    } else {
        console.log('Timeline container not ready, data stored for later rendering');
    }
}

/**
 * Load timeline data from API
 */
function loadTimelineData() {
    return $.ajax({
        url: '/api/timeline',
        method: 'GET',
        timeout: 30000,
        dataType: 'json'
    })
    .done(function(data) {
        console.log('Timeline data loaded:', data.length, 'events');
        setTimelineData(data);
    })
    .fail(function(jqXHR, textStatus, errorThrown) {
        console.error('Failed to load timeline data:', textStatus, errorThrown);
        showError('Failed to load timeline data', 'timeline-section');
    });
}

/**
 * Load device statistics from API
 */
function loadDeviceStats() {
    return $.ajax({
        url: '/api/device_stats',
        method: 'GET',
        timeout: 15000,
        dataType: 'json'
    })
    .done(function(data) {
        console.log('Device stats loaded:', data.length, 'devices');
        renderDeviceStats(data);
    })
    .fail(function(jqXHR, textStatus, errorThrown) {
        console.error('Failed to load device stats:', textStatus, errorThrown);
        showError('Failed to load device statistics', 'device-stats-section');
    });
}

/**
 * Load event statistics from API
 */
function loadEventStats() {
    return $.ajax({
        url: '/api/event_stats',
        method: 'GET',
        timeout: 15000,
        dataType: 'json'
    })
    .done(function(data) {
        console.log('Event stats loaded:', data.length, 'event types');
        renderEventStats(data);
    })
    .fail(function(jqXHR, textStatus, errorThrown) {
        console.error('Failed to load event stats:', textStatus, errorThrown);
        showError('Failed to load event statistics', 'event-stats-section');
    });
}

/**
 * Load device pie chart data from API
 */
function loadDevicePieChart() {
    return $.ajax({
        url: '/api/device_chart_data',
        method: 'GET',
        timeout: 15000,
        dataType: 'json'
    })
    .done(function(data) {
        console.log('Device chart data loaded:', data);
        renderDevicePieChart(data);
    })
    .fail(function(jqXHR, textStatus, errorThrown) {
        console.error('Failed to load device chart data:', textStatus, errorThrown);
        showError('Failed to load device chart', 'device-chart-section');
    });
}

/**
 * Load event pie chart data from API
 */
function loadEventPieChart() {
    return $.ajax({
        url: '/api/event_chart_data',
        method: 'GET',
        timeout: 15000,
        dataType: 'json'
    })
    .done(function(data) {
        console.log('Event chart data loaded:', data);
        renderEventPieChart(data);
    })
    .fail(function(jqXHR, textStatus, errorThrown) {
        console.error('Failed to load event chart data:', textStatus, errorThrown);
        showError('Failed to load event chart', 'event-chart-section');
    });
}

/**
 * Load advanced analytics data
 */
function loadAdvancedAnalytics() {
    const pid = $('#analytics-pid').val();
    const windowSize = $('#analytics-window-size').val() || 1000;
    const overlap = $('#analytics-overlap').val() || 200;
    
    showSectionLoading('analytics-section', 'Running advanced analytics...');
    
    const params = new URLSearchParams();
    if (pid) params.append('pid', pid);
    params.append('window_size', windowSize);
    params.append('overlap', overlap);
    
    return $.ajax({
        url: `/api/advanced-analytics?${params.toString()}`,
        method: 'GET',
        timeout: 60000,
        dataType: 'json'
    })
    .done(function(data) {
        console.log('Advanced analytics loaded:', data);
        renderAdvancedAnalytics(data);
    })
    .fail(function(jqXHR, textStatus, errorThrown) {
        console.error('Failed to load advanced analytics:', textStatus, errorThrown);
        showError('Failed to load advanced analytics', 'analytics-section');
    });
}

/**
 * Load network analysis data
 */
function loadNetworkAnalysis() {
    const pid = $('#network-pid').val();
    
    showSectionLoading('network-section', 'Running network analysis...');
    
    const params = new URLSearchParams();
    if (pid) params.append('pid', pid);
    
    return $.ajax({
        url: `/api/network-analysis?${params.toString()}`,
        method: 'GET',
        timeout: 45000,
        dataType: 'json'
    })
    .done(function(data) {
        console.log('Network analysis loaded:', data);
        networkData = data;
        renderNetworkAnalysis(data);
    })
    .fail(function(jqXHR, textStatus, errorThrown) {
        console.error('Failed to load network analysis:', textStatus, errorThrown);
        showError('Failed to load network analysis', 'network-section');
    });
}

/**
 * Load process analysis data
 */
function loadProcessAnalysis() {
    const pid = $('#process-pid').val();
    
    showSectionLoading('process-section', 'Running process analysis...');
    
    const params = new URLSearchParams();
    if (pid) params.append('pid', pid);
    
    return $.ajax({
        url: `/api/process-analysis?${params.toString()}`,
        method: 'GET',
        timeout: 45000,
        dataType: 'json'
    })
    .done(function(data) {
        console.log('Process analysis loaded:', data);
        processData = data;
        renderProcessAnalysis(data);
    })
    .fail(function(jqXHR, textStatus, errorThrown) {
        console.error('Failed to load process analysis:', textStatus, errorThrown);
        showError('Failed to load process analysis', 'process-section');
    });
}

// Export key functions globally
window.setTimelineData = setTimelineData;
window.loadAllData = loadAllData;
window.loadTimelineData = loadTimelineData;
window.loadDeviceStats = loadDeviceStats;
window.loadEventStats = loadEventStats;