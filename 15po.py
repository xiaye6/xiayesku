from asyncio import sleep
import os

from pyrogram.raw.functions.contacts import GetContacts
from pagermaid.listener import listener
from pagermaid.enums import Message
from pagermaid.services import bot
from pagermaid.utils import safe_remove


async def get_all_contacts_twice():
    """两次拉取联系人列表，确保完整性"""
    users_set = {}
    for attempt in range(2):
        try:
            contacts = await bot.invoke(GetContacts(hash=0))
            for user in contacts.users:
                users_set[user.id] = user
            await sleep(3)
        except Exception as e:
            print(f"第 {attempt + 1} 次获取联系人失败：{e}")
            await sleep(2)
    print(f"共获取联系人：{len(users_set)} 个")
    return list(users_set.values())


@listener(
    command="tongji",
    need_admin=True,
    description="统计所有联系人 ID 并导出为 contact_ids.txt（两次验证）"
)
async def tongji_export_contact_ids(message: Message):
    await message.edit("正在两次获取联系人列表以确保完整……")

    users = await get_all_contacts_twice()
    if not users:
        return await message.edit("未找到任何联系人。")

    ids = sorted(set(user.id for user in users))
    filename = "contact_ids.txt"

    try:
        with open(filename, "w", encoding="utf-8") as f:
            for user_id in ids:
                f.write(f"{user_id}\n")
    except Exception as e:
        return await message.edit(f"写入文件失败：{e}")

    try:
        await bot.send_document(
            message.chat.id,
            filename,
            caption=f"联系人 ID 导出完成，共 {len(ids)} 个。",
            message_thread_id=message.message_thread_id,
        )
    except Exception as e:
        return await message.edit(f"发送文件失败：{e}")
    finally:
        safe_remove(filename)

    await message.edit("contact_ids.txt 已发送。")
