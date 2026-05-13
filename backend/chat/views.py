from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ChatMessage, UserLead
from .serializers import ChatRequestSerializer
from .services import get_ai_response, send_chat_transcript_email


class ChatAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        lead = self.get_or_create_lead(data)

        if data.get('action') == 'end_chat':
            try:
                email_sent = send_chat_transcript_email(lead, data.get('conversation', []))
            except Exception:
                email_sent = False

            return Response(
                {
                    'lead_id': lead.id,
                    'email_sent': email_sent,
                    'response': 'Thank you. Our Tech Webbed team will connect with you shortly for detailed discussion.',
                }
            )

        user_message = data['message'].strip()
        bot_response = get_ai_response(lead, user_message)
        ChatMessage.objects.create(
            user=lead,
            user_message=user_message,
            bot_response=bot_response,
        )

        return Response(
            {
                'lead_id': lead.id,
                'response': bot_response,
            },
            status=status.HTTP_200_OK,
        )

    def get_or_create_lead(self, data):
        lead_id = data.get('lead_id')
        if lead_id:
            try:
                lead = UserLead.objects.get(id=lead_id)
                update_fields = []

                name = data.get('name', '').strip()
                phone = data.get('phone', '').strip()
                business_type = data.get('business_type', '').strip()

                if name and lead.name == 'Website Visitor':
                    lead.name = name
                    update_fields.append('name')
                if phone and not lead.phone:
                    lead.phone = phone
                    update_fields.append('phone')
                if business_type and lead.business_type == 'Not specified':
                    lead.business_type = business_type
                    update_fields.append('business_type')

                if update_fields:
                    lead.save(update_fields=update_fields)

                return lead
            except UserLead.DoesNotExist:
                pass

        return UserLead.objects.create(
            name=data.get('name', '').strip() or 'Website Visitor',
            phone=data.get('phone', '').strip(),
            business_type=data.get('business_type', '').strip() or 'Not specified',
        )
