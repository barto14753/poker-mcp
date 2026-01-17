// Bots management JavaScript

// Modal handling
const createBotModal = document.getElementById('createBotModal');
const createBotBtn = document.getElementById('createBotBtn');
const closeModal = document.querySelector('.close');

if (createBotBtn) {
    createBotBtn.onclick = () => {
        createBotModal.style.display = 'block';
    };
}

if (closeModal) {
    closeModal.onclick = () => {
        createBotModal.style.display = 'none';
    };
}

window.onclick = (event) => {
    if (event.target === createBotModal) {
        createBotModal.style.display = 'none';
    }
};

// Create bot form
const createBotForm = document.getElementById('createBotForm');
if (createBotForm) {
    createBotForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const botName = document.getElementById('botName').value;

        try {
            const response = await fetch('/api/bots/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: botName })
            });

            const data = await response.json();

            if (data.success) {
                location.reload();
            } else {
                alert('Błąd tworzenia bota: ' + (data.error || 'Nieznany błąd'));
            }
        } catch (error) {
            alert('Błąd połączenia z serwerem');
        }
    });
}

// Copy API key buttons
const copyButtons = document.querySelectorAll('.copy-btn');
copyButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        const apiKey = btn.dataset.key;
        navigator.clipboard.writeText(apiKey).then(() => {
            const originalText = btn.textContent;
            btn.textContent = 'Skopiowano!';
            setTimeout(() => {
                btn.textContent = originalText;
            }, 2000);
        });
    });
});
