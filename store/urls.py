from django.urls import path
from store import views

app_name = "store"

urlpatterns = [
    # Public storefront
    path("products/", views.product_list, name="product_list"),
    path("products/<slug:slug>/", views.product_detail, name="product_detail"),

    # Seller portal
    path("vendor/products/", views.vendor_product_list, name="vendor_product_list"),
    path("vendor/products/new/", views.vendor_product_create, name="vendor_product_create"),
    path("vendor/products/<int:pk>/edit/", views.vendor_product_edit, name="vendor_product_edit"),
    path("vendor/products/<int:pk>/submit/", views.vendor_product_submit, name="vendor_product_submit"),

    # Admin moderation
    path("admin/moderation/", views.admin_moderation_queue, name="admin_moderation_queue"),
    path("admin/moderation/<int:pk>/", views.admin_moderate_product, name="admin_moderate_product"),
]
