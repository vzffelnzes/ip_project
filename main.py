import logging
import asyncio
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from database import init_db, add_word_to_db, get_all_banned_words, delete_word_from_db

logging.basicConfig(level=logging.INFO)

TOKEN=""

# Инициализация базы данных
init_db()  # Таблица создаётся здесь перед любым доступом к базе данных

# Загружаем слова из базы данных при запуске
banned_words = set(get_all_banned_words())

bot = Bot(token=TOKEN)
router = Router()
dp = Dispatcher()


# Функция для отправки сообщения с последующим удалением
async def send_temporary_message(chat_id: int, text: str, delay: int = 5):
    """Отправляет сообщение и удаляет его через `delay` секунд."""
    sent_message = await bot.send_message(chat_id, text)
    await asyncio.sleep(delay)
    await bot.delete_message(chat_id, sent_message.message_id)


# Удаление сообщения команды
async def delete_command_message(message: Message, delay: int = 5):
    """Удаляет сообщение команды через `delay` секунд."""
    await asyncio.sleep(delay)
    await bot.delete_message(message.chat.id, message.message_id)


# Команда для кика пользователя
@router.message(Command("kick"))
async def kick_user(message: Message):
    asyncio.create_task(delete_command_message(message))  # Удаляем сообщение команды
    if not message.reply_to_message:
        await send_temporary_message(message.chat.id,
                                     "Эта команда должна быть ответом на сообщение пользователя, которого нужно кикнуть.")
        return

    user_to_kick = message.reply_to_message.from_user.id
    try:
        await bot.ban_chat_member(chat_id=message.chat.id, user_id=user_to_kick)  # Блокируем пользователя
        await bot.unban_chat_member(chat_id=message.chat.id, user_id=user_to_kick)  # Снимаем блокировку
        await send_temporary_message(message.chat.id,
                                     f"Пользователь {message.reply_to_message.from_user.full_name} был кикнут.")
    except Exception as e:
        await send_temporary_message(message.chat.id, f"Не удалось кикнуть пользователя: {e}")


# Команда для бана пользователя
@router.message(Command("ban"))
async def ban_user(message: Message):
    asyncio.create_task(delete_command_message(message))  # Удаляем сообщение команды
    if not message.reply_to_message:
        await send_temporary_message(message.chat.id,
                                     "Эта команда должна быть ответом на сообщение пользователя, которого нужно забанить.")
        return

    user_to_ban = message.reply_to_message.from_user.id
    try:
        await bot.ban_chat_member(chat_id=message.chat.id, user_id=user_to_ban)
        await send_temporary_message(message.chat.id,
                                     f"Пользователь {message.reply_to_message.from_user.full_name} был забанен.")
    except Exception as e:
        await send_temporary_message(message.chat.id, f"Не удалось забанить пользователя: {e}")


# Команда для разбанивания пользователя
@router.message(Command("unban"))
async def unban_user(message: Message):
    asyncio.create_task(delete_command_message(message))  # Удаляем сообщение команды
    if not message.reply_to_message:
        await send_temporary_message(message.chat.id,
                                     "Эта команда должна быть ответом на сообщение пользователя, которого нужно разбанить.")
        return

    user_to_unban = message.reply_to_message.from_user.id
    try:
        await bot.unban_chat_member(chat_id=message.chat.id, user_id=user_to_unban)
        await send_temporary_message(message.chat.id,
                                     f"Пользователь {message.reply_to_message.from_user.full_name} был разбанен.")
    except Exception as e:
        await send_temporary_message(message.chat.id, f"Не удалось разбанить пользователя: {e}")


# Команда для добавления запрещённых слов
@router.message(Command("addword"))
async def add_banned_word(message: Message):
    asyncio.create_task(delete_command_message(message))  # Удаляем сообщение команды
    if len(message.text.split()) < 2:
        await send_temporary_message(message.chat.id, "Укажите слово, которое вы хотите добавить в список запрещённых.")
        return

    new_word = message.text.split(maxsplit=1)[1].lower()
    if new_word in banned_words:
        await send_temporary_message(message.chat.id, f"Слово '{new_word}' уже есть в списке запрещённых.")
        return

    banned_words.add(new_word)
    add_word_to_db(new_word)
    await send_temporary_message(message.chat.id, f"Слово '{new_word}' добавлено в список запрещённых.")


# Команда для удаления запрещённого слова
@router.message(Command("delword"))
async def delete_banned_word(message: Message):
    asyncio.create_task(delete_command_message(message))  # Удаляем сообщение команды
    if len(message.text.split()) < 2:
        await send_temporary_message(message.chat.id, "Укажите слово, которое вы хотите удалить из списка запрещённых.")
        return

    word_to_delete = message.text.split(maxsplit=1)[1].lower()
    if word_to_delete not in banned_words:
        await send_temporary_message(message.chat.id, f"Слово '{word_to_delete}' отсутствует в списке запрещённых.")
        return

    banned_words.remove(word_to_delete)
    delete_word_from_db(word_to_delete)
    await send_temporary_message(message.chat.id, f"Слово '{word_to_delete}' удалено из списка запрещённых.")


# Фильтрация сообщений с запрещёнными словами
@router.message()
async def filter_banned_words(message: Message):
    for word in banned_words:
        if word in message.text.lower():
            await message.delete()
            await send_temporary_message(message.chat.id, f"Сообщение удалено. Использование слова '{word}' запрещено.")
            break


async def main():
    # Настройка и запуск бота
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
