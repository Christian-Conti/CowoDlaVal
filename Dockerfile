FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN addgroup --system django && adduser --system --ingroup django django

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=django:django . .
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]


FROM base AS development

RUN apt-get update && apt-get install -y --no-install-recommends \
    tk8.6 \
    libtk8.6 \
    && rm -rf /var/lib/apt/lists/* \
    && chmod +x \
        /app/scripts/bookings_dashboard_gui.sh \
        /app/scripts/stats_dashboard_gui.sh

USER django


FROM base AS production

USER django
