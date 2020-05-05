import rules
from .models import Schedule, Event
from accounts.models import User

@rules.predicate
def is_schedule_owner(user: User, schedule: Schedule):
    return schedule.user == user

@rules.predicate
def is_superuser(user: User):
    return user.is_superuser

@rules.predicate
def is_event_owner(user: User, event: Event):
    return event.schedule.user == user

rules.add_perm('scheduling.change_schedule', is_schedule_owner | is_superuser)
rules.add_perm('scheduling.view_schedule', is_schedule_owner | is_superuser)
rules.add_perm('scheduling.delete_schedule', is_schedule_owner | is_superuser)

rules.add_perm('scheduling.change_event', is_event_owner | is_superuser)
rules.add_perm('scheduling.view_event', is_event_owner | is_superuser)
rules.add_perm('scheduling.delete_event', is_event_owner | is_superuser)
