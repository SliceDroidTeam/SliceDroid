/**
 * Advanced Analytics Module - Handles advanced analytics visualization and interaction
 */

/**
 * Load advanced analytics with configuration
 */
function loadAdvancedAnalyticsWithConfig() {
    // Get configuration values
    const pid = $('#analytics-pid').val();
    const windowSize = $('#analytics-window-size').val() || 1000;
    const overlap = $('#analytics-overlap').val() || 200;
    
    // Validate configuration
    if (windowSize < 100 || windowSize > 10000) {
        showToast('Window size must be between 100 and 10000', 'error');
        return;
    }
    
    if (overlap < 0 || overlap >= windowSize) {
        showToast('Overlap must be between 0 and less than window size', 'error');
        return;
    }
    
    showSectionLoading('analytics-section', 'Running advanced analytics...');
    
    const params = new URLSearchParams();
    if (pid) params.append('pid', pid);
    params.append('window_size', windowSize);
    params.append('overlap', overlap);
    
    $.ajax({
        url: `/api/advanced-analytics?${params.toString()}`,
        method: 'GET',
        timeout: 60000,
        dataType: 'json'
    })
    .done(function(data) {
        console.log('Advanced analytics loaded:', data);
        renderAdvancedAnalytics(data);
        showToast('Advanced analytics completed successfully');
    })
    .fail(function(jqXHR, textStatus, errorThrown) {
        console.error('Failed to load advanced analytics:', textStatus, errorThrown);
        showAnalyticsError(`Failed to load advanced analytics: ${textStatus}`);
        showToast('Failed to load advanced analytics', 'error');
    });
}

/**
 * Render advanced analytics results
 */
function renderAdvancedAnalytics(data) {
    const container = $('#analytics-section');
    
    if (!data || data.error) {
        showAnalyticsError(data?.error || 'No analytics data available');
        return;
    }
    
    let analyticsHtml = '<div class="row">';
    
    // Summary section
    analyticsHtml += '<div class="col-12 mb-4">';
    analyticsHtml += renderAnalyticsSummary(data);
    analyticsHtml += '</div>';
    
    // Charts section
    if (data.charts) {
        analyticsHtml += '<div class="col-12 mb-4">';
        analyticsHtml += renderAnalyticsCharts(data.charts, data);
        analyticsHtml += '</div>';
    }
    
    // Detailed insights
    if (data.detailed_insights) {
        analyticsHtml += '<div class="col-12 mb-4">';
        analyticsHtml += renderDetailedInsights(data.detailed_insights);
        analyticsHtml += '</div>';
    }
    
    analyticsHtml += '</div>';
    
    container.html(analyticsHtml);
}

/**
 * Render analytics summary
 */
function renderAnalyticsSummary(data) {
    let summaryHtml = `
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">
                    <i class="fas fa-chart-line me-2"></i>Analytics Summary
                </h5>
            </div>
            <div class="card-body">
                <div class="row">
    `;
    
    // Basic metrics
    summaryHtml += `
                    <div class="col-md-3">
                        <div class="text-center">
                            <h4 class="text-primary">${data.total_events?.toLocaleString() || 'N/A'}</h4>
                            <small class="text-muted">Total Events</small>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="text-center">
                            <h4 class="text-info">${data.target_pid || 'N/A'}</h4>
                            <small class="text-muted">Target PID</small>
                        </div>
                    </div>
    `;
    
    // Time range info
    if (data.time_range) {
        const duration = data.time_range.duration_seconds ? 
            (data.time_range.duration_seconds / 1000).toFixed(2) : 'N/A';
        summaryHtml += `
                    <div class="col-md-3">
                        <div class="text-center">
                            <h4 class="text-success">${duration}</h4>
                            <small class="text-muted">Duration (seconds)</small>
                        </div>
                    </div>
        `;
    }
    
    // Process info
    if (data.process_analysis?.total_processes) {
        summaryHtml += `
                    <div class="col-md-3">
                        <div class="text-center">
                            <h4 class="text-warning">${data.process_analysis.total_processes}</h4>
                            <small class="text-muted">Processes</small>
                        </div>
                    </div>
        `;
    }
    
    summaryHtml += `
                </div>
            </div>
        </div>
    `;
    
    return summaryHtml;
}

/**
 * Render analytics charts
 */
function renderAnalyticsCharts(charts, analysisData) {
    let chartsHtml = `
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">
                    <i class="fas fa-chart-bar me-2"></i>Visualization Charts
                </h5>
            </div>
            <div class="card-body">
                <div class="row">
    `;
    
    // Category distribution chart
    if (charts.category_distribution) {
        chartsHtml += `
                    <div class="col-md-6 mb-3">
                        <h6>Category Distribution</h6>
                        <div id="analytics-category-chart" style="height: 300px;"></div>
                    </div>
        `;
    }
    
    // Device usage chart
    if (charts.device_usage) {
        chartsHtml += `
                    <div class="col-md-6 mb-3">
                        <h6>Device Usage</h6>
                        <div id="analytics-device-chart" style="height: 300px;"></div>
                    </div>
        `;
    }
    
    // Network activity chart
    if (charts.network_activity) {
        chartsHtml += `
                    <div class="col-md-6 mb-3">
                        <h6>Network Activity</h6>
                        <div id="analytics-network-chart" style="height: 300px;"></div>
                    </div>
        `;
    }
    
    // Temporal heatmap
    if (charts.temporal_heatmap) {
        chartsHtml += `
                    <div class="col-md-6 mb-3">
                        <h6>Temporal Activity Heatmap</h6>
                        <div id="analytics-temporal-chart" style="height: 300px;"></div>
                    </div>
        `;
    }
    
    chartsHtml += `
                </div>
            </div>
        </div>
    `;
    
    // Render the charts after the HTML is inserted
    setTimeout(() => {
        if (charts.category_distribution?.data) {
            createPieChart('analytics-category-chart', 
                charts.category_distribution.data.map(d => ({
                    label: d.category,
                    value: d.count
                })), 
                'Event Categories'
            );
        }
        
        if (charts.device_usage?.data) {
            createPieChart('analytics-device-chart', 
                charts.device_usage.data.map(d => ({
                    label: `Device ${d.device_id}`,
                    value: d.access_count
                })), 
                'Device Usage'
            );
        }
        
        if (charts.network_activity?.protocol_distribution) {
            const networkData = Object.entries(charts.network_activity.protocol_distribution)
                .map(([protocol, count]) => ({
                    label: protocol,
                    value: count
                }));
            createPieChart('analytics-network-chart', networkData, 'Network Protocols');
        }
        
        if (charts.temporal_heatmap?.data) {
            createBarChart('analytics-temporal-chart', 
                charts.temporal_heatmap.data.map(d => ({
                    label: `Hour ${d.hour}`,
                    value: d.activity_count
                })), 
                'Temporal Activity',
                'Hour',
                'Activity Count'
            );
        }
    }, 100);
    
    return chartsHtml;
}

/**
 * Render detailed insights
 */
function renderDetailedInsights(insights) {
    let insightsHtml = `
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">
                    <i class="fas fa-lightbulb me-2"></i>Detailed Insights
                </h5>
            </div>
            <div class="card-body">
    `;
    
    if (insights && typeof insights === 'object') {
        Object.entries(insights).forEach(([category, categoryInsights]) => {
            insightsHtml += createInsightSection(category, category.replace('_', ' ').toUpperCase(), categoryInsights);
        });
    } else {
        insightsHtml += '<p class="text-muted">No detailed insights available.</p>';
    }
    
    insightsHtml += `
            </div>
        </div>
    `;
    
    return insightsHtml;
}

/**
 * Create insight section HTML
 */
function createInsightSection(id, title, content) {
    let sectionHtml = `
        <div class="mb-3">
            <h6 class="text-primary">${title}</h6>
            <div class="ps-3">
    `;
    
    if (Array.isArray(content)) {
        content.forEach(insight => {
            sectionHtml += `<p class="mb-1"><i class="fas fa-info-circle text-info me-2"></i>${insight}</p>`;
        });
    } else if (typeof content === 'string') {
        sectionHtml += `<p class="mb-1"><i class="fas fa-info-circle text-info me-2"></i>${content}</p>`;
    } else if (typeof content === 'object') {
        Object.entries(content).forEach(([key, value]) => {
            sectionHtml += `<p class="mb-1"><strong>${key}:</strong> ${value}</p>`;
        });
    }
    
    sectionHtml += `
            </div>
        </div>
    `;
    
    return sectionHtml;
}

/**
 * Show analytics error
 */
function showAnalyticsError(error) {
    const container = $('#analytics-section');
    container.html(`
        <div class="alert alert-danger" role="alert">
            <i class="fas fa-exclamation-triangle me-2"></i>
            <strong>Analytics Error:</strong> ${error}
        </div>
    `);
}