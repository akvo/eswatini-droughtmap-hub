from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("v1_iks", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="iksindicator",
            name="section",
            field=models.CharField(
                blank=True,
                choices=[
                    ("B", "Section B \u2013 Rainfall Predictors"),
                    ("C", "Section C \u2013 Seasonal/Extreme Weather"),
                    ("D", "Section D \u2013 Soil/Vegetation"),
                ],
                db_index=True,
                default="",
                max_length=1,
            ),
        ),
    ]
