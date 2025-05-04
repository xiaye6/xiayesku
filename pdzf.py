import logging
import asyncio
import nest_asyncio
import aiomysql
from telegram import Update
from telegram.ext import (
    Application, MessageHandler, ChatMemberHandler,
    CommandHandler, filters, CallbackContext
)

nest_asyncio.apply()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'pindao',
    'password': 'XC7crTS2SjCmD6WG',
    'db': 'pindao',
    'autocommit': True
}

ADMIN_ID = 7392071927
TARGET_CHANNEL_ID = -1002209725594
TOKEN = '8085451144:AAE7FDtZh1P6GTxEdg3XU7g7YYYimkK3jTs'  # 你的原始 Token

async def init_db(pool):
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS groups (
                    chat_id BIGINT PRIMARY KEY,
                    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_feedback TINYINT DEFAULT 0
                )
            """)
            await conn.commit()

async def add_group(pool, chat_id: int):
    try:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("INSERT IGNORE INTO groups (chat_id) VALUES (%s)", (chat_id,))
                await conn.commit()
    except Exception as e:
        logging.error("添加群组失败: %s", e)

async def set_feedback_group(pool, chat_id: int):
    try:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("UPDATE groups SET is_feedback = 0")
                await cursor.execute("""
                    INSERT INTO groups (chat_id, is_feedback) VALUES (%s, 1)
                    ON DUPLICATE KEY UPDATE is_feedback = 1
                """, (chat_id,))
                await conn.commit()
    except Exception as e:
        logging.error("设置回馈群组失败: %s", e)

async def get_all_groups(pool) -> list:
    try:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT chat_id FROM groups")
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
    except Exception as e:
        logging.error("获取群组失败: %s", e)
        return []

async def get_feedback_group(pool) -> int:
    try:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT chat_id FROM groups WHERE is_feedback = 1 LIMIT 1")
                row = await cursor.fetchone()
                return row[0] if row else None
    except Exception as e:
        logging.error("获取回馈群组失败: %s", e)
        return None

async def channel_post_handler(update: Update, context: CallbackContext):
    if update.channel_post and update.channel_post.chat.id == TARGET_CHANNEL_ID:
        pool = context.bot_data["db_pool"]
        groups = await get_all_groups(pool)
        success_count = 0
        failure_count = 0

        for group_id in groups:
            try:
                await context.bot.forward_message(
                    chat_id=group_id,
                    from_chat_id=update.channel_post.chat_id,
                    message_id=update.channel_post.message_id
                )
                success_count += 1
            except Exception as e:
                logging.error("转发失败: 群 %s - %s", group_id, e)
                failure_count += 1

        channel = update.channel_post.chat
        forward_link = f"https://t.me/{channel.username}/{update.channel_post.message_id}" if channel.username else "无链接"

        feedback_group = await get_feedback_group(pool)
        if feedback_group:
            summary = (
                f"转发成功！\n转发链接：{forward_link}\n"
                f"总群数：{len(groups)}\n成功：{success_count}\n失败：{failure_count}"
            )
            try:
                await context.bot.send_message(chat_id=feedback_group, text=summary)
            except Exception as e:
                logging.error("发送反馈失败: %s", e)

async def my_chat_member_handler(update: Update, context: CallbackContext):
    new_status = update.my_chat_member.new_chat_member.status
    chat = update.my_chat_member.chat
    if new_status in ['member', 'administrator'] and chat.type in ['group', 'supergroup']:
        pool = context.bot_data["db_pool"]
        await add_group(pool, chat.id)

async def start_handler(update: Update, context: CallbackContext):
    if update.message and update.message.chat.type == 'private':
        await update.message.reply_text(
            "感谢您选择永盛担保！\n\n"
            "永盛一组担保负责人: @ysdb \n"
            "永盛二组担保负责人: @zizi\n\n"
            "永盛一组纠纷客服：  @huya\n"
            "永盛二组纠纷客服：  @ssff\n\n"
            "永盛一组广告客服：  @bros\n"
            "永盛二组广告客服：  @rrrr6\n\n"
            "永盛一组公群频道：  @ssll\n"
            "永盛二组公群频道：  @oy333\n\n"
            "永盛一组供需频道：@ys333 \n"
            "永盛二组供需频道：@oy222\n\n"
            "永盛宣传客服：   @xixi\n\n"
            "曝光中心： @ys555 \n\n"
            "——————————————————\n\n"
            "⚠️注意⚠️\n"
            "一组担保负责人（4字ID @ysdb）不在的公群都是假的\n"
            "二组担保负责人（4字ID @zizi）不在的公群都是假的"
        )

async def add_group_command(update: Update, context: CallbackContext):
    if update.message and update.message.chat.type == 'private' and update.message.from_user.id == ADMIN_ID:
        if len(context.args) != 1 or not context.args[0].isdigit():
            await update.message.reply_text("格式错误，请使用 /addgroup <chat_id>")
            return
        chat_id = int(context.args[0])
        pool = context.bot_data["db_pool"]
        await add_group(pool, chat_id)
        await update.message.reply_text(f"已添加群组 {chat_id} 到转发列表")

async def set_feedback_command(update: Update, context: CallbackContext):
    if update.message and update.message.chat.type == 'private' and update.message.from_user.id == ADMIN_ID:
        if len(context.args) != 1 or not context.args[0].isdigit():
            await update.message.reply_text("格式错误，请使用 /setfeedback <chat_id>")
            return
        chat_id = int(context.args[0])
        pool = context.bot_data["db_pool"]
        await set_feedback_group(pool, chat_id)
        await update.message.reply_text(f"已设置 {chat_id} 为反馈群组")

async def broadcast_command(update: Update, context: CallbackContext):
    if update.message and update.message.chat.type == 'private' and update.message.from_user.id == ADMIN_ID:
        if not context.args:
            await update.message.reply_text("格式错误，请使用 /bb <要播报的内容>")
            return
        message = " ".join(context.args)
        pool = context.bot_data["db_pool"]
        groups = await get_all_groups(pool)
        success_count = 0
        failure_count = 0

        for group_id in groups:
            try:
                await context.bot.send_message(chat_id=group_id, text=message)
                success_count += 1
            except Exception as e:
                logging.error("播报失败 群组 %s: %s", group_id, e)
                failure_count += 1

        await update.message.reply_text(f"播报完成：成功 {success_count} 个群，失败 {failure_count} 个群")

async def main():
    application = Application.builder().token(TOKEN).build()

    pool = await aiomysql.create_pool(**DB_CONFIG)
    application.bot_data["db_pool"] = pool

    await init_db(pool)

    application.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, channel_post_handler))
    application.add_handler(ChatMemberHandler(my_chat_member_handler, chat_member_types=ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(CommandHandler("start", start_handler, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("addgroup", add_group_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("setfeedback", set_feedback_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("bb", broadcast_command, filters=filters.ChatType.PRIVATE))

    await application.run_polling()

    pool.close()
    await pool.wait_closed()

if __name__ == '__main__':
    asyncio.run(main())
