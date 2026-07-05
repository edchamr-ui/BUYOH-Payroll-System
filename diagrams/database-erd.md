# Database ERD Diagram

```text
ROLES
  │
  └──< USERS
          │
          └──< AUDIT_LOGS

DEPARTMENTS
  │
  └──< EMPLOYEES
          │
          └──< PAYROLL_RECORDS >── PAYROLL_PERIODS
                    │
                    ├──< ALLOWANCES
                    ├──< DEDUCTIONS
                    └── PAYSLIPS

