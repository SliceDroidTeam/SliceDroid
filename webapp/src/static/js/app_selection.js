// Simple App Selection for SliceDroid
// Just a dropdown to select one app for analysis

let allApps = [];
let selectedApp = null;

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
            $('#analyze-app').prop('disabled', false);
            const app = allApps.find(a => a.package_name === selectedPackage);
            if (app) {
                $('#app-status').html(`<small><strong>Selected:</strong> ${app.commercial_name} (${app.package_name}) - Ready to analyze</small>`);
            }
        } else {
            $('#analyze-app').prop('disabled', true);
            $('#app-status').html('<small>Select an app from the dropdown to begin analysis</small>');
        }
    });
    
    // Analyze app button (does both generate targets and analyze)
    $('#analyze-app').click(analyzeApp);
}

function loadApps() {
    $.getJSON('/api/apps', function(data) {
        allApps = data.apps || [];
        
        console.log(`Loaded ${allApps.length} apps`);
        
        // Update dropdown
        updateAppDropdown();
        
    }).fail(function(jqXHR) {
        console.error('Failed to load apps:', jqXHR);
        $('#app-select').html('<option value="">Failed to load apps</option>');
        $('#app-status').html('<small class="text-danger">Failed to load apps. Try refreshing.</small>');
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
        const option = $(`<option value="${app.package_name}">${app.commercial_name} (${app.category})</option>`);
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
    const app = allApps.find(a => a.package_name === selectedApp);
    const processTargets = app ? app.processes : [selectedApp];
    
    // Perform slicing analysis directly
    $('#app-status').html('<small>Performing app-specific slicing analysis...</small>');
    
    $.ajax({
        url: '/api/apps/analyze',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            app_id: selectedApp
        }),
        success: function(analysisData) {
            if (analysisData.success) {
                $('#app-status').html(`
                    <small class="text-success">
                        <strong>Analysis complete for ${analysisData.app_name}</strong><br>
                        Process targets: ${processTargets.join(', ')}<br>
                        Target PID: ${analysisData.target_pid} | Events: ${analysisData.events_count}<br>
                        <strong>Refreshing charts...</strong>
                    </small>
                `);
                
                // Refresh all charts with new data instead of page reload
                refreshChartsWithNewData();
                
            } else {
                $('#app-status').html(`<small class="text-danger">Analysis failed: ${analysisData.error}</small>`);
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
            $('#app-status').html(`<small class="text-danger">${errorMsg}</small>`);
            
            // Clear loading spinners on error
            chartContainers.forEach(containerId => {
                if (document.getElementById(containerId)) {
                    hideChartLoading(containerId);
                }
            });
        },
        complete: function() {
            // Restore button
            analyzeBtn.html(originalText).prop('disabled', false);
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
        
        $('#app-status').html(`
            <small class="text-success">
                <strong>Charts updated successfully!</strong><br>
                Now showing data specific to the selected app.
            </small>
        `);
        
    }, 500); // Small delay to ensure backend has finished writing files
}

// Helper function for escaping HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}