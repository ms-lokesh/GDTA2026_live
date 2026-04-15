from rest_framework import serializers


class StartRegistrationSerializer(serializers.Serializer):
    session_id = serializers.CharField(required=False)


class AnswerRegistrationSerializer(serializers.Serializer):
    session_id = serializers.CharField()
    answer = serializers.CharField()


class CancelRegistrationSerializer(serializers.Serializer):
    session_id = serializers.CharField()


class SubmitRegistrationSerializer(serializers.Serializer):
    consent = serializers.CharField()
    name = serializers.CharField()
    institution = serializers.CharField()
    role = serializers.CharField(required=False, allow_blank=True)
    registration_category = serializers.CharField()
    addon_food = serializers.BooleanField(default=False)
    addon_safari = serializers.BooleanField(default=False)
    safari_route = serializers.CharField(required=False, allow_blank=True)
    country = serializers.CharField()
    state = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField()
    event_id = serializers.CharField()
