## Stage 1 – build
FROM node:20-alpine AS build
ARG VITE_BASE_URL=/
ENV VITE_BASE_URL=$VITE_BASE_URL
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

## Stage 2 – serve
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
