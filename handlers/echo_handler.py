import asyncio
import datetime
import logging
from datetime import datetime, timedelta

from aiogram import Router
from aiogram.client.session import aiohttp
from aiogram.methods import RestrictChatMember
from aiogram.types import Message
from sqlalchemy import func, select

from database import async_session
from models import BadWords, GroupSettings, UserViolation, ViolationRule

router = Router()


async def send_temporary_message(chat, text: str, delay: int = 3):
	"""Отправляет временное сообщение"""
	sent_message = await chat.bot.send_message(chat.id, text)
	await asyncio.sleep(delay)
	await chat.bot.delete_message(chat.id, sent_message.message_id)


async def handle_violation(message: Message, reason: str):
	chat_id = message.chat
	user_id = message.from_user.id
	async with async_session as session:
		async with session.begin():
			# Получаем или создаём запись о нарушении
			result = await session.execute(
				select(UserViolation).where(UserViolation.group_id == chat_id, UserViolation.user_id == user_id)
			)
			violation = result.scalars().first()

			if not violation:
				violation = UserViolation(chat_id=chat_id, user_id=user_id, count=1)
				session.add(violation)
			else:
				violation.count += 1
				violation.last_violation_time = func.now()

			await session.flush()

			# Ищем подходящее правило по количеству нарушений
			result = await session.execute(
				select(ViolationRule)
				.where(ViolationRule.group_id == chat_id)
				.where(ViolationRule.violation_count == violation.count)
				.limit(1)
			)

			rule = result.scalars().first()
			if rule:
				await apply_punishment(message, rule, user_id)

			return violation


async def apply_punishment(message, rule: 'ViolationRule', user_id: int):
	chat_id = message.chat.id
	user = message.from_user

	if rule.action_type == 'warn':
		await message.reply(f'⚠️ Предупреждение для {user.mention} — {rule.violation_count} нарушений.')

	elif rule.action_type == 'mute':
		until_date = datetime.utcnow() + timedelta(seconds=rule.mute_duration_sec)
		await message.bot(
			RestrictChatMember(
				chat_id=chat_id, user_id=user_id, permissions=message.chat.permissions, until_date=until_date
			)
		)
		duration_min = rule.mute_duration_sec // 60
		await message.reply(f'🔇 {user.mention} получил мут на {duration_min} мин за {rule.violation_count} нарушений.')

	elif rule.action_type == 'ban':
		await message.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
		await message.reply(f'⛔️ {user.mention} заблокирован за {rule.violation_count} нарушений.')


@router.message()
async def filter_messages(message: Message):
	chat_id = message.chat.id

	# Проверка текста на запрещенные слова
	if hasattr(message, 'text') and message.text:
		async with async_session as session:
			bad_words = session.execute(select(BadWords).where(BadWords.group_id == chat_id))
			for word in bad_words.scalars():
				if word.word in message.text.lower():
					await handle_violation(message, f"Обнаружено запрещенное слово: '{word}'")
					return

	async with async_session as session:
		spam = session.execute(select(GroupSettings).where(GroupSettings.group_id == chat_id))

	# Проверка на спам (только если включен для этого чата)
	if spam.scalars().first.is_censorship_enabled and hasattr(message, 'text') and message.text:
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
