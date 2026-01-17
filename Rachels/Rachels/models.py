# models.py
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

class Store(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Vendor(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class VendorItem(models.Model):
    UNIT_CHOICES = [
        ("kg", "Kilogram"),
        ("g", "Gram"),
        ("l", "Litre"),
        ("ml", "Millilitre"),
        ("pcs", "Pieces"),
        ("carton", "Carton"),
        ("packet", "Packet"),
    ]

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="items")
    item_name = models.CharField(max_length=100)

    unit = models.CharField(
        max_length=20,
        choices=UNIT_CHOICES,
        default="kg"
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def __str__(self):
        return f"{self.vendor.name} - {self.item_name} ({self.unit} @ {self.unit_price})"

class Record(models.Model):
    date = models.DateField()
    location = models.ForeignKey(
        Store,
        on_delete=models.PROTECT,
        related_name="records"
    )
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True)
    item = models.ForeignKey(VendorItem, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=1)

    status = models.CharField(max_length=20, default="Pending")

    def __str__(self):
        return f"{self.vendor} - {self.item} ({self.quantity})"

class AdvanceSalary(models.Model):
    employee_name = models.CharField("Name", max_length=200)
    paid_on = models.DateField("Date")
    amount = models.DecimalField("Amount", max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["-paid_on", "-id"]

    def __str__(self):
        return f"{self.employee_name} — {self.amount} on {self.paid_on}"

class ManagerProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='managerprofile'
    )
    store = models.ForeignKey(
        Store,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managers'
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        if self.store:
            return f"{self.user.username} — {self.store.name}"
        return f"{self.user.username} — (no store)"

@receiver(post_save, sender=User)
def ensure_manager_profile(sender, instance, created, **kwargs):
    if created:
        ManagerProfile.objects.create(user=instance)

User = settings.AUTH_USER_MODEL

class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    message = models.CharField(max_length=255)
    location = models.CharField(max_length=100, blank=True)  # REQUIRED
    url = models.CharField(max_length=255, blank=True)       # REQUIRED
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

