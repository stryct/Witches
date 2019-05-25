from enum import Enum
from helpers import twodigitnum, coloredText
import logging

from config_game import GAME_OPPONENT_COUNT
from config_learning import *

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

def card_list_to_string(deck):
    """ Get a string representing the players hand """

    from config_game import DRAW_LARGE_CARDS as large_cards

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

class Witches():

    def __init__(self):
        """ Init the Witches Environment """
        
        # used for the nicely colored cards in the console on windows
        import colorama
        colorama.init()

        self.__cards_per_player = int(60 / (GAME_OPPONENT_COUNT+1))
        self.__initial_player_id = 0
        self.__current_player_id = self.__initial_player_id
        self.__turn_index = 0
        self.__turn_amount = int(60/(GAME_OPPONENT_COUNT+1))

        # all cards from which new players decks will be created
        self.__full_deck = possible_cards()

        # keep track of the played cards for this round: [[...agent...], [...op1...],[...op2...],...]
        self.__played_cards = []
        self.__player_tricks = {}

        # keep track of players decks round: [[...agent...], [...op1...],[...op2...],...]
        self.__decks = []
        
        self.__opponents = self.__init_opponents()

        # call reset to start a new round
        self.reset()

    @property
    def player_tricks(self) -> list:
        """ Tricks taken by each player """
        return [self.__player_tricks[key] for key in self.__player_tricks]

    @property
    def decks(self) -> list:
        """ Decks of all players """
        return self.__decks

    @property
    def done(self) -> bool:
        """ Game Finished ? """
        return len(self.__played_cards) >= 60

    @property
    def turn_done(self) -> bool:
        """ Turn finished ? """
        return len(self.__played_cards) % (GAME_OPPONENT_COUNT+1) == 0 and len(self.__played_cards) > 0

    @property
    def table(self) -> list:
        """ Current table """
        return self.__get_cards_from_turn(self.__turn_index)

    def setLogLevel(self,level):
        logging.getLogger().setLevel(level)

    def test(self):
        
        assert self.__evaluate_turn([(3,4),(0,0),(1,2),(1,4),(2,1)], 0) == 0
        assert self.__evaluate_turn([(0,0),(1,1),(1,2),(1,4),(2,1)], 0) == 3
        assert self.__evaluate_turn([(0,0),(0,0),(1,2),(1,4),(2,1)], 0) == 3
        assert self.__evaluate_turn([(0,0),(3,11),(0,0),(1,4),(2,1)], 0) == 1
        assert self.__evaluate_turn([(0,0),(0,0),(0,0),(0,0)], 0) == 3

    # ---------------- Drawing ----------------

    def render(self):
        """ Draw the game state to the console """
        print("====== Players Hands ======")
        for pid in range(GAME_OPPONENT_COUNT+1):
            print(card_list_to_string(self.__decks[pid]))
        print("======     Table     ======")
        turn_index = int(len(self.__played_cards) / (GAME_OPPONENT_COUNT+1))
        print(card_list_to_string(self.__get_cards_from_turn(turn_index)))
    
    # ---------------- Game Mechanics ----------------

    def __run_game_until_player(self, agent_id:int=0):
        """ runs the game until its the players turn """
        while self.__current_player_id is not agent_id:
            
            logging.debug(" =============== Player {} plays =============".format(self.__current_player_id))
            logging.debug("Table\n"+str(card_list_to_string(self.table)))

            color_to_play = self.get_allowed_color()

            logging.debug("Has to play color: {}".format(color_to_play.name))
            logging.debug("From his deck:\n"+card_list_to_string(self.__decks[self.__current_player_id]))
            possibleCards = self.filter_deck_color(self.__current_player_id, color_to_play)
            if len(possibleCards) == 0:
                possibleCards = self.__decks[self.__current_player_id]
            logging.debug("Is playing:\n" + card_list_to_string([possibleCards[0]]))
            self.play_card(self.__current_player_id,self.__decks[self.__current_player_id].index(possibleCards[0]))
            
            if self.done:
                break
    
    def get_allowed_color(self):
        """ Returns the first 'real' color on the table
            if CARD_COLORS.NONE is returned you can play whatever you want 
        """
        color_to_play = CARD_COLORS.NONE
        for c,_ in self.table:
            if c is not CARD_COLORS.NONE.value:
                color_to_play = CARD_COLORS(c)
                break
        return color_to_play

    def __player_has_color(self,pid:int,cardColor:CARD_COLORS):
        """ Check for a color """
        ret = False
        for c,v in self.__decks[pid]:
            ret |= c == cardColor.value
        return ret

    def filter_deck_color(self,pid:int,cardColor:CARD_COLORS):
        """ Filter for color """
        if cardColor is CARD_COLORS.NONE:
            return self.__decks[pid]
        else:
            return [(c,v) for c,v in self.__decks[pid] if c == cardColor.value]

    def __evaluate_played_cards(self):
        """ Calculate scores for all players """

        logging.debug("Calculating player scores...")

        scores = []

        for key in self.__player_tricks:
            logging.debug("Player {}'s cards:".format(key))
            logging.debug("\n"+card_list_to_string(self.__player_tricks[key]))
            scores.append(self.__calc_card_points(self.__player_tricks[key]))

        logging.debug("Scores: {}".format(str(list(zip(list(range(GAME_OPPONENT_COUNT+1)),scores)))))

    def __calc_card_points(self, cards:list):
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

    def __evaluate_turn(self, turn_cards:list, start_player_index:int):
        """ How gets these cards ??? """

        logging.debug("Evaluating cards:\n" + card_list_to_string(turn_cards))

        winning_idx = 0

        while turn_cards[winning_idx][0] == CARD_COLORS['NONE'].value:
            logging.debug("Skipping card at pos "+str(winning_idx))
            winning_idx += 1
            if winning_idx >= len(turn_cards):
                winning_idx -= 1
                break

        for card_id in range(winning_idx,len(turn_cards)):

            col,val = turn_cards[card_id]

            if col == CARD_COLORS['NONE'].value:
                continue
            elif col == turn_cards[winning_idx][0] and turn_cards[winning_idx][1] < val:
                winning_idx = card_id
                continue

        logging.debug("the {}th card gets the trick".format(winning_idx+1))
        # determine the player id of the player that takes the cards
        start_player_index += winning_idx
        start_player_index = start_player_index % (GAME_OPPONENT_COUNT+1)

        logging.debug(">> Player {} gets the following cards:\n".format(start_player_index) + card_list_to_string(turn_cards))

        return start_player_index

    def __get_cards_from_turn(self, turn_index:int):
        """ Extract cards from specific turn from stack """
        turn_length = len(self.__played_cards) % (GAME_OPPONENT_COUNT+1)
        card_start_index = turn_index * (GAME_OPPONENT_COUNT+1)
        return self.__played_cards[card_start_index:card_start_index+(GAME_OPPONENT_COUNT+1)]

    def can_play_card(self, agent_id:int, action_id:int):
        """ Can this card be played ? """
        if len(self.__decks[agent_id])-1 < action_id:
            return False
        if self.__decks[agent_id][action_id][0] == CARD_COLORS['NONE'].value:
            return True
        if len(self.table) > 0:
            fc = self.table[0][0]
            if not fc == CARD_COLORS['NONE'].value:
                if self.__player_has_color(agent_id,CARD_COLORS(fc)) and self.__decks[agent_id][action_id][0] != fc:
                    return False
        return True

    def play_card(self, agent_id:int, action_id:int):
        """ Play the card at index action_id from agent with agent_id """
        
        # 1.) Check if we can play this card
        if not self.can_play_card(agent_id, action_id):
            logging.debug("Illegal Card!")
            return False

        # 2.) Play the card by moving it to a different place
        card = self.__decks[agent_id][action_id]
        self.__decks[agent_id].remove(card)
        self.__played_cards.append(card)

        # 3.) Advance the current player
        self.__current_player_id = (self.__current_player_id + 1)%(GAME_OPPONENT_COUNT+1)

        # 4.) check for end of turn
        if self.turn_done:
            # end of turn:
            self.__initial_player_id = self.__evaluate_turn(self.__get_cards_from_turn(self.__turn_index), self.__initial_player_id)
            self.__player_tricks[self.__initial_player_id].extend(self.__get_cards_from_turn(self.__turn_index))
            self.__current_player_id = self.__initial_player_id
            self.__turn_index += 1
            logging.debug("End of turn! (play_card)")
            if len(self.__played_cards) == 60:
                logging.debug("End of game!")

        return True
    
    def reset(self):
        """ Give out new cards, return the initial observation """

        logging.debug("reseting!")

        import random

        shuffle_deck(self.__full_deck)
        self.__decks = split_deck(self.__full_deck, GAME_OPPONENT_COUNT+1)
        self.__played_cards = []
        self.__player_tricks = {}

        for id in range(GAME_OPPONENT_COUNT+1):
            self.__player_tricks[id] = []
        
        self.__initial_player_id = random.choice(list(range(GAME_OPPONENT_COUNT+1)))
        self.__current_player_id = self.__initial_player_id

        # "prime" the game...
        self.__run_game_until_player()

        return self.observe()


    # --------------- AI related stuff --------------

    def __init_opponents(self):
        """ Initializes all agents """
        # TODO
        pass

    def update_opponent_models(self, model):
        """ Updates all opponents """
        # TODO
        pass

    def observe(self,agent_id:int = 0):
        """ 
            Get observation for agent with agent_id
            - All played cards order by player
            - Cards the agent can play
        """
        # TODO
        return [[None]]

    def step(self, action_id:int ,agent_id:int=0):
        """ Takes a step in the environment and returns (observation, reward, done, info) """

        # 1. play card based on action id
        success = self.play_card(agent_id,action_id)

        # 2. see if are done now
        if not success:
            logging.debug("Played illegal card!")
            observation = self.reset()
            return (observation, REW_WRONG_CARD, True, None)
        
        # 3. Let everyone else play
        self.__run_game_until_player(agent_id=agent_id)

        # 4. See if the game is over now
        if self.done:
            print("game is really finished...")
            points = self.__calc_card_points(self.__player_tricks[agent_id])
            logging.debug("Game over, agent has {} points from these cards:\n{}".format(points,card_list_to_string(self.__player_tricks[agent_id])))
            observation = self.reset()
            # TODO convert points to reward!
            return (observation, points, True, None)

        # 5. not over yet!
        observation = self.observe()
        return (observation, REW_CORRECT_CARD, False, None)


if __name__ == "__main__":

    e = Witches()
    e.test()