from witches import Witches

class Witches_Gym():

    def __init__(self):
        """ Init the Witches Environment """
        self.env = Witches()

    def step_async(self, actions):
        pass

    def step_wait(self):
        pass

    def reset(self):
        pass

    def test(self):
        
        print(">>> Launching interactive testing mode...")
        print(">>> play a card by typing it's (zero-based) index when asked for an action!")

        from witches import card_list_to_string
        import logging

        self.env.setLogLevel(logging.DEBUG)

        while True:
            print("======== YOUR TURN ========")
            print("Current Table:")
            print(card_list_to_string(self.env.table))
            print("Your Deck:")
            print(card_list_to_string(self.env.decks[0]))

            action_id = int(input("Choose an action: "))
            o, r ,d, _ = self.env.step(action_id,0)
            if d:
                print("Game Over:")
                print("Reward: {}".format(r))
                cmd = input("Continue playing?? Type 'yes' or 'no': ")
                if cmd == 'no':
                    break


if __name__ == "__main__":
    tmp = Witches_Gym()
    tmp.test()


