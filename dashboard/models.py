from django.db import models
from django.utils import timezone
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
    subject = models.CharField(max_length=100,blank=True,null=True)
    reply = models.TextField(blank=True, null=True)
    is_replied = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Contact Us"
        verbose_name_plural = "Contact Us"

    def __str__(self):
        return f"{self.name} - {self.email}"



class CustomAd(BaseModel):
    AD_TYPE_CHOICES = [
        ('banner', 'Banner'),
        ('sidebar', 'Sidebar'),
        ('popup', 'Popup'),
        ('video', 'Video'),
        ('custom', 'Custom'),
    ]
    title = models.CharField(max_length=255, verbose_name="Ad Title")
    image = models.ImageField(upload_to='ads/', blank=True, null=True, verbose_name="Ad Image")
    description = models.TextField(blank=True, null=True, verbose_name="Ad Description")
    target_url = models.URLField(max_length=500, blank=True, null=True, verbose_name="Target URL")
    ad_type = models.CharField(max_length=32, choices=AD_TYPE_CHOICES, default='banner', verbose_name="Ad Type")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    start_date = models.DateTimeField(blank=True, null=True, verbose_name="Start Date")
    end_date = models.DateTimeField(blank=True, null=True, verbose_name="End Date")
    priority = models.PositiveIntegerField(default=0, verbose_name="Display Priority")

    class Meta:
        verbose_name = 'Custom Advertisement'
        verbose_name_plural = 'Custom Advertisements'
        ordering = ['-priority', '-created_at']

    def __str__(self):
        return f"{self.title} ({self.ad_type})"

    def is_currently_active(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.start_date and self.start_date > now:
            return False
        if self.end_date and self.end_date < now:
            return False
        return True
