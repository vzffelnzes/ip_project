import logging
import asyncio
import re

import aiohttp
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from database import init_db, add_word_to_db, get_all_banned_words, delete_word_from_db
from g4f.client import Client
from datetime import timedelta, datetime
from collections import defaultdict
from datetime import datetime, timedelta
from database import clear_database

logging.basicConfig(level=logging.INFO)

TOKEN = "7918677372:AAHwcJrckxibqT70loqS8Q5XP3WRi7QpfZI"
spam_detection_mode = False  # Флаг для включения режима фильтрации спама


# Инициализация базы данных
init_db()
banned_words = set(get_all_banned_words())

bot = Bot(token=TOKEN)
router = Router()
dp = Dispatcher()
client = Client()
#жопа

@router.message(Command("cleardb"))
async def clear_db_command(message: Message):
    asyncio.create_task(delete_command_message(message))  # Удаляем сообщение команды через 5 секунд

    # Проверяем, является ли пользователь администратором
    chat_member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ["administrator", "creator"]:
        await send_temporary_message(
            message.chat.id, "У вас нет прав для выполнения этой команды."
        )
        return

    try:
        # Очищаем базу данных
        clear_database()

        # Обновляем локальный кэш запрещённых слов
        global banned_words
        banned_words = set()

        await send_temporary_message(
            message.chat.id, "База данных успешно очищена."
        )
    except Exception as e:
        await send_temporary_message(
            message.chat.id, f"Ошибка при очистке базы данных: {e}"
        )


# Функция отправки временного сообщения
async def send_temporary_message(chat_id: int, text: str, delay: int = 3, command_message_id: int = None):
    """Отправляет сообщение, удаляет его через delay секунд, а также удаляет командное сообщение, если указано."""
    sent_message = await bot.send_message(chat_id, text)
    await asyncio.sleep(delay)
    await bot.delete_message(chat_id, sent_message.message_id)
    if command_message_id:
        await bot.delete_message(chat_id, command_message_id)


@router.message(Command("timeout"))
async def timeout_user(message: Message):
    asyncio.create_task(delete_command_message(message))  # Удаляем сообщение команды
    if not message.reply_to_message:
        await send_temporary_message(message.chat.id, "Эта команда должна быть ответом на сообщение пользователя.")
        return

    args = message.text.split()
    if len(args) < 2:
        await send_temporary_message(
            message.chat.id,
            "Укажите длительность тайм-аута в минутах. Пример: /timeout 10"
        )
        return

    try:
        timeout_duration = int(args[1])
        until_date = datetime.now() + timedelta(minutes=timeout_duration)
    except ValueError:
        await send_temporary_message(
            message.chat.id,
            "Укажите корректное число для длительности тайм-аута."
        )
        return

    user_to_timeout = message.reply_to_message.from_user.id
    try:
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=user_to_timeout,
            permissions={"can_send_messages": False},  # Запрет отправки сообщений
            until_date=until_date
        )
        await send_temporary_message(
            message.chat.id,
            f"Пользователь {message.reply_to_message.from_user.full_name} отправлен в тайм-аут на {timeout_duration} минут."
        )
    except Exception as e:
        await send_temporary_message(message.chat.id, f"Ошибка при отправке в тайм-аут: {e}")


# Команда для снятия тайм-аута
@router.message(Command("untimeout"))
async def untimeout_user(message: Message):
    asyncio.create_task(delete_command_message(message))  # Удаляем сообщение команды
    if not message.reply_to_message:
        await send_temporary_message(
            message.chat.id,
            "Эта команда должна быть ответом на сообщение пользователя."
        )
        return

    user_to_untimeout = message.reply_to_message.from_user.id
    try:
        # Снимаем все ограничения с пользователя
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=user_to_untimeout,
            permissions={
                "can_send_messages": True,
                "can_send_media_messages": True,
                "can_send_polls": True,
                "can_send_other_messages": True,
                "can_add_web_page_previews": True,
                "can_change_info": False,
                "can_invite_users": False,
                "can_pin_messages": False,
            }
        )
        await send_temporary_message(
            message.chat.id,
            f"С пользователя {message.reply_to_message.from_user.full_name} снят тайм-аут."
        )
    except Exception as e:
        await send_temporary_message(message.chat.id, f"Ошибка при снятии тайм-аута: {e}")


# Удаление сообщения команды
async def delete_command_message(message: Message, delay: int = 20):
    """Удаляет сообщение команды через delay секунд."""
    await asyncio.sleep(delay)
    await bot.delete_message(message.chat.id, message.message_id)


# Команда для переключения спам-фильтра
@router.message(Command("togglespam"))
async def toggle_spam_detection(message: Message):
    global spam_detection_mode
    asyncio.create_task(delete_command_message(message))  # Удаляем сообщение команды
    spam_detection_mode = not spam_detection_mode
    state = "включён" if spam_detection_mode else "выключен"
    await send_temporary_message(message.chat.id, f"Режим фильтрации спама {state}.")


@router.message(Command("del"))
async def delete_message_command(message: Message):
    asyncio.create_task(delete_command_message(message))  # Удалить команду
    if not message.reply_to_message:
        await send_temporary_message(
            message.chat.id,
            "Эта команда должна быть ответом на сообщение, которое нужно удалить."
        )
        return

    try:
        await bot.delete_message(message.chat.id, message.reply_to_message.message_id)
        await send_temporary_message(message.chat.id, "Сообщение успешно удалено.")
    except Exception as e:
        await send_temporary_message(message.chat.id, f"Не удалось удалить сообщение: {e}")


# Команда добавления запрещённых слов
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


# Команда удаления запрещённого слова
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


# Команда для кика пользователя
@router.message(Command("kick"))
async def kick_user(message: Message):
    asyncio.create_task(delete_command_message(message))  # Удаляем сообщение команды
    if not message.reply_to_message:
        await send_temporary_message(message.chat.id, "Эта команда должна быть ответом на сообщение пользователя.")
        return

    user_to_kick = message.reply_to_message.from_user.id
    try:
        await bot.ban_chat_member(chat_id=message.chat.id, user_id=user_to_kick)
        await bot.unban_chat_member(chat_id=message.chat.id, user_id=user_to_kick)
        await send_temporary_message(message.chat.id,
                                     f"Пользователь {message.reply_to_message.from_user.full_name} был кикнут.")
    except Exception as e:
        await send_temporary_message(message.chat.id, f"Ошибка при кике пользователя: {e}")


# Команда для бана пользователя
@router.message(Command("ban"))
async def ban_user(message: Message):
    asyncio.create_task(delete_command_message(message))  # Удаляем сообщение команды
    if not message.reply_to_message:
        await send_temporary_message(message.chat.id, "Эта команда должна быть ответом на сообщение пользователя.")
        return

    user_to_ban = message.reply_to_message.from_user.id
    try:
        await bot.ban_chat_member(chat_id=message.chat.id, user_id=user_to_ban)
        await send_temporary_message(message.chat.id,
                                     f"Пользователь {message.reply_to_message.from_user.full_name} был забанен.")
    except Exception as e:
        await send_temporary_message(message.chat.id, f"Ошибка при бане пользователя: {e}")


# Команда для разбанивания пользователя
@router.message(Command("unban"))
async def unban_user(message: Message):
    asyncio.create_task(delete_command_message(message))  # Удаляем сообщение команды
    if not message.reply_to_message:
        await send_temporary_message(message.chat.id, "Эта команда должна быть ответом на сообщение пользователя.")
        return

    user_to_unban = message.reply_to_message.from_user.id
    try:
        await bot.unban_chat_member(chat_id=message.chat.id, user_id=user_to_unban)
        await send_temporary_message(message.chat.id,
                                     f"Пользователь {message.reply_to_message.from_user.full_name} был разбанен.")
    except Exception as e:
        await send_temporary_message(message.chat.id, f"Ошибка при разбане пользователя: {e}")


violations = {}  # Формат: {user_id: count}


# Фильтрация сообщений с запрещёнными словами из базы данных и автоматический бан при 10 нарушениях
@router.message()
async def filter_messages_with_ban(message: Message):
    global violations

    user_id = message.from_user.id

    # Проверка на запрещённые слова
    for word in banned_words:  # banned_words загружаются из базы данных
        if word in message.text.lower():
            await message.delete()  # Удаляем сообщение с запрещённым словом
            # Увеличиваем счётчик нарушений
            violations[user_id] = violations.get(user_id, 0) + 1

            # Проверяем, достиг ли пользователь лимита нарушений
            if violations[user_id] >= 10:
                try:
                    # Бан пользователя
                    await bot.ban_chat_member(chat_id=message.chat.id, user_id=user_id)
                    await send_temporary_message(
                        message.chat.id,
                        f"Пользователь {message.from_user.full_name} забанен за 10 нарушений."
                    )
                    logging.info(f"Пользователь {message.from_user.full_name} забанен за 10 нарушений.")
                except Exception as e:
                    logging.error(f"Ошибка при бане пользователя: {e}")
                return  # Прекращаем обработку, пользователь уже забанен

            # Отправляем пользователя в тайм-аут
            timeout_duration = 1  # Тайм-аут в минутах
            until_date = datetime.now() + timedelta(minutes=timeout_duration)
            try:
                await bot.restrict_chat_member(
                    chat_id=message.chat.id,
                    user_id=user_id,
                    permissions={"can_send_messages": False},  # Запрет только на отправку сообщений
                    until_date=until_date
                )
                await send_temporary_message(
                    message.chat.id,
                    f"Сообщение удалено. Использование слова '{word}' запрещено. "
                    f"Пользователь отправлен в тайм-аут на 5 минут. Нарушений: {violations[user_id]}/10."
                )
                logging.info(
                    f"Пользователь {message.from_user.full_name} получил тайм-аут. Нарушений: {violations[user_id]}.")
            except Exception as e:
                logging.error(f"Ошибка при отправке пользователя в тайм-аут: {e}")
            return  # Прекращаем дальнейшую обработку этого сообщения

    # Дополнительная проверка на спам, если включён режим фильтрации
    if spam_detection_mode:
        try:
            async with aiohttp.ClientSession() as session:
                prompt = {
                    "modelUri": "gpt://b1gus2jr27on3b7n6gpj/yandexgpt-lite",
                    "completionOptions": {
                        "stream": False,
                        "temperature": 0.6,
                        "maxTokens": 2000,
                    },
                    "messages": [
                        {
                            "role": "system",
                            "text": (

                                "Ответь 'да' если данное сообщение является рекламой, содержит нецензурную брань или содержит в себе или какую-либо рекламу. Вот сообщение: '{message.text}'"
                            )
                        }
                    ]
                }
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Api-Key {YANDEX_API_KEY}"
                }
                async with session.post(YANDEX_API_URL, headers=headers, json=prompt) as response:
                    if response.status == 200:
                        result = await response.json()
                        # completion_text = result.get("completions", [{}])[0].get("text", "").lower()
                        # print(completion_text
                        if "да" in result['result']['alternatives'][0]['message']['text'].lower():
                            await message.delete()
                            await send_temporary_message(message.chat.id, "Сообщение удалено как спам.")
                    else:
                        logging.error(f"Ошибка запроса к Yandex Cloud: {response.status} - {await response.text()}")
        except Exception as e:
            logging.error(f"Ошибка при анализе сообщения: {e}")


async def main():
    # Настройка и запуск бота
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped manually.")
