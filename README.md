# AI-PROJECT-FALL-2023

This project aims to create a 2-player wargame (attacker vs defender) between human-human, human-ai, ai-human or ai-ai.

## To start the game:
1. Install the request module using the terminal if it is not already installed : 
        
        pip install requests
2. Run the command below on your terminal at the location of the file. This will run the game:
    
        python project_code.py
3. Enter an input (manual, attacker, defender or comp) to choose the game type.
4. When prompted, enter additional game options:
    
    a. for all game types: enter the max amount of moves before the game ends
    
    b. for attacker, defender or comp: 
    - enter the max allowed time the ai has to return a move
    - select the use of minimax (False) or alpha-beta (True)
    - enter the maximum depth for adversarial search 
    - enter the heuristic chosen (e0, e1 or e2)
5. The game will start once the game options have been set.

## To play the game:
1. When prompted enter a valid move by specifying the coordinates of the source S followed by the coordinates of the target T (eg. E2 D2) or wait until the ai returns a move
2. The game will end when a player's AI has been destroyed or when the game reaches its maximum number of turns in which case the defender will be declared as the winner.

## Some rules for moves allowed:
1. A unit at S can move to an adjacent cell if said cell is empty.

    - Attacker AI, Firewall or Program CAN move UP or LEFT.
    
    - Defenders AI, Firewall or Program CAN move DOWN or RIGHT.
    
    - Tech and Virus CAN move in ANY direction.
2. A unit can attack an opponent's unit if they are adjacent to one another. The amount of damage they cause to each other is based on a  damage table
3. A unit is engaged in combat if it is adjacent to an opponent's unit.
    
    - If the unit is an AI, Firewall or Program and engaged in combat, it is locked into place and is unable to move.
    
    - Tech and Virus can move freely even when engaged in combat.
4. A unit can self-destruct. This will result in 2pts of damage to all surrounding units.
5. An AI or Tech unit can repair a unit if it belongs to them. The repairs allowed are based on a repair table.
6. If the current player plays an invalid move:
    - The player will only receive a warning if the player is a human, and can reattempt moves indefinitely.
    - The player immediately looses the game if the player is a ai.
7. For an ai, if it performs an illegal move or if it exceeds the time limit it has to return a move, it will immediately loose the game.

