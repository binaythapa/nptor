from django.urls import path
from vendors import views, views_settlement

app_name = "vendors"

urlpatterns = [
    path("onboard/", views.vendor_onboarding, name="onboarding"),
    path("dashboard/", views.vendor_dashboard, name="dashboard"),
    path("admin/queue/", views.admin_vendor_queue, name="admin_queue"),
    path("admin/<int:pk>/action/", views.admin_vendor_action, name="admin_action"),
    path("admin/settlement/", views_settlement.admin_settlement_dashboard, name="admin_settlement_dashboard"),
    path("admin/settlement/vendor/<int:vendor_id>/ledger/", views_settlement.admin_vendor_ledger_view, name="admin_vendor_ledger"),
    path("admin/settlement/payouts/", views_settlement.admin_payout_queue, name="admin_payout_queue"),
    path("admin/settlement/payouts/<int:payout_id>/action/", views_settlement.admin_payout_action, name="admin_payout_action"),
]
