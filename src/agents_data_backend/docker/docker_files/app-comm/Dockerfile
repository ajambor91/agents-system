FROM node:20-alpine

WORKDIR /usr/src/app

# Kopiowanie definicji monorepo i paczek
COPY package.json package-lock.json* ./
COPY app-data/package.json ./app-data/
COPY app-comm/package.json ./app-comm/
COPY app-sync/package.json ./app-sync/
COPY tsconfig.base.json ./

# Instalacja zależności
RUN npm install

# --- TEJ LINIJKI BRAKOWAŁO ---
# Skopiowanie kodu źródłowego i konfiguracji TypeScript dla app-comm
COPY app-comm/ ./app-comm/
# -----------------------------

WORKDIR /usr/src/app/app-comm

# Kompilacja
RUN npm run build

CMD ["npm", "start"]