# auctions/urls.py
from django.urls import path
from .views import (
    ActiveAuctionsView,
    AuctionDetailView,
    AuctionWinnerView,
    InvoiceDetailView,
    MarkPaymentDoneView,
    StartAuctionView,
    CloseAuctionView,
    AuctionBidsView,
    SubmitBidView,
    MyBidView,
    UserInvoicesView,
    UserWinsView,
)

urlpatterns = [
    path('active/', ActiveAuctionsView.as_view(), name='active-auctions'),
    path('<str:auction_id>/', AuctionDetailView.as_view(), name='auction-detail'),
    path('chitgroups/<str:chit_id>/auctions/start/', StartAuctionView.as_view(), name='start-auction'),
    path('<str:auction_id>/close/', CloseAuctionView.as_view(), name='close-auction'),
    path('<str:auction_id>/bids/', AuctionBidsView.as_view(), name='auction-bids'),
    path('<str:auction_id>/bid/', SubmitBidView.as_view(), name='submit-bid'),
    path('<str:auction_id>/mybid/', MyBidView.as_view(), name='my-bid'),
    path('<str:auction_id>/winner/', AuctionWinnerView.as_view(), name='auction-winner'),
    path('winners/<str:user_id>/', UserWinsView.as_view(), name='user-winners'),
    path('invoices/<str:user_id>/', UserInvoicesView.as_view(), name='user-invoices'),
    path('invoices/detail/<str:invoice_id>/', InvoiceDetailView.as_view(), name='invoice-detail'),
    path('<str:auction_id>/mark-paid/', MarkPaymentDoneView.as_view()),
]
