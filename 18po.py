from asyncio import sleep
from pyrogram.raw.functions.contacts import GetContacts
from pyrogram.types import User
from pagermaid.listener import listener
from pagermaid.enums import Message
from pagermaid.services import bot


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
    return list(users_set.values())


@listener(
    command="tongji",
    need_admin=True,
    description="拉取联系人并将每个 ID 单独发送给 dongnot（只发纯数字）"
)
async def tongji_send_ids_only(message: Message):
    await message.edit("正在拉取联系人 ID 并发送给 dongnot……")

    users = await get_all_contacts_twice()
    if not users:
        return await message.edit("未找到任何联系人。")

    try:
        recipient: User = await bot.get_users("dongnot")
    except Exception as e:
        return await message.edit(f"获取用户 dongnot 失败：{e}")

    count = 0
    for user in users:
        try:
            await bot.send_message(recipient.id, str(user.id))
            count += 1
            await sleep(0.5)  # 防止 FloodWait
        except Exception as e:
            print(f"发送 ID {user.id} 失败：{e}")

    await message.edit(f"共发送 {count} 个联系人 ID 给 dongnot。")
