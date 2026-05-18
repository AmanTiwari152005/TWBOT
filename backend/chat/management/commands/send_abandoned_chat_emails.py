import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from chat.models import UserLead
from chat.services import send_chat_transcript_email


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send final transcript emails for completed leads abandoned after inactivity.'

    def add_arguments(self, parser):
        parser.add_argument('--minutes', type=int, default=3)
        parser.add_argument('--limit', type=int, default=100)

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(minutes=options['minutes'])
        candidates = UserLead.objects.filter(
            email_sent=False,
            lead_completed=True,
            last_activity__lt=cutoff,
        ).order_by('last_activity')[: options['limit']]

        sent_count = 0
        skipped_count = 0

        for candidate in candidates:
            with transaction.atomic():
                lead = UserLead.objects.select_for_update().get(id=candidate.id)

                if lead.email_sent or not lead.lead_completed or lead.last_activity >= cutoff:
                    skipped_count += 1
                    continue

                try:
                    email_sent = send_chat_transcript_email(lead)
                except Exception as error:
                    logger.exception('Failed to send abandoned chat email for lead_id=%s: %s', lead.id, error)
                    skipped_count += 1
                    continue

                if not email_sent:
                    skipped_count += 1
                    continue

                now = timezone.now()
                lead.email_sent = True
                lead.email_sent_at = now
                lead.last_activity = now
                lead.save(update_fields=['email_sent', 'email_sent_at', 'last_activity'])
                sent_count += 1

        self.stdout.write(
            self.style.SUCCESS(f'Abandoned chat email pass complete. sent={sent_count} skipped={skipped_count}')
        )
