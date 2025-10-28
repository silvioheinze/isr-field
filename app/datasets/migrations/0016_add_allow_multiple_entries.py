from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('datasets', '0015_remove_typology_from_dataset'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataset',
            name='allow_multiple_entries',
            field=models.BooleanField(default=False, help_text='Allow multiple data entries per geometry point'),
        ),
    ]
