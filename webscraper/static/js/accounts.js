// User Account Management JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Initialize all user management features when page loads
    initImagePreview();
    initFormValidation();
    initPaymentMethodCards();
    initConfirmationDialogs();
    initProfileDropdown(); // dropdown menu stuff
});

// Image preview for profile picture uploads - show preview before upload
function initImagePreview() {
    const profileImageInput = document.querySelector('input[type="file"][name="profile_image"]');
    if (profileImageInput) {  // if file input exists
        profileImageInput.addEventListener('change', function(event) {
            const file = event.target.files[0];
            if (file) {  // if file selected
                const reader = new FileReader();  // read the file
                reader.onload = function(e) {
                    // Find existing preview or create new one
                    let preview = document.querySelector('.image-preview');
                    if (!preview) {  // make preview div if not exists
                        preview = document.createElement('div');
                        preview.className = 'image-preview';
                        profileImageInput.parentNode.appendChild(preview);
                    }
                    
                    preview.innerHTML = `  // show preview image
                        <p>New image preview:</p>
                        <img src="${e.target.result}" alt="Preview" style="width: 80px; height: 80px; border-radius: 50%; object-fit: cover; border: 2px solid var(--border-color);">
                    `;
                };
                reader.readAsDataURL(file);  // convert to data url for preview
            }
        });
    }
}

// Enhanced form validation - prevent bad data
function initFormValidation() {
    // Username confirmation validation - make sure they match
    const newUsernameInput = document.querySelector('input[name="new_username"]');
    const confirmUsernameInput = document.querySelector('input[name="confirm_username"]');
    
    if (newUsernameInput && confirmUsernameInput) {  // if both fields exist
        function validateUsernameMatch() {
            const newUsername = newUsernameInput.value;
            const confirmUsername = confirmUsernameInput.value;
            
            if (confirmUsername && newUsername !== confirmUsername) {  // check if they match
                confirmUsernameInput.setCustomValidity("Usernames don't match");
                showFieldError(confirmUsernameInput, "Usernames don't match");
            } else {
                confirmUsernameInput.setCustomValidity("");  // clear error
                clearFieldError(confirmUsernameInput);
            }
        }
        
        newUsernameInput.addEventListener('input', validateUsernameMatch);  // check on type
        confirmUsernameInput.addEventListener('input', validateUsernameMatch);
    }
    
    // Credit card validation - numbers only
    const lastFourInput = document.querySelector('input[name="last_four_digits"]');
    if (lastFourInput) {
        lastFourInput.addEventListener('input', function() {
            const value = this.value.replace(/\D/g, ''); // Remove non-digits
            this.value = value.substring(0, 4); // Limit to 4 digits max
            
            if (value.length < 4 && value.length > 0) {  // need exactly 4
                showFieldError(this, "Must be exactly 4 digits");
            } else {
                clearFieldError(this);
            }
        });
    }
    
    // Expiry date validation
    const expiryMonthInput = document.querySelector('input[name="expiry_month"]');
    const expiryYearInput = document.querySelector('input[name="expiry_year"]');
    
    if (expiryMonthInput && expiryYearInput) {
        function validateExpiryDate() {
            const month = parseInt(expiryMonthInput.value);
            const year = parseInt(expiryYearInput.value);
            const now = new Date();
            const currentMonth = now.getMonth() + 1;
            const currentYear = now.getFullYear();
            
            if (year < currentYear || (year === currentYear && month < currentMonth)) {
                showFieldError(expiryYearInput, "Card has expired");
            } else {
                clearFieldError(expiryYearInput);
            }
        }
        
        expiryMonthInput.addEventListener('change', validateExpiryDate);
        expiryYearInput.addEventListener('change', validateExpiryDate);
    }
}

// Payment method card interactions
function initPaymentMethodCards() {
    const paymentCards = document.querySelectorAll('.payment-method-card');
    
    paymentCards.forEach(card => {
        // Add hover effects and click animations
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
        
        // Handle primary badge clicks
        const primaryBadge = card.querySelector('.primary-badge');
        if (primaryBadge) {
            card.style.border = '2px solid var(--primary-color)';
        }
    });
}

// Confirmation dialogs for destructive actions
function initConfirmationDialogs() {
    // Delete payment method confirmation
    const deleteButtons = document.querySelectorAll('a[href*="delete_payment_method"]');
    
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            const cardType = this.closest('.payment-method-card')?.querySelector('.card-type')?.textContent || 'payment method';
            
            if (!confirm(`Are you sure you want to delete this ${cardType}? This action cannot be undone.`)) {
                event.preventDefault();
            }
        });
    });
    
    // Username change confirmation
    const usernameForm = document.querySelector('form[action*="change-username"]');
    if (usernameForm) {
        usernameForm.addEventListener('submit', function(event) {
            const newUsername = this.querySelector('input[name="new_username"]').value;
            
            if (!confirm(`Are you sure you want to change your username to "${newUsername}"? You won't be able to change it again for 6 months.`)) {
                event.preventDefault();
            }
        });
    }
}

// Profile dropdown menu functionality
function initProfileDropdown() {
    const profileButton = document.getElementById('profileButton');
    const profileDropdown = document.getElementById('profileDropdown');
    const dropdownContainer = document.querySelector('.profile-dropdown');
    
    if (profileButton && profileDropdown) {
        // Toggle dropdown on button click
        profileButton.addEventListener('click', function(e) {
            e.stopPropagation();
            toggleDropdown();
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {
            if (!dropdownContainer.contains(e.target)) {
                closeDropdown();
            }
        });
        
        // Close dropdown on escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeDropdown();
            }
        });
        
        // Handle dropdown item clicks
        const dropdownItems = profileDropdown.querySelectorAll('.dropdown-item');
        dropdownItems.forEach(item => {
            item.addEventListener('click', function() {
                // Add a small delay to show the click effect
                setTimeout(() => {
                    closeDropdown();
                }, 150);
            });
        });
    }
}

function toggleDropdown() {
    const profileDropdown = document.getElementById('profileDropdown');
    const dropdownContainer = document.querySelector('.profile-dropdown');
    
    if (profileDropdown.classList.contains('show')) {
        closeDropdown();
    } else {
        openDropdown();
    }
}

function openDropdown() {
    const profileDropdown = document.getElementById('profileDropdown');
    const dropdownContainer = document.querySelector('.profile-dropdown');
    
    profileDropdown.classList.add('show');
    dropdownContainer.classList.add('active');
}

function closeDropdown() {
    const profileDropdown = document.getElementById('profileDropdown');
    const dropdownContainer = document.querySelector('.profile-dropdown');
    
    profileDropdown.classList.remove('show');
    dropdownContainer.classList.remove('active');
}

// Helper functions for form validation
function showFieldError(field, message) {
    clearFieldError(field);
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'field-error';
    errorDiv.style.color = 'var(--error-color)';
    errorDiv.style.fontSize = '0.9rem';
    errorDiv.style.marginTop = '5px';
    errorDiv.textContent = message;
    
    field.parentNode.appendChild(errorDiv);
    field.style.borderColor = 'var(--error-color)';
}

function clearFieldError(field) {
    const existingError = field.parentNode.querySelector('.field-error');
    if (existingError) {
        existingError.remove();
    }
    field.style.borderColor = '';
}

// Toast notifications for success messages
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? 'var(--primary-color)' : 'var(--error-color)'};
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 1000;
        opacity: 0;
        transform: translateX(100%);
        transition: all 0.3s ease;
    `;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    // Animate in
    setTimeout(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateX(0)';
    }, 100);
    
    // Animate out after 3 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Auto-show toast if there's a success message in the page
document.addEventListener('DOMContentLoaded', function() {
    const alertSuccess = document.querySelector('.alert-success');
    if (alertSuccess) {
        const message = alertSuccess.textContent.trim();
        showToast(message, 'success');
        
        // Hide the original alert after showing toast
        setTimeout(() => {
            alertSuccess.style.opacity = '0';
            setTimeout(() => alertSuccess.style.display = 'none', 300);
        }, 500);
    }
});

// Export functions for use in other files
window.UserManagement = {
    showToast,
    showFieldError,
    clearFieldError
};
