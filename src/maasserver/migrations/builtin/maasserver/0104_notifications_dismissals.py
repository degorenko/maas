# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import (
    migrations,
    models,
)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('maasserver', '0103_notifications'),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificationDismissal',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('notification', models.ForeignKey(to='maasserver.Notification')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
