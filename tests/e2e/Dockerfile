FROM mcr.microsoft.com/playwright:v1.44.0-jammy

WORKDIR /e2e

COPY package.json ./
RUN npm install
RUN npx playwright install --with-deps chromium

COPY . .

CMD ["npx", "playwright", "test"]
