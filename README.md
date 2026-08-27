# Cowo d'la val - production Django booking site

Sito Django per la gestione delle prenotazioni giornaliere delle quattro postazioni del coworking **Cowo d'la val**.

## Cosa è stato integrato

- PostgreSQL al posto di SQLite.
- Interfaccia e contenuti ricostruiti a partire dal materiale `spazio coworking`.
- Quattro postazioni prenotabili per data, con controllo anti-doppia-prenotazione sia applicativo sia a livello database.
- Registrazione, login, cancellazione prenotazioni e pannello admin Django.
- Lingue: italiano, inglese, tedesco e francese.
- Tema chiaro/scuro automatico tramite la preferenza del sistema operativo/browser.
- Form di contatto verso `cowodlaval@inventati.org`, configurabile via ambiente.
- Tariffe, servizi, regole condivise e PDF informativo originale disponibili dal sito.
- WhiteNoise per gli asset statici, Gunicorn e impostazioni di sicurezza parametrizzate per produzione.
- Dockerfile e Docker Compose con PostgreSQL.

## Nota di sicurezza importante

Il PDF `New Services - MAIL.pdf` del materiale sorgente contiene credenziali di accesso reali. Per questo motivo **non viene distribuito nel sito né nel pacchetto finale**. La password di quella casella dovrebbe essere cambiata prima della pubblicazione del sito.

Anche il vecchio prototipo HTML conteneva configurazione Supabase e una password admin direttamente nel JavaScript. Quella logica è stata completamente rimossa: database e amministrazione passano ora dal backend Django.

## Avvio con Docker Compose

1. Copia il file di esempio:

```bash
cp .env.example .env
```

2. Modifica almeno:

```text
DJANGO_SECRET_KEY
DJANGO_ALLOWED_HOSTS
DJANGO_CSRF_TRUSTED_ORIGINS
POSTGRES_PASSWORD
DATABASE_URL
```

Per Docker Compose il valore `DATABASE_URL` deve usare `db` come hostname, ad esempio:

```text
DATABASE_URL=postgresql://coworking:UNA_PASSWORD_FORTE@db:5432/coworking
```

3. Avvia:

```bash
docker compose up --build -d
```

Le migrazioni, `collectstatic` e la creazione/aggiornamento delle quattro postazioni vengono eseguite automaticamente all'avvio del container web.

4. Crea l'amministratore Django:

```bash
docker compose exec web python manage.py createsuperuser
```

5. In sviluppo locale il sito sarà disponibile su:

```text
http://127.0.0.1:8000/
```

## Deploy senza Docker

Serve Python 3.12+ e un'istanza PostgreSQL raggiungibile.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py seed_cowo
python manage.py createsuperuser
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

In produzione Gunicorn dovrebbe stare dietro a un reverse proxy HTTPS, per esempio Nginx, Caddy o il proxy del provider.

## Configurazione email

Il form **Contatti** invia le richieste all'indirizzo definito da:

```text
CONTACT_EMAIL=cowodlaval@inventati.org
```

Per l'invio reale devono essere compilate nel `.env` anche le impostazioni SMTP:

```text
EMAIL_HOST
EMAIL_PORT
EMAIL_HOST_USER
EMAIL_HOST_PASSWORD
EMAIL_USE_TLS
EMAIL_USE_SSL
DEFAULT_FROM_EMAIL
```

Le credenziali SMTP non devono essere inserite nel repository.

## HTTPS e sicurezza

Quando il dominio definitivo è attivo dietro HTTPS:

```text
DJANGO_DEBUG=False
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_BEHIND_PROXY=True
```

Imposta `DJANGO_CSRF_TRUSTED_ORIGINS` con schema HTTPS, ad esempio:

```text
DJANGO_CSRF_TRUSTED_ORIGINS=https://cowodlaval.example.org
```

`DJANGO_SECURE_HSTS_SECONDS` è lasciato a `0` nel file di esempio. Dopo aver verificato che il sito funzioni esclusivamente in HTTPS può essere aumentato progressivamente.

Prima del deploy definitivo eseguire:

```bash
python manage.py check --deploy
```

Prima dell'apertura al pubblico conviene inoltre verificare backup, recupero password, indirizzo SMTP, dominio definitivo e l'informativa privacy applicabile al servizio. Il sito non include analytics o cookie di profilazione: usa solo le funzionalità necessarie a sessione, autenticazione e protezione CSRF.

## Test

I test usano impostazioni separate con SQLite in memoria, esclusivamente per rendere la suite automatica indipendente dal database di produzione:

```bash
DJANGO_SETTINGS_MODULE=config.settings_test python manage.py test
```

L'applicazione normale non usa SQLite.

## Struttura principale

```text
accounts/                 registrazione utenti
bookings/                 prenotazioni, vincoli e logica transazionale
config/                   settings, home e form contatti
locale/                   traduzioni IT/DE/FR; inglese come testo sorgente
spaces/                   quattro postazioni coworking
templates/                interfaccia HTML
static/css/               tema responsive chiaro/scuro
static/img/               loghi forniti
static/docs/              PDF tariffe/regole fornito
Dockerfile                immagine web
docker-compose.yml          stack web + PostgreSQL
```

## Backup

Il volume PostgreSQL contiene i dati delle prenotazioni. In produzione è consigliato usare PostgreSQL gestito oppure predisporre backup periodici con `pg_dump`, conservati fuori dal server applicativo e protetti adeguatamente.
