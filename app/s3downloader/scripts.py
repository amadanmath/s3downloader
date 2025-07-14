import os
import sys
import email
import base64
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import SMTP


def serve():
    """Run the Flask application with gunicorn"""
    # Run gunicorn - environment variables should be set by direnv
    port = os.environ.get('PORT', '5002')
    os.execvp("gunicorn", ["gunicorn", "--bind", f"0.0.0.0:{port}", "s3downloader.wsgi:app"])


def sign():
    """Sign all corpora URLs"""
    # Import and run signing function - environment variables should be set by direnv
    from s3downloader.aws import sign_all_corpora
    sign_all_corpora()


class DebugHandler:
    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        print(f"RCPT TO: {address}")
        envelope.rcpt_tos.append(address)
        return '250 OK'

    async def handle_DATA(self, server, session, envelope):
        print(f"From: {envelope.mail_from}")
        print(f"To: {envelope.rcpt_tos}")
        print("=" * 60)
        
        # Parse the email message
        msg = email.message_from_bytes(envelope.content)
        
        # Display basic headers
        print(f"Subject: {msg.get('Subject', 'No Subject')}")
        print(f"Date: {msg.get('Date', 'No Date')}")
        print()
        
        # Handle multipart messages
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                disposition = part.get('Content-Disposition', '')
                
                if content_type == 'text/plain' and 'attachment' not in disposition:
                    print("TEXT BODY:")
                    print(part.get_payload(decode=True).decode('utf-8'))
                    print()
                elif content_type == 'text/html' and 'attachment' not in disposition:
                    print("HTML BODY:")
                    print(part.get_payload(decode=True).decode('utf-8'))
                    print()
                elif 'attachment' in disposition:
                    filename = part.get_filename()
                    if filename:
                        payload = part.get_payload(decode=True)
                        if payload:
                            print(f"ATTACHMENT: {filename}")
                            
                            # Try to decode text attachments
                            if content_type.startswith('text/'):
                                try:
                                    print("Content:")
                                    print(payload.decode('utf-8'))
                                except UnicodeDecodeError:
                                    print(f"Binary content ({len(payload)} bytes)")
                            else:
                                # Save binary attachments to TMPDIR
                                tmpdir = os.environ.get('TMPDIR', '/tmp')
                                attachment_path = os.path.join(tmpdir, filename)
                                
                                with open(attachment_path, 'wb') as f:
                                    f.write(payload)
                                
                                print(f"Binary content ({len(payload)} bytes)")
                                print(f"Saved to: {attachment_path}")
                        print()
        else:
            # Single part message
            print("MESSAGE BODY:")
            payload = msg.get_payload(decode=True)
            if payload:
                print(payload.decode('utf-8'))
            print()
        
        print("-" * 60)
        sys.stdout.flush()
        return '250 Message accepted for delivery'


def dev():
    """Run development environment with both Flask app and mock SMTP server"""
    os.execvp("honcho", ["honcho", "start"])


def mocksmtp():
    """Run a mock SMTP server for testing"""
    # Get mail server settings from environment
    mail_server = os.environ.get('MAIL_SERVER', 'localhost')
    mail_port = int(os.environ.get('MAIL_PORT', '1025'))
    
    print(f"Starting mock SMTP server on {mail_server}:{mail_port}")
    print("Press Ctrl+C to stop")
    
    handler = DebugHandler()
    controller = Controller(handler, hostname=mail_server, port=mail_port)
    
    try:
        controller.start()
        # Keep the server running
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down mock SMTP server...")
        controller.stop()


def check_certs():
    """Check admin certificates for expiration and send warnings"""
    from s3downloader.config import configure
    from s3downloader.mail import Mailer
    from flask import Flask, url_for
    
    config = configure()
    warning_days = int(os.environ.get('CERT_WARNING_DAYS', '30'))
    
    print(f"Checking certificates for expiration within {warning_days} days...")
    
    # Get all certificates in data directory
    cert_files = list(Path(config.data_dir).glob('*.crt'))
    
    if not cert_files:
        print("No certificates found in data directory")
        return
    
    expiring_certs = []
    
    for cert_file in cert_files:
        try:
            # Get certificate expiration date
            cmd = ['openssl', 'x509', '-in', str(cert_file), '-noout', '-enddate']
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Parse the output: notAfter=Jan 1 00:00:00 2025 GMT
            date_str = result.stdout.strip().split('=')[1]
            expiry_date = datetime.strptime(date_str, '%b %d %H:%M:%S %Y %Z')
            
            # Check if expiring soon or already expired
            days_until_expiry = (expiry_date - datetime.now()).days
            
            if days_until_expiry <= warning_days:
                admin_email = cert_file.stem
                expiring_certs.append({
                    'file': cert_file,
                    'email': admin_email,
                    'expiry_date': expiry_date,
                    'days_until_expiry': days_until_expiry
                })
                
                if days_until_expiry < 0:
                    print(f"❌ {cert_file.name} EXPIRED {abs(days_until_expiry)} days ago ({expiry_date.strftime('%Y-%m-%d')})")
                else:
                    print(f"⚠️  {cert_file.name} expires in {days_until_expiry} days ({expiry_date.strftime('%Y-%m-%d')})")
            else:
                print(f"✅ {cert_file.name} expires in {days_until_expiry} days ({expiry_date.strftime('%Y-%m-%d')})")
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Error checking {cert_file.name}: {e}")
        except Exception as e:
            print(f"❌ Error processing {cert_file.name}: {e}")
    
    # Send warning emails for expiring certificates
    if expiring_certs:
        print(f"\nSending warning emails for {len(expiring_certs)} expiring certificates...")
        
        try:
            # Create Flask app context for mailer
            app = Flask(__name__)
            configure(app)
            
            # Check if APP_BASE_URL is explicitly defined in config
            if config.app_base_url:
                # Parse the base URL to extract components for Flask
                from urllib.parse import urlparse
                parsed = urlparse(config.app_base_url)
                app.config['SERVER_NAME'] = parsed.netloc
                app.config['PREFERRED_URL_SCHEME'] = parsed.scheme
                if parsed.path and parsed.path != '/':
                    app.config['APPLICATION_ROOT'] = parsed.path
                url_available = True
            else:
                # Load server configuration from saved file
                server_config_file = config.data_dir / 'server.conf'
                if server_config_file.exists():
                    with open(server_config_file, 'r') as f:
                        server_config = json.load(f)
                    app.config['SERVER_NAME'] = server_config['server_name']
                    app.config['PREFERRED_URL_SCHEME'] = server_config['scheme']
                    if server_config.get('application_root'):
                        app.config['APPLICATION_ROOT'] = server_config['application_root']
                    url_available = True
                else:
                    # No server config available - use placeholder
                    port = os.environ.get('PORT', '5002')
                    app.config['SERVER_NAME'] = f'localhost:{port}'
                    app.config['PREFERRED_URL_SCHEME'] = 'http'
                    url_available = False
            
            with app.app_context():
                mailer = Mailer(app, config)
                
                # Get the base URL for certificate preparation script
                if url_available:
                    prepare_cert_url = url_for('static', filename='prepare_cert.sh', _external=True)
                else:
                    prepare_cert_url = None
                
                for cert_info in expiring_certs:
                    try:
                        # Create warning email with different messaging for expired vs expiring certs
                        if cert_info['days_until_expiry'] < 0:
                            subject = f"Certificate EXPIRED - {abs(cert_info['days_until_expiry'])} days ago"
                            warning_text = "Your certificate for the S3 downloader system has EXPIRED."
                            urgency_text = "Please renew your certificate immediately to restore service."
                            days_text = f"<li><strong>Days Since Expiry:</strong> {abs(cert_info['days_until_expiry'])}</li>"
                        else:
                            subject = f"Certificate Expiration Warning - {cert_info['days_until_expiry']} days remaining"
                            warning_text = "Your certificate for the S3 downloader system is expiring soon."
                            urgency_text = "Please renew your certificate before it expires to avoid service interruption."
                            days_text = f"<li><strong>Days Until Expiry:</strong> {cert_info['days_until_expiry']}</li>"
                        
                        # Create download instructions based on URL availability
                        if prepare_cert_url:
                            download_text = f'<p>Download the certificate preparation script: <a href="{prepare_cert_url}" download type="text/x-shellscript">prepare_cert.sh</a></p>'
                        else:
                            download_text = '<p><strong>Note:</strong> Please edit the sample URL below to match your application\'s actual URL to download the certificate preparation script at <code>YOUR_APP_URL/static/prepare_cert.sh</code></p>'
                        
                        body = f"""
                        <h2>Certificate Expiration Warning</h2>
                        <p>{warning_text}</p>
                        <ul>
                            <li><strong>Certificate:</strong> {cert_info['file'].name}</li>
                            <li><strong>Email:</strong> {cert_info['email']}</li>
                            <li><strong>Expiry Date:</strong> {cert_info['expiry_date'].strftime('%Y-%m-%d %H:%M:%S')}</li>
                            {days_text}
                        </ul>
                        <p>{urgency_text}</p>
                        
                        <h3>Certificate Renewal Instructions</h3>
                        <p><strong>Note:</strong> OpenSSL is required for certificate generation.</p>
                        {download_text}
                        <p>Run the script with your email address:</p>
                        <pre>
chmod +x prepare_cert.sh
./prepare_cert.sh {cert_info['email']}
                        </pre>
                        
                        <p>Or create manually with OpenSSL:</p>
                        <pre>
# Generate a new private key (if you don't have one)
openssl genrsa -out {cert_info['email']}.key 2048

# Create a certificate signing request
openssl req -new -key {cert_info['email']}.key -out {cert_info['email']}.csr \\
    -subj "/CN={cert_info['email']}/emailAddress={cert_info['email']}"

# Self-sign the certificate (valid for 1 year)
openssl x509 -req -in {cert_info['email']}.csr -signkey {cert_info['email']}.key \\
    -out {cert_info['email']}.crt -days 365
                        </pre>
                        <p>After creating the certificate, place the <code>{cert_info['email']}.crt</code> file in the data directory, or send it to {config.default_admin} to install it for you.</p>
                        """
                        
                        from flask_mail import Message
                        
                        msg = Message(
                            subject=subject,
                            html=body,
                            sender=config.default_sender,
                            recipients=[cert_info['email']]
                        )
                        
                        mailer.mail.send(msg)
                        print(f"✅ Warning email sent to {cert_info['email']}")
                        
                    except Exception as e:
                        print(f"❌ Failed to send warning email to {cert_info['email']}: {e}")
                        
        except Exception as e:
            print(f"❌ Failed to initialize mailer: {e}")
    
    else:
        print("\n✅ All certificates are valid and not expiring soon")
        
    print(f"\nCertificate check complete. Checked {len(cert_files)} certificates.")