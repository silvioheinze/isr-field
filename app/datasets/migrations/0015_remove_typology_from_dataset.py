# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('datasets', '0014_add_typology_to_dataset_field'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='dataset',
            name='typology',
        ),
    ]
