from django.conf import settings
from django.db import models


class Perfil(models.Model):
    """Datos extra del usuario. El User de Django ya tiene username, email y password;
    lo demás va acá, enlazado 1 a 1."""

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil"
    )
    bio = models.TextField(blank=True)
    sitio_web = models.URLField(blank=True)

    def __str__(self):
        return f"Perfil de {self.usuario.username}"
