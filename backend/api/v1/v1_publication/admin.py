from django.contrib import admin
from api.v1.v1_publication.models import PublicationRaster


@admin.register(PublicationRaster)
class PublicationRasterAdmin(admin.ModelAdmin):
    list_display = ("publication", "indicator", "geonode_id", "extracted_at")
    list_filter = ("indicator",)
