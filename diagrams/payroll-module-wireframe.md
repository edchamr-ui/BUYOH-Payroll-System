# Payroll Module Wireframe

```text
+------------------------------------------------------------------------------------------------+
| BUYOH Payroll System                              Payroll Officer ▼                 Logout      |
+------------------------------------------------------------------------------------------------+

| Dashboard | Employees | Payroll | Payslips | Reports | Administration | Audit Logs |

+------------------------------------------------------------------------------------------------+
| Payroll Processing                                                                [ Process ]  |
+------------------------------------------------------------------------------------------------+

Payroll Period:

[ July 2026 ▼ ]          Status: Draft

+------------------------------------------------------------------------------------------------+
| Employee | Basic Salary | Overtime | Allowances | Gross Pay | Deductions | Net Pay | Status |
|------------------------------------------------------------------------------------------------|
| EMP001   | $650.00      | $45.00    | $25.00     | $720.00   | $62.00     | $658.00 | Ready  |
| EMP002   | $550.00      | $30.00    | $20.00     | $600.00   | $48.00     | $552.00 | Ready  |
| EMP003   | $700.00      | $60.00    | $50.00     | $810.00   | $74.00     | $736.00 | Ready  |
+------------------------------------------------------------------------------------------------+

Payroll Summary

Total Employees : 82

Gross Payroll   : $65,400.00

Total Deductions: $10,780.00

Net Payroll     : $54,620.00

+------------------------------------------------------------------------------------------------+

[ Calculate Payroll ]    [ Approve Payroll ]    [ Generate Payslips ]    [ Cancel ]
```

## Purpose

The Payroll Module allows payroll officers to process salaries for an entire payroll period.

---

## Main Functions

- Create payroll period
- Load active employees
- Enter overtime
- Apply allowances
- Apply deductions
- Calculate gross pay
- Calculate statutory deductions
- Calculate net pay
- Approve payroll
- Generate payslips

---

## Payroll Workflow

```text
Create Payroll Period
        │
        ▼
Load Employees
        │
        ▼
Enter Overtime
        │
        ▼
Enter Allowances
        │
        ▼
Enter Deductions
        │
        ▼
Calculate Payroll
        │
        ▼
Review Results
        │
        ▼
Approve Payroll
        │
        ▼
Generate Payslips
```

---

## Security

- Payroll Officer may process payroll.
- Administrator may approve payroll.
- Approved payroll cannot be edited directly.
- Changes after approval require an adjustment process.

---

## Validation Rules

- Payroll period must exist.
- Payroll cannot be processed twice for the same employee and period.
- Gross Pay must be greater than or equal to Net Pay.
- Employee must be active.
- Payroll must be approved before payslips can be generated.
