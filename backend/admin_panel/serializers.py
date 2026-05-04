from rest_framework import serializers


class BulkStatusSerializer(serializers.Serializer):
    registration_ids = serializers.ListField(child=serializers.CharField(), min_length=1)
    status = serializers.ChoiceField(choices=["pending", "approved", "rejected"])


class UserManagementSerializer(serializers.Serializer):
    uid = serializers.CharField()
    name = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    event_ids = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    assigned_venues = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    is_active = serializers.BooleanField(default=True)


class UserManagementUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    password = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    event_ids = serializers.ListField(child=serializers.CharField(), required=False)
    assigned_venues = serializers.ListField(child=serializers.CharField(), required=False)
    is_active = serializers.BooleanField(required=False)


class IdCardGenerateSerializer(serializers.Serializer):
    force_regenerate = serializers.BooleanField(default=False)
