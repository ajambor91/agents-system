FROM node:20-alpine

WORKDIR /usr/src/app

COPY package.json package-lock.json ./
COPY app-data/package.json ./app-data/
COPY app-comm/package.json ./app-comm/
COPY app-sync/package.json ./app-sync/
COPY tsconfig.base.json ./

RUN npm install

COPY app-sync/ ./app-sync/

WORKDIR /usr/src/app/app-sync

RUN npm run build

CMD ["npm", "start"]
