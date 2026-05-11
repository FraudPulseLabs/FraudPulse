# Payment Fraud Detection System

## Overview

This project is a **modular fraud detection system for card payments**. It processes transaction data, generates fraud risk scores, and classifies transactions into **ALLOW, REVIEW, or BLOCK** using a combination of rules and machine learning.

The system is designed as a full pipeline:

* Transaction ingestion API
* Fraud scoring engine
* Decision system
* Case management workflow
* Dashboard for monitoring and investigation

# System Architecture

The system is organized into the following components:

* **Transaction Ingestion API** → receives and validates transactions
* **Fraud Scoring Engine** → generates risk scores (rules + ML)
* **Decision Engine** → classifies transactions
* **Data Layer** → stores transactions, scores, and cases
* **Back-office Processor** → re-evaluates and detects patterns
* **Case Management System** → investigation workflow
* **Dashboard** → monitoring and analytics UI

# Repository Structure

```
/backend        → API, scoring, decision engine  
/frontend       → dashboard UI  
/data           → datasets & schemas
```

# Features

## Core Capabilities

* Real-time transaction ingestion
* Fraud risk scoring
* Rule-based + ML-based detection
* Automated decisioning (ALLOW / REVIEW / BLOCK)
* Case creation from alerts

## Back-office Processing

* Event reprocessing
* Fraud pattern detection
* Batch evaluation of transactions

## Investigation System

* Case lifecycle management
* Alert grouping
* Analyst workflow support

# Tech Stack

* Backend: Python
* ML: 
* API: REST
* Database: Supabase
* Frontend:Angular v20, Tailwind v4
* CI/CD: GitHub Actions

# Branch Protection Rules

* No direct pushes to `main`
* All changes require Pull Requests
* At least 1 approval required
* CI checks must pass before merge

# Key Outputs

* Fraud risk score (0–1)
* Decision: ALLOW / REVIEW / BLOCK
* Case creation for flagged transactions

# Team

* Project Owner: Macharia Kibandi
* Scrum Master: Victor Asena
* Olalekan Erinoso
* James Kilonzo
