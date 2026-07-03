# BUYOH Payroll System

# System Architecture

---

## 1. Overview

The BUYOH Payroll System follows a modern three-tier web architecture.

The system is designed to provide:

- High availability
- Security
- Maintainability
- Scalability
- Future cloud deployment on AWS

The architecture separates presentation, business logic and data storage into independent layers.

---

# 2. High-Level Architecture

```text
Users
   │
   ▼
Web Browser
   │
   ▼
NGINX Reverse Proxy
   │
   ▼
Gunicorn WSGI Server
   │
   ▼
Flask Application
   │
   ▼
PostgreSQL Database
   │
   ▼
Backup System
```

---

# 3. Architecture Components

## Users

Users interact with the system through a standard web browser.

Supported users include:

- Administrator
- Payroll Officer
- Management

Responsibilities:

- Login
- Employee management
- Payroll processing
- Reporting
- Payslip generation

---

## Web Browser

Technology:

- Google Chrome
- Microsoft Edge
- Mozilla Firefox

Responsibilities:

- Display the user interface
- Submit forms
- Receive responses
- Download payslips

Reason for choosing:

Using a browser means no software installation is required on client computers.

---

## NGINX Reverse Proxy

Responsibilities:

- Receive incoming HTTP/HTTPS requests
- Serve static files
- Forward dynamic requests to Gunicorn
- SSL termination
- Improve security
- Improve performance

Reason for choosing:

NGINX is lightweight, fast and widely used in production Flask deployments.

---

## Gunicorn

Responsibilities:

- Run the Flask application
- Manage worker processes
- Handle concurrent requests

Reason for choosing:

Flask's built-in development server is not suitable for production.

Gunicorn is a production-grade WSGI server.

---

## Flask Application

Technology:

Python Flask

Responsibilities:

- User authentication
- Employee management
- Payroll processing
- Salary calculations
- Report generation
- Payslip generation
- Audit logging

Reason for choosing:

Flask is lightweight, modular and easy to maintain while allowing enterprise-quality applications.

---

## PostgreSQL Database

Responsibilities:

Store:

- Users
- Employees
- Departments
- Payroll periods
- Payroll records
- Payslips
- Reports
- Audit logs
- System settings

Reason for choosing:

PostgreSQL provides:

- ACID compliance
- Strong security
- Excellent performance
- Advanced SQL features
- Enterprise reliability

---

## Backup System

Technology:

pg_dump

Cron Jobs

Future AWS S3 Storage

Responsibilities:

- Daily database backups
- Disaster recovery
- Backup verification

Reason for choosing:

Payroll information is business-critical.

Regular backups prevent permanent data loss.

---

# 4. Request Flow

When a payroll officer opens the system:

1. User opens the application.
2. Browser sends request.
3. NGINX receives request.
4. NGINX forwards request to Gunicorn.
5. Gunicorn passes request to Flask.
6. Flask performs business logic.
7. Flask queries PostgreSQL.
8. PostgreSQL returns data.
9. Flask builds the response.
10. Gunicorn sends response to NGINX.
11. NGINX returns the page to the browser.

---

# 5. Security Architecture

The system implements multiple layers of security.

Authentication

↓

Role-Based Access Control

↓

Password Hashing

↓

Environment Variables

↓

HTTPS Encryption

↓

Database Security

↓

Daily Backups

---

# 6. Future AWS Architecture

The system has been designed so it can later migrate to AWS.

Future architecture:

Users

↓

Route 53

↓

Application Load Balancer

↓

EC2 Ubuntu Server

↓

Docker

↓

NGINX

↓

Gunicorn

↓

Flask

↓

Amazon RDS PostgreSQL

↓

Amazon S3 Backups

↓

CloudWatch Monitoring

---

# 7. Architectural Benefits

This architecture provides:

- Modular design
- High security
- Easy maintenance
- Future scalability
- Cloud readiness
- Enterprise deployment capability

---

# 8. Conclusion

The architecture provides a strong foundation for a production-ready payroll management system while supporting future migration to a cloud-based multi-company SaaS platform.
