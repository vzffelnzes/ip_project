from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from database import async_session
from models import Group

router = Router()


class SubscriptionForm(StatesGroup):
	subscription_link = State()


def get_main_keyboard():
	keyboard = InlineKeyboardMarkup(
		inline_keyboard=[
			[InlineKeyboardButton(text='ℹ️ О боте', callback_data='about_bot')],
			[InlineKeyboardButton(text='💼 Моя подписка', callback_data='my_subscription')],
			[InlineKeyboardButton(text='➕ Добавить чат', callback_data='add_chat')],
		]
	)
	return keyboard


@router.callback_query(lambda call: call.data == 'about_bot')
async def about_bot_handler(call: CallbackQuery):
	info_text = (
		'🤖 *Я помогаю модерировать Telegram-чаты.*\n\n'
		'Вот мои возможности:\n'
		'- Фильтрация запрещённых слов\n'
		'- Обнаружение спама и рекламы\n'
		'- Управление пользователями (тайм-аут, бан)\n'
		'- Настраиваемая модерация через команды\n'
		'- Поддержка Yandex GPT для анализа сообщений'
	)
	back_button = InlineKeyboardMarkup(
		inline_keyboard=[[InlineKeyboardButton(text='⬅️ Назад', callback_data='main_menu')]]
	)
	await call.message.edit_text(info_text, reply_markup=back_button, parse_mode='Markdown')
	await call.answer()


@router.callback_query(lambda call: call.data == 'my_subscription')
async def subscription_handler(call: CallbackQuery):
	async with async_session() as session:
		async with session.begin():
			chats = await session.execute(select(Group).where(Group.owner_id == call.from_user.id))
			if chats:
				is_active = chats.scalar().first().subscription.is_premium

				status_text = '✅ Активна' if is_active else '❌ Не активна'
				response_text = (
					f'📋 *Статус вашей подписки*\n\n'
					f'Текущий статус: **{status_text}**\n\n'
					'Подписка необходима для использования всех функций бота.'
				)
				if is_active:
					back_button = InlineKeyboardMarkup(
						inline_keyboard=[[InlineKeyboardButton(text='⬅️ Назад', callback_data='main_menu')]]
					)
				else:
					back_button = InlineKeyboardMarkup(
						inline_keyboard=[
							[
								InlineKeyboardButton(text='⬅️ Назад', callback_data='main_menu'),
								InlineKeyboardButton(text='✅ Включить', callback_data='enable_subscription'),
							]
						]
					)
			else:
				response_text = 'Вначале добавьте хотя бы один чат!'
				back_button = InlineKeyboardMarkup(
					inline_keyboard=[[InlineKeyboardButton(text='⬅️ Назад', callback_data='main_menu')]]
				)

			await call.message.edit_text(response_text, reply_markup=back_button, parse_mode='Markdown')
			await call.answer()


@router.callback_query(lambda call: call.data == 'main_menu')
async def back_to_main(call: CallbackQuery):
	await call.message.edit_text('👋 Привет! Я бот для модерации чатов.', reply_markup=get_main_keyboard())
	await call.answer()


@router.callback_query(lambda call: call.data == 'my_groups')
async def add_chat(call: CallbackQuery):
	buttons = InlineKeyboardMarkup(
		inline_keyboard=[
			[
				InlineKeyboardButton(text='⬅️ Назад', callback_data='main_menu'),
				InlineKeyboardButton(text='✅ Далее', callback_data='chat_link'),
			]
		]
	)
	async with async_session() as session:
		async with session.begin():
			groups = await session.execute(select(Group).where(Group.owner_id == call.from_user.id))
			if groups.scalars().all():
				text = '\n'.join(
					f'{await call.bot.get_chat(int(g.group_id)).title} - {g.subscription.expires_at}'
					for g in groups.scalars()
				)
				await call.message.edit_text('Ваши группы:\n', f'{text}', reply_markup=buttons, parse_mode='Markdown')
			else:
				await call.message.edit_text(
					'Добавьте бота в чат и пропишите в чате /init.', reply_markup=buttons, parse_mode='Markdown'
				)
	await call.answer()


@router.callback_query(lambda call: call.data == 'chat_link')
async def enable_subscription(call: CallbackQuery, state: FSMContext):
	buttons = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='⬅️ Назад', callback_data='main_menu')]])
	await call.message.edit_text('Пришлите ссылку на группу.', reply_markup=buttons)
	await state.set_state(SubscriptionForm.subscription_link)
	await call.answer()


@router.message(SubscriptionForm.subscription_link)
async def process_group_link(message: Message, state: FSMContext):
	group_link = message.text.strip()

	# Проверка формата ссылки (простая проверка)
	if not (group_link.startswith('https://t.me/') or group_link.startswith('@')):
		await message.answer('Некорректная ссылка. Укажите правильную (например, https://t.me/...  или @...)')

		# Не выходим из состояния, чтобы пользователь попробовал снова
		return

	await message.answer(f'Спасибо! Подписка на группу `{group_link}` оформлена.')
	await state.clear()
