from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, reverse_lazy

from users import views as user_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("register/", user_views.register, name="register"),
    path("profile/", user_views.profile, name="profile"),
    path("invite/", user_views.invite_user, name="invite-user"),
    path("login/", auth_views.LoginView.as_view(template_name="users/login.html"), name="login"),
    path("logout/", user_views.custom_logout, name="logout"),
    path(
        "password-change/",
        auth_views.PasswordChangeView.as_view(
            template_name="users/password_change.html",
            success_url=reverse_lazy("profile"),
        ),
        name="password_change",
    ),
    path("api/", include("blog.api.api_urls")),
    path("", include("blog.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)