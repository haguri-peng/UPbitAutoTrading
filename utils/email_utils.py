import smtplib, ssl, os
from datetime import datetime
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

SMTP_SSL_PORT = 465
SMTP_SERVER = 'smtp.gmail.com'

SENDER_EMAIL = os.getenv('SENDER_EMAIL', '')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD', '')
RECEIVER_EMAIL = os.getenv('RECEIVER_EMAIL', '')


def send_email(title: str, send_msg: str):
    # 메일 내용 작성
    msg = MIMEText(send_msg)
    msg['Subject'] = title + ' (' + datetime.now().strftime('%Y-%m-%d %H시 %M분') + ')'

    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_SSL_PORT, context=context) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())

# send_email('TEST', '메일 전송 테스트입니다.')
