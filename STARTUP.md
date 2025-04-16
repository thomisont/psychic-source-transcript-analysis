# Server Start/Stop (Replit Dev & Production)

This document outlines how to start and stop the server in both development and production environments on Replit.

**Development Environment:**

*   Develop using an SSH connection to a Replit instance.
*   The running application is accessible publicly via the following development URL (do not use localhost):
    *   [`https://2cf5c75a-53c7-4770-ac2c-693998adbe64-00-eks0n7ucya4l.kirk.replit.dev/`](https://2cf5c75a-53c7-4770-ac2c-693998adbe64-00-eks0n7ucya4l.kirk.replit.dev/)

**Stop Server (Kill any potential running processes):**

```bash
pkill -f 'python run.py' ; pkill -f 'python -m app' ; pkill -f 'flask run' ; pkill -f 'python app.py'
```

**Start Server (Development):**

```bash
python run.py
```

**Production Deployment (Replit Cloud):**

Replit will automatically install dependencies from `requirements.txt` and start the server using:

```bash
python run.py --port 8080
```

**Notes:**
- All dependencies are managed in `requirements.txt`.
- NLTK data is automatically downloaded by the application on startup if not present (no shell scripts required).
- No shell scripts are needed for startup or deployment.
