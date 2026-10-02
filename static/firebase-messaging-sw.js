importScripts("https://www.gstatic.com/firebasejs/10.13.2/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.13.2/firebase-messaging-compat.js");

firebase.initializeApp({
    apiKey: "AIzaSyD9RAHAeAlZTpykit02OimKx-tvV4DB2lo",
    authDomain: "blooddonorai.firebaseapp.com",
    projectId: "blooddonorai",
    storageBucket: "blooddonorai.firebasestorage.app",
    messagingSenderId: "574610616860",
    appId: "1:574610616860:web:c1c4dea09c1fbc52dae5d9",
    measurementId: "G-GJ9L8KEKNL"
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage(function(payload) {
    console.log("Background notification received:", payload);

    const notificationTitle =
        payload.notification?.title || "LifeLink Blood Alert";

    const notificationOptions = {
        body:
            payload.notification?.body ||
            "A blood request is waiting.",
        icon: "/static/heart-icon.png",
        badge: "/static/heart-icon.png"
    };

    self.registration.showNotification(
        notificationTitle,
        notificationOptions
    );
});