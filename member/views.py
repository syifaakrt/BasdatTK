from django.shortcuts import render
from rewards.views import staff_nav_items, member_nav_items


def kelola_member(request):
    nav_items=staff_nav_items()
    return render(request,'member/kelola_member.html',{"nav_items":nav_items, "role":"staff"})

def identitas(request):
    nav_items=member_nav_items()
    return render(request, 'member/identitas.html', {"nav_items":nav_items, "role":"member"})