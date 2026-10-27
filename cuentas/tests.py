from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

User = get_user_model()
CLAVE = "clave-test-123"


class RegistroTests(TestCase):
    def datos(self, **extra):
        base = {"username": "nuevo", "email": "nuevo@ejemplo.com", "password1": CLAVE, "password2": CLAVE}
        base.update(extra)
        return base

    def test_registro_crea_usuario_perfil_y_abre_sesion(self):
        r = self.client.post(reverse("registro"), self.datos())
        self.assertRedirects(r, reverse("lista_posts"))
        u = User.objects.get(username="nuevo")
        self.assertNotEqual(u.password, CLAVE)       # guardada hasheada
        self.assertTrue(u.check_password(CLAVE))
        self.assertTrue(hasattr(u, "perfil"))         # la señal creó el Perfil
        self.assertEqual(int(self.client.session["_auth_user_id"]), u.id)  # ya está logueado

    def test_contrasenas_distintas(self):
        r = self.client.post(reverse("registro"), self.datos(password2="otra-clave-456"))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="nuevo").exists())

    def test_contrasena_comun_es_rechazada(self):
        r = self.client.post(reverse("registro"), self.datos(password1="12345678", password2="12345678"))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="nuevo").exists())

    def test_email_repetido(self):
        User.objects.create_user("otro", "nuevo@ejemplo.com", CLAVE)
        r = self.client.post(reverse("registro"), self.datos())
        self.assertContains(r, "Ya existe un usuario con ese correo")


class LoginLogoutTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("ana", "ana@ejemplo.com", CLAVE)

    def test_login_ok(self):
        r = self.client.post(reverse("login"), {"username": "ana", "password": CLAVE})
        self.assertRedirects(r, reverse("lista_posts"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_mal(self):
        r = self.client.post(reverse("login"), {"username": "ana", "password": "mala"})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_respeta_next(self):
        r = self.client.post(reverse("login") + "?next=/nuevo/", {"username": "ana", "password": CLAVE, "next": "/nuevo/"})
        self.assertRedirects(r, "/nuevo/")

    def test_logout_es_post(self):
        self.client.login(username="ana", password=CLAVE)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)  # GET no cierra sesión
        self.client.post(reverse("logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_menu_cambia_segun_sesion(self):
        self.assertContains(self.client.get(reverse("lista_posts")), "Ingresar")
        self.client.login(username="ana", password=CLAVE)
        r = self.client.get(reverse("lista_posts"))
        self.assertContains(r, "Hola, ")
        self.assertContains(r, "Salir")


class PerfilYPasswordTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("ana", "ana@ejemplo.com", CLAVE)

    def test_editar_perfil_requiere_login(self):
        url = reverse("editar_perfil")
        self.assertRedirects(self.client.get(url), f"{reverse('login')}?next={url}")

    def test_editar_perfil(self):
        self.client.login(username="ana", password=CLAVE)
        r = self.client.post(reverse("editar_perfil"), {
            "first_name": "Ana", "last_name": "Pérez", "email": "ana@ejemplo.com",
            "bio": "Hola, soy Ana", "sitio_web": "https://ana.dev",
        })
        self.assertRedirects(r, reverse("perfil_publico", args=["ana"]))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Ana")
        self.assertEqual(self.user.perfil.bio, "Hola, soy Ana")

    def test_perfil_publico(self):
        self.assertContains(self.client.get(reverse("perfil_publico", args=["ana"])), "@ana")
        self.assertEqual(self.client.get(reverse("perfil_publico", args=["nadie"])).status_code, 404)

    def test_cambiar_password(self):
        self.client.login(username="ana", password=CLAVE)
        r = self.client.post(reverse("password_change"), {
            "old_password": CLAVE, "new_password1": "otra-clave-789", "new_password2": "otra-clave-789"})
        self.assertRedirects(r, reverse("password_change_done"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("otra-clave-789"))

    def test_recuperar_password_envia_mail(self):
        r = self.client.post(reverse("password_reset"), {"email": "ana@ejemplo.com"})
        self.assertRedirects(r, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/cuentas/password/reset/", mail.outbox[0].body)
