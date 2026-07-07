from unfold.admin import ModelAdmin
from import_export.admin import ImportExportModelAdmin

class BaseAdmin(ModelAdmin, ImportExportModelAdmin):
    list_per_page = 20
    compressed_fields = True
    warn_unsaved_form = True