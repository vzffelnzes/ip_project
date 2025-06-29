from aiogram import Router
from aiogram.types import ErrorEvent

router = Router()


@router.error()
async def handle_errors(event: ErrorEvent):
	print(f'Произошла ошибка: {event.exception}')
