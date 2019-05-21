from enum import Enum

def twodigitnum(num:int):
    if num < 10:
        return "0"+str(num)
    elif num < 100:
        return str(num)
    else:
        raise ValueError("Two digit number doesnt work with {}".format(num))

class TextColors(Enum):
    RED = '\u001b[31m'
    GREEN = '\u001b[32m'
    YELLOW = '\u001b[33m'
    BLUE = '\u001b[34;1m'
    WHITE = '\u001b[37m'
    RESET = '\u001b[0m'

def coloredText(text, color):
    if color == "RED":
        return TextColors.RED.value + text + TextColors.RESET.value
    elif color == "GREEN":
        return TextColors.GREEN.value + text + TextColors.RESET.value
    elif color == "BLUE":  
        return TextColors.BLUE.value + text + TextColors.RESET.value
    elif color == "YELLOW":
        return TextColors.YELLOW.value + text + TextColors.RESET.value
    elif color == "NONE":
        return TextColors.WHITE.value + text + TextColors.RESET.value
    else:
        raise ValueError("TextColor {} is not known!".format(color))
