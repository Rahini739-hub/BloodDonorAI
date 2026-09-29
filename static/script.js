// ===============================
// DONOR REGISTRATION
// ===============================

const donorForm = document.getElementById("donorForm");

if (donorForm) {

    donorForm.addEventListener("submit", async function (event) {

        event.preventDefault();

        const donorData = {

            name: document.getElementById("name").value,

            age: document.getElementById("age").value,

            gender: document.getElementById("gender").value,

            blood_group:
                document.getElementById("blood_group").value,

            location:
                document.getElementById("location").value,

            phone:
                document.getElementById("phone").value,

            email:
                document.getElementById("email").value,

            last_donation:
                document.getElementById("last_donation").value,

            availability:
                document.getElementById("availability").value
        };


        try {

            const response = await fetch("/register", {

                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify(donorData)

            });


            const result = await response.json();


            if (result.success) {

                alert("❤️ Donor registered successfully!");

                donorForm.reset();

                updateDonorCount();

            } else {

                alert(result.message);

            }

        } catch (error) {

            alert("Server connection error.");

            console.error(error);

        }

    });
}


// ===============================
// UPDATE DONOR COUNT
// ===============================

async function updateDonorCount() {

    try {

        const response =
            await fetch("/donor-count");

        const data =
            await response.json();

        const counter =
            document.getElementById("donorCount");

        if (counter) {

            counter.textContent = data.count;

        }

    } catch (error) {

        console.error("Count error:", error);

    }
}


// ===============================
// FIND COMPATIBLE DONORS
// ===============================

async function findDonors() {

    const bloodGroup =
        document.getElementById("requestBlood").value;

    const location =
        document.getElementById("requestLocation").value;

    const emergency =
        document.getElementById("emergency").checked;

    const results =
        document.getElementById("results");


    if (!bloodGroup) {

        results.innerHTML =
            '<div class="no-results">Please select a blood group.</div>';

        return;

    }


    results.innerHTML =
        '<div class="no-results">🤖 AI is finding compatible donors...</div>';


    try {

        const response = await fetch("/match", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({

                blood_group: bloodGroup,

                location: location,

                emergency: emergency

            })

        });


        const data =
            await response.json();


        if (!data.success) {

            results.innerHTML =
                `<div class="no-results">${data.message}</div>`;

            return;

        }


        if (data.count === 0) {

            results.innerHTML = `
                <div class="no-results">
                    No matching donors found.
                    <br>
                    Please register a donor first.
                </div>
            `;

            return;

        }


        results.innerHTML = "";


        data.results.forEach(function (donor) {

            const card =
                document.createElement("div");

            card.className = "donor-result";


            card.innerHTML = `

                <h3>🩸 ${donor.name}</h3>

                <p>
                    Blood Group:
                    <strong>${donor.blood_group}</strong>
                </p>

                <p>
                    Location: ${donor.location}
                </p>

                <p>
                    Phone: ${donor.phone}
                </p>

                <p>
                    Availability: ${donor.availability}
                </p>

                <div class="match-score">
                    AI Match: ${donor.match_score}%
                </div>

            `;


            results.appendChild(card);

        });


    } catch (error) {

        results.innerHTML = `
            <div class="no-results">
                Server connection error.
            </div>
        `;

        console.error(error);

    }

}


// ===============================
// INITIAL LOAD
// ===============================

updateDonorCount();