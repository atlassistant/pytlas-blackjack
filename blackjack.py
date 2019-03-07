import logging
from pytlas import intent, training, translations
import math
import random

class Card(object):
  def __init__(self, color, figure, value):
    self.color = color
    self.figure = figure
    self.value = value
    self.is_ace = False
    if self.figure == 'ace':
      self.is_ace = True

  def __str__(self):
    return '{0} of {1}'.format(self.figure, self.color)
  
  def answer(self, req):
    return req._('{0} of {1}').format(req._(self.figure), req._(self.color))

class Shoe(object):
  def __init__(self):
    self.figures = ['ace','2','3','4','5','6','7','8','9','10','jack','queen','king']
    self.colors = ['clubs','diamonds', 'hearts','spades']
    self.values = [1,2,3,4,5,6,7,8,9,10,10,10,10]
    self.cards = []
    
  def create(self, shoe_number):
    for _packet_index in range(shoe_number):
      for color in self.colors: 
        for index in range(0,len(self.figures)):                 
            value = self.values[index]
            figure = self.figures[index]
            card = Card(color, figure, value)
            self.cards.append(card)

  def shuffle(self):
    counter = len(self.cards)
    while counter > 0:
      index = random.randint(0, counter - 1)
      temp = self.cards[index]
      self.cards[index] = self.cards[counter - 1]
      self.cards[counter-1] = temp
      counter = counter - 1

  def draw(self):
    card = self.cards[0]
    self.cards = self.cards[-(len(self.cards)-1):]
    return card

class Hand(object):
  def __init__(self):
    self.cards = []

  def add(self, card):
    self.cards.append(card)

  def number_of_ace(self):
    number = 0
    for card in self.cards:
      if card.is_ace:
        number += 1
    return number

  def evaluate(self):
    value = 0
    for card in self.cards:
      if card.is_ace:
        fluid_value = value + 11
        if fluid_value > 21:
          fluid_value = value + 1
        value = fluid_value
      else:
        value += card.value
    return value

  def clear(self):
    self.cards = []

  def last(self):
    if len(self.cards) > 0:
      return self.cards[len(self.cards) - 1]
    else:
      return None

  def __str__(self):
    msg = ''
    delimiter = ""
    for card in self.cards:
      msg += delimiter + str(card)
      delimiter = ", "
    return msg
  
  def answer(self, req):
    msg = ''
    delimiter = ''
    for card in self.cards:
      msg += delimiter + card.answer(req)
      delimiter = ", "
    return msg

class Game(object):
  # game state
  START = 0
  NEW_TURN = 1
  BEGIN_OF_TURN = 2
  PLAYER_FIRST_ACTION = 3
  PLAYER_ACTIONS = 4
  DEALER_ACTIONS = 5
  END_OF_TURN = 6
  #player action
  HIT = 0
  STAND = 1
  DOUBLE = 2
  SPLIT = 3
  RETRY = 4
  INSURANCE = 6
  BET = 7
  HELP = 8

  def __init__(self):
    self.blackjack_odds = 3/2
    self.standard_odds = 1
    self.state = self.START 
    self.player_action = None
    self.player_bankroll = 100
    self.player_bet = 0
    self.player_double = False
    self.player_hit_counter = 0
    self.player_insurance = None
    self.number_of_packets = 1
    self.player_hand = Hand()
    self.dealer_hidden_card = None
    self.dealer_hand = Hand()
    self.shoe = Shoe()
    self._logger = logging.getLogger(self.__class__.__name__.lower())

  
  def start(self, req):
    self._logger.debug('start')   
    number_of_packets = 1
    try: 
      number_of_packets = int(req.intent.slot('number_of_packets').first().value)
    except:
      pass
    self.number_of_packets = number_of_packets
    self.shoe.create(self.number_of_packets)
    self.shoe.shuffle()
    req.agent.answer(req._('Welcome in blackjack game'))
    req.agent.answer(req._('A shoe containing {0} packets has been shuffled').format(number_of_packets))
    req.agent.answer(req._('You start with 100$  ships'))
    req.agent.answer(req._('Bet to start the turn'))
    self.player_bet = None
    self.player_action = None
    self.state = self.NEW_TURN
    return self

  def new_turn(self, req):        
    self._logger.debug('new_turn')
    self.player_double = False
    self.player_action_counter = 0
    self.player_insurance = None
    self.player_bet = None
    self.dealer_hidden_card = None
    if req.intent.slot('bet').first().value != None:
      try:
        self.player_bet = int(req.intent.slot('bet').first().value)    
      except:
        pass
    
    if not self.player_bet:
      return req.agent.ask('bet', req._('What is your bet?'))    
    self.player_bankroll -=  self.player_bet
    self.state = self.BEGIN_OF_TURN
    return self

  def begin_of_turn(self, req):
    self._logger.debug('begin_of_turn')
    self.player_hand.clear()
    self.dealer_hand.clear()
    
    try:
      self.player_hand.add(self.shoe.draw())
      self.player_hand.add(self.shoe.draw())
      self.dealer_hand.add(self.shoe.draw())
      self.dealer_hidden_card = self.shoe.draw()
    except:
      self.state = self.END_OF_TURN
      req.agent.answer(req._('No more card'))
      return req.agent.done()

    req.agent.answer(req._('You got a {0} and a {1}').format(req._(self.player_hand.cards[0]), req._(self.player_hand.cards[1])))
    req.agent.answer(req._('Dealer got a {0} and a face down card').format(req._(self.dealer_hand.cards[0])))
    self.state = self.PLAYER_FIRST_ACTION
    return req.agent.done()

  def player_first_action(self, req):
    self._logger.debug('player_first_action')
    if self.player_action == self.DOUBLE:
      self.player_double = True
      self.player_action = self.HIT        
    elif self.player_action == self.HIT or self.player_action == self.STAND:
      self.state = self.PLAYER_ACTIONS
    else:
      req.agent.answer(req._(en_help))
      return req.agent.done()
    return self

  def player_actions(self, req):
    self._logger.debug('player_actions')
    if self.player_action == self.HIT:
      try:
        self.player_hand.add(self.shoe.draw())
      except:
        self.state = self.END_OF_TURN
        req.agent.answer(req._('No more card'))
        return req.agent.done()

      self.player_hit_counter =  self.player_hit_counter + 1
      req.agent.answer(req._('Your got a {0}').format(req._(self.player_hand.last())))
      if  self.player_hand.evaluate() > 21:
        self.state = self.END_OF_TURN
      elif self.player_hand.evaluate() == 21 or (self.player_double and self.player_hit_counter >= 3):
        self.state = self.DEALER_ACTIONS
      else:
        return req.agent.done()
    elif self.player_action == self.STAND:
      self.state = self.DEALER_ACTIONS
    else:
      req.agent.answer(req._(en_help))
      return req.agent.done()
    return self
  
  def dealer_actions(self, req):
    self._logger.debug('dealer_actions')
    self.dealer_hand.add(self.dealer_hidden_card)
    self.dealer_hidden_card = None
    req.agent.answer(req._('Dealer hidden card is a {0}').format(req._(self.dealer_hand.last())))      
    while True:
      if self.dealer_hand.evaluate() > self.player_hand.evaluate() or self.dealer_hand.evaluate() > 17:
        self.state = self.END_OF_TURN
        return self
      try:
        self.dealer_hand.add(self.shoe.draw())
      except:
        self.state = self.END_OF_TURN
        req.agent.answer(req._('No more card'))
        return req.agent.done()

      req.agent.answer(req._('Dealer got a {0}').format(req._(self.dealer_hand.last())))      
      self._logger.info("Dealer hand : %i - Player hand : %i",self.dealer_hand.evaluate(), self.player_hand.evaluate(),exc_info = 0)

  def end_of_turn(self, req):
    self._logger.debug('end_of_turn')
    req.agent.answer(req._('Your hand contains : {0}').format(game.player_hand.answer(req)))
    req.agent.answer(req._('The dealer hand contains (only visible cards) : {0}').format(game.dealer_hand.answer(req)))
    if self.player_hand.evaluate() > 21:
      req.agent.answer(req._('Unfortunately! your hand is over 21. You lost'))
    elif self.dealer_hand.evaluate() > 21:
      req.agent.answer(req._('Congratulation! dealer hand is over 21. You won'))
      self.player_bankroll += self.player_bet * 2        
    elif self.player_hand.evaluate() == self.dealer_hand.evaluate():
      req.agent.answer(req._('Tie, no one won'))
    elif self.player_hand.evaluate() == 21:
      req.agent.answer(req._('Blackjack! You won'))
      self.player_bankroll += math.ceil(self.player_bet * 3/2)        
    elif self.player_hand.evaluate() > self.dealer_hand.evaluate():
      req.agent.answer(req._('Congratulation! You won.'))
      self.player_bankroll += self.player_bet * 2        
    elif self.player_hand.evaluate() < self.dealer_hand.evaluate():
      req.agent.answer(req._('Unfortunately! You lost'))
    else:
      req.agent.answer(req._('Tie'))

    if len(self.shoe.cards) == 0:
      req.agent.answer(req._('Shoe is empty'))
      req.agent.answer(req._('Create a new one'))
      self.shoe.create(self.number_of_packets)
      self.shoe.shuffle()

    req.agent.answer(req._('Bet for a new turn'))
    self.state = self.NEW_TURN
    return req.agent.done()


  def apply_rule(self, req):
    while(True):
      self._logger.info("apply rule %i", self.state,exc_info = 0)  
      if self.state == self.START:
        ret = self.start(req)
      elif self.state == self.NEW_TURN:
        ret = self.new_turn(req)
      elif self.state == self.BEGIN_OF_TURN:
        ret = self.begin_of_turn(req)
      elif self.state == self.PLAYER_FIRST_ACTION:
        ret = self.player_first_action(req)
      elif self.state == self.PLAYER_ACTIONS:
        ret = self.player_actions(req)
      if self.state == self.DEALER_ACTIONS:
        ret = self.dealer_actions(req)      
      if self.state == self.END_OF_TURN:
        ret = self.end_of_turn(req)   
      
      self._logger.info(ret)   
      if ret != self:
        return ret    

# This entity will be shared among training data since it's not language specific

en_help="""
Blackjack is a multiplayer card game where players play against one dealer. 
Players who want entering the game  bet. 
At the begin the dealer gives 2 cards face up to each player in game and take two cards one face down.
At any time if a player hand is exactly 21, he is doing a blackjack. He can reveive no more cards.
At any time if a player hand is over 21, he is busting and loose automatically. 
During their turns, players can
"double"  for  doubling their bet and receiving one last card. 
"hit" for receiving one more card
"stand" to stop receving card.
when all players finished 
The delear reveal his facedown card and draw until his hand reach 17.
If the player hand is over 21, he lost the turn and his bet.
If the player and dealer hand is of equal value, there is a tie and the player take his bet. 
If the player hand  21, he is doing "blackjack" and receive 3/2 times his bet as bonus.
If the player hand is over the dealer hand, he wins and receive 1 times his bet as bonus.
If the dealer hand is over 21, he is busting and the player wins, receiving 1 times the bet as bonus.
Other case the wins and the player loose his bet
Hand value is equal to the cards value sum. "Face card"value is 10. Ace card is a special card wich value is 11 when hand value can be less or equal to 21 or 1 in other case 
At any time, you can "See your hand", "See the dealer hand", "See your banckroll" or "Quit"
"""


@training('en')
def en_data(): return """
%[help_blackjack]
  how does blackjack skill work
  give me help on blackjack skill
  what is blackjack skill

%[play_blackjack]
  I want play blackjack
  let's play blackjack
  play blackjack with @[number_of_packets] packets

@[number_of_packets](type=number)
  1
  2
  3

%[blackjack/hit]
  hit
  hit me

%[blackjack/stand]
  stand

%[blackjack/double]
  double  

%[blackjack/bet]
  I bet @[bet]
  again
  On more time
  deal for @[bet]

@[bet](type=number)
  1
  2
  3

%[blackjack/show_player_hand]
  what is my hand
  seed my hand
  my hand
 
%[blackjack/show_dealer_hand]
  what is the dealer hand
  see dealer hand
  dealer hand
  
%[blackjack/bankroll]
  how many chips I have
  what is my bankroll
  bankroll

%[blackjack/quit]
  I quit

%[blackjack/help]
  give me some advice
  hints
"""

fr_help="""
Le blackjack est un jeu de carte de un à plusieurs joueurs qui jouent contre un donneur. 
Les  joueurs qui souhaitent jouer déposent un pari (par exemple "Je mise  2"). 
Le donneur ensuite distribue 2 cartes face ouverte à chaque joueur et prend  deux cartes dont une face cachée.
Si à un moment le joueurs totalise 21, il fait "blackjack" il ne peut recevoir de carte supplémentaire
Si à un moment le joueur dépasse 21, il saute et à automatiquement perdu
les joueurs ont la possibilités chacun leur tour de 
Soit "doubler" dans ce cas il une seule et dernière carte supplémentaire et double sa mise en cas de victoire 
Soit "tirer" dans ce cas il reçoit une carte supplémentaire
Soit "refuser" dans ce cas sa main est fait et il ne reçoit plus de carte supplémentaire. 
Ensuite le donneur revèle sa carte caché et tire jusqu'à obtenir au moins 17.
Si la main du joeur totalise plus de 21, il a perdu et perd sa mise
Si la main du  joueur et du donneur totalisent le même résultat il y a "égalité" tie et le joueur récupère sa mise
Si la main du joueur totalise 21, il fait "blackjack", il récupère une prime équivalente à  3/2 fois sa  mise
Si la main du joueur totalise plus de point que celle du donneur le joueur gagne et récupère une prime de 1 fois sa mise
Si la main du donneur depasse 21, il saute et le joueur gagne, il récupère une prime de 1 fois sa mise
Dans le cas contraire, il donneur gagne et le joeur perd sa mise 
Une main vaut la somme des valeurs des cartes qui la compose.
Les cartes valent leur valeur chiffrée sauf pour les "bûches" (valet, dame , roi) qui valent 10.
L'as est un peu spéciale, il vaut soit 1, soit 10 selon que la main depasse ou non 21. Ainsi As + 9 vaut 20, As + 9 + 2 vaut 12.
A tout moment, vous pouvez "Voir votre main", "Voir la main du donneur, "Voir votre mise de fond" ou "Quitter"
"""

@training('fr')
def fr_data(): return """
%[help_blackjack]
  quelles sont les rêgles du blackjack
  comment se joue le blackjack

%[play_blackjack]
  je veux joueur au blackjack
  jouer au blackjack avec @[number_of_packets] paquets
  lancer le blackjack

@[number_of_packets](type=number)
  1
  2
  3

%[blackjack/hit]
  hit
  tirer
  encore
  encore une

%[blackjack/stand]
  stand
  arrêter
  rester
  refuser


%[blackjack/double]
  double  
  doubler

%[blackjack/bet]
  je mise @[bet]
  nouvelle donne
  donner pour @[bet]


@[bet](type=number)
  1
  2
  3

%[blackjack/show_player_hand]
  quelle est ma main
  voir ma main
  ma main

%[blackjack/show_dealer_hand]
  quelle est la main du donneur
  voir la main du donneur
  main du donneur

%[blackjack/bankroll]
  combien de jeton me reste-t-il
  quelle est ma mise de fond
  voir ma mise de fond
  bankroll

%[blackjack/quit]
  quitter
  abandonner
  je quitte le jeu

%[blackjack/help]
  quelles sont les rêgles
  aide
  astuce
"""

@translations('fr')
def fr_translations(): return {
  en_help : fr_help,
  'Goodbye': 'Au revoir et à bientôt',
  'Welcome in blackjack game':'Bienvenue dans le jeu du Blackjack',
  'A shoe containing {0} packets has been shuffled' : 'Un sabot contenant {0} paquet(s) de carte vient d\'être battu',
  'You start with 100$  ships' : 'Vous commencez avec 100$ de jetons',
  'Bet to start the turn' : 'Miser pour commencer le jeu',
  'What is your bet?' : 'Qu\'elle est votre mise?',
  'No more card' : 'Plus de carte',
  'You got a {0} and a {1}': 'Vous avez reçu {0} et {1}',
  'Dealer got a {0} and a face down card':'Le donneur vient de recevoir {0} et une carte face cachée',
  'Your got a {0}': 'Vous avez reçu {0}',
  'Dealer hidden card is a {0}': 'La carte face cachée du donneur est {0}',
  'Dealer got a {0}':'Le donneur vient de recevoir {0}',
  'Unfortunately! your hand is over 21. You lost':'Malheureusement! Votre main dépasse 21. Vous avez perdu',
  'Congratulation! dealer hand is over 21. You won':'Félicitation! Le main du donneur dépasse 21. Vous avez gagné',
  'Tie, no one won':'Egalité, personne n\'est vainqueur.',
  'Blackjack! You won':'Blackjack! Vous avez gagné',
  'Congratulation! You won.':'Félicitation! Vous avez gagner',
  'Unfortunately! You lost':'Malheureusement! Vous avez perdu',
  'Tie' : 'Egalité',
  'Shoe is empty': 'Le sabot est vide',
  'Create a new one' : 'Remplissage d\'un nouveau sabot',
  'Bet for a new turn' : 'Misez pour jouer',
  'Your bankroll is {0} chips' : 'Votre mise de fond est {0} jeton(s)',
  'Your hand contains : {0}' : 'Votre main contient : {0}',
  'The dealer hand contains (only visible cards) : {0}' : 'La main du donneur contient (cartes visibles uniquement) : {0}',
  '{0} of {1}': '{0} de {1}',
  'ace':  'as',
  '2':'2',
  '3':'3',
  '4':'4',
  '5':'5',
  '6':'6',
  '7':'7',
  '8':'8',
  '9':'9',
  '10':'10',
  'jack':'valet',
  'queen':'reine',
  'king':'roi',
  'clubs':  'trèfles',
  'diamonds':'carreaux',
  'hearts': 'coeurs',
  'spades':'piques'
}


game = Game()

@intent('help_blackjack')
def on_help_blackjack(req):
  req.agent.answer(req._(en_help))
  return req.agent.done()

@intent('play_blackjack')
def on_play_blackjack(req):
  req.agent.context('blackjack')
  global game
  return game.apply_rule(req)

@intent('blackjack/hit')
def on_hit(req):
  global game
  game.player_action = game.HIT
  return game.apply_rule(req)

@intent('blackjack/stand')
def on_stand(req):
  global game
  game.player_action = game.STAND
  return game.apply_rule(req)

@intent('blackjack/double')
def on_double(req):
  global game
  game.player_action = game.DOUBLE
  return game.apply_rule(req)

@intent('blackjack/bet')
def on_bet(req):
  global game
  game.player_action = game.BET
  return game.apply_rule(req)
"""
@intent('blackjack/split')
def on_split(req):
  global game
  game.player_action = game.SPLIT
  return game.apply_rule(req)
"""

"""
@intent('blackjack/insurance')
def on_insurance(req):
  global game
  game.player_action = game.INSURANCE
  return game.apply_rule(req)
"""

@intent('blackjack/show_player_hand')
def on_show_player_hand(req):
  global game
  req.agent.answer(req._('Your hand contains : {0}').format(game.player_hand.answer(req)))
  return req.agent.done()

@intent('blackjack/show_dealer_hand')
def on_show_dealer_hand(req):
  global game
  req.agent.answer(req._('The dealer hand contains (only visible cards) : {0}').format(game.dealer_hand.answer(req)))
  return req.agent.done()

@intent('blackjack/bankroll')
def on_bankroll(req):
  global game
  req.agent.answer(req._('Your bankroll is {0} chips').format(game.player_bankroll))
  return req.agent.done()

@intent('blackjack/help')
def on_help(req):
  req.agent.answer(req._(en_help))
  return req.agent.done()

@intent('blackjack/quit')
def on_quit(req):
  req.agent.context(None)
  req.agent.answer(req._('Goodbye'))
  return req.agent.done()
