from asyncio import sleep
import csv
from datetime import datetime

from pyrogram.errors import FloodWait
from pyrogram.raw.functions.contacts import GetContacts, DeleteContacts
from pyrogram.raw.types import InputUser
from pyrogram.types import User

from pagermaid.listener import listener
from pagermaid.enums import Message
from pagermaid.services import bot
from pagermaid.utils import safe_remove


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
    """给用户名为 dongnot 的用户发送删除通知"""
    try:
        recipient: User = await bot.get_users("dongnot")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message_text = f"用户 {user_id} 已删除于 {now}"
        await bot.send_message(recipient.id, message_text)
    except Exception as e:
        print(f"发送通知失败：{e}")


async def delete_contacts_by_id_from_csv():
    try:
        with open("contacts.csv", "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            target_ids = {int(row["id"]) for row in reader if "id" in row}
    except Exception as e:
        print(f"读取 CSV 失败：{e}")
        return 0

    print(f"CSV 中读取到 {len(target_ids)} 个 ID，准备开始删除对应联系人……")

    # 获取当前联系人
    all_users = await get_all_contacts_twice()

    # 仅删除真正联系人，且 ID 在 CSV 中的用户
    to_delete = [
        user for user in all_users
        if getattr(user, "contact", False) and user.id in target_ids
    ]

    print(f"实际找到匹配的通讯录联系人：{len(to_delete)} 个")

    count = 0
    for user in to_delete:
        try:
            print(f"删除：{user.id} - {getattr(user, 'first_name', '')}")
            await bot.invoke(DeleteContacts(
                id=[InputUser(user_id=user.id, access_hash=user.access_hash)]
            ))
            await send_deletion_notice(user.id)
            count += 1
            await sleep(1)
        except FloodWait as e:
            print(f"FloodWait：等待 {e.value} 秒")
            await sleep(e.value)
        except Exception as e:
            print(f"删除联系人 {user.id} 失败：{e}")
    return count


@listener(
    command="delete_csv_real_contacts",
    need_admin=True,
    description="根据 contacts.csv 中的 ID 删除通讯录联系人，并通知 dongnot"
)
async def delete_csv_real_contacts_command(message: Message):
    await message.edit("开始根据 contacts.csv 删除通讯录联系人，并通知 dongnot……")
    deleted = await delete_contacts_by_id_from_csv()
    await message.edit(f"完成，共删除 {deleted} 个通讯录联系人。")
