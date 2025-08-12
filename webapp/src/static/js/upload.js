// Upload functionality for SliceDroid
// Handles file upload, drag & drop, progress tracking, and export functions

// Global variables for upload functionality
let dropzone, fileInput;

// Initialize upload functionality
function initializeUploadFunctionality() {
    dropzone = document.getElementById('upload-dropzone');
    fileInput = document.getElementById('trace-file-input');

    if (!dropzone || !fileInput) {
        console.warn('Upload elements not found');
        return;
    }

    setupDragAndDrop();
    setupFileInputHandlers();
    checkPreloadedFile();
}

// Setup drag and drop functionality
function setupDragAndDrop() {
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('dragover');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            handleFileSelection();
        }
    });

    dropzone.addEventListener('click', (e) => {
        // Only trigger file input if not clicking on the select button
        if (!e.target.closest('#select-file-btn')) {
            fileInput.click();
        }
    });
}

// Setup file input event handlers
function setupFileInputHandlers() {
    fileInput.addEventListener('change', handleFileSelection);
    
    const selectBtn = document.getElementById('select-file-btn');
    if (selectBtn) {
        selectBtn.addEventListener('click', () => {
            fileInput.click();
        });
    }
}

// Handle file selection
function handleFileSelection() {
    if (fileInput.files.length > 0) {
        const file = fileInput.files[0];
        if (file.name.endsWith('.trace')) {
            // Remove any existing file info and preload info when we have a valid file
            document.querySelectorAll('.preload-info, .preloaded-file-label, .file-info').forEach(el => el.remove());

            // Show selected file info
            const fileInfo = document.createElement('div');
            fileInfo.className = 'mt-2 text-success file-info';
            fileInfo.innerHTML = `<i class="fas fa-check-circle"></i> Selected: <strong>${file.name}</strong>`;
            fileInput.parentElement.appendChild(fileInfo);

            // Automatically start processing
            setTimeout(() => handleUpload(), 500);
        } else {
            alert('Please select a .trace file');
            fileInput.value = ''; // Clear invalid file
        }
    }
}

// Handle file upload
function handleUpload() {
    // Check if user selected a file or if preloaded file exists
    if (fileInput.files.length === 0) {
        // Check if preloaded file is available
        const preloadInfo = document.querySelector('.preload-info');
        if (preloadInfo) {
            // Process preloaded file
            showUploadSuccess({
                message: 'Using preloaded trace file',
                events_count: 'Available'
            });
            setTimeout(() => {
                if (typeof loadAllData === 'function') {
                    loadAllData();
                }
            }, 1000);
            return;
        } else {
            alert('Please select a .trace file first');
            return;
        }
    }

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('trace_file', file);

    // Show progress
    const progressDiv = document.getElementById('upload-progress');
    const resultDiv = document.getElementById('upload-result');

    progressDiv.style.display = 'block';
    resultDiv.style.display = 'none';

    // Disable file input during processing
    fileInput.disabled = true;

    // Upload file
    fetch('/api/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.upload_id) {
            checkUploadProgress(data.upload_id);
        } else if (data.error) {
            showUploadError(data.error);
            fileInput.disabled = false;
        } else {
            showUploadError('Upload failed: No upload ID received');
            fileInput.disabled = false;
        }
    })
    .catch(error => {
        showUploadError('Upload failed: ' + error.message);
        fileInput.disabled = false;
    });
}

// Check upload progress
function checkUploadProgress(uploadId) {
    const checkProgress = () => {
        fetch(`/api/upload/progress/${uploadId}`)
            .then(response => response.json())
            .then(data => {
                updateProgressBar(data.progress || 0);

                if (data.completed) {
                    if (data.error) {
                        showUploadError(data.error);
                    } else if (data.result && data.result.success) {
                        showUploadSuccess(data.result);
                        // Clear the file input to prevent double processing
                        fileInput.value = '';
                        // Trigger data reload without full page reload
                        setTimeout(() => {
                            if (typeof loadAllData === 'function') {
                                loadAllData();
                            }
                        }, 1000);
                    } else {
                        showUploadError(data.result?.error || 'Processing failed');
                    }
                    fileInput.disabled = false;
                } else {
                    setTimeout(checkProgress, 1000);
                }
            })
            .catch(error => {
                showUploadError('Failed to check progress: ' + error.message);
                fileInput.disabled = false;
            });
    };
    checkProgress();
}

// Update progress bar
function updateProgressBar(progress) {
    const progressBar = document.getElementById('progress-bar');
    const progressPercentage = document.getElementById('progress-percentage');

    if (progressBar) {
        progressBar.style.width = progress + '%';
    }
    if (progressPercentage) {
        progressPercentage.textContent = progress + '%';
    }
}

// Show upload success
function showUploadSuccess(result) {
    const progressDiv = document.getElementById('upload-progress');
    const resultDiv = document.getElementById('upload-result');
    const alertDiv = document.getElementById('upload-alert');

    progressDiv.style.display = 'none';
    resultDiv.style.display = 'block';

    if (alertDiv) {
        alertDiv.className = 'alert alert-success';
        alertDiv.innerHTML = `<strong>Success!</strong> ${result.message}<br>
            <small>Events processed: ${result.events_count || 'N/A'}</small>`;
    }
}

// Show upload error
function showUploadError(error) {
    const progressDiv = document.getElementById('upload-progress');
    const resultDiv = document.getElementById('upload-result');
    const alertDiv = document.getElementById('upload-alert');

    progressDiv.style.display = 'none';
    resultDiv.style.display = 'block';

    if (alertDiv) {
        alertDiv.className = 'alert alert-danger';
        alertDiv.innerHTML = `<strong>Error:</strong> ${error}`;
    }
}

// Check for preloaded file
function checkPreloadedFile() {
    fetch('/api/preloaded-file')
        .then(response => response.json())
        .then(data => {
            if (data.preloaded) {
                // Remove any existing preload info first
                document.querySelectorAll('.preload-info, .preloaded-file-label').forEach(el => el.remove());

                const fileInputContainer = fileInput.parentElement;
                const preloadInfo = document.createElement('div');
                preloadInfo.className = 'mt-2 text-info preload-info';
                preloadInfo.innerHTML = `<i class="fas fa-database"></i> Preloaded: <strong>${data.filename}</strong>`;
                fileInputContainer.appendChild(preloadInfo);
            }
        })
        .catch(error => console.log('No preloaded file available:', error));
}

// Export functions
function exportEvents(format) {
    const pid = document.getElementById('pid-filter').value;
    const device = document.getElementById('device-filter').value;

    // Build parameters
    let params = [];
    params.push(`format=${format}`);
    if (pid) params.push(`pid=${pid}`);
    if (device) params.push(`device=${device}`);

    // Ask for limit (optional)
    const limit = prompt('Enter maximum number of events to export (leave empty for all):');
    if (limit && !isNaN(limit) && parseInt(limit) > 0) {
        params.push(`limit=${parseInt(limit)}`);
    }

    const url = `/api/export/events?${params.join('&')}`;

    // Create a temporary link and click it to download
    const link = document.createElement('a');
    link.href = url;
    link.download = '';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // Show success message
    if (typeof showToast === 'function') {
        showToast('Export started', `Downloading events in ${format.toUpperCase()} format...`, 'success');
    }
}

function exportAnalysis(format) {
    const windowSize = document.getElementById('analytics-window-size').value || 1000;
    const overlap = document.getElementById('analytics-overlap').value || 200;

    // Build parameters
    let params = [];
    params.push(`format=${format}`);
    params.push(`window_size=${windowSize}`);
    params.push(`overlap=${overlap}`);

    const url = `/api/export/analysis?${params.join('&')}`;

    // Show loading message
    if (typeof showToast === 'function') {
        showToast('Export started', 'Performing analysis and preparing export...', 'info');
    }

    // Create a temporary link and click it to download
    const link = document.createElement('a');
    link.href = url;
    link.download = '';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // Show success message after a delay
    setTimeout(() => {
        if (typeof showToast === 'function') {
            showToast('Export complete', `Analysis exported in ${format.toUpperCase()} format`, 'success');
        }
    }, 1000);
}

// Make functions globally available
window.handleFileSelection = handleFileSelection;
window.handleUpload = handleUpload;
window.exportEvents = exportEvents;
window.exportAnalysis = exportAnalysis;