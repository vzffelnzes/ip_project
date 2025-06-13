# Используем официальный образ Python
FROM python:3.12-slim

# Указываем рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код бота
COPY . .

# Команда по умолчанию для запуска бота
CMD ["python", "main.py"]