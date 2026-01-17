// Game view JavaScript

let gameState = null;
let updateInterval = null;

// Suit symbols
const suitSymbols = {
    'H': '♥',
    'D': '♦',
    'C': '♣',
    'S': '♠'
};

// Initialize game
async function initGame() {
    await updateGameState();
    updateInterval = setInterval(updateGameState, 2000); // Update co 2 sekundy
    setupActionButtons();
}

// Fetch and update game state
async function updateGameState() {
    try {
        const response = await fetch(`/api/games/${gameId}/state`);
        const data = await response.json();
        gameState = data;
        renderGame();
    } catch (error) {
        console.error('Błąd pobierania stanu gry:', error);
    }
}

// Render game UI
function renderGame() {
    if (!gameState) return;

    // Update pot
    document.getElementById('potAmount').textContent = gameState.pot;
    
    // Update round info
    document.getElementById('roundInfo').textContent = gameState.current_round;
    
    // Render community cards
    renderCommunityCards();
    
    // Render players
    renderPlayers();
}

// Render community cards
function renderCommunityCards() {
    const container = document.getElementById('communityCards');
    container.innerHTML = '';
    
    if (gameState.community_cards && gameState.community_cards.length > 0) {
        gameState.community_cards.forEach((card, index) => {
            const cardElement = createCardElement(card);
            cardElement.style.animationDelay = `${index * 0.1}s`;
            container.appendChild(cardElement);
        });
    }
}

// Render players
function renderPlayers() {
    const container = document.getElementById('playersContainer');
    container.innerHTML = '';
    
    gameState.players.forEach((player, index) => {
        const playerElement = createPlayerElement(player, index);
        container.appendChild(playerElement);
    });
}

// Create card element
function createCardElement(cardStr) {
    const card = document.createElement('div');
    card.className = 'card';
    
    if (!cardStr || cardStr === '') {
        card.className += ' card-back';
        card.textContent = '🂠';
        return card;
    }
    
    // Parse card (e.g., "AS" = Ace of Spades)
    let rank, suit;
    if (cardStr.length === 3) { // "10H"
        rank = cardStr.substring(0, 2);
        suit = cardStr[2];
    } else { // "AS"
        rank = cardStr[0];
        suit = cardStr[1];
    }
    
    const suitSymbol = suitSymbols[suit] || suit;
    const suitClass = getSuitClass(suit);
    
    card.className += ` ${suitClass}`;
    
    const rankDiv = document.createElement('div');
    rankDiv.className = 'card-rank';
    rankDiv.textContent = rank;
    
    const suitDiv = document.createElement('div');
    suitDiv.className = 'card-suit';
    suitDiv.textContent = suitSymbol;
    
    card.appendChild(rankDiv);
    card.appendChild(suitDiv);
    
    return card;
}

// Get suit class for card styling
function getSuitClass(suit) {
    if (suit === 'H') return 'hearts';
    if (suit === 'D') return 'diamonds';
    if (suit === 'C') return 'clubs';
    if (suit === 'S') return 'spades';
    return '';
}

// Create player element
function createPlayerElement(player, index) {
    const playerSeat = document.createElement('div');
    playerSeat.className = 'player-seat';
    
    const playerInfo = document.createElement('div');
    playerInfo.className = 'player-info';
    
    // Add active class if it's this player's turn
    const isActive = gameState.status === 'playing' && 
                     index === gameState.current_player_idx;
    if (isActive && !player.folded) {
        playerInfo.classList.add('active');
    }
    
    if (player.folded) {
        playerInfo.classList.add('folded');
    }
    
    // Player name
    const nameDiv = document.createElement('div');
    nameDiv.className = 'player-name';
    nameDiv.textContent = player.name;
    if (player.all_in) {
        nameDiv.textContent += ' (ALL-IN)';
    }
    playerInfo.appendChild(nameDiv);
    
    // Player chips
    const chipsDiv = document.createElement('div');
    chipsDiv.className = 'player-chips';
    chipsDiv.textContent = `💰 ${player.chips}`;
    playerInfo.appendChild(chipsDiv);
    
    // Player bet
    if (player.current_bet > 0) {
        const betDiv = document.createElement('div');
        betDiv.className = 'player-bet';
        betDiv.textContent = `Bet: ${player.current_bet}`;
        playerInfo.appendChild(betDiv);
    }
    
    // Player cards (only show if they belong to current user)
    if (player.cards && player.cards.length > 0) {
        const cardsDiv = document.createElement('div');
        cardsDiv.className = 'player-cards';
        player.cards.forEach(card => {
            const cardElement = createCardElement(card);
            cardsDiv.appendChild(cardElement);
        });
        playerInfo.appendChild(cardsDiv);
    }
    
    playerSeat.appendChild(playerInfo);
    return playerSeat;
}

// Setup action buttons
function setupActionButtons() {
    const startGameBtn = document.getElementById('startGameBtn');
    if (startGameBtn) {
        startGameBtn.addEventListener('click', startGame);
    }
    
    const actionButtons = document.querySelectorAll('.action-btn');
    actionButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const action = btn.dataset.action;
            if (action === 'raise') {
                const amount = parseInt(document.getElementById('raiseAmount').value);
                if (!amount || amount <= 0) {
                    alert('Podaj prawidłową kwotę');
                    return;
                }
                makeAction(action, amount);
            } else {
                makeAction(action, 0);
            }
        });
    });
}

// Start game
async function startGame() {
    try {
        const response = await fetch(`/api/games/${gameId}/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (data.success) {
            await updateGameState();
        } else {
            alert('Błąd rozpoczynania gry: ' + (data.error || 'Nieznany błąd'));
        }
    } catch (error) {
        alert('Błąd połączenia z serwerem');
    }
}

// Make action
async function makeAction(action, amount) {
    try {
        const response = await fetch(`/api/games/${gameId}/action`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action, amount })
        });
        
        const data = await response.json();
        
        if (data.success) {
            await updateGameState();
            // Add to log
            addLogEntry(`Wykonano akcję: ${action}`);
        } else {
            alert('Błąd wykonywania akcji: ' + (data.error || 'Nieznany błąd'));
        }
    } catch (error) {
        alert('Błąd połączenia z serwerem');
    }
}

// Add log entry
function addLogEntry(message) {
    const logEntries = document.getElementById('logEntries');
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    const time = new Date().toLocaleTimeString();
    entry.textContent = `[${time}] ${message}`;
    logEntries.insertBefore(entry, logEntries.firstChild);
    
    // Keep only last 10 entries
    while (logEntries.children.length > 10) {
        logEntries.removeChild(logEntries.lastChild);
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', initGame);

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (updateInterval) {
        clearInterval(updateInterval);
    }
});
