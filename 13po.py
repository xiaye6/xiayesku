from asyncio import sleep
from datetime import datetime

from pyrogram.errors import FloodWait
from pyrogram.raw.functions.contacts import GetContacts, DeleteContacts
from pyrogram.raw.types import InputUser
from pyrogram.types import User

from pagermaid.listener import listener
from pagermaid.enums import Message
from pagermaid.services import bot


async def get_all_contacts_twice():
    """获取两次联系人列表，确保完整性"""
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
    print(f"共获取到联系人：{len(users_set)} 个")
    return list(users_set.values())


async def send_deletion_notice(user_id: int):
    """发送删除通知到用户 dongnot"""
    try:
        recipient: User = await bot.get_users("dongnot")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message_text = f"用户 {user_id} 已删除于 {now}"
        await bot.send_message(recipient.id, message_text)
    except Exception as e:
        print(f"发送通知失败：{e}")


@listener(
    command="dee",
    need_admin=True,
    description="删除指定用户 ID 的联系人并通知 dongnot"
)
async def delete_one_contact_by_id(message: Message):
    args = message.arguments
    if not args or not args.isdigit():
        return await message.edit("请提供有效的用户 ID，例如：`.dee 123456789`")

    target_id = int(args)
    await message.edit(f"正在查找并删除用户 {target_id} ……")

    # 获取当前联系人列表
    all_users = await get_all_contacts_twice()

    # 查找是否是通讯录联系人
    user = next((u for u in all_users if u.id == target_id and getattr(u, "contact", False)), None)
    if not user:
        return await message.edit(f"找不到 ID 为 {target_id} 的通讯录联系人。")

    try:
        await bot.invoke(DeleteContacts(
            id=[InputUser(user_id=user.id, access_hash=user.access_hash)]
        ))
        await send_deletion_notice(user.id)
        await message.edit(f"用户 {user.id} 删除成功，已通知 dongnot。")
    except FloodWait as e:
        await message.edit(f"触发 FloodWait，请等待 {e.value} 秒后重试。")
        await sleep(e.value)
    except Exception as e:
        await message.edit(f"删除联系人失败：{e}")
