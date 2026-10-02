from flask import Flask, render_template, request, jsonify
import sqlite3
import math
import os
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, messaging


app = Flask(__name__)

DB_NAME = "blood_donor.db"
FIREBASE_SERVICE_ACCOUNT = "firebase-service-account.json"


# =========================================================
# FIREBASE INITIALIZATION
# =========================================================

firebase_ready = False

try:
    if os.path.exists(FIREBASE_SERVICE_ACCOUNT):

        if not firebase_admin._apps:
            cred = credentials.Certificate(
                FIREBASE_SERVICE_ACCOUNT
            )

            firebase_admin.initialize_app(
                cred
            )

        firebase_ready = True

        print("Firebase Admin initialized successfully.")

    else:

        print(
            "WARNING: firebase-service-account.json not found."
        )

except Exception as e:

    print(
        "WARNING: Firebase initialization failed:",
        e
    )


# =========================================================
# BLOOD GROUP COMPATIBILITY
# =========================================================

COMPATIBILITY = {
    "A+": ["A+", "A-", "O+", "O-"],
    "A-": ["A-", "O-"],
    "B+": ["B+", "B-", "O+", "O-"],
    "B-": ["B-", "O-"],
    "AB+": [
        "A+", "A-", "B+", "B-",
        "AB+", "AB-", "O+", "O-"
    ],
    "AB-": ["A-", "B-", "AB-", "O-"],
    "O+": ["O+", "O-"],
    "O-": ["O-"]
}


# =========================================================
# LOCATION COORDINATES
# =========================================================

LOCATION_COORDS = {
    "chennai": (13.0827, 80.2707),
    "madurai": (9.9252, 78.1198),
    "coimbatore": (11.0168, 76.9558),
    "trichy": (10.7905, 78.7047),
    "tiruchirappalli": (10.7905, 78.7047),
    "salem": (11.6643, 78.1460),
    "tirunelveli": (8.7139, 77.7567),
    "erode": (11.3410, 77.7172),
    "thanjavur": (10.7870, 79.1378),
    "karur": (10.9601, 78.0766),
    "dindigul": (10.3673, 77.9803),
    "tiruppur": (11.1085, 77.3411),
    "pollachi": (10.6627, 77.0067),
    "namakkal": (11.2194, 78.1677),
    "vellore": (12.9165, 79.1325),
    "pondicherry": (11.9416, 79.8083),
    "puducherry": (11.9416, 79.8083),
    "tenkasi": (8.9590, 77.3152),
    "thoothukudi": (8.7642, 78.1348),
    "virudhunagar": (9.5680, 77.9624),
    "sivakasi": (9.4492, 77.7974),
    "ramanathapuram": (9.3639, 78.8395),
    "theni": (10.0104, 77.4768),
    "perambalur": (11.2320, 78.8801),
    "ariyalur": (11.1401, 79.0786),
    "cuddalore": (11.7480, 79.7714),
    "villupuram": (11.9401, 79.4861),
    "kanchipuram": (12.8342, 79.7036),
    "tiruvallur": (13.1430, 79.9082),
    "nagapattinam": (10.7672, 79.8449),
    "mayiladuthurai": (11.1035, 79.6550),
    "dharmapuri": (12.1211, 78.1582),
    "krishnagiri": (12.5186, 78.2137),
    "ooty": (11.4102, 76.6950),
    "nilgiris": (11.4916, 76.7337)
}


# =========================================================
# LOCATION ALIASES
# =========================================================

LOCATION_ALIASES = {
    "thenkasi": "tenkasi",
    "tenkasi district": "tenkasi",
    "tenkasi city": "tenkasi",

    "tirupur": "tiruppur",
    "tiruppur district": "tiruppur",

    "trichy": "trichy",
    "tiruchirappalli": "trichy",
    "tiruchirapalli": "trichy",
    "trichirapalli": "trichy",

    "pondicherry": "puducherry",
    "pondy": "puducherry",

    "madras": "chennai",

    "kovai": "coimbatore",
    "coimbatore city": "coimbatore",

    "nellai": "tirunelveli",
    "tirunelveli city": "tirunelveli",

    "tanjore": "thanjavur",
    "tanjavur": "thanjavur",

    "tuticorin": "thoothukudi",
    "tuticorin city": "thoothukudi",

    "ootacamund": "ooty",
    "udhagamandalam": "ooty"
}


# =========================================================
# DATABASE
# =========================================================

def get_db():

    conn = sqlite3.connect(DB_NAME)

    conn.row_factory = sqlite3.Row

    return conn


def init_db():

    conn = get_db()

    # -----------------------------------------------------
    # Donors table
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS donors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            blood_group TEXT NOT NULL,
            location TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            email TEXT,
            last_donation TEXT,
            availability TEXT NOT NULL,
            created_at TEXT NOT NULL,
            fcm_token TEXT
        )
    """)

    # -----------------------------------------------------
    # Add FCM token to existing database
    # -----------------------------------------------------

    donor_columns = conn.execute(
        "PRAGMA table_info(donors)"
    ).fetchall()

    donor_column_names = [
        column["name"]
        for column in donor_columns
    ]

    if "fcm_token" not in donor_column_names:

        conn.execute("""
            ALTER TABLE donors
            ADD COLUMN fcm_token TEXT
        """)

        print(
            "Added fcm_token column to donors table."
        )

    # -----------------------------------------------------
    # Check old notifications table
    # -----------------------------------------------------

    columns = conn.execute(
        "PRAGMA table_info(notifications)"
    ).fetchall()

    column_names = [
        column["name"]
        for column in columns
    ]

    # -----------------------------------------------------
    # Old table migration
    # -----------------------------------------------------

    if columns and "donor_id" not in column_names:

        conn.execute(
            "ALTER TABLE notifications "
            "RENAME TO notifications_old"
        )

    # -----------------------------------------------------
    # Notifications table
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            donor_id INTEGER,
            donor_name TEXT NOT NULL,
            donor_phone TEXT NOT NULL,
            blood_group TEXT NOT NULL,
            location TEXT NOT NULL,
            distance REAL DEFAULT 0,
            message TEXT NOT NULL,
            emergency INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Pending',
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()

    conn.close()


# =========================================================
# FIREBASE PUSH NOTIFICATION
# =========================================================

def send_push_notification(
    fcm_token,
    title,
    body,
    donor_id=None,
    blood_group=None,
    location=None,
    emergency=False
):

    if not firebase_ready:

        return {
            "success": False,
            "message":
                "Firebase Admin is not initialized."
        }

    if not fcm_token:

        return {
            "success": False,
            "message":
                "Donor does not have an FCM token."
        }

    try:

        message = messaging.Message(

            notification=messaging.Notification(
                title=title,
                body=body
            ),

            data={
                "type": "blood_request",
                "donor_id":
                    str(donor_id)
                    if donor_id is not None
                    else "",

                "blood_group":
                    str(blood_group)
                    if blood_group
                    else "",

                "location":
                    str(location)
                    if location
                    else "",

                "emergency":
                    "true"
                    if emergency
                    else "false"
            },

            token=fcm_token
        )

        response = messaging.send(
            message
        )

        print(
            "FCM notification sent:",
            response
        )

        return {
            "success": True,
            "message_id": response
        }

    except Exception as e:

        print(
            "FCM notification failed:",
            e
        )

        error_text = str(e)

        # -------------------------------------------------
        # If token is no longer valid
        # -------------------------------------------------

        if (
            "registration-token-not-registered"
            in error_text.lower()
            or
            "unregistered"
            in error_text.lower()
        ):

            try:

                conn = get_db()

                conn.execute("""
                    UPDATE donors
                    SET fcm_token = NULL
                    WHERE fcm_token = ?
                """, (
                    fcm_token,
                ))

                conn.commit()

                conn.close()

                print(
                    "Invalid FCM token removed."
                )

            except Exception as cleanup_error:

                print(
                    "Token cleanup failed:",
                    cleanup_error
                )

        return {
            "success": False,
            "message": error_text
        }


# =========================================================
# LOCATION FUNCTIONS
# =========================================================

def normalize_location(location):

    if location is None:

        return ""

    location = str(
        location
    ).strip().lower()

    location = " ".join(
        location.split()
    )

    if location in LOCATION_ALIASES:

        return LOCATION_ALIASES[
            location
        ]

    return location


def get_coordinates(location):

    normalized = normalize_location(
        location
    )

    return LOCATION_COORDS.get(
        normalized
    )


def calculate_distance(
    location1,
    location2
):

    normalized1 = normalize_location(
        location1
    )

    normalized2 = normalize_location(
        location2
    )

    # Same location
    if (
        normalized1 == normalized2
        and normalized1 != ""
    ):

        return 0.0

    coord1 = get_coordinates(
        normalized1
    )

    coord2 = get_coordinates(
        normalized2
    )

    if not coord1 or not coord2:

        return 9999

    lat1, lon1 = coord1
    lat2, lon2 = coord2

    R = 6371

    lat1 = math.radians(
        lat1
    )

    lat2 = math.radians(
        lat2
    )

    dlat = math.radians(
        lat2 - lat1
    )

    dlon = math.radians(
        lon2 - lon1
    )

    a = (
        math.sin(dlat / 2) ** 2
        +
        math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    c = (
        2
        * math.atan2(
            math.sqrt(a),
            math.sqrt(1 - a)
        )
    )

    return R * c


# =========================================================
# AI MATCHING SCORE
# =========================================================

def calculate_match(
    donor_blood,
    donor_location,
    required_blood,
    required_location,
    emergency=False
):

    reasons = []

    score = 0

    # -----------------------------------------------------
    # Blood group
    # -----------------------------------------------------

    if donor_blood == required_blood:

        score += 50

        reasons.append(
            "Exact blood group match"
        )

    elif donor_blood in COMPATIBILITY.get(
        required_blood,
        []
    ):

        score += 30

        reasons.append(
            f"Compatible blood group ({donor_blood})"
        )

    else:

        return 0, [
            "Blood group not compatible"
        ]

    # -----------------------------------------------------
    # Location
    # -----------------------------------------------------

    donor_normalized = normalize_location(
        donor_location
    )

    request_normalized = normalize_location(
        required_location
    )

    exact_location = (
        donor_normalized != ""
        and request_normalized != ""
        and donor_normalized
        == request_normalized
    )

    distance = calculate_distance(
        donor_location,
        required_location
    )

    if exact_location:

        score += 40

        reasons.append(
            "Same location as patient"
        )

    elif distance <= 10:

        score += 30

        reasons.append(
            "Very close to patient"
        )

    elif distance <= 50:

        score += 25

        reasons.append(
            "Nearby donor"
        )

    elif distance <= 100:

        score += 15

        reasons.append(
            "Within reachable distance"
        )

    elif distance < 9999:

        score += 5

        reasons.append(
            "Farther location"
        )

    else:

        reasons.append(
            "Location distance unavailable"
        )

    # -----------------------------------------------------
    # Availability
    # -----------------------------------------------------

    score += 10

    reasons.append(
        "Currently available"
    )

    # -----------------------------------------------------
    # Emergency
    # -----------------------------------------------------

    if emergency:

        score += 10

        reasons.append(
            "Emergency priority applied"
        )

    score = min(
        score,
        100
    )

    return score, reasons


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    conn = get_db()

    donor_count = conn.execute(
        "SELECT COUNT(*) FROM donors"
    ).fetchone()[0]

    conn.close()

    return render_template(
        "index.html",
        donor_count=donor_count
    )


# =========================================================
# REGISTER DONOR
# =========================================================

@app.route(
    "/register",
    methods=["POST"]
)
def register():

    try:

        data = request.get_json()

        if not data:

            return jsonify({
                "success": False,
                "message": "Invalid request"
            }), 400

        name = data.get(
            "name",
            ""
        ).strip()

        age = data.get(
            "age"
        )

        gender = data.get(
            "gender",
            ""
        ).strip()

        blood_group = data.get(
            "blood_group",
            ""
        ).strip()

        location = data.get(
            "location",
            ""
        ).strip()

        phone = data.get(
            "phone",
            ""
        ).strip()

        email = data.get(
            "email",
            ""
        ).strip()

        last_donation = data.get(
            "last_donation",
            ""
        ).strip()

        availability = data.get(
            "availability",
            "Available"
        ).strip()

        fcm_token = data.get(
            "fcm_token",
            ""
        ).strip()

        # -------------------------------------------------
        # Validation
        # -------------------------------------------------

        if not name:

            return jsonify({
                "success": False,
                "message": "Name is required"
            }), 400

        if not age:

            return jsonify({
                "success": False,
                "message": "Age is required"
            }), 400

        if blood_group not in COMPATIBILITY:

            return jsonify({
                "success": False,
                "message": "Invalid blood group"
            }), 400

        if not location:

            return jsonify({
                "success": False,
                "message": "Location is required"
            }), 400

        if not phone:

            return jsonify({
                "success": False,
                "message": "Phone number is required"
            }), 400

        normalized_location = normalize_location(
            location
        )

        conn = get_db()

        # -------------------------------------------------
        # Check existing donor
        # -------------------------------------------------

        existing = conn.execute(
            """
            SELECT id
            FROM donors
            WHERE phone = ?
            """,
            (phone,)
        ).fetchone()

        if existing:

            # -------------------------------------------------
            # If donor already exists but has a new FCM token,
            # update the token so the phone can receive pushes.
            # -------------------------------------------------

            if fcm_token:

                conn.execute("""
                    UPDATE donors
                    SET fcm_token = ?
                    WHERE phone = ?
                """, (
                    fcm_token,
                    phone
                ))

                conn.commit()

                conn.close()

                return jsonify({
                    "success": True,
                    "message":
                        "Donor device notification updated"
                })

            conn.close()

            return jsonify({
                "success": False,
                "message":
                    "Phone number already registered"
            }), 409

        # -------------------------------------------------
        # Insert donor
        # -------------------------------------------------

        conn.execute("""
            INSERT INTO donors
            (
                name,
                age,
                gender,
                blood_group,
                location,
                phone,
                email,
                last_donation,
                availability,
                created_at,
                fcm_token
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            int(age),
            gender,
            blood_group,
            normalized_location,
            phone,
            email,
            last_donation,
            availability,
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            fcm_token
        ))

        conn.commit()

        conn.close()

        return jsonify({
            "success": True,
            "message":
                "Donor registered successfully"
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# =========================================================
# FIND MATCHING DONORS
# =========================================================

@app.route(
    "/match",
    methods=["POST"]
)
def match_donors():

    try:

        data = request.get_json()

        if not data:

            return jsonify({
                "success": False,
                "message": "Invalid request"
            }), 400

        required_blood = data.get(
            "blood_group",
            ""
        ).strip()

        location = data.get(
            "location",
            ""
        ).strip()

        emergency = bool(
            data.get(
                "emergency",
                False
            )
        )

        # -------------------------------------------------
        # Validation
        # -------------------------------------------------

        if required_blood not in COMPATIBILITY:

            return jsonify({
                "success": False,
                "message":
                    "Please select a valid blood group"
            }), 400

        if not location:

            return jsonify({
                "success": False,
                "message":
                    "Please enter patient location"
            }), 400

        request_location = normalize_location(
            location
        )

        conn = get_db()

        # -------------------------------------------------
        # Get available donors
        # -------------------------------------------------

        donors = conn.execute("""
            SELECT *
            FROM donors
            WHERE LOWER(availability)
            IN ('available', 'yes')
        """).fetchall()

        results = []

        # -------------------------------------------------
        # AI matching
        # -------------------------------------------------

        for donor in donors:

            donor_location = normalize_location(
                donor["location"]
            )

            exact_location = (
                donor_location != ""
                and request_location != ""
                and donor_location
                == request_location
            )

            score, reasons = calculate_match(
                donor["blood_group"],
                donor_location,
                required_blood,
                request_location,
                emergency
            )

            if score <= 0:

                continue

            distance = calculate_distance(
                donor_location,
                request_location
            )

            if distance < 9999:

                distance_value = round(
                    distance,
                    1
                )

            else:

                distance_value = None

            results.append({

                "id":
                    donor["id"],

                "name":
                    donor["name"],

                "age":
                    donor["age"],

                "gender":
                    donor["gender"],

                "blood_group":
                    donor["blood_group"],

                "location":
                    donor["location"],

                "phone":
                    donor["phone"],

                "email":
                    donor["email"],

                "availability":
                    donor["availability"],

                "distance":
                    distance_value,

                "score":
                    score,

                "reasons":
                    reasons,

                "exact_location":
                    exact_location,

                "source":
                    "Registered Donor"
            })

        # -------------------------------------------------
        # Sort
        # -----------------------------------------------------

        results.sort(
            key=lambda x: (
                not x["exact_location"],

                -x["score"],

                x["distance"]
                if x["distance"] is not None
                else 9999
            )
        )

        # -------------------------------------------------
        # Nearby donors
        # -------------------------------------------------

        nearby_donors = []

        for donor in results:

            distance = donor["distance"]

            if donor["exact_location"]:

                nearby_donors.append(
                    donor
                )

            elif (
                distance is not None
                and distance <= 100
            ):

                nearby_donors.append(
                    donor
                )

        # Maximum 5 donors notified
        notify_donors = nearby_donors[:5]

        # -------------------------------------------------
        # Notification counters
        # -------------------------------------------------

        notification_records = 0
        push_sent = 0
        push_failed = 0
        duplicate_notifications = 0

        # -------------------------------------------------
        # Create notifications + FCM push
        # -------------------------------------------------

        for donor in notify_donors:

            if emergency:

                message = (
                    "EMERGENCY BLOOD REQUEST: "
                    f"{required_blood} blood is needed "
                    f"in {request_location}. "
                )

            else:

                message = (
                    "New blood request: "
                    f"{required_blood} blood is needed "
                    f"in {request_location}. "
                )

            if donor["distance"] is not None:

                message += (
                    f"You are approximately "
                    f"{donor['distance']} km away."
                )

            else:

                message += (
                    "Your location is nearby."
                )

            # -------------------------------------------------
            # Avoid duplicate notifications
            # -------------------------------------------------

            recent = conn.execute("""
                SELECT id
                FROM notifications
                WHERE donor_id = ?
                AND blood_group = ?
                AND location = ?
                AND created_at >=
                    datetime(
                        'now',
                        '-5 minutes'
                    )
            """, (
                donor["id"],
                required_blood,
                request_location
            )).fetchone()

            if recent:

                duplicate_notifications += 1

                continue

            # -------------------------------------------------
            # Insert internal notification
            # -------------------------------------------------

            conn.execute("""
                INSERT INTO notifications
                (
                    donor_id,
                    donor_name,
                    donor_phone,
                    blood_group,
                    location,
                    distance,
                    message,
                    emergency,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                donor["id"],
                donor["name"],
                donor["phone"],
                required_blood,
                request_location,
                donor["distance"]
                if donor["distance"] is not None
                else 0,
                message,
                1 if emergency else 0,
                "Pending",
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            ))

            notification_records += 1

            # -------------------------------------------------
            # SEND REAL PHONE PUSH NOTIFICATION
            # -------------------------------------------------

            fcm_token = donor["fcm_token"]

            if fcm_token:

                if emergency:

                    push_title = (
                        "LifeLink Emergency Blood Alert"
                    )

                else:

                    push_title = (
                        "LifeLink Blood Request"
                    )

                push_result = send_push_notification(
                    fcm_token=fcm_token,
                    title=push_title,
                    body=message,
                    donor_id=donor["id"],
                    blood_group=required_blood,
                    location=request_location,
                    emergency=emergency
                )

                if push_result["success"]:

                    push_sent += 1

                else:

                    push_failed += 1

            else:

                print(
                    f"No FCM token for donor "
                    f"{donor['name']} "
                    f"({donor['phone']})"
                )

        conn.commit()

        conn.close()

        # -------------------------------------------------
        # Response
        # -------------------------------------------------

        if push_sent > 0:

            response_message = (
                f"{notification_records} nearby "
                f"registered donor(s) notified. "
                f"{push_sent} phone notification(s) sent."
            )

        elif notification_records > 0:

            response_message = (
                f"{notification_records} nearby "
                "registered donor(s) notified. "
                "Phone push notification is not available "
                "for donors without a registered device."
            )

        else:

            response_message = (
                "No new nearby donor notifications were created."
            )

        return jsonify({

            "success": True,

            "count":
                len(results),

            "notified_donors":
                len(notify_donors),

            "notification_records":
                notification_records,

            "push_sent":
                push_sent,

            "push_failed":
                push_failed,

            "duplicate_notifications":
                duplicate_notifications,

            "firebase_ready":
                firebase_ready,

            "emergency":
                emergency,

            "requested_blood":
                required_blood,

            "requested_location":
                request_location,

            "message":
                response_message,

            "results":
                results[:10]
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# =========================================================
# GET DONOR NOTIFICATIONS
# =========================================================

@app.route(
    "/notifications",
    methods=["POST"]
)
def get_notifications():

    try:

        data = request.get_json()

        if not data:

            return jsonify({
                "success": False,
                "message": "Invalid request"
            }), 400

        phone = data.get(
            "phone",
            ""
        ).strip()

        if not phone:

            return jsonify({
                "success": False,
                "message":
                    "Enter registered phone number"
            }), 400

        conn = get_db()

        donor = conn.execute(
            """
            SELECT *
            FROM donors
            WHERE phone = ?
            """,
            (phone,)
        ).fetchone()

        if not donor:

            conn.close()

            return jsonify({
                "success": False,
                "message":
                    "Registered donor not found"
            }), 404

        notifications = conn.execute("""
            SELECT *
            FROM notifications
            WHERE donor_phone = ?
            ORDER BY id DESC
        """, (
            phone,
        )).fetchall()

        conn.close()

        notification_list = []

        for item in notifications:

            notification_list.append({

                "id":
                    item["id"],

                "blood_group":
                    item["blood_group"],

                "location":
                    item["location"],

                "distance":
                    round(
                        item["distance"],
                        1
                    ),

                "message":
                    item["message"],

                "emergency":
                    bool(
                        item["emergency"]
                    ),

                "status":
                    item["status"],

                "created_at":
                    item["created_at"]
            })

        return jsonify({

            "success": True,

            "donor_name":
                donor["name"],

            "blood_group":
                donor["blood_group"],

            "notifications":
                notification_list
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# =========================================================
# ACCEPT / DECLINE NOTIFICATION
# =========================================================

@app.route(
    "/notification-action",
    methods=["POST"]
)
def notification_action():

    try:

        data = request.get_json()

        notification_id = data.get(
            "notification_id"
        )

        phone = data.get(
            "phone",
            ""
        ).strip()

        action = data.get(
            "action",
            ""
        ).lower()

        if action not in [
            "accepted",
            "declined"
        ]:

            return jsonify({
                "success": False,
                "message":
                    "Invalid action"
            }), 400

        conn = get_db()

        notification = conn.execute("""
            SELECT *
            FROM notifications
            WHERE id = ?
            AND donor_phone = ?
        """, (
            notification_id,
            phone
        )).fetchone()

        if not notification:

            conn.close()

            return jsonify({
                "success": False,
                "message":
                    "Notification not found"
            }), 404

        conn.execute("""
            UPDATE notifications
            SET status = ?
            WHERE id = ?
            AND donor_phone = ?
        """, (
            action.title(),
            notification_id,
            phone
        ))

        conn.commit()

        conn.close()

        if action == "accepted":

            message = (
                "You accepted the blood request."
            )

        else:

            message = (
                "You declined the blood request."
            )

        return jsonify({
            "success": True,
            "message": message
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# =========================================================
# DONOR COUNT
# =========================================================

@app.route(
    "/donor-count"
)
def donor_count():

    conn = get_db()

    count = conn.execute(
        "SELECT COUNT(*) FROM donors"
    ).fetchone()[0]

    conn.close()

    return jsonify({

        "success": True,

        "total_donors":
            count
    })


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":

    init_db()

    print("=" * 60)

    print(
        "LifeLink - AI Blood Donor Matching System"
    )

    print(
        "Firebase Push Notifications:",
        "READY" if firebase_ready else "NOT READY"
    )

    print(
        "Local:"
    )

    print(
        "http://127.0.0.1:5000"
    )

    print(
        "Network:"
    )

    print(
        "http://0.0.0.0:5000"
    )

    print("=" * 60)

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )