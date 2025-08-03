// Global variables
let timelineData = [];
let zoomLevel = 1;
let behaviorTimelineData = [];
let behaviorZoomLevel = 1;
let eventColors = {};
let appConfig = {};
let securityData = {};
let networkData = {};
let processData = {};

// DOM ready
$(document).ready(function() {
    // Initialize UI first
    initializeUI();
    
    updateAppStatus('loading', 'Loading...');

    // Load configuration first, then data
    loadConfiguration().then(function() {
        updateAppStatus('success', 'System Ready');
        // Skip loading trace data automatically
        setupEventListeners();
        
        // Initialize upload functionality
        initializeUploadFunctionality();
        
        // Initialize app selection
        initializeAppSelection();
    }).catch(function(error) {
        console.error('Failed to load configuration:', error);
        updateAppStatus('warning', 'Fallback Mode');
        // Use fallback configuration
        setFallbackConfiguration();
        // Skip loading trace data automatically
        setupEventListeners();
        
        // Initialize upload functionality
        initializeUploadFunctionality();
        
        // Initialize app selection
        initializeAppSelection();
    });
});

// Load app configuration from server
function loadConfiguration() {
    console.log('Loading configuration...');
    return $.ajax({
        url: '/api/config',
        method: 'GET',
        timeout: 10000,
        dataType: 'json'
    })
    .done(function(config) {
        console.log('Configuration loaded successfully:', config);
        appConfig = config;
        eventColors = config.event_categories || {};
        zoomLevel = config.default_zoom || 1;
    })
    .fail(function(jqXHR, textStatus, errorThrown) {
        console.error('Failed to load configuration:', textStatus, errorThrown, jqXHR);
    });
}

// Fallback configuration if server config fails
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

// Setup event listeners
function setupEventListeners() {
    $('#zoom-in').click(zoomIn);
    $('#zoom-out').click(zoomOut);
    $('#reset-zoom').click(resetZoom);

    // Upload functionality is now handled in inline script

    // Advanced analytics
    $('#load-analytics-btn').click(loadAdvancedAnalytics);
    $('#apply-analytics-config').click(loadAdvancedAnalyticsWithConfig);
    
    // Also bind to the actual configure button
    $(document).on('click', '#apply-analytics-config', loadAdvancedAnalyticsWithConfig);

}

// Load all data
function loadAllData() {
    // Show loading state for main sections
    showSectionLoading();

    try {
        // Load timeline data
        loadTimelineData();

        // Load statistics
        loadDeviceStats();
        loadEventStats();

        // Load charts
        loadDevicePieChart();
        loadEventPieChart();

        // Auto-load advanced analytics
        loadAdvancedAnalytics();
        
        // Load new enhanced analysis
        loadNetworkAnalysis();
        loadProcessAnalysis();
    } catch (error) {
        console.error('Error loading data:', error);
        showToast('Loading Error', 'Failed to load some data sections', 'error');
    }
}

function showSectionLoading() {
    // Add loading indicators to main sections
    $('#timeline-container').html('<div class="text-center p-4"><div class="loading-spinner"></div><p class="mt-2">Loading timeline...</p></div>');
    $('#device-stats-table tbody').html('<tr><td colspan="4" class="text-center"><div class="loading-spinner"></div> Loading...</td></tr>');
    $('#event-stats-table tbody').html('<tr><td colspan="3" class="text-center"><div class="loading-spinner"></div> Loading...</td></tr>');
}

// Show error message
function showError(message) {
    console.error(message);
    showToast('Error', message, 'error');
}


// Timeline functions
function loadTimelineData() {
    let url = '/api/timeline';

    $.getJSON(url, function(data) {
        if (data.error) {
            showError(`Timeline error: ${data.error}`);
            return;
        }
        timelineData = data;
        renderTimeline();
    }).fail(function(jqXHR) {
        const errorMsg = jqXHR.responseJSON?.error || 'Failed to load timeline data';
        showError(errorMsg);
    });
}

function renderTimeline() {
    // Clear existing timeline
    d3.select('#timeline-container').html('');

    if (timelineData.length === 0) {
        d3.select('#timeline-container')
            .append('div')
            .attr('class', 'alert alert-info')
            .text('No data found for the selected filters.');
        return;
    }

    // Set up dimensions
    const margin = {top: 20, right: 20, bottom: 50, left: 100};
    const width = document.getElementById('timeline-container').clientWidth - margin.left - margin.right;
    const height = document.getElementById('timeline-container').clientHeight - margin.top - margin.bottom;

    // Create SVG
    const svg = d3.select('#timeline-container')
        .append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom)
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    // Apply zoom scaling
    const visibleDataCount = Math.ceil(timelineData.length / zoomLevel);
    const visibleData = timelineData.slice(0, visibleDataCount);

    // Set up scales
    const x = d3.scaleLinear()
        .domain([0, visibleDataCount])
        .range([0, width]);

    // Group data by category for easier display
    const categoryGroups = {};
    const categories = ['read', 'write', 'ioctl', 'binder', 'network', 'other'];

    visibleData.forEach(event => {
        if (!categoryGroups[event.category]) {
            categoryGroups[event.category] = [];
        }
        categoryGroups[event.category].push(event);
    });

    // Calculate y positions for each category
    const y = d3.scaleBand()
        .domain(categories)
        .range([0, height])
        .padding(0.1);

    // Add background stripes for categories
    categories.forEach(category => {
        svg.append('rect')
            .attr('x', 0)
            .attr('y', y(category))
            .attr('width', width)
            .attr('height', y.bandwidth())
            .attr('fill', '#f8f9fa')
            .attr('stroke', '#eee');
    });

    // Add category labels
    svg.selectAll('.category-label')
        .data(categories)
        .enter()
        .append('text')
        .attr('class', 'category-label')
        .attr('x', -10)
        .attr('y', d => y(d) + y.bandwidth() / 2)
        .attr('text-anchor', 'end')
        .attr('dominant-baseline', 'middle')
        .text(d => d.charAt(0).toUpperCase() + d.slice(1));

    // Draw events
    Object.keys(categoryGroups).forEach(category => {
        svg.selectAll(`.dot-${category}`)
            .data(categoryGroups[category])
            .enter()
            .append('circle')
            .attr('class', `dot-${category}`)
            .attr('cx', d => x(d.time))
            .attr('cy', d => y(d.category) + y.bandwidth() / 2)
            .attr('r', 4)
            .attr('fill', eventColors[category])
            .on('mouseover', function(event, d) {
                showTooltip(event, d);
            })
            .on('mouseout', hideTooltip);
    });

    // Add x-axis
    svg.append('g')
        .attr('transform', `translate(0,${height})`)
        .call(d3.axisBottom(x).ticks(10).tickFormat(d3.format('d')));

    // Add x-axis label
    svg.append('text')
        .attr('x', width / 2)
        .attr('y', height + 40)
        .attr('text-anchor', 'middle')
        .text('Timeline of events');

    // Create tooltip div if it doesn't exist
    if (!d3.select('#timeline-tooltip').node()) {
        d3.select('body').append('div')
            .attr('id', 'timeline-tooltip')
            .style('position', 'absolute')
            .style('background', 'white')
            .style('border', '1px solid #ddd')
            .style('border-radius', '4px')
            .style('padding', '10px')
            .style('box-shadow', '0 0 10px rgba(0,0,0,0.1)')
            .style('pointer-events', 'none')
            .style('opacity', 0)
            .style('z-index', 1000);
    }
}

function showTooltip(event, d) {
    const tooltip = d3.select('#timeline-tooltip');
    tooltip.transition().duration(200).style('opacity', 0.9);

    // Format device and pathname information
    let deviceInfo = '';
    if (d.device !== null && d.device !== 0) {
        deviceInfo = `<strong>Device:</strong> ${d.device}<br>`;
    }

    let pathnameInfo = '';
    if (d.pathname) {
        pathnameInfo = `<strong>Path:</strong> ${d.pathname}<br>`;
    }

    tooltip.html(`
        <strong>Event:</strong> ${d.event}<br>
        <strong>Category:</strong> ${d.category}<br>
        <strong>PID:</strong> ${d.pid || 'N/A'}<br>
        <strong>TID:</strong> ${d.tid || 'N/A'}<br>
        ${deviceInfo}
        ${pathnameInfo}
    `)
    .style('left', (event.pageX + 10) + 'px')
    .style('top', (event.pageY - 28) + 'px');
}

function hideTooltip() {
    d3.select('#timeline-tooltip').transition().duration(500).style('opacity', 0);
}

// Zoom functions
function zoomIn() {
    zoomLevel = Math.min(zoomLevel * 1.5, timelineData.length / 10);
    renderTimeline();
}

function zoomOut() {
    zoomLevel = Math.max(zoomLevel / 1.5, 1);
    renderTimeline();
}

function resetZoom() {
    zoomLevel = 1;
    renderTimeline();
}

// Behavior Timeline zoom functions
function behaviorZoomIn() {
    behaviorZoomLevel = Math.min(behaviorZoomLevel * 1.5, 10);
    renderBehaviorTimelineChart();
}

function behaviorZoomOut() {
    behaviorZoomLevel = Math.max(behaviorZoomLevel / 1.5, 1);
    renderBehaviorTimelineChart();
}

function behaviorResetZoom() {
    behaviorZoomLevel = 1;
    renderBehaviorTimelineChart();
}

// Behavior Timeline function (creates timeline from SliceDroid reconstruction)
function renderBehaviorTimeline(analysisData) {
    const container = document.getElementById('behavior-timeline-chart');
    if (!container) return;

    // Clear existing content
    container.innerHTML = '';

    // First check if we have valid analysis data
    if (!analysisData || typeof analysisData !== 'object') {
        container.innerHTML = '<div class="alert alert-info">No analysis data available. Please analyze an app first.</div>';
        return;
    }

    // Extract comprehensive analytics data (from SliceDroid reconstruction)
    const comprehensiveAnalytics = analysisData.comprehensive_analytics;
    
    if (!comprehensiveAnalytics) {
        container.innerHTML = '<div class="alert alert-info">No behavior timeline data available - comprehensive analysis not performed</div>';
        return;
    }

    // Get window data from SliceDroid reconstruction
    const kdevsTrace = comprehensiveAnalytics.kdevs_trace || [];
    const tcpTrace = comprehensiveAnalytics.TCP_trace || [];
    const sensitiveTrace = comprehensiveAnalytics.sensitive_data_trace || {};
    
    if (kdevsTrace.length === 0) {
        container.innerHTML = '<div class="alert alert-info">No behavior windows found</div>';
        return;
    }

    // Load device category mapping from file
    let dev2cat = {};
    
    // Load the category mapping asynchronously
    console.log('Loading device category mapping...');
    fetch('/data/mappings/cat2devs.txt')
        .then(response => {
            console.log('Response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(categoryMapping => {
            console.log('Category mapping loaded successfully:', Object.keys(categoryMapping).length, 'categories');
            // Convert category-to-devices mapping to device-to-category mapping
            Object.keys(categoryMapping).forEach(category => {
                categoryMapping[category].forEach(deviceId => {
                    // Handle both string and numeric device IDs
                    // For strings like "124845621 - 5421", use the whole string as key
                    let deviceKey;
                    if (typeof deviceId === 'string' && deviceId.includes(' - ')) {
                        deviceKey = deviceId; // Keep compound IDs as strings
                    } else {
                        deviceKey = parseInt(deviceId) || deviceId;
                    }
                    dev2cat[deviceKey] = category;
                });
            });
            
            // Now process the timeline data with the loaded mapping
            processBehaviorTimelineData(kdevsTrace, tcpTrace, sensitiveTrace, dev2cat);
        })
        .catch(error => {
            console.error('Error loading device mapping:', error);
            container.innerHTML = '<div class="alert alert-warning">Could not load device category mapping. Behavior timeline unavailable.</div>';
        });
}

// Separate function to process behavior timeline data
function processBehaviorTimelineData(kdevsTrace, tcpTrace, sensitiveTrace, dev2cat) {
    console.log('processBehaviorTimelineData called');
    const container = document.getElementById('behavior-timeline-chart');
    console.log('Container found:', container);
    if (!container) {
        console.log('Container not found, returning');
        return;
    }

    // Create behavior timeline from window data (similar to legacy code)
    behaviorTimelineData = [];
    
    // Process each window
    kdevsTrace.forEach((kdevWindow, windowIndex) => {
        const windowCategories = [];
        
        // Process device events in this window
        Object.keys(kdevWindow).forEach(kdev => {
            const count = kdevWindow[kdev];
            
            // Try to map device to category - check both numeric and string forms
            let category = null;
            const deviceIdNum = parseInt(kdev);
            const deviceIdStr = kdev.toString();
            
            if (deviceIdNum in dev2cat) {
                category = dev2cat[deviceIdNum];
            } else if (deviceIdStr in dev2cat) {
                category = dev2cat[deviceIdStr];
            }
            
            // Skip unknown devices
            if (!category) {
                return;
            }
            
            // Add category to this window if not already present
            if (!windowCategories.includes(category)) {
                windowCategories.push(category);
                
                behaviorTimelineData.push({
                    timestamp: windowIndex,
                    windowIndex: windowIndex,
                    type: 'device',
                    category: category,
                    process: 'system',
                    details: `${category} Activity (Device ${kdev}, ${count} events)`,
                    deviceId: kdev,
                    count: count
                });
            }
        });
        
        // Add TCP events for this window
        if (tcpTrace[windowIndex] && tcpTrace[windowIndex].length > 0) {
            tcpTrace[windowIndex].forEach(tcpEvent => {
                const tcpDetails = tcpEvent.details || {};
                const state = tcpDetails.newstate || 'UNKNOWN';
                const daddr = tcpDetails.daddr || 'unknown';
                
                behaviorTimelineData.push({
                    timestamp: windowIndex + 0.1, // Slight offset to show after device events
                    windowIndex: windowIndex,
                    type: 'network',
                    category: 'TCP',
                    process: tcpEvent.process || 'network',
                    details: `${state}: ${daddr}`,
                    tcpState: state,
                    targetAddr: daddr
                });
            });
        }
        
        // Add sensitive data events for this window
        Object.keys(sensitiveTrace).forEach(sensitiveType => {
            if (sensitiveTrace[sensitiveType] && 
                sensitiveTrace[sensitiveType][windowIndex] && 
                sensitiveTrace[sensitiveType][windowIndex].length > 0) {
                
                // Get the actual sensitive events for this specific window
                const windowEvents = sensitiveTrace[sensitiveType][windowIndex];
                
                if (windowEvents.length > 0) {
                    behaviorTimelineData.push({
                        timestamp: windowIndex + 0.2, // Offset for sensitive events
                        windowIndex: windowIndex,
                        type: 'sensitive',
                        category: sensitiveType,
                        process: 'system',
                        details: `${sensitiveType.charAt(0).toUpperCase() + sensitiveType.slice(1)} Access (${windowEvents.length} events)`,
                        count: windowEvents.length
                    });
                }
            }
        });
    });

    // Sort events by timestamp (window order)
    behaviorTimelineData.sort((a, b) => a.timestamp - b.timestamp);

    if (behaviorTimelineData.length === 0) {
        if (container) {
            container.innerHTML = '<div class="alert alert-info">No behavior events found in reconstruction windows</div>';
        }
        return;
    }

    renderBehaviorTimelineChart();
}

function renderBehaviorTimelineChart() {
    const container = document.getElementById('behavior-timeline-chart');
    if (!container || behaviorTimelineData.length === 0) return;

    // Clear existing content
    container.innerHTML = '';

    // Apply zoom to data
    const visibleDataCount = Math.ceil(behaviorTimelineData.length / behaviorZoomLevel);
    const visibleData = behaviorTimelineData.slice(0, visibleDataCount);

    // Create timeline visualization similar to Event Timeline
    const containerWidth = container.clientWidth || 800;
    const containerHeight = 300;
    const margin = {top: 20, right: 20, bottom: 50, left: 100};
    const width = containerWidth - margin.left - margin.right;
    const height = containerHeight - margin.top - margin.bottom;

    // Create SVG
    const svg = d3.select(container)
        .append('svg')
        .attr('width', containerWidth)
        .attr('height', containerHeight)
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    // Define categories and colors for behavior timeline (based on legacy SliceDroid code)
    const categories = ['camera', 'audio_in', 'TCP', 'bluetooth', 'nfc', 'gnss', 'contacts', 'sms', 'calendar', 'call_logs', 'callogger'];
    const categoryColors = {
        'camera': '#007bff',      // Blue
        'audio_in': '#dc3545',    // Red
        'TCP': '#28a745',         // Green  
        'bluetooth': '#6c757d',   // Grey
        'nfc': '#e83e8c',         // Magenta/Pink
        'gnss': '#343a40',        // Black/Dark
        'contacts': '#fd7e14',    // Orange
        'sms': '#ffc107',         // Yellow
        'calendar': '#17a2b8',    // Cyan
        'call_logs': '#6f42c1',   // Purple
        'callogger': '#8e44ad'    // Dark purple
    };

    // Set up scales
    const timeScale = d3.scaleLinear()
        .domain([0, visibleData.length - 1])
        .range([0, width]);

    const categoryScale = d3.scaleBand()
        .domain(categories)
        .range([0, height])
        .padding(0.1);

    // Add background stripes for categories
    categories.forEach(category => {
        svg.append('rect')
            .attr('x', 0)
            .attr('y', categoryScale(category))
            .attr('width', width)
            .attr('height', categoryScale.bandwidth())
            .attr('fill', '#f8f9fa')
            .attr('stroke', '#eee');
    });

    // Add category labels
    svg.selectAll('.category-label')
        .data(categories)
        .enter()
        .append('text')
        .attr('class', 'category-label')
        .attr('x', -10)
        .attr('y', d => categoryScale(d) + categoryScale.bandwidth() / 2)
        .attr('text-anchor', 'end')
        .attr('dominant-baseline', 'middle')
        .style('font-size', '12px')
        .style('font-weight', 'bold')
        .text(d => d.charAt(0).toUpperCase() + d.slice(1));

    // Add events as circles
    svg.selectAll('.event-dot')
        .data(visibleData)
        .enter()
        .append('circle')
        .attr('class', 'event-dot')
        .attr('cx', (d, i) => timeScale(i))
        .attr('cy', d => categoryScale(d.category) + categoryScale.bandwidth() / 2)
        .attr('r', 4)
        .attr('fill', d => categoryColors[d.category] || '#6c757d')
        .attr('stroke', '#fff')
        .attr('stroke-width', 1)
        .style('cursor', 'pointer')
        .on('mouseover', function(event, d) {
            // Show tooltip
            const tooltip = d3.select('body').append('div')
                .attr('class', 'timeline-tooltip')
                .style('position', 'absolute')
                .style('background', '#333')
                .style('color', '#fff')
                .style('padding', '8px')
                .style('border-radius', '4px')
                .style('font-size', '12px')
                .style('pointer-events', 'none')
                .style('z-index', '1000')
                .html(`
                    <strong>${d.details}</strong><br>
                    Category: ${d.category}<br>
                    Process: ${d.process}<br>
                    Timestamp: ${d.timestamp.toFixed(6)}
                `);

            tooltip.style('left', (event.pageX + 10) + 'px')
                   .style('top', (event.pageY - 10) + 'px');
        })
        .on('mouseout', function() {
            d3.selectAll('.timeline-tooltip').remove();
        });

    // Add x-axis
    svg.append('g')
        .attr('transform', `translate(0,${height})`)
        .call(d3.axisBottom(timeScale).ticks(10).tickFormat(d => `Window ${Math.floor(d)}`));

    // Add title
    svg.append('text')
        .attr('x', width / 2)
        .attr('y', -5)
        .attr('text-anchor', 'middle')
        .style('font-size', '14px')
        .style('font-weight', 'bold')
        .text(`Behavior Timeline (${behaviorTimelineData.length} events, showing ${visibleData.length})`);
}

// Statistics functions
function loadDeviceStats() {
    $.getJSON('/api/device_stats', function(data) {
        if (data && data.error) {
            $('#device-stats-table tbody').html(`<tr><td colspan="4" class="text-center text-danger">Error: ${data.error}</td></tr>`);
            return;
        }
        renderDeviceStats(data);
    }).fail(function(jqXHR) {
        const errorMsg = jqXHR.responseJSON?.error || 'Failed to load device statistics';
        $('#device-stats-table tbody').html(`<tr><td colspan="4" class="text-center text-danger">Error: ${errorMsg}</td></tr>`);
        console.error('Device stats error:', errorMsg);
    });
}

function renderDeviceStats(data) {
    const tableBody = $('#device-stats-table tbody');

    if (tableBody.length === 0) {
        console.error('Device stats table body not found!');
        return;
    }

    tableBody.empty();

    if (!data || !Array.isArray(data) || data.length === 0) {
        tableBody.html('<tr><td colspan="4" class="text-center">No data found</td></tr>');
        return;
    }

    let html = '';
    data.forEach(item => {
        const paths = Array.isArray(item.paths) ? item.paths.join(', ') : '';
        const pathCount = Array.isArray(item.paths) ? item.paths.length : 0;
        html += `
            <tr>
                <td>${item.device || 'Unknown'}</td>
                <td>${item.count || 0}</td>
                <td>${pathCount}</td>
                <td title="${paths}">${paths.length > 50 ? paths.substring(0, 50) + '...' : paths}</td>
            </tr>
        `;
    });
    tableBody.html(html);
}

function loadEventStats() {
    $.getJSON('/api/event_stats', function(data) {
        if (data && data.error) {
            $('#event-stats-table tbody').html(`<tr><td colspan="3" class="text-center text-danger">Error: ${data.error}</td></tr>`);
            return;
        }
        renderEventStats(data);
    }).fail(function(jqXHR) {
        const errorMsg = jqXHR.responseJSON?.error || 'Failed to load event statistics';
        $('#event-stats-table tbody').html(`<tr><td colspan="3" class="text-center text-danger">Error: ${errorMsg}</td></tr>`);
        console.error('Event stats error:', errorMsg);
    });
}

function renderEventStats(data) {
    const tableBody = $('#event-stats-table tbody');

    if (tableBody.length === 0) {
        console.error('Event stats table body not found!');
        return;
    }

    tableBody.empty();

    if (!data || !Array.isArray(data) || data.length === 0) {
        tableBody.html('<tr><td colspan="3" class="text-center">No data found</td></tr>');
        return;
    }

    const totalEvents = data.reduce((sum, item) => sum + (item.count || 0), 0);

    let html = '';
    data.forEach(item => {
        const count = item.count || 0;
        const percentage = totalEvents > 0 ? ((count / totalEvents) * 100).toFixed(2) : '0.00';
        html += `
            <tr>
                <td>${item.event || 'Unknown'}</td>
                <td>${count}</td>
                <td>${percentage}%</td>
            </tr>
        `;
    });
    tableBody.html(html);
}

// Chart functions
function loadDevicePieChart() {
    $.getJSON('/api/device_stats', function(data) {
        if (data.error) {
            showError(`Device chart error: ${data.error}`);
            return;
        }
        renderDevicePieChart(data);
    }).fail(function(jqXHR) {
        const errorMsg = jqXHR.responseJSON?.error || 'Failed to load device chart data';
        showError(errorMsg);
    });
}

function renderDevicePieChart(data) {
    if (data.length === 0) {
        $('#device-chart-container').html('<div class="alert alert-info">No data found</div>');
        return;
    }

    // Prepare data for pie chart (top N devices)
    const topN = appConfig.top_devices || 10;
    const topDevices = data.slice(0, topN);
    const chartData = topDevices.map(item => ({
        label: `Device ${item.device}`,
        value: item.count
    }));

    createPieChart('device-chart-container', chartData, 'Device Usage Distribution');
}

function loadEventPieChart() {
    $.getJSON('/api/event_stats', function(data) {
        if (data.error) {
            showError(`Event chart error: ${data.error}`);
            return;
        }
        renderEventPieChart(data);
    }).fail(function(jqXHR) {
        const errorMsg = jqXHR.responseJSON?.error || 'Failed to load event chart data';
        showError(errorMsg);
    });
}

function renderEventPieChart(data) {
    if (data.length === 0) {
        $('#event-chart-container').html('<div class="alert alert-info">No data found</div>');
        return;
    }

    // Prepare data for pie chart (top N events)
    const topN = appConfig.top_events || 10;
    const topEvents = data.slice(0, topN);
    const chartData = topEvents.map(item => ({
        label: item.event,
        value: item.count
    }));

    createPieChart('event-chart-container', chartData, 'Event Type Distribution');
}

// Upload functionality is now handled in inline script

// Advanced Analytics functionality
function loadAdvancedAnalytics() {
    let url = '/api/advanced-analytics';

    // Show loading
    $('#analytics-loading').show();
    $('#analytics-content').hide();
    $('#analytics-error').hide();
    $('#load-analytics-btn').prop('disabled', true);

    $.getJSON(url, function(data) {
        if (data.error) {
            showAnalyticsError(data.error);
        } else {
            renderAdvancedAnalytics(data);
        }
    }).fail(function(jqXHR) {
        const errorMsg = jqXHR.responseJSON?.error || 'Failed to load advanced analytics';
        showAnalyticsError(errorMsg);
    }).always(function() {
        $('#analytics-loading').hide();
        $('#load-analytics-btn').prop('disabled', false);
    });
}

function renderAdvancedAnalytics(data) {
    $('#analytics-content').show();

    try {
        // Render summary cards
        renderAnalyticsSummary(data);

        // Render charts
        renderAnalyticsCharts(data.charts, data);

        // Render detailed insights
        renderDetailedInsights(data);

    } catch (error) {
        console.error('Error rendering analytics:', error);
        showToast('Rendering Error', 'Failed to display some analytics results', 'error');
    }
}

function renderAnalyticsSummary(data) {
    const summaryContainer = $('#analytics-summary');
    summaryContainer.empty();

    // Create summary cards
    const summaryCards = [
        {
            title: 'Target PID',
            value: data.target_pid || 'N/A',
            icon: 'fas fa-bullseye',
            color: 'primary'
        },
        {
            title: 'Total Events',
            value: data.total_events?.toLocaleString() || '0',
            icon: 'fas fa-list',
            color: 'success'
        },
        {
            title: 'Unique Processes',
            value: data.process_analysis?.unique_processes || '0',
            icon: 'fas fa-cogs',
            color: 'info'
        },
        {
            title: 'Unique Devices',
            value: data.device_analysis?.unique_devices || '0',
            icon: 'fas fa-hdd',
            color: 'warning'
        },
        {
            title: 'Duration',
            value: data.time_range?.duration ? `${data.time_range.duration.toFixed(2)}s` : 'N/A',
            icon: 'fas fa-clock',
            color: 'secondary'
        },
        {
            title: 'Events/Second',
            value: data.temporal_patterns?.events_per_second ?
                   data.temporal_patterns.events_per_second.toFixed(2) : 'N/A',
            icon: 'fas fa-tachometer-alt',
            color: 'danger'
        }
    ];

    summaryCards.forEach(card => {
        summaryContainer.append(`
            <div class="col-md-2 mb-3">
                <div class="card border-${card.color}">
                    <div class="card-body text-center">
                        <i class="${card.icon} fa-2x text-${card.color} mb-2"></i>
                        <h5 class="card-title">${card.value}</h5>
                        <small class="text-muted">${card.title}</small>
                    </div>
                </div>
            </div>
        `);
    });
}

function renderAnalyticsCharts(charts, analysisData) {
    if (!charts) return;

    // Render behavior timeline similar to event timeline
    renderBehaviorTimeline(analysisData || {})

    if (charts.category_distribution) {
        $('#category-chart').html(`<img src="${charts.category_distribution}" class="img-fluid" alt="Category Distribution" style="max-height: 350px; max-width: 100%; object-fit: contain;">`);
    } else {
        $('#category-chart').html('<div class="alert alert-info">No category data available</div>');
    }

    if (charts.device_usage) {
        $('#device-usage-chart').html(`<img src="${charts.device_usage}" class="img-fluid" alt="Device Usage">`);
    } else {
        $('#device-usage-chart').html('<div class="alert alert-info">No device usage data available</div>');
    }

    if (charts.process_activity) {
        $('#process-activity-chart').html(`<img src="${charts.process_activity}" class="img-fluid" alt="Process Activity">`);
    } else {
        $('#process-activity-chart').html('<div class="alert alert-info">No process activity data available</div>');
    }

    if (charts.network_activity) {
        $('#network-chart').html(`<img src="${charts.network_activity}" class="img-fluid" alt="Network Activity">`);
    } else {
        $('#network-chart').html('<div class="alert alert-info">No network activity data available</div>');
    }
}

function renderDetailedInsights(data) {
    const insightsContainer = $('#detailed-insights');
    insightsContainer.empty();

    if (!data.detailed_insights || Object.keys(data.detailed_insights).length === 0) {
        insightsContainer.html('<div class="alert alert-info">No detailed insights available</div>');
        return;
    }

    let insights = '<div class="accordion" id="insightsAccordion">';

    // Render insights from backend
    Object.entries(data.detailed_insights).forEach(([key, insightData]) => {
        insights += createInsightSection(key, insightData.title,
            generateInsightContent(insightData.insights));
    });

    insights += '</div>';
    insightsContainer.html(insights);
}

function generateInsightContent(insights) {
    if (!insights || insights.length === 0) {
        return '<div class="alert alert-info">No insights available</div>';
    }

    let content = '<ul class="list-group list-group-flush">';
    insights.forEach(insight => {
        content += `<li class="list-group-item">${insight.icon} ${insight.text}</li>`;
    });
    content += '</ul>';
    return content;
}

function createInsightSection(id, title, content) {
    return `
        <div class="accordion-item">
            <h2 class="accordion-header">
                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse"
                        data-bs-target="#collapse${id}" aria-expanded="false">
                    ${title}
                </button>
            </h2>
            <div id="collapse${id}" class="accordion-collapse collapse" data-bs-parent="#insightsAccordion">
                <div class="accordion-body">
                    ${content}
                </div>
            </div>
        </div>
    `;
}

function showAnalyticsError(error) {
    $('#analytics-error').html(`<strong>Error:</strong> ${error}`).show();
}

function loadAdvancedAnalyticsWithConfig() {
    const pid = $('#analytics-target-pid').val();
    const windowSize = $('#analytics-window-size').val();
    const overlap = $('#analytics-overlap').val();
    
    // Validation
    if (parseInt(overlap) >= parseInt(windowSize)) {
        showToast('Configuration Error', 'Overlap must be less than window size', 'error');
        return;
    }
    
    // Build URL with parameters
    let url = '/api/advanced-analytics';
    let params = [];
    if (pid) params.push(`pid=${pid}`);
    if (windowSize) params.push(`window_size=${windowSize}`);
    if (overlap) params.push(`overlap=${overlap}`);
    
    if (params.length > 0) {
        url += '?' + params.join('&');
    }
    
    // Show loading
    updateAppStatus('loading', 'Running Custom Analysis...');
    $('#analytics-loading').show();
    $('#analytics-content').hide();
    $('#analytics-error').hide();
    
    $.getJSON(url, function(data) {
        if (data.error) {
            showAnalyticsError(data.error);
        } else {
            renderAdvancedAnalytics(data);
            showToast('Custom Analysis Complete', `Analysis with window size ${windowSize} completed`, 'success');
            // Collapse the config panel after successful run
            $('#analytics-config').collapse('hide');
        }
    }).fail(function(jqXHR) {
        const errorMsg = jqXHR.responseJSON?.error || 'Failed to load custom analytics';
        showAnalyticsError(errorMsg);
    }).always(function() {
        $('#analytics-loading').hide();
        updateAppStatus('success', 'System Ready');
    });
}


// Enhanced Network Analysis Functions
function loadNetworkAnalysis() {
    let url = '/api/network-analysis';

    // Show loading
    $('#network-loading').show();
    $('#network-content').hide();
    $('#network-error').hide();

    $.getJSON(url, function(data) {
        if (data.error) {
            showNetworkError(data.error);
        } else {
            networkData = data;
            renderNetworkAnalysis(data);
        }
    }).fail(function(jqXHR) {
        const errorMsg = jqXHR.responseJSON?.error || 'No network analysis data available';
        showNetworkError(errorMsg);
    }).always(function() {
        $('#network-loading').hide();
    });
}

function renderNetworkAnalysis(data) {
    $('#network-content').show();
    $('#network-error').hide();
    $('#network-loading').hide();

    // Wait for container to be fully visible before rendering charts
    setTimeout(() => {
        // Update intensity badge
        updateNetworkIntensityBadge(data.network_analysis);

        // Render summary cards
        renderNetworkSummary(data);

        // Render network flow chart with container check
        if (document.getElementById('network-flow-chart') && 
            document.getElementById('network-flow-chart').offsetWidth > 0) {
            renderNetworkFlowChart(data.network_analysis);
        } else {
            setTimeout(() => renderNetworkFlowChart(data.network_analysis), 500);
        }
        
        // Render network communication heatmap
        if (document.getElementById('network-heatmap-chart') && 
            document.getElementById('network-heatmap-chart').offsetWidth > 0) {
            renderNetworkHeatmap(data.network_analysis);
        } else {
            setTimeout(() => renderNetworkHeatmap(data.network_analysis), 500);
        }

        // Render MB sent per protocol pie chart
        if (document.getElementById('mb-sent-per-protocol-chart') && 
            document.getElementById('mb-sent-per-protocol-chart').offsetWidth > 0) {
            renderMBSentPerProtocolChart(data.network_analysis);
        } else {
            setTimeout(() => renderMBSentPerProtocolChart(data.network_analysis), 500);
        }
        
        // Render MB transferred per protocol chart
        if (document.getElementById('mb-per-protocol-chart') && 
            document.getElementById('mb-per-protocol-chart').offsetWidth > 0) {
            renderMBPerProtocolChart(data.network_analysis);
        } else {
            setTimeout(() => renderMBPerProtocolChart(data.network_analysis), 500);
        }
        
        // Render MB received per protocol chart
        if (document.getElementById('mb-received-per-protocol-chart') && 
            document.getElementById('mb-received-per-protocol-chart').offsetWidth > 0) {
            renderMbReceivedPerProtocolChart(data.network_analysis);
        } else {
            setTimeout(() => renderMbReceivedPerProtocolChart(data.network_analysis), 500);
        }

        // Render connection tables
        renderConnectionTables(data.network_analysis);
    }, 200);
}

function updateNetworkIntensityBadge(networkAnalysis) {
    const badge = $('#network-intensity-badge');
    if (!networkAnalysis || !networkAnalysis.summary) {
        badge.text('No Data').removeClass().addClass('badge');
        return;
    }

    const intensity = networkAnalysis.summary.communication_intensity || 'LOW';
    badge.text(intensity)
         .removeClass()
         .addClass(`badge security-badge intensity-${intensity.toLowerCase()}`);
}

function renderNetworkSummary(data) {
    const summaryContainer = $('#network-summary');
    summaryContainer.empty();

    if (!data.network_analysis || !data.network_analysis.summary) {
        summaryContainer.html('<div class="col-12"><div class="alert alert-info">No network summary available</div></div>');
        return;
    }

    const summary = data.network_analysis.summary;
    const summaryCards = [
        {
            title: 'TCP Events',
            value: summary.total_tcp_events || 0,
            type: 'info',
            icon: 'fas fa-exchange-alt'
        },
        {
            title: 'UDP Events',
            value: summary.total_udp_events || 0,
            type: 'info',
            icon: 'fas fa-broadcast-tower'
        },
        {
            title: 'Socket Operations',
            value: summary.total_socket_operations || 0,
            type: 'success',
            icon: 'fas fa-plug'
        },
        {
            title: 'Protocols',
            value: summary.active_protocols ? summary.active_protocols.length : 0,
            type: 'warning',
            icon: 'fas fa-layer-group'
        }
    ];

    summaryCards.forEach(card => {
        summaryContainer.append(`
            <div class="col-md-3 mb-2">
                <div class="summary-card ${card.type}">
                    <div class="card-value">${card.value}</div>
                    <div class="card-label">${card.title}</div>
                </div>
            </div>
        `);
    });
}

function renderNetworkFlowChart(networkAnalysis) {
    if (!networkAnalysis || !networkAnalysis.flow_relationships) {
        $('#network-flow-chart').html('<div class="alert alert-info">No network flow data available</div>');
        return;
    }

    const flowData = networkAnalysis.flow_relationships;
    const flowKeys = Object.keys(flowData);
    
    if (flowKeys.length === 0) {
        $('#network-flow-chart').html('<div class="alert alert-info">No communication flows detected</div>');
        return;
    }

    // Clear previous chart
    d3.select('#network-flow-chart').html('');

    // Add zoom controls
    const controlsHtml = `
        <div class="chart-controls mb-2">
            <button class="btn btn-sm btn-outline-primary" id="flow-zoom-in" title="Zoom In">
                <i class="fas fa-search-plus"></i>
            </button>
            <button class="btn btn-sm btn-outline-primary" id="flow-zoom-out" title="Zoom Out">
                <i class="fas fa-search-minus"></i>
            </button>
            <button class="btn btn-sm btn-outline-secondary" id="flow-reset-zoom" title="Reset Zoom">
                <i class="fas fa-expand-arrows-alt"></i>
            </button>
            <button class="btn btn-sm btn-outline-info" id="flow-center" title="Center View">
                <i class="fas fa-crosshairs"></i>
            </button>
        </div>
    `;
    d3.select('#network-flow-chart').append('div').html(controlsHtml);

    // Set up dimensions
    const container = d3.select('#network-flow-chart');
    const containerWidth = container.node().getBoundingClientRect().width;
    const width = containerWidth - 40;
    const height = 280;

    // Create main SVG with zoom container
    const mainSvg = container
        .append('svg')
        .attr('width', width + 40)
        .attr('height', height + 20)
        .style('border', '1px solid #ddd')
        .style('border-radius', '4px');

    // Create zoom behavior
    const zoom = d3.zoom()
        .scaleExtent([0.3, 3])
        .on('zoom', function(event) {
            svg.attr('transform', event.transform);
        });

    // Apply zoom to main SVG
    mainSvg.call(zoom);

    // Create zoomable group
    const svg = mainSvg
        .append('g')
        .attr('transform', 'translate(20,10)');

    // Extract unique PIDs and create nodes
    const pids = new Set();
    const links = [];

    flowKeys.forEach(flowKey => {
        const flow = flowData[flowKey];
        pids.add(flow.from_pid);
        pids.add(flow.to_pid);
        
        links.push({
            source: flow.from_pid,
            target: flow.to_pid,
            count: flow.count,
            types: flow.types,
            flowKey: flowKey
        });
    });

    const nodes = Array.from(pids).map(pid => ({
        id: pid,
        pid: pid
    }));

    // Create force simulation
    const simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(100))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2));

    // Create arrow markers
    svg.append('defs').append('marker')
        .attr('id', 'arrowhead')
        .attr('viewBox', '-0 -5 10 10')
        .attr('refX', 13)
        .attr('refY', 0)
        .attr('orient', 'auto')
        .attr('markerWidth', 10)
        .attr('markerHeight', 10)
        .attr('xoverflow', 'visible')
        .append('svg:path')
        .attr('d', 'M 0,-5 L 10 ,0 L 0,5')
        .attr('fill', '#999')
        .style('stroke', 'none');

    // Create links
    const link = svg.append('g')
        .attr('class', 'links')
        .selectAll('line')
        .data(links)
        .enter().append('line')
        .attr('stroke', '#999')
        .attr('stroke-opacity', 0.6)
        .attr('stroke-width', d => Math.min(8, Math.max(1, d.count / 2)))
        .attr('marker-end', 'url(#arrowhead)');

    // Create nodes
    const node = svg.append('g')
        .attr('class', 'nodes')
        .selectAll('circle')
        .data(nodes)
        .enter().append('circle')
        .attr('r', 20)
        .attr('fill', '#69b3ff')
        .attr('stroke', '#333')
        .attr('stroke-width', 2)
        .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));

    // Add labels
    const labels = svg.append('g')
        .attr('class', 'labels')
        .selectAll('text')
        .data(nodes)
        .enter().append('text')
        .attr('text-anchor', 'middle')
        .attr('dy', '.35em')
        .attr('font-size', '10px')
        .attr('font-weight', 'bold')
        .attr('fill', 'white')
        .text(d => `PID ${d.pid}`);

    // Add tooltips
    node.on('mouseover', function(event, d) {
        const tooltip = d3.select('body').append('div')
            .attr('class', 'network-tooltip')
            .style('position', 'absolute')
            .style('background', 'rgba(0,0,0,0.8)')
            .style('color', 'white')
            .style('padding', '8px')
            .style('border-radius', '4px')
            .style('font-size', '12px')
            .style('pointer-events', 'none')
            .style('z-index', '1000');

        // Count incoming and outgoing connections
        const incoming = links.filter(l => l.target.id === d.id).length;
        const outgoing = links.filter(l => l.source.id === d.id).length;

        tooltip.html(`
            <strong>Process ID: ${d.pid}</strong><br>
            Incoming connections: ${incoming}<br>
            Outgoing connections: ${outgoing}
        `)
        .style('left', (event.pageX + 10) + 'px')
        .style('top', (event.pageY - 10) + 'px');
    })
    .on('mouseout', function() {
        d3.selectAll('.network-tooltip').remove();
    });

    // Add link tooltips
    link.on('mouseover', function(event, d) {
        const tooltip = d3.select('body').append('div')
            .attr('class', 'network-tooltip')
            .style('position', 'absolute')
            .style('background', 'rgba(0,0,0,0.8)')
            .style('color', 'white')
            .style('padding', '8px')
            .style('border-radius', '4px')
            .style('font-size', '12px')
            .style('pointer-events', 'none')
            .style('z-index', '1000');

        tooltip.html(`
            <strong>Communication Flow</strong><br>
            From PID: ${d.source.id}<br>
            To PID: ${d.target.id}<br>
            Messages: ${d.count}<br>
            Types: ${d.types.join(', ')}
        `)
        .style('left', (event.pageX + 10) + 'px')
        .style('top', (event.pageY - 10) + 'px');
    })
    .on('mouseout', function() {
        d3.selectAll('.network-tooltip').remove();
    });

    // Update positions on tick
    simulation.on('tick', () => {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);

        node
            .attr('cx', d => d.x)
            .attr('cy', d => d.y);

        labels
            .attr('x', d => d.x)
            .attr('y', d => d.y);
    });

    // Zoom control functions
    $('#flow-zoom-in').click(function() {
        mainSvg.transition().duration(300).call(
            zoom.scaleBy, 1.5
        );
    });

    $('#flow-zoom-out').click(function() {
        mainSvg.transition().duration(300).call(
            zoom.scaleBy, 1 / 1.5
        );
    });

    $('#flow-reset-zoom').click(function() {
        mainSvg.transition().duration(500).call(
            zoom.transform,
            d3.zoomIdentity.translate(0, 0).scale(1)
        );
    });

    $('#flow-center').click(function() {
        // Calculate bounds of all nodes
        const bounds = {
            minX: d3.min(nodes, d => d.x || 0),
            maxX: d3.max(nodes, d => d.x || 0),
            minY: d3.min(nodes, d => d.y || 0),
            maxY: d3.max(nodes, d => d.y || 0)
        };
        
        const centerX = (bounds.minX + bounds.maxX) / 2;
        const centerY = (bounds.minY + bounds.maxY) / 2;
        
        const targetX = (width / 2) - centerX;
        const targetY = (height / 2) - centerY;
        
        mainSvg.transition().duration(500).call(
            zoom.transform,
            d3.zoomIdentity.translate(targetX + 20, targetY + 10).scale(1)
        );
    });

    // Allow wheel zoom and pan
    mainSvg.on('wheel.zoom', null);  // Remove default wheel behavior first
    mainSvg.call(zoom);

    // Prevent zoom on double-click but allow it manually
    mainSvg.on('dblclick.zoom', null);

    // Drag functions
    function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
}

function renderMBSentPerProtocolChart(networkAnalysis) {
    if (!networkAnalysis) {
        $('#mb-sent-per-protocol-chart').html('<div class="alert alert-info">No network analysis data available</div>');
        return;
    }
    
    // Calculate data transfer from network events
    const data = calculateDataTransfer(networkAnalysis);
    
    // Create protocol distribution with MB sent
    const protocolData = [];
    
    if (data.tcp && data.tcp.sent_mb > 0) {
        protocolData.push({name: 'TCP', value: data.tcp.sent_mb, color: '#007bff'});
    }
    if (data.udp && data.udp.sent_mb > 0) {
        protocolData.push({name: 'UDP', value: data.udp.sent_mb, color: '#28a745'});
    }
    if (data.unix_stream && data.unix_stream.sent_mb > 0) {
        protocolData.push({name: 'Unix Stream', value: data.unix_stream.sent_mb, color: '#ffc107'});
    }
    if (data.unix_dgram && data.unix_dgram.sent_mb > 0) {
        protocolData.push({name: 'Unix Dgram', value: data.unix_dgram.sent_mb, color: '#dc3545'});
    }
    if (data.bluetooth && data.bluetooth.sent_mb > 0) {
        protocolData.push({name: 'Bluetooth', value: data.bluetooth.sent_mb, color: '#6f42c1'});
    }

    // If no data or all values are 0, show a message
    if (protocolData.length === 0) {
        // Check if we have any network events at all
        if (networkAnalysis.summary && 
            (networkAnalysis.summary.total_tcp_events > 0 || 
             networkAnalysis.summary.total_udp_events > 0 || 
             networkAnalysis.summary.total_unix_stream_events > 0 ||
             networkAnalysis.summary.total_unix_dgram_events > 0)) {
            // We have events but no calculated data transfer
            $('#mb-sent-per-protocol-chart').html('<div class="alert alert-info">Network activity detected but no data size information available</div>');
        } else {
            // No events at all
            $('#mb-sent-per-protocol-chart').html('<div class="alert alert-info">No network data sent detected</div>');
        }
        return;
    }

    // Clear previous chart
    d3.select('#mb-sent-per-protocol-chart').html('');

    // Create pie chart
    const width = 280;
    const height = 280;
    const radius = Math.min(width, height) / 2;

    const svg = d3.select('#mb-sent-per-protocol-chart')
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .append('g')
        .attr('transform', `translate(${width/2},${height/2})`);

    const pie = d3.pie()
        .value(d => d.value)
        .sort(null);

    const arc = d3.arc()
        .innerRadius(0)
        .outerRadius(radius - 10);

    const arcs = svg.selectAll('.arc')
        .data(pie(protocolData))
        .enter().append('g')
        .attr('class', 'arc');

    arcs.append('path')
        .attr('d', arc)
        .attr('fill', d => d.data.color)
        .attr('stroke', 'white')
        .attr('stroke-width', 2)
        .on('mouseover', function(event, d) {
            const tooltip = d3.select('body').append('div')
                .attr('class', 'protocol-tooltip')
                .style('position', 'absolute')
                .style('background', 'rgba(0,0,0,0.8)')
                .style('color', 'white')
                .style('padding', '8px')
                .style('border-radius', '4px')
                .style('font-size', '12px')
                .style('pointer-events', 'none')
                .style('z-index', '1000');

            const totalMB = d3.sum(protocolData, d => d.value);
            const percentage = ((d.data.value / totalMB) * 100).toFixed(1);
            
            tooltip.html(`
                <strong>${d.data.name}</strong><br>
                MB Sent: ${d.data.value.toFixed(2)} MB<br>
                Percentage: ${percentage}%
            `)
            .style('left', (event.pageX + 10) + 'px')
            .style('top', (event.pageY - 10) + 'px');
        })
        .on('mouseout', function() {
            d3.selectAll('.protocol-tooltip').remove();
        });

    // Add labels
    arcs.append('text')
        .attr('transform', d => `translate(${arc.centroid(d)})`)
        .attr('text-anchor', 'middle')
        .attr('font-size', '12px')
        .attr('font-weight', 'bold')
        .attr('fill', 'white')
        .text(d => d.data.value > 0 ? d.data.name : '');
}

function renderMBPerProtocolChart(networkAnalysis) {
    const container = d3.select('#mb-per-protocol-chart');
    container.selectAll('*').remove();
    
    if (!networkAnalysis) {
        container.append('div')
            .attr('class', 'alert alert-info')
            .text('No network analysis data available');
        return;
    }
    
    // Calculate data transfer from network events
    const data = calculateDataTransfer(networkAnalysis);
    const margin = {top: 20, right: 30, bottom: 40, left: 50};
    const width = 400 - margin.left - margin.right;
    const height = 280 - margin.top - margin.bottom;
    
    const svg = container.append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom);
        
    const g = svg.append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);
    
    // Prepare data for chart - group by protocol instead of sent/received
    const chartData = [];
    
    // Add TCP data if available
    if (data.tcp) {
        chartData.push({
            protocol: 'TCP', 
            sent: data.tcp.sent_mb || 0, 
            received: data.tcp.received_mb || 0,
            total: (data.tcp.sent_mb || 0) + (data.tcp.received_mb || 0),
            color: '#007bff'
        });
    }
    
    // Add UDP data if available
    if (data.udp) {
        chartData.push({
            protocol: 'UDP', 
            sent: data.udp.sent_mb || 0, 
            received: data.udp.received_mb || 0,
            total: (data.udp.sent_mb || 0) + (data.udp.received_mb || 0),
            color: '#28a745'
        });
    }
    
    // Add Unix Stream data if available
    if (data.unix_stream) {
        chartData.push({
            protocol: 'Unix Stream', 
            sent: data.unix_stream.sent_mb || 0, 
            received: data.unix_stream.received_mb || 0,
            total: (data.unix_stream.sent_mb || 0) + (data.unix_stream.received_mb || 0),
            color: '#ffc107'
        });
    }
    
    // Add Unix Datagram data if available
    if (data.unix_dgram) {
        chartData.push({
            protocol: 'Unix Dgram', 
            sent: data.unix_dgram.sent_mb || 0, 
            received: data.unix_dgram.received_mb || 0,
            total: (data.unix_dgram.sent_mb || 0) + (data.unix_dgram.received_mb || 0),
            color: '#dc3545'
        });
    }
    
    // Add Bluetooth data if available
    if (data.bluetooth) {
        chartData.push({
            protocol: 'Bluetooth', 
            sent: data.bluetooth.sent_mb || 0, 
            received: data.bluetooth.received_mb || 0,
            total: (data.bluetooth.sent_mb || 0) + (data.bluetooth.received_mb || 0),
            color: '#6f42c1'
        });
    }
    
    if (chartData.length === 0) {
        // Check if we have any network events at all
        if (networkAnalysis.summary && 
            (networkAnalysis.summary.total_tcp_events > 0 || 
             networkAnalysis.summary.total_udp_events > 0 || 
             networkAnalysis.summary.total_unix_stream_events > 0 ||
             networkAnalysis.summary.total_unix_dgram_events > 0)) {
            // We have events but no calculated data transfer
            container.append('div')
                .attr('class', 'alert alert-info')
                .text('Network activity detected but no data size information available');
        } else {
            // No events at all
            container.append('div')
                .attr('class', 'alert alert-info')
                .text('No protocol data transfer detected');
        }
        return;
    }
    
    // Sort by total MB transferred
    chartData.sort((a, b) => b.total - a.total);
    
    const maxValue = d3.max(chartData, d => Math.max(d.sent, d.received)) || 1;
    
    const xScale = d3.scaleBand()
        .domain(chartData.map(d => d.protocol))
        .range([0, width])
        .padding(0.2);
        
    const yScale = d3.scaleLinear()
        .domain([0, maxValue])
        .range([height, 0]);
    
    // Create a grouped bar chart
    const subgroups = ['sent', 'received'];
    const xSubgroup = d3.scaleBand()
        .domain(subgroups)
        .range([0, xScale.bandwidth()])
        .padding(0.05);
    
    const colors = {
        sent: '#007bff',
        received: '#17a2b8'
    };
    
    // Add grouped bars
    g.selectAll('.protocol-group')
        .data(chartData)
        .enter()
        .append('g')
        .attr('class', 'protocol-group')
        .attr('transform', d => `translate(${xScale(d.protocol)},0)`)
        .selectAll('rect')
        .data(d => subgroups.map(key => ({key: key, value: d[key], protocol: d.protocol})))
        .enter()
        .append('rect')
        .attr('x', d => xSubgroup(d.key))
        .attr('y', d => yScale(d.value))
        .attr('width', xSubgroup.bandwidth())
        .attr('height', d => height - yScale(d.value))
        .attr('fill', d => colors[d.key])
        .on('mouseover', function(event, d) {
            const tooltip = d3.select('body').append('div')
                .attr('class', 'protocol-tooltip')
                .style('position', 'absolute')
                .style('background', 'rgba(0,0,0,0.8)')
                .style('color', 'white')
                .style('padding', '8px')
                .style('border-radius', '4px')
                .style('font-size', '12px')
                .style('pointer-events', 'none')
                .style('z-index', '1000');
            
            tooltip.html(`
                <strong>${d.protocol}</strong><br>
                ${d.key === 'sent' ? 'Sent' : 'Received'}: ${d.value.toFixed(2)} MB
            `)
            .style('left', (event.pageX + 10) + 'px')
            .style('top', (event.pageY - 10) + 'px');
        })
        .on('mouseout', function() {
            d3.selectAll('.protocol-tooltip').remove();
        });
    
    // Add x axis
    g.append('g')
        .attr('transform', `translate(0,${height})`)
        .call(d3.axisBottom(xScale))
        .selectAll('text')
        .style('font-size', '10px')
        .style('text-anchor', 'end')
        .attr('dx', '-.8em')
        .attr('dy', '.15em')
        .attr('transform', 'rotate(-25)');
    
    // Add y axis
    g.append('g')
        .call(d3.axisLeft(yScale))
        .selectAll('text')
        .style('font-size', '10px');
        
    // Add y axis label
    g.append('text')
        .attr('transform', 'rotate(-90)')
        .attr('y', 0 - margin.left)
        .attr('x', 0 - (height / 2))
        .attr('dy', '1em')
        .style('text-anchor', 'middle')
        .style('font-size', '12px')
        .text('Data (MB)');
    
    // Add legend
    const legend = svg.append('g')
        .attr('transform', `translate(${width - 80}, 10)`);
    
    const legendItems = [
        {label: 'Sent', color: colors.sent},
        {label: 'Received', color: colors.received}
    ];
    
    legendItems.forEach((item, i) => {
        const legendRow = legend.append('g')
            .attr('transform', `translate(0, ${i * 20})`);
        
        legendRow.append('rect')
            .attr('width', 10)
            .attr('height', 10)
            .attr('fill', item.color);
        
        legendRow.append('text')
            .attr('x', 15)
            .attr('y', 10)
            .attr('text-anchor', 'start')
            .style('font-size', '12px')
            .text(item.label);
    });
}

// Calculate data transfer from network events
function calculateDataTransfer(networkAnalysis) {
    const result = {
        tcp: { sent_mb: 0, received_mb: 0 },
        udp: { sent_mb: 0, received_mb: 0 },
        unix_stream: { sent_mb: 0, received_mb: 0 },
        unix_dgram: { sent_mb: 0, received_mb: 0 },
        bluetooth: { sent_mb: 0, received_mb: 0 }
    };
    
    // Process TCP connections
    if (networkAnalysis.tcp_connections && networkAnalysis.tcp_connections.length > 0) {
        networkAnalysis.tcp_connections.forEach(conn => {
            // For TCP send events, use the 'size' field
            if (conn.direction === 'send') {
                // Convert bytes to MB
                const sizeMB = conn.size ? parseFloat(conn.size) / (1024 * 1024) : 0;
                result.tcp.sent_mb += sizeMB;
            } 
            // For TCP receive events, use the 'len' field
            else if (conn.direction === 'receive') {
                // Convert bytes to MB
                const sizeMB = conn.len ? parseFloat(conn.len) / (1024 * 1024) : 0;
                result.tcp.received_mb += sizeMB;
            }
        });
    }
    
    // Process UDP communications
    if (networkAnalysis.udp_communications && networkAnalysis.udp_communications.length > 0) {
        networkAnalysis.udp_communications.forEach(comm => {
            // UDP uses 'len' field for both send and receive
            const sizeMB = comm.len ? parseFloat(comm.len) / (1024 * 1024) : 0;
            
            if (comm.direction === 'send') {
                result.udp.sent_mb += sizeMB;
            } else if (comm.direction === 'receive') {
                result.udp.received_mb += sizeMB;
            }
        });
    }
    
    // Process Unix stream connections
    if (networkAnalysis.unix_stream_connections && networkAnalysis.unix_stream_connections.length > 0) {
        networkAnalysis.unix_stream_connections.forEach(conn => {
            // Unix stream doesn't have explicit size fields, check in details
            let sizeMB = 0;
            if (conn.details && conn.details.size) {
                sizeMB = parseFloat(conn.details.size) / (1024 * 1024);
            } else if (conn.details && conn.details.len) {
                sizeMB = parseFloat(conn.details.len) / (1024 * 1024);
            }
            
            if (conn.direction === 'send') {
                result.unix_stream.sent_mb += sizeMB;
            } else if (conn.direction === 'receive') {
                result.unix_stream.received_mb += sizeMB;
            }
        });
    }
    
    // Process Unix datagram communications
    if (networkAnalysis.unix_dgram_communications && networkAnalysis.unix_dgram_communications.length > 0) {
        networkAnalysis.unix_dgram_communications.forEach(comm => {
            // Unix datagram doesn't have explicit size fields, check in details
            let sizeMB = 0;
            if (comm.details && comm.details.size) {
                sizeMB = parseFloat(comm.details.size) / (1024 * 1024);
            } else if (comm.details && comm.details.len) {
                sizeMB = parseFloat(comm.details.len) / (1024 * 1024);
            }
            
            if (comm.direction === 'send') {
                result.unix_dgram.sent_mb += sizeMB;
            } else if (comm.direction === 'receive') {
                result.unix_dgram.received_mb += sizeMB;
            }
        });
    }
    
    // Process Bluetooth activity if available
    if (networkAnalysis.bluetooth_activity && networkAnalysis.bluetooth_activity.length > 0) {
        networkAnalysis.bluetooth_activity.forEach(activity => {
            // Check for size information in the bluetooth activity
            let sizeMB = 0;
            if (activity.details && activity.details.size) {
                sizeMB = parseFloat(activity.details.size) / (1024 * 1024);
            } else if (activity.details && activity.details.len) {
                sizeMB = parseFloat(activity.details.len) / (1024 * 1024);
            }
            
            if (activity.direction === 'send') {
                result.bluetooth.sent_mb += sizeMB;
            } else if (activity.direction === 'receive') {
                result.bluetooth.received_mb += sizeMB;
            }
        });
    }
    
    return result;
}

function renderMbReceivedPerProtocolChart(networkAnalysis) {
    const container = d3.select('#mb-received-per-protocol-chart');
    container.selectAll('*').remove();
    
    if (!networkAnalysis) {
        container.append('div')
            .attr('class', 'alert alert-info')
            .text('No network analysis data available');
        return;
    }
    
    // Calculate data transfer from network events
    const data = calculateDataTransfer(networkAnalysis);
    
    // Create protocol distribution with MB received
    const protocolData = [];
    
    if (data.tcp && data.tcp.received_mb > 0) {
        protocolData.push({name: 'TCP', value: data.tcp.received_mb, color: '#007bff'});
    }
    if (data.udp && data.udp.received_mb > 0) {
        protocolData.push({name: 'UDP', value: data.udp.received_mb, color: '#28a745'});
    }
    if (data.unix_stream && data.unix_stream.received_mb > 0) {
        protocolData.push({name: 'Unix Stream', value: data.unix_stream.received_mb, color: '#ffc107'});
    }
    if (data.unix_dgram && data.unix_dgram.received_mb > 0) {
        protocolData.push({name: 'Unix Dgram', value: data.unix_dgram.received_mb, color: '#dc3545'});
    }
    if (data.bluetooth && data.bluetooth.received_mb > 0) {
        protocolData.push({name: 'Bluetooth', value: data.bluetooth.received_mb, color: '#6f42c1'});
    }

    // If no data or all values are 0, show a message
    if (protocolData.length === 0) {
        // Check if we have any network events at all
        if (networkAnalysis.summary && 
            (networkAnalysis.summary.total_tcp_events > 0 || 
             networkAnalysis.summary.total_udp_events > 0 || 
             networkAnalysis.summary.total_unix_stream_events > 0 ||
             networkAnalysis.summary.total_unix_dgram_events > 0)) {
            // We have events but no calculated data transfer
            container.append('div')
                .attr('class', 'alert alert-info')
                .text('Network activity detected but no data size information available');
        } else {
            // No events at all
            container.append('div')
                .attr('class', 'alert alert-info')
                .text('No network data received detected');
        }
        return;
    }

    // Create pie chart
    const width = 280;
    const height = 280;
    const radius = Math.min(width, height) / 2;

    const svg = container.append('svg')
        .attr('width', width)
        .attr('height', height)
        .append('g')
        .attr('transform', `translate(${width/2},${height/2})`);

    const pie = d3.pie()
        .value(d => d.value)
        .sort(null);

    const arc = d3.arc()
        .innerRadius(0)
        .outerRadius(radius - 10);

    const arcs = svg.selectAll('.arc')
        .data(pie(protocolData))
        .enter().append('g')
        .attr('class', 'arc');

    arcs.append('path')
        .attr('d', arc)
        .attr('fill', d => d.data.color)
        .attr('stroke', 'white')
        .attr('stroke-width', 2)
        .on('mouseover', function(event, d) {
            const tooltip = d3.select('body').append('div')
                .attr('class', 'protocol-tooltip')
                .style('position', 'absolute')
                .style('background', 'rgba(0,0,0,0.8)')
                .style('color', 'white')
                .style('padding', '8px')
                .style('border-radius', '4px')
                .style('font-size', '12px')
                .style('pointer-events', 'none')
                .style('z-index', '1000');

            const totalMB = d3.sum(protocolData, d => d.value);
            const percentage = ((d.data.value / totalMB) * 100).toFixed(1);
            
            tooltip.html(`
                <strong>${d.data.name}</strong><br>
                MB Received: ${d.data.value.toFixed(2)} MB<br>
                Percentage: ${percentage}%
            `)
            .style('left', (event.pageX + 10) + 'px')
            .style('top', (event.pageY - 10) + 'px');
        })
        .on('mouseout', function() {
            d3.selectAll('.protocol-tooltip').remove();
        });

    // Add labels
    arcs.append('text')
        .attr('transform', d => `translate(${arc.centroid(d)})`)
        .attr('text-anchor', 'middle')
        .attr('font-size', '12px')
        .attr('font-weight', 'bold')
        .attr('fill', 'white')
        .text(d => d.data.value > 0 ? d.data.name : '');
}

function renderConnectionTables(networkAnalysis) {
    console.log('Rendering connection tables with data:', networkAnalysis);
    
    // 1. Render TCP connections table
    renderTcpConnections(networkAnalysis);
    
    // 2. Render UDP communications table 
    renderUdpCommunications(networkAnalysis);
}

function renderTcpConnections(networkAnalysis) {
    console.log('renderTcpConnections called with:', networkAnalysis);
    console.log('TCP connections data:', networkAnalysis?.tcp_connections);
    
    if (networkAnalysis && networkAnalysis.tcp_connections && networkAnalysis.tcp_connections.length > 0) {
        let tcpHtml = '<div class="table-responsive" style="max-height: 300px; overflow-y: auto;"><table class="table table-sm table-striped">';
        tcpHtml += '<thead class="table-dark sticky-top"><tr><th>Time</th><th>Direction</th><th>Source</th><th>Destination</th><th>Size</th><th>Process</th></tr></thead><tbody>';
        
        networkAnalysis.tcp_connections.forEach(conn => {
            const time = new Date(conn.timestamp * 1000).toLocaleTimeString();
            const directionIcon = conn.direction === 'send' ? '→' : (conn.direction === 'connect' ? '🔗' : '←');
            const directionBadge = conn.direction === 'send' ? 'bg-primary' : (conn.direction === 'connect' ? 'bg-warning' : 'bg-success');
            
            // Use readable IP addresses if available, fallback to raw IPs
            let srcIP = 'N/A';
            let dstIP = 'N/A';
            
            // Debug logging (only first connection)
            if (networkAnalysis.tcp_connections.indexOf(conn) === 0) {
                console.log('TCP Connection sample:', {
                    src_ip_readable: conn.src_ip_readable,
                    src_ip: conn.src_ip,
                    dst_ip_readable: conn.dst_ip_readable,
                    dst_ip: conn.dst_ip
                });
            }
            
            if (conn.src_ip_readable) {
                srcIP = conn.src_ip_readable;
            } else if (conn.src_ip !== undefined && conn.src_ip !== null) {
                srcIP = conn.src_ip.toString();
            }
            
            if (conn.dst_ip_readable) {
                dstIP = conn.dst_ip_readable;
            } else if (conn.dst_ip !== undefined && conn.dst_ip !== null) {
                dstIP = conn.dst_ip.toString();
            }
            const srcPort = conn.src_port || '';
            const dstPort = conn.dst_port || '';
            
            // Format source and destination with ports
            const source = srcPort ? `${srcIP}:${srcPort}` : srcIP;
            const destination = dstPort ? `${dstIP}:${dstPort}` : dstIP;
            
            // Use formatted size if available, fallback to raw size, or show "N/A" for connect events
            const sizeDisplay = conn.direction === 'connect' ? 'N/A' : (conn.size_formatted || conn.len_formatted || `${conn.size || conn.len || 0}B`);
            
            tcpHtml += `<tr>
                <td><small>${time}</small></td>
                <td><span class="badge ${directionBadge}">${directionIcon} ${conn.direction}</span></td>
                <td><small><code>${source}</code></small></td>
                <td><small><code>${destination}</code></small></td>
                <td><strong>${sizeDisplay}</strong></td>
                <td><small>${conn.process}</small></td>
            </tr>`;
        });
        
        tcpHtml += '</tbody></table></div>';
        tcpHtml += `<small class="text-muted mt-2 d-block">Total: ${networkAnalysis.tcp_connections.length} TCP connections</small>`;
        $('#tcp-connections-table').html(tcpHtml);
    } else {
        $('#tcp-connections-table').html('<div class="alert alert-info">No TCP connections found</div>');
    }
}

function renderUdpCommunications(networkAnalysis) {
    if (networkAnalysis && networkAnalysis.udp_communications && networkAnalysis.udp_communications.length > 0) {
        let udpHtml = '<div class="table-responsive" style="max-height: 300px; overflow-y: auto;"><table class="table table-sm table-striped">';
        udpHtml += '<thead class="table-dark sticky-top"><tr><th>Time</th><th>Direction</th><th>Source</th><th>Destination</th><th>Size</th><th>Process</th></tr></thead><tbody>';
        
        networkAnalysis.udp_communications.forEach(comm => {
            const time = new Date(comm.timestamp * 1000).toLocaleTimeString();
            const directionIcon = comm.direction === 'send' ? '→' : '←';
            const directionBadge = comm.direction === 'send' ? 'bg-warning' : 'bg-info';
            
            // Use readable IP addresses if available, fallback to raw IPs
            let srcIP = 'N/A';
            let dstIP = 'N/A';
            
            // Debug logging (only first communication)
            if (networkAnalysis.udp_communications.indexOf(comm) === 0) {
                console.log('UDP Communication sample:', {
                    src_ip_readable: comm.src_ip_readable,
                    src_ip: comm.src_ip,
                    dst_ip_readable: comm.dst_ip_readable,
                    dst_ip: comm.dst_ip
                });
            }
            
            if (comm.src_ip_readable) {
                srcIP = comm.src_ip_readable;
            } else if (comm.src_ip !== undefined && comm.src_ip !== null) {
                srcIP = comm.src_ip.toString();
            }
            
            if (comm.dst_ip_readable) {
                dstIP = comm.dst_ip_readable;
            } else if (comm.dst_ip !== undefined && comm.dst_ip !== null) {
                dstIP = comm.dst_ip.toString();
            }
            const srcPort = comm.src_port || '';
            const dstPort = comm.dst_port || '';
            
            // Format source and destination with ports
            const source = srcPort ? `${srcIP}:${srcPort}` : srcIP;
            const destination = dstPort ? `${dstIP}:${dstPort}` : dstIP;
            
            // Use formatted size if available, fallback to raw size
            const sizeDisplay = comm.len_formatted || `${comm.len || 0}B`;
            
            udpHtml += `<tr>
                <td><small>${time}</small></td>
                <td><span class="badge ${directionBadge}">${directionIcon} ${comm.direction}</span></td>
                <td><small><code>${source}</code></small></td>
                <td><small><code>${destination}</code></small></td>
                <td><strong>${sizeDisplay}</strong></td>
                <td><small>${comm.process}</small></td>
            </tr>`;
        });
        
        udpHtml += '</tbody></table></div>';
        udpHtml += `<small class="text-muted mt-2 d-block">Total: ${networkAnalysis.udp_communications.length} UDP communications</small>`;
        $('#udp-communications-table').html(udpHtml);
    } else {
        $('#udp-communications-table').html('<div class="alert alert-info">No UDP communications found</div>');
    }
}

function renderNetworkHeatmap(networkAnalysis) {
    if (!networkAnalysis) {
        $('#network-heatmap-chart').html('<div class="alert alert-info">No network analysis data available</div>');
        return;
    }
    
    // Prepare heatmap data from network events
    const heatmapData = prepareNetworkHeatmapData(networkAnalysis);
    
    if (heatmapData.length === 0) {
        $('#network-heatmap-chart').html('<div class="alert alert-info">No temporal network data available for heatmap</div>');
        return;
    }
    
    // Create the heatmap visualization
    createNetworkHeatmap('network-heatmap-chart', { heatmapData });
}

function prepareNetworkHeatmapData(networkAnalysis) {
    const heatmapData = [];
    
    // Get all network events with timestamps
    const allEvents = [];
    
    // Process TCP events
    if (networkAnalysis.tcp_connections && networkAnalysis.tcp_connections.length > 0) {
        networkAnalysis.tcp_connections.forEach(event => {
            if (event.timestamp) {
                allEvents.push({
                    timestamp: event.timestamp,
                    protocol: 'TCP',
                    direction: event.direction || 'unknown',
                    size: event.size || event.len || 0
                });
            }
        });
    }
    
    // Process UDP events
    if (networkAnalysis.udp_communications && networkAnalysis.udp_communications.length > 0) {
        networkAnalysis.udp_communications.forEach(event => {
            if (event.timestamp) {
                allEvents.push({
                    timestamp: event.timestamp,
                    protocol: 'UDP',
                    direction: event.direction || 'unknown',
                    size: event.len || 0
                });
            }
        });
    }
    
    // Process Unix Stream events
    if (networkAnalysis.unix_stream_connections && networkAnalysis.unix_stream_connections.length > 0) {
        networkAnalysis.unix_stream_connections.forEach(event => {
            if (event.timestamp) {
                allEvents.push({
                    timestamp: event.timestamp,
                    protocol: 'Unix Stream',
                    direction: event.direction || 'unknown',
                    size: (event.details && event.details.size) || 0
                });
            }
        });
    }
    
    // Process Unix Datagram events
    if (networkAnalysis.unix_dgram_communications && networkAnalysis.unix_dgram_communications.length > 0) {
        networkAnalysis.unix_dgram_communications.forEach(event => {
            if (event.timestamp) {
                allEvents.push({
                    timestamp: event.timestamp,
                    protocol: 'Unix Dgram',
                    direction: event.direction || 'unknown',
                    size: (event.details && event.details.size) || 0
                });
            }
        });
    }
    
    // If no events with timestamps, return empty array
    if (allEvents.length === 0) {
        return [];
    }
    
    // Sort events by timestamp
    allEvents.sort((a, b) => a.timestamp - b.timestamp);
    
    // Get start time (t=0)
    const startTime = allEvents[0].timestamp;
    
    // Group events by protocol and time buckets (1 second intervals)
    const timeGroups = {};
    const protocols = ['TCP', 'UDP', 'Unix Stream', 'Unix Dgram'];
    
    allEvents.forEach(event => {
        // Calculate time index (seconds from start)
        const timeIndex = Math.floor(event.timestamp - startTime);
        const timeKey = `${timeIndex}`;
        
        if (!timeGroups[timeKey]) {
            timeGroups[timeKey] = {
                'TCP': { count: 0, size: 0 },
                'UDP': { count: 0, size: 0 },
                'Unix Stream': { count: 0, size: 0 },
                'Unix Dgram': { count: 0, size: 0 }
            };
        }
        
        // Increment count and add size for this protocol and time bucket
        timeGroups[timeKey][event.protocol].count++;
        timeGroups[timeKey][event.protocol].size += parseFloat(event.size) || 0;
    });
    
    // Convert grouped data to heatmap format
    Object.keys(timeGroups).forEach(timeKey => {
        const timeIndex = parseInt(timeKey);
        
        protocols.forEach(protocol => {
            const count = timeGroups[timeKey][protocol].count;
            if (count > 0) {
                // Calculate intensity based on event count and data size
                const size = timeGroups[timeKey][protocol].size;
                // Normalize intensity: log scale to handle wide range of values
                const intensity = count > 0 ? Math.log10(count + 1) : 0;
                
                heatmapData.push({
                    timeIndex: timeIndex,
                    timeFormatted: `t=${timeIndex}s`,
                    protocol: protocol,
                    count: count,
                    size: size,
                    intensity: intensity
                });
            }
        });
    });
    
    return heatmapData;
}

function showNetworkError(error) {
    $('#network-error').html(`<strong>Error:</strong> ${error}`).show();
}

// Enhanced Process Analysis Functions
function loadProcessAnalysis() {
    let url = '/api/process-analysis';

    // Show loading
    $('#process-loading').show();
    $('#process-content').hide();
    $('#process-error').hide();

    $.getJSON(url, function(data) {
        if (data.error) {
            showProcessError(data.error);
        } else {
            processData = data;
            renderProcessAnalysis(data);
        }
    }).fail(function(jqXHR) {
        const errorMsg = jqXHR.responseJSON?.error || 'No process analysis data available';
        showProcessError(errorMsg);
    }).always(function() {
        $('#process-loading').hide();
    });
}

function renderProcessAnalysis(data) {
    $('#process-content').show();
    $('#process-error').hide();
    $('#process-loading').hide();

    // Wait for container to be fully visible before rendering charts
    setTimeout(() => {
        // Render summary cards
        renderProcessSummary(data);

        // Render process tree with container check
        if (document.getElementById('process-tree-chart') && 
            document.getElementById('process-tree-chart').offsetWidth > 0) {
            renderProcessTree(data.process_analysis);
        } else {
            setTimeout(() => renderProcessTree(data.process_analysis), 500);
        }

        // Render suspicious patterns
        renderSuspiciousPatterns(data.process_analysis);
    }, 200);
}

function renderProcessSummary(data) {
    const summaryContainer = $('#process-summary');
    summaryContainer.empty();

    if (!data.process_analysis || !data.process_analysis.summary) {
        summaryContainer.html('<div class="col-12"><div class="alert alert-info">No process summary available</div></div>');
        return;
    }

    const summary = data.process_analysis.summary;
    const summaryCards = [
        {
            title: 'Active Processes',
            value: summary.total_processes || 0,
            type: 'info',
            icon: 'fas fa-microchip'
        },
        {
            title: 'File Operations',
            value: summary.total_file_operations || 0,
            type: 'success',
            icon: 'fas fa-file'
        },
        {
            title: 'IPC Events',
            value: summary.total_ipc_events || 0,
            type: 'warning',
            icon: 'fas fa-exchange-alt'
        },
        {
            title: 'Suspicious Patterns',
            value: summary.suspicious_patterns ? summary.suspicious_patterns.length : 0,
            type: summary.suspicious_patterns && summary.suspicious_patterns.length > 0 ? 'danger' : 'success',
            icon: 'fas fa-exclamation-triangle'
        }
    ];

    summaryCards.forEach(card => {
        summaryContainer.append(`
            <div class="col-md-3 mb-2">
                <div class="summary-card ${card.type}">
                    <div class="card-value">${card.value}</div>
                    <div class="card-label">${card.title}</div>
                </div>
            </div>
        `);
    });
}

function renderProcessTree(processAnalysis) {
    if (!processAnalysis || !processAnalysis.process_tree) {
        $('#process-tree-chart').html('<div class="alert alert-info">No process tree data available</div>');
        return;
    }

    const processTree = processAnalysis.process_tree;
    const processKeys = Object.keys(processTree);
    
    if (processKeys.length === 0) {
        $('#process-tree-chart').html('<div class="alert alert-info">No process relationships detected</div>');
        return;
    }

    // Create a simple process list view with activity information
    let treeHtml = '<div class="process-tree-list" style="max-height: 350px; overflow-y: auto;">';
    treeHtml += '<div class="row"><div class="col-12">';
    treeHtml += '<h6><i class="fas fa-list"></i> Process Activity Summary</h6>';
    treeHtml += '</div></div>';
    
    // Sort processes by total events (most active first)
    const sortedProcesses = processKeys.sort((a, b) => {
        const eventsA = processTree[a].total_events || 0;
        const eventsB = processTree[b].total_events || 0;
        return eventsB - eventsA;
    });
    
    sortedProcesses.forEach(pid => {
        const process = processTree[pid];
        const duration = process.duration ? (process.duration / 1000).toFixed(2) + 's' : 'N/A';
        const partners = process.communication_partners ? process.communication_partners.length : 0;
        
        treeHtml += `
            <div class="process-item mb-2 p-2 border rounded">
                <div class="row">
                    <div class="col-md-6">
                        <strong>PID ${pid}</strong> - <small>${process.process_name || 'Unknown'}</small>
                    </div>
                    <div class="col-md-6 text-end">
                        <span class="badge bg-primary">${process.total_events || 0} events</span>
                        <span class="badge bg-info">${duration}</span>
                        ${partners > 0 ? `<span class="badge bg-warning">${partners} partners</span>` : ''}
                    </div>
                </div>
                ${process.children && process.children.length > 0 ? `
                    <div class="mt-1">
                        <small class="text-muted">Communicates with: ${process.children.map(c => `PID ${c.pid}`).join(', ')}</small>
                    </div>
                ` : ''}
            </div>
        `;
    });
    
    treeHtml += '</div>';
    $('#process-tree-chart').html(treeHtml);
}


function renderSuspiciousPatterns(processAnalysis) {
    const container = $('#process-suspicious-patterns');
    container.empty();

    if (!processAnalysis || !processAnalysis.summary || !processAnalysis.summary.suspicious_patterns) {
        container.html('<div class="alert alert-success"><i class="fas fa-check-circle"></i> No suspicious patterns detected</div>');
        return;
    }

    const patterns = processAnalysis.summary.suspicious_patterns;
    if (patterns.length === 0) {
        container.html('<div class="alert alert-success"><i class="fas fa-check-circle"></i> No suspicious patterns detected</div>');
        return;
    }

    const patternList = $('<div class="pattern-list" style="max-height: 300px; overflow-y: auto;"></div>');
    patterns.forEach(pattern => {
        patternList.append(`
            <div class="alert alert-warning alert-sm mb-2">
                <strong>${pattern.type}</strong><br>
                <small>${pattern.description}</small>
            </div>
        `);
    });

    container.append(patternList);
}

function showProcessError(error) {
    $('#process-error').html(`<strong>Error:</strong> ${error}`).show();
}

// Upload and UI functionality are now handled in separate files

// Make behavior timeline functions globally available for button event handlers
window.behaviorZoomIn = behaviorZoomIn;
window.behaviorZoomOut = behaviorZoomOut;
window.behaviorResetZoom = behaviorResetZoom;

// Note: DOM ready initialization is already handled above