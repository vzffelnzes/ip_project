import logging
import asyncio
from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command
from aiogram.types import Message

logging.basicConfig(level=logging.INFO)

TOKEN=""

# Инициализация бота, диспетчера и роутера
bot = Bot(token=TOKEN)
router = Router()
dp = Dispatcher()

# Команда для кика пользователя
@router.message(Command("kick"))
async def kick_user(message: Message):
    if not message.reply_to_message:
        await message.reply("Эта команда должна быть ответом на сообщение пользователя, которого нужно кикнуть.")
        return

    user_to_kick = message.reply_to_message.from_user.id
    try:
        await bot.ban_chat_member(chat_id=message.chat.id, user_id=user_to_kick)  # Блокируем пользователя
        await bot.unban_chat_member(chat_id=message.chat.id, user_id=user_to_kick)  # Снимаем блокировку, чтобы он мог вернуться
        await message.reply(f"Пользователь {message.reply_to_message.from_user.full_name} был кикнут.")
    except Exception as e:
        await message.reply(f"Не удалось кикнуть пользователя: {e}")

# Команда для бана пользователя
@router.message(Command("ban"))
async def ban_user(message: Message):
    if not message.reply_to_message:
        await message.reply("Эта команда должна быть ответом на сообщение пользователя, которого нужно забанить.")
        return

    user_to_ban = message.reply_to_message.from_user.id
    try:
        await bot.ban_chat_member(chat_id=message.chat.id, user_id=user_to_ban)
        await message.reply(f"Пользователь {message.reply_to_message.from_user.full_name} был забанен.")
    except Exception as e:
        await message.reply(f"Не удалось забанить пользователя: {e}")

# Команда для разбанивания пользователя
@router.message(Command("unban"))
async def unban_user(message: Message):
    if not message.reply_to_message:
        await message.reply("Эта команда должна быть ответом на сообщение пользователя, которого нужно разбанить.")
        return

    user_to_unban = message.reply_to_message.from_user.id
    try:
        await bot.unban_chat_member(chat_id=message.chat.id, user_id=user_to_unban)
        await message.reply(f"Пользователь {message.reply_to_message.from_user.full_name} был разбанен.")
    except Exception as e:
        await message.reply(f"Не удалось разбанить пользователя: {e}")

async def main():
    # Настройка и запуск бота
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
