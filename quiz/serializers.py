from rest_framework import serializers
from .models import Exam, Question, Choice

class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ('id','text')

class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True)
    class Meta:
        model = Question
        fields = ('id','text','choices','question_type','matching_pairs','ordering_items','numeric_tolerance','difficulty')

class ExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = ('id','title','question_count','duration_seconds')
