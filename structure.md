# Project Structure

This document outlines the high-level architecture of the Unified Credentials Manager repository. The codebase has been organized into a standard monorepo structure to separate concerns and make development easier.

## Directory Layout

```
unified-credentials-manager/
├── frontend/             # Next.js web application
│   ├── src/
│   │   ├── app/          # Next.js App Router 
│   │   ├── pages/        # Next.js API routes (and legacy Pages)
│   │   ├── components/   # React components
│   │   ├── lib/          # Utilities and data functions
│   │   └── styles/       # Global CSS
│   ├── public/           # Static assets (images, icons)
│   ├── package.json      # Node.js dependencies
│   ├── tailwind.config.js
│   └── ...               # Config files (tsconfig, eslint, next.config, etc.)
│
├── backend/              # Python FastAPI backend
│   ├── ml_artifacts/     # Machine Learning models (.pkl) & data files (.bloom, master.key)
│   ├── appbackend/       # Secondary backend logic
│   ├── main.py           # Core FastAPI application
│   ├── backend.py        # Database/Auth initialization & routing
│   ├── Ano_detect.py     # Anomaly detection & blocking logic
│   └── requirements.txt  # Python dependencies
│
├── mobile/               # Flutter cross-platform mobile application
│   ├── lib/              # Dart source code (login, signup, etc.)
│   ├── android/          # Android-specific native code
│   ├── ios/              # iOS-specific native code
│   └── pubspec.yaml      # Dart dependencies
│
├── infra/                # DevOps & Infrastructure configuration
│   └── elk/              # Docker compose for Elasticsearch, Logstash, Kibana
│
├── docs/                 # Documentation & reference materials
│   └── Round-2-TechnicalRulebook-Mhash-2025.pdf
│
├── .env                  # Local environment variables (DO NOT COMMIT)
├── .env.example          # Template for environment variables (Safe to commit)
├── .gitignore            # Git ignored files & directories
└── README.md             # Project overview
```

## How to Run

### Frontend
```bash
cd frontend
npm run dev
```

### Backend
```bash
cd backend
# Set up your venv and install dependencies
python backend.py # or whichever entry point you use
```

### Mobile
```bash
cd mobile
flutter run
```
