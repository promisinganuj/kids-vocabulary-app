/* ============================================================
   VCE Vocabulary Flashcards — Common JavaScript
   Toast notifications, navbar, loading, fetch helpers
   ============================================================ */

/* --- Toast Notification System --- */
const Toast = (function () {
    let container;

    function getContainer() {
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            container.setAttribute('role', 'status');
            container.setAttribute('aria-live', 'polite');
            container.setAttribute('aria-label', 'Notifications');
            document.body.appendChild(container);
        }
        return container;
    }

    const icons = {
        success: '&#10004;',
        error: '&#10008;',
        warning: '&#9888;',
        info: '&#8505;'
    };

    function escapeHTML(str) {
        const d = document.createElement('div');
        d.textContent = str;
        return d.innerHTML;
    }

    function show(message, type, duration) {
        type = type || 'info';
        duration = duration || 4000;
        const c = getContainer();
        const toast = document.createElement('div');
        toast.className = 'toast toast--' + type;
        toast.setAttribute('role', 'alert');
        toast.innerHTML =
            '<span class="toast-icon">' + (icons[type] || icons.info) + '</span>' +
            '<span class="toast-body">' + escapeHTML(message) + '</span>' +
            '<button class="toast-close" aria-label="Dismiss notification">&times;</button>';

        toast.querySelector('.toast-close').addEventListener('click', function () {
            dismiss(toast);
        });

        c.appendChild(toast);

        if (duration > 0) {
            setTimeout(function () { dismiss(toast); }, duration);
        }

        return toast;
    }

    function dismiss(toast) {
        if (toast && toast.parentNode) {
            toast.classList.add('removing');
            toast.addEventListener('animationend', function () {
                if (toast.parentNode) toast.parentNode.removeChild(toast);
            });
        }
    }

    return {
        show: show,
        success: function (msg, dur) { return show(msg, 'success', dur); },
        error: function (msg, dur) { return show(msg, 'error', dur || 5000); },
        warning: function (msg, dur) { return show(msg, 'warning', dur); },
        info: function (msg, dur) { return show(msg, 'info', dur); }
    };
})();

/* --- Navbar Toggle (Mobile) --- */
function initNavbar() {
    const toggler = document.querySelector('.navbar-toggler');
    const collapse = document.querySelector('.navbar-collapse');
    if (!toggler || !collapse) return;

    toggler.addEventListener('click', function () {
        const expanded = toggler.getAttribute('aria-expanded') === 'true';
        toggler.setAttribute('aria-expanded', String(!expanded));
        collapse.classList.toggle('show');
    });

    // Close on outside click
    document.addEventListener('click', function (e) {
        if (!collapse.classList.contains('show')) return;
        if (!collapse.contains(e.target) && !toggler.contains(e.target)) {
            toggler.setAttribute('aria-expanded', 'false');
            collapse.classList.remove('show');
        }
    });

    // Close on Escape
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && collapse.classList.contains('show')) {
            toggler.setAttribute('aria-expanded', 'false');
            collapse.classList.remove('show');
            toggler.focus();
        }
    });
}

/* --- Loading Overlay --- */
const Loading = (function () {
    let overlay;

    function show(text) {
        text = text || 'Loading...';
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'loading-overlay';
            overlay.setAttribute('role', 'progressbar');
            overlay.setAttribute('aria-label', 'Loading');
            overlay.innerHTML =
                '<div class="spinner spinner--lg"></div>' +
                '<div class="loading-text"></div>';
            document.body.appendChild(overlay);
        }
        overlay.querySelector('.loading-text').textContent = text;
        overlay.style.display = 'flex';
    }

    function hide() {
        if (overlay) overlay.style.display = 'none';
    }

    return { show: show, hide: hide };
})();

/* --- CSRF Token Helper --- */
function getCsrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

/* --- Fetch Wrapper with CSRF --- */
async function apiFetch(url, options) {
    options = options || {};
    var headers = options.headers || {};
    var token = getCsrfToken();
    if (token) headers['X-CSRFToken'] = token;
    options.headers = headers;
    if (!options.credentials) options.credentials = 'same-origin';
    var response = await fetch(url, options);
    if (!response.ok) {
        var msg = 'Request failed (' + response.status + ')';
        try { var data = await response.json(); msg = data.detail || data.message || msg; } catch (e) { /* ignore */ }
        throw new Error(msg);
    }
    return response;
}

/* --- Init on DOM Ready --- */
document.addEventListener('DOMContentLoaded', function () {
    initNavbar();
});
