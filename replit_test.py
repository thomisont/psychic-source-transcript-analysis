"""
Simple test script to verify Replit web server configuration.
Run this directly to check if Replit can serve a web page on port 8080.
"""

import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return """
    <html>
    <head>
        <title>Replit Flask Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
            .container { max-width: 800px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
            h1 { color: #4a86e8; }
            .success { color: green; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Replit Flask Server Test</h1>
            <p class="success">✅ Success! Your Flask server is running correctly on port 8080.</p>
            <p>You can now run your main application with confidence:</p>
            <pre>bash simplified_start.sh</pre>
        </div>
    </body>
    </html>
    """

if __name__ == '__main__':
    # Get port from environment variable or use default 8080
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port) 