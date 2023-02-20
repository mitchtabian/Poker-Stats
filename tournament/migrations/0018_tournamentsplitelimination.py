# Generated by Django 3.2 on 2023-02-19 23:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tournament', '0017_auto_20230215_0621'),
    ]

    operations = [
        migrations.CreateModel(
            name='TournamentSplitElimination',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('eliminated_at', models.DateTimeField(auto_now_add=True)),
                ('is_backfill', models.BooleanField(default=False)),
                ('eliminatee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='Eliminatee_for_split', to='tournament.tournamentplayer')),
                ('eliminators', models.ManyToManyField(related_name='Eliminators_for_split', to='tournament.TournamentPlayer')),
            ],
        ),
    ]
