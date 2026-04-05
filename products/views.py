from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from .models import Product, CartItem, Order, OrderItem, Category
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
import uuid
from django.db import transaction
from django.core.paginator import Paginator
import logging

logger = logging.getLogger(__name__)

# Health check / root
def home(request):
    return HttpResponse("E-commerce API is live!")

# Product listing
def product_list(request):
    query = request.GET.get('q')
    category_id = request.GET.get('category')

    # Add order_by to avoid pagination crash
    product_list = Product.objects.all().select_related('category').order_by('id')

    if query:
        product_list = product_list.filter(name__icontains=query)
    if category_id:
        product_list = product_list.filter(category_id=category_id)

    paginator = Paginator(product_list, 6)
    page_number = request.GET.get('page')
    products = paginator.get_page(page_number)
    categories = Category.objects.all()

    return render(request, 'products/product_list.html', {
        'products': products,
        'categories': categories
    })

def product_detail(request, id):
    product = get_object_or_404(Product, id=id)
    return render(request, 'products/product_detail.html', {'product': product})

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart_item, created = CartItem.objects.get_or_create(user=request.user, product=product)
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    return redirect('cart_view')

@login_required
def cart_view(request):
    cart_items = CartItem.objects.filter(user=request.user)
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render(request, 'products/cart.html', {'cart_items': cart_items, 'total': total})

@login_required
def checkout(request):
    cart_items = CartItem.objects.filter(user=request.user).select_related('product')
    if not cart_items.exists():
        return redirect('cart_view')

    try:
        with transaction.atomic():
            total = sum(item.product.price * item.quantity for item in cart_items)
            order = Order.objects.create(user=request.user, total_price=total)

            for item in cart_items:
                if item.product.stock < item.quantity:
                    raise Exception(f"Not enough stock for {item.product.name}")

                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    product_name=item.product.name,
                    quantity=item.quantity,
                    price=item.product.price
                )
                item.product.stock -= item.quantity
                item.product.save()

            cart_items.delete()
    except Exception as e:
        logger.error(f"Checkout failed: {e}")
        return redirect('cart_view')

    return redirect('payment_page', order_id=order.id)

@login_required
def process_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if request.method == 'POST':
        order.status = 'paid'
        order.payment_reference = str(uuid.uuid4())
        order.save()
        return redirect('order_success', order_id=order.id)
    return redirect('payment_page', order_id=order.id)

@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if order.status != 'paid':
        return redirect('payment_page', order_id=order.id)
    return render(request, 'products/order_success.html', {'order': order})

@login_required
def payment_page(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.status == 'paid':
        return redirect('order_success', order_id=order.id)
    return render(request, 'products/payment.html', {'order': order})

def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('product_list')
    else:
        form = UserCreationForm()
    return render(request, 'products/signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('product_list')
    else:
        form = AuthenticationForm()
    return render(request, 'products/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('product_list')

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user)
    return render(request, 'products/order_history.html', {'orders': orders})

@require_POST
@login_required
def increase_quantity(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, user=request.user)
    if item.quantity < item.product.stock:
        item.quantity += 1
        item.save()
    return JsonResponse({'quantity': item.quantity})

@require_POST
@login_required
def decrease_quantity(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, user=request.user)
    if item.quantity > 1:
        item.quantity -= 1
        item.save()
        return JsonResponse({'quantity': item.quantity})
    else:
        item.delete()
        return JsonResponse({'deleted': True})

@require_POST
@login_required
def remove_item(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, user=request.user)
    item.delete()
    return JsonResponse({'deleted': True})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'products/order_detail.html', {'order': order})