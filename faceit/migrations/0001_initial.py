from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='FaceitAnalysis',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('game_id', models.CharField(max_length=100, unique=True)),
                ('date_analyzed', models.DateTimeField(auto_now_add=True)),
                ('match_data', models.TextField(blank=True, null=True)),
            ],
        ),
    ]
