# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('datasets', '0021_dataset_mapping_area_limits'),
    ]

    operations = [
        migrations.AddField(
            model_name='datasetfield',
            name='non_editable',
            field=models.BooleanField(default=False, help_text='If enabled, this field cannot be edited in data entry forms'),
        ),
    ]

