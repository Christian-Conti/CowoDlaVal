FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    tk8.6 \
    libtk8.6 \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --system django && adduser --system --ingroup django django

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x /app/entrypoint.sh /app/scripts/bookings_dashboard_gui.sh && \
    chown -R django:django /app
USER django

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]

# cowodlaval-stats-launcher-permissions
RUN chmod +x /app/scripts/stats_dashboard_gui.sh
