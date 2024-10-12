from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q
from .models import Book, Order, OrderItem
from .forms import BookForm

from django.contrib.auth import login

import stripe


# from django.contrib.auth import login

stripe.api_key = settings.STRIPE_SECRET_KEY

def book_list(request):
    books = Book.objects.all()
    return render(request, 'store/book_list.html', {'books': books})

@login_required
def add_book(request):
    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('book_list')
    else:
        form = BookForm()
    return render(request, 'store/add_book.html', {'form': form})

@login_required
def add_to_cart(request, book_id):
    book = Book.objects.get(id=book_id)
    cart = request.session.get('cart', {})
    cart[book_id] = cart.get(book_id, 0) + 1
    request.session['cart'] = cart
    return redirect('book_list')

@login_required
def view_cart(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total = 0
    for book_id, quantity in cart.items():
        book = Book.objects.get(id=book_id)
        item_total = book.price * quantity
        total += item_total
        cart_items.append({
            'book': book,
            'quantity': quantity,
            'total': item_total,
        })
    return render(request, 'store/cart.html', {'cart_items': cart_items, 'total': total})

@login_required
def checkout(request):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        total = sum(Book.objects.get(id=book_id).price * quantity for book_id, quantity in cart.items())
        
        try:
            charge = stripe.Charge.create(
                amount=int(total * 100),  # Amount in cents
                currency='usd',
                source=request.POST['stripeToken'],
                description='Book purchase',
            )

            order = Order.objects.create(user=request.user, total_price=total, is_paid=True)
            for book_id, quantity in cart.items():
                book = Book.objects.get(id=book_id)
                OrderItem.objects.create(order=order, book=book, quantity=quantity)

            del request.session['cart']
            return render(request, 'store/success.html')
        except stripe.error.CardError as e:
            return render(request, 'store/error.html', {'error': str(e)})

    return render(request, 'store/checkout.html', {'stripe_public_key': settings.STRIPE_PUBLIC_KEY})

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('book_list')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

def search(request):
    query = request.GET.get('q')
    if query:
        books = Book.objects.filter(Q(title__icontains=query) | Q(author__icontains=query))
    else:
        books = Book.objects.all()
    return render(request, 'store/search_results.html', {'books': books, 'query': query})