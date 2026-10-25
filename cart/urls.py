from django.urls import path
from cart import views

app_name = "cart"

urlpatterns = [
    path("", views.cart_detail, name="detail"),
    path("add/<int:variant_id>/", views.cart_add, name="add"),
    path("update/<int:item_id>/", views.cart_update, name="update"),
    path("remove/<int:item_id>/", views.cart_remove, name="remove"),
    path("remove-demo/", views.cart_remove_demo, name="remove_demo"),
    path("clear/", views.cart_clear, name="clear"),
]
