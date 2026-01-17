from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import secrets
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///poker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Modele bazy danych
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Bot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    api_key = db.Column(db.String(64), unique=True, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    active = db.Column(db.Boolean, default=True)
    
    owner = db.relationship('User', backref='bots')

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='waiting')  # waiting, playing, finished
    current_round = db.Column(db.String(20), default='preflop')  # preflop, flop, turn, river
    pot = db.Column(db.Integer, default=0)
    community_cards = db.Column(db.String(50), default='')
    current_bet = db.Column(db.Integer, default=0)
    current_player_idx = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    creator = db.relationship('User', backref='created_games')

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    bot_id = db.Column(db.Integer, db.ForeignKey('bot.id'), nullable=True)
    position = db.Column(db.Integer, nullable=False)
    chips = db.Column(db.Integer, default=1000)
    current_bet = db.Column(db.Integer, default=0)
    cards = db.Column(db.String(20), default='')  # np. "AS,KH"
    folded = db.Column(db.Boolean, default=False)
    all_in = db.Column(db.Boolean, default=False)
    
    game = db.relationship('Game', backref='players')
    user = db.relationship('User', backref='player_games')
    bot = db.relationship('Bot', backref='player_games')
    
    @property
    def name(self):
        if self.user_id:
            return User.query.get(self.user_id).username
        elif self.bot_id:
            return Bot.query.get(self.bot_id).name
        return "Unknown"

class GameAction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=False)
    action = db.Column(db.String(20), nullable=False)  # fold, call, raise, check, all_in
    amount = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    game = db.relationship('Game', backref='actions')
    player = db.relationship('Player')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# API Key authentication helper
def authenticate_bot():
    """Authenticate bot using API key from header"""
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        return None
    
    bot = Bot.query.filter_by(api_key=api_key, active=True).first()
    return bot

def login_required_or_bot(f):
    """Decorator that allows either logged in user or valid bot API key"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Try bot authentication first
        bot = authenticate_bot()
        if bot:
            request.bot = bot
            return f(*args, **kwargs)
        
        # Fall back to regular login
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function

# Routes
@app.route('/')
def index():
    games = Game.query.order_by(Game.created_at.desc()).all()
    bots = Bot.query.filter_by(active=True).all()
    return render_template('index.html', games=games, bots=bots)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 400
        
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return jsonify({'success': True, 'username': username})
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return jsonify({'success': True, 'username': username})
        
        return jsonify({'error': 'Invalid credentials'}), 401
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/bots')
@login_required
def bots():
    user_bots = Bot.query.filter_by(owner_id=current_user.id).all()
    return render_template('bots.html', bots=user_bots)

@app.route('/api/bots/create', methods=['POST'])
@login_required
def create_bot():
    data = request.get_json()
    name = data.get('name')
    
    if Bot.query.filter_by(name=name).first():
        return jsonify({'error': 'Bot name already exists'}), 400
    
    api_key = secrets.token_urlsafe(32)
    bot = Bot(name=name, api_key=api_key, owner_id=current_user.id)
    db.session.add(bot)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'bot_id': bot.id,
        'name': bot.name,
        'api_key': bot.api_key
    })

@app.route('/api/games/list', methods=['GET'])
def list_games():
    """List all games - public endpoint for MCP"""
    games = Game.query.order_by(Game.created_at.desc()).all()
    games_data = []
    
    for game in games:
        players_count = Player.query.filter_by(game_id=game.id).count()
        games_data.append({
            'id': game.id,
            'name': game.name,
            'status': game.status,
            'pot': game.pot,
            'players_count': players_count,
            'created_at': game.created_at.isoformat()
        })
    
    return jsonify({'games': games_data})

@app.route('/api/games/create', methods=['POST'])
@login_required_or_bot
def create_game():
    data = request.get_json()
    
    # Check if it's a bot or user
    if hasattr(request, 'bot') and request.bot:
        creator_id = request.bot.owner_id
        name = data.get('name', f'Game by {request.bot.name}')
        creator_type = 'bot'
        creator_entity_id = request.bot.id
    else:
        creator_id = current_user.id
        name = data.get('name', f'Game by {current_user.username}')
        creator_type = 'user'
        creator_entity_id = current_user.id
    
    game = Game(name=name, creator_id=creator_id)
    db.session.add(game)
    db.session.commit()
    
    # Creator joins automatically
    if creator_type == 'bot':
        player = Player(
            game_id=game.id,
            bot_id=creator_entity_id,
            position=0,
            chips=1000
        )
    else:
        player = Player(
            game_id=game.id,
            user_id=creator_entity_id,
            position=0,
            chips=1000
        )
    db.session.add(player)
    db.session.commit()
    
    return jsonify({'success': True, 'game_id': game.id})

@app.route('/api/games/<int:game_id>/join', methods=['POST'])
@login_required_or_bot
def join_game(game_id):
    game = Game.query.get_or_404(game_id)
    
    if game.status != 'waiting':
        return jsonify({'error': 'Game already started'}), 400
    
    # Check if it's a bot or user
    if hasattr(request, 'bot') and request.bot:
        # Check if bot already joined
        existing = Player.query.filter_by(game_id=game_id, bot_id=request.bot.id).first()
        if existing:
            return jsonify({'error': 'Already joined'}), 400
        
        entity_id = request.bot.id
        entity_type = 'bot'
    else:
        # Check if user already joined
        existing = Player.query.filter_by(game_id=game_id, user_id=current_user.id).first()
        if existing:
            return jsonify({'error': 'Already joined'}), 400
        
        entity_id = current_user.id
        entity_type = 'user'
    
    # Get next position
    max_pos = db.session.query(db.func.max(Player.position)).filter_by(game_id=game_id).scalar() or -1
    
    if entity_type == 'bot':
        player = Player(
            game_id=game_id,
            bot_id=entity_id,
            position=max_pos + 1,
            chips=1000
        )
    else:
        player = Player(
            game_id=game_id,
            user_id=entity_id,
            position=max_pos + 1,
            chips=1000
        )
    db.session.add(player)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/game/<int:game_id>')
def game(game_id):
    game = Game.query.get_or_404(game_id)
    return render_template('game.html', game=game)

@app.route('/api/games/<int:game_id>/state')
def game_state(game_id):
    game = Game.query.get_or_404(game_id)
    players = Player.query.filter_by(game_id=game_id).order_by(Player.position).all()
    
    players_data = []
    for p in players:
        player_data = {
            'id': p.id,
            'name': p.name,
            'position': p.position,
            'chips': p.chips,
            'current_bet': p.current_bet,
            'folded': p.folded,
            'all_in': p.all_in,
            'cards': p.cards.split(',') if p.cards and (current_user.is_authenticated and p.user_id == current_user.id) else []
        }
        players_data.append(player_data)
    
    community_cards = game.community_cards.split(',') if game.community_cards else []
    
    return jsonify({
        'id': game.id,
        'name': game.name,
        'status': game.status,
        'pot': game.pot,
        'current_bet': game.current_bet,
        'current_player_idx': game.current_player_idx,
        'community_cards': community_cards,
        'current_round': game.current_round,
        'players': players_data
    })

@app.route('/api/games/<int:game_id>/start', methods=['POST'])
@login_required_or_bot
def start_game(game_id):
    game = Game.query.get_or_404(game_id)
    
    # Check if requester is the creator (user or bot)
    is_creator = False
    if hasattr(request, 'bot') and request.bot:
        # Check if bot is creator
        creator_player = Player.query.filter_by(game_id=game_id, position=0, bot_id=request.bot.id).first()
        is_creator = creator_player is not None
    else:
        is_creator = game.creator_id == current_user.id
    
    if not is_creator:
        return jsonify({'error': 'Only creator can start'}), 403
    
    if game.status != 'waiting':
        return jsonify({'error': 'Game already started'}), 400
    
    players_list = Player.query.filter_by(game_id=game_id).order_by(Player.position).all()
    if len(players_list) < 2:
        return jsonify({'error': 'Need at least 2 players'}), 400
    
    game.status = 'playing'
    db.session.commit()
    
    # Import poker logic and deal cards
    from poker_logic import deal_cards
    deal_cards(db, game, players_list)
    
    return jsonify({'success': True})

@app.route('/api/games/<int:game_id>/action', methods=['POST'])
@login_required_or_bot
def game_action(game_id):
    data = request.get_json()
    action = data.get('action')
    amount = data.get('amount', 0)
    
    game = Game.query.get_or_404(game_id)
    
    # Find player based on bot or user
    if hasattr(request, 'bot') and request.bot:
        player = Player.query.filter_by(game_id=game_id, bot_id=request.bot.id).first()
    else:
        player = Player.query.filter_by(game_id=game_id, user_id=current_user.id).first()
    
    if not player:
        return jsonify({'error': 'Not in this game'}), 403
    
    # Get all players in game
    players_list = Player.query.filter_by(game_id=game_id).order_by(Player.position).all()
    
    # Import poker logic
    from poker_logic import process_action
    result = process_action(db, game, player, players_list, GameAction, action, amount)
    
    if result.get('error'):
        return jsonify(result), 400
    
    return jsonify({'success': True})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5001)
