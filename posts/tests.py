from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import resolve, reverse

from .forms import ContactoForm, PostForm
from .models import Post


User = get_user_model()


def datos(**extra):
    """Campos del modelo (para Post.objects.create). 'autor' se completa en cada test."""
    base = {"titulo": "Mi primer post", "contenido": "Hola mundo", "likes": 3, "estado": "publicado"}
    base.update(extra)
    return base


def datos_form(**extra):
    """Lo que envía el navegador: el autor NO viaja en el form, sale de request.user."""
    # Por defecto "borrador": publicar desde el formulario exige el permiso posts.puede_publicar.
    base = {"titulo": "Mi primer post", "contenido": "Hola mundo", "estado": "borrador"}
    base.update(extra)
    return base


class AuthTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ana = User.objects.create_user("ana", password="clave-test-123")
        cls.beto = User.objects.create_user("beto", password="clave-test-123")

    def crear(self, **extra):
        extra.setdefault("autor", self.ana)
        return Post.objects.create(**datos(**extra))

    def entrar(self, user="ana"):
        self.client.login(username=user, password="clave-test-123")


class FormTests(TestCase):
    def test_form_unbound_y_bound(self):
        self.assertFalse(PostForm().is_bound)
        self.assertTrue(PostForm(datos_form()).is_bound)

    def test_titulo_corto_es_invalido(self):
        form = PostForm(datos_form(titulo="Hola"))
        self.assertFalse(form.is_valid())
        self.assertIn("titulo", form.errors)

    def test_campos_obligatorios(self):
        form = PostForm({})
        self.assertFalse(form.is_valid())
        for campo in ("titulo", "contenido", "estado"):
            self.assertIn(campo, form.errors)

    def test_likes_no_se_editan_a_mano(self):
        self.assertNotIn("likes", PostForm().fields)

    def test_fecha_slug_y_autor_no_estan_en_el_form(self):
        self.assertNotIn("autor", PostForm().fields)  # el autor lo pone la vista
        self.assertNotIn("fecha_creacion", PostForm().fields)
        self.assertNotIn("slug", PostForm().fields)

    def test_contacto_form(self):
        ok = ContactoForm({"nombre": "Ana", "correo": "ana@x.com", "mensaje": "Mensaje largo ok"})
        self.assertTrue(ok.is_valid())
        self.assertEqual(ok.cleaned_data["nombre"], "Ana")
        mal = ContactoForm({"nombre": "Ana", "correo": "hola", "mensaje": "corto"})
        self.assertFalse(mal.is_valid())
        self.assertIn("correo", mal.errors)
        self.assertIn("mensaje", mal.errors)


class SlugTests(AuthTestCase):
    def test_slug_automatico_sin_acentos(self):
        p = self.crear(titulo="Cómo configurar VS Code")
        self.assertEqual(p.slug, "como-configurar-vs-code")

    def test_titulos_repetidos_no_rompen(self):
        a = self.crear(titulo="Hola mundo")
        b = self.crear(titulo="Hola mundo")
        self.assertEqual((a.slug, b.slug), ("hola-mundo", "hola-mundo-2"))

    def test_slug_no_cambia_al_editar_titulo(self):
        p = self.crear()
        slug = p.slug
        p.titulo = "Otro título distinto"
        p.save()
        self.assertEqual(p.slug, slug)


class UrlTests(TestCase):
    def test_reverse_y_resolve(self):
        self.assertEqual(reverse("lista_posts"), "/")
        self.assertEqual(reverse("detalle_post", args=["x"]), "/x/")
        self.assertEqual(reverse("login"), "/cuentas/login/")
        self.assertEqual(resolve("/nuevo/").func.__name__, "crear_post")
        m = resolve("/mi-post/")
        self.assertEqual((m.func.__name__, m.kwargs), ("detalle_post", {"slug": "mi-post"}))
        self.assertEqual(resolve("/mi-post/editar/").func.__name__, "editar_post")


class CrudViewTests(AuthTestCase):
    def test_crear_get_y_post(self):
        self.entrar()
        self.assertEqual(self.client.get(reverse("crear_post")).status_code, 200)
        r = self.client.post(reverse("crear_post"), datos_form())
        post = Post.objects.get()
        self.assertRedirects(r, reverse("detalle_post", args=[post.slug]))
        self.assertEqual(post.autor, self.ana)  # el autor sale de la sesión

    def test_crear_invalido_muestra_errores_y_no_guarda(self):
        self.entrar()
        r = self.client.post(reverse("crear_post"), datos_form(titulo="abc"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "al menos 5 caracteres")
        self.assertEqual(Post.objects.count(), 0)

    def test_csrf_se_exige(self):
        from django.test import Client
        c = Client(enforce_csrf_checks=True)
        c.login(username="ana", password="clave-test-123")
        self.assertEqual(c.post(reverse("crear_post"), datos_form()).status_code, 403)

    def test_editar_actualiza_el_mismo_post(self):
        p = self.crear()
        self.entrar()
        url = reverse("editar_post", args=[p.slug])
        self.assertContains(self.client.get(url), "Mi primer post")  # precargado
        r = self.client.post(url, datos_form(titulo="Título editado"))
        self.assertRedirects(r, reverse("detalle_post", args=[p.slug]))
        self.assertEqual(Post.objects.count(), 1)
        p.refresh_from_db()
        self.assertEqual(p.titulo, "Título editado")
        self.assertEqual(p.autor, self.ana)  # editar no cambia el autor

    def test_eliminar_requiere_post(self):
        p = self.crear()
        self.entrar()
        url = reverse("eliminar_post", args=[p.slug])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(Post.objects.count(), 1)  # GET no borra
        self.assertRedirects(self.client.post(url), reverse("lista_posts"))
        self.assertEqual(Post.objects.count(), 0)

    def test_detalle_404(self):
        self.assertEqual(self.client.get("/no-existe/").status_code, 404)

    def test_busqueda_por_get(self):
        self.crear(titulo="Django para todos", autor=self.ana)
        self.crear(titulo="Python básico", autor=self.beto)
        r = self.client.get(reverse("lista_posts"), {"q": "django"})
        self.assertContains(r, "Django para todos")
        self.assertNotContains(r, "Python básico")
        r = self.client.get(reverse("lista_posts"), {"autor": "BETO"})
        self.assertContains(r, "Python básico")
        self.assertNotContains(r, "Django para todos")

    def test_estadisticas(self):
        self.assertContains(self.client.get(reverse("estadisticas")), "Todavía no hay posts")
        self.crear(titulo="Post uno", likes=2)
        self.crear(titulo="Post dos", likes=6)
        r = self.client.get(reverse("estadisticas"))
        self.assertContains(r, "Post dos")
        self.assertContains(r, "4,0")  # es-ar usa coma decimal

    def test_contacto(self):
        r = self.client.post(reverse("contacto"), {"nombre": "Ana", "correo": "a@b.com", "mensaje": "Mensaje largo ok"})
        self.assertContains(r, "Gracias por contactarte, Ana")


class AutorizacionTests(AuthTestCase):
    """Autenticación = quién sos. Autorización = qué podés hacer."""

    def test_anonimo_es_redirigido_al_login_con_next(self):
        for nombre, args in [("crear_post", []), ("mis_posts", [])]:
            url = reverse(nombre, args=args)
            self.assertRedirects(self.client.get(url), f"{reverse('login')}?next={url}")

    def test_anonimo_no_puede_editar_ni_eliminar(self):
        p = self.crear()
        for nombre in ("editar_post", "eliminar_post"):
            url = reverse(nombre, args=[p.slug])
            self.assertRedirects(self.client.get(url), f"{reverse('login')}?next={url}")
        self.assertRedirects(self.client.post(reverse("eliminar_post", args=[p.slug])),
                             f"{reverse('login')}?next={reverse('eliminar_post', args=[p.slug])}")
        self.assertEqual(Post.objects.count(), 1)

    def test_otro_usuario_recibe_403(self):
        p = self.crear(autor=self.ana)
        self.entrar("beto")
        self.assertEqual(self.client.get(reverse("editar_post", args=[p.slug])).status_code, 403)
        self.assertEqual(self.client.post(reverse("editar_post", args=[p.slug]), datos_form(titulo="Hackeado!")).status_code, 403)
        self.assertEqual(self.client.post(reverse("eliminar_post", args=[p.slug])).status_code, 403)
        p.refresh_from_db()
        self.assertEqual(p.titulo, "Mi primer post")

    def test_el_autor_si_puede(self):
        p = self.crear(autor=self.ana)
        self.entrar("ana")
        self.assertEqual(self.client.get(reverse("editar_post", args=[p.slug])).status_code, 200)

    def test_permiso_de_grupo_editores(self):
        from django.contrib.auth.models import Group, Permission
        g = Group.objects.create(name="Editores")
        g.permissions.add(Permission.objects.get(codename="change_post"),
                          Permission.objects.get(codename="delete_post"))
        self.beto.groups.add(g)
        p = self.crear(autor=self.ana)
        self.entrar("beto")
        self.assertEqual(self.client.get(reverse("editar_post", args=[p.slug])).status_code, 200)

    def test_botones_solo_para_quien_puede(self):
        p = self.crear(autor=self.ana)
        url = reverse("detalle_post", args=[p.slug])
        self.assertNotContains(self.client.get(url), "mi-primer-post/editar/")  # anónimo
        self.entrar("beto")
        self.assertNotContains(self.client.get(url), "mi-primer-post/editar/")  # logueado pero ajeno
        self.client.logout()
        self.entrar("ana")
        self.assertContains(self.client.get(url), "mi-primer-post/editar/")     # dueña

    def test_mis_posts_solo_muestra_los_propios(self):
        self.crear(titulo="De Ana", autor=self.ana)
        self.crear(titulo="De Beto", autor=self.beto)
        self.entrar("ana")
        r = self.client.get(reverse("mis_posts"))
        self.assertContains(r, "De Ana")
        self.assertNotContains(r, "De Beto")
