FROM node:20-alpine

WORKDIR /usr/src/app

COPY package.json package-lock.json ./
COPY app-data/package.json ./app-data/
COPY app-comm/package.json ./app-comm/
COPY app-sync/package.json ./app-sync/
COPY tsconfig.base.json ./

RUN npm install

COPY app-data/ ./app-data/

WORKDIR /usr/src/app/app-data

RUN npm run build

CMD ["npm", "start"]