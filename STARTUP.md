# Server Start/Stop (Replit Dev Environment)

This document outlines how to start and stop the development server when running in the Replit environment via SSH.

**Development Environment:**

*   We develop using an SSH connection to a Replit instance.
*   The running application is accessible publicly via the following development URL (do not use localhost):
    *   [`https://2cf5c75a-53c7-4770-ac2c-693998adbe64-00-eks0n7ucya4l.kirk.replit.dev/`](https://2cf5c75a-53c7-4770-ac2c-693998adbe64-00-eks0n7ucya4l.kirk.replit.dev/)

**Stop Server (Kill any potential running processes):**

```bash
pkill -f 'python run.py' ; pkill -f 'python -m app' ; pkill -f 'flask run' ; pkill -f 'python app.py'
```

**Start Server:**

```bash
python run.py 