# Sistema de inventario (Django)

## Puesta en marcha
```bash
python -m venv env && env\Scripts\activate        # Linux/Mac: source env/bin/activate
pip install -r requirements.txt                   # incluye Django y Pillow (imágenes)
python manage.py makemigrations inventario
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000           # accesible desde la red local
```
Abra http://127.0.0.1:8000/ e inicie sesión. Cree más usuarios desde /admin/ (Usuarios).

## Secciones
- **Resumen** (`/resumen/`): indicadores, gráfico de ventas por mes y promedio de ventas mensual.
- **Productos** (`/`): tarjetas con imagen, descripción, precio y stock; botón flotante de carrito para vender.
- **Ventas** (`/ventas/`): últimas 20 ventas, con búsqueda por rango de fechas.

## Imágenes de productos
Se guardan en `media/` (configurado en settings.py con `MEDIA_URL` y `MEDIA_ROOT`).

## PostgreSQL (recomendado para producción)
```bash
pip install "psycopg[binary]"
set DB_ENGINE=postgresql & set DB_NAME=inventario & set DB_USER=... & set DB_PASSWORD=...
python manage.py migrate
```
