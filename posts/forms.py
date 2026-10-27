from django import forms
from django.contrib.auth import get_user_model
from guardian.conf import settings as guardian_settings

from .models import Post


class PostForm(forms.ModelForm):
    """ModelForm: crear y editar posts. El mismo formulario sirve para las dos cosas."""

    class Meta:
        model = Post
        fields = ["titulo", "contenido", "estado"]  # autor y likes ya no se escriben a mano
        labels = {
            "titulo": "Título del post",
            "contenido": "Contenido",
            "estado": "Estado de publicación",
        }
        widgets = {
            "titulo": forms.TextInput(attrs={"placeholder": "Escribí el título del post"}),
            "contenido": forms.Textarea(attrs={"rows": 6, "placeholder": "Escribí el contenido"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        # La vista le pasa el usuario para poder preguntar por sus permisos.
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_estado(self):
        estado = self.cleaned_data["estado"]
        # Solo se bloquea el cambio A "publicado": si el post ya estaba publicado y no se toca, pasa.
        publica_ahora = estado == "publicado" and estado != self.instance.estado
        if publica_ahora and not (self.user and self.user.has_perm("posts.puede_publicar")):
            raise forms.ValidationError("No tenés permiso para publicar. Guardalo como borrador.")
        return estado

    def clean_titulo(self):
        titulo = self.cleaned_data["titulo"].strip()
        if len(titulo) < 5:
            raise forms.ValidationError("El título debe tener al menos 5 caracteres.")
        return titulo  # siempre devolver el valor limpio


class BuscarForm(forms.Form):
    """forms.Form (sin modelo): reemplaza las opciones 3 y 4 del menú de consola.
    Se envía por GET porque solo lee datos, no los modifica."""

    q = forms.CharField(label="Título contiene", required=False)
    autor = forms.CharField(label="Autor (usuario)", required=False)


class ContactoForm(forms.Form):
    """forms.Form (sin modelo): no guarda nada en la base, solo valida y usa los datos."""

    nombre = forms.CharField(max_length=100, label="Tu nombre")
    correo = forms.EmailField(label="Tu correo electrónico")
    mensaje = forms.CharField(
        label="Mensaje",
        min_length=10,
        widget=forms.Textarea(attrs={"rows": 4}),
    )


class CompartirForm(forms.Form):
    """Para darle a otro usuario permiso de editar UN post (permiso por objeto, django-guardian)."""

    usuario = forms.CharField(label="Nombre de usuario con quien compartir")

    def __init__(self, *args, post=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.post = post

    def clean_usuario(self):
        username = self.cleaned_data["usuario"].strip()
        User = get_user_model()
        try:
            usuario = User.objects.get(username=username)
        except User.DoesNotExist:
            raise forms.ValidationError("No existe ese usuario.")
        if usuario.username == guardian_settings.ANONYMOUS_USER_NAME:
            raise forms.ValidationError("No existe ese usuario.")
        if usuario.id == self.post.autor_id:
            raise forms.ValidationError("Esa persona ya es la autora del post.")
        return usuario    # devuelve el objeto User, no el texto
