import logging

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission

class Command(BaseCommand):
    def handle(self, *args, **options):
        perms_event_organizer = [
            'add_event',
            'change_event',
            'add_location',
            'change_location',
            'add_participant',
            'change_participant',
            'add_tag'
        ]
        perms_pr = [
            'change_approval'
        ]
        perms_experienced_event_organizer = perms_event_organizer + [
            'add_approval',
            'delete_approval',
            'add_event_scheduled'
        ]
        perms_producer = perms_experienced_event_organizer + [
            'change_user',
            'add_category',
            'change_category',
            'delete_category',
            'change_event_others',
            'change_participant_others',
            'delete_participant',
            'add_template',
            'change_template',
            'delete_template'
        ]
        groups_add = [
            ('Event Organizer', perms_event_organizer),
            ('Experienced Event Organizer', perms_experienced_event_organizer),
            ('Producer', perms_producer),
            ('PR', perms_pr)
        ]
        for group, perms in groups_add:
            try:
                Group.objects.get(name=group)
                print "Skipping %s" % group
            except Group.DoesNotExist:
                print "Creating group %s" % group
                group = Group.objects.create(name=group)
                for perm in perms:
                    try:
                        perm_obj = Permission.objects.get(codename=perm)
                        group.permissions.add(perm_obj)
                        print "\tAttaching permission %s" % perm
                    except Permission.DoesNotExist:
                        print "\tSkipping permission %s" % perm
                group.save()
