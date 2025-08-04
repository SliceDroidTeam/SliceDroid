/**
 * ChartFactory - Factory pattern for creating charts
 * Centralized chart creation with consistent API and error handling
 */
class ChartFactory {
    constructor() {
        this.chartTypes = new Map();
        this.instances = new Map();
        
        // Register default chart types
        this.registerDefaults();
    }
    
    /**
     * Register default chart types
     */
    registerDefaults() {
        // These will be registered when the specific chart classes are loaded
        this.chartTypes.set('pie', null);
        this.chartTypes.set('bar', null);
        this.chartTypes.set('line', null);
        this.chartTypes.set('timeline', null);
        this.chartTypes.set('heatmap', null);
        this.chartTypes.set('network-flow', null);
        this.chartTypes.set('process-tree', null);
    }
    
    /**
     * Register a chart type
     */
    register(type, chartClass) {
        if (typeof chartClass !== 'function') {
            throw new Error(`Chart class for type '${type}' must be a constructor function`);
        }
        
        this.chartTypes.set(type, chartClass);
        console.log(`Chart type '${type}' registered successfully`);
    }
    
    /**
     * Create a chart instance
     */
    create(type, containerId, options = {}) {
        const ChartClass = this.chartTypes.get(type);
        
        if (!ChartClass) {
            throw new Error(`Unknown chart type: ${type}. Available types: ${Array.from(this.chartTypes.keys()).join(', ')}`);
        }
        
        // Check if container exists
        const container = document.getElementById(containerId);
        if (!container) {
            throw new Error(`Container '${containerId}' not found`);
        }
        
        try {
            // Create chart instance
            const chart = new ChartClass(containerId, options);
            
            // Store instance for management
            const instanceKey = `${type}_${containerId}`;
            this.instances.set(instanceKey, chart);
            
            // Add metadata
            chart._factoryMeta = {
                type,
                containerId,
                created: new Date(),
                instanceKey
            };
            
            console.log(`Created ${type} chart in container '${containerId}'`);
            return chart;
            
        } catch (error) {
            console.error(`Failed to create ${type} chart:`, error);
            this.showErrorInContainer(containerId, `Failed to create ${type} chart: ${error.message}`);
            throw error;
        }
    }
    
    /**
     * Get existing chart instance
     */
    getInstance(type, containerId) {
        const instanceKey = `${type}_${containerId}`;
        return this.instances.get(instanceKey);
    }
    
    /**
     * Update existing chart or create new one
     */
    createOrUpdate(type, containerId, data, options = {}) {
        let chart = this.getInstance(type, containerId);
        
        if (chart) {
            // Update existing chart
            chart.setData(data);
            if (options.title) chart.options.title = options.title;
            return chart;
        } else {
            // Create new chart
            chart = this.create(type, containerId, options);
            chart.setData(data);
            return chart;
        }
    }
    
    /**
     * Destroy chart instance
     */
    destroy(type, containerId) {
        const instanceKey = `${type}_${containerId}`;
        const chart = this.instances.get(instanceKey);
        
        if (chart) {
            chart.destroy();
            this.instances.delete(instanceKey);
            console.log(`Destroyed ${type} chart in container '${containerId}'`);
            return true;
        }
        
        return false;
    }
    
    /**
     * Destroy all chart instances
     */
    destroyAll() {
        for (const [instanceKey, chart] of this.instances) {
            chart.destroy();
        }
        this.instances.clear();
        console.log('All chart instances destroyed');
    }
    
    /**
     * Get available chart types
     */
    getAvailableTypes() {
        return Array.from(this.chartTypes.keys()).filter(type => this.chartTypes.get(type) !== null);
    }
    
    /**
     * Get chart instances summary
     */
    getInstancesSummary() {
        const summary = [];
        for (const [instanceKey, chart] of this.instances) {
            const meta = chart._factoryMeta;
            summary.push({
                key: instanceKey,
                type: meta.type,
                containerId: meta.containerId,
                created: meta.created,
                hasData: chart.data !== null
            });
        }
        return summary;
    }
    
    /**
     * Show error in container
     */
    showErrorInContainer(containerId, message) {
        const container = d3.select(`#${containerId}`);
        if (!container.empty()) {
            container.html(`
                <div class="chart-factory-error alert alert-danger d-flex align-items-center" role="alert">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    <div>
                        <strong>Chart Error:</strong> ${message}
                    </div>
                </div>
            `);
        }
    }
    
    /**
     * Batch create charts
     */
    createBatch(chartConfigs) {
        const results = [];
        const errors = [];
        
        for (const config of chartConfigs) {
            const { type, containerId, data, options } = config;
            
            try {
                const chart = this.createOrUpdate(type, containerId, data, options);
                results.push({ success: true, chart, config });
            } catch (error) {
                errors.push({ success: false, error, config });
                results.push({ success: false, error, config });
            }
        }
        
        return {
            results,
            errors,
            successCount: results.filter(r => r.success).length,
            errorCount: errors.length
        };
    }
    
    /**
     * Auto-detect chart type based on data structure
     */
    detectChartType(data) {
        if (!data || typeof data !== 'object') {
            return 'bar'; // Default fallback
        }
        
        if (Array.isArray(data)) {
            if (data.length === 0) return 'bar';
            
            const firstItem = data[0];
            
            // Timeline data (has timestamp)
            if (firstItem.timestamp || firstItem.time) {
                return 'timeline';
            }
            
            // Network data (has source/target)
            if (firstItem.source && firstItem.target) {
                return 'network-flow';
            }
            
            // Process tree data (has parent/child relationship)
            if (firstItem.parent_pid || firstItem.children) {
                return 'process-tree';
            }
            
            // Simple key-value pairs
            if (firstItem.label && firstItem.value) {
                return data.length <= 10 ? 'pie' : 'bar';
            }
        }
        
        // Object with coordinates (heatmap)
        if (data.x && data.y && data.values) {
            return 'heatmap';
        }
        
        // Object with series data (multi-line)
        if (data.series || data.datasets) {
            return 'line';
        }
        
        return 'bar'; // Default fallback
    }
    
    /**
     * Smart chart creation with auto-detection
     */
    createSmart(containerId, data, options = {}) {
        const autoType = this.detectChartType(data);
        const type = options.type || autoType;
        
        console.log(`Auto-detected chart type: ${autoType}, using: ${type}`);
        
        return this.createOrUpdate(type, containerId, data, {
            ...options,
            autoDetected: autoType !== type
        });
    }
}

/**
 * ChartRegistry - Global registry for chart management
 */
class ChartRegistry {
    constructor() {
        this.factory = new ChartFactory();
        this.globalOptions = {
            theme: 'default',
            responsive: true,
            animation: true
        };
    }
    
    /**
     * Set global options for all charts
     */
    setGlobalOptions(options) {
        Object.assign(this.globalOptions, options);
    }
    
    /**
     * Create chart with global options merged
     */
    create(type, containerId, data, options = {}) {
        const mergedOptions = { ...this.globalOptions, ...options };
        return this.factory.createOrUpdate(type, containerId, data, mergedOptions);
    }
    
    /**
     * Register chart type
     */
    register(type, chartClass) {
        return this.factory.register(type, chartClass);
    }
    
    /**
     * Get factory instance
     */
    getFactory() {
        return this.factory;
    }
    
    /**
     * Cleanup all charts
     */
    cleanup() {
        this.factory.destroyAll();
    }
}

// Create global registry instance
const chartRegistry = new ChartRegistry();

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ChartFactory, ChartRegistry, chartRegistry };
} else {
    window.ChartFactory = ChartFactory;
    window.ChartRegistry = ChartRegistry;
    window.chartRegistry = chartRegistry;
}