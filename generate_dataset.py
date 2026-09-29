import pandas as pd
import random

names = [
    "Arun", "Priya", "Karthik", "Divya", "Rahul",
    "Anitha", "Vijay", "Sneha", "Suresh", "Meena",
    "Hari", "Nisha", "Gokul", "Pavithra", "Surya"
]

locations = [
    "Dindigul",
    "Madurai",
    "Chennai",
    "Coimbatore",
    "Trichy",
    "Salem",
    "Tirunelveli",
    "Erode",
    "Thanjavur",
    "Karur"
]

blood_groups = [
    "A+", "A-", "B+", "B-",
    "AB+", "AB-", "O+", "O-"
]

genders = ["Male", "Female"]

data = []

for i in range(500):

    data.append({
        "donor_id": i + 1,
        "name": random.choice(names) + "_" + str(i + 1),
        "age": random.randint(18, 55),
        "gender": random.choice(genders),
        "blood_group": random.choice(blood_groups),
        "location": random.choice(locations),
        "phone": "9" + str(random.randint(100000000, 999999999)),
        "email": f"donor{i + 1}@lifelink.com",
        "availability": random.choice(
            ["Available", "Available", "Available", "Unavailable"]
        ),
        "last_donation_days": random.randint(30, 365)
    })

df = pd.DataFrame(data)

df.to_csv("donors.csv", index=False)

print("Dataset created successfully!")
print("Total records:", len(df))
print(df.head())