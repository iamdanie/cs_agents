FROM python:3.12-slim

RUN apt-get update \
	&& apt-get install -y curl build-essential gcc \
	&& curl -sSL https://install.python-poetry.org | python3 - \
	&& apt-get purge -y --auto-remove curl build-essential \
	&& rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
	&& poetry install --no-interaction --no-ansi --no-root

# 3. Copy the rest of the code
COPY . .

# 4. Expose FastAPI port and start Uvicorn
ENV PORT=8000
EXPOSE 8000
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
