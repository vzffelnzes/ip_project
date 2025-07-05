import asyncio
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

# === Настройки ===
DATABASE_URL_ASYNC = 'postgresql+asyncpg://postgres:password@localhost/mydatabase'
DATABASE_URL_SYNC = 'postgresql://postgres:password@localhost/postgres'  # Для создания новой БД

# === Логирование ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('DB Setup')

# === ORM Base ===
Base = declarative_base()

# === Асинхронный движок и сессия ===
engine = create_async_engine(DATABASE_URL_ASYNC, echo=True)
async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


# === Функция для создания БД и таблиц ===
def setup_database():
	# Синхронный движок для управления на уровне БД
	sync_engine = create_engine(DATABASE_URL_SYNC)

	with sync_engine.connect() as conn:
		conn.execution_options(isolation_level='AUTOCOMMIT')
		db_exists = conn.scalar(text("SELECT 1 FROM pg_database WHERE datname='mydatabase'"))

		if not db_exists:
			logger.info('База данных не найдена. Создаю новую...')
			conn.execute(text('CREATE DATABASE mydatabase'))
		else:
			logger.info('База данных уже существует.')

	# Теперь подключаемся к созданной БД и создаём таблицы
	try:
		asyncio.run(create_tables())
	except Exception as e:
		logger.warning(f'Не удалось создать таблицы: {e}')


async def create_tables():
	async with engine.begin() as conn:
		await conn.run_sync(Base.metadata.create_all)
		logger.info('Таблицы успешно созданы.')


# === Запуск ===
if __name__ == '__main__':
	setup_database()


"""def add_word_to_db(word: str, group_id: int):
    db = SessionLocal()
    try:
        new_word = BadWords(word=word.lower(), group_id=group_id)  # сохраняем в нижнем регистре
        db.add(new_word)
        db.commit()
    except Exception:
        db.rollback()  # откат при ошибке дубликата и т.п.
    finally:
        db.close()


def get_all_banned_words(group_id: int):
    db = SessionLocal()
    words = db.query(BadWords.word).filter(BadWords.group_id == group_id).all()
    db.close()
    return [word[0] for word in words]


def delete_word_from_db(word: str, group_id: int):
    db = SessionLocal()
    db.query(BadWords).filter(BadWords.word == word.lower(), BadWords.group_id == group_id).delete()
    db.commit()
    db.close()


def clear_all_words(group_id: int):
    db = SessionLocal()
    db.query(BadWords).filter(BadWords.group_id == group_id).delete()
    db.commit()
    db.close()
"""
