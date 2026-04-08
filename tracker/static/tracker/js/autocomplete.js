/* ═══════════════════════════════════════════════════
   NUTRIFLOW — Autocomplete alimente
   Folosit in dashboard.html si journal.html
   ═══════════════════════════════════════════════════ */

(function () {

    /* ── CSS injectat o singura data ─────────────────── */
    var style = document.createElement('style');
    style.textContent = `
    .nf-ac-wrap {
      position: relative;
    }
    .nf-ac-input {
      width: 100%;
    }
    .nf-ac-dropdown {
      position: absolute;
      top: calc(100% + 4px);
      left: 0; right: 0;
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 12px;
      box-shadow: var(--shadow-md);
      z-index: 999;
      overflow: hidden;
      max-height: 320px;
      overflow-y: auto;
      display: none;
    }
    .nf-ac-dropdown.open { display: block; }

    .nf-ac-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 14px;
      cursor: pointer;
      border-bottom: 1px solid var(--border-subtle);
      transition: background 0.12s;
      gap: 10px;
    }
    .nf-ac-item:last-child { border-bottom: none; }
    .nf-ac-item:hover,
    .nf-ac-item.selected { background: var(--accent-bg); }

    .nf-ac-item-left { flex: 1; min-width: 0; }
    .nf-ac-name {
      font-size: 14px;
      font-weight: 600;
      color: var(--text-primary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .nf-ac-meta {
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 2px;
    }
    .nf-ac-kcal {
      font-size: 13px;
      font-weight: 700;
      color: var(--accent);
      white-space: nowrap;
      flex-shrink: 0;
    }
    .nf-ac-badge {
      font-size: 10px;
      padding: 2px 6px;
      border-radius: 4px;
      background: var(--accent-bg);
      color: var(--accent);
      flex-shrink: 0;
    }
    .nf-ac-empty {
      padding: 14px;
      font-size: 13px;
      color: var(--text-muted);
      text-align: center;
    }
    .nf-ac-spinner {
      padding: 14px;
      text-align: center;
      color: var(--text-muted);
      font-size: 13px;
    }

    /* highlight textul cautat */
    .nf-ac-name mark {
      background: var(--accent-bg);
      color: var(--accent);
      border-radius: 2px;
      padding: 0 1px;
      font-weight: 700;
    }
  `;
    document.head.appendChild(style);

    /* ── Utility: highlight termen in text ───────────── */
    function highlight(text, query) {
        if (!query) return escHtml(text);
        var re = new RegExp('(' + escRe(query) + ')', 'gi');
        return escHtml(text).replace(re, '<mark>$1</mark>');
    }

    function escHtml(s) {
        return String(s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;')
            .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function escRe(s) {
        return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    /* ── Debounce ────────────────────────────────────── */
    function debounce(fn, ms) {
        var t;
        return function () {
            clearTimeout(t);
            t = setTimeout(fn, ms);
        };
    }

    /* ══════════════════════════════════════════════════
       CLASA PRINCIPALA NutriAutocomplete
       ══════════════════════════════════════════════════ */
    function NutriAutocomplete(opts) {
        /*
          opts = {
            inputId:    'food-search-input',   // input text vizibil
            hiddenId:   'food-id-hidden',      // input hidden cu food.id
            gramsId:    'id_grams',            // input grame (pentru preview)
            previewId:  'nutrition-preview',   // div preview nutritional
            onSelect:   function(food) {}      // callback optional
          }
        */
        this.input = document.getElementById(opts.inputId);
        this.hidden = document.getElementById(opts.hiddenId);
        this.gramsEl = opts.gramsId ? document.getElementById(opts.gramsId) : null;
        this.preview = opts.previewId ? document.getElementById(opts.previewId) : null;
        this.onSelect = opts.onSelect || null;

        if (!this.input || !this.hidden) return;

        this.selectedFood = null;
        this.results = [];
        this.activeIdx = -1;
        this.query = '';

        this._buildDropdown();
        this._bindEvents();
    }

    NutriAutocomplete.prototype._buildDropdown = function () {
        // Wrap input
        var wrap = document.createElement('div');
        wrap.className = 'nf-ac-wrap';
        this.input.parentNode.insertBefore(wrap, this.input);
        wrap.appendChild(this.input);

        // Dropdown
        this.dropdown = document.createElement('div');
        this.dropdown.className = 'nf-ac-dropdown';
        wrap.appendChild(this.dropdown);
    };

    NutriAutocomplete.prototype._bindEvents = function () {
        var self = this;

        // Input text — cautare cu debounce
        this.input.addEventListener('input', debounce(function () {
            self.query = self.input.value.trim();
            // Daca userul sterge textul, reseteaza selectia
            if (!self.query) {
                self.hidden.value = '';
                self.selectedFood = null;
                self._close();
                self._clearPreview();
                return;
            }
            // Daca textul nu mai corespunde cu alimentul selectat, reseteaza
            if (self.selectedFood && self.input.value !== self.selectedFood.name) {
                self.hidden.value = '';
                self.selectedFood = null;
                self._clearPreview();
            }
            if (self.query.length >= 2) {
                self._fetch(self.query);
            }
        }, 280));

        // Navigare cu tastatura
        this.input.addEventListener('keydown', function (e) {
            if (!self.dropdown.classList.contains('open')) return;
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                self._moveActive(1);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                self._moveActive(-1);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (self.activeIdx >= 0 && self.results[self.activeIdx]) {
                    self._select(self.results[self.activeIdx]);
                }
            } else if (e.key === 'Escape') {
                self._close();
            }
        });

        // Inchide la click in afara
        document.addEventListener('click', function (e) {
            if (!self.input.closest('.nf-ac-wrap').contains(e.target)) {
                self._close();
            }
        });

        // Recalculeaza preview cand se schimba gramele
        if (this.gramsEl) {
            this.gramsEl.addEventListener('input', function () {
                if (self.selectedFood) {
                    self._updatePreview(self.selectedFood, parseFloat(self.gramsEl.value) || 0);
                }
            });
        }
    };

    NutriAutocomplete.prototype._fetch = function (query) {
        var self = this;
        self._showSpinner();

        fetch('/api/food-autocomplete/?q=' + encodeURIComponent(query))
            .then(function (r) { return r.json(); })
            .then(function (data) {
                self.results = data.results || [];
                self.activeIdx = -1;
                self._render();
            })
            .catch(function () {
                self._close();
            });
    };

    NutriAutocomplete.prototype._render = function () {
        var self = this;
        this.dropdown.innerHTML = '';

        if (!this.results.length) {
            this.dropdown.innerHTML =
                '<div class="nf-ac-empty">Niciun aliment găsit pentru "<strong>' +
                escHtml(this.query) + '</strong>"</div>';
            this.dropdown.classList.add('open');
            return;
        }

        this.results.forEach(function (food, i) {
            var item = document.createElement('div');
            item.className = 'nf-ac-item';
            item.dataset.idx = i;

            item.innerHTML =
                '<div class="nf-ac-item-left">' +
                '<div class="nf-ac-name">' + highlight(food.name, self.query) + '</div>' +
                '<div class="nf-ac-meta">' +
                escHtml(food.category) +
                ' &nbsp;·&nbsp; P ' + food.protein + 'g' +
                ' · C ' + food.carbs + 'g' +
                ' · G ' + food.fat + 'g' +
                '</div>' +
                '</div>' +
                '<span class="nf-ac-kcal">' + food.kcal + ' kcal</span>' +
                (food.off ? '<span class="nf-ac-badge">🌍 OFF</span>' : '');

            item.addEventListener('mousedown', function (e) {
                e.preventDefault(); // nu pierde focus de pe input
                self._select(food);
            });

            self.dropdown.appendChild(item);
        });

        this.dropdown.classList.add('open');
    };

    NutriAutocomplete.prototype._showSpinner = function () {
        this.dropdown.innerHTML = '<div class="nf-ac-spinner">Se caută...</div>';
        this.dropdown.classList.add('open');
    };

    NutriAutocomplete.prototype._select = function (food) {
        this.selectedFood = food;
        this.input.value = food.name;
        this.hidden.value = food.id;
        this.activeIdx = -1;
        this._close();

        // Preview nutritional
        var grams = this.gramsEl ? (parseFloat(this.gramsEl.value) || 100) : 100;
        this._updatePreview(food, grams);

        if (this.onSelect) this.onSelect(food);

        // Focus pe gramaj
        if (this.gramsEl) this.gramsEl.focus();
    };

    NutriAutocomplete.prototype._updatePreview = function (food, grams) {
        if (!this.preview) return;
        if (!grams || grams <= 0) {
            this.preview.style.display = 'none';
            return;
        }
        var factor = grams / 100;
        document.getElementById('preview-kcal').textContent = Math.round(food.kcal * factor * 10) / 10;
        document.getElementById('preview-protein').textContent = Math.round(food.protein * factor * 10) / 10 + 'g';
        document.getElementById('preview-carbs').textContent = Math.round(food.carbs * factor * 10) / 10 + 'g';
        document.getElementById('preview-fat').textContent = Math.round(food.fat * factor * 10) / 10 + 'g';
        this.preview.style.display = 'block';
    };

    NutriAutocomplete.prototype._clearPreview = function () {
        if (this.preview) this.preview.style.display = 'none';
    };

    NutriAutocomplete.prototype._moveActive = function (dir) {
        var items = this.dropdown.querySelectorAll('.nf-ac-item');
        if (!items.length) return;
        if (this.activeIdx >= 0) items[this.activeIdx].classList.remove('selected');
        this.activeIdx = Math.max(0, Math.min(items.length - 1, this.activeIdx + dir));
        items[this.activeIdx].classList.add('selected');
        items[this.activeIdx].scrollIntoView({ block: 'nearest' });
    };

    NutriAutocomplete.prototype._close = function () {
        this.dropdown.classList.remove('open');
        this.activeIdx = -1;
    };

    /* ── Expune global ───────────────────────────────── */
    window.NutriAutocomplete = NutriAutocomplete;

})();