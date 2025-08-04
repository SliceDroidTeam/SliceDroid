/**
 * Core Modules Index
 * Single import point for all core application functionality
 */

// Core modules are function-based, so we import them as scripts
// This index provides a centralized loading point

// Export module paths for dynamic loading
export const coreModules = [
    'config.js',
    'ui-utils.js', 
    'data-loader.js',
    'events.js'
];

// Global registry for core functions (populated by individual modules)
if (typeof window !== 'undefined') {
    window.CoreModules = {
        // Core functions will be registered here by individual modules
        // Config functions from config.js
        // UI utilities from ui-utils.js  
        // Data loading from data-loader.js
        // Event handling from events.js
    };
}