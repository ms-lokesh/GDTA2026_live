from rest_framework import serializers


class VenueSerializer(serializers.Serializer):
    event_id = serializers.CharField()
    name = serializers.CharField(max_length=255)
    venue_type = serializers.CharField(max_length=64)
    description = serializers.CharField(required=False, allow_blank=True)
    location = serializers.CharField(required=False, allow_blank=True)
    capacity = serializers.IntegerField(required=False)
    is_active = serializers.BooleanField(default=True)
    access_limit = serializers.CharField(default="unlimited")


class QRValidateSerializer(serializers.Serializer):
    unique_id = serializers.CharField()
    venue_id = serializers.CharField()
