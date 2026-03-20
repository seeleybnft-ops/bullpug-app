/**
 * Bullpug Service Worker for Push Notifications
 * Handles incoming push events and notification display
 */

// eslint-disable-next-line no-restricted-globals
self.addEventListener('push', function(event) {
  if (!event.data) {
    console.log('Push event with no data');
    return;
  }

  try {
    const data = event.data.json();
    
    const options = {
      body: data.body || 'You have a new notification',
      icon: data.icon || '/bullpug-icon.png',
      badge: data.badge || '/bullpug-badge.png',
      vibrate: [100, 50, 100],
      data: data.data || {},
      actions: data.actions || [],
      requireInteraction: data.requireInteraction || false,
      tag: data.tag || 'bullpug-notification',
      renotify: true
    };

    event.waitUntil(
      // eslint-disable-next-line no-restricted-globals
      self.registration.showNotification(data.title || 'Bullpug', options)
    );
  } catch (e) {
    console.error('Error processing push event:', e);
  }
});

// Handle notification click
// eslint-disable-next-line no-restricted-globals
self.addEventListener('notificationclick', function(event) {
  event.notification.close();

  const notificationData = event.notification.data || {};
  const url = notificationData.url || '/';

  event.waitUntil(
    // eslint-disable-next-line no-restricted-globals
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(function(windowClients) {
        // Check if there's already a window open
        for (let i = 0; i < windowClients.length; i++) {
          const client = windowClients[i];
          if (client.url.includes(url) && 'focus' in client) {
            return client.focus();
          }
        }
        // If not, open a new window
        // eslint-disable-next-line no-restricted-globals
        if (clients.openWindow) {
          // eslint-disable-next-line no-restricted-globals
          return clients.openWindow(url);
        }
      })
  );
});

// Handle push subscription change
// eslint-disable-next-line no-restricted-globals
self.addEventListener('pushsubscriptionchange', function(event) {
  event.waitUntil(
    // eslint-disable-next-line no-restricted-globals
    self.registration.pushManager.subscribe({ userVisibleOnly: true })
      .then(function(subscription) {
        console.log('Push subscription updated:', subscription);
        // In production, send the new subscription to the server
      })
  );
});

// Log activation
// eslint-disable-next-line no-restricted-globals
self.addEventListener('activate', function(event) {
  console.log('Bullpug service worker activated');
});
