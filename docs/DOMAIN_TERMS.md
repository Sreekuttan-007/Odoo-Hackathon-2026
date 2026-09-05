# Domain Terms

Canonical terminology across all PeoplePay360 systems:

- **User**: A system login account (has an email and password).
- **Employee**: The core HR personnel record. Not all employees may be Users.
- **Department**: A structural group of employees.
- **Contract**: Legal working conditions, salary, and validity dates for an Employee.
- **Working Schedule**: Defines expected working hours (e.g. 40 Hours/Week).
- **Attendance**: Time tracking records.
- **Time Off Type**: Categories of leave (Sick, Vacation).
- **Time Off Allocation**: Total leave granted to an employee.
- **Time Off Request**: A request by an employee to take time off.
- **Salary Structure**: The collection of rules dictating how a Payslip is calculated.
- **Salary Rule**: Individual formula (e.g., Basic, HRA, Tax).
- **Payrun**: A batch of Payslips generated for a Payroll Period.
- **Payslip**: Individual salary record for a specific employee.
- **Payroll Period**: The date range for a Payrun.
- **Payroll Dashboard**: High level metrics summary.

## Canonical Roles
- `EMPLOYEE`: Basic self-service access
- `HR_MANAGER`: Can manage employees and time off
- `HR_PAYROLL_USER`: Can process payruns
- `HR_PAYROLL_MANAGER`: Can configure payroll rules
- `ADMIN`: Full system access and user management

## Status Conventions
- `ACTIVE` → Active
- `INACTIVE` → Inactive
