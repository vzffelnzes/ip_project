import logging
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from database import init_db, add_word_to_db, get_all_banned_words, delete_word_from_db, clear_database
from datetime import datetime, timedelta
from collections import defaultdict


logging.basicConfig(level=logging.INFO)

TOKEN = "7918677372:AAHwcJrckxibqT70loqS8Q5XP3WRi7QpfZI"

# Yandex API ключи
YANDEX_API_KEY = "AQVNwQd4okK1MAXU82jebu7DR3ub5pMeVlRllu5Z"
YANDEX_API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

# Инициализация базы данных
init_db()
banned_words = set(get_all_banned_words())

bot = Bot(token=TOKEN)
router = Router()
dp = Dispatcher()

# Глобальные переменные с настройками для каждого чата
chat_settings = defaultdict(lambda: {
    'spam_detection': False,
    'violations': defaultdict(int)
})


async def is_admin(chat_id: int, user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором чата"""
    try:
        chat_member = await bot.get_chat_member(chat_id, user_id)
        return chat_member.status in ["administrator", "creator"]
    except Exception as e:
        logging.error(f"Ошибка при проверке прав администратора: {e}")
        return False


async def send_temporary_message(chat_id: int, text: str, delay: int = 3):
    """Отправляет временное сообщение"""
    sent_message = await bot.send_message(chat_id, text)
    await asyncio.sleep(delay)
    await bot.delete_message(chat_id, sent_message.message_id)


async def delete_command_message(message: Message, delay: int = 20):
    """Удаляет сообщение команды"""
    await asyncio.sleep(delay)
    await bot.delete_message(message.chat.id, message.message_id)


"""async def handle_violation(message: Message, reason: str):
    """'Обрабатывает нарушение и применяет меры (1-е нарушение: тайм-аут 24ч, 2-е: бан)'"""
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Увеличиваем счетчик нарушений
    violations_count = chat_settings[chat_id]['violations'][user_id] + 1
    chat_settings[chat_id]['violations'][user_id] = violations_count

    try:
        await message.delete()
    except Exception as e:
        logging.error(f"Ошибка удаления сообщения: {e}")

    # Первое нарушение - тайм-аут на 24 часа
    if violations_count == 1:
        timeout_duration = 24 * 60  # 24 часа в минутах
        until_date = datetime.now() + timedelta(minutes=timeout_duration)
        try:
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions={"can_send_messages": False},
                until_date=until_date
            )
            await send_temporary_message(
                chat_id,
                f"⚠️ {reason}\n"
                f"Пользователь получил тайм-аут на 24 часа!\n"
                f"Следующее нарушение: бан"
            )
            logging.info(f"Пользователь {message.from_user.full_name} получил тайм-аут на 24 часа")
        except Exception as e:
            logging.error(f"Ошибка тайм-аута: {e}")

    # Второе нарушение - бан
    elif violations_count >= 2:
        try:
            await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            await send_temporary_message(
                chat_id,
                f"🚫 Пользователь {message.from_user.full_name} забанен!\n"
                f"Причина: повторное нарушение ({reason})"
            )
            logging.info(f"Пользователь {message.from_user.full_name} забанен за 2 нарушения")
            # Сбрасываем счетчик нарушений после бана
            chat_settings[chat_id]['violations'][user_id] = 0
        except Exception as e:
            logging.error(f"Ошибка бана: {e}")"""


# Команды модерации
@router.message(Command("cleardb"))
async def clear_db_command(message: Message):
    asyncio.create_task(delete_command_message(message))
    if not await is_admin(message.chat.id, message.from_user.id):
        await send_temporary_message(message.chat.id, "❌ Команда доступна только администраторам")
        return
    try:
        clear_database()
        global banned_words
        banned_words = set()
        await send_temporary_message(message.chat.id, "✅ База данных успешно очищена")
    except Exception as e:
        await send_temporary_message(message.chat.id, f"❌ Ошибка при очистке базы данных: {e}")


"""@router.message(Command("timeout"))
async def timeout_user(message: Message):
    asyncio.create_task(delete_command_message(message))
    if not await is_admin(message.chat.id, message.from_user.id):
        await send_temporary_message(message.chat.id, "❌ Команда доступна только администраторам")
        return
    if not message.reply_to_message:
        await send_temporary_message(message.chat.id, "⚠️ Эта команда должна быть ответом на сообщение пользователя")
        return
    args = message.text.split()
    if len(args) < 2:
        await send_temporary_message(message.chat.id,
                                     "⚠️ Укажите длительность тайм-аута в минутах. Пример: /timeout 10")
        return
    try:
        timeout_duration = int(args[1])
        until_date = datetime.now() + timedelta(minutes=timeout_duration)
    except ValueError:
        await send_temporary_message(message.chat.id, "⚠️ Укажите корректное число для длительности тайм-аута")
        return
    user_to_timeout = message.reply_to_message.from_user.id
    try:
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=user_to_timeout,
            permissions={"can_send_messages": False},
            until_date=until_date
        )
        await send_temporary_message(
            message.chat.id,
            f"⏳ Пользователь {message.reply_to_message.from_user.full_name} отправлен в тайм-аут на {timeout_duration} мин."
        )
    except Exception as e:
        await send_temporary_message(message.chat.id, f"❌ Ошибка при тайм-ауте: {e}")"""


"""@router.message(Command("untimeout"))
async def untimeout_user(message: Message):
    asyncio.create_task(delete_command_message(message))
    if not await is_admin(message.chat.id, message.from_user.id):
        await send_temporary_message(message.chat.id, "❌ Команда доступна только администраторам")
        return
    if not message.reply_to_message:
        await send_temporary_message(message.chat.id, "⚠️ Эта команда должна быть ответом на сообщение пользователя")
        return
    user_to_untimeout = message.reply_to_message.from_user.id
    try:
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
            f"✅ С пользователя {message.reply_to_message.from_user.full_name} снят тайм-аут"
        )
    except Exception as e:
        await send_temporary_message(message.chat.id, f"❌ Ошибка при снятии тайм-аута: {e}")"""


@router.message(Command("togglespam"))
async def toggle_spam_detection(message: Message):
    asyncio.create_task(delete_command_message(message))
    if not await is_admin(message.chat.id, message.from_user.id):
        await send_temporary_message(message.chat.id, "❌ Команда доступна только администраторам")
        return

    chat_id = message.chat.id
    current_state = chat_settings[chat_id]['spam_detection']
    chat_settings[chat_id]['spam_detection'] = not current_state

    state = "✅ включен" if chat_settings[chat_id]['spam_detection'] else "❌ выключен"
    await send_temporary_message(chat_id, f"Режим фильтрации спама {state} для этого чата")


@router.message(Command("spamstatus"))
async def spam_status(message: Message):
    asyncio.create_task(delete_command_message(message))
    chat_id = message.chat.id
    state = "✅ включен" if chat_settings.get(chat_id, {}).get('spam_detection', False) else "❌ выключен"
    await send_temporary_message(chat_id, f"Текущий статус спам-фильтра: {state}")


@router.message(Command("del"))
async def delete_message_command(message: Message):
    asyncio.create_task(delete_command_message(message))
    if not await is_admin(message.chat.id, message.from_user.id):
        await send_temporary_message(message.chat.id, "❌ Команда доступна только администраторам")
        return
    if not message.reply_to_message:
        await send_temporary_message(message.chat.id, "⚠️ Ответьте на сообщение, которое нужно удалить")
        return
    try:
        await bot.delete_message(message.chat.id, message.reply_to_message.message_id)
        await send_temporary_message(message.chat.id, "✅ Сообщение удалено")
    except Exception as e:
        await send_temporary_message(message.chat.id, f"❌ Ошибка удаления: {e}")


@router.message(Command("addword"))
async def add_banned_word(message: Message):
    asyncio.create_task(delete_command_message(message))
    if not await is_admin(message.chat.id, message.from_user.id):
        await send_temporary_message(message.chat.id, "❌ Команда доступна только администраторам")
        return
    if len(message.text.split()) < 2:
        await send_temporary_message(message.chat.id, "⚠️ Укажите слово для добавления в список запрещенных")
        return
    new_word = message.text.split(maxsplit=1)[1].lower()
    if new_word in banned_words:
        await send_temporary_message(message.chat.id, f"⚠️ Слово '{new_word}' уже запрещено")
        return
    banned_words.add(new_word)
    add_word_to_db(new_word)
    await send_temporary_message(message.chat.id, f"✅ Слово '{new_word}' добавлено в список запрещенных")


@router.message(Command("delword"))
async def delete_banned_word(message: Message):
    asyncio.create_task(delete_command_message(message))
    if not await is_admin(message.chat.id, message.from_user.id):
        await send_temporary_message(message.chat.id, "❌ Команда доступна только администраторам")
        return
    if len(message.text.split()) < 2:
        await send_temporary_message(message.chat.id, "⚠️ Укажите слово для удаления из списка запрещенных")
        return
    word_to_delete = message.text.split(maxsplit=1)[1].lower()
    if word_to_delete not in banned_words:
        await send_temporary_message(message.chat.id, f"⚠️ Слово '{word_to_delete}' не найдено в списке запрещенных")
        return
    banned_words.remove(word_to_delete)
    delete_word_from_db(word_to_delete)
    await send_temporary_message(message.chat.id, f"✅ Слово '{word_to_delete}' удалено из списка запрещенных")


@router.message(Command("kick"))
async def kick_user(message: Message):
    asyncio.create_task(delete_command_message(message))
    if not await is_admin(message.chat.id, message.from_user.id):
        await send_temporary_message(message.chat.id, "❌ Команда доступна только администраторам")
        return
    if not message.reply_to_message:
        await send_temporary_message(message.chat.id, "⚠️ Ответьте на сообщение пользователя для кика")
        return
    user_to_kick = message.reply_to_message.from_user.id
    try:
        await bot.ban_chat_member(chat_id=message.chat.id, user_id=user_to_kick)
        await bot.unban_chat_member(chat_id=message.chat.id, user_id=user_to_kick)
        await send_temporary_message(
            message.chat.id,
            f"👢 Пользователь {message.reply_to_message.from_user.full_name} был кикнут"
        )
    except Exception as e:
        await send_temporary_message(message.chat.id, f"❌ Ошибка кика: {e}")


@router.message(Command("ban"))
async def ban_user(message: Message):
    asyncio.create_task(delete_command_message(message))
    if not await is_admin(message.chat.id, message.from_user.id):
        await send_temporary_message(message.chat.id, "❌ Команда доступна только администраторам")
        return
    if not message.reply_to_message:
        await send_temporary_message(message.chat.id, "⚠️ Ответьте на сообщение пользователя для бана")
        return
    user_to_ban = message.reply_to_message.from_user.id
    try:
        await bot.ban_chat_member(chat_id=message.chat.id, user_id=user_to_ban)
        await send_temporary_message(
            message.chat.id,
            f"🔨 Пользователь {message.reply_to_message.from_user.full_name} был забанен"
        )
    except Exception as e:
        await send_temporary_message(message.chat.id, f"❌ Ошибка бана: {e}")


@router.message(Command("unban"))
async def unban_user(message: Message):
    asyncio.create_task(delete_command_message(message))
    if not await is_admin(message.chat.id, message.from_user.id):
        await send_temporary_message(message.chat.id, "❌ Команда доступна только администраторам")
        return
    if not message.reply_to_message:
        await send_temporary_message(message.chat.id, "⚠️ Ответьте на сообщение пользователя для разбана")
        return
    user_to_unban = message.reply_to_message.from_user.id
    try:
        await bot.unban_chat_member(chat_id=message.chat.id, user_id=user_to_unban)
        await send_temporary_message(
            message.chat.id,
            f"✅ Пользователь {message.reply_to_message.from_user.full_name} был разбанен"
        )
    except Exception as e:
        await send_temporary_message(message.chat.id, f"❌ Ошибка разбана: {e}")


@router.message()
async def filter_messages(message: Message):
    chat_id = message.chat.id

    # Проверка текста на запрещенные слова
    if hasattr(message, 'text') and message.text:
        for word in banned_words:
            if word in message.text.lower():
                await handle_violation(message, f"Обнаружено запрещенное слово: '{word}'")
                return

    # Проверка на спам (только если включен для этого чата)
    if chat_settings[chat_id]['spam_detection'] and hasattr(message, 'text') and message.text:
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
                                f"Ответь 'да' если данное сообщение является рекламой, содержит нецензурную брань или "
                                f"содержит в себе или какую-либо рекламу. Вот сообщение: {message.text}"
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
                        if "да" in result['result']['alternatives'][0]['message']['text'].lower():
                            await handle_violation(message, "Обнаружен спам")
                    else:
                        logging.error(f"Ошибка Yandex API: {response.status} - {await response.text()}")
        except Exception as e:
            logging.error(f"Ошибка анализа спама: {e}")


async def main():
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")