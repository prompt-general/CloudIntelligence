# 🌌 CloudIntelligence Platform

[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2014-black?style=for-the-badge&logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Neo4j](https://img.shields.io/badge/Graph-Neo4j-4581C3?style=for-the-badge&logo=neo4j)](https://neo4j.com/)
[![Multi-Cloud](https://img.shields.io/badge/Cloud-AWS%20|%20GCP%20|%20Azure-orange?style=for-the-badge)](https://aws.amazon.com/)

> **The Ultimate Multi-Cloud Intelligence & Security Command Center.**  
> Monitor, Predict, and Secure your cloud infrastructure with AI-driven insights and graph-based attack path analysis.

---

## ✨ Executive Overview

CloudIntelligence is a state-of-the-art **Cloud Native Application Protection Platform (CNAPP)** designed for the modern enterprise. It bridges the gap between FinOps, SecOps, and Compliance by providing a unified "Single Pane of Glass" for all your cloud assets across AWS, GCP, and Azure.

---

## 🚀 Core Pillars

### 🛡️ 1. Advanced Security & Attack Path Engine
Beyond simple vulnerability lists, CloudIntelligence understands **Reachability**.
- **Neo4j Powered Graph Analysis**: Visualize complex attack vectors that traditional scanners miss.
- **Deep Attack Paths**: Identify multi-hop lateral movement risks from internet-exposed resources to critical data.
- **Blast Radius Analysis**: Instantly calculate the potential impact of a single compromised node.
- **Automated Remediation**: One-click security fixes and configuration hardening.

### 💰 2. Predictive Cost Intelligence (FinOps)
Stop reacting to bills and start predicting them.
- **ML-Based Forecasting**: 30-day cost projections using linear trend analysis and anomaly detection.
- **Intelligence Profiling**: Every resource gets a "Volatility Score" and "Efficiency Rating".
- **Multi-Cloud Optimization**: Unified savings recommendations across all providers (Idle VMs, Unused Buckets, Reserved Instances).

### ⚖️ 3. Continuous Compliance
Real-time audit-ready posture for global standards.
- **Framework Support**: SOC2, HIPAA, PCI-DSS, and ISO 27001.
- **Automated Evidence Collection**: No more manual spreadsheet tracking.
- **Drift Detection**: Instant alerts when a resource falls out of compliance.

---

## 🛠️ Technical Excellence

### Command Center (Stack)
| Layer | Technologies |
| :--- | :--- |
| **Frontend** | Next.js 14, TypeScript, Tailwind CSS, D3.js (Graph Visuals), Recharts |
| **Backend** | FastAPI (Python 3.10+), SQLAlchemy (Async), Pydantic v2 |
| **Database** | PostgreSQL (Relational), Neo4j (Graph), TimescaleDB (Time-series) |
| **AI/ML** | Scikit-learn (Isolation Forest for Anomaly Detection), Linear Forecasting |
| **Messaging** | WebSockets (Real-time broadcasting), Kafka (Event stream) |

---

## 🔌 Multi-Cloud Integration

CloudIntelligence is provider-agnostic. We integrate natively with:
*   **AWS**: IAM, EC2, S3, RDS, Lambda, CloudTrail.
*   **GCP**: Compute Engine, Cloud Storage, IAM policies, GKE.
*   **Azure**: Virtual Machines, Storage Accounts, Entra ID (AAD), Subscriptions.

---

## 🔧 Installation & Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- Neo4j Instance
- PostgreSQL

### 1. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
# Configure your .env file
uvicorn app.main:app --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 🗺️ Future Roadmap

- [ ] **LLM Remediation Agent**: AI-generated Infrastructure-as-Code (Terraform/CDK) PRs to fix security findings.
- [ ] **Kubernetes Deep Scan**: In-cluster security agent for GKE, EKS, and AKS.
- [ ] **External Attack Surface Management (EASM)**: Scanning your public domain footprint.
- [ ] **Advanced ML Models**: Implementing Facebook Prophet for complex seasonal billing trends.

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Built with ❤️ by the CloudIntelligence Engineering Team
</p>
