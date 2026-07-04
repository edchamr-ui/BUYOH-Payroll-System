---

# 2. Database Design Principles

The database has been designed according to the following principles.

## 2.1 Relational Database Design

The system uses a relational database model where related information is stored in separate tables and linked using primary and foreign keys.

This minimizes data duplication and improves data integrity.

---

## 2.2 Data Integrity

The database shall enforce data integrity through:

- Primary Keys
- Foreign Keys
- Unique Constraints
- NOT NULL Constraints
- Check Constraints

This ensures payroll information remains accurate and consistent.

---

## 2.3 Normalization

The database will be normalized to Third Normal Form (3NF).

Benefits include:

- Reduced data redundancy
- Easier maintenance
- Improved consistency
- Faster updates
- Better scalability

---

## 2.4 Security

Sensitive payroll information will be protected by:

- User authentication
- Role-based access control
- Password hashing
- Database constraints
- Audit logging

---

## 2.5 Scalability

Although Version 1 is designed for BUYOH, the database structure should support future expansion into a multi-company SaaS platform.

Future versions may introduce:

- Companies table
- Tenant isolation
- Company-specific payroll settings
- Company branding

without requiring a complete redesign.

---

# 3. Database Naming Conventions

The database follows consistent naming standards.

Tables:

- users
- roles
- employees
- departments
- payroll_periods
- payroll_records
- allowances
- deductions
- payslips
- audit_logs
- settings

Primary Keys:

id

Foreign Keys:

employee_id

department_id

payroll_period_id

user_id

company_id (future)

Dates:

created_at

updated_at

deleted_at (optional)

Boolean fields:

is_active

is_admin

is_processed

is_approved

---

# 4. Database Relationships

The database follows a relational structure.

One Department can have many Employees.

One Employee can have many Payroll Records.

One Payroll Period can contain many Payroll Records.

One Payroll Record generates one Payslip.

One User can create many Payroll Records.

Audit Logs record actions performed by Users.



---

# 5. Database Tables

The BUYOH Payroll System will consist of the following core tables.

| Table | Purpose |
|---------|---------|
| users | Stores login accounts |
| roles | Defines user permissions |
| departments | Stores company departments |
| employees | Stores employee information |
| payroll_periods | Stores payroll months |
| payroll_records | Stores salary calculations |
| allowances | Stores employee allowances |
| deductions | Stores employee deductions |
| payslips | Stores generated payslips |
| audit_logs | Stores system activity |
| settings | Stores payroll configuration |


---

# 6. Table Design

## 6.1 Roles

Purpose:

Stores user permission levels.

Examples:

- Administrator
- Payroll Officer
- Manager

### Columns

| Column | Data Type | Constraints | Description |
|----------|-----------|-------------|-------------|
| id | SERIAL | Primary Key | Unique role ID |
| name | VARCHAR(50) | UNIQUE NOT NULL | Role name |
| description | TEXT | NULL | Role description |
| created_at | TIMESTAMP | NOT NULL | Date created |

Relationship:

One Role can be assigned to many Users.


---

## 6.2 Users

Purpose:

Stores user login accounts.

### Columns

| Column | Data Type | Constraints | Description |
|----------|-----------|-------------|-------------|
| id | SERIAL | Primary Key | User ID |
| role_id | INTEGER | Foreign Key | References Roles |
| full_name | VARCHAR(100) | NOT NULL | User full name |
| email | VARCHAR(120) | UNIQUE NOT NULL | Login email |
| password_hash | TEXT | NOT NULL | Hashed password |
| is_active | BOOLEAN | DEFAULT TRUE | Account status |
| created_at | TIMESTAMP | NOT NULL | Creation date |

Relationship:

Each User belongs to one Role.

One Role may have many Users.



---

## 6.3 Departments

Purpose:

Stores company departments or business units.

Examples:

- Finance
- Human Resources
- Operations
- IT
- Sales
- Administration

### Columns

| Column | Data Type | Constraints | Description |
|----------|-----------|-------------|-------------|
| id | SERIAL | Primary Key | Department ID |
| name | VARCHAR(100) | UNIQUE NOT NULL | Department name |
| description | TEXT | NULL | Department description |
| is_active | BOOLEAN | DEFAULT TRUE | Department status |
| created_at | TIMESTAMP | NOT NULL | Creation date |

Relationship:

One Department can have many Employees.

Each Employee belongs to one Department.

---

## 6.4 Employees

Purpose:

Stores employee master records.

This is one of the central tables in the payroll system.

### Columns

| Column | Data Type | Constraints | Description |
|----------|-----------|-------------|-------------|
| id | SERIAL | Primary Key | Employee ID |
| department_id | INTEGER | Foreign Key | References Departments |
| employee_number | VARCHAR(50) | UNIQUE NOT NULL | Internal employee number |
| first_name | VARCHAR(100) | NOT NULL | Employee first name |
| last_name | VARCHAR(100) | NOT NULL | Employee surname |
| national_id | VARCHAR(50) | UNIQUE NULL | National ID number |
| job_title | VARCHAR(100) | NOT NULL | Employee job title |
| employment_date | DATE | NOT NULL | Date employee joined |
| termination_date | DATE | NULL | Date employee left |
| basic_salary | NUMERIC(12,2) | NOT NULL | Monthly basic salary |
| employment_status | VARCHAR(30) | NOT NULL | Active, Suspended, Terminated |
| is_active | BOOLEAN | DEFAULT TRUE | Payroll eligibility |
| created_at | TIMESTAMP | NOT NULL | Creation date |
| updated_at | TIMESTAMP | NULL | Last update date |

Relationship:

One Employee belongs to one Department.

One Employee can have many Payroll Records.

One Employee can have many Allowances.

One Employee can have many Deductions.

One Employee can have many Payslips through Payroll Records.


---

## 6.5 Payroll Periods

Purpose:

Stores monthly payroll cycles.

Examples:

- January 2026
- February 2026
- March 2026

### Columns

| Column | Data Type | Constraints | Description |
|----------|-----------|-------------|-------------|
| id | SERIAL | Primary Key | Payroll period ID |
| month | INTEGER | NOT NULL | Payroll month, 1 to 12 |
| year | INTEGER | NOT NULL | Payroll year |
| status | VARCHAR(30) | NOT NULL | Draft, Processed, Approved, Closed |
| created_by | INTEGER | Foreign Key | User who created the period |
| created_at | TIMESTAMP | NOT NULL | Creation date |
| approved_by | INTEGER | Foreign Key NULL | User who approved payroll |
| approved_at | TIMESTAMP | NULL | Approval date |

Relationship:

One Payroll Period can contain many Payroll Records.

A Payroll Period is created by one User.

A Payroll Period may be approved by one User.

Important Constraint:

The system should not allow duplicate payroll periods for the same month and year.

---

## 6.6 Payroll Records

Purpose:

Stores the actual salary calculation results for each employee in a payroll period.

This table is the financial heart of the system.

### Columns

| Column | Data Type | Constraints | Description |
|----------|-----------|-------------|-------------|
| id | SERIAL | Primary Key | Payroll record ID |
| payroll_period_id | INTEGER | Foreign Key | References Payroll Periods |
| employee_id | INTEGER | Foreign Key | References Employees |
| basic_salary | NUMERIC(12,2) | NOT NULL | Employee basic salary |
| overtime_amount | NUMERIC(12,2) | DEFAULT 0.00 | Overtime paid |
| allowances_total | NUMERIC(12,2) | DEFAULT 0.00 | Total allowances |
| gross_pay | NUMERIC(12,2) | NOT NULL | Gross salary |
| nssa | NUMERIC(12,2) | DEFAULT 0.00 | NSSA deduction |
| paye | NUMERIC(12,2) | DEFAULT 0.00 | PAYE deduction |
| aids_levy | NUMERIC(12,2) | DEFAULT 0.00 | AIDS levy |
| other_deductions_total | NUMERIC(12,2) | DEFAULT 0.00 | Other deductions |
| total_deductions | NUMERIC(12,2) | NOT NULL | Total deductions |
| net_pay | NUMERIC(12,2) | NOT NULL | Final salary after deductions |
| status | VARCHAR(30) | NOT NULL | Draft, Processed, Approved |
| processed_by | INTEGER | Foreign Key | User who processed record |
| processed_at | TIMESTAMP | NOT NULL | Processing date |

Relationship:

One Payroll Record belongs to one Payroll Period.

One Payroll Record belongs to one Employee.

One Employee can have many Payroll Records over time.

Important Constraint:

The system should not allow the same employee to have more than one payroll record in the same payroll period.


---

## 6.7 Allowances

Purpose:

Stores additional earnings added to an employee’s salary.

Examples:

- Transport allowance
- Housing allowance
- Fuel allowance
- Bonus
- Commission

### Columns

| Column | Data Type | Constraints | Description |
|----------|-----------|-------------|-------------|
| id | SERIAL | Primary Key | Allowance ID |
| payroll_record_id | INTEGER | Foreign Key | References Payroll Records |
| employee_id | INTEGER | Foreign Key | References Employees |
| allowance_type | VARCHAR(100) | NOT NULL | Type of allowance |
| amount | NUMERIC(12,2) | NOT NULL | Allowance amount |
| description | TEXT | NULL | Additional notes |
| created_at | TIMESTAMP | NOT NULL | Creation date |

Relationship:

One Payroll Record can have many Allowances.

One Employee can have many Allowances.

---

## 6.8 Deductions

Purpose:

Stores deductions subtracted from an employee’s salary.

Examples:

- Staff loan
- Advance salary
- Pension
- Disciplinary deduction
- Other company deductions

### Columns

| Column | Data Type | Constraints | Description |
|----------|-----------|-------------|-------------|
| id | SERIAL | Primary Key | Deduction ID |
| payroll_record_id | INTEGER | Foreign Key | References Payroll Records |
| employee_id | INTEGER | Foreign Key | References Employees |
| deduction_type | VARCHAR(100) | NOT NULL | Type of deduction |
| amount | NUMERIC(12,2) | NOT NULL | Deduction amount |
| description | TEXT | NULL | Additional notes |
| created_at | TIMESTAMP | NOT NULL | Creation date |

Relationship:

One Payroll Record can have many Deductions.

One Employee can have many Deductions.

---

## 6.9 Payslips

Purpose:

Stores generated payslip records.

The actual PDF file may be stored locally in Version 1 and later moved to AWS S3.

### Columns

| Column | Data Type | Constraints | Description |
|----------|-----------|-------------|-------------|
| id | SERIAL | Primary Key | Payslip ID |
| payroll_record_id | INTEGER | Foreign Key UNIQUE | References Payroll Records |
| employee_id | INTEGER | Foreign Key | References Employees |
| file_path | TEXT | NOT NULL | Local or cloud file path |
| generated_by | INTEGER | Foreign Key | User who generated payslip |
| generated_at | TIMESTAMP | NOT NULL | Generation date |

Relationship:

One Payroll Record generates one Payslip.

One Employee can have many Payslips over time.


---

## 6.10 Audit Logs

Purpose:

Stores important system activity for accountability and security tracking.

Examples:

- User login
- Employee created
- Employee salary changed
- Payroll processed
- Payroll approved
- Payslip generated
- Report exported

### Columns

| Column | Data Type | Constraints | Description |
|----------|-----------|-------------|-------------|
| id | SERIAL | Primary Key | Audit log ID |
| user_id | INTEGER | Foreign Key | User who performed the action |
| action | VARCHAR(100) | NOT NULL | Action performed |
| description | TEXT | NULL | Detailed activity description |
| ip_address | VARCHAR(50) | NULL | User IP address |
| created_at | TIMESTAMP | NOT NULL | Date and time of action |

Relationship:

One User can create many Audit Logs.

---

## 6.11 Settings

Purpose:

Stores system-wide payroll configuration.

Examples:

- NSSA rate
- PAYE settings
- AIDS levy rate
- Company name
- Currency
- Payroll approval rules

### Columns

| Column | Data Type | Constraints | Description |
|----------|-----------|-------------|-------------|
| id | SERIAL | Primary Key | Setting ID |
| setting_key | VARCHAR(100) | UNIQUE NOT NULL | Name of setting |
| setting_value | TEXT | NOT NULL | Value of setting |
| description | TEXT | NULL | Setting description |
| updated_by | INTEGER | Foreign Key NULL | User who last updated setting |
| updated_at | TIMESTAMP | NULL | Date setting was updated |

Relationship:

Settings may be updated by Users.

---

## 6.12 Companies Future SaaS Table

Purpose:

This table is planned for future SaaS expansion.

It will allow the system to support multiple companies using the same payroll platform.

Version 1 may operate with a single default company, but the database design keeps this future direction in mind.

### Columns

| Column | Data Type | Constraints | Description |
|----------|-----------|-------------|-------------|
| id | SERIAL | Primary Key | Company ID |
| company_name | VARCHAR(150) | UNIQUE NOT NULL | Company name |
| trading_name | VARCHAR(150) | NULL | Trading name |
| logo_path | TEXT | NULL | Company logo location |
| currency | VARCHAR(10) | DEFAULT 'USD' | Payroll currency |
| country | VARCHAR(100) | DEFAULT 'Zimbabwe' | Operating country |
| timezone | VARCHAR(100) | DEFAULT 'Africa/Harare' | Company timezone |
| subscription_plan | VARCHAR(50) | NULL | SaaS subscription plan |
| is_active | BOOLEAN | DEFAULT TRUE | Company account status |
| created_at | TIMESTAMP | NOT NULL | Creation date |

Future Relationship:

One Company can have many Users.

One Company can have many Departments.

One Company can have many Employees.

One Company can have many Payroll Periods.

One Company can have many Payroll Records.

Future SaaS Note:

When SaaS mode is introduced, major tables will include:

```text
company_id


---

# 7. Database Constraints

The BUYOH Payroll System will enforce several database constraints to maintain data integrity and prevent inconsistent or invalid payroll information.

## Primary Key Constraints

Every table will have a Primary Key (`id`) that uniquely identifies each record.

## Foreign Key Constraints

Relationships between tables will be enforced using Foreign Keys.

Examples:

- `role_id` → roles
- `department_id` → departments
- `employee_id` → employees
- `payroll_period_id` → payroll_periods
- `payroll_record_id` → payroll_records
- `user_id` → users

## Unique Constraints

The following values must be unique:

- Employee Number
- User Email
- Department Name
- Payroll Period (Month + Year)
- Payslip per Payroll Record

## NOT NULL Constraints

Critical fields cannot be empty.

Examples:

- Employee First Name
- Employee Last Name
- Basic Salary
- Payroll Month
- Payroll Year
- Net Pay

## Check Constraints

The system should enforce logical business rules such as:

- Salary cannot be negative.
- Allowance amount cannot be negative.
- Deduction amount cannot be negative.
- Net Pay cannot exceed Gross Pay unless explicitly configured.
- Payroll Month must be between 1 and 12.

---

# 8. Database Indexes

Indexes improve query performance.

Recommended indexes include:

- employee_number
- email
- payroll_period_id
- employee_id
- department_id
- created_at

Benefits:

- Faster payroll processing
- Faster employee searches
- Faster report generation
- Improved scalability

---

# 9. Entity Relationship Summary (ERD)

The relationships between major entities are shown below.

```text
                    ROLES
                      │
                      │ 1
                      │
                      │ N
                    USERS
                      │
                      │
                      ▼
               AUDIT LOGS

DEPARTMENTS ─────► EMPLOYEES
                      │
                      │
                      │
                      ▼
             PAYROLL RECORDS
              ▲           ▲
              │           │
              │           │
PAYROLL PERIODS      ALLOWANCES
              │           │
              │           │
              ▼           ▼
          DEDUCTIONS
              │
              ▼
           PAYSLIPS
```

---

# 10. Database Design Summary

The database has been designed using relational database principles and follows Third Normal Form (3NF).

Key characteristics:

- Relational design
- Strong referential integrity
- Secure authentication support
- Financial data consistency
- Modular structure
- Scalable architecture
- Future SaaS readiness

The design supports the current BUYOH deployment while allowing future expansion into a multi-company payroll platform with minimal structural changes.

---

# 11. Future Enhancements

Future versions may include:

- Multiple companies
- Multiple branches
- Leave management
- Attendance integration
- Employee self-service portal
- Email payslips
- Mobile application
- AWS RDS deployment
- Amazon S3 payslip storage
- Cloud backup automation
