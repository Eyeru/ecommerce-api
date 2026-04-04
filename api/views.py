from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.db import transaction
from django.shortcuts import get_object_or_404

from products.models import Product, Category, CartItem, Order, OrderItem
from .serializers import (
    ProductSerializer, CategorySerializer, 
    CartItemSerializer, OrderSerializer
)


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [permissions.AllowAny()]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get('category')
        search = self.request.query_params.get('search')
        
        if category:
            queryset = queryset.filter(category_id=category)
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        return queryset


class CartViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """View cart items"""
        cart_items = CartItem.objects.filter(user=request.user)
        serializer = CartItemSerializer(cart_items, many=True)
        total = sum(item.product.price * item.quantity for item in cart_items)
        return Response({
            'items': serializer.data, 
            'total': total
        })
    
    @action(detail=False, methods=['post'])
    def add(self, request):
        """Add item to cart"""
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)
        
        if not product_id:
            return Response({'error': 'product_id is required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, 
                          status=status.HTTP_404_NOT_FOUND)
        
        cart_item, created = CartItem.objects.get_or_create(
            user=request.user, 
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        return Response({
            'message': 'Added to cart',
            'quantity': cart_item.quantity
        })
    
    @action(detail=False, methods=['post'])
    def update_quantity(self, request):
        """Update cart item quantity"""
        item_id = request.data.get('item_id')
        quantity = request.data.get('quantity')
        
        if not item_id or not quantity:
            return Response({'error': 'item_id and quantity are required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            cart_item = CartItem.objects.get(id=item_id, user=request.user)
        except CartItem.DoesNotExist:
            return Response({'error': 'Item not found in cart'}, 
                          status=status.HTTP_404_NOT_FOUND)
        
        if quantity <= 0:
            cart_item.delete()
            return Response({'message': 'Item removed from cart'})
        
        cart_item.quantity = quantity
        cart_item.save()
        
        return Response({'message': 'Quantity updated', 'quantity': cart_item.quantity})
    
    @action(detail=False, methods=['delete'])
    def remove(self, request):
        """Remove item from cart"""
        item_id = request.data.get('item_id')
        
        if not item_id:
            return Response({'error': 'item_id is required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            cart_item = CartItem.objects.get(id=item_id, user=request.user)
            cart_item.delete()
        except CartItem.DoesNotExist:
            pass
        
        return Response({'message': 'Item removed from cart'})
    
    @action(detail=False, methods=['post'])
    def checkout(self, request):
        """Process checkout and create order"""
        cart_items = CartItem.objects.filter(user=request.user)
        
        if not cart_items.exists():
            return Response({'error': 'Cart is empty'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                # Calculate total
                total = sum(item.product.price * item.quantity for item in cart_items)
                
                # Create order
                order = Order.objects.create(
                    user=request.user, 
                    total_price=total
                )
                
                # Create order items and update stock
                for item in cart_items:
                    if item.product.stock < item.quantity:
                        return Response(
                            {'error': f'Insufficient stock for {item.product.name}'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        product_name=item.product.name,
                        quantity=item.quantity,
                        price=item.product.price
                    )
                    
                    item.product.stock -= item.quantity
                    item.product.save()
                
                # Clear cart
                cart_items.delete()
                
                serializer = OrderSerializer(order)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            return Response({'error': str(e)}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return Order.objects.all()
        return Order.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        """Process payment for order"""
        order = self.get_object()
        
        if order.status == 'paid':
            return Response({'error': 'Order already paid'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        order.status = 'paid'
        order.save()
        
        return Response({
            'message': 'Payment successful',
            'order_id': order.id,
            'status': order.status
        })