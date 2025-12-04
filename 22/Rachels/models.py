from django.db import models

class Record(models.Model):
    date = models.DateField()
    location = models.CharField(max_length=200)
    details = models.TextField()
    status = models.CharField(max_length=50, default="Pending")

    def __str__(self):
        # Show location + date; this avoids using a non-existent 'name' field.
        return f"{self.location} — {self.date}"