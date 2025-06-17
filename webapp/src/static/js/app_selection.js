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
    
    // Refresh button
    $('#refresh-apps-btn').click(refreshAppsFromDevice);
    
    // Analyze app button (does both generate targets and analyze)
    $('#analyze-app').click(analyzeApp);
}

function loadApps() {
    $.getJSON('/api/apps', function(data) {
        allApps = data.apps || [];
        
        console.log(`Loaded ${allApps.length} apps`);
        
        // Update dropdown
        updateAppDropdown();
        updateRefreshButton(data.device_status);
        
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

function updateRefreshButton(deviceStatus) {
    const refreshBtn = $('#refresh-apps-btn');
    
    if (deviceStatus && deviceStatus.device_connected) {
        refreshBtn.removeClass('btn-outline-warning btn-outline-primary')
                  .addClass('btn-outline-success')
                  .html('<i class="fas fa-mobile-alt"></i> Device Connected');
    } else if (deviceStatus && deviceStatus.adb_available) {
        refreshBtn.removeClass('btn-outline-success btn-outline-primary')
                  .addClass('btn-outline-warning')
                  .html('<i class="fas fa-wifi"></i> Connect Device');
    } else {
        refreshBtn.removeClass('btn-outline-success btn-outline-warning')
                  .addClass('btn-outline-primary')
                  .html('<i class="fas fa-sync"></i> Refresh Apps');
    }
}

function refreshAppsFromDevice() {
    const refreshBtn = $('#refresh-apps-btn');
    const originalText = refreshBtn.html();
    
    // Show loading state
    refreshBtn.html('<i class="fas fa-spinner fa-spin"></i> Refreshing...').prop('disabled', true);
    $('#app-status').html('<small>Refreshing apps from device...</small>');
    
    $.post('/api/apps/refresh', function(data) {
        if (data.success) {
            // Reload apps
            loadApps();
            $('#app-status').html(`<small class="text-success">Refreshed successfully! Found ${data.message}</small>`);
        } else {
            $('#app-status').html(`<small class="text-danger">Refresh failed: ${data.error}</small>`);
        }
    }).fail(function(jqXHR) {
        $('#app-status').html('<small class="text-danger">Refresh failed. Check device connection.</small>');
    }).always(function() {
        // Restore button
        refreshBtn.html(originalText).prop('disabled', false);
    });
}


function analyzeApp() {
    if (!selectedApp) {
        alert('Please select an app first');
        return;
    }
    
    const analyzeBtn = $('#analyze-app');
    const originalText = analyzeBtn.html();
    
    // Show loading state
    analyzeBtn.html('<i class="fas fa-spinner fa-spin"></i> Analyzing...').prop('disabled', true);
    
    // Step 1: Generate process targets
    $('#app-status').html('<small>Step 1/2: Generating process targets...</small>');
    
    $.ajax({
        url: '/api/apps/generate-targets',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            selected_apps: [selectedApp]
        }),
        success: function(targetsData) {
            if (targetsData.success) {
                // Step 2: Perform slicing analysis
                $('#app-status').html('<small>Step 2/2: Performing app-specific slicing analysis...</small>');
                
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
                                    Process targets: ${targetsData.processes.join(', ')}<br>
                                    Target PID: ${analysisData.target_pid} | Events: ${analysisData.events_count}<br>
                                    <strong>Charts now show data specific to this app!</strong>
                                </small>
                            `);
                            
                            // Auto-refresh page to show new charts
                            setTimeout(() => {
                                window.location.reload();
                            }, 3000);
                            
                        } else {
                            $('#app-status').html(`<small class="text-danger">Analysis failed: ${analysisData.error}</small>`);
                        }
                    },
                    error: function(jqXHR) {
                        let errorMsg = 'Analysis failed';
                        if (jqXHR.responseJSON && jqXHR.responseJSON.error) {
                            errorMsg += ': ' + jqXHR.responseJSON.error;
                        }
                        $('#app-status').html(`<small class="text-danger">${errorMsg}</small>`);
                    },
                    complete: function() {
                        // Restore button
                        analyzeBtn.html(originalText).prop('disabled', false);
                    }
                });
                
            } else {
                $('#app-status').html(`<small class="text-danger">Failed to generate targets: ${targetsData.error}</small>`);
                analyzeBtn.html(originalText).prop('disabled', false);
            }
        },
        error: function(jqXHR) {
            $('#app-status').html('<small class="text-danger">Failed to generate process targets</small>');
            analyzeBtn.html(originalText).prop('disabled', false);
        }
    });
}

// Helper function for escaping HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}