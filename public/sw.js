/**
 * TelePlay Service Worker
 * Caches static assets for offline PWA support
 */
const CACHE_NAME = 'teleplay-v1';
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/manifest.json',
    '/favicon.ico',
    '/android-chrome-192x192.png',
    '/android-chrome-512x512.png',
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    const req = event.request;
    if (req.method !== 'GET') return;
    event.respondWith(
        caches.match(req).then((cached) => {
            if (cached) return cached;
            return fetch(req).then((res) => {
                const resClone = res.clone();
                caches.open(CACHE_NAME).then((cache) => cache.put(req, resClone));
                return res;
            }).catch(() => caches.match('/'));
        })
    );
});