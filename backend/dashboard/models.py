from django.contrib.auth.models import AbstractUser
from django.db import models

class Hospital(models.Model):
    nome = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nome


class AirCentral(models.Model):
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)


class OxygenCentral(models.Model):
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)


class CustomUser(AbstractUser):
    hospital = models.ForeignKey(
        Hospital, on_delete=models.SET_NULL, null=True, blank=True
    )
