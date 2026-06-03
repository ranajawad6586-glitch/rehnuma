FROM node:22-slim

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .
RUN npm run build

EXPOSE 3000
# API_PROXY_TARGET is read at RUNTIME by the proxy route handler (no build arg needed).
# Honor $PORT (Render sets it); default 3000 for local compose.
CMD ["sh", "-c", "npm start -- -p ${PORT:-3000}"]
