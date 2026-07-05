# Login Screen Wireframe

```text
+------------------------------------------------------+
|                                                      |
|                BUYOH PAYROLL SYSTEM                  |
|                                                      |
|                  [ Company Logo ]                    |
|                                                      |
|------------------------------------------------------|
|                                                      |
| Email Address                                        |
| +--------------------------------------------------+ |
|                                                      |
| Password                                             |
| +--------------------------------------------------+ |
|                                                      |
|          [ Login ]                                  |
|                                                      |
| Forgot Password (Future Version)                    |
|                                                      |
+------------------------------------------------------+
```

## Purpose

The Login screen authenticates users before they access the payroll system.

## Components

- Company Logo
- Email Address
- Password
- Login Button
- Forgot Password (Future Enhancement)

## Validation

- Email is required.
- Password is required.
- Invalid credentials should display a generic error message.
- Passwords must never be displayed in plain text.

## Security

- Passwords stored using hashing.
- Authentication handled by Flask-Login.
- Sessions secured with HTTPS in production.
