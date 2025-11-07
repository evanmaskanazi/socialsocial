# Quick check if everything is configured
from app import app
import os

with app.app_context():
    required_vars = ['SMTP_SERVER', 'SMTP_PORT', 'SMTP_USERNAME', 'SMTP_PASSWORD', 'FROM_EMAIL']
    missing = [var for var in required_vars if not os.environ.get(var)]
    
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
    else:
        print("✅ All SMTP environment variables are set")
        
        # Try a connection
        import smtplib
        import ssl
        
        try:
            context = ssl.create_default_context()
            server = smtplib.SMTP(os.environ['SMTP_SERVER'], int(os.environ['SMTP_PORT']))
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(os.environ['SMTP_USERNAME'], os.environ['SMTP_PASSWORD'])
            server.quit()
            print("✅ SMTP authentication successful!")
        except Exception as e:
            print(f"❌ SMTP error: {e}")
