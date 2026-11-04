# FlatHarmony

**Shared Living & Expense Coordination Platform**
Graduate Course Project in Advanced Software Engineering

## 1. Project Overview
Living with roommates often creates friction over shared finances and household maintenance. FlatHarmony is a lightweight Python web platform engineered to resolve this by unifying communal expense splitting, recurring chore rotations, AI-driven receipt ingestion, and graph-based debt simplification.

## 2. System Versions
* **Version 1.0 (Core):** Delivers a deterministic ledger, round-robin chore scheduling, and basic peer-to-peer debt tracking.
* **Version 2.0 (Intelligent):** Replaces manual typing with multimodal receipt parsing via the Google Gemini API, and simplifies multi-party debts using a network-flow graph algorithm.

## 3. Configuration Management (CM) 
This repository follows strict CM practices:
* **Beginner:** Tracks all project assets using Git/GitHub with clear commit history.
* **Intermediate:** Uses isolated feature branches (e.g., `feature/v1-ledger`) and Pull Requests for code review. Configurations are decoupled using `config.json`.
* **Expert:** Implements Continuous Integration (CI) via GitHub Actions to automate testing, and uses Git tags (e.g., `v1.0.0`) for release management.

## 4. Local Setup
1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `config.json` and add your Gemini API key.
4. Run the app: `python main.py`