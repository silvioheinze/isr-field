# isr-field

 docker compose exec app python manage.py makemigrations

 docker compose up -d
 docker compose exec app python manage.py migrate
 docker compose exec app python manage.py createsuperuser