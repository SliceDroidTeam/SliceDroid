// Simple App Selection for SliceDroid
// Just a dropdown to select one app for analysis

let allApps = [];
let selectedApp = null;
let lastAnalyzedApp = null;

// Initialize app selection functionality
function initializeAppSelection() {
    setupAppEventListeners();
    loadApps();
}

function setupAppEventListeners() {
    // App selection dropdown
    $('#app-select').change(function() {
        const selectedPackage = $(this).val();
        selectedApp = selectedPackage;
        
        // Enable/disable the analyze button
        if (selectedPackage) {
            // Enable button only if app changed or hasn't been analyzed yet
            const hasAppChanged = selectedPackage !== lastAnalyzedApp;
            $('#analyze-app').prop('disabled', !hasAppChanged);
            
            const app = allApps.find(a => a.package_name === selectedPackage);
            if (app) {
                if (hasAppChanged) {
                    $('#app-status').removeClass('alert-info alert-warning alert-danger').addClass('alert-success')
                        .html(`<i class="fas fa-check-circle me-2"></i><span><strong>${app.commercial_name}</strong> selected and ready for analysis</span>`);
                } else {
                    $('#app-status').removeClass('alert-info alert-warning alert-danger').addClass('alert-warning')
                        .html(`<i class="fas fa-info-circle me-2"></i><span><strong>${app.commercial_name}</strong> already analyzed. Select a different app to enable analysis.</span>`);
                }
            }
        } else {
            $('#analyze-app').prop('disabled', true);
            $('#app-status').removeClass('alert-success alert-warning alert-danger').addClass('alert-info')
                .html('<i class="fas fa-info-circle me-2"></i><span>Select an application from the dropdown to begin analysis</span>');
        }
    });
    
    // Analyze app button (does both generate targets and analyze)
    $('#analyze-app').click(analyzeApp);
}

function loadApps() {
    $.getJSON('/api/apps', function(data) {
        allApps = data.apps || [];
        
        // Update dropdown
        updateAppDropdown();
        
    }).fail(function(jqXHR) {
        console.error('Failed to load apps:', jqXHR);
        $('#app-select').html('<option value="">Failed to load apps</option>');
        $('#app-status').removeClass('alert-info alert-success alert-warning').addClass('alert-danger')
            .html('<i class="fas fa-exclamation-triangle me-2"></i><span>Failed to load applications. Please try refreshing the page.</span>');
    });
}

function updateAppDropdown() {
    const select = $('#app-select');
    select.empty();
    
    if (allApps.length === 0) {
        select.html('<option value="">No apps found - try refreshing</option>');
        return;
    }
    
    // Add default option
    select.append('<option value="">-- Select an app --</option>');
    
    // Sort apps by commercial name
    const sortedApps = allApps.sort((a, b) => a.commercial_name.localeCompare(b.commercial_name));
    
    // Add all apps
    sortedApps.forEach(app => {
        const option = $(`<option value="${app.package_name}">${app.commercial_name}</option>`);
        select.append(option);
    });
}



function analyzeApp() {
    if (!selectedApp) {
        alert('Please select an app first');
        return;
    }
    
    const analyzeBtn = $('#analyze-app');
    const originalText = analyzeBtn.html();
    const app = allApps.find(a => a.package_name === selectedApp);
    const appName = app ? app.commercial_name : selectedApp;
    
    // Show loading state on button
    analyzeBtn.html('<i class="fas fa-spinner fa-spin"></i> Analyzing...').prop('disabled', true);
    
    // Show loading spinners on all chart containers
    const chartContainers = [
        'timeline-container',
        'device-chart-container',
        'event-chart-container', 
        'top-devices-chart-container',
        'network-flow-chart',
        'protocol-distribution-chart',
        'process-tree-chart',
        'process-timeline-chart',
        'behavior-timeline-chart',
        'category-chart',
        'network-chart',
        'device-usage-chart',
        'process-activity-chart'
    ];
    
    chartContainers.forEach(containerId => {
        if (document.getElementById(containerId)) {
            showChartLoading(containerId, `Analyzing ${appName}...`);
        }
    });
    
    // Get process targets from existing app data  
    const selectedAppData = allApps.find(a => a.package_name === selectedApp);
    const processTargets = selectedAppData ? selectedAppData.processes : [selectedApp];
    
    // Perform slicing analysis directly
    $('#app-status').removeClass('alert-info alert-success alert-danger').addClass('alert-warning')
        .html('<i class="fas fa-spinner fa-spin me-2"></i><span>Performing app-specific analysis...</span>');
    
    $.ajax({
        url: '/api/apps/analyze',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            app_id: selectedApp
        }),
        success: function(analysisData) {
            if (analysisData.success) {
                // Mark this app as analyzed
                lastAnalyzedApp = selectedApp;
                
                // Show all analysis sections
                $('.analysis-only').show();
                
                $('#app-status').removeClass('alert-info alert-warning alert-danger').addClass('alert-success')
                    .html(`
                        <i class="fas fa-check-circle me-2"></i>
                        <span>
                            <strong>Analysis complete for ${analysisData.app_name}</strong><br>
                            <small>Process targets: ${processTargets.join(', ')} | Target PID: ${analysisData.target_pid} | Events: ${analysisData.events_count}</small><br>
                            <small><i class="fas fa-sync fa-spin me-1"></i>Refreshing charts...</small>
                        </span>
                    `);
                
                // Refresh all charts with new data instead of page reload
                refreshChartsWithNewData();
                
            } else {
                $('#app-status').removeClass('alert-info alert-warning alert-success').addClass('alert-danger')
                    .html(`<i class="fas fa-exclamation-triangle me-2"></i><span>Analysis failed: ${analysisData.error}</span>`);
                // Clear loading spinners on error
                chartContainers.forEach(containerId => {
                    if (document.getElementById(containerId)) {
                        hideChartLoading(containerId);
                    }
                });
            }
        },
        error: function(jqXHR) {
            let errorMsg = 'Analysis failed';
            if (jqXHR.responseJSON && jqXHR.responseJSON.error) {
                errorMsg += ': ' + jqXHR.responseJSON.error;
            }
            $('#app-status').removeClass('alert-info alert-warning alert-success').addClass('alert-danger')
                .html(`<i class="fas fa-exclamation-triangle me-2"></i><span>${errorMsg}</span>`);
            
            // Clear loading spinners on error
            chartContainers.forEach(containerId => {
                if (document.getElementById(containerId)) {
                    hideChartLoading(containerId);
                }
            });
        },
        complete: function() {
            // Restore button text but keep it disabled
            analyzeBtn.html(originalText);
        }
    });
}

function refreshChartsWithNewData() {
    // Reload all chart data without full page refresh
    setTimeout(() => {
        // Refresh timeline
        if (typeof loadTimelineData === 'function') {
            loadTimelineData();
        }
        
        // Refresh device stats
        if (typeof loadDeviceStats === 'function') {
            loadDeviceStats();
        }
        
        // Refresh event stats  
        if (typeof loadEventStats === 'function') {
            loadEventStats();
        }
        
        // Load all data function from main.js
        if (typeof loadAllData === 'function') {
            loadAllData();
        }
        
        $('#app-status').removeClass('alert-info alert-warning alert-danger').addClass('alert-success')
            .html(`
                <i class="fas fa-chart-line me-2"></i>
                <span>
                    <strong>Charts updated successfully!</strong><br>
                    <small>Now showing data specific to the selected application.</small>
                </span>
            `);
        
    }, 500); // Small delay to ensure backend has finished writing files
}

// Helper function for escaping HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}