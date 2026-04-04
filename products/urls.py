from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('api/products/', views.product_list, name='product_list'),
    path('product/<int:id>/', views.product_detail, name='product_detail'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, 
         name='add_to_cart'),
    path('cart/', views.cart_view, name='cart_view'),
    path('checkout/', views.checkout, name='checkout'),  
    path('order-success/<int:order_id>/', views.order_success, 
         name='order_success'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('orders/', views.order_history, name='order_history'),
    path('increase/<int:item_id>/', views.increase_quantity, 
         name='increase_quantity'),
    path('decrease/<int:item_id>/', views.decrease_quantity, 
         name='decrease_quantity'),
    path('remove/<int:item_id>/', views.remove_item, name='remove_item'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('payment/<int:order_id>/', views.payment_page, name='payment_page'),
    path('process-payment/<int:order_id>/', views.process_payment, 
         name='process_payment'),
]
