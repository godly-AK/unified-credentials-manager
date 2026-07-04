# Unified Credentials Manager: Live Demo Script

This script is designed to help you walk an interviewer, recruiter, or team member through the core features of the Unified Credentials Manager. It highlights the architecture, the rigid security hygiene, the machine learning anomaly detection, and the cryptographic mobile app reset flow.

---

## Prerequisites (Before the Call)
Make sure your environment is running:
1. **PostgreSQL** is running (`localhost:5432`)
2. **Elasticsearch** is running (`localhost:9200`)
3. In a terminal, start the FastAPI backend:
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

---

## Step 1: The Modern Backend & Security Rigor
**Goal:** Show off the professional architecture and strict password hygiene.

1. Open your browser and navigate to the auto-generated Swagger UI: `http://localhost:8000/docs`.
   - *Talking point:* "The backend is built on a modern FastAPI architecture. All endpoints use strict Pydantic schemas for validation, replacing loose JSON parsing."
2. Expand the `POST /api/register` endpoint.
3. Attempt to register a user with a weak, compromised password like `password123`.
   - *Talking point:* "When a user registers or changes their password, we don't just hash it. The backend checks it against the **HaveIBeenPwned API** to ensure it hasn't been leaked, runs it through a **Credential Hygiene Scanner**, and checks a local **Bloom Filter** to prevent historical password reuse."
   - *Action:* Show the API rejecting the password because it appeared in breaches or is too weak.

---

## Step 2: Threat Simulation (Data Seeding)
**Goal:** Set the stage for the anomaly detector by simulating a targeted attack on a specific user.

1. Open a new terminal window.
2. Run the seeder script:
   ```bash
   cd backend
   python seed.py
   ```
3. *Talking point:* "I've just run a seeder script. It creates a clean `demo_user` in our PostgreSQL database and simulates weeks of normal login behavior. However, it also injects a few recent anomalous login attempts from foreign IP addresses and unrecognized user agents directly into our Elasticsearch cluster."

---

## Step 3: AI Threat Detection
**Goal:** Demonstrate the asynchronous Machine Learning worker catching the bad actor.

1. In the same terminal, run the anomaly detector:
   ```bash
   python Ano_detect.py
   ```
2. *Talking point:* "This is our offline ML worker. In a real environment, it runs on a cron job. It fetches the latest logs from Elasticsearch, extracts features like IP reputation and session duration, and feeds them into a trained Random Forest model."
3. *Action:* Point to the console output. You will see the script identify `demo_user` as anomalous and fire a database update to block the account.
4. Go back to the Swagger UI (`/docs`) and try to `POST /api/login` as `demo_user` with the password `Correct-Horse-Battery-42!`.
   - *Action:* The API will reject the login with `User account is blocked.`

---

## Step 4: The Mobile App Cryptographic Recovery
**Goal:** Explain the final, most advanced piece of the architecture—recovering the account without relying on insecure email links.

1. *Talking point:* "Because the account is blocked due to suspicious activity, an email reset link is too risky—the attacker might have compromised their email as well."
2. *Talking point:* "Instead, we use our Mobile App as a trusted hardware key. When the user first sets up the mobile app, it generates a cryptographic Public/Private keypair and registers the Public Key with this backend."
3. *Talking point:* "To recover the account, the backend issues a random challenge nonce. The mobile device uses its locally secured Private Key to sign that nonce. The backend verifies the signature, guaranteeing the request came from the owner's physical device, and securely processes the password reset."

---

**End of Demo!**
