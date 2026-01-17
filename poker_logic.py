import random
from itertools import combinations

# Karty i kolory
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
SUITS = ['H', 'D', 'C', 'S']  # Hearts, Diamonds, Clubs, Spades

def create_deck():
    """Tworzy talię kart"""
    return [f"{rank}{suit}" for rank in RANKS for suit in SUITS]

def deal_cards(db, game, players):
    """Rozdaje karty graczom na początku gry
    
    Args:
        db: SQLAlchemy database instance
        game: Game object
        players: List of Player objects ordered by position
    """
    
    deck = create_deck()
    random.shuffle(deck)
    
    # Każdy gracz dostaje 2 karty
    for player in players:
        player.cards = f"{deck.pop()},{deck.pop()}"
        player.folded = False
        player.current_bet = 0
    
    # Pozostałe karty w talii (do community cards)
    game.community_cards = ''
    game.current_round = 'preflop'
    game.pot = 0
    game.current_bet = 0
    game.current_player_idx = 0
    
    db.session.commit()
    
    return deck

def process_action(db, game, player, players, GameAction, action, amount=0):
    """Przetwarza akcję gracza
    
    Args:
        db: SQLAlchemy database instance
        game: Game object
        player: Player object (current player)
        players: List of all Player objects in game ordered by position
        GameAction: GameAction model class
        action: String action type
        amount: Optional bet amount
    """
    if game.status != 'playing':
        return {'error': 'Game not in progress'}
    
    # Sprawdź czy to tura tego gracza
    current_player = players[game.current_player_idx]
    if current_player.id != player.id:
        return {'error': 'Not your turn'}
    
    if player.folded:
        return {'error': 'Already folded'}
    
    # Przetworz akcję
    if action == 'fold':
        player.folded = True
        
    elif action == 'check':
        if game.current_bet > player.current_bet:
            return {'error': 'Cannot check, must call or raise'}
            
    elif action == 'call':
        call_amount = game.current_bet - player.current_bet
        if call_amount > player.chips:
            call_amount = player.chips
            player.all_in = True
        player.chips -= call_amount
        player.current_bet += call_amount
        game.pot += call_amount
        
    elif action == 'raise':
        if amount < game.current_bet * 2:
            return {'error': 'Raise must be at least double current bet'}
        
        raise_amount = amount - player.current_bet
        if raise_amount > player.chips:
            raise_amount = player.chips
            player.all_in = True
            
        player.chips -= raise_amount
        player.current_bet += raise_amount
        game.pot += raise_amount
        game.current_bet = player.current_bet
        
    elif action == 'all_in':
        all_in_amount = player.chips
        player.chips = 0
        player.current_bet += all_in_amount
        game.pot += all_in_amount
        if player.current_bet > game.current_bet:
            game.current_bet = player.current_bet
        player.all_in = True
    
    # Zapisz akcję
    game_action = GameAction(
        game_id=game.id,
        player_id=player.id,
        action=action,
        amount=amount
    )
    db.session.add(game_action)
    
    # Przejdź do następnego gracza
    next_player_idx = (game.current_player_idx + 1) % len(players)
    
    # Sprawdź czy runda się kończy
    active_players = [p for p in players if not p.folded]
    
    # Jeśli wszyscy spasowali oprócz jednego
    if len(active_players) == 1:
        end_game(db, game, active_players[0])
        db.session.commit()
        return {'success': True, 'game_ended': True}
    
    # Sprawdź czy wszyscy zagrali w tej rundzie
    all_acted = all(
        p.folded or p.all_in or p.current_bet == game.current_bet
        for p in players
    )
    
    if all_acted:
        # Przejdź do następnej rundy
        advance_round(db, game, players)
    else:
        game.current_player_idx = next_player_idx
    
    db.session.commit()
    return {'success': True}

def advance_round(db, game, players):
    """Przechodzi do następnej rundy gry
    
    Args:
        db: SQLAlchemy database instance
        game: Game object
        players: List of Player objects
    """
    
    # Reset current bets
    for player in players:
        player.current_bet = 0
    
    game.current_bet = 0
    game.current_player_idx = 0
    
    # Deal community cards
    if game.current_round == 'preflop':
        # Flop - 3 karty
        deck = create_deck()
        random.shuffle(deck)
        game.community_cards = f"{deck[0]},{deck[1]},{deck[2]}"
        game.current_round = 'flop'
        
    elif game.current_round == 'flop':
        # Turn - 1 karta
        deck = create_deck()
        random.shuffle(deck)
        cards = game.community_cards.split(',')
        cards.append(deck[0])
        game.community_cards = ','.join(cards)
        game.current_round = 'turn'
        
    elif game.current_round == 'turn':
        # River - 1 karta
        deck = create_deck()
        random.shuffle(deck)
        cards = game.community_cards.split(',')
        cards.append(deck[0])
        game.community_cards = ','.join(cards)
        game.current_round = 'river'
        
    elif game.current_round == 'river':
        # Showdown
        determine_winner(db, game, players)
        game.status = 'finished'

def determine_winner(db, game, players_in_game):
    """Określa zwycięzcę gry
    
    Args:
        db: SQLAlchemy database instance
        game: Game object
        players_in_game: List of all Player objects in game
    """
    # Filter only non-folded players
    players = [p for p in players_in_game if not p.folded]
    
    if len(players) == 1:
        winner = players[0]
    else:
        # Evaluate hands and determine winner
        best_player = None
        best_hand_rank = -1
        
        community_cards = game.community_cards.split(',')
        
        for player in players:
            player_cards = player.cards.split(',')
            all_cards = player_cards + community_cards
            hand_rank = evaluate_hand(all_cards)
            
            if hand_rank > best_hand_rank:
                best_hand_rank = hand_rank
                best_player = player
        
        winner = best_player
    
    # Przyznaj pot zwycięzcy
    if winner:
        winner.chips += game.pot
        game.pot = 0

def end_game(db, game, winner):
    """Kończy grę i przyznaje pot zwycięzcy
    
    Args:
        db: SQLAlchemy database instance
        game: Game object
        winner: Player object
    """
    winner.chips += game.pot
    game.pot = 0
    game.status = 'finished'

def evaluate_hand(cards):
    """
    Ocenia siłę ręki pokera (uproszczona wersja)
    Zwraca liczbę reprezentującą siłę ręki (wyższa = lepsza)
    """
    if len(cards) < 5:
        return 0
    
    # Konwertuj karty na rangi i kolory
    card_data = []
    for card in cards:
        if len(card) == 3:  # '10H'
            rank = card[:2]
            suit = card[2]
        else:  # 'AH'
            rank = card[0]
            suit = card[1]
        
        rank_value = RANKS.index(rank) if rank in RANKS else 0
        card_data.append((rank_value, suit))
    
    # Znajdź najlepszą 5-kartową kombinację
    best_rank = 0
    for combo in combinations(card_data, 5):
        rank = evaluate_five_cards(combo)
        if rank > best_rank:
            best_rank = rank
    
    return best_rank

def evaluate_five_cards(five_cards):
    """Ocenia konkretną 5-kartową rękę"""
    ranks = sorted([card[0] for card in five_cards], reverse=True)
    suits = [card[1] for card in five_cards]
    
    is_flush = len(set(suits)) == 1
    is_straight = (ranks[0] - ranks[4] == 4) and len(set(ranks)) == 5
    
    # Royal flush / Straight flush
    if is_straight and is_flush:
        if ranks[0] == RANKS.index('A'):  # Royal flush
            return 10000
        return 9000 + ranks[0]  # Straight flush
    
    # Four of a kind
    rank_counts = {}
    for rank in ranks:
        rank_counts[rank] = rank_counts.get(rank, 0) + 1
    
    if 4 in rank_counts.values():
        return 8000 + max(rank_counts.keys())
    
    # Full house
    if 3 in rank_counts.values() and 2 in rank_counts.values():
        return 7000 + max(rank_counts.keys())
    
    # Flush
    if is_flush:
        return 6000 + ranks[0]
    
    # Straight
    if is_straight:
        return 5000 + ranks[0]
    
    # Three of a kind
    if 3 in rank_counts.values():
        return 4000 + max(rank_counts.keys())
    
    # Two pair
    pairs = [rank for rank, count in rank_counts.items() if count == 2]
    if len(pairs) == 2:
        return 3000 + max(pairs)
    
    # One pair
    if len(pairs) == 1:
        return 2000 + pairs[0]
    
    # High card
    return 1000 + ranks[0]
