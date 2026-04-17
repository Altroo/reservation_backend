from django.db import migrations


class Migration(migrations.Migration):

	dependencies = [
		("notification", "0004_remove_notificationpreference_channel_sms"),
	]

	operations = [
		migrations.RemoveField(
			model_name="historicalnotificationpreference",
			name="channel_email",
		),
		migrations.RemoveField(
			model_name="historicalnotificationpreference",
			name="channel_push",
		),
		migrations.RemoveField(
			model_name="notificationpreference",
			name="channel_email",
		),
		migrations.RemoveField(
			model_name="notificationpreference",
			name="channel_push",
		),
	]