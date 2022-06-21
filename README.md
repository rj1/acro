## acro
an irc game where you create hilarious phrases based on acronyms with your friends!

a simple & fun irc game, where people make phrases (acronyms) with letters which the bot gives you. for example, the bot will start a round w/ an acronym, e.g. 'yeis', and you'll come up with an acronym, e.g. 'your epidermis is showing', and submit it privately to the game bot.

after 60 seconds, the bot will display each acronym submission anonymously, and every player can vote for other acronyms (you can't vote for your own). the creator of the acronym with the most votes wins the round! each round win gains you 3 points, and games usually go up to 15 points, though this could be changed.

this code is a module for [sopel](https://sopel.chat/), an irc bot framework created w/ python.

have fun!

p.s. join #acro on the [efnet irc network](http://www.efnet.org/) to try this game out. ask for fred.

rest in peace Emi

#### commands
| command | description | example | priv lvl |
| ---     | ---         | ---     | ---      |
|.acro|	start a new game of acro|.acro	|user
|.acroscores|show the high scores for acro|.acroscores|user
|.acrochangescore <user> <#>|change a users game wins|.acrochangescore knivey 5|bot owner
|.addacro <acro>|add a custom acro to the game|.addacro knivey|op
|.delacro <acro>|delete a custom acro from the game|.delacro knivey|bot owner
|.acrocustom <#>|change the odds that a custom acro will appear in the game|.acrocustom 10|op
|.acrolist|view a list of the custom acros available in the game|.acrolist|user
|.acrolog <user> (parameter optional)|view a list of acros that <user> has submitted, without the <user> parameter it will show your acros|.acrolog knivey|user
|.acroletters <letter> (parameter optional)|see the probability of letters appearing in the game|.acroletters a|user
|.acroadjust <letter> <#>|change the probability for a letter to appear in the game|.acroadjust a 13|op
