from django.contrib.auth.models import User, Group

# Get or create the "Managers" group
managers_group, created = Group.objects.get_or_create(name='Managers')
if created:
    print(f"Created 'Managers' group")
else:
    print(f"'Managers' group already exists")

# Add a user to the Managers group
username = 'your_username'  # Replace with actual username
user = User.objects.get(username=username)
user.groups.add(managers_group)
print(f"Added {username} to Managers group")

# Verify
if user.groups.filter(name='Managers').exists():
    print(f"{username} can now create datasets!")
else:
    print(f"Something went wrong - {username} is not in Managers group")
