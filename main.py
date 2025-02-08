from settings import deck, USER_DATA_FILE
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
import telebot
import random
import json
import os
import time


load_dotenv("token.env")
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    print("❌ Не вдалося завантажити TOKEN!")
    exit(1)
else:
    bot = telebot.TeleBot(TOKEN)


# Store game states
games = {}


# Load user data
def load_users():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r") as file:
            return json.load(file)
    return {}


# Save user data
def save_users(users):
    with open(USER_DATA_FILE, "w") as file:
        json.dump(users, file, indent=4)


# Check if user registered
def is_registered(user_id):
    users = load_users()
    return str(user_id) in users


# Register a new user
@bot.message_handler(commands=['start'])
def register_user(message):
    user_id = str(message.chat.id)
    users = load_users()

    if user_id in users:
        bot.send_message(message.chat.id, f"👋 Welcome back, {users[user_id]['username']}!\n Your balance: 💰 {users[user_id]['balance']} $.\n/play")

    else:
        users[user_id] = {
            "username": message.from_user.username or f"User{user_id}",
            "balance": 1000  # Starting balance
        }
        save_users(users)
        bot.send_message(message.chat.id, f"✅ Registration successful!\n🎰 Welcome, {users[user_id]['username']}!\n💰 You start with **1000 $**.\n/play")


# Show user balance
@bot.message_handler(commands=['balance'])
def check_balance(message):
    user_id = str(message.chat.id)
    users = load_users()

    if user_id in users:
        bot.send_message(message.chat.id, f"💰 Your balance: **{users[user_id]['balance']} $**")
    else:
        bot.send_message(message.chat.id, "⚠ You are not registered. Type /start to sign up!")


# Play Command
@bot.message_handler(commands=['play'])
def play(message):
    bot.send_message(message.chat.id, "Choose a game: \n🎲 /dice, \n🎰 /roulette, \n🃏 /blackjack")


@bot.message_handler(commands=['dice'])
def start_dice_game(message):
    user_id = str(message.chat.id)
    bot.send_message(user_id, "💸 Enter your bet amount:")
    bot.register_next_step_handler(message, get_dice_bet_amount)


def get_dice_bet_amount(message):
    user_id = str(message.chat.id)
    users = load_users()

    try:
        bet_amount = int(message.text)
        if bet_amount <= 0:
            raise ValueError
    except ValueError:
        bot.send_message(user_id, "❌ Invalid bet amount. Enter a positive number.")
        return

    if bet_amount > users[user_id]["balance"]:
        bot.send_message(user_id, "💰 Insufficient funds! Check your balance with /balance.")
        return

    users[user_id]["bet"] = bet_amount
    save_users(users)

    markup = InlineKeyboardMarkup()
    for i in range(1, 7):
        markup.add(InlineKeyboardButton(f"🎲 {i}", callback_data=f"dice_{i}_{bet_amount}"))

    bot.send_message(user_id, "🎲 Choose a number (1-6):", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("dice_"))
def roll_dice(call):
    user_id = str(call.message.chat.id)
    users = load_users()

    data = call.data.split("_")
    chosen_number = int(data[1])
    bet_amount = int(data[2])

    rolled_number = random.randint(1, 6)

    time.sleep(1)
    bot.send_message(user_id, f"🎲 The dice rolled **{rolled_number}**!\n Your number **{chosen_number}**")
    time.sleep(1)

    if chosen_number == rolled_number:
        winnings = bet_amount * 6
        users[user_id]["balance"] += winnings
        bot.send_message(user_id, f"🏆 You won **${winnings}**! 🎉\n💰 New balance: **${users[user_id]['balance']}**\n /dice")
    else:
        users[user_id]["balance"] -= bet_amount
        bot.send_message(user_id, f"💔 You lost **${bet_amount}**.\n💰 New balance: **${users[user_id]['balance']}**\n /dice")

    save_users(users)


# Handle bet input
@bot.message_handler(commands=['roulette'])
def process_roulette_bet(message):
    user_id = str(message.chat.id)
    bot.send_message(user_id, "🎰 Enter your bet amount in $:")

    bot.register_next_step_handler(message, get_bet_amount)


def get_bet_amount(message):
    user_id = str(message.chat.id)
    users = load_users()

    try:
        bet_amount = int(message.text)
        if bet_amount <= 0:
            raise ValueError
    except ValueError:
        bot.send_message(user_id, "❌ Invalid bet amount. Enter a positive number.")
        return

    if bet_amount > users[user_id]["balance"]:
        bot.send_message(user_id, "💰 Insufficient funds! Check your balance with /balance.")
        return

    # Ask user to choose Red, Black, or a Number
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🔴 Red", callback_data=f"bet_red_{bet_amount}"),
        InlineKeyboardButton("⚫ Black", callback_data=f"bet_black_{bet_amount}"),
        InlineKeyboardButton("🔢 Number", callback_data=f"bet_number_{bet_amount}")
    )

    bot.send_message(user_id, "🎡 Choose your bet:", reply_markup=markup)


# Handle bet choices
@bot.callback_query_handler(func=lambda call: call.data.startswith("bet_"))
def save_roulette_bet(call):
    user_id = str(call.message.chat.id)
    users = load_users()

    data = call.data.split("_")
    bet_type = data[1]  # "red", black, or number
    bet_amount = int(data[2])

    if bet_type == "number":
        bot.send_message(user_id, "🔢 Enter a number between 0 and 36:")
        bot.register_next_step_handler(call.message, get_number_bet, bet_amount)
    else:
        users[user_id]["roulette_bet"] = bet_type  # Save color bet
        users[user_id]["bet"] = bet_amount  # Save bet amount
        save_users(users)  # Save updated user data

        bot.send_message(user_id, f"🎰 Bet placed: **${bet_amount}** on {bet_type.upper()}!\n🎡 Spinning the wheel...")
        roll_roulette(user_id)


def get_number_bet(message, bet_amount):
    user_id = str(message.chat.id)
    users = load_users()

    try:
        number_bet = int(message.text)
        if number_bet < 0 or number_bet > 36:
            raise ValueError
    except ValueError:
        bot.send_message(user_id, "❌ Invalid number. Please enter a number between 0 and 36.")
        return

    users[user_id]["roulette_bet"] = number_bet  # Save number bet
    users[user_id]["bet"] = bet_amount  # Save bet amount
    save_users(users)  # Save updated user data

    bot.send_message(user_id, f"🎰 Bet placed: **${bet_amount}** on number **{number_bet}**!\n🎡 Spinning the wheel...")
    roll_roulette(user_id)


# Function to roll the roulette
def roll_roulette(user_id):
    users = load_users()

    winning_number = random.randint(0, 36)
    winning_color = "red" if winning_number % 2 == 1 else "black"
    if winning_number == 0:
        winning_color = "green"

    bet_amount = users[user_id]["bet"]
    chosen_bet = users[user_id]["roulette_bet"]
    # bot.send_message(user_id, '🎰')
    time.sleep(1.5)
    bot.send_message(user_id, f"🎲 The wheel landed on \n**{winning_number} ({winning_color.upper()})**!")
    time.sleep(0.5)

    if isinstance(chosen_bet, int):  # Number bet
        if chosen_bet == winning_number:
            winnings = bet_amount * 35
            users[user_id]["balance"] += winnings
            bot.send_message(user_id, f"🏆 You won **${winnings}**! 🎉\n💰 New balance: **${users[user_id]['balance']}**")
        else:
            users[user_id]["balance"] -= bet_amount
            bot.send_message(user_id, f"💔 You lost **${bet_amount}**.\n💰 New balance: **${users[user_id]['balance']}**")

    elif chosen_bet == "red" or chosen_bet == "black":
        if winning_number == 0:  # Zero case (house wins)
            users[user_id]["balance"] -= bet_amount
            bot.send_message(user_id,
                             f"💔 The wheel landed on **0 (GREEN)**, house wins!\n💰 New balance: **${users[user_id]['balance']}**")
        elif chosen_bet == winning_color:
            winnings = bet_amount * 2
            users[user_id]["balance"] += winnings
            bot.send_message(user_id, f"🏆 You won **${winnings}**! 🎉\n💰 New balance: **${users[user_id]['balance']}**")
        else:
            users[user_id]["balance"] -= bet_amount
            bot.send_message(user_id, f"💔 You lost **${bet_amount}**.\n💰 New balance: **${users[user_id]['balance']}**")

    save_users(users)


# Check balance command
@bot.message_handler(commands=['balance'])
def check_balance(message):
    user_id = str(message.chat.id)
    users = load_users()
    bot.send_message(user_id, f"💰 Your balance: **${users[user_id]['balance']}**")


def draw_card():
    """Draw a random card"""
    card = random.choice(list(deck.keys()))
    value = deck[card]
    return card, value


def calculate_score(hand):
    """Calculate Blackjack hand score"""
    score = sum(hand)
    aces = hand.count(11)

    while score > 21 and aces:
        score -= 10  # Convert Ace from 11 to 1
        aces -= 1

    return score


@bot.message_handler(commands=['blackjack'])
def start_blackjack(message):
    """Ask user for bet amount"""
    user_id = str(message.chat.id)
    users = load_users()

    if user_id not in users:
        bot.send_message(message.chat.id, "⚠ You are not registered. Type /start to sign up!")
        return

    bot.send_message(message.chat.id, "♠️ Enter your bet amount in $:")
    bot.register_next_step_handler(message, process_blackjack_bet)


def process_blackjack_bet(message):
    """Check bet validity and start game"""
    user_id = str(message.chat.id)
    users = load_users()

    try:
        bet_amount = int(message.text)
        if bet_amount <= 0:
            raise ValueError
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid bet. Enter a positive number.")
        return

    if bet_amount > users[user_id]["balance"]:
        bot.send_message(message.chat.id, "💰 Insufficient funds! Check your balance with /balance.")
        return

    users[user_id]["bet"] = bet_amount
    save_users(users)

    play_blackjack(user_id)


def play_blackjack(user_id):
    """Start a Blackjack game"""
    player_hand = [draw_card()[1], draw_card()[1]]
    dealer_hand = [draw_card()[1]]

    games[user_id] = {"player": player_hand, "dealer": dealer_hand}

    send_blackjack_status(user_id)


def send_blackjack_status(user_id):
    """Send Blackjack game status with Hit/Stand buttons"""
    game = games[user_id]
    player_score = calculate_score(game["player"])
    dealer_card = game["dealer"][0]

    text = f"🃏 **Your hand:** {game['player']} (Total: {player_score})\n"
    text += f"🏦 **Dealer's hand:** [{dealer_card}, ?]"

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✋ Stand", callback_data=f"stand_{user_id}"),
        InlineKeyboardButton("🃏 Hit", callback_data=f"hit_{user_id}")
    )

    bot.send_message(user_id, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith(("hit_", "stand_")))
def process_blackjack_action(call):
    """Process Hit/Stand choices"""
    user_id = call.data.split("_")[1]

    if "hit" in call.data:
        _, value = draw_card()
        games[user_id]["player"].append(value)

        if calculate_score(games[user_id]["player"]) > 21:
            bot.send_message(user_id, f"💥 You busted!({games[user_id]['player']}) Dealer wins.\n /blackjack")
            # finish_blackjack(user_id, win=False)
            return

        send_blackjack_status(user_id)

    elif "stand" in call.data:
        dealer_turn(user_id)


def dealer_turn(user_id):
    """Dealer plays and game results decided"""
    game = games[user_id]
    users = load_users()
    bet_amount = users[user_id]["bet"]

    player_score = calculate_score(game["player"])
    dealer_hand = game["dealer"]

    while calculate_score(dealer_hand) < 17:
        _, value = draw_card()
        dealer_hand.append(value)

    dealer_score = calculate_score(dealer_hand)
    result = f"🃏 Your hand: **{player_score}**\n🏦 Dealer's hand: **{dealer_score}**\n"

    if dealer_score > 21 or player_score > dealer_score:
        winnings = bet_amount * (3 if player_score == 21 else 2)
        users[user_id]["balance"] += winnings
        result += f"🎉 You win **${winnings}**!\n /blackjack"
    elif dealer_score > player_score:
        users[user_id]["balance"] -= bet_amount
        result += f"😞 Dealer wins! You lost **${bet_amount}**.\n /blackjack"
    else:
        result += "😐 It's a tie. You get your bet back.\n /blackjack"

    save_users(users)
    bot.send_message(user_id, result)


bot.polling()
