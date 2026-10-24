from django.urls import path
from orders import views, views_checkout, views_digital, views_payment

app_name = "orders"

urlpatterns = [
    # Customer flows
    path("checkout/", views_checkout.checkout_view, name="checkout"),
    path("my-orders/", views.customer_order_list, name="customer_order_list"),
    path("my-orders/<str:order_number>/", views.customer_order_detail, name="customer_order_detail"),
    path("suborders/<str:suborder_number>/return/", views.customer_return_request, name="customer_return_request"),
    path("my-orders/<str:order_number>/pay/", views_payment.initiate_online_payment, name="initiate_online_payment"),
    path("my-orders/<str:order_number>/payment-callback/", views_payment.payment_callback, name="payment_callback"),
    path("downloads/<str:download_token>/", views_digital.download_digital_asset, name="download_digital_asset"),

    # Seller fulfillment
    path("vendor-suborders/", views.vendor_suborder_list, name="vendor_suborder_list"),
    path("vendor-suborders/<str:suborder_number>/", views.vendor_suborder_detail, name="vendor_suborder_detail"),

    # Staff order overview
    path("admin/all/", views.admin_order_list, name="admin_order_list"),
]
