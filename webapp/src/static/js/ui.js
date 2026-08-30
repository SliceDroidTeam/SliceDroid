// Formatting helpers and small UI utilities.

export function fmtNum(n) {
  if (n == null) return '—';
  return new Intl.NumberFormat('en-US').format(n);
}

export function fmtBytes(n) {
  if (n == null) return '—';
  if (n === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.min(Math.floor(Math.log2(Math.abs(n)) / 10), units.length - 1);
  const v = n / 2 ** (10 * i);
  return `${v >= 100 || i === 0 ? Math.round(v) : v.toFixed(1)} ${units[i]}`;
}

export function fmtDuration(seconds) {
  if (seconds == null) return '—';
  if (seconds < 60) return `${seconds.toFixed(1)} s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m} m ${s} s`;
}

export function toast(message, kind = 'info', timeout = 5000) {
  const host = document.getElementById('toasts');
  const el = document.createElement('div');
  el.className = `toast ${kind}`;
  el.textContent = message;
  host.appendChild(el);
  setTimeout(() => el.remove(), timeout);
}

// Escape-free cell builder: always uses textContent.
export function tr(cells) {
  const row = document.createElement('tr');
  for (const cell of cells) {
    const td = document.createElement('td');
    if (cell instanceof Node) {
      td.appendChild(cell);
    } else if (cell !== null && typeof cell === 'object') {
      td.textContent = cell.text ?? '';
      if (cell.num) td.classList.add('num');
    } else {
      td.textContent = cell ?? '';
    }
    row.appendChild(td);
  }
  return row;
}
