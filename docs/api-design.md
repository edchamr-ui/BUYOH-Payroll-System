# BUYOH Payroll System — API Design

## 1. API Overview

This document defines the application routes and backend endpoints for the BUYOH Payroll System.

The system will primarily use Flask server-rendered pages, but documenting routes helps guide backend development.

---

## 2. Route Groups

The application routes will be grouped by module:

- Authentication
- Dashboard
- Employees
- Departments
- Payroll
- Payslips
- Reports
- Administration
- Audit Logs


---

# 3. Authentication Routes

| Method | Route | Purpose |
|---------|-------|---------|
| GET | /login | Display login page |
| POST | /login | Authenticate user |
| GET | /logout | Logout current user |
| GET | /profile | View user profile |
| POST | /change-password | Change user password |

Access:

- Public: Login
- Authenticated Users: Profile
- Authenticated Users: Logout

---

# 4. Dashboard Routes

| Method | Route | Purpose |
|---------|-------|---------|
| GET | /dashboard | Main dashboard |
| GET | /dashboard/statistics | Dashboard statistics |


---

# 5. Employee Routes

| Method | Route | Purpose |
|---------|-------|---------|
| GET | /employees | List employees |
| GET | /employees/add | Add employee form |
| POST | /employees/add | Save employee |
| GET | /employees/<id> | View employee |
| GET | /employees/<id>/edit | Edit employee |
| POST | /employees/<id>/edit | Update employee |
| POST | /employees/<id>/delete | Deactivate employee |


---

# 6. Department Routes

| Method | Route | Purpose |
|---------|-------|---------|
| GET | /departments | View departments |
| GET | /departments/add | Add department |
| POST | /departments/add | Save department |
| GET | /departments/<id>/edit | Edit department |
| POST | /departments/<id>/edit | Update department |


---

# 7. Payroll Routes

| Method | Route | Purpose |
|---------|-------|---------|
| GET | /payroll | Payroll dashboard |
| GET | /payroll/periods | View payroll periods |
| GET | /payroll/periods/add | Create payroll period |
| POST | /payroll/periods/add | Save payroll period |
| GET | /payroll/process/<period_id> | Process payroll |
| POST | /payroll/process/<period_id> | Calculate payroll |
| GET | /payroll/review/<period_id> | Review payroll |
| POST | /payroll/approve/<period_id> | Approve payroll |


---

# 8. Payslip Routes

| Method | Route | Purpose |
|---------|-------|---------|
| GET | /payslips | List payslips |
| GET | /payslips/<id> | View payslip |
| GET | /payslips/<id>/download | Download payslip PDF |
| POST | /payslips/generate/<payroll_record_id> | Generate payslip |

---

# 9. Report Routes

| Method | Route | Purpose |
|---------|-------|---------|
| GET | /reports | Reports dashboard |
| GET | /reports/monthly-summary | Monthly payroll summary |
| GET | /reports/paye | PAYE report |
| GET | /reports/nssa | NSSA report |
| GET | /reports/net-salary-schedule | Net salary schedule |
| GET | /reports/department | Department payroll report |
| GET | /reports/export/pdf | Export report as PDF |
| GET | /reports/export/csv | Export report as CSV |

---

# 10. Administration Routes

| Method | Route | Purpose |
|---------|-------|---------|
| GET | /admin/users | List system users |
| GET | /admin/users/add | Add user form |
| POST | /admin/users/add | Save user |
| GET | /admin/users/<id>/edit | Edit user |
| POST | /admin/users/<id>/edit | Update user |
| POST | /admin/users/<id>/deactivate | Deactivate user |
| GET | /admin/settings | System settings |
| POST | /admin/settings | Update settings |

---

# 11. Audit Log Routes

| Method | Route | Purpose |
|---------|-------|---------|
| GET | /audit-logs | View audit logs |
| GET | /audit-logs/filter | Filter audit logs |

---

# 12. Route Protection Rules

The system shall protect routes based on authentication and user roles.

## Public Routes

- /login

## Authenticated User Routes

- /dashboard
- /profile
- /logout

## Payroll Officer Routes

- /employees
- /payroll
- /payslips
- /reports

## Administrator Routes

- /admin/users
- /admin/settings
- /payroll/approve/<period_id>
- /audit-logs

## Management Routes

- /dashboard
- /reports
- /payslips

---

# 13. API Design Summary

The route structure is organized by module to keep the Flask application clean and maintainable.

Each major system function has its own route group:

- Authentication
- Dashboard
- Employees
- Departments
- Payroll
- Payslips
- Reports
- Administration
- Audit Logs

This design will guide the Flask Blueprint structure during backend development.
