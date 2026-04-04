from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from .models import Product, CartItem, Order, OrderItem, Category
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import uuid
from django.db import transaction
from django.core.paginator import Paginator


def product_list(request):
    query = request.GET.get('q')
    category_id = request.GET.get('category')

    product_list = Product.objects.all().select_related('category')

    if query:
        product_list = product_list.filter(name__icontains=query)
    if category_id:
        product_list = product_list.filter(category_id=category_id)

    # --- API LOGIC START ---
    if request.GET.get('format') == 'json':
        data = list(
            product_list.values(
                'id', 'name', 'price', 'stock', 'category__name'
            )
        )
        return JsonResponse({'products': data}, safe=False)
    # --- API LOGIC END ---

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
    return render(
        request, 'products/product_detail.html', {'product': product})


@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    cart_item, created = CartItem.objects.get_or_create(
        user=request.user,
        product=product
    )

    if not created:
        cart_item.quantity += 1
        cart_item.save()

    return redirect('cart_view')


@login_required
def cart_view(request):
    cart_items = CartItem.objects.filter(user=request.user)

    total = sum(
        item.product.price * item.quantity
        for item in cart_items
    )

    return render(request, 'products/cart.html', {
        'cart_items': cart_items,
        'total': total
    })


@login_required
def checkout(request):
    cart_items = (
        CartItem.objects.filter(user=request.user)
        .select_related('product')
    )

    if not cart_items.exists():
        return redirect('cart_view')

    try:
        with transaction.atomic():
            # 1. Calculate total and create the base order
            total = sum(
                item.product.price * item.quantity
                for item in cart_items
            )
            order = Order.objects.create(user=request.user, total_price=total)

            for item in cart_items:
                # 2. Critical Check: Is there enough stock?
                if item.product.stock < item.quantity:
                    # Raise an error to trigger the 'rollback'
                    raise Exception(
                        f"Not enough stock for {item.product.name}"
                    )

                # 3. Create OrderItem (Price snapshotting is already here!)
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    product_name=item.product.name,
                    quantity=item.quantity,
                    price=item.product.price
                )

                # 4. Update Stock
                item.product.stock -= item.quantity
                item.product.save()

            # 5. Clear Cart only if everything above worked
            cart_items.delete()

    except Exception:
        # You could add a message here using django.contrib.messages
        return redirect('cart_view')

    return redirect('payment_page', order_id=order.id)


@login_required
def process_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if request.method == 'POST':
        # simulate payment success
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
            login(request, user)  # auto-login after signup
            return redirect('product_list')
    else:
        form = UserCreationForm()
    return render(request, 'products/signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
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
def increase_quantity(request, item_id):
    item = CartItem.objects.get(id=item_id, user=request.user)
    if item.quantity < item.product.stock:
        item.quantity += 1
        item.save()

    return JsonResponse({
        'quantity': item.quantity
    })


def decrease_quantity(request, item_id):
    item = CartItem.objects.get(id=item_id, user=request.user)

    if item.quantity > 1:
        item.quantity -= 1
        item.save()
        return JsonResponse({'quantity': item.quantity})
    else:
        item.delete()
        return JsonResponse({'deleted': True})


def remove_item(request, item_id):
    item = CartItem.objects.get(id=item_id, user=request.user)
    item.delete()
    return JsonResponse({'deleted': True})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'products/order_detail.html', {'order': order})
