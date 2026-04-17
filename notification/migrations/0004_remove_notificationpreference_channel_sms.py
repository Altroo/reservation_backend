from django.db import migrations


class Migration(migrations.Migration):

	dependencies = [
		("notification", "0003_notificationpreference_channels_and_unpaid_rents"),
	]

	operations = [
		migrations.RemoveField(
			model_name="historicalnotificationpreference",
			name="channel_sms",
		),
		migrations.RemoveField(
			model_name="notificationpreference",
			name="channel_sms",
		),
	]