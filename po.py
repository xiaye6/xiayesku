from pagermaid import bot
from pagermaid.listener import listener
from pagermaid.enums import Message
from telethon.tl.functions.messages import DeleteHistoryRequest
from telethon.tl.types import InputPeerUser, InputPeerChat, InputPeerChannel

@listener(command="po",
          description="删除当前账号归档中的所有对话，包括已注销用户的对话。",
          parameters="")
async def po(message: Message):
    await message.edit("开始清理归档对话...")

    failed = []
    count = 0

    async for dialog in bot.iter_dialogs(archived=True):
        entity = dialog.entity
        try:
            # 根据对话类型构造对应的 InputPeer
            if hasattr(entity, 'access_hash'):
                if entity.__class__.__name__ == 'User':
                    peer = InputPeerUser(entity.id, entity.access_hash)
                elif entity.__class__.__name__ == 'Channel':
                    peer = InputPeerChannel(entity.id, entity.access_hash)
                else:
                    continue
            elif entity.__class__.__name__ == 'Chat':
                peer = InputPeerChat(entity.id)
            else:
                continue

            # 删除对话历史
            await bot(DeleteHistoryRequest(
                peer=peer,
                max_id=0,
                revoke=True
            ))
            count += 1
        except Exception:
            failed.append(dialog.name or str(dialog.id))
            continue

    result = f"已成功清理 {count} 个对话。"
    if failed:
        result += f"\n以下对话跳过（无法删除）：{', '.join(failed)}"
    await message.edit(result)
