import os

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from posts.models import Post

User = get_user_model()

# Se puede cambiar con la variable DEMO_PASSWORD (útil si la app queda pública, por ejemplo en Heroku).
CLAVE_DEMO = os.environ.get("DEMO_PASSWORD", "clave-demo-123")


class Command(BaseCommand):
    help = "Crea usuarios demo (ana, beto, carla, dani), los grupos Editores y Publicadores y algunos posts."

    def handle(self, *args, **options):
        # Editores: pueden editar/eliminar posts ajenos (permisos globales change/delete).
        editores, _ = Group.objects.get_or_create(name="Editores")
        editores.permissions.set(
            Permission.objects.filter(content_type__app_label="posts",
                                      codename__in=["change_post", "delete_post"])
        )
        # Publicadores: tienen el permiso propio del Meta del modelo.
        publicadores, _ = Group.objects.get_or_create(name="Publicadores")
        publicadores.permissions.set(
            Permission.objects.filter(content_type__app_label="posts", codename="puede_publicar")
        )

        usuarios = {}
        for nombre in ("ana", "beto", "carla", "dani"):
            user, creado = User.objects.get_or_create(username=nombre, defaults={"email": f"{nombre}@ejemplo.com"})
            if creado:
                user.set_password(CLAVE_DEMO)  # set_password hashea; nunca guardar texto plano
                user.save()
            usuarios[nombre] = user
        usuarios["carla"].groups.add(editores)
        usuarios["dani"].groups.add(publicadores)

        if not Post.objects.exists():
            # Por el ORM se puede crear con cualquier estado; por el formulario, publicar exige el permiso.
            Post.objects.create(titulo="Hola desde Ana", contenido="Primer post de Ana.",
                                autor=usuarios["ana"], estado="publicado", likes=5)
            Post.objects.create(titulo="Mi post borrador", contenido="Beto escribe.",
                                autor=usuarios["beto"], estado="borrador")
        self.stdout.write(self.style.SUCCESS(
            "Listo. ana y beto: autores comunes. carla: Editores. dani: Publicadores. "
            + ("Contraseña de todos: clave-demo-123" if CLAVE_DEMO == "clave-demo-123"
               else "Contraseña de todos: la de DEMO_PASSWORD")))
