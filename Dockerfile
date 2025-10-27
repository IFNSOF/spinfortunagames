# Используем Python
FROM python:3.11-slim

WORKDIR /app

# Установим зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем файлы
COPY . .

# Указываем порт (Koyeb Health Check)
EXPOSE 8000

# Команда запуска
CMD ["python", "bot.py"]
