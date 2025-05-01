from pagermaid.listener import listener
from pagermaid.enums import Client, Message
from pyrogram.raw.functions.contacts import GetContacts, DeleteContacts
from pyrogram.raw.types import InputUser
from pyrogram.errors import RPCError

@listener(
    command="sclxr",
    description="删除当前账号的所有联系人（含数字进度条显示）",
)
async def delete_all_contacts(client: Client, message: Message):
    await message.edit("正在获取联系人列表...")

    try:
        result = await client.invoke(GetContacts(hash=0))
        contacts = result.users
    except RPCError as e:
        return await message.edit(f"获取联系人失败：{e}")

    if not contacts:
        return await message.edit("你没有任何联系人。")

    total = len(contacts)
    deleted = 0

    for user in contacts:
        try:
            await client.invoke(DeleteContacts(id=[InputUser(user.id, user.access_hash)]))
            deleted += 1

            # 数字+条形进度
            percent = int((deleted / total) * 100)
            bar = "█" * (percent // 10) + "░" * (10 - percent // 10)
            await message.edit(f"正在删除联系人：[{bar}] {percent}% ({deleted}/{total})")

        except Exception:
            continue

    await message.edit(f"联系人清理完成，共删除 {deleted} 个联系人。")
