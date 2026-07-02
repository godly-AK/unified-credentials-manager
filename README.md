<div align="center">

# Unified Credentials Manager

**A credential security platform combining breach-aware authentication, biometric re-verification, and ML-driven anomaly detection.**

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688)](#)
[![Flutter](https://img.shields.io/badge/Mobile-Flutter-02569B)](#)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-336791)](#)
[![ELK](https://img.shields.io/badge/SIEM-Elasticsearch%20%2B%20Kibana-005571)](#)
[![ML](https://img.shields.io/badge/Detection-Trained%20ML%20Model-F7931E)](#)
[![Docker](https://img.shields.io/badge/Deploy-Docker%20Compose-2496ED)](#)

</div>

---

## The problem

Password checks alone don't catch breaches — they catch typos. A credential can be technically "correct" and still be compromised, reused, or being entered by someone who isn't the account owner. This project treats authentication as a pipeline, not a single check: every credential is screened against real breach data before it's accepted, every password change requires device-backed biometric proof of identity, and login behavior is continuously scored for anomalies rather than trusted by default.

## What it does

- **Breach-aware password changes** — every new password is checked against Have I Been Pwned before it's accepted; passwords found in known breaches are rejected outright.
- **Password reuse prevention via Bloom filter** — a space-efficient Bloom filter tracks previously used password fingerprints, blocking reuse without storing plaintext history.
- **Password strength & hygiene scoring** — a weighted strength analyzer scores new passwords on entropy and common-pattern detection before they're accepted, in addition to client-side `zxcvbn` feedback during registration.
- **Native biometric re-authentication** — a companion Flutter app uses device-backed biometric signing (fingerprint/face, via hardware-key-backed signatures) to verify identity before sensitive actions like password changes are authorized.
- **ML-based anomaly detection** — a trained classifier scores login patterns (behavioral/contextual features) to flag anomalous activity and mark accounts for review.
- **Security event pipeline with SIEM dashboarding** — auth events flow into Elasticsearch and are visualized live in Kibana, with rate-limited endpoints (`slowapi`) to blunt brute-force and credential-stuffing attempts.
- **Automated breach-alert emails** — flagged anomalous activity triggers an email notification to the account owner.

## Architecture

```
 Flutter app (biometric key generation & signing)
        │
        ▼
 Next.js frontend  ──────────────►  FastAPI backend  ──────────────►  PostgreSQL
   (register / login /                 │  auth, rate limiting,          (hashed credentials,
    password-change UI)                │  HIBP + Bloom-filter checks,    password history)
                                        │  biometric signature verify
                                        │
                                        ├──────────► Elasticsearch ──► Kibana (SIEM dashboard)
                                        │
                                        └──────────► Trained ML model (anomaly scoring) ──► Email alert
```

## Tech stack

| Layer | Choice |
|---|---|
| Backend / API | FastAPI, SQLAlchemy, `slowapi` rate limiting |
| Mobile / biometric | Flutter, `biometric_signature` (hardware-key-backed device signing) |
| Frontend | Next.js, TypeScript, `zxcvbn` client-side strength scoring |
| Database | PostgreSQL |
| Security intelligence | Have I Been Pwned integration, Bloom-filter reuse tracking, trained ML anomaly classifier |
| Monitoring | Elasticsearch + Kibana |
| Deployment | Docker Compose |

## Running it

```bash
git clone https://github.com/godly-AK/unified-credentials-manager.git
cd unified-credentials-manager
```

Copy `.env.example` to `.env` and fill in your own values (SMTP credentials, JWT secret, DB connection) — the app will not start with placeholder secrets.

```bash
docker compose up -d
```

Backend: `http://localhost:8000` · Kibana: `http://localhost:5601`

For the mobile app:
```bash
cd auth_app
flutter pub get
flutter run
```

## Roadmap

- Wire the ML anomaly detector directly into the live login path (currently run as a standalone scoring pass over stored events) for real-time blocking rather than after-the-fact flagging
- Isolate the credential store into its own service/database boundary
- Migrate password hashing from bcrypt to Argon2id
- Admin portal for reviewing flagged accounts and audit trails directly, instead of via Kibana alone

---

<sub>**Base version originally built as a team hackathon MVP** — *NetKnights*, Manipal Hackathon 2025, problem statement: Cybersecurity / Password Breach Detection & Behavioural Analysis. The original team submission is preserved here: [Manipal-Hackathon-2025/NetKnights](https://github.com/Manipal-Hackathon-2025/NetKnights-Bugbounty). This repository is an independent, actively evolving continuation built on top of that base.</sub>
