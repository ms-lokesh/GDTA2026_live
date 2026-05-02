from rest_framework import serializers

from registrations.security import is_sanctioned_country


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
    title = serializers.CharField(required=False, allow_blank=True)
    gender = serializers.CharField(required=False, allow_blank=True)
    institution = serializers.CharField()
    role = serializers.CharField(required=False, allow_blank=True)
    registration_category = serializers.CharField()
    addon_food = serializers.BooleanField(default=False)
    addon_food_accommodation = serializers.CharField(required=False, allow_blank=True)
    addon_safari = serializers.BooleanField(default=False)
    safari_route = serializers.CharField(required=False, allow_blank=True)
    gdta_member = serializers.CharField(required=False, allow_blank=True)
    gdta_affiliation = serializers.CharField(required=False, allow_blank=True)
    country = serializers.CharField()
    state = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField()
    event_id = serializers.CharField()

    def validate_country(self, value):
        if is_sanctioned_country(value):
            raise serializers.ValidationError("Registration not available in your region")
        return value


class PaymentCreateLinkSerializer(serializers.Serializer):
    registration_id = serializers.CharField()
    name = serializers.CharField()
    email = serializers.EmailField()
    registration_category = serializers.CharField()
    addon_food = serializers.BooleanField(default=False)
    addon_safari = serializers.BooleanField(default=False)
    payment_method = serializers.CharField(required=False, allow_blank=True)


class PaymentStatusSerializer(serializers.Serializer):
    invoice_id = serializers.CharField()
    registration_id = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)


class UnifiedPaymentCreateSerializer(serializers.Serializer):
    registration_id = serializers.CharField()
    user_name = serializers.CharField()
    email = serializers.EmailField()
    category = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_method = serializers.ChoiceField(choices=["paytm", "razorpay"])
    addon_food = serializers.BooleanField(default=False)
    addon_safari = serializers.BooleanField(default=False)


class PaytmCallbackSerializer(serializers.Serializer):
    ORDERID = serializers.CharField()
    TXNID = serializers.CharField(required=False, allow_blank=True)
    STATUS = serializers.CharField(required=False, allow_blank=True)
    CHECKSUMHASH = serializers.CharField()
