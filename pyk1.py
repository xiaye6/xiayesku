import os

from pagermaid.listener import listener
from pagermaid.enums import Message
from pagermaid.services import bot
from pagermaid.utils import safe_remove


@listener(
    command="pyk",
    need_admin=True,
    description="将跟随命令的 Python 代码写入 .py 文件并发送回对话"
)
async def pyk_generate_python_file(message: Message):
    full_text = message.text or ""
    lines = full_text.split("\n", 1)

    if len(lines) < 2 or not lines[1].strip():
        return await message.edit("请在 `.pyk` 命令下一行粘贴 Python 代码。")

    code_text = lines[1]
    filename = "code_output.py"

    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(code_text)
    except Exception as e:
        return await message.edit(f"写入文件失败：{e}")

    try:
        await bot.send_document(
            message.chat.id,
            filename,
            caption="你的 Python 文件已生成。",
            message_thread_id=message.message_thread_id
        )
    except Exception as e:
        return await message.edit(f"发送文件失败：{e}")
    finally:
        safe_remove(filename)

    await message.edit("Python 文件已发送。")
