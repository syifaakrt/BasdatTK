from django.urls import path
from .views import *

urlpatterns=[
    path("", dashboard),
    path('login/',   login_view,  name='login'),
    path('logout/',  logout_view, name='logout'),
    path('register/', register_view, name='register'),
    path("dashboard/", dashboard, name='dashboard'),
    path('profile/', pengaturan_profile, name='pengaturan_profile'),
    path('profile/update/', update_profile, name='update_profile'),
    path('profile/password/', update_password, name='update_password'),


]