/**
 * ChartUtils - Utility functions for chart operations
 */
class ChartUtils {
    /**
     * Validate chart data
     */
    static validateData(data, chartType) {
        if (!data) {
            return { valid: false, error: 'No data provided' };
        }
        
        if (!Array.isArray(data) && typeof data !== 'object') {
            return { valid: false, error: 'Data must be an array or object' };
        }
        
        const requiredFields = ChartConstants.VALIDATION.REQUIRED_FIELDS[chartType.toUpperCase()];
        if (!requiredFields) {
            return { valid: true }; // No validation rules for this chart type
        }
        
        if (Array.isArray(data)) {
            for (let i = 0; i < data.length; i++) {
                const item = data[i];
                if (typeof item !== 'object') {
                    return { valid: false, error: `Item at index ${i} must be an object` };
                }
                
                for (const field of requiredFields) {
                    if (!(field in item)) {
                        return { valid: false, error: `Missing required field '${field}' in item at index ${i}` };
                    }
                }
            }
        }
        
        return { valid: true };
    }
    
    /**
     * Normalize data for different chart types
     */
    static normalizeData(data, chartType) {
        if (!data) return [];
        
        switch (chartType.toLowerCase()) {
            case 'pie':
            case 'bar':
                return this.normalizeCategoricalData(data);
            
            case 'line':
            case 'timeline':
                return this.normalizeTimeSeriesData(data);
            
            case 'heatmap':
                return this.normalizeHeatmapData(data);
            
            default:
                return Array.isArray(data) ? data : [data];
        }
    }
    
    /**
     * Normalize categorical data (for pie/bar charts)
     */
    static normalizeCategoricalData(data) {
        if (Array.isArray(data)) {
            return data.map(item => {
                if (typeof item === 'object' && item.value !== undefined) {
                    return {
                        label: item.label || item.name || item.key || 'Unknown',
                        value: Number(item.value) || 0,
                        color: item.color
                    };
                } else if (typeof item === 'object') {
                    const value = item.count || item.size || item.amount || item.y || 0;
                    const label = item.label || item.name || item.key || item.x || 'Unknown';
                    return { label, value: Number(value) || 0, color: item.color };
                }
                return { label: 'Item', value: Number(item) || 0 };
            });
        } else if (typeof data === 'object') {
            return Object.entries(data).map(([key, value]) => ({
                label: key,
                value: typeof value === 'object' ? (Number(value.value) || 0) : (Number(value) || 0)
            }));
        }
        
        return [];
    }
    
    /**
     * Normalize time series data (for line/timeline charts)
     */
    static normalizeTimeSeriesData(data) {
        if (!Array.isArray(data)) return [];
        
        return data.map(item => {
            if (typeof item === 'object' && item.x !== undefined && item.y !== undefined) {
                return {
                    x: this.parseTimeValue(item.x),
                    y: Number(item.y) || 0
                };
            } else if (Array.isArray(item) && item.length >= 2) {
                return {
                    x: this.parseTimeValue(item[0]),
                    y: Number(item[1]) || 0
                };
            } else if (typeof item === 'object' && item.timestamp !== undefined) {
                return {
                    x: this.parseTimeValue(item.timestamp),
                    y: Number(item.value || item.count || 0)
                };
            }
            return null;
        }).filter(d => d !== null);
    }
    
    /**
     * Normalize heatmap data
     */
    static normalizeHeatmapData(data) {
        if (!Array.isArray(data)) return [];
        
        return data.map(item => {
            if (typeof item === 'object' && item.x !== undefined && item.y !== undefined) {
                return {
                    x: item.x,
                    y: item.y,
                    value: Number(item.value || item.z || 0)
                };
            }
            return null;
        }).filter(d => d !== null);
    }
    
    /**
     * Parse time value (string, number, or Date)
     */
    static parseTimeValue(value) {
        if (value instanceof Date) return value;
        if (typeof value === 'number') return new Date(value);
        if (typeof value === 'string') {
            const parsed = new Date(value);
            return isNaN(parsed.getTime()) ? new Date() : parsed;
        }
        return new Date();
    }
    
    /**
     * Calculate responsive dimensions
     */
    static calculateResponsiveDimensions(container, options = {}) {
        const element = typeof container === 'string' ? 
            document.getElementById(container) : container;
        
        if (!element) {
            return {
                width: ChartConstants.DIMENSIONS.DEFAULT_WIDTH,
                height: ChartConstants.DIMENSIONS.DEFAULT_HEIGHT
            };
        }
        
        const rect = element.getBoundingClientRect();
        const containerWidth = rect.width || ChartConstants.DIMENSIONS.DEFAULT_WIDTH;
        const containerHeight = rect.height || ChartConstants.DIMENSIONS.DEFAULT_HEIGHT;
        
        // Apply minimum dimensions
        const width = Math.max(containerWidth, options.minWidth || ChartConstants.DIMENSIONS.MIN_WIDTH);
        const height = Math.max(containerHeight, options.minHeight || ChartConstants.DIMENSIONS.MIN_HEIGHT);
        
        // Calculate aspect ratio constraints
        if (options.aspectRatio) {
            const calculatedHeight = width / options.aspectRatio;
            return {
                width,
                height: Math.max(calculatedHeight, options.minHeight || ChartConstants.DIMENSIONS.MIN_HEIGHT)
            };
        }
        
        return { width, height };
    }
    
    /**
     * Generate color palette
     */
    static generateColorPalette(count, scheme = 'default') {
        const baseColors = ChartConstants.COLOR_SCHEMES[scheme.toUpperCase()] || 
                          ChartConstants.COLOR_SCHEMES.DEFAULT;
        
        if (count <= baseColors.length) {
            return baseColors.slice(0, count);
        }
        
        // Generate additional colors if needed
        const colors = [...baseColors];
        const hslBase = d3.hsl(baseColors[0]);
        
        for (let i = baseColors.length; i < count; i++) {
            const hue = (hslBase.h + (i * 360 / count)) % 360;
            const saturation = Math.max(0.3, hslBase.s - ((i - baseColors.length) * 0.1));
            const lightness = Math.max(0.2, Math.min(0.8, hslBase.l + ((i % 2 === 0) ? 0.1 : -0.1)));
            
            colors.push(d3.hsl(hue, saturation, lightness).toString());
        }
        
        return colors;
    }
    
    /**
     * Format number for display
     */
    static formatNumber(value, format = 'auto') {
        if (typeof value !== 'number' || isNaN(value)) {
            return value?.toString() || '0';
        }
        
        switch (format) {
            case 'integer':
                return Math.round(value).toLocaleString();
            
            case 'decimal':
                return value.toFixed(2);
            
            case 'percentage':
                return (value * 100).toFixed(1) + '%';
            
            case 'currency':
                return new Intl.NumberFormat('en-US', {
                    style: 'currency',
                    currency: 'USD'
                }).format(value);
            
            case 'compact':
                if (Math.abs(value) >= 1e9) {
                    return (value / 1e9).toFixed(1) + 'B';
                } else if (Math.abs(value) >= 1e6) {
                    return (value / 1e6).toFixed(1) + 'M';
                } else if (Math.abs(value) >= 1e3) {
                    return (value / 1e3).toFixed(1) + 'K';
                }
                return value.toLocaleString();
            
            case 'auto':
            default:
                if (Number.isInteger(value)) {
                    return value.toLocaleString();
                } else {
                    return value.toFixed(2);
                }
        }
    }
    
    /**
     * Format time for display
     */
    static formatTime(date, format = 'auto') {
        if (!(date instanceof Date)) {
            date = new Date(date);
        }
        
        if (isNaN(date.getTime())) {
            return 'Invalid Date';
        }
        
        switch (format) {
            case 'time':
                return d3.timeFormat('%H:%M:%S')(date);
            
            case 'date':
                return d3.timeFormat('%Y-%m-%d')(date);
            
            case 'datetime':
                return d3.timeFormat('%Y-%m-%d %H:%M')(date);
            
            case 'relative':
                return this.formatRelativeTime(date);
            
            case 'auto':
            default:
                const now = new Date();
                const diffMs = now - date;
                const diffDays = diffMs / (1000 * 60 * 60 * 24);
                
                if (diffDays < 1) {
                    return d3.timeFormat('%H:%M')(date);
                } else if (diffDays < 7) {
                    return d3.timeFormat('%a %H:%M')(date);
                } else {
                    return d3.timeFormat('%m/%d %H:%M')(date);
                }
        }
    }
    
    /**
     * Format relative time (e.g., "2 hours ago")
     */
    static formatRelativeTime(date) {
        const now = new Date();
        const diffMs = now - date;
        const diffSeconds = Math.floor(diffMs / 1000);
        const diffMinutes = Math.floor(diffSeconds / 60);
        const diffHours = Math.floor(diffMinutes / 60);
        const diffDays = Math.floor(diffHours / 24);
        
        if (diffSeconds < 60) {
            return 'just now';
        } else if (diffMinutes < 60) {
            return `${diffMinutes} minute${diffMinutes !== 1 ? 's' : ''} ago`;
        } else if (diffHours < 24) {
            return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
        } else if (diffDays < 7) {
            return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
        } else {
            return d3.timeFormat('%m/%d/%Y')(date);
        }
    }
    
    /**
     * Debounce function
     */
    static debounce(func, wait, immediate = false) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                timeout = null;
                if (!immediate) func.apply(this, args);
            };
            const callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func.apply(this, args);
        };
    }
    
    /**
     * Throttle function
     */
    static throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
    
    /**
     * Deep clone object
     */
    static deepClone(obj) {
        if (obj === null || typeof obj !== 'object') return obj;
        if (obj instanceof Date) return new Date(obj.getTime());
        if (obj instanceof Array) return obj.map(item => this.deepClone(item));
        if (typeof obj === 'object') {
            const cloned = {};
            for (const key in obj) {
                if (obj.hasOwnProperty(key)) {
                    cloned[key] = this.deepClone(obj[key]);
                }
            }
            return cloned;
        }
    }
    
    /**
     * Merge objects deeply
     */
    static deepMerge(target, ...sources) {
        if (!sources.length) return target;
        const source = sources.shift();
        
        if (this.isObject(target) && this.isObject(source)) {
            for (const key in source) {
                if (this.isObject(source[key])) {
                    if (!target[key]) Object.assign(target, { [key]: {} });
                    this.deepMerge(target[key], source[key]);
                } else {
                    Object.assign(target, { [key]: source[key] });
                }
            }
        }
        
        return this.deepMerge(target, ...sources);
    }
    
    /**
     * Check if value is object
     */
    static isObject(item) {
        return item && typeof item === 'object' && !Array.isArray(item);
    }
    
    /**
     * Generate unique ID
     */
    static generateId(prefix = 'chart') {
        return `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }
    
    /**
     * Check if device is mobile/tablet
     */
    static isMobileDevice() {
        return window.innerWidth <= ChartConstants.BREAKPOINTS.TABLET;
    }
    
    /**
     * Get device type
     */
    static getDeviceType() {
        const width = window.innerWidth;
        
        if (width <= ChartConstants.BREAKPOINTS.MOBILE) {
            return 'mobile';
        } else if (width <= ChartConstants.BREAKPOINTS.TABLET) {
            return 'tablet';
        } else if (width <= ChartConstants.BREAKPOINTS.DESKTOP) {
            return 'desktop';
        } else {
            return 'large';
        }
    }
    
    /**
     * Calculate statistics for dataset
     */
    static calculateStatistics(data, valueField = 'value') {
        if (!Array.isArray(data) || data.length === 0) {
            return {
                count: 0,
                sum: 0,
                mean: 0,
                median: 0,
                min: 0,
                max: 0,
                stdDev: 0
            };
        }
        
        const values = data.map(d => Number(d[valueField] || d) || 0);
        const sortedValues = [...values].sort((a, b) => a - b);
        const count = values.length;
        const sum = values.reduce((acc, val) => acc + val, 0);
        const mean = sum / count;
        
        const median = count % 2 === 0 ?
            (sortedValues[count / 2 - 1] + sortedValues[count / 2]) / 2 :
            sortedValues[Math.floor(count / 2)];
        
        const variance = values.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) / count;
        const stdDev = Math.sqrt(variance);
        
        return {
            count,
            sum,
            mean,
            median,
            min: sortedValues[0],
            max: sortedValues[count - 1],
            stdDev
        };
    }
    
    /**
     * Export data to different formats
     */
    static exportData(data, format = 'json', filename = 'chart-data') {
        let content;
        let mimeType;
        let extension;
        
        switch (format.toLowerCase()) {
            case 'csv':
                content = this.convertToCSV(data);
                mimeType = 'text/csv';
                extension = 'csv';
                break;
            
            case 'tsv':
                content = this.convertToTSV(data);
                mimeType = 'text/tab-separated-values';
                extension = 'tsv';
                break;
            
            case 'json':
            default:
                content = JSON.stringify(data, null, 2);
                mimeType = 'application/json';
                extension = 'json';
                break;
        }
        
        this.downloadFile(content, `${filename}.${extension}`, mimeType);
    }
    
    /**
     * Convert data to CSV format
     */
    static convertToCSV(data) {
        if (!Array.isArray(data) || data.length === 0) {
            return '';
        }
        
        const headers = Object.keys(data[0]);
        const csvHeader = headers.join(',') + '\n';
        const csvRows = data.map(row => 
            headers.map(header => {
                const value = row[header];
                return typeof value === 'string' && value.includes(',') ? 
                    `"${value}"` : value;
            }).join(',')
        ).join('\n');
        
        return csvHeader + csvRows;
    }
    
    /**
     * Convert data to TSV format
     */
    static convertToTSV(data) {
        return this.convertToCSV(data).replace(/,/g, '\t');
    }
    
    /**
     * Download file
     */
    static downloadFile(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.style.display = 'none';
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        URL.revokeObjectURL(url);
    }
}

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ChartUtils;
} else {
    window.ChartUtils = ChartUtils;
}