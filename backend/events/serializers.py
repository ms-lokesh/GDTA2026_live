from rest_framework import serializers


class EventSerializer(serializers.Serializer):
    event_id = serializers.CharField(max_length=100)
    name = serializers.CharField(max_length=255)
    year = serializers.IntegerField()
    start_date = serializers.CharField(max_length=64)
    end_date = serializers.CharField(max_length=64)
    location = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(default=True)
