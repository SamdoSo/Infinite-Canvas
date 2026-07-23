(function(){
    const VERSION = '2026.07.04.rec-ui.1';
    const scripts = [
        '/static/js/i18n-core.js',
        '/static/js/i18n/common.js',
        '/static/js/i18n/studio.js',
        '/static/js/i18n/api-settings.js',
        '/static/js/i18n/canvas.js',
        '/static/js/i18n/smart-canvas.js',
        '/static/js/i18n/comfyui-settings.js',
        '/static/js/i18n/admin.js',
    ];
    const tags = scripts.map(src => '<script src="' + src + '?v=' + VERSION + '"></script>').join('');
    if(document.readyState === 'loading' && document.currentScript){
        document.write(tags);
        return;
    }
    scripts.reduce((promise, src) => promise.then(() => new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = src + '?v=' + VERSION;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    })), Promise.resolve()).then(() => window.StudioI18n?.apply?.()).catch(err => console.error('Failed to load i18n modules', err));
})();

/**
 * 幽灵登录（Impersonation）全局拦截器
 * 
 * 自动为所有 /api/ 请求附加 impersonate_user_id 参数和请求头。
 * 同时也拦截 WebSocket 连接，确保画布等实时功能也处于正确的用户身份下。
 * 
 * 设计原则：无侵入式 —— 所有页面只要加载了 i18n.js 就自动获得此能力，
 * 各业务页面无需关心 impersonation 细节。
 */
(function(){
    'use strict';

    const IMPERSONATE_KEY = 'impersonate_user_id';

    function getImpersonateId() {
        try { return localStorage.getItem(IMPERSONATE_KEY) || null; } catch(e) { return null; }
    }

    function isApiUrl(url) {
        if (!url || typeof url !== 'string') return false;
        if (url.startsWith('/api/')) return true;
        try {
            const u = new URL(url, window.location.origin);
            return u.origin === window.location.origin && u.pathname.startsWith('/api/');
        } catch(e) {
            return false;
        }
    }

    function appendImpersonationToUrl(url, impersonateId) {
        if (!impersonateId) return url;
        const sep = url.includes('?') ? '&' : '?';
        return url + sep + 'impersonate_user_id=' + encodeURIComponent(impersonateId);
    }

    function setImpersonationHeader(headers, impersonateId) {
        if (!impersonateId) return;
        if (headers instanceof Headers) {
            headers.set('X-Impersonate-User-Id', impersonateId);
        } else if (Array.isArray(headers)) {
            headers.push(['X-Impersonate-User-Id', impersonateId]);
        } else if (headers && typeof headers === 'object') {
            headers['X-Impersonate-User-Id'] = impersonateId;
        }
    }

    // --- 拦截 fetch ---
    const originalFetch = window.fetch;
    window.fetch = function(input, init) {
        const impersonateId = getImpersonateId();
        if (!impersonateId) {
            return originalFetch.apply(this, arguments);
        }

        let url = typeof input === 'string' ? input : (input && input.url ? input.url : '');
        
        if (isApiUrl(url)) {
            // 修改 URL
            const newUrl = appendImpersonationToUrl(url, impersonateId);
            if (typeof input === 'string') {
                input = newUrl;
            } else if (input && typeof input === 'object' && 'url' in input) {
                try {
                    // Request 对象是 immutable 的，需要用 Object.assign 克隆属性后重建
                    input = new Request(newUrl, Object.assign({}, input));
                } catch(e) {
                    // 失败则原样返回，不影响主流程
                }
            }

            // 修改 headers（双保险）
            init = init || {};
            if (!init.headers) {
                init.headers = {};
            }
            setImpersonationHeader(init.headers, impersonateId);
        }

        return originalFetch.call(this, input, init);
    };

    // --- 拦截 WebSocket（给 URL 附加 impersonate_user_id 参数） ---
    const OriginalWebSocket = window.WebSocket;
    const WrappedWebSocket = function(url, protocols) {
        const impersonateId = getImpersonateId();
        if (impersonateId && typeof url === 'string') {
            try {
                const u = new URL(url, window.location.origin);
                if (u.host === window.location.host) {
                    url = appendImpersonationToUrl(url, impersonateId);
                }
            } catch(e) {}
        }
        if (protocols !== undefined) {
            return new OriginalWebSocket(url, protocols);
        }
        return new OriginalWebSocket(url);
    };
    WrappedWebSocket.prototype = OriginalWebSocket.prototype;
    // 复制静态常量（CONNECTING=0, OPEN=1, CLOSING=2, CLOSED=3）
    WrappedWebSocket.CONNECTING = OriginalWebSocket.CONNECTING;
    WrappedWebSocket.OPEN = OriginalWebSocket.OPEN;
    WrappedWebSocket.CLOSING = OriginalWebSocket.CLOSING;
    WrappedWebSocket.CLOSED = OriginalWebSocket.CLOSED;
    window.WebSocket = WrappedWebSocket;

})();
