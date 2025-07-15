from django.urls import path
from .views import create_chit_group,join_chit_group,list_chit_groups,list_available_groups

urlpatterns = [
    path('chit-groups/create/', create_chit_group),
    path('chit-groups/join/', join_chit_group),
    path('chit-groups/', list_chit_groups),
    path('chit-groups/available/<str:username>/', list_available_groups),


]
