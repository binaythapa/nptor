from django.urls import path
from store import views

app_name = "store"

urlpatterns = [
    # Public storefront
    path("products/", views.product_list, name="product_list"),
    path("products/<slug:slug>/", views.product_detail, name="product_detail"),
    path("products/<slug:slug>/review/", views.submit_product_review, name="submit_product_review"),
    path("reviews/<int:review_id>/vote/", views.vote_review_helpful, name="vote_review_helpful"),
    path("reviews/<int:review_id>/report/", views.report_product_review, name="report_product_review"),
    path("wishlist/", views.wishlist_view, name="wishlist_view"),
    path("wishlist/toggle/<int:product_id>/", views.wishlist_toggle, name="wishlist_toggle"),

    # Seller portal
    path("vendor/products/", views.vendor_product_list, name="vendor_product_list"),
    path("vendor/products/new/", views.vendor_product_create, name="vendor_product_create"),
    path("vendor/products/<int:pk>/edit/", views.vendor_product_edit, name="vendor_product_edit"),
    path("vendor/products/<int:pk>/submit/", views.vendor_product_submit, name="vendor_product_submit"),

    # Admin moderation
    path("admin/moderation/", views.admin_moderation_queue, name="admin_moderation_queue"),
    path("admin/moderation/<int:pk>/", views.admin_moderate_product, name="admin_moderate_product"),
]
