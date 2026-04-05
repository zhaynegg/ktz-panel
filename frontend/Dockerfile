FROM node:20-alpine

WORKDIR /app

# Сначала копируем конфиги для кэширования слоев
COPY package.json package-lock.json ./
RUN npm ci

# Копируем остальной код
COPY . .

ENV NODE_ENV=production
EXPOSE 3000

# Собираем в рантайме, чтобы NEXT_PUBLIC_* из docker-compose точно попали в клиентский бандл
CMD ["sh", "-c", "npm run build && npm start"]