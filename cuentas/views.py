from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from django.contrib.auth import get_user_model

from .forms import PerfilForm, RegistroForm, UsuarioForm

User = get_user_model()


def registro(request):
    if request.user.is_authenticated:
        return redirect("lista_posts")
    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()   # crea el usuario con la contraseña hasheada
            # Con más de un backend configurado (ModelBackend + guardian), login() necesita saber
            # con cuál se autenticó el usuario; si no, lanza ValueError.
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, f"¡Bienvenido, {user.username}!")
            return redirect("lista_posts")
    else:
        form = RegistroForm()
    return render(request, "cuentas/registro.html", {"form": form})


def perfil_publico(request, username):
    usuario = get_object_or_404(User, username=username)
    posts = usuario.posts.filter(estado="publicado")
    return render(request, "cuentas/perfil_publico.html", {"usuario": usuario, "posts": posts})


@login_required
def editar_perfil(request):
    if request.method == "POST":
        user_form = UsuarioForm(request.POST, instance=request.user)
        perfil_form = PerfilForm(request.POST, instance=request.user.perfil)
        if user_form.is_valid() and perfil_form.is_valid():
            user_form.save()
            perfil_form.save()
            messages.success(request, "Perfil actualizado.")
            return redirect("perfil_publico", username=request.user.username)
    else:
        user_form = UsuarioForm(instance=request.user)
        perfil_form = PerfilForm(instance=request.user.perfil)
    return render(request, "cuentas/editar_perfil.html", {
        "user_form": user_form, "perfil_form": perfil_form,
    })
