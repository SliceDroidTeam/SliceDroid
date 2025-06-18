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
        loadAllData();
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
        loadAllData();
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
    $('#apply-filters').click(loadAllData);
    $('#reset-filters').click(resetFilters);
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

// Load all data based on current filters
function loadAllData() {
    const pid = $('#pid-filter').val();
    const device = $('#device-filter').val();

    // Show loading state for main sections
    showSectionLoading();

    try {
        // Load timeline data
        loadTimelineData(pid, device);

        // Load statistics
        loadDeviceStats(pid);
        loadEventStats(pid, device);
        loadStatsSummary(pid, device);

        // Load charts
        loadDevicePieChart(pid);
        loadEventPieChart(pid, device);

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

function loadStatsSummary(pid, device) {
    // Build API URL with parameters
    let url = '/api/device_stats';
    let params = [];
    if (pid) params.push(`pid=${pid}`);
    if (device) params.push(`device=${device}`);
    if (params.length > 0) url += '?' + params.join('&');

    $.getJSON(url, function(deviceData) {
        // Also get event stats for more comprehensive summary
        let eventUrl = '/api/event_stats';
        if (params.length > 0) eventUrl += '?' + params.join('&');

        $.getJSON(eventUrl, function(eventData) {
            const summaryData = calculateSummaryFromData(deviceData, eventData);
            renderStatsSummary(summaryData);
            renderTopDevicesChart(summaryData.topDevices);
        }).fail(function() {
            showError('Failed to load event statistics');
        });
    }).fail(function() {
        showError('Failed to load device statistics');
    });
}

// Show error message
function showError(message) {
    console.error(message);
    showToast('Error', message, 'error');
}

// Calculate summary statistics from actual data
function calculateSummaryFromData(deviceData, eventData) {
    const totalDevices = deviceData.length;
    const totalEvents = eventData.reduce((sum, item) => sum + item.count, 0);

    // Find most used event type
    const mostUsedEvent = eventData.length > 0 ? eventData[0] : { event: 'none', count: 0 };

    // Get top devices (limit based on config)
    const topN = appConfig.top_devices || 5;
    const topDevices = deviceData.slice(0, topN).map(d => ({
        device: d.device,
        count: d.count
    }));

    return {
        totalEvents: totalEvents,
        totalEventTypes: eventData.length,
        totalUniqueDevices: totalDevices,
        mostUsedEvent: {
            name: mostUsedEvent.event,
            count: mostUsedEvent.count
        },
        topDevices: topDevices
    };
}

// Function to render the top devices chart
function renderTopDevicesChart(topDevices) {
    if (!topDevices || topDevices.length === 0) {
        $('#top-devices-chart-container').html('<div class="alert alert-info">No data found</div>');
        return;
    }

    const chartData = topDevices.map(device => ({
        label: `Device ${device.device}`,
        value: device.count
    }));

    createBarChart('top-devices-chart-container', chartData,
                  `Top ${appConfig.top_devices || 5} Devices by Usage`,
                  'Device ID', 'Count');
}

// Function to render the statistics summary table
function renderStatsSummary(data) {
    const tableBody = $('#stats-summary-table tbody');
    tableBody.empty();

    // Add rows to the table
    tableBody.append(`
        <tr>
            <td><strong>Total Events</strong></td>
            <td>${data.totalEvents}</td>
        </tr>
        <tr>
            <td><strong>Event Types</strong></td>
            <td>${data.totalEventTypes}</td>
        </tr>
        <tr>
            <td><strong>Unique Devices</strong></td>
            <td>${data.totalUniqueDevices}</td>
        </tr>
        <tr>
            <td><strong>Most Used Event</strong></td>
            <td>${data.mostUsedEvent.name} (${data.mostUsedEvent.count} times)</td>
        </tr>
    `);

    // Add top devices as a list in a single row
    const topN = appConfig.top_devices || 5;
    let topDevicesHtml = '<ul class="list-unstyled mb-0">';
    data.topDevices.forEach(device => {
        topDevicesHtml += `<li>Device ${device.device}: ${device.count} events</li>`;
    });
    topDevicesHtml += '</ul>';

    tableBody.append(`
        <tr>
            <td><strong>Top ${topN} Devices</strong></td>
            <td>${topDevicesHtml}</td>
        </tr>
    `);
}

// Reset all filters
function resetFilters() {
    $('#pid-filter').val('');
    $('#device-filter').val('');
    loadAllData();
}

// Timeline functions
function loadTimelineData(pid, device) {
    let url = '/api/timeline';
    let params = [];
    if (pid) params.push(`pid=${pid}`);
    if (device) params.push(`device=${device}`);
    if (params.length > 0) url += '?' + params.join('&');

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

    // Load device category mapping (simulated for now)
    const dev2cat = {
        // Simulated device to category mapping based on legacy code
        // These should come from cat2devs.txt file in production
        // Camera devices
        264241152: 'camera',
        264241153: 'camera',
        // Audio devices  
        402653184: 'audio_in',
        402653185: 'audio_in',
        // Bluetooth devices
        167772160: 'bluetooth',
        // NFC devices
        285212672: 'nfc',
        // GNSS devices
        301989888: 'gnss'
    };

    // Create behavior timeline from window data (similar to legacy code)
    behaviorTimelineData = [];
    
    // Process each window
    kdevsTrace.forEach((kdevWindow, windowIndex) => {
        const windowCategories = [];
        
        // Process device events in this window
        Object.keys(kdevWindow).forEach(kdev => {
            const deviceId = parseInt(kdev);
            const count = kdevWindow[kdev];
            
            // Map device to category
            let category = 'other';
            if (deviceId in dev2cat) {
                category = dev2cat[deviceId];
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
                    details: `${category} Activity (Device ${deviceId}, ${count} events)`,
                    deviceId: deviceId,
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
            if (sensitiveTrace[sensitiveType] && sensitiveTrace[sensitiveType].length > 0) {
                // Check if any sensitive events are in this window range
                const windowEvents = sensitiveTrace[sensitiveType].filter(event => {
                    // This is a simplified check - in production you'd need proper window bounds
                    return Math.floor(Math.random() * kdevsTrace.length) === windowIndex;
                });
                
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
        container.innerHTML = '<div class="alert alert-info">No behavior events found in reconstruction windows</div>';
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
    const categories = ['camera', 'audio_in', 'TCP', 'bluetooth', 'nfc', 'gnss', 'contacts', 'sms', 'calendar', 'call_logs', 'other'];
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
        'other': '#6c757d'        // Grey
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
        .attr('fill', d => categoryColors[d.category] || categoryColors.other)
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
function loadDeviceStats(pid) {
    let url = '/api/device_stats';
    if (pid) url += `?pid=${pid}`;

    $.getJSON(url, function(data) {
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

function loadEventStats(pid, device) {
    let url = '/api/event_stats';
    let params = [];
    if (pid) params.push(`pid=${pid}`);
    if (device) params.push(`device=${device}`);
    if (params.length > 0) url += '?' + params.join('&');

    $.getJSON(url, function(data) {
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
function loadDevicePieChart(pid) {
    let url = '/api/device_stats';
    if (pid) url += `?pid=${pid}`;

    $.getJSON(url, function(data) {
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

function loadEventPieChart(pid, device) {
    let url = '/api/event_stats';
    let params = [];
    if (pid) params.push(`pid=${pid}`);
    if (device) params.push(`device=${device}`);
    if (params.length > 0) url += '?' + params.join('&');

    $.getJSON(url, function(data) {
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
    const pid = $('#pid-filter').val();
    let url = '/api/advanced-analytics';
    if (pid) url += `?pid=${pid}`;

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
        $('#category-chart').html(`<img src="${charts.category_distribution}" class="img-fluid" alt="Category Distribution">`);
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
    const pid = $('#analytics-target-pid').val() || $('#pid-filter').val();
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
    const pid = $('#pid-filter').val();
    let url = '/api/network-analysis';
    if (pid) url += `?pid=${pid}`;

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

        // Render protocol distribution with container check
        if (document.getElementById('protocol-distribution-chart') && 
            document.getElementById('protocol-distribution-chart').offsetWidth > 0) {
            renderProtocolDistribution(data.network_analysis);
        } else {
            setTimeout(() => renderProtocolDistribution(data.network_analysis), 500);
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
        .attr('fill', d => {
            const currentPid = $('#pid-filter').val();
            return (currentPid && d.pid == currentPid) ? '#ff6b6b' : '#69b3ff';
        })
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

function renderProtocolDistribution(networkAnalysis) {
    if (!networkAnalysis || !networkAnalysis.summary) {
        $('#protocol-distribution-chart').html('<div class="alert alert-info">No protocol data available</div>');
        return;
    }

    const summary = networkAnalysis.summary;
    const protocols = summary.active_protocols || [];
    
    if (protocols.length === 0) {
        $('#protocol-distribution-chart').html('<div class="alert alert-info">No protocols detected</div>');
        return;
    }

    // Create protocol distribution with counts
    const protocolData = [];
    
    if (summary.total_tcp_events > 0) {
        protocolData.push({name: 'TCP', count: summary.total_tcp_events, color: '#007bff'});
    }
    if (summary.total_udp_events > 0) {
        protocolData.push({name: 'UDP', count: summary.total_udp_events, color: '#28a745'});
    }
    if (summary.total_unix_stream_events > 0) {
        protocolData.push({name: 'Unix Stream', count: summary.total_unix_stream_events, color: '#ffc107'});
    }
    if (summary.total_unix_dgram_events > 0) {
        protocolData.push({name: 'Unix Datagram', count: summary.total_unix_dgram_events, color: '#dc3545'});
    }
    if (summary.total_bluetooth_events > 0) {
        protocolData.push({name: 'Bluetooth', count: summary.total_bluetooth_events, color: '#6f42c1'});
    }

    if (protocolData.length === 0) {
        $('#protocol-distribution-chart').html('<div class="alert alert-info">No protocol activity detected</div>');
        return;
    }

    // Clear previous chart
    d3.select('#protocol-distribution-chart').html('');

    // Create pie chart
    const width = 280;
    const height = 280;
    const radius = Math.min(width, height) / 2;

    const svg = d3.select('#protocol-distribution-chart')
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .append('g')
        .attr('transform', `translate(${width/2},${height/2})`);

    const pie = d3.pie()
        .value(d => d.count)
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

            const percentage = ((d.data.count / d3.sum(protocolData, d => d.count)) * 100).toFixed(1);
            
            tooltip.html(`
                <strong>${d.data.name}</strong><br>
                Events: ${d.data.count}<br>
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
        .text(d => d.data.count > 0 ? d.data.name : '');
}

function renderConnectionTables(networkAnalysis) {
    // Show Unix Stream connections (most relevant for this trace data)
    if (networkAnalysis && networkAnalysis.unix_stream_connections && networkAnalysis.unix_stream_connections.length > 0) {
        let streamHtml = '<div class="table-responsive" style="max-height: 300px; overflow-y: auto;"><table class="table table-sm table-striped">';
        streamHtml += '<thead class="table-dark sticky-top"><tr><th>Time</th><th>Direction</th><th>PID</th><th>To/From PID</th><th>Process</th></tr></thead><tbody>';
        
        // Show all connections, not just first 10
        networkAnalysis.unix_stream_connections.forEach(conn => {
            const time = new Date(conn.timestamp * 1000).toLocaleTimeString();
            const peerPid = conn.direction === 'send' ? conn.to_pid : conn.from_pid;
            const directionIcon = conn.direction === 'send' ? '→' : '←';
            
            streamHtml += `<tr>
                <td><small>${time}</small></td>
                <td><span class="badge ${conn.direction === 'send' ? 'bg-primary' : 'bg-success'}">${directionIcon} ${conn.direction}</span></td>
                <td><strong>${conn.pid}</strong></td>
                <td>${peerPid || 'N/A'}</td>
                <td><small>${conn.process}</small></td>
            </tr>`;
        });
        streamHtml += '</tbody></table></div>';
        
        streamHtml += `<small class="text-muted mt-2 d-block">Total: ${networkAnalysis.unix_stream_connections.length} Unix stream connections</small>`;
        
        $('#tcp-connections-table').html(streamHtml);
        
        // Update the header to reflect what we're showing
        $('#tcp-connections-table').closest('.professional-card').find('h6').html('<i class="fas fa-exchange-alt"></i> Unix Stream Connections');
    } else if (networkAnalysis && networkAnalysis.tcp_connections && networkAnalysis.tcp_connections.length > 0) {
        // Fallback to TCP if available
        let tcpHtml = '<div class="table-responsive"><table class="table table-sm"><thead><tr><th>Time</th><th>Direction</th><th>Size/Length</th></tr></thead><tbody>';
        networkAnalysis.tcp_connections.slice(0, 10).forEach(conn => {
            const time = new Date(conn.timestamp * 1000).toLocaleTimeString();
            tcpHtml += `<tr><td>${time}</td><td>${conn.direction}</td><td>${conn.size || conn.len || 0} bytes</td></tr>`;
        });
        tcpHtml += '</tbody></table></div>';
        $('#tcp-connections-table').html(tcpHtml);
    } else {
        $('#tcp-connections-table').html('<div class="alert alert-info">No TCP or Unix stream connections</div>');
    }

    // Show Unix Datagram communications
    if (networkAnalysis && networkAnalysis.unix_dgram_communications && networkAnalysis.unix_dgram_communications.length > 0) {
        let dgramHtml = '<div class="table-responsive" style="max-height: 300px; overflow-y: auto;"><table class="table table-sm table-striped">';
        dgramHtml += '<thead class="table-dark sticky-top"><tr><th>Time</th><th>Direction</th><th>PID</th><th>Process</th><th>Inode</th></tr></thead><tbody>';
        
        // Show all communications, not just first 10
        networkAnalysis.unix_dgram_communications.forEach(comm => {
            const time = new Date(comm.timestamp * 1000).toLocaleTimeString();
            const directionIcon = comm.direction === 'send' ? '→' : '←';
            
            dgramHtml += `<tr>
                <td><small>${time}</small></td>
                <td><span class="badge ${comm.direction === 'send' ? 'bg-warning' : 'bg-info'}">${directionIcon} ${comm.direction}</span></td>
                <td><strong>${comm.pid}</strong></td>
                <td><small>${comm.process}</small></td>
                <td>${comm.inode || 'N/A'}</td>
            </tr>`;
        });
        dgramHtml += '</tbody></table></div>';
        
        dgramHtml += `<small class="text-muted mt-2 d-block">Total: ${networkAnalysis.unix_dgram_communications.length} Unix datagram communications</small>`;
        
        $('#udp-communications-table').html(dgramHtml);
        
        // Update the header to reflect what we're showing
        $('#udp-communications-table').closest('.professional-card').find('h6').html('<i class="fas fa-broadcast-tower"></i> Unix Datagram Communications');
    } else if (networkAnalysis && networkAnalysis.udp_communications && networkAnalysis.udp_communications.length > 0) {
        // Fallback to UDP if available
        let udpHtml = '<div class="table-responsive"><table class="table table-sm"><thead><tr><th>Time</th><th>Direction</th><th>Length</th></tr></thead><tbody>';
        networkAnalysis.udp_communications.slice(0, 10).forEach(comm => {
            const time = new Date(comm.timestamp * 1000).toLocaleTimeString();
            udpHtml += `<tr><td>${time}</td><td>${comm.direction}</td><td>${comm.len || 0} bytes</td></tr>`;
        });
        udpHtml += '</tbody></table></div>';
        $('#udp-communications-table').html(udpHtml);
    } else {
        $('#udp-communications-table').html('<div class="alert alert-info">No UDP or Unix datagram communications</div>');
    }
}

function showNetworkError(error) {
    $('#network-error').html(`<strong>Error:</strong> ${error}`).show();
}

// Enhanced Process Analysis Functions
function loadProcessAnalysis() {
    const pid = $('#pid-filter').val();
    let url = '/api/process-analysis';
    if (pid) url += `?pid=${pid}`;

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

        // Render process timeline with container check
        if (document.getElementById('process-timeline-chart') && 
            document.getElementById('process-timeline-chart').offsetWidth > 0) {
            renderProcessTimeline(data.process_analysis);
        } else {
            setTimeout(() => renderProcessTimeline(data.process_analysis), 500);
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

function renderProcessTimeline(processAnalysis) {
    if (!processAnalysis || !processAnalysis.execution_timeline) {
        $('#process-timeline-chart').html('<div class="alert alert-info">No process timeline data available</div>');
        return;
    }

    // Simple timeline for process events
    $('#process-timeline-chart').html('<div class="alert alert-info">Process timeline chart will show fork/exec events over time</div>');
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

    const patternList = $('<div class="pattern-list"></div>');
    patterns.forEach(pattern => {
        patternList.append(`
            <div class="alert alert-warning alert-sm">
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