from django.urls import path
from . import views

app_name="miles"

urlpatterns = [
    # Fitur 8 - Claim Missing Miles (Member)
    path('klaim/', views.claim_list, name='claim_list'),
    path('klaim/ajukan/', views.claim_create, name='claim_create'),
    path('klaim/edit/<int:id>/', views.claim_edit, name='claim_edit'),
    path('klaim/batal/<int:id>/', views.claim_delete, name='claim_delete'),

    # Fitur 9 - Claim Missing Miles (Staf)
    path('staf/klaim/', views.staf_claim_list, name='staf_claim_list'),
    path('staf/klaim/proses/<int:id>/', views.staf_claim_update, name='staf_claim_update'),

    # Fitur 10 - Transfer Miles (Member)
    path('transfer/', views.transfer_list, name='transfer_list'),
    path('transfer/kirim/', views.transfer_create, name='transfer_create'),

]