from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

app_name = "rewards"

urlpatterns = [
    # Pages
    path("guest/", views.guest_home, name="guest_home"),
    path("member/redeem-hadiah/", views.member_redeem_hadiah, name="member_redeem_hadiah"),
    path("member/beli-package/", views.member_beli_package, name="member_beli_package"),
    path("member/info-tier/", views.member_info_tier, name="member_info_tier"),
    path("staf/laporan-transaksi/", views.staff_laporan_transaksi, name="staff_laporan_transaksi"),
    path("staf/kelola-mitra", views.kelola_mitra, name='kelola_mitra'),
    path("staf/kelola-hadiah", views.kelola_hadiah, name='kelola_hadiah'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),

    # API Hadiah
    path("api/hadiah/", views.api_hadiah_list, name="api_hadiah_list"),
    path("api/hadiah/create/", views.api_hadiah_create, name="api_hadiah_create"),
    path("api/hadiah/update/<str:kode>/", views.api_hadiah_update, name="api_hadiah_update"),
    path("api/hadiah/delete/<str:kode>/", views.api_hadiah_delete, name="api_hadiah_delete"),

    # API Mitra
    path("api/mitra/", views.api_mitra_list, name="api_mitra_list"),
    path("api/mitra/create/", views.api_mitra_create, name="api_mitra_create"),
    path("api/mitra/update/<str:email>/", views.api_mitra_update, name="api_mitra_update"),
    path("api/mitra/delete/<str:email>/", views.api_mitra_delete, name="api_mitra_delete"),
]

