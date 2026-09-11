from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Notification
from accounts.services.notifications import create_notification, mark_notification_read


class NotificationServiceTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="alice", email="alice@example.com", password="test-password")
        self.other = User.objects.create_user(username="bob", email="bob@example.com", password="test-password")

    def test_create_notification_is_unread_for_recipient(self):
        notification = create_notification(self.user, "organization", "Access approved", "Your access is active.", priority="success", target_url="/org/demo-school/")
        self.assertTrue(notification.is_unread_for(self.user))
        self.assertFalse(notification.is_visible_to(self.other))
        self.assertEqual(notification.target_url, "/org/demo-school/")

    def test_mark_read_is_idempotent(self):
        notification = create_notification(self.user, "system", "Hello", "World")
        mark_notification_read(notification)
        notification.refresh_from_db()
        self.assertFalse(notification.is_unread_for(self.user))
        mark_notification_read(notification)
        self.assertFalse(notification.is_unread_for(self.user))

    def test_notification_center_is_recipient_isolated(self):
        Notification.objects.create(title="Hidden", message="Nope").recipients.add(self.other)
        self.client.force_login(self.user)
        response = self.client.get(reverse("accounts:notifications"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Hidden")
