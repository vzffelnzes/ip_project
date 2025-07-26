# Этап 1: Сборка uv
FROM python:3.12-slim as builder

# Установка uv
RUN pip install --no-cache-dir uv

# Копируем pyproject.toml и устанавливаем зависимости
WORKDIR /app
COPY pyproject.toml ./

# Устанавливаем зависимости в режиме production (без dev)
RUN uv pip install --system --no-dev -r pyproject.toml


# Этап 2: Финальный образ
FROM python:3.12-slim

# Устанавливаем зависимости через pip (чтобы не тащить uv в продакшн)
# Но мы скопируем установленные пакеты из builder

WORKDIR /app

# Копируем установленные пакеты из builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Копируем исходный код
COPY . .

# Запуск бота
CMD ["python", "main.py"]
