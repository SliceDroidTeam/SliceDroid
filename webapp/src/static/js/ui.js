// UI utilities for SliceDroid
// Handles tooltips, toasts, sidebar, filter toggles and other UI interactions

// Handle filter toggle
function initializeFilterToggle() {
    const filtersContent = document.getElementById('filters-content');
    if (filtersContent) {
        filtersContent.addEventListener('hidden.bs.collapse', function () {
            const icon = document.getElementById('filter-toggle-icon');
            if (icon) icon.className = 'fas fa-chevron-down';
        });

        filtersContent.addEventListener('shown.bs.collapse', function () {
            const icon = document.getElementById('filter-toggle-icon');
            if (icon) icon.className = 'fas fa-chevron-up';
        });
    }
}

// Sidebar functionality
let sidebarCollapsed = false;

function toggleSidebar() {
    const collapsedView = document.querySelector('.collapsed-view');
    const fullView = document.querySelector('.full-view');
    const sidebar = document.querySelector('.filters-sidebar');
    const sidebarColumn = document.getElementById('sidebar-column');
    const mainContent = document.getElementById('main-content');

    if (sidebarCollapsed) {
        // Expanding: Change layout first, then show content
        sidebarColumn.className = 'col-md-3';
        mainContent.className = 'col-md-9 main-content';

        // Small delay to let layout settle, then show content
        setTimeout(() => {
            sidebar.classList.remove('collapsed');
            collapsedView.style.display = 'none';
            fullView.style.display = 'block';
        }, 50);

        sidebarCollapsed = false;
    } else {
        // Collapsing: Hide content first, then change layout
        collapsedView.style.display = 'block';
        fullView.style.display = 'none';
        sidebar.classList.add('collapsed');

        // Small delay to let content hide, then change layout
        setTimeout(() => {
            sidebarColumn.className = 'col-md-1';
            mainContent.className = 'col-md-11 main-content';
        }, 50);

        sidebarCollapsed = true;
    }
}

function initializeSidebarToggle() {
    const sidebarToggle = document.getElementById('sidebar-toggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', toggleSidebar);
    }
}

// Toast notification system
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

// Initialize tooltips
function initializeTooltips() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Progress bar helper
function updateProgressBar(progress) {
    const progressBar = document.getElementById('progress-bar');
    const progressPercentage = document.getElementById('progress-percentage');

    if (progressBar) {
        progressBar.style.width = progress + '%';
    }
    if (progressPercentage) {
        progressPercentage.textContent = progress + '%';
    }
}

// Security tooltip utilities
function showSecurityTooltip(event, d) {
    // Create tooltip
    const tooltip = d3.select("body").append("div")
        .attr("class", "chart-tooltip")
        .style("position", "absolute")
        .style("background", "rgba(0,0,0,0.9)")
        .style("color", "white")
        .style("padding", "8px 12px")
        .style("border-radius", "4px")
        .style("font-size", "12px")
        .style("pointer-events", "none")
        .style("z-index", "1000")
        .style("opacity", 0);

    const time = new Date(d.timestamp * 1000).toLocaleString();
    tooltip.html(`<strong>${d.event_type}</strong><br>Time: ${time}<br>Severity: ${d.severity || 'low'}<br>Process: ${d.process || 'unknown'}`)
        .style("left", (event.pageX + 10) + "px")
        .style("top", (event.pageY - 10) + "px")
        .transition().duration(200).style("opacity", 1);
}

function hideSecurityTooltip() {
    d3.selectAll(".chart-tooltip").remove();
}

// Process tree utility
function expandProcessTree() {
    if (!processData || !processData.process_analysis) {
        showToast('Process Tree', 'No process data available to expand', 'warning');
        return;
    }
    
    const treeContainer = $('#process-tree-chart');
    const processTree = processData.process_analysis.process_tree;
    
    if (!processTree || Object.keys(processTree).length === 0) {
        showToast('Process Tree', 'No process tree data available', 'info');
        return;
    }
    
    // Generate expanded tree view
    let expandedHtml = '<div class="process-tree-expanded">';
    expandedHtml += '<h6><i class="fas fa-sitemap"></i> Expanded Process Tree</h6>';
    expandedHtml += '<div class="tree-structure">';
    
    // Recursive function to build tree HTML
    function buildTreeNode(node, level = 0) {
        const indent = '  '.repeat(level);
        const pid = node.pid || 'unknown';
        const info = node.info || {};
        const name = info.name || 'unknown';
        const birthTime = info.birth_time ? new Date(info.birth_time * 1000).toLocaleString() : 'unknown';
        
        let html = `${indent}<div class="tree-node level-${level}">`;
        html += `<div class="node-content">`;
        html += `<strong>PID ${pid}</strong> - ${name}`;
        if (birthTime !== 'unknown') {
            html += ` <small class="text-muted">(${birthTime})</small>`;
        }
        html += `</div>`;
        
        if (node.children && node.children.length > 0) {
            html += `<div class="node-children">`;
            for (const child of node.children) {
                html += buildTreeNode(child, level + 1);
            }
            html += `</div>`;
        }
        
        html += `</div>`;
        return html;
    }
    
    // Build the tree for each root process
    for (const [rootPid, rootNode] of Object.entries(processTree)) {
        if (rootNode) {
            expandedHtml += buildTreeNode(rootNode);
        }
    }
    
    expandedHtml += '</div>';
    expandedHtml += '<button class="btn btn-secondary btn-sm mt-2" onclick="collapseProcessTree()">Collapse Tree</button>';
    expandedHtml += '</div>';
    
    // Add CSS for tree styling
    if (!document.getElementById('tree-styles')) {
        const styles = document.createElement('style');
        styles.id = 'tree-styles';
        styles.textContent = `
            .process-tree-expanded {
                max-height: 600px;
                overflow-y: auto;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 15px;
                background: #f8f9fa;
            }
            .tree-structure {
                font-family: monospace;
                line-height: 1.4;
            }
            .tree-node {
                margin: 2px 0;
                padding: 2px 0;
            }
            .tree-node.level-0 .node-content {
                font-weight: bold;
                color: #007bff;
            }
            .tree-node.level-1 .node-content {
                color: #28a745;
                margin-left: 20px;
            }
            .tree-node.level-2 .node-content {
                color: #ffc107;
                margin-left: 40px;
            }
            .tree-node.level-3 .node-content {
                color: #dc3545;
                margin-left: 60px;
            }
            .node-children {
                border-left: 2px solid #eee;
                margin-left: 10px;
                padding-left: 10px;
            }
        `;
        document.head.appendChild(styles);
    }
    
    treeContainer.html(expandedHtml);
    showToast('Process Tree', 'Process tree expanded successfully', 'success');
}

function collapseProcessTree() {
    if (processData && processData.process_analysis) {
        renderProcessTree(processData.process_analysis);
        showToast('Process Tree', 'Process tree collapsed', 'info');
    }
}

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
        'loading': 'status-loading',
        'success': 'status-ready',
        'warning': 'status-warning',
        'error': 'status-error'
    };
    
    statusEl.removeClass('status-ready status-loading status-warning status-error')
           .addClass(classMap[type] || 'status-ready');
    statusEl.html(`<i class="${iconMap[type] || 'fas fa-question'}"></i> <span>${message}</span>`);
}

// Initialize all UI functionality
function initializeUI() {
    initializeFilterToggle();
    initializeSidebarToggle();
    initializeTooltips();
}

// Make functions globally available
window.showToast = showToast;
window.updateProgressBar = updateProgressBar;
window.showSecurityTooltip = showSecurityTooltip;
window.hideSecurityTooltip = hideSecurityTooltip;
window.expandProcessTree = expandProcessTree;
window.collapseProcessTree = collapseProcessTree;
window.toggleSidebar = toggleSidebar;
window.updateAppStatus = updateAppStatus;
window.initializeUI = initializeUI;