document.addEventListener('DOMContentLoaded', () => {

    // Mobile Menu Toggle
    const menuBtn = document.getElementById('mobile-menu-btn');
    const mobileMenu = document.getElementById('mobile-menu');
    if (menuBtn && mobileMenu) {
        menuBtn.addEventListener('click', () => {
            mobileMenu.classList.toggle('hidden');
        });
    }

    // Dismiss Flash Messages
    const dismissBtns = document.querySelectorAll('.dismiss-flash');
    dismissBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.target.closest('.flash-banner').style.display = 'none';
        });
    });

    // Remove flash messages after 5 seconds
    setTimeout(() => {
        const flashes = document.querySelectorAll('.flash-banner');
        flashes.forEach(flash => flash.style.opacity = '0');
        setTimeout(() => flashes.forEach(flash => flash.remove()), 500);
    }, 5000);

    // Vote Logic
    const voteBtns = document.querySelectorAll('.vote-btn');
    voteBtns.forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            const issueId = btn.dataset.issueId;
            try {
                const res = await fetch(`/issues/${issueId}/vote`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({}) // Assuming session user handling
                });
                
                const data = await res.json();
                if (res.ok) {
                    const countSpan = document.getElementById(`vote-count-${issueId}`);
                    countSpan.innerText = data.issue.votes;
                    
                    const icon = btn.querySelector('i');
                    if (data.message === 'Vote cast') {
                        icon.classList.remove('text-gray-400');
                        icon.classList.add('text-red-500');
                        showToast(`Vote added! ❤️`, 'success');
                    } else if (data.message === 'Vote removed') {
                        icon.classList.remove('text-red-500');
                        icon.classList.add('text-gray-400');
                        showToast(`Vote removed.`, 'info');
                    }
                } else {
                    if (res.status === 401) {
                        window.location.href = "/login";
                    } else {
                        showToast(data.error || 'Failed to vote', 'error');
                    }
                }
            } catch (err) {
                console.error(err);
            }
        });
    });

    // Animated Counters for Stats
    const counters = document.querySelectorAll('.count-up');
    const speed = 200; 
    counters.forEach(counter => {
        const updateCount = () => {
            const target = +counter.getAttribute('data-target');
            const count = +counter.innerText;
            const inc = target / speed;
            if (count < target) {
                counter.innerText = Math.ceil(count + inc);
                setTimeout(updateCount, 10);
            } else {
                counter.innerText = target;
            }
        };
        updateCount();
    });
});

function showToast(message, type) {
    const toastElem = document.getElementById('toast');
    if (!toastElem) return;
    
    document.getElementById('toast-msg').innerText = message;
    
    // reset classes
    const icon = document.getElementById('toast-icon');
    icon.className = 'fas fa-info-circle text-blue-500';

    if (type === 'success') {
        icon.className = 'fas fa-check-circle text-green-500';
    } else if (type === 'error') {
        icon.className = 'fas fa-exclamation-circle text-red-500';
    }

    toastElem.classList.add('show');
    setTimeout(() => toastElem.classList.remove('show'), 3000);
}
