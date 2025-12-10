# models.py
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Vendor(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class VendorItem(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="items")
    item_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.vendor.name} - {self.item_name}"


class Record(models.Model):
    date = models.DateField()
    location = models.CharField(max_length=100)

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


# --- Manager profile (link user -> location) ---
class ManagerProfile(models.Model):
    LOCATION_CHOICES = [
        ('Dulari', 'Dulari'),
        ('Pours and Plates', 'Pours and Plates'),
        ('Rachels', 'Rachels'),
        ('Rachels1', 'Rachels1'),
        ('Rachels2', 'Rachels2'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='managerprofile')
    # only meaningful for manager accounts (admin will not have a managerprofile by default)
    location = models.CharField(max_length=64, choices=LOCATION_CHOICES, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} — {self.location or '(no location)'}"


# Create ManagerProfile automatically when a User is created (so templates can safely reference)
@receiver(post_save, sender=User)
def ensure_manager_profile(sender, instance, created, **kwargs):
    if created:
        ManagerProfile.objects.create(user=instance)
