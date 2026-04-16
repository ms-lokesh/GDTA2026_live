from rest_framework import serializers


class EmailSendSerializer(serializers.Serializer):
    to_emails = serializers.ListField(child=serializers.EmailField(), min_length=1)
    subject = serializers.CharField(max_length=255, required=False, allow_blank=True)
    message = serializers.CharField(required=False, allow_blank=True)
    template_id = serializers.CharField(required=False, allow_blank=True)
    variables = serializers.DictField(required=False)


class EmailTemplateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=128)
    subject = serializers.CharField(max_length=255)
    body = serializers.CharField()
    is_active = serializers.BooleanField(default=True)


class EmailTemplateUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=128, required=False)
    subject = serializers.CharField(max_length=255, required=False)
    body = serializers.CharField(required=False)
    is_active = serializers.BooleanField(required=False)
