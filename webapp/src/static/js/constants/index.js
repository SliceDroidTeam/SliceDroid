/**
 * Constants Index
 * Single import point for all application constants
 */

// Import all constants
import ChartConstants from './ChartConstants.js';

// Export for ES6 module imports
export {
    ChartConstants
};

// Global registration for non-module usage
if (typeof window !== 'undefined') {
    window.Constants = {
        ChartConstants
    };
}