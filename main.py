import logging
import asyncio
from aiogram import Bot, Dispatcher, Router
from aiogram.dispatcher import router
from aiogram.filters import Command
from aiogram.types import Message
from database import init_db, add_word_to_db, get_all_banned_words

logging.basicConfig(level=logging.INFO)

TOKEN=""

# Инициализация базы данных
init_db()  # Таблица создаётся здесь перед любым доступом к базе данных

# Загружаем слова из базы данных при запуске
banned_words = set(get_all_banned_words())

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
        await bot.unban_chat_member(chat_id=message.chat.id, user_id=user_to_kick)  # Снимаем блокировку
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

# Команда для добавления запрещённых слов
@router.message(Command("addword"))
async def add_banned_word(message: Message):
    if len(message.text.split()) < 2:
        await message.reply("Укажите слово, которое вы хотите добавить в список запрещённых.")
        return

    new_word = message.text.split(maxsplit=1)[1].lower()
    if new_word in banned_words:
        await message.reply(f"Слово '{new_word}' уже есть в списке запрещённых.")
        return

    banned_words.add(new_word)
    add_word_to_db(new_word)
    await message.reply(f"Слово '{new_word}' добавлено в список запрещённых.")

# Фильтрация сообщений с запрещёнными словами
@router.message()
async def filter_banned_words(message: Message):
    for word in banned_words:
        if word in message.text.lower():
            await message.delete()
            await message.answer(f"Сообщение удалено. Использование слова '{word}' запрещено.", reply_to_message_id=message.message_id)
            break

# Инициализация базы данных
init_db()

async def main():
    # Настройка и запуск бота
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
