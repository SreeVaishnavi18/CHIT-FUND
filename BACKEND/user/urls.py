from django.urls import path
from .views import MyInvoicesView, UserMeView, UserChitsView, UserInvoicesView,login_user

urlpatterns = [
    path('me/', UserMeView.as_view(), name='user-me'),
    path('<str:user_id>/chits/', UserChitsView.as_view(), name='user-chits'),
    path('<str:user_id>/invoices/', UserInvoicesView.as_view(), name='user-invoices'),
    path('me/invoices/', MyInvoicesView.as_view(), name='me-invoices'),
    path('login/', login_user),


]
