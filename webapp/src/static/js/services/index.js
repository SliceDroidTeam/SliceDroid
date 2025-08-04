/**
 * Services Index
 * Single import point for all service classes
 */

// Import all services
import APIService from './APIService.js';

// Export for ES6 module imports
export {
    APIService
};

// Global registration for non-module usage
if (typeof window !== 'undefined') {
    window.Services = {
        APIService
    };
}