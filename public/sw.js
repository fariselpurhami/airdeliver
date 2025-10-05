// file: public/sw.js
// version: 1.0.0
// date: 2025-09-23
// author: Gemini

self.addEventListener('push', function (event) {
  const data = event.data.json();
  const options = {
    body: data.body,
    icon: '/icons/icon-192x192.png', // Make sure you have an icon here
    badge: '/icons/icon-72x72.png',
  };
  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

