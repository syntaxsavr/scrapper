from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import PaymentMethod  # payment model
from ..forms import PaymentMethodForm  # payment form


@login_required  # must be logged in
def payment_methods_view(request):
    """View all payment methods"""
    payment_methods = PaymentMethod.objects.filter(user=request.user)  # get user's cards only
    context = {'payment_methods': payment_methods}
    return render(request, 'accounts/payment_methods.html', context)


@login_required
def add_payment_method_view(request):
    """Add new payment method"""
    if request.method == 'POST':  # form submitted
        form = PaymentMethodForm(request.POST)
        if form.is_valid():
            payment_method = form.save(commit=False)
            payment_method.user = request.user  # assign to current user
            payment_method.save()
            messages.success(request, 'Payment method added successfully!')
            return redirect('payment_methods')  # back to list
    else:
        form = PaymentMethodForm()  # empty form
    
    context = {'form': form}
    return render(request, 'accounts/add_payment_method.html', context)


@login_required
def edit_payment_method_view(request, payment_id):
    """Edit existing payment method"""
    payment_method = get_object_or_404(PaymentMethod, id=payment_id, user=request.user)  # make sure user owns it
    
    if request.method == 'POST':  # form submitted
        form = PaymentMethodForm(request.POST, instance=payment_method)
        if form.is_valid():
            form.save()  # update the payment method
            messages.success(request, 'Payment method updated successfully!')
            return redirect('payment_methods')
    else:
        form = PaymentMethodForm(instance=payment_method)  # load existing data
    
    context = {'form': form, 'payment_method': payment_method}
    return render(request, 'accounts/edit_payment_method.html', context)


@login_required
def delete_payment_method_view(request, payment_id):
    """Delete payment method"""
    payment_method = get_object_or_404(PaymentMethod, id=payment_id, user=request.user)  # make sure user owns it
    
    if request.method == 'POST':  # confirmed deletion
        payment_method.delete()  # remove from db
        messages.success(request, 'Payment method deleted successfully!')
        return redirect('payment_methods')
    
    context = {'payment_method': payment_method}  # show confirmation page
    return render(request, 'accounts/delete_payment_method.html', context)