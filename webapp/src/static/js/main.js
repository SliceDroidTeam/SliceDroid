// Global variables
let timelineData = [];
let zoomLevel = 1;
let eventColors = {};
let appConfig = {};
let securityData = {};
let networkData = {};
let processData = {};

// DOM ready
$(document).ready(function() {
    updateAppStatus('loading', 'Loading...');

    // Load configuration first, then data
    loadConfiguration().then(function() {
        updateAppStatus('success', 'System Ready');
        loadAllData();
        setupEventListeners();
    }).catch(function(error) {
        console.error('Failed to load configuration:', error);
        updateAppStatus('warning', 'Fallback Mode');
        // Use fallback configuration
        setFallbackConfiguration();
        loadAllData();
        setupEventListeners();
    });
});

// Load app configuration from server
function loadConfiguration() {
    return $.getJSON('/api/config')
        .done(function(config) {
            appConfig = config;
            eventColors = config.event_categories || {};
            zoomLevel = config.default_zoom || 1;
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
        loadSecurityAnalysis();
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
        renderAnalyticsCharts(data.charts);

        // Render detailed insights
        renderDetailedInsights(data);

        showToast('Analysis Complete', 'Advanced analytics loaded successfully', 'success');
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

function renderAnalyticsCharts(charts) {
    if (!charts) return;

    // Render each chart
    if (charts.behavior_timeline) {
        $('#behavior-timeline-chart').html(`<img src="${charts.behavior_timeline}" class="img-fluid" alt="High-Level Behavior Timeline">`);
    } else {
        $('#behavior-timeline-chart').html('<div class="alert alert-info">No behavior timeline data available</div>');
    }

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

// Enhanced Security Analysis Functions
function loadSecurityAnalysis() {
    const pid = $('#pid-filter').val();
    let url = '/api/security-analysis';
    if (pid) url += `?pid=${pid}`;

    // Show loading
    $('#security-loading').show();
    $('#security-content').hide();
    $('#security-error').hide();

    $.getJSON(url, function(data) {
        if (data.error) {
            showSecurityError(data.error);
        } else {
            securityData = data;
            renderSecurityAnalysis(data);
        }
    }).fail(function(jqXHR) {
        const errorMsg = jqXHR.responseJSON?.error || 'No security analysis data available';
        showSecurityError(errorMsg);
    }).always(function() {
        $('#security-loading').hide();
    });
}

function renderSecurityAnalysis(data) {
    $('#security-content').show();

    // Update risk badge
    updateSecurityRiskBadge(data.risk_assessment);

    // Render summary cards
    renderSecuritySummary(data);

    // Render security timeline
    renderSecurityTimeline(data.timeline_data);

    // Render security events list
    renderSecurityEventsList(data.security_analysis);

    // Render recommendations
    renderSecurityRecommendations(data.recommendations);
}

function updateSecurityRiskBadge(riskAssessment) {
    const badge = $('#security-risk-badge');
    if (!riskAssessment) {
        badge.text('No Data').removeClass().addClass('badge');
        return;
    }

    const riskLevel = riskAssessment.risk_category || 'UNKNOWN';
    badge.text(riskLevel)
         .removeClass()
         .addClass(`badge security-badge risk-${riskLevel.toLowerCase()}`);
}

function renderSecuritySummary(data) {
    const summaryContainer = $('#security-summary');
    summaryContainer.empty();

    if (!data.security_analysis || !data.security_analysis.summary) {
        summaryContainer.html('<div class="col-12"><div class="alert alert-info">No security summary available</div></div>');
        return;
    }

    const summary = data.security_analysis.summary;
    const summaryCards = [
        {
            title: 'Privilege Escalations',
            value: summary.total_privilege_escalations || 0,
            type: summary.total_privilege_escalations > 0 ? 'danger' : 'success',
            icon: 'fas fa-user-shield'
        },
        {
            title: 'Debug Attempts',
            value: summary.total_debugging_attempts || 0,
            type: summary.total_debugging_attempts > 0 ? 'warning' : 'success',
            icon: 'fas fa-bug'
        },
        {
            title: 'Memory Changes',
            value: summary.total_memory_changes || 0,
            type: summary.total_memory_changes > 0 ? 'info' : 'success',
            icon: 'fas fa-memory'
        },
        {
            title: 'Suspicious Activities',
            value: summary.total_suspicious_activities || 0,
            type: summary.total_suspicious_activities > 0 ? 'danger' : 'success',
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

function renderSecurityTimeline(timelineData) {
    if (!timelineData || timelineData.length === 0) {
        $('#security-timeline-chart').html('<div class="alert alert-info">No security events found</div>');
        return;
    }

    // Create simple timeline chart
    const container = d3.select('#security-timeline-chart');
    container.html('');

    const margin = {top: 20, right: 20, bottom: 30, left: 50};
    const width = container.node().clientWidth - margin.left - margin.right;
    const height = 180;

    const svg = container.append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom)
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    // Filter security events
    const securityEvents = timelineData.filter(d => d.category === 'security');
    
    if (securityEvents.length === 0) {
        container.html('<div class="alert alert-info">No security events in timeline</div>');
        return;
    }

    // Create time scale
    const timeExtent = d3.extent(securityEvents, d => d.timestamp);
    const x = d3.scaleTime()
        .domain(timeExtent)
        .range([0, width]);

    // Create severity scale
    const y = d3.scaleOrdinal()
        .domain(['low', 'medium', 'high'])
        .range([height - 20, height/2, 20]);

    // Add dots for events
    svg.selectAll('.security-dot')
        .data(securityEvents)
        .enter()
        .append('circle')
        .attr('class', 'security-dot')
        .attr('cx', d => x(new Date(d.timestamp * 1000)))
        .attr('cy', d => y(d.severity || 'low'))
        .attr('r', 4)
        .attr('fill', d => d.severity === 'high' ? '#dc3545' : 
                          d.severity === 'medium' ? '#ffc107' : '#28a745')
        .on('mouseover', function(event, d) {
            showSecurityTooltip(event, d);
        })
        .on('mouseout', hideSecurityTooltip);

    // Add axes
    svg.append('g')
        .attr('transform', `translate(0,${height})`)
        .call(d3.axisBottom(x).ticks(5));

    svg.append('g')
        .call(d3.axisLeft(y));
}

function renderSecurityEventsList(securityAnalysis) {
    const container = $('#security-events-list');
    container.empty();

    if (!securityAnalysis) {
        container.html('<div class="alert alert-info">No security events available</div>');
        return;
    }

    const events = [
        ...(securityAnalysis.privilege_escalation || []),
        ...(securityAnalysis.debugging_attempts || []),
        ...(securityAnalysis.suspicious_activity || [])
    ];

    if (events.length === 0) {
        container.html('<div class="alert alert-success"><i class="fas fa-check-circle"></i> No security issues detected</div>');
        return;
    }

    const eventList = $('<div class="event-list"></div>');
    events.slice(0, 10).forEach(event => {
        const timestamp = new Date(event.timestamp * 1000).toLocaleString();
        const severity = event.type === 'setuid_root' ? 'high' : 'medium';
        
        eventList.append(`
            <div class="event-item event-severity-${severity}">
                <div class="event-timestamp">${timestamp}</div>
                <div class="event-description">${event.type}: ${event.process || 'Unknown'}</div>
            </div>
        `);
    });

    container.append(eventList);
}

function renderSecurityRecommendations(recommendations) {
    const container = $('#security-recommendations');
    container.empty();

    if (!recommendations || recommendations.length === 0) {
        container.html('<div class="alert alert-success"><i class="fas fa-thumbs-up"></i> No security recommendations at this time</div>');
        return;
    }

    const recList = $('<div class="recommendations-list"></div>');
    recommendations.forEach(rec => {
        const priorityClass = rec.priority === 'HIGH' ? 'danger' : 
                             rec.priority === 'MEDIUM' ? 'warning' : 'info';
        
        recList.append(`
            <div class="alert alert-${priorityClass} alert-sm">
                <strong>${rec.title}</strong><br>
                <small>${rec.description}</small>
            </div>
        `);
    });

    container.append(recList);
}

function showSecurityError(error) {
    $('#security-error').html(`<strong>Error:</strong> ${error}`).show();
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

    // Update intensity badge
    updateNetworkIntensityBadge(data.network_analysis);

    // Render summary cards
    renderNetworkSummary(data);

    // Render network flow chart
    renderNetworkFlowChart(data.network_analysis);

    // Render protocol distribution
    renderProtocolDistribution(data.network_analysis);

    // Render connection tables
    renderConnectionTables(data.network_analysis);
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
    if (!networkAnalysis) {
        $('#network-flow-chart').html('<div class="alert alert-info">No network flow data available</div>');
        return;
    }

    // Simple network activity chart
    $('#network-flow-chart').html('<div class="alert alert-info">Network flow visualization will be implemented with D3.js</div>');
}

function renderProtocolDistribution(networkAnalysis) {
    if (!networkAnalysis || !networkAnalysis.summary) {
        $('#protocol-distribution-chart').html('<div class="alert alert-info">No protocol data available</div>');
        return;
    }

    const protocols = networkAnalysis.summary.active_protocols || [];
    if (protocols.length === 0) {
        $('#protocol-distribution-chart').html('<div class="alert alert-info">No protocols detected</div>');
        return;
    }

    // Create simple protocol list for now
    let protocolHtml = '<ul class="list-group">';
    protocols.forEach(protocol => {
        protocolHtml += `<li class="list-group-item">${protocol}</li>`;
    });
    protocolHtml += '</ul>';

    $('#protocol-distribution-chart').html(protocolHtml);
}

function renderConnectionTables(networkAnalysis) {
    // TCP connections
    if (networkAnalysis && networkAnalysis.tcp_connections && networkAnalysis.tcp_connections.length > 0) {
        let tcpHtml = '<div class="table-responsive"><table class="table table-sm"><thead><tr><th>Time</th><th>Direction</th><th>Size/Length</th></tr></thead><tbody>';
        networkAnalysis.tcp_connections.slice(0, 10).forEach(conn => {
            const time = new Date(conn.timestamp * 1000).toLocaleTimeString();
            tcpHtml += `<tr><td>${time}</td><td>${conn.direction}</td><td>${conn.size || conn.len || 0} bytes</td></tr>`;
        });
        tcpHtml += '</tbody></table></div>';
        $('#tcp-connections-table').html(tcpHtml);
    } else {
        $('#tcp-connections-table').html('<div class="alert alert-info">No TCP connections</div>');
    }

    // UDP communications
    if (networkAnalysis && networkAnalysis.udp_communications && networkAnalysis.udp_communications.length > 0) {
        let udpHtml = '<div class="table-responsive"><table class="table table-sm"><thead><tr><th>Time</th><th>Direction</th><th>Length</th></tr></thead><tbody>';
        networkAnalysis.udp_communications.slice(0, 10).forEach(comm => {
            const time = new Date(comm.timestamp * 1000).toLocaleTimeString();
            udpHtml += `<tr><td>${time}</td><td>${comm.direction}</td><td>${comm.len || 0} bytes</td></tr>`;
        });
        udpHtml += '</tbody></table></div>';
        $('#udp-communications-table').html(udpHtml);
    } else {
        $('#udp-communications-table').html('<div class="alert alert-info">No UDP communications</div>');
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

    // Render summary cards
    renderProcessSummary(data);

    // Render process tree
    renderProcessTree(data.process_analysis);

    // Render process timeline
    renderProcessTimeline(data.process_analysis);

    // Render suspicious patterns
    renderSuspiciousPatterns(data.process_analysis);
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
            title: 'Process Forks',
            value: summary.total_forks || 0,
            type: 'info',
            icon: 'fas fa-code-branch'
        },
        {
            title: 'Executions',
            value: summary.total_execs || 0,
            type: 'success',
            icon: 'fas fa-play'
        },
        {
            title: 'Tree Depth',
            value: summary.process_tree_depth || 0,
            type: 'warning',
            icon: 'fas fa-sitemap'
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

    // Placeholder for process tree visualization
    $('#process-tree-chart').html('<div class="alert alert-info">Process tree visualization will be implemented with D3.js hierarchical layout</div>');
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

// Initialize all functionality when DOM is ready
$(document).ready(function() {
    // Initialize UI first
    initializeUI();
    
    // App initialization
    updateAppStatus('loading', 'Loading...');

    // Load configuration first, then data
    loadConfiguration().then(function() {
        updateAppStatus('success', 'System Ready');
        loadAllData();
        setupEventListeners();
        
        // Initialize upload functionality
        initializeUploadFunctionality();
    }).catch(function(error) {
        console.error('Failed to load configuration:', error);
        updateAppStatus('warning', 'Fallback Mode');
        // Use fallback configuration
        setFallbackConfiguration();
        loadAllData();
        setupEventListeners();
        
        // Initialize upload functionality
        initializeUploadFunctionality();
    });
});