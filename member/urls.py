from django.urls import path
from member.views import *

app_name = 'member'

urlpatterns = [
    #path('', show_main, name='show_main'),
    #path('login', login)
    path('kelola/', kelola_member, name='kelola_member'),
    path('identitas/', identitas, name='identitas')
]