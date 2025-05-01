from pagermaid.listener import listener
from pagermaid.enums import Client, Message
from pyrogram.raw.functions.messages import GetDialogs
from pyrogram.raw.types import InputPeerEmpty
from pyrogram import utils

@listener(
    command="po",
    description="删除当前账号归档中的所有对话（包括已注销的）",
)
async def delete_archived_chats(client: Client, message: Message):
    await message.edit("开始清理归档对话...")

    success_count = 0
    failed = []

    offset_date = None
    offset_id = 0
    offset_peer = InputPeerEmpty()
    limit = 100

    while True:
        try:
            result = await client.invoke(
                GetDialogs(
                    offset_date=offset_date,
                    offset_id=offset_id,
                    offset_peer=offset_peer,
                    limit=limit,
                    hash=0,
                    folder_id=1  # 获取归档对话
                )
            )
        except Exception as e:
            return await message.edit(f"获取归档失败：{e}")

        if not result.dialogs:
            break

        for dialog in result.dialogs:
            try:
                peer = dialog.peer
                chat_id = utils.get_peer_id(peer)
                await client.delete_dialog(chat_id)
                success_count += 1
            except Exception:
                try:
                    chat = await client.get_chat(chat_id)
                    failed.append(chat.title or str(chat.id))
                except Exception:
                    failed.append(str(chat_id))
                continue

        last_message = result.messages[-1]
        offset_id = last_message.id
        offset_date = last_message.date  # 正确使用 datetime 对象
        offset_peer = peer

    result_text = f"已成功清理 {success_count} 个对话。"
    if failed:
        result_text += f"\n以下对话跳过：{', '.join(failed)}"
    await message.edit(result_text)
