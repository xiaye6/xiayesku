from asyncio import sleep
import csv

from pyrogram.errors import FloodWait
from pyrogram.raw.functions.contacts import GetContacts, DeleteContacts
from pyrogram.raw.types import InputUser

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


async def export_contacts_to_csv(users):
    with open("contacts.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "access_hash", "first_name", "last_name", "username", "is_contact"])
        for user in users:
            writer.writerow([
                user.id,
                user.access_hash,
                getattr(user, "first_name", ""),
                getattr(user, "last_name", ""),
                getattr(user, "username", ""),
                getattr(user, "contact", False)
            ])


async def delete_all_contacts_force(users):
    count = 0
    print(f"准备尝试删除所有 {len(users)} 个联系人（不判断是否为联系人）……")
    for user in users:
        try:
            print(f"删除联系人：{user.id} - {getattr(user, 'first_name', '')}")
            await bot.invoke(
                DeleteContacts(
                    id=[InputUser(user_id=user.id, access_hash=user.access_hash)]
                )
            )
            count += 1
            await sleep(1)
        except FloodWait as e:
            print(f"FloodWait 等待 {e.value} 秒")
            await sleep(e.value)
        except Exception as e:
            print(f"删除联系人 {user.id} 出错：{e}")
    return count


async def delete_contacts_from_csv():
    to_delete = []
    try:
        with open("contacts.csv", "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    user_id = int(row["id"])
                    access_hash = int(row["access_hash"])
                    to_delete.append(InputUser(user_id=user_id, access_hash=access_hash))
                except Exception as e:
                    print(f"跳过无效行：{e}")
    except FileNotFoundError:
        print("未找到 contacts.csv 文件")
        return 0

    count = 0
    for user in to_delete:
        try:
            print(f"尝试删除联系人：{user.user_id}")
            await bot.invoke(DeleteContacts(id=[user]))
            count += 1
            await sleep(1)
        except FloodWait as e:
            print(f"FloodWait 等待 {e.value} 秒")
            await sleep(e.value)
        except Exception as e:
            print(f"删除联系人失败 {user.user_id}：{e}")
    return count


@listener(
    command="delete_all_contacts",
    need_admin=True,
    description="导出并强制删除所有联系人（不判断 contact）",
)
async def delete_all_contacts_command(message: Message):
    """导出所有联系人并强制删除"""
    await message.edit("正在两次拉取联系人列表以确保完整性……")
    users = await get_all_contacts_twice()
    if not users:
        return await message.edit("未找到任何联系人。")

    await message.edit(f"已找到 {len(users)} 个联系人，正在导出 CSV 文件……")
    await export_contacts_to_csv(users)

    await bot.send_document(
        message.chat.id,
        "contacts.csv",
        caption=f"联系人导出完成，共导出 {len(users)} 个联系人。",
        message_thread_id=message.message_thread_id,
    )
    safe_remove("contacts.csv")

    await message.edit("CSV 导出完成，开始删除所有联系人……")
    deleted = await delete_all_contacts_force(users)
    await message.edit(f"联系人处理完成：共删除尝试 {deleted} 个联系人。")


@listener(
    command="delete_contacts_from_csv",
    need_admin=True,
    description="从 contacts.csv 中读取联系人并尝试删除"
)
async def delete_from_csv_command(message: Message):
    """从导出的 contacts.csv 中删除联系人"""
    await message.edit("正在从 contacts.csv 中读取联系人并删除……")
    deleted = await delete_contacts_from_csv()
    await message.edit(f"处理完成，共删除 {deleted} 个联系人。")
