# BUYOH Payroll System

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.x-black?logo=flask)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?logo=postgresql)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5-purple?logo=bootstrap)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)
![Status](https://img.shields.io/badge/Status-Active%20Development-orange)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Enterprise Payroll Management System

BUYOH Payroll System is a modern web-based payroll management application developed with **Flask**, **PostgreSQL**, and **Bootstrap**.

The application is designed to automate payroll processing, employee management, statutory deductions, reporting, and payslip generation for Zimbabwean organisations while following enterprise software engineering best practices.

This project also serves as a portfolio demonstrating backend software engineering, database design, authentication, DevOps principles, and enterprise application architecture.

---

# Features

## Authentication

- Secure Login
- Password Hashing
- Session Management
- Role-Based Authentication

## Employee Management

- Add Employees
- Edit Employees
- Delete Employees
- Employee Profiles
- Department Assignment

## Department Management

- Create Departments
- Update Departments
- Delete Departments

## Payroll

- Payroll Periods
- Salary Processing
- Allowances
- Deductions
- Overtime
- Net Pay Calculation

## Zimbabwe Compliance

- PAYE
- NSSA
- AIDS Levy

## Reporting

- Payroll Reports
- Employee Reports
- Department Reports

## Payslips

- PDF Generation
- Email Delivery
- Printable Payslips

## Security

- SQL Injection Protection
- CSRF Protection
- Secure Password Storage
- Session Security
- Role Permissions

---

# Technology Stack

## Backend

- Python
- Flask
- SQLAlchemy
- Flask-Login
- Flask-Migrate

## Database

- PostgreSQL

## Frontend

- HTML5
- Bootstrap 5
- Jinja2

## Infrastructure

- Docker
- Docker Compose
- Gunicorn
- NGINX

---

# System Architecture

```text
                 Users
                   │
                   ▼
              NGINX Reverse Proxy
                   │
                   ▼
               Gunicorn WSGI
                   │
                   ▼
              Flask Application
        ┌──────────┼──────────┐
        │          │          │
 Authentication  Payroll   Reporting
        │          │          │
        └──────────┼──────────┘
                   │
                   ▼
             PostgreSQL Database
```

---

# Repository Structure

```text
BUYOH-Payroll-System/

├── 01-project-vision/
├── 02-requirements/
├── 03-architecture/
├── 04-database/
├── 05-ui-ux/
├── 06-backend/
├── docs/
├── diagrams/
├── screenshots/
├── source-code/
│   ├── app/
│   ├── migrations/
│   ├── config.py
│   ├── run.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── docker-compose.yml
├── README.md
└── LICENSE
```

---

# Getting Started

## Clone

```bash
git clone https://github.com/edchamr-ui/BUYOH-Payroll-System.git
cd BUYOH-Payroll-System/source-code
```

## Create Virtual Environment

```bash
python -m venv venv
```

Linux/macOS

```bash
source venv/bin/activate
```

Windows

```powershell
venv\Scripts\activate
```

## Install Dependencies

```bash
pip install -r requirements.txt
```

## Configure Environment

Create a `.env` file with your application configuration and database connection details.

## Run Database Migrations

```bash
flask db upgrade
```

## Start the Application

```bash
flask --app run.py run
```

Open:

```
http://127.0.0.1:5000
```

---

# Docker

Build and run with Docker Compose:

```bash
docker compose up --build
```

---

# Current Status

## Completed

- ✅ Project Planning
- ✅ Requirements Engineering
- ✅ System Architecture
- ✅ Database Design
- ✅ Authentication
- ✅ Employee Management
- ✅ Department Management
- ✅ Docker Configuration

## In Progress

- 🚧 Payroll Engine
- 🚧 Payslip Generation
- 🚧 Reporting
- 🚧 Dashboard

## Planned

- ⏳ Production Deployment
- ⏳ AWS Cloud Migration

---

# Development Roadmap

| Phase | Status |
|-------|--------|
| Planning | ✅ |
| Requirements | ✅ |
| Architecture | ✅ |
| Database | ✅ |
| Authentication | ✅ |
| Employee Module | ✅ |
| Department Module | ✅ |
| Payroll Engine | 🚧 |
| Reports | 🚧 |
| Dashboard | 🚧 |
| Testing | ⏳ |
| Production | ⏳ |
| AWS Migration | ⏳ |

---

# Future Enterprise Features

- Executive Dashboard
- Payroll Analytics
- Employee Payroll History
- Email Delivery History
- Excel Export
- PDF Export
- Advanced Search
- Pagination
- Granular Permissions
- Audit Logging
- REST API
- CI/CD Pipeline
- Automated Backups
- Multi-Company Support
- Ubuntu Production Deployment
- AWS Cloud Deployment

---

# Screenshots

Screenshots will be added as development progresses.

- Login
- Dashboard
- Employees
- Departments
- Payroll
- Reports
- Payslips

---

# Portfolio Highlights

This project demonstrates practical experience with:

- Flask
- PostgreSQL
- SQLAlchemy
- Authentication
- Docker
- REST APIs
- Enterprise Application Design
- Payroll Systems
- Database Design
- Secure Software Development

---

# Contributing

Contributions, suggestions, and feedback are welcome. Feel free to open an issue or submit a pull request.

---

# License

This project is licensed under the MIT License.

---

# Author

**Edmond Chamunorwa**

IT Specialist • Network Administrator • Cloud & DevOps Engineering Enthusiast

Zimbabwe
