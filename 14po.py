from pagermaid.utils import safe_remove

@listener(
    command="tongji",
    need_admin=True,
    description="统计所有联系人 ID 并导出为 contact_ids.txt（双重获取确保完整）"
)
async def tongji_export_contact_ids(message: Message):
    await message.edit("正在两次获取联系人列表以确保完整……")

    users = await get_all_contacts_twice()
    if not users:
        return await message.edit("未找到任何联系人。")

    ids = sorted(set(user.id for user in users))

    # 写入 TXT 文件
    filename = "contact_ids.txt"
    with open(filename, "w", encoding="utf-8") as f:
        for user_id in ids:
            f.write(f"{user_id}\n")

    await bot.send_document(
        message.chat.id,
        filename,
        caption=f"已导出 {len(ids)} 个联系人 ID。",
        message_thread_id=message.message_thread_id,
    )
    safe_remove(filename)

    await message.edit(f"联系人 ID 导出完成，共 {len(ids)} 个。")
