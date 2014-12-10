from django.db import models


class CronLog(models.Model):
    job = models.CharField(max_length=100)
    stdout = models.TextField(blank=True)
    stderr = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)
    exc_type = models.CharField(max_length=200, null=True, blank=True)
    exc_value = models.TextField(null=True, blank=True)
    exc_traceback = models.TextField(null=True, blank=True)
    duration = models.DecimalField(null=True, max_digits=10, decimal_places=3)
