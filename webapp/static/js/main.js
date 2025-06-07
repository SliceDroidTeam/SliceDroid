// Global variables
let timelineData = [];
let zoomLevel = 1;
let eventColors = {};
let appConfig = {};

// DOM ready
$(document).ready(function() {
    updateAppStatus('loading', 'Loading...');
    
    // Load configuration first, then data
    loadConfiguration().then(function() {
        updateAppStatus('success', 'Ready');
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
        'loading': 'bg-info',
        'success': 'bg-success',
        'warning': 'bg-warning',
        'error': 'bg-danger'
    };
    
    statusEl.removeClass('bg-success bg-warning bg-danger bg-info')
           .addClass(classMap[type] || 'bg-secondary');
    statusEl.html(`<i class="${iconMap[type] || 'fas fa-question'}"></i> ${message}`);
}

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
    
    // Upload functionality
    $('#trace-file-input').change(handleFileSelection);
    $('#upload-btn').click(handleUpload);
    
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

// Upload functionality
function handleFileSelection() {
    const fileInput = $('#trace-file-input')[0];
    const uploadBtn = $('#upload-btn');
    
    if (fileInput.files.length > 0) {
        const file = fileInput.files[0];
        if (file.name.endsWith('.trace')) {
            uploadBtn.prop('disabled', false);
            hideUploadResult();
        } else {
            uploadBtn.prop('disabled', true);
            showUploadError('Please select a .trace file');
        }
    } else {
        uploadBtn.prop('disabled', true);
    }
}

function handleUpload() {
    const fileInput = $('#trace-file-input')[0];
    
    if (fileInput.files.length === 0) {
        showUploadError('Please select a file');
        return;
    }
    
    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('trace_file', file);
    
    // Show progress
    showUploadProgress();
    $('#upload-btn').prop('disabled', true);
    
    // Upload file
    $.ajax({
        url: '/api/upload',
        type: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            if (response.upload_id) {
                checkUploadProgress(response.upload_id);
            } else {
                showUploadError('Upload failed: No upload ID received');
                resetUploadUI();
            }
        },
        error: function(xhr) {
            const error = xhr.responseJSON?.error || 'Upload failed';
            showUploadError(error);
            resetUploadUI();
        }
    });
}

function checkUploadProgress(uploadId) {
    const checkProgress = () => {
        $.get(`/api/upload/progress/${uploadId}`)
            .done(function(data) {
                updateProgressBar(data.progress);
                updateProgressStatus(data.status);
                
                if (data.completed) {
                    if (data.error) {
                        showUploadError(data.error);
                    } else if (data.result && data.result.success) {
                        showUploadSuccess(data.result);
                        // Reload data after successful processing
                        setTimeout(() => {
                            loadAllData();
                        }, 1000);
                    } else {
                        showUploadError(data.result?.error || 'Processing failed');
                    }
                    resetUploadUI();
                } else {
                    // Continue checking progress
                    setTimeout(checkProgress, 1000);
                }
            })
            .fail(function() {
                showUploadError('Failed to check upload progress');
                resetUploadUI();
            });
    };
    
    checkProgress();
}

function showUploadProgress() {
    $('#upload-progress').show();
    $('#upload-result').hide();
    updateProgressBar(0);
    updateProgressStatus('Starting upload...');
}

function updateProgressBar(progress) {
    $('#progress-bar').css('width', progress + '%').attr('aria-valuenow', progress);
}

function updateProgressStatus(status) {
    $('#upload-status').text(status);
}

function showUploadSuccess(result) {
    $('#upload-progress').hide();
    $('#upload-result').show();
    $('#upload-alert')
        .removeClass('alert-danger')
        .addClass('alert-success')
        .html(`
            <strong>Success!</strong> ${result.message}<br>
            <small>
                Events processed: ${result.events_count}<br>
                Target PID: ${result.target_pid}<br>
                Output file: ${result.json_file}
            </small>
        `);
}

function showUploadError(error) {
    $('#upload-progress').hide();
    $('#upload-result').show();
    $('#upload-alert')
        .removeClass('alert-success')
        .addClass('alert-danger')
        .html(`<strong>Error:</strong> ${error}`);
}

function hideUploadResult() {
    $('#upload-result').hide();
}

function resetUploadUI() {
    $('#upload-btn').prop('disabled', false);
    $('#trace-file-input').val('');
    $('#upload-btn').prop('disabled', true);
}

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
        updateAppStatus('success', 'Ready');
    });
}

// Comprehensive Analysis functionality
function runComprehensiveAnalysis() {
    const windowSize = $('#window-size').val();
    const overlap = $('#overlap-size').val();
    const asynchronous = $('#asynchronous-analysis').val();
    const targetPid = $('#analysis-target-pid').val();
    
    // Validation
    if (parseInt(overlap) >= parseInt(windowSize)) {
        showToast('Parameter Error', 'Overlap must be less than window size', 'error');
        return;
    }
    
    updateAppStatus('loading', 'Running Analysis...');
    
    // Show loading
    $('#comprehensive-loading').show();
    $('#comprehensive-error').hide();
    $('#comprehensive-analysis-btn').prop('disabled', true);
    
    // Build parameters
    let params = [];
    if (targetPid) params.push(`pid=${targetPid}`);
    if (windowSize) params.push(`window_size=${windowSize}`);
    if (overlap) params.push(`overlap=${overlap}`);
    params.push(`asynchronous=${asynchronous}`);
    
    const url = `/api/comprehensive-analysis?${params.join('&')}`;
    
    $.getJSON(url, function(data) {
        if (data.error) {
            showComprehensiveError(data.error);
        } else {
            renderComprehensiveResults(data);
        }
    }).fail(function(jqXHR) {
        const errorMsg = jqXHR.responseJSON?.error || 'Failed to run comprehensive analysis';
        showComprehensiveError(errorMsg);
    }).always(function() {
        $('#comprehensive-loading').hide();
        $('#comprehensive-analysis-btn').prop('disabled', false);
        updateAppStatus('success', 'Ready');
    });
    
    // Also load API instances and event slicing in parallel
    loadApiInstances(targetPid);
    loadEventSlicing(targetPid, asynchronous);
}

function renderComprehensiveResults(data) {
    // Render comprehensive statistics
    const statsContainer = $('#comprehensive-stats-content');
    statsContainer.html(generateComprehensiveStatsHTML(data));
}

function generateComprehensiveStatsHTML(data) {
    const stats = data.comprehensive_stats;
    const params = data.parameters;
    
    let html = `
        <div class="row mb-4">
            <div class="col-md-12">
                <div class="alert alert-success">
                    <h5><i class="fas fa-check-circle"></i> Analysis Complete</h5>
                    <p><strong>Target PID:</strong> ${data.target_pid}</p>
                    <p><strong>Parameters:</strong> Window Size: ${params.window_size}, Overlap: ${params.overlap}, Type: ${params.asynchronous ? 'Asynchronous' : 'Synchronous'}</p>
                </div>
            </div>
        </div>
        
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h3 class="text-primary">${stats.total_windows}</h3>
                        <small class="text-muted">Analysis Windows</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h3 class="text-success">${stats.events_processed.toLocaleString()}</h3>
                        <small class="text-muted">Events Processed</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h3 class="text-info">${stats.total_devices}</h3>
                        <small class="text-muted">Unique Devices</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h3 class="text-warning">${stats.total_categories}</h3>
                        <small class="text-muted">Device Categories</small>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    if (stats.most_used_category && stats.most_used_category.name) {
        html += `
            <div class="row mb-4">
                <div class="col-md-12">
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="fas fa-trophy"></i> Most Used Category</h5>
                        </div>
                        <div class="card-body">
                            <h4 class="text-primary">${stats.most_used_category.name}</h4>
                            <p>Used in <strong>${stats.most_used_category.count}</strong> analysis windows</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    if (stats.top_devices && stats.top_devices.length > 0) {
        html += `
            <div class="row mb-4">
                <div class="col-md-12">
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="fas fa-list"></i> Top Devices</h5>
                        </div>
                        <div class="card-body">
                            <div class="table-responsive">
                                <table class="table table-striped">
                                    <thead>
                                        <tr>
                                            <th>Device ID</th>
                                            <th>Windows</th>
                                            <th>Usage</th>
                                        </tr>
                                    </thead>
                                    <tbody>
        `;
        
        stats.top_devices.slice(0, 10).forEach(([device, count]) => {
            const percentage = ((count / stats.total_windows) * 100).toFixed(1);
            html += `
                <tr>
                    <td><code>${device}</code></td>
                    <td><span class="badge bg-primary">${count}</span></td>
                    <td>
                        <div class="progress" style="width: 100px;">
                            <div class="progress-bar" style="width: ${percentage}%"></div>
                        </div>
                        <small>${percentage}%</small>
                    </td>
                </tr>
            `;
        });
        
        html += `
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    return html;
}

function loadApiInstances(targetPid) {
    let url = '/api/api-instances';
    if (targetPid) url += `?pid=${targetPid}`;
    
    $.getJSON(url, function(data) {
        if (data.error) {
            $('#api-instances-content').html(`<div class="alert alert-danger">Error: ${data.error}</div>`);
        } else {
            renderApiInstances(data);
        }
    }).fail(function(jqXHR) {
        const errorMsg = jqXHR.responseJSON?.error || 'Failed to load API instances';
        $('#api-instances-content').html(`<div class="alert alert-danger">Error: ${errorMsg}</div>`);
    });
}

function renderApiInstances(data) {
    const container = $('#api-instances-content');
    
    if (!data.api_instances || Object.keys(data.api_instances).length === 0) {
        container.html('<div class="alert alert-info">No API instances found</div>');
        return;
    }
    
    let html = `
        <div class="row mb-3">
            <div class="col-md-12">
                <div class="alert alert-info">
                    <strong>Target PID:</strong> ${data.target_pid || 'All'}<br>
                    <strong>API Types Found:</strong> ${Object.keys(data.api_instances).length}<br>
                    <strong>Relevant APIs:</strong> ${data.relevant_apis.length}
                </div>
            </div>
        </div>
        
        <div class="accordion" id="apiInstancesAccordion">
    `;
    
    Object.entries(data.api_instances).forEach(([apiCode, instances], index) => {
        const isRelevant = data.relevant_apis.includes(parseInt(apiCode));
        const badgeClass = isRelevant ? 'bg-success' : 'bg-secondary';
        
        html += `
            <div class="accordion-item">
                <h2 class="accordion-header">
                    <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" 
                            data-bs-target="#apiCollapse${index}" aria-expanded="false">
                        API ${apiCode} <span class="badge ${badgeClass} ms-2">${instances.length} instances</span>
                        ${isRelevant ? '<i class="fas fa-star text-warning ms-2" title="Relevant to target PID"></i>' : ''}
                    </button>
                </h2>
                <div id="apiCollapse${index}" class="accordion-collapse collapse" data-bs-parent="#apiInstancesAccordion">
                    <div class="accordion-body">
                        <p><strong>Total Instances:</strong> ${instances.length}</p>
                        <div class="table-responsive">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>Instance</th>
                                        <th>Start Index</th>
                                        <th>End Index</th>
                                        <th>Duration</th>
                                    </tr>
                                </thead>
                                <tbody>
        `;
        
        instances.slice(0, 20).forEach((instance, idx) => {
            const duration = instance[1] - instance[0];
            html += `
                <tr>
                    <td>${idx + 1}</td>
                    <td><code>${instance[0]}</code></td>
                    <td><code>${instance[1]}</code></td>
                    <td><span class="badge bg-info">${duration} events</span></td>
                </tr>
            `;
        });
        
        if (instances.length > 20) {
            html += `<tr><td colspan="4" class="text-muted text-center">... and ${instances.length - 20} more instances</td></tr>`;
        }
        
        html += `
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.html(html);
}

function loadEventSlicing(targetPid, asynchronous) {
    if (!targetPid) {
        $('#event-slicing-content').html('<div class="alert alert-warning">Please select a target PID for event slicing</div>');
        return;
    }
    
    const url = `/api/event-slicing?pid=${targetPid}&asynchronous=${asynchronous}`;
    
    $.getJSON(url, function(data) {
        if (data.error) {
            $('#event-slicing-content').html(`<div class="alert alert-danger">Error: ${data.error}</div>`);
        } else {
            renderEventSlicing(data);
        }
    }).fail(function(jqXHR) {
        const errorMsg = jqXHR.responseJSON?.error || 'Failed to load event slicing';
        $('#event-slicing-content').html(`<div class="alert alert-danger">Error: ${errorMsg}</div>`);
    });
}

function renderEventSlicing(data) {
    const container = $('#event-slicing-content');
    const reductionPercentage = ((1 - data.sliced_events_count / data.original_events_count) * 100).toFixed(1);
    
    let html = `
        <div class="row mb-3">
            <div class="col-md-12">
                <div class="alert alert-success">
                    <h5><i class="fas fa-cut"></i> Event Slicing Results</h5>
                    <p><strong>Target PID:</strong> ${data.target_pid}</p>
                    <p><strong>Analysis Type:</strong> ${data.parameters.asynchronous ? 'Asynchronous' : 'Synchronous'}</p>
                </div>
            </div>
        </div>
        
        <div class="row mb-4">
            <div class="col-md-4">
                <div class="card text-center">
                    <div class="card-body">
                        <h3 class="text-info">${data.original_events_count.toLocaleString()}</h3>
                        <small class="text-muted">Original Events</small>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card text-center">
                    <div class="card-body">
                        <h3 class="text-success">${data.sliced_events_count.toLocaleString()}</h3>
                        <small class="text-muted">Relevant Events</small>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card text-center">
                    <div class="card-body">
                        <h3 class="text-warning">${reductionPercentage}%</h3>
                        <small class="text-muted">Reduction</small>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    if (data.sliced_events && data.sliced_events.length > 0) {
        html += `
            <div class="row">
                <div class="col-md-12">
                    <div class="card">
                        <div class="card-header">
                            <h5><i class="fas fa-list"></i> Relevant Events (First ${Math.min(data.sliced_events.length, 1000)})</h5>
                        </div>
                        <div class="card-body">
                            <div class="table-responsive" style="max-height: 400px;">
                                <table class="table table-sm table-striped">
                                    <thead class="sticky-top bg-white">
                                        <tr>
                                            <th>Event</th>
                                            <th>Pathname</th>
                                            <th>Details</th>
                                        </tr>
                                    </thead>
                                    <tbody>
        `;
        
        data.sliced_events.slice(0, 100).forEach(event => {
            const pathname = event.details?.pathname || '-';
            const detailsText = JSON.stringify(event.details || {}).substring(0, 100) + '...';
            
            html += `
                <tr>
                    <td><code>${event.event}</code></td>
                    <td><small>${pathname}</small></td>
                    <td><small class="text-muted">${detailsText}</small></td>
                </tr>
            `;
        });
        
        if (data.sliced_events.length > 100) {
            html += `<tr><td colspan="3" class="text-muted text-center">... and ${data.sliced_events.length - 100} more events</td></tr>`;
        }
        
        html += `
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    container.html(html);
}

function showComprehensiveError(error) {
    $('#comprehensive-error').html(`<strong>Error:</strong> ${error}`).show();
}

function exportDeveloperAnalysis(format) {
    const windowSize = $('#window-size').val() || 5000;
    const overlap = $('#overlap-size').val() || 1000;
    const asynchronous = $('#asynchronous-analysis').val() || 'true';
    const targetPid = $('#analysis-target-pid').val() || $('#pid-filter').val();
    
    // Use the comprehensive analysis export endpoint with developer parameters
    exportAnalysis(format);
    
    showToast('Developer Export', `Exporting comprehensive analysis in ${format.toUpperCase()} format`, 'info');
}

// Export functionality
function exportEvents(format) {
    const pid = $('#pid-filter').val();
    const device = $('#device-filter').val();
    
    // Build parameters
    let params = [];
    params.push(`format=${format}`);
    if (pid) params.push(`pid=${pid}`);
    if (device) params.push(`device=${device}`);
    
    // Ask for limit (optional)
    const limit = prompt('Enter maximum number of events to export (leave empty for all):');
    if (limit && !isNaN(limit) && parseInt(limit) > 0) {
        params.push(`limit=${parseInt(limit)}`);
    }
    
    const url = `/api/export/events?${params.join('&')}`;
    
    // Create a temporary link and click it to download
    const link = document.createElement('a');
    link.href = url;
    link.download = ''; // Browser will use the filename from Content-Disposition header
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Show success message
    showToast('Export started', `Downloading events in ${format.toUpperCase()} format...`, 'success');
}

function exportAnalysis(format) {
    const pid = $('#analysis-target-pid').val() || $('#pid-filter').val();
    const windowSize = $('#window-size').val() || 5000;
    const overlap = $('#overlap-size').val() || 1000;
    const asynchronous = $('#asynchronous-analysis').val() || 'true';
    
    // Build parameters
    let params = [];
    params.push(`format=${format}`);
    if (pid) params.push(`pid=${pid}`);
    params.push(`window_size=${windowSize}`);
    params.push(`overlap=${overlap}`);
    params.push(`asynchronous=${asynchronous}`);
    
    const url = `/api/export/analysis?${params.join('&')}`;
    
    // Show loading message
    showToast('Export started', 'Performing analysis and preparing export...', 'info');
    
    // Create a temporary link and click it to download
    const link = document.createElement('a');
    link.href = url;
    link.download = ''; // Browser will use the filename from Content-Disposition header
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Show success message after a delay
    setTimeout(() => {
        showToast('Export complete', `Analysis exported in ${format.toUpperCase()} format`, 'success');
    }, 1000);
}

// Toast notification helper
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