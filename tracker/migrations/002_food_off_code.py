"""
Migrare manuala: adauga campul off_code la modelul Food.
Ruleaza dupa migrarile initiale (0001_initial).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='food',
            name='off_code',
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=50,
                verbose_name='Cod Open Food Facts',
            ),
        ),
    ]