from asyncio import sleep

from pyrogram.enums import ChatType
from pyrogram.errors import FloodWait
from pyrogram.raw.functions.messages import DeleteHistory

from pagermaid.listener import listener
from pagermaid.enums import Message
from pagermaid.services import bot


async def delete_private_chat(cid: int):
    try:
        await bot.invoke(
            DeleteHistory(
                just_clear=False,
                revoke=False,
                peer=await bot.resolve_peer(cid),
                max_id=0,
            )
        )
    except FloodWait as e:
        await sleep(e.value)
        await delete_private_chat(cid)
    except Exception:
        pass


@listener(
    command="clear_all_private_chats",
    need_admin=True,
    description="删除所有私聊对话记录",
)
async def clear_all_private_chats(message: Message):
    """删除所有私聊对话"""
    count = 0
    message: Message = await message.edit("正在删除所有私聊对话，请稍候……")
    async for dialog in bot.get_dialogs():
        if dialog.chat.type != ChatType.PRIVATE:
            continue
        await delete_private_chat(dialog.chat.id)
        count += 1
    await message.edit(f"已成功删除 {count} 个私聊对话。")
