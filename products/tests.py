from django.test import TestCase
from django.contrib.auth.models import User
from products.models import Product, Category, CartItem, Order

class ProductModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Electronics', slug='electronics')
        self.product = Product.objects.create(
            name='Laptop',
            price=1000,
            stock=10,
            category=self.category
        )
    
    def test_product_creation(self):
        self.assertEqual(self.product.name, 'Laptop')
        self.assertEqual(self.product.price, 1000)

class CheckoutFlowTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        self.category = Category.objects.create(name='Electronics', slug='electronics')
        self.product = Product.objects.create(
            name='Laptop',
            price=1000,
            stock=5,
            category=self.category
        )
    
    def test_checkout_reduces_stock(self):
        # Add to cart
        CartItem.objects.create(user=self.user, product=self.product, quantity=2)
        
        # Checkout
        response = self.client.post('/checkout/')
        
        # Verify stock decreased
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        
        # Verify order created
        order = Order.objects.filter(user=self.user).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.total_price, 2000)