from asyncio import sleep
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


async def send_deletion_notice(user_id: int):
    """发送删除通知给 dongnot"""
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
    description="读取 .txt 文件中 ID（逐行处理），删除联系人并通知 dongnot"
)
async def delete_contacts_line_by_line(message: Message):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.edit("请将 `.dee` 命令回复到一个包含用户 ID 的 `.txt` 文件。")

    file_path = await bot.download_media(message.reply_to_message.document)
    if not file_path.endswith(".txt"):
        return await message.edit("请使用纯文本 (.txt) 文件，每行一个用户 ID。")

    await message.edit("正在开始逐行读取和处理联系人……")

    # 获取联系人数据（缓存一次）
    all_users = await get_all_contacts_twice()
    user_map = {user.id: user for user in all_users if getattr(user, "contact", False)}

    deleted = 0
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line.isdigit():
                    print(f"无效行：{line}，跳过")
                    continue
                user_id = int(line)
                user = user_map.get(user_id)
                if not user:
                    print(f"用户 {user_id} 不存在或不是联系人，跳过。")
                    continue
                try:
                    await bot.invoke(DeleteContacts(
                        id=[InputUser(user_id=user.id, access_hash=user.access_hash)]
                    ))
                    await send_deletion_notice(user.id)
                    print(f"用户 {user.id} 删除成功")
                    deleted += 1
                    await sleep(1)
                except FloodWait as e:
                    print(f"FloodWait：等待 {e.value} 秒")
                    await sleep(e.value)
                except Exception as e:
                    print(f"删除用户 {user_id} 出错：{e}")
    except Exception as e:
        return await message.edit(f"读取文件失败：{e}")
    finally:
        safe_remove(file_path)

    await message.edit(f"处理完成，成功删除 {deleted} 个联系人。")
