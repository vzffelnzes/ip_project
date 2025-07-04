import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, Router
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from database import Base, async_session, engine
from handlers import admin_handlers, callback_handlers, echo_handler, user_commands
from models import Group

logging.basicConfig(level=logging.INFO)

# Инициализируем планировщик
scheduler = AsyncIOScheduler(timezone='UTC')

# Yandex API ключи


bot = Bot(token=TOKEN)
router = Router()
dp = Dispatcher()


# Глобальные переменные с настройками для каждого чата


# Планировщик
async def check_expired_subscriptions():
	now = datetime.now()
	async with async_session() as session:
		async with session.begin():
			expired_subs = await session.execute(
				select(Group).where(Group.subscription.expires_at <= now, Group.subscription.is_premium == True)
			)
			for chat in expired_subs.scalars():
				try:
					print(f'Подписка пользователя {chat.owner_id} истекла!')
					chat.subscription.expires_at = None
					chat.subscription.is_premium = False
					session.flush()
					group_title = (await bot.get_chat(chat.group_id)).title
					await bot.send_message(chat.owner_id, f'Подписка на бота для группы {group_title} истекла!')
				except Exception as e:
					print(f'Ошибка при отправке сообщения: {e}')


async def start_scheduler():
	scheduler.add_job(check_expired_subscriptions, 'interval', minutes=1)
	scheduler.start()


async def init_db():
	async with engine.begin() as conn:
		await conn.run_sync(Base.metadata.create_all)


async def main():
	await init_db()
	await start_scheduler()
	dp.include_router(router)
	dp.include_router(echo_handler.router)
	dp.include_router(user_commands.router)
	dp.include_router(admin_handlers.router)
	dp.include_router(callback_handlers.router)
	await bot.delete_webhook(drop_pending_updates=True)
	await dp.start_polling(bot)


if __name__ == '__main__':
	try:
		asyncio.run(main())
	except (KeyboardInterrupt, SystemExit):
		logging.info('Бот остановлен')
