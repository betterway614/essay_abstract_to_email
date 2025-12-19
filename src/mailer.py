import smtplib
import logging
import os
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from typing import List, Dict, Any
from config import settings

logger = logging.getLogger(__name__)

class Mailer:
    def __init__(self):
        self.user = settings.mail_user
        self.password = settings.mail_pass
        self.recipients = settings.mail_recipients

        env_host = os.getenv("SMTP_HOST", "").strip()
        env_port = os.getenv("SMTP_PORT", "").strip()

        if env_host:
            self.smtp_host = env_host
            self.smtp_port = int(env_port) if env_port else 465
        else:
            self.smtp_host, self.smtp_port = self._infer_smtp_settings(self.user)
        
        # Jinja setup
        template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')
        self.env = Environment(loader=FileSystemLoader(template_dir))

    def send_daily_digest(self, papers: List[Dict[str, Any]]):
        if not papers and not settings.email_config.get("send_empty", False):
            logger.info("No papers to send and send_empty is False. Skipping email.")
            return

        if not self.user or not self.password:
            logger.error("Mail credentials not found. Skipping email.")
            return
        if not self.recipients:
            logger.error("Mail recipients not found. Skipping email.")
            return

        try:
            subject_prefix = settings.email_config.get("subject_prefix", "[ArXiv Daily]")
            date_str = datetime.now().strftime("%Y-%m-%d")
            subject = f"{subject_prefix} {date_str} Update: {len(papers)} Papers Found"

            # Render HTML
            template = self.env.get_template('email_template.html')
            html_content = template.render(
                papers=papers,
                subject_prefix=subject_prefix,
                date_str=date_str
            )

            # Create Message
            msg = MIMEMultipart()
            msg['From'] = self.user
            msg['To'] = ", ".join(self.recipients)
            msg['Subject'] = subject
            msg.attach(MIMEText(html_content, 'html'))

            # Send
            logger.info(f"Connecting to SMTP server: {self.smtp_host}:{self.smtp_port}")
            self._send_message(msg)
            
            logger.info(f"Email sent successfully to {', '.join(self.recipients)}")

        except Exception as e:
            logger.error(f"Failed to send email: {type(e).__name__}: {e}")

    def _send_message(self, msg: MIMEMultipart):
        host = self.smtp_host
        port = self.smtp_port
        send_to = self.recipients

        tried = []
        for attempt_host, attempt_port, attempt_mode in self._iter_smtp_fallbacks(host, port):
            tried.append(f"{attempt_host}:{attempt_port}/{attempt_mode}")
            try:
                if attempt_mode == "ssl":
                    server = smtplib.SMTP_SSL(attempt_host, attempt_port, timeout=20)
                    try:
                        server.login(self.user, self.password)
                        server.send_message(msg, to_addrs=send_to)
                        return
                    finally:
                        try:
                            server.quit()
                        except Exception:
                            try:
                                server.close()
                            except Exception:
                                pass
                else:
                    server = smtplib.SMTP(attempt_host, attempt_port, timeout=20)
                    try:
                        server.ehlo()
                        server.starttls(context=ssl.create_default_context())
                        server.ehlo()
                        server.login(self.user, self.password)
                        server.send_message(msg, to_addrs=send_to)
                        return
                    finally:
                        try:
                            server.quit()
                        except Exception:
                            try:
                                server.close()
                            except Exception:
                                pass
            except Exception as e:
                logger.warning(f"SMTP attempt failed {attempt_host}:{attempt_port}/{attempt_mode}: {type(e).__name__}: {e}")
                continue

        raise RuntimeError(f"All SMTP attempts failed: {', '.join(tried)}")

    def _infer_smtp_settings(self, email_addr: str) -> tuple[str, int]:
        domain = ""
        if "@" in email_addr:
            domain = email_addr.split("@", 1)[1].lower().strip()

        if domain in {"qq.com", "foxmail.com"}:
            return "smtp.qq.com", 465
        if domain in {"gmail.com"}:
            return "smtp.gmail.com", 465
        if domain in {"outlook.com", "hotmail.com", "live.com", "office365.com"}:
            return "smtp.office365.com", 587

        return "smtp.qq.com", 465

    def _iter_smtp_fallbacks(self, host: str, port: int):
        if port == 465:
            yield host, 465, "ssl"
            yield host, 587, "starttls"
        elif port == 587:
            yield host, 587, "starttls"
            yield host, 465, "ssl"
        else:
            yield host, port, "ssl"
            yield host, port, "starttls"

if __name__ == "__main__":
    pass
