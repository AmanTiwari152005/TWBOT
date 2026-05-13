from rest_framework import serializers


class ChatRequestSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['message', 'end_chat'], default='message')
    lead_id = serializers.IntegerField(required=False, allow_null=True)
    name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    business_type = serializers.CharField(max_length=160, required=False, allow_blank=True)
    message = serializers.CharField(required=False, allow_blank=True)
    conversation = serializers.ListField(required=False, child=serializers.DictField(), allow_empty=True)

    def validate(self, attrs):
        action = attrs.get('action', 'message')

        if action == 'message' and not attrs.get('message', '').strip():
            raise serializers.ValidationError({'message': 'Message is required.'})

        return attrs
