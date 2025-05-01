from pagermaid.listener import listener
from pagermaid.enums import Client, Message
from pyrogram.raw.types import InputUser
import math

@listener(
    command="sclxr",
    description="删除当前账号的所有联系人（含数字进度条显示）",
)
async def delete_all_contacts(client: Client, message: Message):
    await message.edit("正在获取联系人列表...")

    try:
        contacts = await client.get_contacts()
    except Exception as e:
        return await message.edit(f"获取联系人失败：{e}")

    if not contacts:
        return await message.edit("你没有任何联系人。")

    total = len(contacts)
    deleted = 0

    for contact in contacts:
        try:
            await client.delete_contacts(contact.id)
            deleted += 1

            # 数字进度条
            percent = int((deleted / total) * 100)
            bar = "█" * (percent // 10) + "░" * (10 - percent // 10)
            await message.edit(f"正在删除联系人：[{bar}] {percent}% ({deleted}/{total})")

        except Exception:
            continue  # 出错的跳过

    await message.edit(f"联系人清理完成，共删除 {deleted} 个联系人。")
