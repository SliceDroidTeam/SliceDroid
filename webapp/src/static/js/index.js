/**
 * SliceDroid JavaScript Framework Index
 * Master initialization point for the entire application
 * 
 * This file provides global registration and initialization
 * for maximum browser compatibility.
 */

// Wait for DOM to be ready before initializing
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, chart components ready for initialization');
    
    // Initialize chart system if available
    if (window.initChartSystem) {
        console.log('Initializing chart system...');
        try {
            window.initChartSystem();
        } catch (error) {
            console.error('Failed to initialize chart system:', error);
        }
    }
    
    // Initialize responsive design
    if (window.ResponsiveDesign && window.ResponsiveDesign.init) {
        try {
            window.ResponsiveDesign.init();
        } catch (error) {
            console.error('Failed to initialize responsive design:', error);
        }
    }
});

// Global namespace registration for backward compatibility
if (typeof window !== 'undefined') {
    // Create SliceDroid global namespace
    window.SliceDroid = {
        // Version information
        version: '2.0.0',
        
        // Core modules
        Constants: window.Constants || {},
        Utils: window.ChartUtilities || {},
        Services: window.Services || {},
        Charts: window.Charts || {},
        Modules: window.AppModules || {},
        
        // Convenience methods
        createChart: (type, containerId, options) => {
            if (window.chartRegistry && window.chartRegistry.get) {
                const ChartClass = window.chartRegistry.get(type);
                if (ChartClass) {
                    return new ChartClass(containerId, options);
                }
            }
            console.warn(`Chart type '${type}' not found`);
            return null;
        },
        
        // Initialization
        init: () => {
            console.log('SliceDroid Framework v2.0.0 initialized');
            
            // Initialize responsive design if available
            if (window.ResponsiveDesign && window.ResponsiveDesign.init) {
                window.ResponsiveDesign.init();
            }
            
            // Dispatch ready event
            document.dispatchEvent(new CustomEvent('slicedroid:ready', {
                detail: { version: '2.0.0' }
            }));
        }
    };
    
    console.log('SliceDroid Framework loaded - call SliceDroid.init() to initialize');
}