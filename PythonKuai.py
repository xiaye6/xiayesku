import os
import re

from pagermaid.listener import listener
from pagermaid.enums import Message
from pagermaid.services import bot
from pagermaid.utils import safe_remove


@listener(
    command="pyk",
    need_admin=True,
    description="发送 .pyk 命令，下一行指定文件名，再下一行开始写 Python 代码。\n格式如下：\n.pyk\ntext.py\nprint(\"hello world\")"
)
async def pyk_generate_python_file(message: Message):
    full_text = message.text or ""
    lines = full_text.strip().split("\n")

    if len(lines) < 3:
        return await message.edit("格式错误：请提供文件名和 Python 代码。\n例如：\n.pyk\ntext.py\nprint(\"hello\")")

    filename = lines[1].strip()

    if not re.match(r"^[\w\-]+\.py$", filename):
        return await message.edit("非法文件名。请使用如 `my_script.py` 格式的合法名称。")

    code_text = "\n".join(lines[2:]).strip()

    if not code_text:
        return await message.edit("请提供 Python 代码内容。")

    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(code_text)
    except Exception as e:
        return await message.edit(f"写入文件失败：{e}")

    try:
        await bot.send_document(
            message.chat.id,
            filename,
            message_thread_id=message.message_thread_id
        )
    except Exception as e:
        return await message.edit(f"发送文件失败：{e}")
    finally:
        safe_remove(filename)
