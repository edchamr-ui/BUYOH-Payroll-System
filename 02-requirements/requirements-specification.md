# BUYOH Payroll System — Requirements Specification

## 1. Introduction

This document defines the software requirements for the BUYOH Payroll System.

The purpose of this phase is to clearly describe what the system must do before development begins.

---

## 2. Project Scope

The system will provide a secure payroll management platform for managing employees, processing salaries, calculating statutory deductions, generating payslips and producing payroll reports.

Version 1 will focus on a single-company deployment while keeping the design flexible enough for future SaaS expansion.

---

## 3. User Roles

The system will support the following user roles:

### Administrator

Can manage users, employees, payroll settings, payroll processing, reports and system configuration.

### Payroll Officer

Can manage employee salary data, process payroll, generate payslips and view payroll reports.

### Management / Viewer

Can view reports and payslips but cannot modify payroll data.

---

## 4. Functional Requirements

Functional requirements describe what the system must do.

### 4.1 Authentication

The system shall allow users to log in securely.

The system shall allow users to log out.

The system shall restrict access based on user roles.

The system shall store passwords using secure password hashing.

---

### 4.2 Employee Management

The system shall allow authorized users to add employees.

The system shall allow authorized users to edit employee details.

The system shall allow authorized users to deactivate employees.

The system shall store employee salary information.

The system shall store employee department and job title.

---

### 4.3 Payroll Processing

The system shall allow authorized users to create payroll periods.

The system shall allow authorized users to process payroll for active employees.

The system shall calculate gross pay.

The system shall calculate statutory deductions.

The system shall calculate net pay.

The system shall save payroll history.

---

### 4.4 Payslip Generation

The system shall generate PDF payslips.

The system shall allow authorized users to download payslips.

The system shall store generated payslip records.

---

### 4.5 Reporting

The system shall generate monthly payroll summaries.

The system shall generate employee payroll reports.

The system shall generate NSSA reports.

The system shall generate PAYE reports.

The system shall generate net salary schedules.

---

## 5. Non-Functional Requirements

Non-functional requirements describe how the system should behave.

### 5.1 Security

The system shall require authentication before accessing payroll data.

The system shall restrict actions based on role permissions.

The system shall not store plain-text passwords.

The system shall protect sensitive configuration using environment variables.

---

### 5.2 Reliability

The system shall preserve payroll history.

The system shall support regular database backups.

The system shall prevent duplicate payroll processing for the same employee and period.

---

### 5.3 Performance

The system shall load common pages quickly.

The system shall process payroll for all active employees within an acceptable time.

---

### 5.4 Maintainability

The system shall use a modular code structure.

The payroll calculation logic shall be separated from routes and templates.

The database schema shall support future updates through migrations.

---

## 6. Payroll Business Rules

Gross Pay = Basic Salary + Overtime + Allowances

Total Deductions = NSSA + PAYE + AIDS Levy + Other Deductions

Net Pay = Gross Pay - Total Deductions

Payroll shall only be processed for active employees.

Approved payroll records shall not be edited directly.

Changes after approval shall require an adjustment record.

---

## 7. User Stories

As an Administrator, I want to manage system users so that access is controlled.

As a Payroll Officer, I want to add employees so that they can be included in payroll.

As a Payroll Officer, I want to process payroll so that salaries are calculated accurately.

As a Manager, I want to view payroll reports so that I can review salary costs.

As an employee, I want to receive a payslip so that I can see my salary breakdown.

---

## 8. Use Cases

### Use Case 1: Process Monthly Payroll

Actor: Payroll Officer

Steps:

1. Payroll Officer logs in.
2. Payroll Officer creates payroll period.
3. System loads active employees.
4. Payroll Officer enters overtime, allowances and deductions.
5. System calculates payroll.
6. Payroll Officer reviews results.
7. Administrator approves payroll.
8. System generates payslips and reports.

---

### Use Case 2: Generate Payslip

Actor: Payroll Officer

Steps:

1. Payroll Officer opens payroll period.
2. Payroll Officer selects employee.
3. System retrieves payroll record.
4. System generates PDF payslip.
5. Payroll Officer downloads the payslip.

---

## 9. Reporting Requirements

The system shall support:

- Monthly payroll summary
- Employee payslips
- PAYE report
- NSSA report
- Department payroll report
- Net salary schedule
- Payroll history report

---

## 10. Future SaaS Requirements

The system should be designed so that future versions can support:

- Multiple companies
- Company-specific branding
- Subscription plans
- Company-level user isolation
- Separate payroll settings per company
- Cloud storage for payslips
- Online tenant onboarding

---

## 11. Acceptance Criteria

Phase 2 will be considered complete when:

- Functional requirements are documented
- Non-functional requirements are documented
- Payroll rules are documented
- User roles are documented
- User stories are documented
- Use cases are documented
- Future SaaS considerations are documented
