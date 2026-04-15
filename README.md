<div align="center">

> [!TIP]
> [📖 View Full Documentation](../Docs/README.md)

![WealthFam Branding](../Docs/Media/branding/wordmark.png)

### The Ultimate Family Finance Operating System

[![Demo Status](https://img.shields.io/badge/Demo-Live_🟢-success?style=for-the-badge&logo=render&logoColor=white)](https://wealthfam.onrender.com) &nbsp; [![Version](https://img.shields.io/badge/Version-2.0.0-blue?style=for-the-badge)](version.json)
<br><br>

[**🚀 Try Live Demo**](https://wealthfam.onrender.com) &nbsp;•&nbsp; [**📂 Documentation**](../Docs/) &nbsp;•&nbsp; [**☁️ Deploy Now**](#-cloud-deployment-one-click)

<br>

**Demo Credentials**: `demo@demo.com` • `demo123`

---

[![Docker Hub](https://img.shields.io/docker/v/wglabz/wealthfam?label=Docker%20Hub&logo=docker&color=2496ED)](https://hub.docker.com/r/wglabz/wealthfam)
[![Docker Pulls](https://img.shields.io/docker/pulls/wglabz/wealthfam?logo=docker&color=2496ED)](https://hub.docker.com/r/wglabz/wealthfam)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Download Mobile APK](https://img.shields.io/badge/Download-Mobile%20APK-success?logo=android&logoColor=white)](app-release.apk)
[![Deploy to Koyeb](https://img.shields.io/badge/Deploy-Koyeb-121212?logo=koyeb)](https://app.koyeb.com/deploy?type=git&repository=github.com/oksbwn/wealthfam&branch=main&name=wealthfam)
[![Deploy to Railway](https://img.shields.io/badge/Deploy-Railway-0B0D0E?logo=railway)](https://railway.app/template/wealthfam)

</div>

## 🛠️ Tech Stack & Architecture

The WealthFam Backend is a high-performance REST API built for financial data orchestration and AI-powered intelligence.

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python)
- **Database**: [DuckDB](https://duckdb.org/) (Serverless SQL)
- **ORM**: [SQLAlchemy](https://www.sqlalchemy.org/)
- **AI Engine**: Gemini Pro for advanced transaction parsing.

### 📚 Key Documentation
- **[🔄 Data Ingestion Flow](../Docs/technical/architecture/ingestion.md)**: How transactions are parsed and deduplicated.
- **[🛠️ Development Setup](../Docs/technical/development/setup.md)**: How to run the backend locally.
- **[✨ System Features](../Docs/user/features.md)**: Overview of what the ecosystem supports.

## 🐳 Quick Start with Docker
The easiest way to run WealthFam is using our pre-built Docker image. You don't need to build anything yourself!

1. **Create a directory** for your data and configuration:
   ```bash
   mkdir wealthfam && cd wealthfam
   ```

2. **Create a `docker-compose.yml` file**:
   ```yaml
   version: '3.8'
   services:
     wealthfam:
       image: wglabz/wealthfam:latest
       container_name: wealthfam
       restart: unless-stopped
       ports:
         - "80:80"
       volumes:
         - ./data:/data
       environment:
         - DATABASE_URL=duckdb:////data/family_finance_v3.duckdb
   ```

3. **Run the application**:
   ```bash
   docker-compose up -d
   ```

## 🔐 Security & Privacy
WealthFam is designed with data privacy at its core. By leveraging DuckDB, your financial data remains in a local, high-performance database, ensuring you have full control over your intelligence.

---
*Maintained by the WealthFam Backend Team*
