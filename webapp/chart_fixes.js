// Enhanced chart initialization with proper container handling

function renderChartWithContainerCheck(containerId, renderFunction, data) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Chart container '${containerId}' not found`);
        return;
    }
    
    // Check if container is visible and has dimensions
    if (container.offsetWidth === 0 || container.offsetHeight === 0) {
        // Container is hidden, wait for it to become visible
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'attributes' && 
                    (mutation.attributeName === 'style' || mutation.attributeName === 'class')) {
                    if (container.offsetWidth > 0 && container.offsetHeight > 0) {
                        observer.disconnect();
                        setTimeout(() => renderFunction(data), 100);
                    }
                }
            });
        });
        
        observer.observe(container, {
            attributes: true,
            subtree: true
        });
        
        // Also observe parent containers
        let parent = container.parentElement;
        while (parent && parent !== document.body) {
            observer.observe(parent, {
                attributes: true
            });
            parent = parent.parentElement;
        }
    } else {
        // Container is visible, render immediately
        renderFunction(data);
    }
}

// Enhanced security analysis rendering
function renderSecurityAnalysisFixed(data) {
    $('#security-content').show();
    $('#security-error').hide();
    $('#security-loading').hide();
    
    // Wait for container to be visible before rendering charts
    setTimeout(() => {
        updateSecurityRiskBadge(data.risk_assessment);
        renderSecuritySummary(data);
        
        renderChartWithContainerCheck('security-timeline-chart', 
            (timelineData) => renderSecurityTimeline(timelineData), 
            data.timeline_data);
            
        renderSecurityEventsList(data.security_analysis);
        renderSecurityRecommendations(data.recommendations);
    }, 250);
}

// Enhanced network analysis rendering  
function renderNetworkAnalysisFixed(data) {
    $('#network-content').show();
    $('#network-error').hide();
    $('#network-loading').hide();
    
    setTimeout(() => {
        updateNetworkIntensityBadge(data.network_analysis);
        renderNetworkSummary(data);
        
        renderChartWithContainerCheck('network-flow-chart',
            (networkAnalysis) => renderNetworkFlowChart(networkAnalysis),
            data.network_analysis);
            
        renderChartWithContainerCheck('protocol-distribution-chart',
            (networkAnalysis) => renderProtocolDistribution(networkAnalysis),
            data.network_analysis);
            
        renderConnectionTables(data.network_analysis);
    }, 250);
}

// Enhanced process analysis rendering
function renderProcessAnalysisFixed(data) {
    $('#process-content').show();
    $('#process-error').hide(); 
    $('#process-loading').hide();
    
    setTimeout(() => {
        renderProcessSummary(data);
        
        renderChartWithContainerCheck('process-tree-chart',
            (processAnalysis) => renderProcessTree(processAnalysis),
            data.process_analysis);
            
        renderChartWithContainerCheck('process-timeline-chart',
            (processAnalysis) => renderProcessTimeline(processAnalysis),
            data.process_analysis);
            
        renderSuspiciousPatterns(data.process_analysis);
    }, 250);
}