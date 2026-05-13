from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main.urls')),
    path('rewards/', include('rewards.urls')),
    path('miles/', include('miles.urls')),
    path('manage/', include('member.urls'))
]
