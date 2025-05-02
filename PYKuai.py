import re

from pagermaid.listener import listener
from pagermaid.enums import Message
from pagermaid.services import bot
from pagermaid.utils import safe_remove


@listener(
    command="pyk",
    need_admin=True,
    description="生成 Python 文件（格式：`.pyk 文件名.py 代码内容`）\n例如：`.pyk test.py print(\"hello\")`"
)
async def pyk_generate_python_file(message: Message):
    full_text = message.text or ""
    parts = full_text.strip().split(maxsplit=2)

    if len(parts) < 3:
        return await message.edit("格式错误：请使用 `.pyk 文件名.py 代码内容` 的格式。")

    _, filename, code_text = parts

    if not re.match(r"^[\w\-]+\.py$", filename):
        return await message.edit("非法文件名。请使用合法格式如 `script.py`。")

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
