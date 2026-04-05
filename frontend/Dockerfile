FROM node:20-alpine

WORKDIR /app

# Сначала копируем конфиги для кэширования слоев
COPY package*.json ./
RUN npm install

# Копируем остальной код
COPY . .

# Собираем в рантайме, чтобы NEXT_PUBLIC_* из docker-compose точно попали в клиентский бандл
CMD ["sh", "-c", "npm run build && npm start"]