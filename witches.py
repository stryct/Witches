from enum import Enum
import numpy as np
from helpers import twodigitnum, coloredText
import logging

from config_game import GAME_OPPONENT_COUNT
from config_observation import OBS_NO_CARD

class CARD_COLORS(Enum):
    NONE = 0
    BLUE = 1
    GREEN = 2
    RED = 3
    YELLOW = 4

def possible_cards():
    """ Generates and returns the card deck as [(card_color, card_value)] """
    
    ret = []

    # all cards with color
    for v,_ in [(c.value,c.name) for c in CARD_COLORS]:
        if v == 0:
            continue
        else:
            ret.extend([(v,x) for x in range(1,15)])

    # add the four zeros
    ret.extend([(0,0)]*4)

    return ret

def shuffle_deck(deck:list):
    """ Shuffle the deck in-place """
    import random
    random.shuffle(deck)

def split_deck(deck:list, player_number:int):
    """ Returns a list [[...(card)...]*player_number] """

    assert player_number > 1 and player_number <= 6, "{} is not a sensible amount of players :)".format(player_number)
    assert 60 % player_number == 0, "60 is not divisible by {}, please pick a different player amount (including the agent)".format(player_number)

    cards_per_player = int(60 / player_number)
    split_deck = []

    for player_id in range(player_number):
        idx = player_id*cards_per_player
        split_deck.append(deck[idx:idx+cards_per_player])

    return split_deck

class Witches():

    def __init__(self):
        """ Init the Witches Environment """

        self._cards_per_player = int(60 / (GAME_OPPONENT_COUNT+1))
        self._initial_player_id = 0

        # all cards from which new players decks will be created
        self.full_deck = possible_cards()

        # keep track of the played cards for this round: [[...agent...], [...op1...],[...op2...],...]
        self.played_cards = []
        self.player_tricks = {}
        self._turn_index = 0
        self._turn_amount = int(60/(GAME_OPPONENT_COUNT+1))

        # keep track of players decks round: [[...agent...], [...op1...],[...op2...],...]
        self.decks = []
        
        self.opponents = self._init_opponents()

        # call reset to start a new round
        self.reset()

    def test(self):
        
        import random
        random.seed(0)

        logging.getLogger().setLevel(logging.DEBUG)

        logging.debug("Testing...")
        turn_amount = int(60/(GAME_OPPONENT_COUNT+1))
        logging.debug("Playing {} turns.".format(turn_amount))
        
        for _ in range(turn_amount):
            self.step_interactive()
        
        

        #for turn_number in range(int(60/(GAME_OPPONENT_COUNT+1))):
        #    print(self._card_list_to_string(self._get_cards_from_turn(turn_number)))

    # ---------------- Drawing ----------------

    def render(self):
        """ Draw the game state to the console """
        print("====== Players Hands ======")
        for pid in range(GAME_OPPONENT_COUNT+1):
            print(self._card_list_to_string(self.decks[pid]))
        print("======     Table     ======")
        turn_index = int(len(self.played_cards) / (GAME_OPPONENT_COUNT+1))
        print(self._card_list_to_string(self._get_cards_from_turn(turn_index)))

    def _card_list_to_string(self, deck, large_cards = False):
        """ Get a string representing the players hand """

        top = "╔══╗" if not large_cards else "╔═══╗"
        bottom = "╚══╝" if not large_cards else "╚═══╝"
        cards_val = ""
        cards_col = ""
        tops = ""
        bottoms = ""
        c = 0
        cnames = []

        for col,val in deck:
            c += 1
            cname = CARD_COLORS(col).name
            cnames.append(cname)

            if large_cards:
                cards_col += coloredText("║{}║".format(cname[:3]), cname)
                cards_val += coloredText("║{} ║".format(twodigitnum(val)), cname)
            else:
                cards_val += coloredText("║{}║".format(twodigitnum(val)), cname)

            bottoms += coloredText(bottom, cname)
            tops += coloredText(top, cname)

        if large_cards:
            return tops + '\n' + cards_col + '\n' + cards_val + '\n' + bottoms
        else:
            return tops + '\n' + cards_val + '\n' + bottoms
    
    # ---------------- Game Mechanics ----------------

    def step_interactive(self, auto_select=False):

        # let each player play a card starting from the starting player
        logging.debug("Player {} starts.".format(self._initial_player_id))
        for i in range(GAME_OPPONENT_COUNT+1):
            pid = (self._initial_player_id + i)%(GAME_OPPONENT_COUNT+1)
            if pid == 0 and not auto_select:
                table = self._get_cards_from_turn(self._turn_index)
                print("Table:")
                print(self._card_list_to_string(table))
                
                print("Your deck:")
                if len(table) > 0:
                    firstColor = table[0][0]
                    if self._player_has_color(pid,CARD_COLORS(firstColor)) and CARD_COLORS(firstColor).name is not "NONE":
                        print("You need to play {}!".format(CARD_COLORS(firstColor).name))

                print(self._card_list_to_string(self.decks[pid]))
                self._play_card(pid,int(input("Which card to you want to play? (index from 0): ")))
            else:
                self._play_card(pid,0)

        # see how gets all cards
        self._initial_player_id = self._evaluate_turn(self._get_cards_from_turn(self._turn_index), self._initial_player_id)
        self.player_tricks[self._initial_player_id].extend(self._get_cards_from_turn(self._turn_index))

        self._turn_index += 1

        if self._turn_index >= self._turn_amount:
            # round is over
            self._evaluate_played_cards()
            self.reset()

    def _player_has_color(self,pid:int,cardColor:CARD_COLORS):
        """ Check for a color """

        ret = False
        for c,v in self.decks[pid]:
            ret |= c == cardColor.value
        return ret

    def _filter_deck_color(self,pid:int,cardColor:CARD_COLORS):
        
        return [(c,v) for c,v in self.decks[pid] if c == cardColor.value]

    def _evaluate_played_cards(self):
        """ Calculate scores for all players """

        logging.debug("Calculating player scores...")

        scores = []

        for key in self.player_tricks:
            logging.debug("Player {}'s cards:".format(key))
            logging.debug("\n"+self._card_list_to_string(self.player_tricks[key]))
            scores.append(self._calc_card_points(self.player_tricks[key]))

        logging.debug("Scores: {}".format(str(list(zip(list(range(GAME_OPPONENT_COUNT+1)),scores)))))

    def _calc_card_points(self, cards:list):
        """ Calculate the score for a list of cards """
        
        g11 = (CARD_COLORS['GREEN'].value, 11) in cards
        g12 = (CARD_COLORS['GREEN'].value, 12) in cards
        r11 = (CARD_COLORS['RED'].value, 11) in cards
        y11 = (CARD_COLORS['YELLOW'].value, 11) in cards
        b11 = (CARD_COLORS['BLUE'].value, 11) in cards

        reds = 0

        for color, value in cards:
            
            if value == 11 or (value == 12 and color == CARD_COLORS['GREEN'].value):
                continue

            reds += 1 if color == CARD_COLORS['RED'].value else 0

        reds *= 2 if r11 else 1
        reds = 15 if reds > 15 else reds
        reds += 5 if g11 and not b11 else 0
        reds += 10 if g12 and not b11 else 0
        reds -= 5 if y11 else 0

        return reds

    def _evaluate_turn(self, turn_cards:list, start_player_index:int):
        """ How gets these cards ??? """

        winning_idx = 0
        for card_id in range(0,len(turn_cards)):

            col,val = turn_cards[card_id]

            if col == CARD_COLORS['NONE'].value:
                winning_idx = 1 if card_id == 0 else winning_idx
                continue
            elif col == turn_cards[winning_idx][0] and turn_cards[winning_idx][1] < val:
                winning_idx = card_id
                continue

        # determine the player id of the player that takes the cards
        start_player_index += winning_idx
        start_player_index = start_player_index % (GAME_OPPONENT_COUNT+1)

        logging.debug(">> Player {} gets the following cards:\n".format(start_player_index) + self._card_list_to_string(turn_cards))

        return start_player_index


    def _get_cards_from_turn(self, turn_index:int):
        """ Extract cards from specific turn from stack """
        turn_length = len(self.played_cards) % (GAME_OPPONENT_COUNT+1)
        card_start_index = turn_index * (GAME_OPPONENT_COUNT+1)
        return self.played_cards[card_start_index:card_start_index+(GAME_OPPONENT_COUNT+1)]

    def _play_card(self, agent_id:int, action_id:int):
        """ Play the card at index action_id from agent with agent_id """
        
        if len(self.decks[agent_id])-1 < action_id:
            return False

        card = self.decks[agent_id][action_id]
        self.decks[agent_id].remove(card)
        self.played_cards.append(card)

        return True
    
    def reset(self):
        """ Give out new cards, return the initial observation """

        import random

        shuffle_deck(self.full_deck)
        self.decks = split_deck(self.full_deck, GAME_OPPONENT_COUNT+1)
        self.played_cards = []
        self.player_tricks = {}

        for id in range(GAME_OPPONENT_COUNT+1):
            self.player_tricks[id] = []
        
        self._initial_player_id = random.choice(list(range(GAME_OPPONENT_COUNT+1)))

    # --------------- AI related stuff --------------

    def _init_opponents(self):
        """ Initializes all agents """
        # TODO
        pass

    def update_opponent_models(self, model):
        """ Updates all opponents """
        # TODO
        pass

    def observe(self,agent_id:int):
        """ 
            Get observation for agent with agent_id
            - All played cards order by player
            - Cards the agent can play
        """
        # TODO


if __name__ == "__main__":

    import colorama
    colorama.init()

    e = Witches()
    e.test()