
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP_SSL


class SMTPClient:

    def __init__(self, config):

        self.smtp_host = config.get("host")
        self.smtp_username = config.get("username")
        self.smtp_password = config.get("password")
        self.mail_from = config.get("from")
        self.mail_recipient = config.get("recipient")

        assert self.smtp_host is not None, "'host' is missing from 'smtp' config."
        assert self.smtp_username is not None, "'username' is missing from 'smtp' config."
        assert self.smtp_password is not None, "'password' is missing from 'smtp' config."
        assert self.mail_from is not None, "'from' is missing from 'smtp' config."
        assert self.mail_recipient is not None, "'recipient' is missing from 'smtp' config."

        self.smtp_client = SMTP_SSL(self.smtp_host)
        self.smtp_client.login(user=self.smtp_username, password=self.smtp_password)


    def __del__(self):

        self.smtp_client.close()


    def send_mail(self, subject, body):

        message = MIMEMultipart()
        message["From"] = self.mail_from
        message["To"] = self.mail_recipient
        message["Subject"] = subject

        message.attach(MIMEText(body, "plain"))

        self.smtp_client.sendmail(self.mail_from, self.mail_recipient, message.as_string())
