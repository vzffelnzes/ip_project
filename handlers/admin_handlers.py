import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from database import async_session
from models import Group

router = Router()
chat_settings = defaultdict(lambda: {'spam_detection': False, 'violations': defaultdict(int)})


async def is_admin(message: int, user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором чата"""
    try:
        chat_member = await message.bot.get_chat_member(message.chat.id, user_id)
        return chat_member.status in ['administrator', 'creator']
    except Exception as e:
        logging.error(f'Ошибка при проверке прав администратора: {e}')
        return False


async def send_temporary_message(chat, text: str, delay: int = 3):
    """Отправляет временное сообщение"""
    sent_message = await chat.bot.send_message(chat.id, text)
    await asyncio.sleep(delay)
    await chat.bot.delete_message(chat.id, sent_message.message_id)


async def delete_command_message(message: Message, delay: int = 20):
    """Удаляет сообщение команды"""
    await asyncio.sleep(delay)
    await message.delete_message(message.chat.id, message.message_id)


@router.message(Command('init'))
async def init_command(message: Message):
    if not await is_admin(message, message.from_user.id):
        await send_temporary_message(message.chat, '❌ Команда доступна только администраторам')
        return
    async with async_session() as session:
        async with session.begin():
            try:
                new_group = Group(
                    group_id=str(message.chat.id),
                    owner_id=message.from_user.id,
                )
                session.add(new_group)
                await session.commit()
                await send_temporary_message(message.chat, 'Группа успешно добавлена!')
            except Exception as e:
                await send_temporary_message(message.chat, f'Ошибка при добавлении группы: {e}')


@router.message(Command('unban'))
async def unban_user(message: Message):
    asyncio.create_task(delete_command_message(message))
    if not await is_admin(message, message.from_user.id):
        await send_temporary_message(message.chat, '❌ Команда доступна только администраторам')
        return
    if not message.reply_to_message:
        await send_temporary_message(message.chat, '⚠️ Ответьте на сообщение пользователя для разбана')
        return
    user_to_unban = message.reply_to_message.from_user.id
    try:
        await message.unban_chat_member(chat_id=message.chat, user_id=user_to_unban)
        await send_temporary_message(
            message.chat, f'✅ Пользователь {message.reply_to_message.from_user.full_name} был разбанен'
        )
    except Exception as e:
        await send_temporary_message(message.chat, f'❌ Ошибка разбана: {e}')


@router.message(Command('ban'))
async def ban_user(message: Message):
    asyncio.create_task(delete_command_message(message))
    if not await is_admin(message, message.from_user.id):
        await send_temporary_message(message.chat, '❌ Команда доступна только администраторам')
        return
    if not message.reply_to_message:
        await send_temporary_message(message.chat, '⚠️ Ответьте на сообщение пользователя для бана')
        return
    user_to_ban = message.reply_to_message.from_user.id
    try:
        await message.ban_chat_member(chat_id=message.chat.id, user_id=user_to_ban)
        await send_temporary_message(
            message.chat.id, f'🔨 Пользователь {message.reply_to_message.from_user.full_name} был забанен'
        )
    except Exception as e:
        await send_temporary_message(message.chat.id, f'❌ Ошибка бана: {e}')


@router.message(Command('kick'))
async def kick_user(message: Message):
    asyncio.create_task(delete_command_message(message))
    if not await is_admin(message, message.from_user.id):
        await send_temporary_message(message.chat.id, '❌ Команда доступна только администраторам')
        return
    if not message.reply_to_message:
        await send_temporary_message(message.chat.id, '⚠️ Ответьте на сообщение пользователя для кика')
        return
    user_to_kick = message.reply_to_message.from_user.id
    try:
        await message.ban_chat_member(chat_id=message.chat.id, user_id=user_to_kick)
        await message.unban_chat_member(chat_id=message.chat.id, user_id=user_to_kick)
        await send_temporary_message(
            message.chat.id, f'👢 Пользователь {message.reply_to_message.from_user.full_name} был кикнут'
        )
    except Exception as e:
        await send_temporary_message(message.chat.id, f'❌ Ошибка кика: {e}')


@router.message(Command('addword'))
async def add_banned_word(message: Message):
    asyncio.create_task(delete_command_message(message))
    if not await is_admin(message, message.from_user.id):
        await send_temporary_message(message.chat.id, '❌ Команда доступна только администраторам')
        return
    if len(message.text.split()) < 2:
        await send_temporary_message(message.chat.id, '⚠️ Укажите слово для добавления в список запрещенных')
        return
    new_word = message.text.split(maxsplit=1)[1].lower()
    if new_word in banned_words:
        await send_temporary_message(message.chat.id, f"⚠️ Слово '{new_word}' уже запрещено")
        return
    banned_words.add(new_word)
    add_word_to_db(new_word)
    await send_temporary_message(message.chat.id, f"✅ Слово '{new_word}' добавлено в список запрещенных")


@router.message(Command('delword'))
async def delete_banned_word(message: Message):
    asyncio.create_task(delete_command_message(message))
    if not await is_admin(message, message.from_user.id):
        await send_temporary_message(message.chat.id, '❌ Команда доступна только администраторам')
        return
    if len(message.text.split()) < 2:
        await send_temporary_message(message.chat.id, '⚠️ Укажите слово для удаления из списка запрещенных')
        return
    word_to_delete = message.text.split(maxsplit=1)[1].lower()
    if word_to_delete not in banned_words:
        await send_temporary_message(message.chat.id, f"⚠️ Слово '{word_to_delete}' не найдено в списке запрещенных")
        return
    banned_words.remove(word_to_delete)
    delete_word_from_db(word_to_delete)
    await send_temporary_message(message.chat.id, f"✅ Слово '{word_to_delete}' удалено из списка запрещенных")


@router.message(Command('del'))
async def delete_message_command(message: Message):
    asyncio.create_task(delete_command_message(message))
    if not await is_admin(message, message.from_user.id):
        await send_temporary_message(message.chat.id, '❌ Команда доступна только администраторам')
        return
    if not message.reply_to_message:
        await send_temporary_message(message.chat.id, '⚠️ Ответьте на сообщение, которое нужно удалить')
        return
    try:
        await message.delete_message(message.chat.id, message.reply_to_message.message_id)
        await send_temporary_message(message.chat.id, '✅ Сообщение удалено')
    except Exception as e:
        await send_temporary_message(message.chat.id, f'❌ Ошибка удаления: {e}')


@router.message(Command('spamstatus'))
async def spam_status(message: Message):
    asyncio.create_task(delete_command_message(message))
    chat_id = message.chat.id
    state = '✅ включен' if chat_settings.get(chat_id, {}).get('spam_detection', False) else '❌ выключен'
    await send_temporary_message(chat_id, f'Текущий статус спам-фильтра: {state}')


@router.message(Command('togglespam'))
async def toggle_spam_detection(message: Message):
    asyncio.create_task(delete_command_message(message))
    if not await is_admin(message, message.from_user.id):
        await send_temporary_message(message.chat.id, '❌ Команда доступна только администраторам')
        return

    chat_id = message.chat.id
    current_state = chat_settings[chat_id]['spam_detection']
    chat_settings[chat_id]['spam_detection'] = not current_state

    state = '✅ включен' if chat_settings[chat_id]['spam_detection'] else '❌ выключен'
    await send_temporary_message(chat_id, f'Режим фильтрации спама {state} для этого чата')


@router.message(Command('cleardb'))
async def clear_db_command(message: Message):
    asyncio.create_task(delete_command_message(message))
    if not await is_admin(message, message.from_user.id):
        await send_temporary_message(message.chat.id, '❌ Команда доступна только администраторам')
        return
    try:
        clear_database()
        global banned_words
        banned_words = set()
        await send_temporary_message(message.chat.id, '✅ База данных успешно очищена')
    except Exception as e:
        await send_temporary_message(message.chat.id, f'❌ Ошибка при очистке базы данных: {e}')


@router.message(Command('timeout'))
async def timeout_user(message: Message):
    asyncio.create_task(delete_command_message(message))
    if not await is_admin(message, message.from_user.id):
        await send_temporary_message(message.chat.id, '❌ Команда доступна только администраторам')
        return
    if not message.reply_to_message:
        await send_temporary_message(message.chat.id, '⚠️ Эта команда должна быть ответом на сообщение пользователя')
        return
    args = message.text.split()
    if len(args) < 2:
        await send_temporary_message(message.chat.id,
                                     '⚠️ Укажите длительность тайм-аута в минутах. Пример: /timeout 10')
        return
    try:
        timeout_duration = int(args[1])
        until_date = datetime.now() + timedelta(minutes=timeout_duration)
    except ValueError:
        await send_temporary_message(message.chat.id, '⚠️ Укажите корректное число для длительности тайм-аута')
        return
    user_to_timeout = message.reply_to_message.from_user.id
    try:
        await message.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=user_to_timeout,
            permissions={'can_send_messages': False},
            until_date=until_date,
        )
        await send_temporary_message(
            message.chat.id,
            f'⏳ Пользователь {message.reply_to_message.from_user.full_name} отправлен в тайм-аут на {timeout_duration} мин.',
        )
    except Exception as e:
        await send_temporary_message(message.chat.id, f'❌ Ошибка при тайм-ауте: {e}')


@router.message(Command('untimeout'))
async def untimeout_user(message: Message):
    asyncio.create_task(delete_command_message(message))
    if not await is_admin(message.chat.id, message.from_user.id):
        await send_temporary_message(message.chat.id, '❌ Команда доступна только администраторам')
        return
    if not message.reply_to_message:
        await send_temporary_message(message.chat.id, '⚠️ Эта команда должна быть ответом на сообщение пользователя')
        return
    user_to_untimeout = message.reply_to_message.from_user.id
    try:
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=user_to_untimeout,
            permissions={
                'can_send_messages': True,
                'can_send_media_messages': True,
                'can_send_polls': True,
                'can_send_other_messages': True,
                'can_add_web_page_previews': True,
                'can_change_info': False,
                'can_invite_users': False,
                'can_pin_messages': False,
            },
        )
        await send_temporary_message(
            message.chat.id, f'✅ С пользователя {message.reply_to_message.from_user.full_name} снят тайм-аут'
        )
    except Exception as e:
        await send_temporary_message(message.chat.id, f'❌ Ошибка при снятии тайм-аута: {e}')
