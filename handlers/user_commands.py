import asyncio

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

router = Router()


async def send_temporary_message(chat, text: str, delay: int = 3):
	"""Отправляет временное сообщение"""
	sent_message = await chat.bot.send_message(chat.id, text)
	await asyncio.sleep(delay)
	# await chat.bot.delete_message(chat.id, sent_message.message_id)


def is_private_chat(handler):
	async def wrapper(message: Message):
		if message.chat.type == 'private':
			return await handler(message)

	return wrapper


def not_private_chat(handler):
	async def wrapper(message: Message):
		if message.chat.type != 'private':
			print('Not private chat')
			return await handler(message)

	return wrapper


@router.message(Command('start'))
@is_private_chat
async def start_command(message: Message):
	keyboard = InlineKeyboardMarkup(
		inline_keyboard=[
			[InlineKeyboardButton(text='ℹ️ О боте', callback_data='about_bot')],
			[InlineKeyboardButton(text='💼 Моя подписка', callback_data='my_subscription')],
			[InlineKeyboardButton(text='👥 Мои группы', callback_data='my_groups')],
		]
	)

	await message.answer('👋 Привет! Я бот для модерации чатов.', reply_markup=keyboard)


@router.message(Command('id'))
async def id_command(message: Message):
	await message.answer(str(message.from_user.id))
