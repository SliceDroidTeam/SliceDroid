/**
 * Chart Components Index - Central export for all chart components
 * This file consolidates all chart components for easy importing
 */

// Core chart infrastructure
// (These will be loaded separately in the HTML)

// Specialized chart components
// (These will also be loaded separately in the HTML)

/**
 * Chart initialization and registration
 * This function is called after all chart scripts are loaded
 */
function initializeCharts() {
    console.log('Initializing chart system...');
    
    // Verify that all required components are loaded
    const requiredComponents = [
        'BaseChart',
        'ChartFactory', 
        'ChartRegistry',
        'ChartThemes',
        'ChartConstants',
        'ChartUtils',
        'APIService'
    ];
    
    const missingComponents = requiredComponents.filter(component => !window[component]);
    
    if (missingComponents.length > 0) {
        console.error('Missing chart components:', missingComponents);
        return false;
    }
    
    // Verify chart types are registered
    const availableTypes = chartRegistry.getFactory().getAvailableTypes();
    console.log('Available chart types:', availableTypes);
    
    // Setup global chart event listeners
    setupGlobalChartEvents();
    
    // Setup responsive behavior
    setupResponsiveCharts();
    
    // Setup theme management
    setupThemeManagement();
    
    console.log('Chart system initialized successfully');
    return true;
}

/**
 * Setup global chart event listeners
 */
function setupGlobalChartEvents() {
    // Listen for theme changes
    document.addEventListener('chartThemeChanged', (event) => {
        console.log('Chart theme changed to:', event.detail.theme);
        
        // Update all existing charts with new theme
        const instances = chartRegistry.getFactory().getInstancesSummary();
        instances.forEach(instance => {
            const chart = chartRegistry.getFactory().getInstance(instance.type, instance.containerId);
            if (chart) {
                chart.options.theme = event.detail.theme;
                chart.render();
            }
        });
    });
    
    // Listen for API errors
    document.addEventListener('apiError', (event) => {
        console.error('API Error occurred:', event.detail);
        
        // Show error in all chart containers that are currently loading
        const loadingContainers = document.querySelectorAll('.chart-loading');
        loadingContainers.forEach(container => {
            const containerId = container.id || container.parentElement.id;
            if (containerId) {
                d3.select(`#${containerId}`)
                    .html(`<div class="alert alert-danger">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        Error loading data: ${event.detail.message}
                    </div>`);
            }
        });
    });
    
    // Listen for window resize
    let resizeTimeout;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
            // Refresh all charts
            const instances = chartRegistry.getFactory().getInstancesSummary();
            instances.forEach(instance => {
                const chart = chartRegistry.getFactory().getInstance(instance.type, instance.containerId);
                if (chart && chart.options.responsive) {
                    chart.render();
                }
            });
        }, 250);
    });
}

/**
 * Setup responsive chart behavior
 */
function setupResponsiveCharts() {
    // Create responsive observer if available
    if (window.ResizeObserver) {
        const chartObserver = new ResizeObserver(entries => {
            for (let entry of entries) {
                const containerId = entry.target.id;
                if (containerId) {
                    // Find chart instance for this container
                    const instances = chartRegistry.getFactory().getInstancesSummary();
                    const instance = instances.find(inst => inst.containerId === containerId);
                    
                    if (instance) {
                        const chart = chartRegistry.getFactory().getInstance(instance.type, containerId);
                        if (chart && chart.options.responsive) {
                            // Debounce the resize
                            clearTimeout(chart._resizeTimeout);
                            chart._resizeTimeout = setTimeout(() => {
                                chart.render();
                            }, 100);
                        }
                    }
                }
            }
        });
        
        // Observe all chart containers
        const observeChartContainers = () => {
            const chartContainers = document.querySelectorAll('[id*="chart"], [class*="chart"]');
            chartContainers.forEach(container => {
                if (container.id) {
                    chartObserver.observe(container);
                }
            });
        };
        
        // Initial observation
        observeChartContainers();
        
        // Re-observe when new containers are added
        const mutationObserver = new MutationObserver(() => {
            observeChartContainers();
        });
        
        mutationObserver.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
}

/**
 * Setup theme management
 */
function setupThemeManagement() {
    // Set initial theme based on system preference
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        ChartThemes.setTheme('dark');
    }
    
    // Listen for system theme changes
    if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (e.matches) {
                ChartThemes.setTheme('dark');
            } else {
                ChartThemes.setTheme('default');
            }
        });
    }
}

/**
 * Create chart with automatic type detection and error handling
 */
function createChart(containerId, data, options = {}) {
    try {
        // Show loading state
        d3.select(`#${containerId}`)
            .html(`<div class="chart-loading d-flex align-items-center justify-content-center p-4">
                <div class="spinner-border text-primary me-3" role="status"></div>
                <span>Creating chart...</span>
            </div>`);
        
        // Validate data
        if (!data || (Array.isArray(data) && data.length === 0)) {
            d3.select(`#${containerId}`)
                .html(`<div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    No data available for chart
                </div>`);
            return null;
        }
        
        // Create chart using smart detection or specified type
        const chart = options.type ? 
            chartRegistry.create(options.type, containerId, data, options) :
            chartRegistry.getFactory().createSmart(containerId, data, options);
        
        console.log(`Created ${chart._factoryMeta.type} chart in container '${containerId}'`);
        return chart;
        
    } catch (error) {
        console.error('Failed to create chart:', error);
        
        d3.select(`#${containerId}`)
            .html(`<div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Failed to create chart: ${error.message}
            </div>`);
        
        return null;
    }
}

/**
 * Batch create multiple charts
 */
function createCharts(chartConfigs) {
    console.log('Creating batch of charts:', chartConfigs.length);
    
    const results = chartConfigs.map(config => {
        const { containerId, data, options = {} } = config;
        
        try {
            const chart = createChart(containerId, data, options);
            return { success: true, chart, config };
        } catch (error) {
            console.error(`Failed to create chart for ${containerId}:`, error);
            return { success: false, error, config };
        }
    });
    
    const successCount = results.filter(r => r.success).length;
    console.log(`Created ${successCount}/${chartConfigs.length} charts successfully`);
    
    return results;
}

/**
 * Destroy all charts and cleanup
 */
function destroyAllCharts() {
    chartRegistry.cleanup();
    console.log('All charts destroyed and cleaned up');
}

/**
 * Get chart statistics
 */
function getChartStatistics() {
    const instances = chartRegistry.getFactory().getInstancesSummary();
    const typeCount = {};
    
    instances.forEach(instance => {
        typeCount[instance.type] = (typeCount[instance.type] || 0) + 1;
    });
    
    return {
        totalCharts: instances.length,
        chartsByType: typeCount,
        chartsWithData: instances.filter(i => i.hasData).length,
        availableTypes: chartRegistry.getFactory().getAvailableTypes()
    };
}

/**
 * Export chart functions for global use
 */
window.initializeCharts = initializeCharts;
window.createChart = createChart;
window.createCharts = createCharts;
window.destroyAllCharts = destroyAllCharts;
window.getChartStatistics = getChartStatistics;

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, chart components ready for initialization');
});

// Initialize charts when all scripts are loaded
window.addEventListener('load', () => {
    // Small delay to ensure all scripts are fully loaded
    setTimeout(() => {
        if (typeof initializeCharts === 'function') {
            initializeCharts();
        }
    }, 100);
});

console.log('Chart index loaded - ready for initialization');