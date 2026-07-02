# Manipal Hackathon 2025: [NetKnights]

**Team Name:** NetKnights

**Problem Statement:** `Cybersecurity, Password Breach Detection and Behavioural Analysis`

---

## Introduction

In the digital era, organizations face growing cybersecurity challenges as cyberattacks become increasingly sophisticated. One of the most common and damaging threats is password breaches, which can compromise sensitive information and disrupt critical operations. Traditional security measures often fail to detect subtle anomalies in user behaviour that precede or follow such breaches. To address this, advanced behavioural analysis and password breach detection systems are essential. By combining real-time monitoring, anomaly detection, and intelligent threat analysis, organizations can proactively identify suspicious activities, prevent unauthorized access, and strengthen their overall security posture.

---

## Access & Live Demo

The website is currently not deployed.

---

## Local Deployment Instructions

 However, for a complete technical review, code verification, and to ensure reproducibility, the following instructions are provided to set up and run the project locally. This allows for a thorough assessment of the project's architecture and build process.

### Method 1: Using Docker 

1.  **Clone the repository:**
    ```bash
    git clone [git@github.com:Manipal-Hackathon-2025/NetKnights.git](git@github.com:Manipal-Hackathon-2025/NetKnights.git)
    cd NetKnights
    ```

2.  **Build the Docker image:**
    ```bash
    docker compose up -d .
    ```

3.  **Access the application:**
    Backend API: http://localhost:8000

    Frontend: http://localhost:3000

    Kibana: http://localhost:5601

    Elasticsearch API: http://localhost:9200

    Access the Frontend to view the demo page, access kibana to view the analytics dashboard and logs.

    
### Method 2: Without Using Docker

1. **Clone this repository**
   ```bash
   git clone [git@github.com:Manipal-Hackathon-2025/NetKnights.git](git@github.com:Manipal-Hackathon-2025/NetKnights.git)
    cd NetKnights
   ```
2. **Run this command to run the frontend**
   ```bash
   npm install zxcvbn
   npm run dev
   ```
3. **Run this command to run the backend**
   ```bash
   pip install -r requirements.txt
   uvicorn backend:app --reload --port 8000
   ```

## 🌐 Web Application

### **Feature 1: [Transaction History Between Admin Users](#feature-1-transaction-history-between-admin-users)**
This feature allows web administrators to view detailed transaction logs between two admin accounts. It provides insights into activities such as fund transfers, data exchanges, or access requests — helping ensure accountability and transparency within the admin network.

---

### **Feature 2: [Password Breach Threat Detection](#feature-2-password-breach-threat-detection)**
This functionality continuously monitors user credentials to identify potential threats resulting from password breaches. If a password is found to be compromised or reused in unsafe contexts, the system alerts administrators and recommends immediate security actions.

---

### **Feature 3: [Integration with SIEM Tools](#feature-3-integration-with-siem-tools)**
The platform integrates with Security Information and Event Management (SIEM) tools to aggregate, analyze, and visualize security-related data in real time. This enables advanced threat detection, incident response, and centralized monitoring across the entire system.

---

### **Feature 4: [Biometric Authentication](#feature-5-biometric-authentication)**
The application now supports biometric authentication mechanisms for enhanced user verification.

---

### **Feature 5: [Anomaly Detection using Elasticsearch and Kibana](#feature-6-anomaly-detection-using-elasticsearch-and-kibana)**
Real-time behavior anomaly detection with visualization on Kibana dashboards.

---

### **Feature 6: [Random Forest Anomaly Detection with User Alerts](#feature-7-random-forest-anomaly-detection-with-user-alerts)**
ML-based anomaly detection using the Random Forest algorithm to identify suspicious activity and notify users.

---

### **Feature 7: [Salting and Peppering for Password Encryption](#feature-8-salting-and-peppering-for-password-encryption)**
Enhanced password security by applying **salting** and **peppering** techniques during login.



---

## Tech Stack

List the primary technologies, frameworks, and tools used to build your project.

* **Frontend:** `React, Next.js`
* **Backend:** `FastAPI`
* **Database:** `PostgreSQL`
* **Machine Learning:** `None`
* **Deployment:** `Docker`
