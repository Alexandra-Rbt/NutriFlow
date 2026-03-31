/* ═══════════════════════════════════════════════════
   NUTRIFLOW — JavaScript Principal
   ═══════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', function () {

    // ─────────────────────────────────────────
    //  1. SCHIMBARE TEMA — live fara reload
    // ─────────────────────────────────────────
    function applyTheme(theme) {
        document.body.setAttribute('data-theme', theme);
        localStorage.setItem('nf_theme', theme);

        // Actualizeaza vizual optiunile din settings
        document.querySelectorAll('.theme-option').forEach(el => {
            el.classList.toggle('active', el.dataset.theme === theme);
        });
    }

    // Click pe optiunea de tema din pagina Settings
    document.querySelectorAll('.theme-option').forEach(function (el) {
        el.addEventListener('click', function () {
            const theme = this.dataset.theme;

            // Aplica imediat vizual
            applyTheme(theme);

            // Salveaza in baza de date prin AJAX
            fetch('/api/set-theme/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: JSON.stringify({ theme: theme }),
            })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        showToast('Tema schimbata cu succes!', 'success');
                    }
                })
                .catch(() => showToast('Eroare la salvarea temei.', 'error'));
        });
    });

    // ─────────────────────────────────────────
    //  2. CALCUL NUTRITIONAL LIVE (dashboard)
    // ─────────────────────────────────────────
    const foodSelect = document.getElementById('id_food');
    const gramsInput = document.getElementById('id_grams');
    const previewBox = document.getElementById('nutrition-preview');

    function updateNutritionPreview() {
        const foodId = foodSelect ? foodSelect.value : null;
        const grams = gramsInput ? gramsInput.value : null;

        if (!foodId || !grams || parseFloat(grams) <= 0) {
            if (previewBox) previewBox.style.display = 'none';
            return;
        }

        fetch(`/api/nutrition-calc/?food_id=${foodId}&grams=${grams}`)
            .then(r => r.json())
            .then(data => {
                if (!data.success || !previewBox) return;
                document.getElementById('preview-kcal').textContent = data.kcal;
                document.getElementById('preview-protein').textContent = data.protein + 'g';
                document.getElementById('preview-carbs').textContent = data.carbs + 'g';
                document.getElementById('preview-fat').textContent = data.fat + 'g';
                previewBox.style.display = 'block';
            })
            .catch(() => { });
    }

    if (foodSelect) foodSelect.addEventListener('change', updateNutritionPreview);
    if (gramsInput) gramsInput.addEventListener('input', updateNutritionPreview);

    // ─────────────────────────────────────────
    //  3. ANIMARE PROGRESS BARS / RINGS
    // ─────────────────────────────────────────
    function animateProgressBars() {
        document.querySelectorAll('[data-pct]').forEach(function (el) {
            const pct = parseFloat(el.dataset.pct) || 0;
            setTimeout(() => { el.style.width = pct + '%'; }, 100);
        });
    }
    animateProgressBars();

    // Animare inel SVG calorii
    const ringCircle = document.querySelector('.kcal-ring-progress');
    if (ringCircle) {
        const pct = parseFloat(ringCircle.dataset.pct) || 0;
        const radius = parseFloat(ringCircle.getAttribute('r'));
        const circumf = 2 * Math.PI * radius;
        const dashoffset = circumf * (1 - pct / 100);
        ringCircle.style.strokeDasharray = circumf;
        ringCircle.style.strokeDashoffset = circumf; // start de la 0
        setTimeout(() => {
            ringCircle.style.transition = 'stroke-dashoffset 1.2s cubic-bezier(0.4, 0, 0.2, 1)';
            ringCircle.style.strokeDashoffset = dashoffset;
        }, 200);
    }

    // ─────────────────────────────────────────
    //  4. GRAFIC CALORII 7 ZILE (Chart.js)
    // ─────────────────────────────────────────
    const weekChartEl = document.getElementById('weekChart');
    if (weekChartEl && typeof Chart !== 'undefined') {
        const rawData = JSON.parse(weekChartEl.dataset.values || '[]');
        const labels = rawData.map(d => d.date);
        const values = rawData.map(d => d.kcal);
        const accentColor = getComputedStyle(document.body).getPropertyValue('--accent').trim();

        new Chart(weekChartEl, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Calorii (kcal)',
                    data: values,
                    backgroundColor: accentColor + '55',
                    borderColor: accentColor,
                    borderWidth: 2,
                    borderRadius: 8,
                    borderSkipped: false,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: ctx => ` ${ctx.parsed.y} kcal`,
                        },
                    },
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: getComputedStyle(document.body).getPropertyValue('--text-muted').trim() },
                    },
                    y: {
                        grid: { color: getComputedStyle(document.body).getPropertyValue('--divider').trim() },
                        ticks: { color: getComputedStyle(document.body).getPropertyValue('--text-muted').trim() },
                        beginAtZero: true,
                    },
                },
            },
        });
    }

    // ─────────────────────────────────────────
    //  5. GRAFIC GREUTATE (Chart.js linie)
    // ─────────────────────────────────────────
    const weightChartEl = document.getElementById('weightChart');
    if (weightChartEl && typeof Chart !== 'undefined') {
        const rawData = JSON.parse(weightChartEl.dataset.values || '[]');
        const labels = rawData.map(d => d.date);
        const values = rawData.map(d => d.kg);
        const accentColor = getComputedStyle(document.body).getPropertyValue('--accent').trim();

        new Chart(weightChartEl, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Greutate (kg)',
                    data: values,
                    borderColor: accentColor,
                    backgroundColor: accentColor + '20',
                    borderWidth: 2.5,
                    pointRadius: 4,
                    pointBackgroundColor: accentColor,
                    fill: true,
                    tension: 0.4,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { callbacks: { label: ctx => ` ${ctx.parsed.y} kg` } },
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: getComputedStyle(document.body).getPropertyValue('--text-muted').trim() },
                    },
                    y: {
                        grid: { color: getComputedStyle(document.body).getPropertyValue('--divider').trim() },
                        ticks: { color: getComputedStyle(document.body).getPropertyValue('--text-muted').trim() },
                    },
                },
            },
        });
    }

    // ─────────────────────────────────────────
    //  6. TOAST NOTIFICARI
    // ─────────────────────────────────────────
    window.showToast = function (msg, type = 'success') {
        const existing = document.querySelector('.nf-toast');
        if (existing) existing.remove();

        const toast = document.createElement('div');
        toast.className = 'nf-toast nf-toast-' + type;
        toast.textContent = msg;

        Object.assign(toast.style, {
            position: 'fixed',
            bottom: '24px',
            right: '24px',
            padding: '12px 20px',
            borderRadius: '12px',
            fontSize: '14px',
            fontWeight: '600',
            zIndex: '9999',
            animation: 'fadeInUp 0.3s ease',
            boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
        });

        if (type === 'success') {
            toast.style.background = getComputedStyle(document.body).getPropertyValue('--success-bg');
            toast.style.color = getComputedStyle(document.body).getPropertyValue('--success-text');
        } else {
            toast.style.background = getComputedStyle(document.body).getPropertyValue('--danger-bg');
            toast.style.color = getComputedStyle(document.body).getPropertyValue('--danger-text');
        }

        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    };

    // ─────────────────────────────────────────
    //  7. HELPER CSRF TOKEN
    // ─────────────────────────────────────────
    window.getCookie = function (name) {
        let val = null;
        document.cookie.split(';').forEach(c => {
            const [k, v] = c.trim().split('=');
            if (k === name) val = decodeURIComponent(v);
        });
        return val;
    };

    // ─────────────────────────────────────────
    //  8. AUTO-CLOSE MESAJE DJANGO
    // ─────────────────────────────────────────
    document.querySelectorAll('.alert').forEach(function (alert) {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.4s ease';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 400);
        }, 4000);
    });

});