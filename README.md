# Blog con Django: formas de proteger vistas

Blog con formularios, autenticación y perfil, más cuatro formas de proteger vistas:
vistas con clases y mixins, decoradores, un permiso propio en el modelo y permisos por objeto con django-guardian.

## Cómo correrlo

    pip install -r requirements.txt      # necesita Python 3.12 o más (Django 6.1)
    python manage.py migrate
    python manage.py cargar_demo_auth    # usuarios, grupos y 2 posts
    python manage.py runserver
    python manage.py test                # 70 tests

Usuarios demo (contraseña de todos: `clave-demo-123`):

| Usuario | Qué es | Qué puede |
|---|---|---|
| `ana`, `beto` | Autores comunes | Escribir, editar lo suyo. No pueden publicar (solo guardar borradores) |
| `carla` | Grupo **Editores** | Editar y eliminar posts ajenos, ver `/borradores/` |
| `dani` | Grupo **Publicadores** | Tiene `posts.puede_publicar`: puede pasar un post a "publicado" |

Para el admin: `python manage.py createsuperuser`. Un superusuario pasa TODAS las verificaciones de permisos,
así que no sirve para probar permisos: usá los usuarios comunes.

## Mapa: dónde está cada forma de protección

| Forma | Archivo | Rutas para probar |
|---|---|---|
| `LoginRequiredMixin` | `posts/views_cbv.py` → `PostCreateView` | `/cbv/nuevo/` |
| `UserPassesTestMixin` (solo el dueño) | `posts/views_cbv.py` → `PostUpdateView`, `PostDeleteView` | `/<slug>/cbv-editar/`, `/<slug>/cbv-eliminar/` |
| `PermissionRequiredMixin` | `posts/views_cbv.py` → `BorradoresCbvView` | `/cbv/borradores/` |
| `@permission_required` | `posts/views.py` → `borradores` | `/borradores/` |
| `@user_passes_test` | `posts/views.py` → `panel_editores`, `es_editor` | `/panel-editores/` |
| Permiso propio (`Meta.permissions`) | `posts/models.py` (`puede_publicar`), `posts/forms.py` (`PostForm.clean_estado`) | publicar desde `/nuevo/` |
| Permisos por objeto (guardian) | `posts/views.py` → `compartir_post`, `quitar_colaborador`, `mis_posts`; `posts/forms.py` → `CompartirForm` | `/<slug>/compartir/`, `/mis-posts/` |
| La regla que une todo | `posts/views.py` → `puede_modificar` | — |
| Configuración de guardian | `config/settings.py` (`INSTALLED_APPS`, `AUTHENTICATION_BACKENDS`) | — |
| Tests | `posts/test_proteccion.py` | — |

## Demos sugeridas

1. **Mismo resultado, dos estilos.** `/<slug>/editar/` (función) y `/<slug>/cbv-editar/` (clase): entrar como `beto` al post de `ana` en ambas.
2. **Redirección o 403.** `/borradores/` como visitante (login), como `ana` (403), como `carla` (200). Después `/panel-editores/` como `ana`: *redirige al login aunque ya esté logueada* (así se comporta `@user_passes_test`).
3. **Permiso propio.** Como `ana`, crear un post con estado "Publicado": error. Como `dani`: se publica. En `/admin/`, dar `puede_publicar` a otro usuario o grupo.
4. **Permiso por objeto.** Como `ana`, ir a un post suyo → Compartir → `beto`. Como `beto`, `/mis-posts/` muestra el post en "Compartidos conmigo" y puede editarlo; los demás posts de `ana` siguen dando 403. Quitar el permiso y repetir.
5. **Global frente a objeto.** En el shell: `carla.has_perm("posts.change_post")` es `True`, pero `carla.has_perm("posts.change_post", post)` es `False`. Por eso `puede_modificar` pregunta por los dos.

## Cosas que conviene saber (salieron al probar el proyecto)

- **Orden de los mixins.** Van antes de la vista genérica (`class X(LoginRequiredMixin, UpdateView)`). Al revés, no protegen y Django no avisa.
- **`raise_exception=True` en el decorador.** Le da 403 también al visitante sin sesión. Por eso `borradores` apila `@login_required` arriba: visitante → login, logueado sin permiso → 403.
- **`@user_passes_test` no ve el objeto.** Solo recibe al usuario. Para "es dueño de este post" hay que usar `UserPassesTestMixin` o chequear dentro de la vista.
- **Varios backends y `login()`.** Con `ModelBackend` + guardian, `login(request, user)` después de `form.save()` falla con `ValueError ... multiple authentication backends`. Hay que pasar `backend="django.contrib.auth.backends.ModelBackend"` (ver `cuentas/views.py`).
- **Usuario `AnonymousUser`.** Guardian crea un usuario con ese nombre en la base. El formulario de compartir lo rechaza y no se puede registrar ese nombre.
- **`accept_global_perms=False`.** En `mis_posts`, sin eso los Editores verían todos los posts como "compartidos conmigo".
- **Caché de permisos.** Si das un permiso en el shell y consultás con el mismo objeto `User`, no lo ve: volvé a cargar el usuario.
- **Si venís de una base anterior**, borrá `db.sqlite3` y las migraciones de `posts/` y `cuentas/` antes de `makemigrations` (cambió `Post.autor` y hay permisos nuevos).

## Despliegue en Heroku

El proyecto ya trae lo que Heroku necesita: `Procfile` (Gunicorn y fase de *release*), `.python-version` (Python 3.13), `requirements.txt` con versiones fijas, `app.json` y una `config/settings.py` que lee su configuración de variables de entorno. Sin variables, todo sigue funcionando en local como antes (SQLite, `DEBUG` activado).

Heroku es de pago: revisá el costo del dyno y de la base Postgres antes de crear la app.

### Pasos

    git init && git add . && git commit -m "Blog listo para Heroku"
    heroku login
    heroku create nombre-de-tu-app
    heroku addons:create heroku-postgresql          # planes: heroku addons:plans heroku-postgresql
    heroku config:set DEBUG=0 SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(60))')"
    git push heroku main                            # o master, según el nombre de tu rama
    heroku run python manage.py createsuperuser     # para entrar a /admin/
    heroku open

Opcional, para tener usuarios de prueba (si la app queda pública, cambiá antes la contraseña):

    heroku config:set DEMO_PASSWORD="una-clave-tuya"
    heroku run python manage.py cargar_demo_auth

### Variables de entorno

| Variable | Obligatoria | Para qué sirve |
|---|---|---|
| `SECRET_KEY` | Sí | Clave secreta de Django. Sin ella el deploy se corta (ver abajo). |
| `DEBUG` | Sí, con `0` | Desactiva el modo desarrollo. Por defecto vale `1`. |
| `DATABASE_URL` | La pone Heroku | Heroku Postgres la define al agregar el add-on. Sin ella usa SQLite. |
| `ALLOWED_HOSTS` | No | Lista separada por comas. Por defecto acepta local y `.herokuapp.com`. |
| `CSRF_TRUSTED_ORIGINS` | No | Solo si usás un dominio propio con HTTPS (ej. `https://miblog.com`). |
| `DEMO_PASSWORD` | No | Contraseña de los usuarios de `cargar_demo_auth`. |
| `LOG_LEVEL` | No | Nivel de logs de Django en producción (por defecto `WARNING`). |

### Cosas que conviene saber

- **El release se corta a propósito.** Antes de cada deploy, Heroku corre `check --deploy` y `migrate` (ver `Procfile`). Si falta `SECRET_KEY` o `DEBUG` sigue en `1`, el release falla y la versión nueva no se publica. Los logs dicen por qué: `heroku logs --tail`.
- **Mails por consola.** La recuperación de contraseña imprime el mail en los logs (`heroku logs --tail`), no lo envía. Para enviar mails reales hay que configurar SMTP y quitar `mail.E001` de `SILENCED_SYSTEM_CHECKS` en `settings.py`.
- **Archivos estáticos.** Los sirve WhiteNoise; Heroku corre `collectstatic` solo al construir la app.
- **Tests.** Correlos con `DEBUG` por defecto (`python manage.py test`). Con `DEBUG=0` Django redirige todo a HTTPS y los tests fallan.
- **Disco efímero.** Este proyecto no sube archivos, así que no hay problema. Si más adelante agregás imágenes o adjuntos, no los guardes en el disco de Heroku: se pierden en cada deploy (usá S3 o similar).
- **Postgres en local (opcional).** `DATABASE_URL=postgresql://usuario:clave@localhost/blog python manage.py test` prueba el proyecto contra Postgres, igual que en Heroku.

