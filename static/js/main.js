// Main page JavaScript

// Modal handling
const createGameModal = document.getElementById('createGameModal');
const createGameBtn = document.getElementById('createGameBtn');
const closeModal = document.querySelector('.close');

if (createGameBtn) {
    createGameBtn.onclick = () => {
        createGameModal.style.display = 'block';
    };
}

if (closeModal) {
    closeModal.onclick = () => {
        createGameModal.style.display = 'none';
    };
}

window.onclick = (event) => {
    if (event.target === createGameModal) {
        createGameModal.style.display = 'none';
    }
};

// Create game form
const createGameForm = document.getElementById('createGameForm');
if (createGameForm) {
    createGameForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const gameName = document.getElementById('gameName').value;

        try {
            const response = await fetch('/api/games/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: gameName })
            });

            const data = await response.json();

            if (data.success) {
                window.location.href = `/game/${data.game_id}`;
            } else {
                alert('Błąd tworzenia gry: ' + (data.error || 'Nieznany błąd'));
            }
        } catch (error) {
            alert('Błąd połączenia z serwerem');
        }
    });
}

// Join game buttons
const joinGameButtons = document.querySelectorAll('.join-game-btn');
joinGameButtons.forEach(btn => {
    btn.addEventListener('click', async () => {
        const gameId = btn.dataset.gameId;

        try {
            const response = await fetch(`/api/games/${gameId}/join`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            const data = await response.json();

            if (data.success) {
                window.location.href = `/game/${gameId}`;
            } else {
                alert('Błąd dołączania do gry: ' + (data.error || 'Nieznany błąd'));
            }
        } catch (error) {
            alert('Błąd połączenia z serwerem');
        }
    });
});

// Auto-refresh games list
setInterval(() => {
    location.reload();
}, 30000); // Refresh co 30 sekund
