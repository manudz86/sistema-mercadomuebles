const CACHE_NAME = 'cannon-v1';
const STATIC_ASSETS = [
    '/',
    '/static/loguito_fav.png',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
];

// Instalación: cachear assets estáticos
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
    );
    self.skipWaiting();
});

// Activación: limpiar caches viejas
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        )
    );
    self.clients.claim();
});

// Fetch: network first para páginas, cache first para estáticos
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // Assets estáticos: cache first
    if (url.pathname.startsWith('/static/') || url.hostname.includes('jsdelivr.net')) {
        event.respondWith(
            caches.match(event.request).then(cached =>
                cached || fetch(event.request).then(response => {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
                    return response;
                })
            )
        );
        return;
    }

    // Páginas: network first, fallback a cache
    event.respondWith(
        fetch(event.request).catch(() => caches.match(event.request))
    );
});
