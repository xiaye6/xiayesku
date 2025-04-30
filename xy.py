import smtplib
import json
from email.mime.text import MIMEText
from email.header import Header
from pagermaid.enums import Message
from pagermaid.listener import listener
from pagermaid.utils import MessageConfig

MAIL_CONFIG_FILE = "data/mail_config.json"


def save_mail_config(email, password, smtp_server="smtp.office365.com", port=587):
    config = {
        "email": email,
        "password": password,
        "smtp_server": smtp_server,
        "port": port
    }
    with open(MAIL_CONFIG_FILE, "w") as f:
        json.dump(config, f)


def load_mail_config():
    try:
        with open(MAIL_CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return None


@listener(command="setmail", description="配置发件邮箱（默认微软邮箱）\n用法：.setmail 邮箱地址 授权码")
async def set_mail(message: Message):
    if len(message.arguments.split()) != 2:
        return await message.edit("用法错误：.setmail 邮箱地址 授权码")
    email, password = message.arguments.split()
    save_mail_config(email, password)
    await message.edit("邮箱配置已保存。")


@listener(command="sendmail", description="发送邮件\n用法：.sendmail 收件人 主题 正文")
async def send_mail(message: Message):
    args = message.arguments.split(maxsplit=2)
    if len(args) != 3:
        return await message.edit("用法错误：.sendmail 收件人 主题 正文")

    to_address, subject, body = args
    config = load_mail_config()
    if not config:
        return await message.edit("尚未配置发件邮箱，请先使用 .setmail 配置。")

    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["From"] = config["email"]
        msg["To"] = to_address
        msg["Subject"] = Header(subject, "utf-8")

        server = smtplib.SMTP(config["smtp_server"], config["port"])
        server.starttls()
        server.login(config["email"], config["password"])
        server.sendmail(config["email"], [to_address], msg.as_string())
        server.quit()

        await message.edit("邮件发送成功！")
    except Exception as e:
        await message.edit(f"发送失败：{str(e)}")
