// Thin fetch wrappers for the SliceDroid API.

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(url, options = {}) {
  let res;
  try {
    res = await fetch(url, options);
  } catch {
    throw new ApiError('Server unreachable — is the dashboard backend running?', 0);
  }
  let body = null;
  try { body = await res.json(); } catch { /* non-JSON response */ }
  if (!res.ok) {
    const detail = body && (body.error || body.message);
    throw new ApiError(detail || `Request failed (${res.status})`, res.status);
  }
  return body;
}

export const api = {
  health:    () => request('/api/health'),
  traceInfo: () => request('/api/trace-info'),
  apps:      () => request('/api/apps'),
  refreshApps: () => request('/api/apps/refresh', { method: 'POST' }),
  traceProcesses: () => request('/api/trace-processes'),
  analysis:  () => request('/api/analysis'),

  analyze: (payload) => request('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }),

  upload: (file) => {
    const form = new FormData();
    form.append('file', file);
    return request('/api/upload', { method: 'POST', body: form });
  },
};

export { ApiError };
