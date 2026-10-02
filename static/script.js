// =========================================================
// LIFELINK - AI BLOOD DONOR MATCHING SYSTEM
// FULL SCRIPT + FIREBASE FCM PUSH NOTIFICATIONS
// =========================================================

let currentLanguage =
    localStorage.getItem("lifelinkLanguage") || "en";

let lifelinkFCMToken = null;

// =========================================================
// FIREBASE CONFIG
// =========================================================

const LIFELINK_VAPID_KEY =
    "BNX5uFh9PvlJyDc8Ei2mxGwj2h9zt53cRm2uUj8qxGYOUg99s_u06zrTHZ6uiBryuK-MAxvKjfm4T2DzZjn5E2k";

// =========================================================
// TRANSLATIONS
// =========================================================

const translations = {
    en: {
        navHome: "Home",
        navRegister: "Register Donor",
        navFind: "Find Donor",
        navEmergency: "Emergency",

        available: "Available",
        unavailable: "Unavailable",
        submit: "Submit",
        search: "Search",
        cancel: "Cancel",
        close: "Close",

        registerSuccess:
            "Donor registered successfully!",
        registerError:
            "Unable to register donor.",

        matchSuccess:
            "Matching completed successfully.",
        noDonors:
            "No compatible registered donors found.",

        notificationPermission:
            "Please allow notifications to receive blood alerts.",
        notificationEnabled:
            "Push notifications enabled.",
        notificationNotSupported:
            "Push notifications are not supported on this device.",
        emergencyNotification:
            "Emergency blood request received!",
        bloodRequest:
            "New blood request received!",

        fillRequired:
            "Please fill all required fields.",
        invalidPhone:
            "Please enter a valid phone number.",

        languageButton: "தமிழ்"
    },

    ta: {
        navHome: "முகப்பு",
        navRegister: "டோனர் பதிவு",
        navFind: "டோனர் தேடல்",
        navEmergency: "அவசரம்",

        available: "கிடைக்கும்",
        unavailable: "கிடைக்காது",
        submit: "சமர்ப்பிக்கவும்",
        search: "தேடுக",
        cancel: "ரத்து",
        close: "மூடு",

        registerSuccess:
            "டோனர் பதிவு வெற்றிகரமாக முடிந்தது!",
        registerError:
            "டோனரை பதிவு செய்ய முடியவில்லை.",

        matchSuccess:
            "டோனர் Matching வெற்றிகரமாக முடிந்தது.",
        noDonors:
            "பொருத்தமான பதிவு செய்யப்பட்ட டோனர் கிடைக்கவில்லை.",

        notificationPermission:
            "இரத்த அறிவிப்புகளைப் பெற Notification-ஐ அனுமதிக்கவும்.",
        notificationEnabled:
            "Push Notification இயக்கப்பட்டது.",
        notificationNotSupported:
            "இந்த சாதனத்தில் Push Notification ஆதரிக்கப்படவில்லை.",
        emergencyNotification:
            "அவசர இரத்தத் தேவை அறிவிப்பு வந்துள்ளது!",
        bloodRequest:
            "புதிய இரத்தத் தேவை அறிவிப்பு வந்துள்ளது!",

        fillRequired:
            "தேவையான அனைத்து விவரங்களையும் நிரப்பவும்.",
        invalidPhone:
            "சரியான Phone Number-ஐ உள்ளிடவும்.",

        languageButton: "English"
    }
};

// =========================================================
// SAFE HTML
// =========================================================

function escapeHTML(value) {
    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// =========================================================
// TRANSLATION HELPER
// =========================================================

function t(key) {
    return (
        (translations[currentLanguage] &&
            translations[currentLanguage][key]) ||
        translations.en[key] ||
        key
    );
}

// =========================================================
// TOAST MESSAGE
// =========================================================

function showToast(message, type = "info") {
    let toast =
        document.getElementById("lifelinkToast");

    if (!toast) {
        toast = document.createElement("div");

        toast.id = "lifelinkToast";

        toast.style.position = "fixed";
        toast.style.right = "25px";
        toast.style.bottom = "25px";
        toast.style.zIndex = "99999";
        toast.style.padding = "14px 20px";
        toast.style.borderRadius = "12px";
        toast.style.fontSize = "14px";
        toast.style.fontWeight = "600";
        toast.style.maxWidth = "350px";
        toast.style.boxShadow =
            "0 10px 30px rgba(0,0,0,0.35)";
        toast.style.transition =
            "all 0.3s ease";

        document.body.appendChild(toast);
    }

    toast.textContent = message;

    if (type === "success") {
        toast.style.background = "#16a34a";
        toast.style.color = "#ffffff";
    } else if (type === "error") {
        toast.style.background = "#dc2626";
        toast.style.color = "#ffffff";
    } else {
        toast.style.background = "#111827";
        toast.style.color = "#ffffff";
    }

    toast.style.opacity = "1";
    toast.style.transform = "translateY(0)";

    clearTimeout(window.lifelinkToastTimer);

    window.lifelinkToastTimer = setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform =
            "translateY(10px)";
    }, 3500);
}

// =========================================================
// NOTIFICATION SUPPORT
// =========================================================

function isNotificationSupported() {
    return (
        "Notification" in window &&
        "serviceWorker" in navigator
    );
}

// =========================================================
// FIREBASE SUPPORT
// =========================================================

function isFirebaseSupported() {
    return (
        typeof firebase !== "undefined" &&
        firebase.messaging
    );
}

// =========================================================
// REGISTER SERVICE WORKER
// =========================================================

async function registerFirebaseServiceWorker() {
    if (!("serviceWorker" in navigator)) {
        console.error(
            "Service Worker is not supported."
        );
        return null;
    }

    try {
        const registration =
            await navigator.serviceWorker.register(
                "/static/firebase-messaging-sw.js"
            );

        console.log(
            "Firebase Service Worker registered:",
            registration.scope
        );

        return registration;
    } catch (error) {
        console.error(
            "Service Worker registration error:",
            error
        );

        return null;
    }
}

// =========================================================
// GET FCM TOKEN
// =========================================================

async function getLifeLinkFCMToken() {
    if (!isFirebaseSupported()) {
        console.error(
            "Firebase Messaging is not available."
        );
        return null;
    }

    if (!isNotificationSupported()) {
        showToast(
            t("notificationNotSupported"),
            "error"
        );
        return null;
    }

    try {
        const permission =
            await Notification.requestPermission();

        if (permission !== "granted") {
            showToast(
                t("notificationPermission"),
                "error"
            );

            return null;
        }

        const serviceWorkerRegistration =
            await registerFirebaseServiceWorker();

        if (!serviceWorkerRegistration) {
            return null;
        }

        const messaging =
            firebase.messaging();

        const token = await messaging.getToken({
            vapidKey:
                LIFELINK_VAPID_KEY,
            serviceWorkerRegistration:
                serviceWorkerRegistration
        });

        if (!token) {
            console.error(
                "FCM token was not generated."
            );

            return null;
        }

        lifelinkFCMToken = token;

        console.log(
            "LifeLink FCM Token generated."
        );

        console.log(
            "FCM token:",
            token
        );

        showToast(
            t("notificationEnabled"),
            "success"
        );

        return token;

    } catch (error) {
        console.error(
            "FCM token error:",
            error
        );

        showToast(
            "Unable to enable push notifications.",
            "error"
        );

        return null;
    }
}

// =========================================================
// ENABLE NOTIFICATIONS
// =========================================================

async function enableNotifications() {
    return await getLifeLinkFCMToken();
}

// =========================================================
// REGISTER DONOR
// =========================================================

async function registerDonor(formData) {

    try {

        /*
         * Generate FCM token before registration.
         * If notification permission is denied,
         * donor can still register normally.
         */

        let fcmToken =
            await getLifeLinkFCMToken();

        const dataToSend = {
            ...formData,

            fcm_token:
                fcmToken || ""
        };

        const response =
            await fetch("/register", {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify(
                    dataToSend
                )
            });

        const data =
            await response.json();

        if (data.success) {

            showToast(
                data.message ||
                    t("registerSuccess"),
                "success"
            );

            updateDonorCount();

            return data;
        }

        showToast(
            data.message ||
                t("registerError"),
            "error"
        );

        return data;

    } catch (error) {

        console.error(
            "Registration error:",
            error
        );

        showToast(
            t("registerError"),
            "error"
        );

        return {
            success: false,
            message: error.message
        };
    }
}

// =========================================================
// FIND DONORS
// =========================================================

async function findDonors() {

    try {

        /*
         * These IDs match the actual index.html.
         */

        const bloodGroupElement =
            document.getElementById(
                "requestBlood"
            );

        const locationElement =
            document.getElementById(
                "requestLocation"
            );

        const emergencyElement =
            document.getElementById(
                "emergency"
            );

        const bloodGroup =
            bloodGroupElement
                ? bloodGroupElement.value
                : "";

        const location =
            locationElement
                ? locationElement.value.trim()
                : "";

        const emergency =
            emergencyElement
                ? emergencyElement.checked
                : false;

        if (!bloodGroup || !location) {

            showToast(
                t("fillRequired"),
                "error"
            );

            return {
                success: false
            };
        }

        const response =
            await fetch("/match", {

                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({

                    blood_group:
                        bloodGroup,

                    location:
                        location,

                    emergency:
                        emergency
                })
            });

        const data =
            await response.json();

        if (!data.success) {

            showToast(
                data.message ||
                    t("noDonors"),
                "error"
            );

            displayDonorResults([]);

            return data;
        }

        showToast(
            data.message ||
                t("matchSuccess"),
            "success"
        );

        displayDonorResults(
            data.results || []
        );

        return data;

    } catch (error) {

        console.error(
            "Matching error:",
            error
        );

        showToast(
            "Unable to find donors.",
            "error"
        );

        return {
            success: false,
            message: error.message
        };
    }
}

// =========================================================
// DISPLAY DONOR RESULTS
// =========================================================

function displayDonorResults(donors) {

    const container =
        document.getElementById(
            "results"
        );

    if (!container) {
        return;
    }

    if (!donors.length) {

        container.innerHTML = `
            <div class="no-results">
                <h3>
                    ${escapeHTML(
                        t("noDonors")
                    )}
                </h3>
            </div>
        `;

        return;
    }

    let html = "";

    donors.forEach((donor) => {

        const score =
            donor.score || 0;

        const distance =
            donor.distance !== null &&
            donor.distance !== undefined
                ? `${donor.distance} km`
                : "Distance unavailable";

        const reasons =
            Array.isArray(
                donor.reasons
            )
                ? donor.reasons
                    .map(
                        reason =>
                            `<li>${escapeHTML(
                                reason
                            )}</li>`
                    )
                    .join("")
                : "";

        html += `
            <div class="donor-result-card">

                <div class="donor-result-header">

                    <div>

                        <h3>
                            ${escapeHTML(
                                donor.name
                            )}
                        </h3>

                        <p>
                            ${escapeHTML(
                                donor.blood_group
                            )}
                        </p>

                    </div>

                    <div class="match-score">
                        ${score}%
                    </div>

                </div>

                <div class="donor-result-details">

                    <p>
                        <strong>Location:</strong>
                        ${escapeHTML(
                            donor.location
                        )}
                    </p>

                    <p>
                        <strong>Distance:</strong>
                        ${escapeHTML(
                            distance
                        )}
                    </p>

                    <p>
                        <strong>Phone:</strong>
                        ${escapeHTML(
                            donor.phone
                        )}
                    </p>

                    <p>
                        <strong>Status:</strong>
                        ${escapeHTML(
                            donor.availability
                        )}
                    </p>

                </div>

                <div class="match-reasons">

                    <strong>
                        Match reasons
                    </strong>

                    <ul>
                        ${reasons}
                    </ul>

                </div>

            </div>
        `;
    });

    container.innerHTML = html;
}

// =========================================================
// NOTIFICATION BUTTON
// =========================================================

function setupNotificationButton() {

    const buttons =
        document.querySelectorAll(
            "[data-enable-notifications]"
        );

    buttons.forEach(button => {

        button.addEventListener(
            "click",
            async function() {

                await enableNotifications();

            }
        );

    });

    const button =
        document.getElementById(
            "enableNotifications"
        );

    if (
        button &&
        !button.dataset.listenerAdded
    ) {

        button.dataset.listenerAdded =
            "true";

        button.addEventListener(
            "click",
            async function() {

                await enableNotifications();

            }
        );
    }
}

// =========================================================
// CHECK NOTIFICATION STATUS
// =========================================================

function checkNotificationStatus() {

    if (
        !isNotificationSupported()
    ) {
        return;
    }

    console.log(
        "Notification permission:",
        Notification.permission
    );
}

// =========================================================
// DONOR COUNT
// =========================================================

async function updateDonorCount() {

    try {

        const response =
            await fetch(
                "/donor-count"
            );

        const data =
            await response.json();

        if (!data.success) {
            return;
        }

        const elements =
            document.querySelectorAll(
                "[data-donor-count]"
            );

        elements.forEach(element => {

            element.textContent =
                data.total_donors;

        });

        const countElement =
            document.getElementById(
                "donorCount"
            );

        if (countElement) {

            countElement.textContent =
                data.total_donors;

        }

    } catch (error) {

        console.error(
            "Donor count error:",
            error
        );
    }
}

// =========================================================
// LANGUAGE SWITCH
// =========================================================

function setLanguage(language) {

    if (
        language !== "en" &&
        language !== "ta"
    ) {
        language = "en";
    }

    currentLanguage =
        language;

    localStorage.setItem(
        "lifelinkLanguage",
        currentLanguage
    );

    applyLanguage(
        currentLanguage
    );
}

// =========================================================
// APPLY LANGUAGE
// =========================================================

function applyLanguage(language) {

    currentLanguage =
        language;

    const elements =
        document.querySelectorAll(
            "[data-lang]"
        );

    elements.forEach(element => {

        const key =
            element.getAttribute(
                "data-lang"
            );

        const translated =
            translations[language] &&
            translations[language][key];

        if (
            translated !== undefined
        ) {

            element.textContent =
                translated;
        }

    });

    const placeholders =
        document.querySelectorAll(
            "[data-placeholder]"
        );

    placeholders.forEach(element => {

        const key =
            element.getAttribute(
                "data-placeholder"
            );

        const translated =
            translations[language] &&
            translations[language][key];

        if (
            translated !== undefined
        ) {

            element.placeholder =
                translated;
        }

    });

    const languageButtons =
        document.querySelectorAll(
            ".language-btn"
        );

    languageButtons.forEach(button => {

        button.textContent =
            language === "en"
                ? "தமிழ்"
                : "English";

    });
}

// =========================================================
// LOAD SAVED LANGUAGE
// =========================================================

function loadSavedLanguage() {

    const savedLanguage =
        localStorage.getItem(
            "lifelinkLanguage"
        );

    if (
        savedLanguage === "ta" ||
        savedLanguage === "en"
    ) {

        currentLanguage =
            savedLanguage;
    }

    applyLanguage(
        currentLanguage
    );
}

// =========================================================
// REGISTER FORM
// =========================================================

function setupRegisterForm() {

    const form =
        document.getElementById(
            "donorForm"
        );

    if (!form) {
        return;
    }

    form.addEventListener(
        "submit",
        async function(event) {

            event.preventDefault();

            const formData =
                new FormData(form);

            const data = {

                name:
                    formData.get("name"),

                age:
                    formData.get("age"),

                gender:
                    formData.get("gender"),

                blood_group:
                    formData.get(
                        "blood_group"
                    ),

                location:
                    formData.get(
                        "location"
                    ),

                phone:
                    formData.get("phone"),

                email:
                    formData.get("email"),

                last_donation:
                    formData.get(
                        "last_donation"
                    ),

                availability:
                    formData.get(
                        "availability"
                    ) || "Available"
            };

            if (
                !data.name ||
                !data.age ||
                !data.blood_group ||
                !data.location ||
                !data.phone
            ) {

                showToast(
                    t("fillRequired"),
                    "error"
                );

                return;
            }

            const phonePattern =
                /^[0-9+\-\s]{8,15}$/;

            if (
                !phonePattern.test(
                    data.phone
                )
            ) {

                showToast(
                    t("invalidPhone"),
                    "error"
                );

                return;
            }

            const result =
                await registerDonor(
                    data
                );

            if (result.success) {
                form.reset();
            }
        }
    );
}

// =========================================================
// MATCH FORM SUPPORT
// =========================================================

function setupMatchForm() {

    /*
     * Current index.html uses:
     *
     * onclick="findDonors()"
     *
     * So no form listener is required.
     */

    console.log(
        "LifeLink donor matching ready."
    );
}

// =========================================================
// GLOBAL FUNCTIONS
// =========================================================

window.findDonors =
    findDonors;

window.findBloodDonors =
    findDonors;

window.registerDonor =
    registerDonor;

window.enableLifeLinkNotifications =
    enableNotifications;

window.sendLifeLinkNotification =
    function(title, body) {

        if (
            !isNotificationSupported() ||
            Notification.permission !== "granted"
        ) {
            return;
        }

        try {

            new Notification(
                title,
                {
                    body: body,
                    icon:
                        "/static/favicon.ico"
                }
            );

        } catch (error) {

            console.error(
                "Browser notification error:",
                error
            );
        }
    };

window.setLanguage =
    setLanguage;

// =========================================================
// PAGE INITIALIZATION
// =========================================================

document.addEventListener(
    "DOMContentLoaded",
    function() {

        loadSavedLanguage();

        setupRegisterForm();

        setupMatchForm();

        setupNotificationButton();

        checkNotificationStatus();

        updateDonorCount();

        console.log(
            "LifeLink initialized successfully."
        );

    }
);