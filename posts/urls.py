from django.urls import path

from . import views, views_cbv

# De lo más específico a lo más general: <slug:slug>/ captura casi cualquier cosa.
urlpatterns = [
    path("", views.lista_posts, name="lista_posts"),
    path("nuevo/", views.crear_post, name="crear_post"),
    path("mis-posts/", views.mis_posts, name="mis_posts"),
    path("estadisticas/", views.estadisticas, name="estadisticas"),
    # Protecciones: decoradores
    path("borradores/", views.borradores, name="borradores"),
    path("panel-editores/", views.panel_editores, name="panel_editores"),
    # Protecciones: vistas con clases (mixins)
    path("cbv/nuevo/", views_cbv.PostCreateView.as_view(), name="cbv_crear_post"),
    path("cbv/borradores/", views_cbv.BorradoresCbvView.as_view(), name="cbv_borradores"),
    path("<slug:slug>/cbv-editar/", views_cbv.PostUpdateView.as_view(), name="cbv_editar_post"),
    path("<slug:slug>/cbv-eliminar/", views_cbv.PostDeleteView.as_view(), name="cbv_eliminar_post"),
    # Permisos por objeto (guardian)
    path("<slug:slug>/compartir/", views.compartir_post, name="compartir_post"),
    path("<slug:slug>/compartir/quitar/<str:username>/", views.quitar_colaborador, name="quitar_colaborador"),
    path("contacto/", views.contacto, name="contacto"),
    path("<slug:slug>/editar/", views.editar_post, name="editar_post"),
    path("<slug:slug>/eliminar/", views.eliminar_post, name="eliminar_post"),
    path("<slug:slug>/", views.detalle_post, name="detalle_post"),
]
