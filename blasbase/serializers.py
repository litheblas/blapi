from rest_framework import serializers

from .models import Person


class PersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        exclude = (
            #'functions',
            #'user',
        )
        read_only_fields = ('user',)
