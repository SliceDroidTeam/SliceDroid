/**
 * Page Modules Index
 * Single import point for all page-specific functionality
 */

// Page modules are function-based, so we import them as scripts
// This index provides a centralized loading point

// Export module paths for dynamic loading
export const pageModules = [
    'analytics.js',
    'network-analysis.js',
    'process-analysis.js'
];

// Global registry for page functions (populated by individual modules)
if (typeof window !== 'undefined') {
    window.PageModules = {
        // Analytics functions from analytics.js
        // Network analysis from network-analysis.js
        // Process analysis from process-analysis.js
    };
}