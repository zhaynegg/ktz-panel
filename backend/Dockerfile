# Используем легкий образ Python
FROM python:3.11

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код бэкенда
COPY backend/ /app/
COPY scripts/locomotive_simulator.py /app/locomotive_simulator.py

# Запускаем через uvicorn (важно для FastAPI)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]