** Curious Caller Outbound emails
** HTML Summary Call email to caller

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Curious Caller Email</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f4f4;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 600px;
            background: #ffffff;
            padding: 20px;
            border-radius: 8px;
        }
        .info-box {
            background: #f9f9f9;
            padding: 10px;
            border-left: 4px solid #0073e6;
            margin: 10px 0;
            border-radius: 5px;
        }
        .link-button {
            display: block;
            background-color: #0073e6;
            color: white;
            padding: 10px;
            margin: 5px 0;
            border-radius: 5px;
            text-decoration: none;
            text-align: center;
            font-weight: bold;
        }
        .footer {
            margin-top: 20px;
            font-size: 12px;
            color: #777;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <p>Hello,</p>
        <p>Thanks for reaching out! I've informed the team at Psychic Source about our recent conversation. Someone will be in touch shortly.</p>
        
        <div class="info-box">
            <p><strong>Name:</strong> {{ $('11Labs Agent Webhook').item.json.body.userName }}</p>
            <p><strong>Email:</strong> {{ $('11Labs Agent Webhook').item.json.body.userEmail }}</p>
        </div>

        <p>Meanwhile, here are some helpful resources:</p>

        <a href="https://www.psychicsource.com/psychics" class="link-button">Browse Psychics</a>
        <a href="https://www.psychicsource.com/getting-started" class="link-button">Getting Started Guide</a>
      
        <p class="footer">If you have further questions, don't hesitate to reach out.</p>
    </div>
    <div class="footer">
        &copy; 2025 Psychic Source. All rights reserved.
    </div>

    <style>
        .link-button {
            display: block;
            background-color: #0073e6;
            color: #ffffff;
            text-decoration: none;
            padding: 10px;
            border-radius: 5px;
            text-align: center;
            margin: 8px 0;
            font-weight: bold;
        }
        .footer {
            margin-top: 20px;
            font-size: 12px;
            color: #777;
            text-align: center;
        }
    </style>
</body>
</html>

** Team Notice of New Call

<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>New Curious Caller Chat Update</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f4f4;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 600px;
            background: #ffffff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        h2 {
            color: #333;
        }
        p {
            color: #555;
            line-height: 1.6;
        }
        .info-box {
            background: #f9f9f9;
            padding: 10px;
            border-left: 4px solid #0073e6;
            margin: 10px 0;
            border-radius: 5px;
        }
        .footer {
            margin-top: 20px;
            font-size: 12px;
            color: #777;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>New Curious Caller Chat Update</h2>
        <p>Hi Prototype Team,</p>
        <p>Lily just completed another chat. Here are the details:</p>

        <div class="info-box">
            <p><strong>Name:</strong> {{ $('11Labs Agent Webhook').item.json.body.userName }}</p>
            <p><strong>Email:</strong> {{ $('11Labs Agent Webhook').item.json.body.userEmail }}</p>
            <p><strong>Preferences & Background Details:</strong> {{ $('11Labs Agent Webhook').item.json.body.userProfile }}</p>
            <p><strong>Psychic Selected (if any):</strong> {{ $('11Labs Agent Webhook').item.json.body.selectedPsychic }}</p>
        </div>

        <p>An email has been sent to the curious caller.</p>
        <p>The <strong>Curious Caller Google Sheet</strong> has also been updated.</p>

        <p class="footer">If you do not want to be notified upon each successful call, just let me know and I can remove you from the distribution list.</p>
    </div>
</body>
</html>