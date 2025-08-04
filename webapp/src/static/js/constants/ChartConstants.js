/**
 * ChartConstants - Constants and configuration for charts
 */
const ChartConstants = {
    // Chart types
    CHART_TYPES: {
        PIE: 'pie',
        BAR: 'bar',
        LINE: 'line',
        TIMELINE: 'timeline',
        HEATMAP: 'heatmap',
        NETWORK_FLOW: 'network-flow',
        PROCESS_TREE: 'process-tree'
    },
    
    // Animation settings
    ANIMATION: {
        DURATION: {
            FAST: 300,
            NORMAL: 750,
            SLOW: 1200
        },
        EASING: {
            LINEAR: 'linear',
            EASE_OUT: 'cubic-out',
            EASE_IN: 'cubic-in',
            EASE_IN_OUT: 'cubic-in-out',
            BOUNCE: 'bounce'
        }
    },
    
    // Color schemes
    COLOR_SCHEMES: {
        SECURITY: ['#dc3545', '#fd7e14', '#ffc107', '#28a745', '#6c757d'],
        NETWORK: ['#007bff', '#17a2b8', '#6610f2', '#6f42c1', '#e83e8c'],
        PROCESS: ['#28a745', '#20c997', '#17a2b8', '#6f42c1', '#fd7e14'],
        FILESYSTEM: ['#343a40', '#495057', '#6c757d', '#adb5bd', '#ced4da'],
        DEFAULT: ['#007bff', '#28a745', '#dc3545', '#ffc107', '#17a2b8', '#6f42c1', '#fd7e14', '#6c757d']
    },
    
    // Chart dimensions
    DIMENSIONS: {
        MIN_WIDTH: 200,
        MIN_HEIGHT: 150,
        DEFAULT_WIDTH: 800,
        DEFAULT_HEIGHT: 400,
        MARGIN: {
            TOP: 20,
            RIGHT: 20,
            BOTTOM: 50,
            LEFT: 50
        }
    },
    
    // Responsive breakpoints
    BREAKPOINTS: {
        MOBILE: 576,
        TABLET: 768,
        DESKTOP: 992,
        LARGE: 1200
    },
    
    // Chart events
    EVENTS: {
        CHART_CREATED: 'chartCreated',
        CHART_UPDATED: 'chartUpdated',
        CHART_DESTROYED: 'chartDestroyed',
        DATA_CHANGED: 'dataChanged',
        THEME_CHANGED: 'themeChanged',
        INTERACTION: {
            CLICK: 'chartClick',
            HOVER: 'chartHover',
            ZOOM: 'chartZoom',
            SELECTION: 'chartSelection'
        }
    },
    
    // Data formats
    DATA_FORMATS: {
        JSON: 'json',
        CSV: 'csv',
        TSV: 'tsv'
    },
    
    // Tooltip settings
    TOOLTIP: {
        OFFSET: {
            X: 10,
            Y: -10
        },
        MAX_WIDTH: 250,
        ANIMATION_DURATION: 200
    },
    
    // Accessibility
    A11Y: {
        MIN_COLOR_CONTRAST: 4.5,
        FOCUS_OUTLINE_WIDTH: 2,
        ARIA_LABELS: {
            CHART: 'Interactive chart',
            PIE_SLICE: 'Pie chart slice',
            BAR: 'Bar chart item',
            LINE_POINT: 'Data point',
            LEGEND_ITEM: 'Legend item'
        }
    },
    
    // Performance settings
    PERFORMANCE: {
        LARGE_DATASET_THRESHOLD: 1000,
        DEBOUNCE_DELAY: 100,
        LAZY_LOAD_THRESHOLD: 50
    },
    
    // Error messages
    ERROR_MESSAGES: {
        NO_DATA: 'No data available for chart',
        INVALID_DATA: 'Invalid data format provided',
        CONTAINER_NOT_FOUND: 'Chart container not found',
        CHART_TYPE_NOT_SUPPORTED: 'Chart type not supported',
        INITIALIZATION_FAILED: 'Chart initialization failed'
    },
    
    // Export formats
    EXPORT_FORMATS: {
        PNG: 'png',
        SVG: 'svg',
        PDF: 'pdf',
        JSON: 'json',
        CSV: 'csv'
    },
    
    // Chart states
    STATES: {
        LOADING: 'loading',
        READY: 'ready',
        ERROR: 'error',
        EMPTY: 'empty',
        UPDATING: 'updating'
    },
    
    // CSS classes
    CSS_CLASSES: {
        CHART_CONTAINER: 'chart-container',
        CHART_SVG: 'chart-svg',
        CHART_GROUP: 'chart-group',
        CHART_LOADING: 'chart-loading',
        CHART_ERROR: 'chart-error',
        CHART_EMPTY: 'chart-empty',
        TOOLTIP: 'chart-tooltip',
        LEGEND: 'chart-legend',
        AXIS: 'chart-axis',
        GRID: 'chart-grid'
    },
    
    // Data validation rules
    VALIDATION: {
        REQUIRED_FIELDS: {
            PIE: ['label', 'value'],
            BAR: ['label', 'value'],
            LINE: ['x', 'y'],
            TIMELINE: ['timestamp', 'value'],
            HEATMAP: ['x', 'y', 'value']
        },
        DATA_TYPES: {
            NUMBER: 'number',
            STRING: 'string',
            DATE: 'date',
            BOOLEAN: 'boolean'
        }
    },
    
    // Default options for each chart type
    DEFAULT_OPTIONS: {
        PIE: {
            showLabels: true,
            showPercentages: true,
            showLegend: true,
            innerRadius: 0,
            padAngle: 0.02
        },
        BAR: {
            orientation: 'vertical',
            showValues: true,
            showGrid: true,
            barPadding: 0.1
        },
        LINE: {
            showPoints: true,
            lineWidth: 2,
            curveType: 'cardinal',
            showGrid: true
        },
        TIMELINE: {
            showBrush: true,
            showZoom: true,
            timeFormat: '%H:%M'
        },
        HEATMAP: {
            colorScale: 'Blues',
            showLabels: false,
            cellPadding: 1
        }
    }
};

// Freeze the object to prevent modifications
Object.freeze(ChartConstants);

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ChartConstants;
} else {
    window.ChartConstants = ChartConstants;
}