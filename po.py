from pagermaid.listener import listener
from pagermaid.enums import Client, Message

@listener(
    command="po",
    description="删除当前账号归档中的所有对话（包括已注销的）",
)
async def delete_archived_chats(client: Client, message: Message):
    await message.edit("开始清理归档对话...")

    success_count = 0
    failed = []

    try:
        dialogs = await client.get_dialogs(folder_id=1)  # folder_id=1 代表归档
    except Exception as e:
        return await message.edit(f"获取归档失败：{e}")

    for dialog in dialogs:
        try:
            await client.delete_dialog(dialog.chat.id)
            success_count += 1
        except Exception:
            failed.append(dialog.chat.title or str(dialog.chat.id))

    result = f"已成功清理 {success_count} 个对话。"
    if failed:
        result += f"\n以下对话跳过：{', '.join(failed)}"
    await message.edit(result)
