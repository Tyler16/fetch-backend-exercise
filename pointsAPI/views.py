from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum
from .models import Transaction, Payer
from .serializers import TransactionSerializer, PayerSerializer

@api_view(['POST'])
def add(request):
    # Create new transaction based on data
    serialized_transaction = TransactionSerializer(data=request.data)

    # Check if request is valid
    if serialized_transaction.is_valid():
        # Save transaction
        transaction = serialized_transaction.save()

        # Get or create payer value associated with transaction
        payer, created = Payer.objects.get_or_create(
            pk=transaction.payer,
            defaults={'points': transaction.points}
        )

        # Add points to payer points if payer already exists
        if not created:
            payer.points += transaction.points
            payer.save()

        # Respond with OK status
        return Response(status=status.HTTP_200_OK)
    else:
        # Respond with errors
        return Response(serialized_transaction.errors)


@api_view(['POST'])
def spend(request):
    # Check if total points exceeded by request
    total_points = Payer.objects.aggregate(Sum('points'))['points__sum'] or 0
    total_spent_points = request.data['points']
    if total_points < total_spent_points:
        return Response("User doesn't have enough points", status=status.HTTP_400_BAD_REQUEST)
    
    # Get transactions sorted by timestamp
    response = dict()
    transactions = Transaction.objects.all().order_by('timestamp')

    # Go through transactions and subtract points
    for transaction in transactions:
        # Check if points still need to be spent
        if total_spent_points <= 0:
            break

        # Get payer object
        payer_str = transaction.payer
        payer = Payer.objects.get(pk=payer_str)
        spent_points = 0

        # If all points from transaction spent delete transaction and remove points
        if transaction.points <= total_spent_points:
            # Spend all remaining points in transaction
            spent_points = transaction.points

            # Remove transaction
            transaction.delete()

        # Otherwise, spend all remaining points on transaction
        else:
            # Spend any remaining points that need to be spent
            spent_points = total_spent_points

            # Update current transaction
            transaction.points -= total_spent_points
            transaction.save()
        
        # Add spent points for transaction to response
        response[payer_str] = response.get(payer_str, 0) - spent_points
        
        # Reduce total spent points by spent points for transaction
        total_spent_points -= spent_points

        # Update amount of points in payer table by spent points
        payer.points -= spent_points

        # Check if points remain for a given payer and remove if necessary
        if payer.points == 0:
            payer.delete()
        else:
            payer.save()


    return Response(response, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_balance(request):
    # Get balance for payers and serialize
    balance = Payer.objects.all()
    serialized_balance = PayerSerializer(balance, many=True).data

    # Reformat data to be key, value based
    formatted_balance = {}
    for payer_obj in serialized_balance:
        formatted_balance[payer_obj['payer']] = payer_obj['points']

    # Return data
    return Response(formatted_balance, status=status.HTTP_200_OK)