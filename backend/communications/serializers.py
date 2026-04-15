from rest_framework import serializers


class EmailSendSerializer(serializers.Serializer):
    to_emails = serializers.ListField(child=serializers.EmailField(), min_length=1)
    subject = serializers.CharField(max_length=255)
    message = serializers.CharField()
