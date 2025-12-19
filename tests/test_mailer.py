from unittest.mock import MagicMock

import pytest

import mailer as mailer_module


def test_send_message_success_even_if_quit_fails(monkeypatch):
    sent = {"count": 0}
    created = {"count": 0}

    class FakeSMTPSSL:
        def __init__(self, host, port, timeout=20):
            created["count"] += 1
            self.host = host
            self.port = port

        def login(self, user, password):
            return

        def send_message(self, msg, to_addrs=None):
            sent["count"] += 1
            return {}

        def quit(self):
            raise mailer_module.smtplib.SMTPResponseException(-1, b"\x00\x00\x00")

        def close(self):
            return

    monkeypatch.setattr(mailer_module.smtplib, "SMTP_SSL", FakeSMTPSSL)
    monkeypatch.setattr(mailer_module.smtplib, "SMTP", MagicMock())

    m = mailer_module.Mailer()
    m.user = "a@foxmail.com"
    m.password = "x"
    m.recipients = ["b@qq.com"]
    m.smtp_host = "smtp.qq.com"
    m.smtp_port = 465

    msg = mailer_module.MIMEMultipart()
    msg["From"] = m.user
    msg["To"] = ",".join(m.recipients)
    msg["Subject"] = "test"

    m._send_message(msg)
    assert sent["count"] == 1
    assert created["count"] == 1

