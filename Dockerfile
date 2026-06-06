FROM python:3.11-slim

LABEL org.opencontainers.image.title="Kuzuryu Board Meetings"
LABEL org.opencontainers.image.description="Slack board meeting quorum, voting, and minutes service."
LABEL org.opencontainers.image.source="https://github.com/Quantyra/kuzuryu-board-meetings"
LABEL org.opencontainers.image.licenses="AGPL-3.0-or-later"

WORKDIR /app
COPY pyproject.toml README.md /app/
COPY src /app/src
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "kuzuryu_board_meetings.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
