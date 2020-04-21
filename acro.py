"""
acro.py - make acronyms w/ your friends on irc!
this is a plugin for the sopel irc bot framework - https://sopel.chat
"""

import sopel.module as module
import sopel.tools as tools
from sopel.formatting import color, bold, colors
import random
import time
import operator
import json
from datetime import datetime
import requests

def setup(bot):
    # check if we have letters in db, if not, import them
    letterPool = bot.db.get_plugin_value('acro', 'letters', [])
    if not letterPool:
        for char in 'xzqqjjjyyyyvvvvkkkkuuuuuggggggnnnnnnnllllllleeeeeeeerrrrrrrrdddddddddmmmmmmmmmmffffffffffhhhhhhhhhhhpppppppppppbbbbbbbbbbbccccccccccccwwwwwwwwwwwwwssssssssssssssiiiiiiiiiiiiiiiooooooooooooooooaaaaaaaaaaaaaaaaatttttttttttttttttt':
            letterPool.append(char)
            bot.db.set_plugin_value('acro', 'letters', letterPool)

class AcroGame:
    def __init__(self, trigger):
        self.owner = trigger.nick
        self.channel = trigger.sender
        self.scores = {}
        self.currentAcro = []
        self.currentAcroString = ''
        self.submittedAcros = {}
        self.letters = []
        self.roundPlayers = []
        self.active = True
        self.gameMode = ''
        self.countAcros = 1
        self.voteCount = 0
        self.voterLog = []
        self.badRounds = 0
        self.scoreNeeded = 15

    def generateAcro(self, bot, trigger):
        self.currentAcro = []
        self.countAcros = 1
        self.submittedAcros = {}
        self.voteCount = 0
        self.letters = []

        if random.randint(1,100) <= bot.db.get_plugin_value('acro', 'custom_chance', 10):
            customAcros = bot.db.get_plugin_value('acro', 'custom_acros', ['ACRO', 'GAME'])
            customAcro = random.choice(customAcros).lower()
            for letter in customAcro:
                self.currentAcro.append(letter)
        else:
            letterPool = bot.db.get_plugin_value('acro', 'letters')

            for char in letterPool:
                self.letters.append(char)

            if(random.randint(0,5)) == 0:
                max_length = 6
            else:
                max_length = 4

            for _ in range(random.randint(3,max_length)):
                randomLetter = random.choice(self.letters)
                self.letters.remove(randomLetter)
                self.currentAcro.append(randomLetter)

        self.currentAcroString = bold(color(''.join(self.currentAcro).upper(), colors.ORANGE))
        return bot.say(f"Acro for this round: {self.currentAcroString}")

    def submitAcro(self, bot, trigger):
        if self.gameMode is not 'SUBMITTING':
            return
        if len(self.submittedAcros) >= 9:
            return bot.notice("We already have 9 acros for this round, which is the limit. Try to submit faster next round!")

        submittedAcro = trigger.group(0)
        words = submittedAcro.split()

        if(len(words) != len(self.currentAcro)):
            return bot.notice(f"There's a problem with the acro you submitted, remember, the current acro is: {self.currentAcroString}")

        for word, letter in zip(words, self.currentAcro):
            if word[0].lower() != letter:
                return bot.notice(f"There's a problem with the acro you submitted, remember, the current acro is: {self.currentAcroString}")

        for username, info in self.submittedAcros.items():
            if username == trigger.sender:
                self.submittedAcros[str(trigger.sender)].update({'acro': submittedAcro})
                return bot.notice(f"Your acro for this round has been updated! {bold(submittedAcro)}")

        self.submittedAcros[str(trigger.sender)] = {}
        self.submittedAcros[str(trigger.sender)].update({'acroID': self.countAcros, 'username': str(trigger.sender), 'acro': submittedAcro})
        self.submittedAcros[str(trigger.sender)]['votes'] = []
        bot.say(f"Acro #{self.countAcros} has been submitted!", self.channel)
        self.countAcros += 1
        return bot.notice(f"Your acro for this round has been recorded! {bold(submittedAcro)}")

    def displayAcros(self, bot):
        if len(self.submittedAcros) < 3:
            self.badRounds += 1
            if self.badRounds > 2:
                bot.say("We need at least 3 players to play acro. Stopping the game now.")
                self.active = False
                return False
            else:
                bot.say("We need at least 3 players to play acro. Restarting the round...")
                return False
        self.badRounds = 0
        self.voterLog = []

        bot.say("Ok, Acro submission time is over. Its time to VOTE:")
        for username, info in self.submittedAcros.items():
            acroID = bold(color(str(info['acroID']), colors.RED))
            acro = color(' ' + info['acro'] + ' ', colors.ORANGE, colors.BLACK)
            bot.say(f"[{acroID}] {acro}")

        time.sleep(2)

        vote_instructions = bold(color(f"/msg {bot.nick} #", colors.GREEN))
        bot.say(f"Ok, you have 30 seconds to vote for your favorite acro! Type {vote_instructions} to vote now!")

        self.gameMode = 'VOTING'
        voteEndTime = time.time() + 30
        while(self.gameMode == 'VOTING'):
            if self.voteCount == len(self.submittedAcros) or time.time() > voteEndTime:
                self.gameMode = 'NONE'
                bot.say("Voting is over!")

    def voteAcro(self, bot, trigger):
        if self.gameMode != 'VOTING':
            return
        if str(trigger.sender) not in self.submittedAcros:
            bot.notice(f"You didn't submit an acro, you can't vote!", trigger.sender)
            return
        if str(trigger.sender) in self.voterLog:
            return bot.notice("You already voted. Chill out!", trigger.sender)

        votedFor = int(trigger.group(0))
        for username, info in self.submittedAcros.items():
            acroID = info['acroID']
            if votedFor == acroID:
                if username == trigger.sender:
                    return bot.notice("You can't vote for your own acro!")
                self.submittedAcros[username]['votes'].append(str(trigger.sender))
        self.voteCount += 1
        self.voterLog.append(str(trigger.sender))
        bot.say(f"Vote #{self.voteCount} has been submitted!", self.channel)
        return bot.notice(f"You have voted for acro #{votedFor}", trigger.sender)

    def addPoints(self, username, amount):
        if username not in self.scores:
            self.scores[username] = amount
        else:
            self.scores[username] += amount

    def displayVotes(self, bot):
        if self.gameMode != 'SCORING':
            return

        if self.voteCount < 1:
            bot.say("No votes were submitted. Stopping the game now.")
            self.active = False
            return False

        voterList = []
        highestVotes = 0
        candidates = {}
        for username, info in self.submittedAcros.items():
            acro = info['acro']
            voterList.extend(info['votes'])
            voteCount = len(info['votes'])
            self.logAcro(bot, username, acro, voteCount)
            if voteCount >= highestVotes:
                highestVotes = voteCount
                candidates[username] = voteCount
            voters = ' '.join(info['votes'])
            if voteCount > 0:
                bot.say(f"{color(username,colors.RED)}'s acro: {color(' ' + acro + ' ', colors.ORANGE, colors.BLACK)} got {str(voteCount)} votes from: {voters}")
            else:
                bot.say(f"{color(username,colors.RED)}'s acro: {color(' ' + acro + ' ', colors.ORANGE, colors.BLACK)} got no votes :(")

        winningScore = max(candidates.values())

        winners = []
        assholes = []
        for key in candidates:
            if candidates[key] == winningScore:
                if key in voterList:
                    winners.append(key)
                else:
                    assholes.append(key)

        if len(assholes) > 0 and winningScore > 0:
            for asshole in assholes:
                bot.say(bold(color(f"{asshole} should have won, but they didn't vote. Please refrain from being a {random.choice(['idiot', 'dummy', 'jerk'])} in the future, thanks.", colors.RED)))
        if len(winners) == 0:
            winString = bold(color("Nobody won any points this round. If you don't vote you don't win! VOTE!!!", colors.RED))
        elif len(winners) == 1:
            winner = winners[0]
            winString = f"{bold(winner)} had the most votes and wins 3 points this round!"
            self.addPoints(winner, 3)
            if len(self.submittedAcros[winner]['votes']) > 1:
                firstVoter = self.submittedAcros[winner]['votes'][0]
                self.addPoints(firstVoter, 1)
                bot.say(f"{bold(firstVoter)} was the first to vote for a winning acro and receives 1 bonus point!")
        else:
            for winner in winners:
                self.addPoints(winner, 3)
                winnerString = ' + '.join(winners)
                winString = bold(f"{winnerString} tied for the most votes and each win 3 points this round!")

        bot.say(winString)

        sortedScores = dict(sorted(self.scores.items(), key=operator.itemgetter(1),reverse=True))
        scoreString = bold("Scores: ")
        for user, points in sortedScores.items():
            scoreString += f"{bold(color(user, colors.BLUE))}: {color(str(points), colors.GREEN)}  "
        bot.say(scoreString.rstrip())

        winners = []
        for winner in self.scores:
            if self.scores[winner] >= self.scoreNeeded:
                winners.append(winner)

        if len(winners) != 0:
            if len(winners) > 1:
                for winner in winners:
                    self.addWin(bot, winner)
                bot.say(bold(f"{', '.join(winners)} all have {self.scoreNeeded} or more points and tie for the win!"))
            elif len(winners) == 1:
                winner = winners.pop()
                self.addWin(bot, winner)
                bot.say(bold(f"{winner} has won the game! ALL GLORY GOES TO YOU!!!"))

            self.active = False
            return False

    def addWin(self, bot, winner):
        highScores = bot.db.get_plugin_value('acro', 'scores', {})

        if winner not in highScores:
            highScores[winner] = 1
        else:
            highScores[winner] += 1

        bot.db.set_plugin_value('acro', 'scores', highScores)

        return highScores[winner]

    def logAcro(self, bot, nick, acro, voteCount):
        acros = bot.db.get_nick_value(nick, 'acros', [])
        logData = {"date": datetime.now().strftime("%m/%d/%Y"), "acro": acro, "votes": voteCount}
        acros.append(logData)
        bot.db.set_nick_value(nick, 'acros', acros)

class AcroBot:
    def __init__(self):
        self.games = {}

    def start(self, bot, trigger):
        if len(self.games) > 0:
            bot.say("I'm already hosting an acro game!")
            return

        bot.notice(f"New acro game started by {trigger.nick}! Have fun and good luck!", trigger.sender)
        time.sleep(1)
        self.games[trigger.sender] = AcroGame(trigger)
        game = self.games[trigger.sender]

        instructions = bold(color(f"/msg {bot.nick} <answer>", colors.GREEN))

        # game loop
        while(game.active is True):
            game.gameMode = 'SUBMITTING'
            bot.say(f"Points needed to win this game: {game.scoreNeeded}")
            bot.say(f"Submit an acro by messaging me. {instructions} is how you do it!")
            time.sleep(2)
            bot.say("You have 60 seconds to come up with your best acro! GO!")
            game.generateAcro(bot, trigger)
            time.sleep(45)
            bot.say(bold(color("HURRY THE FUCK UP! 15 SECONDS LEFT!", colors.RED)))
            time.sleep(15)
            game.gameMode = 'PREVOTE'
            if game.displayAcros(bot) == False:
                continue
            game.gameMode = 'SCORING'
            if game.displayVotes(bot) == False:
                continue
            time.sleep(8)

        del self.games[trigger.sender]

    def submitAcro(self, bot, trigger):
        if not self.games:
            return
        channel = next(iter(self.games))
        game = self.games[channel]
        game.submitAcro(bot, trigger)

    def voteAcro(self, bot, trigger):
        if not self.games:
            return
        channel = next(iter(self.games))
        game = self.games[channel]
        game.voteAcro(bot, trigger)

    def highScore(self, bot, trigger):

        highScores = bot.db.get_plugin_value('acro', 'scores', {})

        sortedScores = dict(sorted(highScores.items(), key=operator.itemgetter(1),reverse=True))
        scoreString = bold("GAME WINS: ")
        for user, points in sortedScores.items():
            scoreString += f"{bold(color(user, colors.BLUE))}: {color(str(points), colors.GREEN)}  "
        bot.say(scoreString.rstrip())

    def addAcro(self, bot, trigger):
        if (len(trigger.group(2)) > 6) or (len(trigger.group(2)) < 3):
            return bot.say("This custom acro is a bad length. Try again.")
        if(trigger.group(2).isalpha()) == False:
            return bot.say("The custom acro you're trying to add is invalid. Try again.")

        customAcros = bot.db.get_plugin_value('acro', 'custom_acros', [])

        newAcro = trigger.group(2).upper()
        if(newAcro in customAcros):
            return bot.say("This custom acro is already in the game!")

        customAcros.append(newAcro)
        bot.db.set_plugin_value('acro', 'custom_acros', customAcros)

        return bot.say(f"Your custom acro {bold(color(newAcro, colors.ORANGE))} has been added to the game!")

    def delAcro(self, bot, trigger):
        if(trigger.group(2).isalpha()) == False:
            return bot.say("That acro wasn't found")
        customAcros = bot.db.get_plugin_value('acro', 'custom_acros', [])
        if not customAcros:
            return bot.say("Can't do that")
        acro = trigger.group(2).upper()
        if acro not in customAcros:
            return bot.say("That acro wasn't found")

        customAcros.remove(acro)
        bot.db.set_plugin_value('acro', 'custom_acros', customAcros)
        return bot.say(f"The acro {bold(color(acro, colors.ORANGE))} was removed")

    def generateLog(self, bot, trigger):
        if trigger.group(2):
            nick = trigger.group(2)
        else:
            nick = trigger.nick

        acros = bot.db.get_nick_value(nick, 'acros', [])
        if not acros:
            return bot.say("This user doesn't have any logged acros")
        string = f"{nick}'s acro list:\n"
        for acro in acros:
            string += f"{acro['date']} - {acro['acro']} - {acro['votes']} votes\n"

        url = self.clbin(string)
        bot.say(f"Here's a list of acros that {bold(nick)} has submitted: {url} (sponsored by gooch)")

    def generateCustom(self, bot):
        customAcros = bot.db.get_plugin_value('acro', 'custom_acros', [])

        if not customAcros:
            return bot.say("We don't have any custom acros, make some w/ !addacro")

        url = self.clbin("\n".join(customAcros))
        bot.say(f"Here's a list of custom acros in the game: {url}")

    def clbin(self, string):
        try:
            r = requests.post('https://clbin.com/', data={'clbin': string})
        except requests.exceptions.RequestException:
            raise

        return r.content.decode('utf-8').strip()

    def adjustScore(self, bot, trigger):
        params = trigger.group(2).split()
        username = params[0]
        if params[1].isdigit() == False:
            return bot.say("Invalid score. Please do !acrochangescore <user> #")
        score = int(params[1])
        highScores = bot.db.get_plugin_value('acro', 'scores', {})

        if username.isalnum() == False or len(username) > 9:
            return bot.say("Invalid user name. Please try again")

        if username in highScores:
            oldScore = highScores[username]
        else:
            oldScore = 0

        if score == 0:
            del highScores[username]
        else:
            highScores[username] = score
        bot.db.set_plugin_value('acro', 'scores', highScores)

        return bot.say(f"{username}'s game wins have been adjusted from {oldScore} to {score}")

    def viewLetters(self, bot, trigger):
        if trigger.group(2):
            # individual letter count
            letter = trigger.group(2).lower()
            if letter.isalpha() == False or len(letter) > 1:
                return bot.say("Invalid letter check. !acroletters <LETTER> (parameter is optional)")

            letters = bot.db.get_plugin_value('acro', 'letters', [])
            count = letters.count(letter)
            return bot.say(f"The letter {letter.upper()} occurs {count} times")

        else:
            # all letter count
            letters = bot.db.get_plugin_value('acro', 'letters', [])
            uniqueLetters = set(letters)
            string = bold('LETTER PROBABILITIES: ')
            for uniqueLetter in uniqueLetters:
                count = letters.count(uniqueLetter)
                string += f"{bold(color(uniqueLetter.upper(), colors.BLUE))}: {color(str(count), colors.GREEN)} "

            return bot.say(string)

    def adjustLetter(self, bot, trigger):
        params = trigger.group(2).split()
        if len(params) < 2:
            return bot.say("Invalid parameters. Please do !acroadjust <letter> #")
        if params[1].isdigit() == False:
            return bot.say("Invalid parameters. Please do !acroadjust <letter> #")
        letter = params[0].lower()
        if letter.isalpha() == False or len(letter) > 1:
            return bot.say("Please enter a valid letter to change. !acroadjust <letter> #")
        count = int(params[1])

        if count > 100:
            return bot.say("Why would you want more than 100 of the same letter?")

        letters = bot.db.get_plugin_value('acro', 'letters', [])
        oldCount = letters.count(letter)

        letters = list(filter((letter).__ne__, letters))

        for _ in range(count):
            letters.append(letter)

        bot.db.set_plugin_value('acro', 'letters', letters)
        return bot.say(f"Changed occurences of letter {letter.upper()} from {oldCount} to {count}!")

    def setCustomChance(self, bot, trigger):
        if trigger.group(2) == False:
            return bot.say("Bad value. Please use a percentage value between 1-100. e.g. !acrocustom 10")
        if trigger.group(2).isdigit() == False:
            return bot.say("Bad value. Please use a percentage value between 1-100. e.g. !acrocustom 10")
        chance = int(trigger.group(2))
        if chance > 100 or chance < 0:
            return bot.say("Bad value. Please use a percentage value between 1-100. e.g. !acrocustom 10")
        oldChance = bot.db.get_plugin_value('acro', 'custom_chance', 10)

        bot.db.set_plugin_value('acro', 'custom_chance', chance)

        return bot.say(f"Acro game's potential to play a custom acro has changed from {oldChance} to {chance}")


acro = AcroBot()

@module.commands('acro')
@module.example(".acro")
@module.priority('high')
@module.require_chanmsg
def acrostart(bot, trigger):
    """
    Start a game of acro in the current channel
    """
    acro.start(bot, trigger)

@module.rule("[A-Za-z,;:.-`~'!?'\"\\s]+")
@module.priority('high')
@module.require_privmsg
def submitacro(bot, trigger):
    """
    Player submitted an acro
    """
    acro.submitAcro(bot, trigger)

@module.rule("[0-9]")
@module.priority('high')
@module.require_privmsg
def voteacro(bot, trigger):
    """
    Player voted for an acro
    """
    acro.voteAcro(bot, trigger)

@module.commands('acroscores')
@module.example(".acroscores")
@module.priority('low')
@module.require_chanmsg
def acroScore(bot, trigger):
    """
    Show acro scores in channel
    """
    acro.highScore(bot, trigger)

@module.commands('addacro')
@module.example(".addacro")
@module.priority('low')
@module.require_privilege(module.OP, 'You require more minerals.')
@module.require_chanmsg
def addacro(bot, trigger):
    """
    Add a custom acro
    """
    acro.addAcro(bot, trigger)

@module.commands('delacro')
@module.example(".delacro")
@module.priority('low')
@module.require_owner('You require more minerals.')
@module.require_chanmsg
def delacro(bot, trigger):
    """
    Delete a custom acro
    """
    acro.delAcro(bot, trigger)

@module.commands('acrolog')
@module.example(".acrolog")
@module.priority('low')
@module.require_chanmsg
def acrolog(bot, trigger):
    """
    View log for a user
    """
    acro.generateLog(bot, trigger)

@module.commands('acrolist')
@module.example(".acrolist")
@module.priority('low')
@module.require_chanmsg
def acrocustoms(bot, trigger):
    """
    View a list of custom acros in the game
    """
    acro.generateCustom(bot)

@module.commands('acrochangescore')
@module.example(".acrochangescore")
@module.require_owner('You require more minerals.')
@module.priority('low')
def changescore(bot, trigger):
    """
    Change a users game wins on acro
    """
    acro.adjustScore(bot, trigger)

@module.commands('acroletters')
@module.example(".acroletters")
@module.priority('low')
def acroletters(bot, trigger):
    """
    View the probability of letters
    """
    acro.viewLetters(bot, trigger)

@module.commands('acroadjust')
@module.example(".acroadjust")
@module.priority('low')
@module.require_privilege(module.OP, 'You require more minerals.')
def acroadjust(bot, trigger):
    """
    Adjust the probability of letters
    """
    acro.adjustLetter(bot, trigger)

@module.commands('acrocustom')
@module.example(".acrocustom")
@module.priority('low')
@module.require_privilege(module.OP, 'You require more minerals.')
def acrocustom(bot, trigger):
    """
    Adjust the probability of letters
    """
    acro.setCustomChance(bot, trigger)
