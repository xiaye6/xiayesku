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

# 配置项
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
TOKEN = '8085451144:AAE7FDtZh1P6GTxEdg3XU7g7YYYimkK3jTs'

# 初始化数据库
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

# 群组操作函数
async def add_group(pool, chat_id: int):
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("INSERT IGNORE INTO groups (chat_id) VALUES (%s)", (chat_id,))
            await conn.commit()

async def set_feedback_group(pool, chat_id: int):
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("UPDATE groups SET is_feedback = 0")
            await cursor.execute("""
                INSERT INTO groups (chat_id, is_feedback) VALUES (%s, 1)
                ON DUPLICATE KEY UPDATE is_feedback = 1
            """, (chat_id,))
            await conn.commit()

async def get_all_groups(pool):
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT chat_id FROM groups")
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def get_feedback_group(pool):
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT chat_id FROM groups WHERE is_feedback = 1 LIMIT 1")
            row = await cursor.fetchone()
            return row[0] if row else None

# 新增：删除无效群组的函数
async def remove_invalid_groups(pool, group_ids):
    if not group_ids:
        return
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            placeholders = ", ".join(["%s"] * len(group_ids))
            query = f"DELETE FROM groups WHERE chat_id IN ({placeholders})"
            await cursor.execute(query, group_ids)
            await conn.commit()
    logging.info(f"已删除 {len(group_ids)} 个无效群组: {group_ids}")

# 频道消息转发处理（修改后）
async def channel_post_handler(update: Update, context: CallbackContext):
    from telegram.error import BadRequest
    
    if update.channel_post and update.channel_post.chat.id == TARGET_CHANNEL_ID:
        pool = context.bot_data["db_pool"]
        groups = await get_all_groups(pool)
        success_count = 0
        failure_count = 0
        invalid_groups = []  # 记录无效群组ID

        for group_id in groups:
            try:
                # 先检查机器人是否在群内
                await context.bot.get_chat_member(chat_id=group_id, user_id=context.bot.id)
                await context.bot.forward_message(
                    chat_id=group_id,
                    from_chat_id=update.channel_post.chat.id,
                    message_id=update.channel_post.message_id
                )
                success_count += 1
            except BadRequest as e:
                error_msg = f"转发失败: 群 {group_id} - {e}"
                logging.error(error_msg)
                failure_count += 1
                
                # 判断失效原因并记录无效群组
                if "bot was kicked" in str(e) or "Chat not found" in str(e):
                    invalid_groups.append(group_id)
                    error_detail = f"【群组失效】群ID: {group_id}，错误: {e}"
                    logging.error(error_detail)
        
        # 批量删除无效群组
        if invalid_groups:
            await remove_invalid_groups(pool, invalid_groups)
        
        # 发送反馈（包含失效群组信息）
        forward_link = f"https://t.me/{update.channel_post.chat.username}/{update.channel_post.message_id}" if update.channel_post.chat.username else "无链接"
        feedback_group = await get_feedback_group(pool)
        if feedback_group:
            summary = (
                f"转发结果：\n"
                f"转发链接：{forward_link}\n"
                f"总群数：{len(groups)}\n"
                f"成功：{success_count}\n"
                f"失败：{failure_count}\n"
                f"无效群组：{invalid_groups}"
            )
            try:
                await context.bot.send_message(chat_id=feedback_group, text=summary)
            except Exception as e:
                logging.error("发送反馈失败: %s", e)

# 机器人被拉入群时自动记录
async def my_chat_member_handler(update: Update, context: CallbackContext):
    new_status = update.my_chat_member.new_chat_member.status
    chat = update.my_chat_member.chat
    if new_status in ['member', 'administrator'] and chat.type in ['group', 'supergroup']:
        pool = context.bot_data["db_pool"]
        await add_group(pool, chat.id)

# start 命令（修改后）
async def start_handler(update: Update, context: CallbackContext):
    if update.message and update.message.chat.type == 'private':
        reply_text = """
感谢您选择永盛担保！

永盛一组担保负责人: @ysdb 
永盛二组担保负责人: @zizi

永盛一组纠纷客服： @huya
永盛二组纠纷客服： @ssff

永盛一组广告客服： @bros
永盛二组广告客服： @rrrr6

永盛一组公群频道： @ssll
永盛二组公群频道： @oy333

永盛一组供需频道：@ys333 
永盛二组供需频道：@oy222

永盛宣传客服： @xixi

曝光中心： @ys555 

——————————————————

⚠️注意⚠️
一组担保负责人（4字ID @ysdb）不在的公群都是假的
二组担保负责人（4字ID @zizi）不在的公群都是假的
"""
        await update.message.reply_text(reply_text)

# 管理员添加群组，带权限检查
async def add_group_command(update: Update, context: CallbackContext):
    if update.message and update.message.chat.type == 'private' and update.message.from_user.id == ADMIN_ID:
        if len(context.args) != 1 or not context.args[0].startswith("-") or not context.args[0][1:].isdigit():
            await update.message.reply_text("格式错误，请使用 /addgroup <chat_id>")
            return

        chat_id = int(context.args[0])

        try:
            member = await context.bot.get_chat_member(chat_id=chat_id, user_id=context.bot.id)
            if member.status not in ['administrator', 'creator']:
                await update.message.reply_text("机器人在该群组中不是管理员，无法添加。")
                return
        except Exception:
            await update.message.reply_text("机器人未在该群组中，或无法访问。")
            return

        pool = context.bot_data["db_pool"]
        await add_group(pool, chat_id)
        await update.message.reply_text(f"已添加群组 {chat_id} 到转发列表。")

# 管理员删除群组，需机器人不再是群管理员
async def remove_group_command(update: Update, context: CallbackContext):
    if update.message and update.message.chat.type == 'private' and update.message.from_user.id == ADMIN_ID:
        if len(context.args) != 1 or not context.args[0].startswith("-") or not context.args[0][1:].isdigit():
            await update.message.reply_text("格式错误，请使用 /removegroup <chat_id>")
            return

        chat_id = int(context.args[0])

        try:
            member = await context.bot.get_chat_member(chat_id=chat_id, user_id=context.bot.id)
            if member.status in ['administrator', 'creator']:
                await update.message.reply_text("机器人仍是该群的管理员，请先将其移除。")
                return
        except:
            pass  # 机器人不在群中，可继续删除

        try:
            pool = context.bot_data["db_pool"]
            async with pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("DELETE FROM groups WHERE chat_id = %s", (chat_id,))
                    await conn.commit()
            await update.message.reply_text(f"已删除群组 {chat_id} 的记录。")
        except Exception as e:
            logging.error("删除群组失败: %s", e)
            await update.message.reply_text("删除时发生错误，请稍后再试。")

# 管理员查看群组列表
async def list_groups_command(update: Update, context: CallbackContext):
    if update.message and update.message.chat.type == 'private' and update.message.from_user.id == ADMIN_ID:
        pool = context.bot_data["db_pool"]
        groups = await get_all_groups(pool)
        if not groups:
            await update.message.reply_text("当前没有任何记录的群组。")
        else:
            group_list = "\n".join(str(gid) for gid in groups)
            await update.message.reply_text(f"已记录的群组 ID 列表：\n{group_list}")

# 管理员群发广播
async def broadcast_command(update: Update, context: CallbackContext):
    if update.message and update.message.chat.type == 'private' and update.message.from_user.id == ADMIN_ID:
        if not context.args:
            await update.message.reply_text("格式错误，请使用 /bb <消息>")
            return

        text = " ".join(context.args)
        pool = context.bot_data["db_pool"]
        groups = await get_all_groups(pool)
        success = 0
        failure = 0

        for group_id in groups:
            try:
                await context.bot.send_message(chat_id=group_id, text=text)
                success += 1
            except Exception as e:
                logging.error("播报失败: 群 %s - %s", group_id, e)
                failure += 1

        await update.message.reply_text(f"播报完成：成功 {success} 个群，失败 {failure} 个群")

# 群组内设置反馈群的命令（限管理员）
async def addtjq_command(update: Update, context: CallbackContext):
    if update.message and update.message.chat.type in ['group', 'supergroup']:
        user_id = update.message.from_user.id
        chat_id = update.message.chat.id
        if user_id != ADMIN_ID:
            await update.message.reply_text("您没有权限执行此操作。")
            return
        pool = context.bot_data["db_pool"]
        await add_group(pool, chat_id)
        await set_feedback_group(pool, chat_id)
        await update.message.reply_text("已将本群设置为反馈群组。")

# 主函数
async def main():
    application = Application.builder().token(TOKEN).build()
    pool = await aiomysql.create_pool(**DB_CONFIG)
    application.bot_data["db_pool"] = pool

    await init_db(pool)

    application.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, channel_post_handler))
    application.add_handler(ChatMemberHandler(my_chat_member_handler, chat_member_types=ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(CommandHandler("start", start_handler, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("addgroup", add_group_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("removegroup", remove_group_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("listgroups", list_groups_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("bb", broadcast_command, filters=filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("addtjq", addtjq_command, filters=filters.ChatType.GROUPS))

    await application.run_polling()

    pool.close()
    await pool.wait_closed()

if __name__ == '__main__':
    asyncio.run(main())
