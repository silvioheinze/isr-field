# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('datasets', '0022_add_non_editable_to_dataset_field'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datasetfield',
            name='order',
            field=models.IntegerField(default=0, help_text='Display order (0 = first, -1 = last)'),
        ),
    ]

