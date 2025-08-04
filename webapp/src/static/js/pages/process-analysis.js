/**
 * Process Analysis Module - Handles process analysis visualization and interaction
 */

/**
 * Load process analysis from API
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
        showProcessError(`Failed to load process analysis: ${textStatus}`);
    });
}

/**
 * Main process analysis rendering function
 */
function renderProcessAnalysis(data) {
    const container = $('#process-section');
    
    if (!data || data.error) {
        showProcessError(data?.error || 'No process analysis data available');
        return;
    }
    
    // Render different components
    renderProcessSummary(data);
    renderProcessTree(data.process_analysis);
    renderSuspiciousPatterns(data.process_analysis);
}

/**
 * Expand/collapse the process tree visualization
 */
function expandProcessTree() {
    const container = $('#process-tree-chart');
    const button = $('button[onclick="expandProcessTree()"]');
    
    if (!container.length) {
        console.warn('Process tree container not found');
        return;
    }
    
    // Check current state
    const isExpanded = container.hasClass('expanded');
    
    if (isExpanded) {
        // Collapse the tree
        container.removeClass('expanded');
        container.css({
            'height': '400px',
            'overflow': 'auto'
        });
        button.html('<i class="fas fa-expand"></i> Expand Tree');
        
        console.log('Process tree collapsed');
    } else {
        // Expand the tree
        container.addClass('expanded');
        container.css({
            'height': 'auto',
            'max-height': '1200px',
            'overflow': 'visible'
        });
        button.html('<i class="fas fa-compress"></i> Collapse Tree');
        
        // Re-render the process tree if data is available
        if (window.processData && window.processData.process_analysis) {
            console.log('Re-rendering expanded process tree');
            renderProcessTree(window.processData.process_analysis);
        }
        
        console.log('Process tree expanded');
    }
}

/**
 * Render process analysis summary
 */
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
            title: 'Total Processes',
            value: summary.total_processes || 0,
            type: 'info',
            icon: 'fas fa-microchip'
        },
        {
            title: 'Process Events',
            value: summary.total_process_events || 0,
            type: 'primary',
            icon: 'fas fa-list'
        },
        {
            title: 'Parent Processes',
            value: summary.parent_processes || 0,
            type: 'success',
            icon: 'fas fa-sitemap'
        },
        {
            title: 'Child Processes',
            value: summary.child_processes || 0,
            type: 'warning',
            icon: 'fas fa-code-branch'
        }
    ];

    summaryCards.forEach(card => {
        summaryContainer.append(`
            <div class="col-md-3 mb-2">
                <div class="summary-card ${card.type}">
                    <div class="card-icon">
                        <i class="${card.icon}"></i>
                    </div>
                    <div class="card-content">
                        <div class="card-value">${card.value.toLocaleString()}</div>
                        <div class="card-label">${card.title}</div>
                    </div>
                </div>
            </div>
        `);
    });
}

/**
 * Render process tree visualization
 */
function renderProcessTree(processAnalysis) {
    const container = $('#process-tree-chart');
    
    if (!processAnalysis || !processAnalysis.process_tree) {
        container.html('<div class="alert alert-info">No process tree data available</div>');
        return;
    }

    // Use the existing chart helper from charts.js
    createProcessTreeChart('process-tree-chart', processAnalysis.process_tree, 'Process Genealogy Tree');
}

/**
 * Render suspicious patterns analysis
 */
function renderSuspiciousPatterns(processAnalysis) {
    const container = $('#suspicious-patterns');
    
    if (!processAnalysis || !processAnalysis.suspicious_patterns) {
        container.html('<div class="alert alert-info">No suspicious pattern analysis available</div>');
        return;
    }

    const patterns = processAnalysis.suspicious_patterns;
    let patternsHtml = '<div class="row">';

    // Rapid Process Creation
    if (patterns.rapid_process_creation) {
        patternsHtml += createSuspiciousPatternCard(
            'Rapid Process Creation',
            patterns.rapid_process_creation,
            'fas fa-rocket',
            'danger'
        );
    }

    // Unusual Parent-Child Relationships
    if (patterns.unusual_relationships) {
        patternsHtml += createSuspiciousPatternCard(
            'Unusual Relationships',
            patterns.unusual_relationships,
            'fas fa-exclamation-triangle',
            'warning'
        );
    }

    // Process Anomalies
    if (patterns.process_anomalies) {
        patternsHtml += createSuspiciousPatternCard(
            'Process Anomalies',
            patterns.process_anomalies,
            'fas fa-bug',
            'info'
        );
    }

    // Privilege Escalation Indicators
    if (patterns.privilege_escalation) {
        patternsHtml += createSuspiciousPatternCard(
            'Privilege Escalation',
            patterns.privilege_escalation,
            'fas fa-user-shield',
            'danger'
        );
    }

    patternsHtml += '</div>';

    if (patternsHtml === '<div class="row"></div>') {
        container.html('<div class="alert alert-success">No suspicious patterns detected</div>');
    } else {
        container.html(patternsHtml);
    }
}

/**
 * Create suspicious pattern card HTML
 */
function createSuspiciousPatternCard(title, patternData, iconClass, alertType) {
    const count = Array.isArray(patternData) ? patternData.length : (patternData.count || 0);
    const description = patternData.description || 'Pattern detected in process behavior';
    
    return `
        <div class="col-md-6 mb-3">
            <div class="card border-${alertType}">
                <div class="card-header bg-${alertType} text-white">
                    <i class="${iconClass} me-2"></i>${title}
                    <span class="badge bg-light text-dark ms-2">${count}</span>
                </div>
                <div class="card-body">
                    <p class="card-text">${description}</p>
                    ${createPatternDetails(patternData)}
                </div>
            </div>
        </div>
    `;
}

/**
 * Create pattern details HTML
 */
function createPatternDetails(patternData) {
    if (Array.isArray(patternData)) {
        if (patternData.length === 0) return '<p class="text-muted">No details available</p>';
        
        let detailsHtml = '<ul class="list-unstyled">';
        patternData.slice(0, 5).forEach(item => {
            if (typeof item === 'string') {
                detailsHtml += `<li><i class="fas fa-chevron-right text-muted me-2"></i>${item}</li>`;
            } else if (item.name) {
                detailsHtml += `<li><i class="fas fa-chevron-right text-muted me-2"></i><code>${item.name}</code> (PID: ${item.pid || 'N/A'})</li>`;
            }
        });
        
        if (patternData.length > 5) {
            detailsHtml += `<li class="text-muted"><i>... and ${patternData.length - 5} more</i></li>`;
        }
        
        detailsHtml += '</ul>';
        return detailsHtml;
    } else if (typeof patternData === 'object') {
        let detailsHtml = '<dl class="row">';
        Object.entries(patternData).forEach(([key, value]) => {
            if (key !== 'description' && key !== 'count') {
                detailsHtml += `
                    <dt class="col-sm-4">${key.replace(/_/g, ' ')}</dt>
                    <dd class="col-sm-8">${value}</dd>
                `;
            }
        });
        detailsHtml += '</dl>';
        return detailsHtml;
    }
    
    return '<p class="text-muted">Details not available</p>';
}

/**
 * Show process analysis error
 */
function showProcessError(error) {
    const container = $('#process-section');
    container.html(`
        <div class="alert alert-danger" role="alert">
            <i class="fas fa-exclamation-triangle me-2"></i>
            <strong>Process Analysis Error:</strong> ${error}
        </div>
    `);
}