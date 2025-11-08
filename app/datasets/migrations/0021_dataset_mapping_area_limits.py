from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('datasets', '0020_mappingarea'),
    ]

    operations = [
        migrations.CreateModel(
            name='DatasetUserMappingArea',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dataset', models.ForeignKey(on_delete=models.CASCADE, related_name='user_mapping_area_limits', to='datasets.dataset')),
                ('mapping_area', models.ForeignKey(on_delete=models.CASCADE, related_name='user_access_limits', to='datasets.mappingarea')),
                ('user', models.ForeignKey(on_delete=models.CASCADE, related_name='dataset_mapping_area_limits', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Dataset User Mapping Area',
                'verbose_name_plural': 'Dataset User Mapping Areas',
                'unique_together': {('dataset', 'user', 'mapping_area')},
            },
        ),
        migrations.CreateModel(
            name='DatasetGroupMappingArea',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dataset', models.ForeignKey(on_delete=models.CASCADE, related_name='group_mapping_area_limits', to='datasets.dataset')),
                ('group', models.ForeignKey(on_delete=models.CASCADE, related_name='dataset_mapping_area_limits', to='auth.group')),
                ('mapping_area', models.ForeignKey(on_delete=models.CASCADE, related_name='group_access_limits', to='datasets.mappingarea')),
            ],
            options={
                'verbose_name': 'Dataset Group Mapping Area',
                'verbose_name_plural': 'Dataset Group Mapping Areas',
                'unique_together': {('dataset', 'group', 'mapping_area')},
            },
        ),
    ]

