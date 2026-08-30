// A small custom combobox: a text input that filters a styled, theme-aware
// dropdown of options. Replaces the native <select>, which renders an OS
// listbox that can't be styled and is unwieldy for long lists.
//
// Usage:
//   const cb = new Combobox(rootEl, { placeholder, emptyText, onChange });
//   cb.setItems([{ value, label, search }]);   // search = lowercased haystack
//   cb.value;                                    // current selected value ('' if none)

export class Combobox {
  constructor(root, { placeholder = 'Search…', emptyText = 'No matches', onChange } = {}) {
    this.root = root;
    this.items = [];
    this.filtered = [];
    this.value = '';
    this.activeIndex = -1;
    this.emptyText = emptyText;
    this.onChange = onChange;

    root.classList.add('combo');
    root.innerHTML = `
      <input type="text" class="combo-input mono" role="combobox"
             aria-autocomplete="list" aria-expanded="false" autocomplete="off"
             spellcheck="false" placeholder="${placeholder}">
      <span class="combo-caret" aria-hidden="true">
        <svg viewBox="0 0 12 12" width="12" height="12"><path d="M2 4l4 4 4-4"
          fill="none" stroke="currentColor" stroke-width="1.6"
          stroke-linecap="round" stroke-linejoin="round"/></svg>
      </span>
      <ul class="combo-list" role="listbox" hidden></ul>`;

    this.input = root.querySelector('.combo-input');
    this.list = root.querySelector('.combo-list');
    this.caret = root.querySelector('.combo-caret');

    this.input.addEventListener('focus', () => this.open());
    this.input.addEventListener('input', () => {
      this.value = '';                       // typing invalidates the selection
      this.filter(this.input.value);
      this.open();
    });
    this.input.addEventListener('keydown', (e) => this._onKey(e));
    this.caret.addEventListener('mousedown', (e) => {
      e.preventDefault();
      this.input.focus();
      this.list.hidden ? this.open() : this.close();
    });
    document.addEventListener('click', (e) => { if (!root.contains(e.target)) this.close(); });
  }

  setItems(items) {
    this.items = items;
    this.setDisabled(items.length === 0);
    this.filter(this.value ? '' : this.input.value);
  }

  filter(query) {
    const q = query.trim().toLowerCase();
    this.filtered = q ? this.items.filter(it => it.search.includes(q)) : this.items.slice();
    this.activeIndex = this.filtered.length ? 0 : -1;
    this._renderList();
  }

  _renderList() {
    this.list.innerHTML = '';
    if (!this.filtered.length) {
      const li = document.createElement('li');
      li.className = 'combo-empty';
      li.textContent = this.items.length ? 'No matches' : this.emptyText;
      this.list.appendChild(li);
      return;
    }
    this.filtered.forEach((it, i) => {
      const li = document.createElement('li');
      li.className = 'combo-option' + (i === this.activeIndex ? ' active' : '');
      li.setAttribute('role', 'option');
      li.textContent = it.label;
      li.title = it.label;
      li.addEventListener('mousedown', (e) => { e.preventDefault(); this._choose(it); });
      li.addEventListener('mouseenter', () => { this.activeIndex = i; this._highlight(); });
      this.list.appendChild(li);
    });
  }

  _highlight() {
    [...this.list.children].forEach((li, i) => li.classList.toggle('active', i === this.activeIndex));
    this.list.children[this.activeIndex]?.scrollIntoView({ block: 'nearest' });
  }

  _choose(it) {
    this.value = it.value;
    this.input.value = it.label;
    this.close();
    this.onChange?.(it.value, it);
  }

  _onKey(e) {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (this.list.hidden) this.open();
      this.activeIndex = Math.min(this.activeIndex + 1, this.filtered.length - 1);
      this._highlight();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      this.activeIndex = Math.max(this.activeIndex - 1, 0);
      this._highlight();
    } else if (e.key === 'Enter') {
      if (this.activeIndex >= 0 && this.filtered[this.activeIndex]) {
        e.preventDefault();
        this._choose(this.filtered[this.activeIndex]);
      }
    } else if (e.key === 'Escape') {
      this.close();
      this.input.blur();
    }
  }

  open() {
    if (this.input.disabled || !this.items.length) return;
    this.list.hidden = false;
    this.input.setAttribute('aria-expanded', 'true');
  }

  close() {
    this.list.hidden = true;
    this.input.setAttribute('aria-expanded', 'false');
  }

  clear() {
    this.value = '';
    this.input.value = '';
    this.filter('');
  }

  setDisabled(disabled) {
    this.input.disabled = disabled;
    this.root.classList.toggle('disabled', disabled);
  }
}
