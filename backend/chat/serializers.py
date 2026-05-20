from rest_framework import serializers


def normalize_phone_number(value):
    cleaned = value.strip()

    if any(character not in '+0123456789 .()-' for character in cleaned):
        return ''

    digits = ''.join(character for character in cleaned if character.isdigit())

    if digits.startswith('91') and len(digits) == 12:
        digits = digits[2:]

    digits = digits.lstrip('0')

    if len(digits) != 10 or digits.startswith('0'):
        return ''

    return digits


class ChatRequestSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['message', 'capture_lead', 'end_chat'], default='message')
    lead_id = serializers.IntegerField(required=False, allow_null=True)
    session_id = serializers.CharField(max_length=80, required=False, allow_blank=True)
    name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=40, required=False, allow_blank=True)
    business_type = serializers.CharField(max_length=160, required=False, allow_blank=True)
    message = serializers.CharField(required=False, allow_blank=True)
    conversation = serializers.ListField(required=False, child=serializers.DictField(), allow_empty=True)
    trigger = serializers.CharField(max_length=40, required=False, allow_blank=True)

    def validate(self, attrs):
        action = attrs.get('action', 'message')
        phone = attrs.get('phone', '').strip()

        if action == 'message' and not attrs.get('message', '').strip():
            raise serializers.ValidationError({'message': 'Message is required.'})

        if phone:
            normalized_phone = normalize_phone_number(phone)

            if not normalized_phone:
                raise serializers.ValidationError({'phone': 'Please enter a valid 10-digit contact number.'})

            attrs['phone'] = normalized_phone

        return attrs
