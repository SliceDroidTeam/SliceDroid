/**
 * Application Modules Index
 * Single import point for all core application modules
 */

// Import all modules
import { AppSelectionModule } from './AppSelectionModule.js';
import { UIModule } from './UIModule.js';
import { UploadModule } from './UploadModule.js';

// Export for ES6 module imports
export {
    AppSelectionModule,
    UIModule,
    UploadModule
};

// Global registration for non-module usage
if (typeof window !== 'undefined') {
    window.AppModules = {
        AppSelectionModule,
        UIModule,
        UploadModule
    };
}