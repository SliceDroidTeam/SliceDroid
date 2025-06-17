// App Selection functionality for SliceDroid
// Handles app selection, filtering, and process target generation

let allApps = [];
let filteredApps = [];
let selectedApps = new Set();
let categories = [];

// Initialize app selection functionality
function initializeAppSelection() {
    setupAppEventListeners();
    
    // Show loading state initially
    showAppConnectionStatus();
    
    // Load apps (which will auto-connect if possible)
    loadApps();
}

function showAppConnectionStatus() {
    // Show a notification about ADB connection attempt
    updateAppStatus('loading', 'Checking for ADB connection...');
    
    const appsError = $('#apps-error');
    appsError.html('<i class="fas fa-spinner fa-spin"></i> Checking ADB connection and loading apps from device...');
    
    // Set timeout to fallback to popular apps if device connection takes too long
    setTimeout(() => {
        if ($('#apps-grid').is(':empty')) {
            appsError.html('<i class="fas fa-info-circle"></i> Using popular apps. Connect Android device for more apps.');
            updateAppStatus('success', 'System Ready');
        }
    }, 5000);
}

function setupAppEventListeners() {
    // Search functionality
    $('#app-search').on('input', debounce(handleAppSearch, 300));
    $('#clear-search').click(clearAppSearch);
    
    // Category filter
    $('#category-filter').change(handleCategoryFilter);
    
    // Selection controls
    $('#select-all-apps').click(selectAllVisibleApps);
    $('#clear-all-apps').click(clearAllAppSelections);
    
    // Refresh from device
    $('#refresh-apps-btn').click(refreshAppsFromDevice);
    
    // Generate targets
    $('#generate-targets').click(generateProcessTargets);
}

function loadApps(category = '', search = '') {
    let url = '/api/apps';
    let params = [];
    if (category) params.push(`category=${encodeURIComponent(category)}`);
    if (search) params.push(`search=${encodeURIComponent(search)}`);
    if (params.length > 0) url += '?' + params.join('&');
    
    console.log('Loading apps from:', url);
    
    $.getJSON(url, function(data) {
        allApps = data.apps || [];
        categories = data.categories || [];
        
        console.log(`Loaded ${allApps.length} apps in ${categories.length} categories`);
        
        // Update UI
        updateCategoryFilter();
        updateAppCountBadge(data.stats, data.device_status);
        renderApps(allApps);
        updateDeviceStatus(data.device_status);
        
        // Hide error, show content
        $('#apps-error').hide();
        $('#apps-grid').show();
        
    }).fail(function(jqXHR) {
        console.error('Failed to load apps:', jqXHR);
        showAppError('Failed to load apps. Using default popular apps.');
        // Keep showing popular apps even on error
    });
}

function updateCategoryFilter() {
    const categorySelect = $('#category-filter');
    categorySelect.find('option:not(:first)').remove();
    
    categories.forEach(category => {
        categorySelect.append(`<option value="${category}">${category}</option>`);
    });
}

function updateAppCountBadge(stats, deviceStatus) {
    const badge = $('#app-count-badge');
    if (stats) {
        let badgeText = `${stats.total_apps} apps`;
        if (stats.popular_apps > 0) {
            badgeText += ` (${stats.popular_apps} popular)`;
        }
        if (deviceStatus && deviceStatus.device_connected) {
            badgeText += ' 📱';
        }
        badge.text(badgeText);
    } else {
        badge.text(`${allApps.length} apps`);
    }
}

function updateDeviceStatus(deviceStatus) {
    if (!deviceStatus) return;
    
    const refreshBtn = $('#refresh-apps-btn');
    const appsError = $('#apps-error');
    
    if (deviceStatus.device_connected) {
        // Device connected - show success state
        refreshBtn.removeClass('btn-outline-primary btn-outline-warning')
                  .addClass('btn-outline-success')
                  .html('<i class="fas fa-mobile-alt"></i> Device Connected');
        
        if (deviceStatus.mapping_age_hours !== null && deviceStatus.mapping_age_hours < 24) {
            const ageText = deviceStatus.mapping_age_hours < 1 ? 
                          'less than 1 hour ago' : 
                          `${Math.round(deviceStatus.mapping_age_hours)} hours ago`;
            appsError.html(`<i class="fas fa-check-circle text-success"></i> Apps loaded from device (updated ${ageText})`);
        } else {
            appsError.html('<i class="fas fa-info-circle"></i> Device connected. Apps will refresh automatically.');
        }
    } else if (deviceStatus.adb_available) {
        // ADB available but no device
        refreshBtn.removeClass('btn-outline-primary btn-outline-success')
                  .addClass('btn-outline-warning')
                  .html('<i class="fas fa-wifi"></i> Connect Device');
        
        appsError.html('<i class="fas fa-exclamation-triangle text-warning"></i> ADB available but no device connected. Connect your Android device and click "Connect Device".');
    } else {
        // No ADB
        refreshBtn.removeClass('btn-outline-success btn-outline-warning')
                  .addClass('btn-outline-primary')
                  .html('<i class="fas fa-sync"></i> Refresh from Device');
        
        appsError.html('<i class="fas fa-info-circle"></i> Install ADB and connect Android device for live app discovery.');
    }
}

function renderApps(apps) {
    const grid = $('#apps-grid');
    grid.empty();
    
    if (apps.length === 0) {
        grid.html('<div class="text-center p-4"><i class="fas fa-search"></i><br>No apps found</div>');
        return;
    }
    
    apps.forEach(app => {
        const appCard = createAppCard(app);
        grid.append(appCard);
    });
    
    filteredApps = apps;
}

function createAppCard(app) {
    const isSelected = selectedApps.has(app.package_name);
    const categoryClass = `category-${app.category.toLowerCase().replace(/[^a-z]/g, '')}`;
    
    // Get app icon based on category or first letter
    const appIcon = getAppIcon(app);
    
    const card = $(`
        <div class="app-card ${isSelected ? 'selected' : ''} ${app.is_popular ? 'popular' : ''}" 
             data-package="${app.package_name}">
            <div class="app-status ${app.is_running ? '' : 'not-running'}"></div>
            
            <div class="app-header">
                <div class="app-icon">
                    <i class="${appIcon}"></i>
                </div>
                <div class="app-info">
                    <h5>${escapeHtml(app.commercial_name)}</h5>
                    <small>${escapeHtml(app.package_name)}</small>
                </div>
            </div>
            
            <div class="app-details">
                <span class="category-badge ${categoryClass}">${app.category}</span>
                ${app.is_popular ? '<span class="badge badge-warning ms-1">Popular</span>' : ''}
                ${app.is_running ? '<span class="badge badge-success ms-1">Running</span>' : ''}
            </div>
            
            <div class="app-processes">
                <strong>Processes:</strong> ${app.processes.map(p => `<code>${p}</code>`).join(', ')}
            </div>
        </div>
    `);
    
    // Click handler for selection
    card.click(function() {
        toggleAppSelection(app.package_name);
    });
    
    return card;
}

function getAppIcon(app) {
    // Icon mapping based on app category or specific apps
    const iconMap = {
        'social': 'fas fa-users',
        'entertainment': 'fas fa-play-circle', 
        'productivity': 'fas fa-briefcase',
        'communication': 'fas fa-comments',
        'gaming': 'fas fa-gamepad',
        'browsers': 'fas fa-globe',
        'finance': 'fas fa-dollar-sign',
        'shopping': 'fas fa-shopping-cart',
        'navigation': 'fas fa-map-marker-alt',
        'photography': 'fas fa-camera',
        'unknown': 'fas fa-mobile-alt'
    };
    
    // Specific app icons
    const specificIcons = {
        'com.facebook.katana': 'fab fa-facebook',
        'com.facebook.orca': 'fab fa-facebook-messenger',
        'com.instagram.android': 'fab fa-instagram',
        'com.whatsapp': 'fab fa-whatsapp',
        'com.twitter.android': 'fab fa-twitter',
        'com.snapchat.android': 'fab fa-snapchat',
        'com.google.android.youtube': 'fab fa-youtube',
        'com.spotify.music': 'fab fa-spotify',
        'com.netflix.mediaclient': 'fas fa-film',
        'com.discord': 'fab fa-discord',
        'com.android.chrome': 'fab fa-chrome',
        'com.google.android.gm': 'fas fa-envelope'
    };
    
    return specificIcons[app.package_name] || 
           iconMap[app.category.toLowerCase()] || 
           iconMap['unknown'];
}

function toggleAppSelection(packageName) {
    if (selectedApps.has(packageName)) {
        selectedApps.delete(packageName);
    } else {
        selectedApps.add(packageName);
    }
    
    // Update visual state
    const card = $(`.app-card[data-package="${packageName}"]`);
    card.toggleClass('selected', selectedApps.has(packageName));
    
    // Update selected apps summary
    updateSelectedAppsSummary();
}

function updateSelectedAppsSummary() {
    const summaryCard = $('#selected-apps-summary');
    const countSpan = $('#selected-count');
    const listDiv = $('#selected-apps-list');
    
    if (selectedApps.size === 0) {
        summaryCard.hide();
        return;
    }
    
    countSpan.text(selectedApps.size);
    listDiv.empty();
    
    // Get selected app info
    const selectedAppsList = Array.from(selectedApps).map(packageName => {
        return allApps.find(app => app.package_name === packageName);
    }).filter(app => app); // Filter out undefined
    
    selectedAppsList.forEach(app => {
        const item = $(`
            <div class="selected-app-item">
                <div class="flex-grow-1">
                    <div class="selected-app-name">${escapeHtml(app.commercial_name)}</div>
                    <div class="selected-app-package">${escapeHtml(app.package_name)}</div>
                </div>
                <button class="remove-app-btn" data-package="${app.package_name}" title="Remove">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `);
        
        item.find('.remove-app-btn').click(function(e) {
            e.stopPropagation();
            toggleAppSelection(app.package_name);
        });
        
        listDiv.append(item);
    });
    
    summaryCard.show();
}

function handleAppSearch() {
    const query = $('#app-search').val().trim();
    
    if (query === '') {
        renderApps(allApps);
        return;
    }
    
    const filtered = allApps.filter(app => 
        app.commercial_name.toLowerCase().includes(query.toLowerCase()) ||
        app.package_name.toLowerCase().includes(query.toLowerCase()) ||
        app.category.toLowerCase().includes(query.toLowerCase())
    );
    
    renderApps(filtered);
}

function clearAppSearch() {
    $('#app-search').val('');
    renderApps(allApps);
}

function handleCategoryFilter() {
    const selectedCategory = $('#category-filter').val();
    
    if (selectedCategory === '') {
        renderApps(allApps);
        return;
    }
    
    const filtered = allApps.filter(app => app.category === selectedCategory);
    renderApps(filtered);
}

function selectAllVisibleApps() {
    filteredApps.forEach(app => {
        selectedApps.add(app.package_name);
    });
    
    // Update visual state for all visible cards
    $('.app-card').each(function() {
        const packageName = $(this).data('package');
        $(this).toggleClass('selected', selectedApps.has(packageName));
    });
    
    updateSelectedAppsSummary();
    showToast('Selection', `Selected ${filteredApps.length} apps`, 'success');
}

function clearAllAppSelections() {
    selectedApps.clear();
    $('.app-card').removeClass('selected');
    updateSelectedAppsSummary();
    showToast('Selection', 'Cleared all selections', 'info');
}

function refreshAppsFromDevice() {
    const refreshBtn = $('#refresh-apps-btn');
    const originalText = refreshBtn.html();
    
    // Show loading state
    refreshBtn.html('<i class="fas fa-spinner fa-spin"></i> Refreshing...').prop('disabled', true);
    $('#apps-loading').show();
    $('#apps-grid').hide();
    
    updateAppStatus('loading', 'Refreshing apps from device...');
    
    $.ajax({
        url: '/api/apps/refresh',
        method: 'POST',
        timeout: 120000, // 2 minutes timeout
        success: function(data) {
            if (data.success) {
                showToast('Device Sync', data.message, 'success');
                // Reload apps after successful refresh
                loadApps();
            } else {
                showToast('Device Sync', data.error || 'Failed to refresh apps', 'error');
            }
        },
        error: function(jqXHR) {
            const errorMsg = jqXHR.responseJSON?.error || 'Failed to connect to device';
            showToast('Device Sync', errorMsg, 'error');
            showAppError('Failed to refresh from device. Make sure ADB is connected.');
        },
        complete: function() {
            // Restore button state
            refreshBtn.html(originalText).prop('disabled', false);
            $('#apps-loading').hide();
            $('#apps-grid').show();
            updateAppStatus('success', 'System Ready');
        }
    });
}

function generateProcessTargets() {
    if (selectedApps.size === 0) {
        showToast('Process Targets', 'No apps selected', 'warning');
        return;
    }
    
    const selectedArray = Array.from(selectedApps);
    const generateBtn = $('#generate-targets');
    const originalText = generateBtn.html();
    
    generateBtn.html('<i class="fas fa-spinner fa-spin"></i> Generating...').prop('disabled', true);
    
    $.ajax({
        url: '/api/apps/generate-targets',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            selected_apps: selectedArray
        }),
        success: function(data) {
            if (data.success) {
                showToast('Process Targets', data.message, 'success');
                
                // Show detailed info in modal or expandable section
                showProcessTargetsInfo(data.processes, data.targets_file);
            } else {
                showToast('Process Targets', data.error || 'Failed to generate targets', 'error');
            }
        },
        error: function(jqXHR) {
            const errorMsg = jqXHR.responseJSON?.error || 'Failed to generate process targets';
            showToast('Process Targets', errorMsg, 'error');
        },
        complete: function() {
            generateBtn.html(originalText).prop('disabled', false);
        }
    });
}

function showProcessTargetsInfo(processes, targetsFile) {
    // Create modal or info section showing generated targets
    const infoHtml = `
        <div class="alert alert-success mt-3">
            <h6><i class="fas fa-check-circle"></i> Process Targets Generated</h6>
            <p><strong>File:</strong> <code>${targetsFile}</code></p>
            <p><strong>Processes (${processes.length}):</strong></p>
            <div class="processes-list" style="max-height: 200px; overflow-y: auto;">
                ${processes.map(p => `<code class="d-block">${p}</code>`).join('')}
            </div>
            <small class="text-muted">These process names will be used for targeted tracing.</small>
        </div>
    `;
    
    // Add to selected apps summary or show as separate notification
    $('#selected-apps-summary .card-body').append(infoHtml);
    
    // Auto-hide after 10 seconds
    setTimeout(() => {
        $('.alert-success').fadeOut();
    }, 10000);
}

function showAppError(message) {
    $('#apps-error').html(`<i class="fas fa-exclamation-triangle"></i> ${message}`).show();
}

// Utility functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Make functions globally available
window.initializeAppSelection = initializeAppSelection;
window.loadApps = loadApps;
window.refreshAppsFromDevice = refreshAppsFromDevice;
window.generateProcessTargets = generateProcessTargets;