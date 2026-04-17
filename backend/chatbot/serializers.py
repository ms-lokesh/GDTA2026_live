from rest_framework import serializers


class ChatbotStartSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(
        choices=["conference_registration", "hackathon_registration", "event_planner", "conference_assistant"],
        default="conference_registration",
        required=False,
    )


class ChatbotMessageSerializer(serializers.Serializer):
    session_id = serializers.CharField()
    message = serializers.CharField(allow_blank=False)


class ChatbotSessionSerializer(serializers.Serializer):
    session_id = serializers.CharField()
