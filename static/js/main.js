// JS UTAMA HALAMAN

document.addEventListener('DOMContentLoaded', function() {
    const body = document.body;

    const sidebar = document.getElementById('optionsSidebar');
    const toggleBtn = document.getElementById('sidebar-main-toggle');

    if (sidebar && toggleBtn) {
        const toggleIcon = toggleBtn.querySelector('i');

        function updateSidebarToggleIcon() {
            if (body.classList.contains('sidebar-hidden')) {
                toggleIcon.classList.remove('fa-chevron-right');
                toggleIcon.classList.add('fa-chevron-left');
                toggleBtn.title = "Tampilkan Opsi";
            } else {
                toggleIcon.classList.remove('fa-chevron-left');
                toggleIcon.classList.add('fa-chevron-right');
                toggleBtn.title = "Sembunyikan Opsi";
            }
        }
        
        updateSidebarToggleIcon();

        toggleBtn.addEventListener('click', () => {
            body.classList.toggle('sidebar-hidden');
            const isHidden = body.classList.contains('sidebar-hidden');
            localStorage.setItem('sidebarHidden', isHidden); 
            updateSidebarToggleIcon();
        });
        
        if (localStorage.getItem('sidebarHidden') === 'true') {
            body.classList.add('sidebar-hidden');
        } else {
            body.classList.remove('sidebar-hidden');
        }
        updateSidebarToggleIcon();
    }

    const mainTextarea = document.getElementById('mainTextarea');
    const tokenCountSpan = document.getElementById('tokenCount');
    const tokenDisplayDiv = document.getElementById('tokenDisplay');
    const submitBtn = document.getElementById('submitBtn');
    const navBurgerBtn = document.getElementById('navBurgerBtn');
    const navMenuWrapper = document.getElementById('navMenuWrapper');
    const burgerIcon = document.getElementById('burgerIcon');
    
    if (navBurgerBtn && navMenuWrapper) {
        navBurgerBtn.addEventListener('click', () => {
            const isActive = navMenuWrapper.classList.toggle('active');
            navBurgerBtn.setAttribute('aria-expanded', isActive);
            if (isActive) {
                burgerIcon.classList.remove('fa-bars');
                burgerIcon.classList.add('fa-times');
            } else {
                burgerIcon.classList.remove('fa-times');
                burgerIcon.classList.add('fa-bars');
            }
        });
    }

    function debounce(func, delay) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), delay);
        };
    }

    const updateTokenCount = async () => {
        if (!mainTextarea || !tokenCountSpan) return;
        const text = mainTextarea.value;
        if (text.trim() === '') {
            tokenCountSpan.textContent = '0';
            if (tokenDisplayDiv) tokenDisplayDiv.style.borderColor = 'var(--border-color)';
            if (submitBtn) submitBtn.disabled = true;
            return;
        }
        if (submitBtn) submitBtn.disabled = false;

        try {
            const response = await fetch('/api/count_tokens', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text })
            });
            if (!response.ok) { tokenCountSpan.textContent = 'Error'; return; }
            const data = await response.json();
            if (data.token_count !== undefined) {
                const count = data.token_count;
                tokenCountSpan.textContent = count.toLocaleString('id-ID');
                if (tokenDisplayDiv) tokenDisplayDiv.style.borderColor = count > 45000 ? 'var(--error-text-color)' : 'var(--border-color)';
            }
        } catch (error) {
            tokenCountSpan.textContent = 'Error';
        }
    };

    if (mainTextarea) {
        const autoGrowTextarea = () => {
            mainTextarea.style.height = 'auto';
            mainTextarea.style.height = (mainTextarea.scrollHeight) + 'px';
        };
        mainTextarea.addEventListener('input', () => {
            debounce(updateTokenCount, 500)();
            autoGrowTextarea();
        });
        updateTokenCount();
        autoGrowTextarea();
    }
});
