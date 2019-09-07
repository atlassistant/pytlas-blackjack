from sure import expect
from pytlas.testing import create_skill_agent
import os
import blackjack
import copy

class Test_Blackjack:

  def test_as_card_should_is_ace(self):
    ace_card = blackjack.Card('club', 'an ace', 11)
    expect(ace_card.is_ace).to.be(True)
  
  def test_shoe_create_should_contains_correct_number_of_card(self):
    shoe = blackjack.Shoe()
    expect(len(shoe.cards)).equal(0)
    shoe.create(0)
    expect(len(shoe.cards)).equal(0)
    shoe.create(1)
    expect(len(shoe.cards)).equal(52)
    shoe.create(2)
    expect(len(shoe.cards)).equal(104)

  def test_shoe_create_one_packet_should_contains_uniq_card(self):
    shoe = blackjack.Shoe()
    shoe.create(1)
    visited_cards = []
    for card in shoe.cards:
      already_in = next( (visited_card for visited_card  in visited_cards if (visited_card.figure == card.figure and visited_card.color == card.color) ), None) 
      expect(already_in).to.be(None)
      visited_cards.append(card)

  def test_shoe_shuffle_should_contains_same_card_ordered_differently(self):
    shoe = blackjack.Shoe()
    shoe.create(1)
    ordered_cards = copy.deepcopy(shoe.cards)
    shoe.shuffle()
    different_position = 0
    for index in range(0, len(shoe.cards)):
      if ordered_cards[index].figure != shoe.cards[index].figure or ordered_cards[index].color != shoe.cards[index].color:
        different_position += 1
    expect(different_position).greater_than(0)

  def test_shoe_draw_should_return_first_card_and_remove_it_from_deck(self):
    shoe = blackjack.Shoe()
    shoe.cards = [blackjack.Card('club', 'an ace', 11), blackjack.Card('club', 'jack', 10)]
    first_card = shoe.draw()
    expect(first_card.figure == 'an ace' and first_card.color == 'club').to.be(True)
    expect(len(shoe.cards)).equal(1)
    expect(shoe.cards[0].figure == 'jack' and shoe.cards[0].color == 'club').to.be(True)

  def test_empty_shoe_draw_should_return_none(self):
    shoe = blackjack.Shoe()
    card = shoe.draw()
    expect(card).to.be(None)

  def test_hand_should_have_added_card(self):
    hand = blackjack.Hand()
    expect(len(hand.cards)).equal(0)
    card = blackjack.Card('club', 'an ace', 11)
    hand.add(card)
    expect(len(hand.cards)).equal(1)
    expect(hand.cards[-1].figure=='an ace' and hand.cards[-1].color=='club').to.be(True)
    card = blackjack.Card('spades', 'jack', 10)
    hand.add(card)
    expect(len(hand.cards)).equal(2)
    expect(hand.cards[-1].figure=='jack' and hand.cards[-1].color=='spades').to.be(True)

  def test_hand_should_return_correct_number_of_ace(self):
    hand = blackjack.Hand()
    expect(hand.number_of_ace()).equal(0)
    card = blackjack.Card('club', 'an ace', 11)
    hand.add(card)
    expect(hand.number_of_ace()).equal(1)
    card = blackjack.Card('spades', 'jack', 10)
    hand.add(card)
    expect(hand.number_of_ace()).equal(1)
    card = blackjack.Card('spades', 'an ace', 11)
    hand.add(card)
    expect(hand.number_of_ace()).equal(2)

  def test_hand_should_contains_no_card_after_clear(self):
    hand = blackjack.Hand()
    card = blackjack.Card('club', 'an ace', 11)
    hand.add(card)
    card = blackjack.Card('spades', 'jack', 10)
    hand.add(card)
    expect(len(hand.cards)).equal(2)
    hand.clear()
    expect(len(hand.cards)).equal(0)

  def test_hand_should_evalute_correctly(self):
    hand = blackjack.Hand()
    card = blackjack.Card('club', 'an ace', 1)
    hand.add(card)
    expect(hand.evaluate()).equal(11)
    card = blackjack.Card('club', '4', 4)
    hand.add(card)
    expect(hand.evaluate()).equal(15)
    card = blackjack.Card('club', 'jack', 10)
    hand.add(card)
    expect(hand.evaluate()).equal(15)
    card = blackjack.Card('spades', 'an as', 1)
    hand.add(card)
    expect(hand.evaluate()).equal(16)



  def test_blackjack_launch(self):
    agent = create_skill_agent(os.path.dirname(__file__), lang='en')
    agent.parse('play blackjack')
    call = agent.model.on_answer.get_call()
    expect(call.text).to.equal('Bet to play')
