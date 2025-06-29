import asyncio
import datetime
import logging
from collections import defaultdict

from aiogram import Router
from aiogram.client.session import aiohttp
from aiogram.types import Message

router = Router()
chat_settings = defaultdict(lambda: {'spam_detection': False, 'violations': defaultdict(int)})


async def send_temporary_message(chat, text: str, delay: int = 3):
    """Отправляет временное сообщение"""
    sent_message = await chat.bot.send_message(chat.id, text)
    await asyncio.sleep(delay)
    await chat.bot.delete_message(chat.id, sent_message.message_id)


async def handle_violation(message: Message, reason: str):
    """'Обрабатывает нарушение и применяет меры (1-е нарушение: тайм-аут 24ч, 2-е: бан)'"""
    chat_id = message.chat
    user_id = message.from_user.id
    # Увеличиваем счетчик нарушений
    violations_count = chat_settings[chat_id]['violations'][user_id] + 1
    chat_settings[chat_id]['violations'][user_id] = violations_count

    try:
        await message.delete()
    except Exception as e:
        logging.error(f'Ошибка удаления сообщения: {e}')

    # Первое нарушение - тайм-аут на 24 часа
    if violations_count == 1:
        timeout_duration = 24 * 60  # 24 часа в минутах
        until_date = datetime.now() + datetime.timedelta(minutes=timeout_duration)
        try:
            await message.bot.restrict_chat_member(
                chat_id=chat_id.id, user_id=user_id, permissions={'can_send_messages': False}, until_date=until_date
            )
            await send_temporary_message(
                chat_id, f'⚠️ {reason}\nПользователь получил тайм-аут на 24 часа!\nСледующее нарушение: бан'
            )
            logging.info(f'Пользователь {message.from_user.full_name} получил тайм-аут на 24 часа')
        except Exception as e:
            logging.error(f'Ошибка тайм-аута: {e}')

    # Второе нарушение - бан
    elif violations_count >= 2:
        try:
            await message.bot.ban_chat_member(chat_id=chat_id.id, user_id=user_id)
            await send_temporary_message(
                chat_id,
                f'🚫 Пользователь {message.from_user.full_name} забанен!\nПричина: повторное нарушение ({reason})',
            )
            logging.info(f'Пользователь {message.from_user.full_name} забанен за 2 нарушения')
            # Сбрасываем счетчик нарушений после бана
            chat_settings[chat_id]['violations'][user_id] = 0
        except Exception as e:
            logging.error(f'Ошибка бана: {e}')


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
                    'modelUri': 'gpt://b1gus2jr27on3b7n6gpj/yandexgpt-lite',
                    'completionOptions': {
                        'stream': False,
                        'temperature': 0.6,
                        'maxTokens': 2000,
                    },
                    'messages': [
                        {
                            'role': 'system',
                            'text': (
                                f"Ты бот для цензурирования сообщений в чате. Отвечай только да или нет. Ответь 'да' если данное сообщение является рекламой, содержит нецензурную брань или "
                                f"содержит в себе или какую-либо рекламу или политический подтекст, а так же оскорбления на политической или религиозной почве. Иначе ответь 'Нет'. Вот сообщение: {message.text}"
                            ),
                        }
                    ],
                }
                headers = {'Content-Type': 'application/json', 'Authorization': f'Api-Key {YANDEX_API_KEY}'}
                async with session.post(YANDEX_API_URL, headers=headers, json=prompt) as response:
                    if response.status == 200:
                        result = await response.json()
                        print(result['result']['alternatives'][0]['message']['text'])
                        if 'да' in result['result']['alternatives'][0]['message']['text'].lower():
                            await handle_violation(message, 'Обнаружен спам')
                    else:
                        logging.error(f'Ошибка Yandex API: {response.status} - {await response.text()}')
        except Exception as e:
            logging.error(f'Ошибка анализа спама: {e}')
