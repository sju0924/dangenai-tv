importScripts('https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.12.2/firebase-messaging-compat.js');
importScripts('sw-env.js'); // git-ignored, SW_ENV.FIREBASE_API_KEY 등을 제공

firebase.initializeApp({
  apiKey:            SW_ENV.FIREBASE_API_KEY,
  authDomain:        "project-9ed97ef0-254a-4ec3-975.firebaseapp.com",
  projectId:         "project-9ed97ef0-254a-4ec3-975",
  storageBucket:     "project-9ed97ef0-254a-4ec3-975.firebasestorage.app",
  messagingSenderId: "792333060863",
  appId:             SW_ENV.FIREBASE_APP_ID,
});

const messaging = firebase.messaging();

// 백그라운드 알림 처리 (앱이 닫혀 있을 때)
messaging.onBackgroundMessage((payload) => {
  const { title, body } = payload.notification;
  self.registration.showNotification(title, {
    body,
    icon: '/icon.png',
  });
});
