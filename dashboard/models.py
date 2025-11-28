from django.db import models
from authentication.models import BaseModel



class TermsCondition(BaseModel):
    title = models.CharField(max_length=100)
    content = models.TextField()

    class Meta:
        verbose_name = "Terms & Condition"
        verbose_name_plural = "Terms & Conditions"

    def __str__(self):
        return self.title

class ContactUs(BaseModel):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    content = models.TextField()

    class Meta:
        verbose_name = "Contact Us"
        verbose_name_plural = "Contact Us"

    def __str__(self):
        return f"{self.name} - {self.email}"
