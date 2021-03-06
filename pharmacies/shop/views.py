from random import randint

import icontract
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from rest_framework import viewsets

from pharmacies import settings
from pharmacies.permission import IsAdminOrReadOnly, IsStaffOrReadOnly, IsStaff
from shop.forms import (
    ReviewForm,
    SellProductForm,
    BuyerDeliveryForm,
    ContactForm,
)
from shop.models import Category, Product, Pharmacy, Contact, Review, Buyer
from shop.serializer import (
    PharmacySerializer,
    CategorySerializer,
    ReviewSerializer,
    BuyerSerializer,
    ProductSerializer,
    ContactSerializer,
)


def homepage(request):
    products_all = Product.objects.filter(active=True)
    categ = Category.objects.filter(active=True)
    products = Product.objects.filter(active=True).order_by("-created")
    featured_products = Product.objects.filter(featured=True)
    paginator = Paginator(products, 6)
    page = request.GET.get("page")
    products = paginator.get_page(page)
    return render(
        request,
        "shop/base.html",
        {
            "products_all": products_all,
            "categories": categ,
            "product": products,
            "featured_products": featured_products,
        },
    )


def about(request):
    return render(request, "shop/about.html")


def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            c = form.save(commit=False)
            c.save()
            messages.success(request, "Your message has been sent!")
            return redirect("shop:contact")
        else:
            messages.error(request, "Error! Try again")
            return redirect("shop:contact")
    else:
        form = ContactForm()
    return render(request, "shop/contact.html", {"form": form})


def pharmacy_list(request):
    pharmacies = Pharmacy.objects.filter(active=True)
    return render(
        request, "shop/pharmacies_list.html", {"pharmacies": pharmacies}
    )


def pharmacy_detail(request, iden):
    pharmacy = Pharmacy.objects.get(active=True, id=iden)
    return render(
        request, "shop/pharmacies_detail.html", {"pharmacy": pharmacy}
    )


def categories(request, slug):
    category = Category.objects.get(slug=slug)
    products = Product.objects.filter(category=category, active=True)
    return render(request, "shop/products_list.html", {"products": products})


def product_list(request):
    products_all = Product.objects.filter(active=True)
    products = Product.objects.filter(active=True).order_by("-created")
    paginator = Paginator(products, 6)
    page = request.GET.get("page")
    products = paginator.get_page(page)
    return render(
        request,
        "shop/products_list.html",
        {"products_all": products_all, "products": products},
    )


def product_detail(request, iden):
    product = Product.objects.get(id=iden)
    form = ReviewForm()
    return render(
        request,
        "shop/products_detail.html",
        {"product": product, "form": form},
    )


def search(request):
    q = request.GET["q"]
    if q:
        products = Product.objects.filter(active=True, name__icontains=q)
        categ = Category.objects.filter(active=True)
        context = {"products": products, "categories": categ}
        return render(request, "shop/products_list.html", context)
    else:
        return redirect("/")


def sell_product(request):
    if not request.user.is_staff:
        messages.info(
            request, "You have to logged in first to sell the product"
        )
        return redirect("%s?next=%s" % (settings.LOGIN_URL, request.path))
    if request.method == "POST":
        form = SellProductForm(request.POST, request.FILES)
        if form.is_valid():
            myproduct = form.save(commit=False)
            myproduct.seller = request.user
            myproduct.save()
            messages.success(
                request, "Your product has been posted successfully"
            )
            return redirect("shop:products_list")

    else:
        form = SellProductForm()
    return render(request, "shop/sell_product.html", {"form": form})


def buy_items(request):
    if not request.user.is_authenticated:
        messages.info(request, "You have to logged in first")
        return redirect("%s?next=%s" % (settings.LOGIN_URL, request.path))
    sess = request.session.get("data", {"items": []})
    if request.method == "POST":
        form = BuyerDeliveryForm(request.POST)
        if form.is_valid():
            buyer = form.save(commit=False)
            buyer.save()
            buyer.product.set(
                Product.objects.filter(active=True, id__in=sess["items"])
            )
            return redirect("shop:payment")
    else:
        form = BuyerDeliveryForm()
    return render(request, "shop/delivery_form.html", {"form": form})


def cart(request):
    sess = request.session.get("data", {"items": []})
    products = Product.objects.filter(active=True, id__in=sess["items"])
    if not products:
        return render(request, "shop/empty_cart.html")
    context = {"products": products, "categories": categories}
    return render(request, "shop/cart_item.html", context)


def reset_cart(request):
    request.session.pop("data", None)
    messages.success(request, "Done! Cart resetted")
    return redirect("shop:cart")


def payment(request):
    return render(request, "shop/payment.html")


def checkout(request):
    request.session.pop("data", None)
    p = Payment(1, FakeCreditCard(50))  # Fake
    status = p.process()
    if status == "processed":
        messages.success(request, "Done! Thanks for using our services!")
    else:
        messages.error(request, "Cancelled! Not enough money!")
    return redirect("shop:cart")


"""
Payment and FakeCreditCard classes called by checkout()
"""


def calculate_amount():
    return randint(1, 100)  # Random


class Payment:
    def __init__(self, invoice_id, credit_card):
        self.status = "cancelled"
        self.invoice_id = invoice_id
        assert isinstance(
            credit_card, FakeCreditCard
        ), "credit_card is not a FakeCreditCard instance"
        self.credit_card = credit_card

    def process(self):
        amount = calculate_amount()
        assert amount >= 0, "amount should be positive"
        if self.credit_card.has_enough_credit(amount):
            self.credit_card.withdraw(amount)
            self.status = "processed"
        else:
            self.status = "cancelled"
        return self.status


@icontract.invariant(
    lambda self: self.balance >= 0, "balance must not be negative"
)
class FakeCreditCard:
    def __init__(self, b=50):
        assert b >= 0, "balance should not be negative"
        self.balance = b

    def has_enough_credit(self, amount):
        return self.balance > amount

    def withdraw(self, amount):
        self.balance = self.balance - amount
        assert self.balance >= 0, "balance should not be negative"


def add_cart(request, iden):
    product = Product.objects.get(id=iden)
    initial = {"items": [], "price": 0.0, "count": 0}
    session = request.session.get("data", initial)
    if iden in session["items"]:
        messages.error(request, "Already added")
    else:
        session["items"].append(iden)
        session["price"] += float(product.price)
        if product.shipping_fee:
            session["price"] += float(product.shipping_fee)
        session["count"] += 1
        request.session["data"] = session
        messages.success(request, "Added to cart")
    return redirect("shop:products_detail", iden)


def add_review(request, iden):
    if not request.user.is_authenticated:
        messages.info(
            request, "You need to be logged in in order to give a review"
        )
        return redirect("%s?next=%s" % (settings.LOGIN_URL, request.path))
    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = Product.objects.get(id=iden)
            review.user = request.user
            review.save()
            messages.success(request, "Review saved")
            return redirect("shop:products_detail", iden)
    else:
        return redirect("shop:products_detail", iden)


"""
API with permissions
"""


class ContactViewSet(viewsets.ModelViewSet):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    permission_classes = [IsStaff]


class PharmacyViewSet(viewsets.ModelViewSet):
    queryset = Pharmacy.objects.filter(active=True)
    serializer_class = PharmacySerializer
    permission_classes = [IsAdminOrReadOnly]


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsStaffOrReadOnly]


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsStaffOrReadOnly]


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsStaffOrReadOnly]


class BuyerViewSet(viewsets.ModelViewSet):
    queryset = Buyer.objects.all()
    serializer_class = BuyerSerializer
    permission_classes = [IsStaff]
