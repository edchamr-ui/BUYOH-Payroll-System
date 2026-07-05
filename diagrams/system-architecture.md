# System Architecture Diagram

```text
Users
  ↓
Web Browser
  ↓
NGINX Reverse Proxy
  ↓
Gunicorn WSGI Server
  ↓
Flask Application
  ↓
PostgreSQL Database
  ↓
Backup System
