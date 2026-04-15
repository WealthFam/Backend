# ⚙️ WealthFam Backend

<div align="center">

[![Version](https://img.shields.io/badge/Version-2.2.15-4338ca?style=for-the-badge)](https://github.com/WealthFam/backend)
[![Framework](https://img.shields.io/badge/FastAPI-0.109+-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Database](https://img.shields.io/badge/DuckDB-Serverless-FFF000?style=for-the-badge&logo=duckdb&logoColor=black)](https://duckdb.org/)
[![Status](https://img.shields.io/badge/Docs-Technical_Hub-e11d48?style=for-the-badge)](https://wealthfam.github.io/docs)
[![Docker Hub](https://img.shields.io/badge/Docker_Hub-wglabz/wealthfam--backend-blue?style=for-the-badge&logo=docker)](https://hub.docker.com/r/wglabz/wealthfam-backend)

**High-performance REST API for financial orchestration and AI intelligence.**  
*Built for speed, security, and local-first data privacy.*

</div>

---

## 🚀 Overview

The WealthFam Backend is the central nervous system of the ecosystem. It manages the transaction lifecycle, multi-tenant partitioning, and secure storage via local DuckDB instances. 

---

## 🛠️ Technical Stack at a Glance

For a detailed breakdown of our technical choices, see:  
[**📖 Deep Dive: The WealthFam Stack**](../Docs/technical/stack.md)

| Category | Technology |
| :--- | :--- |
| **Framework** | [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+) |
| **Storage** | [DuckDB](https://duckdb.org/) / SQLAlchemy |
| **Validation** | [Pydantic v2](https://docs.pydantic.dev/) |
| **AI Engine** | [Google Gemini Pro](https://ai.google.dev/) |

---

## 🏗️ Architecture

The backend follows a modular service pattern, ensuring that parsing, persistence, and presentation are strictly decoupled.

- **[🏛️ System Overview](../Docs/technical/architecture/system_overview.md)**
- **[🔄 Ingestion Logic](../Docs/technical/architecture/ingestion.md)**

---

## 🏁 Development Setup

To run the backend locally or contribute to the core services:

[**🛠️ Master Setup Guide**](../Docs/technical/getting_started.md)

---
<div align="center">
*Maintained by the WealthFam Backend Engineering Team*
</div>
