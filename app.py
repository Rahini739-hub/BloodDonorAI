from flask import Flask, render_template, request, jsonify
import sqlite3
import pandas as pd
from datetime import datetime
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier

app = Flask(__name__)

DATABASE = "blood_donor.db"
DATASET = "donors.csv"


# ==========================================
# DATABASE
# ==========================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS donors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            blood_group TEXT NOT NULL,
            location TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            last_donation TEXT,
            availability TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# ==========================================
# LOAD DATASET
# ==========================================

def load_dataset():

    try:
        df = pd.read_csv(DATASET)

        print("Dataset loaded successfully!")
        print("Dataset records:", len(df))

        return df

    except Exception as e:
        print("Dataset error:", e)
        return pd.DataFrame()


# ==========================================
# AI MODEL
# ==========================================

def train_model():

    df = load_dataset()

    if df.empty:
        return None, None

    # Encode categorical values
    blood_encoder = LabelEncoder()
    location_encoder = LabelEncoder()
    availability_encoder = LabelEncoder()

    df["blood_code"] = blood_encoder.fit_transform(
        df["blood_group"]
    )

    df["location_code"] = location_encoder.fit_transform(
        df["location"]
    )

    df["availability_code"] = availability_encoder.fit_transform(
        df["availability"]
    )

    # Target:
    # 1 = available donor
    # 0 = unavailable donor
    df["target"] = (
        df["availability"] == "Available"
    ).astype(int)

    X = df[
        [
            "blood_code",
            "location_code",
            "availability_code",
            "age"
        ]
    ]

    y = df["target"]

    model = RandomForestClassifier(
        n_estimators=50,
        random_state=42
    )

    model.fit(X, y)

    print("AI model trained successfully!")

    return model, df


# ==========================================
# BLOOD COMPATIBILITY
# ==========================================

compatibility = {

    "A+": ["A+", "A-", "O+", "O-"],

    "A-": ["A-", "O-"],

    "B+": ["B+", "B-", "O+", "O-"],

    "B-": ["B-", "O-"],

    "AB+": [
        "A+", "A-",
        "B+", "B-",
        "AB+", "AB-",
        "O+", "O-"
    ],

    "AB-": [
        "A-", "B-",
        "AB-", "O-"
    ],

    "O+": ["O+", "O-"],

    "O-": ["O-"]
}


# ==========================================
# HOME PAGE
# ==========================================

@app.route("/")
def home():

    df = load_dataset()
    dataset_count = len(df)

    conn = get_db()

    live_count = conn.execute(
        "SELECT COUNT(*) FROM donors"
    ).fetchone()[0]

    conn.close()

    total_count = dataset_count + live_count

    return render_template(
        "index.html",
        donor_count=total_count
    )


# ==========================================
# REGISTER DONOR
# ==========================================

@app.route("/register", methods=["POST"])
def register():

    data = request.get_json()

    required = [
        "name",
        "age",
        "gender",
        "blood_group",
        "location",
        "phone",
        "availability"
    ]

    for field in required:

        if not data.get(field):

            return jsonify({
                "success": False,
                "message":
                f"Please enter {field.replace('_', ' ')}."
            }), 400

    try:

        conn = get_db()

        conn.execute("""
            INSERT INTO donors (
                name,
                age,
                gender,
                blood_group,
                location,
                phone,
                email,
                last_donation,
                availability,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (

            data["name"],
            data["age"],
            data["gender"],
            data["blood_group"],
            data["location"],
            data["phone"],
            data.get("email", ""),
            data.get("last_donation", ""),
            data["availability"],
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        ))

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "message":
            "Donor registered successfully."
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message":
            "Database error: " + str(e)
        }), 500


# ==========================================
# DONOR COUNT
# ==========================================

@app.route("/donor-count")
def donor_count():

    df = load_dataset()

    dataset_count = len(df)

    conn = get_db()

    live_count = conn.execute(
        "SELECT COUNT(*) FROM donors"
    ).fetchone()[0]

    conn.close()

    return jsonify({
        "count": dataset_count + live_count
    })


# ==========================================
# AI DONOR MATCHING
# ==========================================

@app.route("/match", methods=["POST"])
def match():

    data = request.get_json()

    required_blood = data.get("blood_group")

    location = data.get(
        "location",
        ""
    ).strip().lower()

    emergency = data.get(
        "emergency",
        False
    )

    if not required_blood:

        return jsonify({
            "success": False,
            "message":
            "Please select a blood group."
        })

    compatible_groups = compatibility.get(
        required_blood,
        []
    )

    results = []


    # ======================================
    # DATASET DONORS
    # ======================================

    df = load_dataset()

    if not df.empty:

        for _, donor in df.iterrows():

            blood = str(
                donor["blood_group"]
            ).strip()

            availability = str(
                donor["availability"]
            ).strip()

            # Only available donors
            if availability != "Available":
                continue

            # Check compatibility
            if blood not in compatible_groups:
                continue

            score = 0

            # Exact blood group
            if blood == required_blood:
                score += 50
            else:
                score += 35

            # Location matching
            donor_location = str(
                donor["location"]
            ).lower()

            if location and location in donor_location:
                score += 30
            else:
                score += 10

            # Emergency priority
            if emergency:
                score += 20

            score = min(score, 100)

            results.append({

                "name": str(
                    donor["name"]
                ),

                "blood_group": blood,

                "location": str(
                    donor["location"]
                ),

                "phone": str(
                    donor["phone"]
                ),

                "email": str(
                    donor["email"]
                ),

                "availability":
                    availability,

                "match_score": score,

                "source": "AI Dataset"
            })


    # ======================================
    # LIVE REGISTERED DONORS
    # ======================================

    conn = get_db()

    live_donors = conn.execute("""
        SELECT *
        FROM donors
        WHERE availability = 'Available'
    """).fetchall()

    conn.close()


    for donor in live_donors:

        blood = donor["blood_group"]

        if blood not in compatible_groups:
            continue

        score = 0

        # Exact blood group
        if blood == required_blood:
            score += 50
        else:
            score += 35

        # Location
        donor_location = (
            donor["location"].lower()
        )

        if location and location in donor_location:
            score += 30
        else:
            score += 10

        # Emergency
        if emergency:
            score += 20

        score = min(score, 100)

        results.append({

            "name":
                donor["name"],

            "blood_group":
                blood,

            "location":
                donor["location"],

            "phone":
                donor["phone"],

            "email":
                donor["email"],

            "availability":
                donor["availability"],

            "match_score":
                score,

            "source":
                "Registered Donor"
        })


    # ======================================
    # SORT BEST MATCH FIRST
    # ======================================

    results.sort(
        key=lambda x:
        x["match_score"],
        reverse=True
    )


    return jsonify({

        "success": True,

        "count":
            len(results),

        "results":
            results[:10]
    })


# ==========================================
# START APPLICATION
# ==========================================

if __name__ == "__main__":

    init_db()

    load_dataset()

    model, dataset = train_model()

    print("----------------------------------")
    print("LifeLink AI Blood Donor System")
    print("Dataset + ML + SQLite Ready")
    print("----------------------------------")

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )