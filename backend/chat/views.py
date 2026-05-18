import logging

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ChatMessage, UserLead
from .serializers import ChatRequestSerializer
from .services import get_ai_response, send_chat_transcript_email, send_lead_capture_email


logger = logging.getLogger(__name__)


class ChatAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        lead = self.get_or_create_lead(data)

        if data.get('action') == 'capture_lead':
            lead_notification_sent = self.maybe_send_lead_capture_email(lead)
            return Response(
                {
                    'lead_id': lead.id,
                    'lead_completed': lead.lead_completed,
                    'lead_notification_sent': lead_notification_sent,
                },
                status=status.HTTP_200_OK,
            )

        if data.get('action') == 'end_chat':
            return self.end_chat(lead, data)

        user_message = data['message'].strip()
        bot_response = get_ai_response(lead, user_message)
        ChatMessage.objects.create(
            user=lead,
            user_message=user_message,
            bot_response=bot_response,
        )
        self.touch_lead(lead)
        if lead.lead_completed and not lead.lead_notification_sent:
            self.maybe_send_lead_capture_email(lead)

        return Response(
            {
                'lead_id': lead.id,
                'response': bot_response,
            },
            status=status.HTTP_200_OK,
        )

    def end_chat(self, lead, data):
        trigger = data.get('trigger', '').strip() or 'unknown'
        logger.info('End chat trigger fired: trigger=%s lead_id=%s.', trigger, lead.id)

        with transaction.atomic():
            lead = UserLead.objects.select_for_update().get(id=lead.id)

            if lead.email_sent:
                logger.info('Duplicate end chat ignored for lead_id=%s trigger=%s.', lead.id, trigger)
                return Response(
                    {
                        'lead_id': lead.id,
                        'email_sent': True,
                        'data_deleted': False,
                        'duplicate_skipped': True,
                        'response': 'Thank you. Our Tech Webbed team will connect with you shortly for detailed discussion.',
                    }
                )

            try:
                email_sent = send_chat_transcript_email(lead, data.get('conversation', []))
            except Exception as error:
                logger.exception('Failed to send chat transcript for lead_id=%s trigger=%s: %s', lead.id, trigger, error)
                email_sent = False

            if email_sent:
                now = timezone.now()
                lead.email_sent = True
                lead.email_sent_at = now
                lead.lead_completed = bool(lead.name and lead.phone)
                lead.last_activity = now
                lead.save(update_fields=['email_sent', 'email_sent_at', 'lead_completed', 'last_activity'])
                logger.info('End chat email marked sent for lead_id=%s trigger=%s.', lead.id, trigger)
            else:
                logger.warning('End chat email not sent for lead_id=%s trigger=%s.', lead.id, trigger)

        return Response(
            {
                'lead_id': lead.id,
                'email_sent': email_sent,
                'data_deleted': False,
                'duplicate_skipped': False,
                'response': 'Thank you. Our Tech Webbed team will connect with you shortly for detailed discussion.',
            }
        )

    def maybe_send_lead_capture_email(self, lead):
        if not lead.name or not lead.phone:
            return False

        with transaction.atomic():
            lead = UserLead.objects.select_for_update().get(id=lead.id)

            if lead.lead_notification_sent:
                return True

            try:
                email_sent = send_lead_capture_email(lead)
            except Exception as error:
                logger.exception('Failed to send lead capture email for lead_id=%s: %s', lead.id, error)
                return False

            if email_sent:
                now = timezone.now()
                lead.lead_notification_sent = True
                lead.lead_notification_sent_at = now
                lead.lead_completed = True
                lead.last_activity = now
                lead.save(
                    update_fields=[
                        'lead_notification_sent',
                        'lead_notification_sent_at',
                        'lead_completed',
                        'last_activity',
                    ]
                )
            else:
                logger.warning('Lead capture email not sent for lead_id=%s.', lead.id)

        return email_sent

    def touch_lead(self, lead):
        lead.last_activity = timezone.now()
        lead.save(update_fields=['last_activity'])

    def get_or_create_lead(self, data):
        lead_id = data.get('lead_id')
        session_id = data.get('session_id', '').strip() or None
        name = data.get('name', '').strip()
        phone = data.get('phone', '').strip()
        business_type = data.get('business_type', '').strip()
        lead = None

        if lead_id:
            try:
                lead = UserLead.objects.get(id=lead_id)
            except UserLead.DoesNotExist:
                pass

        if not lead and session_id:
            lead = UserLead.objects.filter(session_id=session_id).first()

        if not lead:
            try:
                return UserLead.objects.create(
                    session_id=session_id,
                    name=name or 'Website Visitor',
                    phone=phone,
                    business_type=business_type or 'Not specified',
                    lead_completed=bool(name and phone),
                    last_activity=timezone.now(),
                )
            except IntegrityError:
                if not session_id:
                    raise
                lead = UserLead.objects.get(session_id=session_id)

        update_fields = []

        if session_id and not lead.session_id:
            lead.session_id = session_id
            update_fields.append('session_id')
        if name and lead.name == 'Website Visitor':
            lead.name = name
            update_fields.append('name')
        if phone and not lead.phone:
            lead.phone = phone
            update_fields.append('phone')
        if business_type and lead.business_type == 'Not specified':
            lead.business_type = business_type
            update_fields.append('business_type')
        if lead.name and lead.phone and not lead.lead_completed:
            lead.lead_completed = True
            update_fields.append('lead_completed')

        lead.last_activity = timezone.now()
        update_fields.append('last_activity')

        if update_fields:
            lead.save(update_fields=list(dict.fromkeys(update_fields)))

        return lead
