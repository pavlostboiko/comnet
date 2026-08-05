# Digest замість тега (див. frontend/Dockerfile щодо оновлення).
FROM python:3.12-slim@sha256:646fb0bca3dd3ea1bcc6feb72c17ed16eed6e10cffc732fcc1478bd3e7f02d7b

WORKDIR /app

# requirements.txt — джерело правди (редагуємо руками), requirements.lock —
# згенерований зліпок УСІХ залежностей із хешами. `--require-hashes` не дасть
# встановити перевипущений артефакт із тією ж версією.
# Перегенерувати: pip-compile --generate-hashes --output-file=requirements.lock requirements.txt
COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir --require-hashes -r requirements.lock

COPY . .
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/bin/sh", "/app/entrypoint.sh"]
