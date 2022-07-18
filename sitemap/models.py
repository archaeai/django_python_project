from django.db import models

# Create your models here.

class MarketScore(models.Model):
    year = models.IntegerField()
    gu = models.CharField(max_length=10)
    dong = models.CharField(max_length=20)
    dong_code = models.IntegerField()
    service = models.CharField(max_length=10)
    sales_per_mart = models.BigIntegerField()
    run_month = models.IntegerField()
    close_month = models.IntegerField()
    close_rate = models.IntegerField()

    def __str__(self) -> str:
        return self.gu + ' ' + self.dong + ' ' + self.service

class GraphImage(models.Model):
    title = models.CharField(max_length=120)
    image = models.ImageField(upload_to='images/', null=True, blank=True)