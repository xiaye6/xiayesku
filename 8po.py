from pagermaid.listener import listener
from pagermaid.enums import Client, Message

@listener(
    command="sclxr",
    description="删除当前账号的所有联系人，每 100 人向 @dongnot 发送进度。",
)
async def delete_all_contacts(client: Client, message: Message):
    await message.edit("开始删除联系人...")

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

            # 每删除100人发送一次进度消息给 @dongnot
            if deleted % 100 == 0 or deleted == total:
                progress = f"已删除联系人：{deleted}/{total}"
                try:
                    await client.send_message("dongnot", progress)
                except Exception:
                    pass  # 如果不能发消息给对方则跳过
        except Exception:
            continue  # 删除失败跳过

    await message.edit(f"联系人清理完成，共删除 {deleted} 个联系人。")
