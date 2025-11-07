# Comprehensive Password Reset Backend Testing
from app import app, db
from sqlalchemy import text
import smtplib
import ssl
import os

with app.app_context():
    print("=" * 60)
    print("COMPREHENSIVE PASSWORD RESET TESTING")
    print("=" * 60)
    
    # Test 1: Check environment variables
    print("\n1. CHECKING ENVIRONMENT VARIABLES:")
    print("-" * 40)
    smtp_server = os.environ.get('SMTP_SERVER', 'NOT SET')
    smtp_port = os.environ.get('SMTP_PORT', 'NOT SET')
    smtp_username = os.environ.get('SMTP_USERNAME', 'NOT SET')
    smtp_password = os.environ.get('SMTP_PASSWORD', 'NOT SET')
    from_email = os.environ.get('FROM_EMAIL', 'NOT SET')
    
    print(f"SMTP_SERVER: {smtp_server}")
    print(f"SMTP_PORT: {smtp_port}")
    print(f"SMTP_USERNAME: {smtp_username}")
    print(f"SMTP_PASSWORD: {'*' * len(smtp_password) if smtp_password != 'NOT SET' else 'NOT SET'}")
    print(f"FROM_EMAIL: {from_email}")
    
    # Test 2: Check if users exist in database
    print("\n2. CHECKING USERS IN DATABASE:")
    print("-" * 40)
    test_emails = ['ema9u@virginia.edu', 'evanmax@outlook.com', 'emaskanazi@gmail.com']
    
    for email in test_emails:
        result = db.session.execute(text("""
            SELECT id, username, email FROM users WHERE email = :email
        """), {"email": email})
        user = result.fetchone()
        if user:
            print(f"✅ {email}: Found (ID: {user.id}, Username: {user.username})")
        else:
            print(f"❌ {email}: NOT FOUND in database")
    
    # Test 3: Test SMTP connection
    print("\n3. TESTING SMTP CONNECTION:")
    print("-" * 40)
    
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
            print(f"✅ Connected to {smtp_server}:{smtp_port}")
            
            server.ehlo()
            print("✅ EHLO command successful")
            
            server.starttls(context=context)
            print("✅ STARTTLS successful")
            
            server.ehlo()
            print("✅ Post-TLS EHLO successful")
            
            try:
                server.login(smtp_username, smtp_password)
                print(f"✅ LOGIN successful for {smtp_username}")
            except smtplib.SMTPAuthenticationError as e:
                print(f"❌ Authentication failed: {e}")
                print("\nPossible issues:")
                print("1. Wrong password (need App Password, not regular password)")
                print("2. 2-Step Verification not enabled")
                print("3. App Password not generated correctly")
            
    except Exception as e:
        print(f"❌ SMTP connection failed: {e}")
    
    # Test 4: Check reset tokens table
    print("\n4. CHECKING PASSWORD RESET TOKENS:")
    print("-" * 40)
    result = db.session.execute(text("""
        SELECT COUNT(*) as total,
               COUNT(CASE WHEN used = true THEN 1 END) as used,
               COUNT(CASE WHEN expires_at < NOW() THEN 1 END) as expired
        FROM password_reset_tokens
    """))
    stats = result.fetchone()
    print(f"Total tokens: {stats.total}")
    print(f"Used tokens: {stats.used}")
    print(f"Expired tokens: {stats.expired}")
    
    # Test 5: Manual email send test
    print("\n5. MANUAL EMAIL SEND TEST:")
    print("-" * 40)
    
    def test_send_email(to_email):
        """Test sending an actual email"""
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = "Test Email from SocialSocial"
            message["From"] = from_email
            message["To"] = to_email
            
            text = "This is a test email from your password reset system."
            part = MIMEText(text, "plain")
            message.attach(part)
            
            context = ssl.create_default_context()
            with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(smtp_username, smtp_password)
                server.send_message(message)
                
            print(f"✅ Test email sent to {to_email}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send to {to_email}: {e}")
            return False
    
    # Uncomment to actually send test emails
    # for email in test_emails:
    #     test_send_email(email)
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE - Review results above")
    print("=" * 60)
