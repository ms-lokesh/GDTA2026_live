from rest_framework import serializers


class BulkStatusSerializer(serializers.Serializer):
    registration_ids = serializers.ListField(child=serializers.CharField(), min_length=1)
    status = serializers.ChoiceField(choices=["pending", "approved", "rejected"])
