# this is the start of our AI project
from __future__ import annotations
import argparse
import copy
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from time import sleep
from typing import Tuple, TypeVar, Type, Iterable, ClassVar
import random
import requests

# maximum and minimum values for our heuristic scores (usually represents an end of game condition)
MAX_HEURISTIC_SCORE = 2000000000
MIN_HEURISTIC_SCORE = -2000000000

class UnitType(Enum):
    """Every unit type."""
    AI = 0
    Tech = 1
    Virus = 2
    Program = 3
    Firewall = 4

class Player(Enum):
    """The 2 players."""
    Attacker = 0
    Defender = 1

    def next(self) -> Player:
        """The next (other) player."""
        if self is Player.Attacker:
            return Player.Defender
        else:
            return Player.Attacker

class GameType(Enum):
    AttackerVsDefender = 0
    AttackerVsComp = 1
    CompVsDefender = 2
    CompVsComp = 3

##############################################################################################################

@dataclass(slots=True)
class Unit:
    player: Player = Player.Attacker
    type: UnitType = UnitType.Program
    health : int = 9
    # class variable: damage table for units (based on the unit type constants in order)
    damage_table : ClassVar[list[list[int]]] = [
        [3,3,3,3,1], # AI
        [1,1,6,1,1], # Tech
        [9,6,1,6,1], # Virus
        [3,3,3,3,1], # Program
        [1,1,1,1,1], # Firewall
    ]
    # class variable: repair table for units (based on the unit type constants in order)
    repair_table : ClassVar[list[list[int]]] = [
        [0,1,1,0,0], # AI
        [3,0,0,3,3], # Tech
        [0,0,0,0,0], # Virus
        [0,0,0,0,0], # Program
        [0,0,0,0,0], # Firewall
    ]

    def is_alive(self) -> bool:
        """Are we alive ?"""
        return self.health > 0

    def mod_health(self, health_delta : int):
        """Modify this unit's health by delta amount."""
        self.health += health_delta
        if self.health < 0:
            self.health = 0
        elif self.health > 9:
            self.health = 9

    def to_string(self) -> str:
        """Text representation of this unit."""
        p = self.player.name.lower()[0]
        t = self.type.name.upper()[0]
        return f"{p}{t}{self.health}"
    
    def __str__(self) -> str:
        """Text representation of this unit."""
        return self.to_string()
    
    def damage_amount(self, target: Unit) -> int:
        """How much can this unit damage another unit."""
        #self.damage_table[[]]
        amount = self.damage_table[self.type.value][target.type.value]
        if target.health - amount < 0:
            return target.health
        return amount

    def repair_amount(self, target: Unit) -> int:
        """How much can this unit repair another unit."""
        amount = self.repair_table[self.type.value][target.type.value]
        if target.health + amount > 9:
            return 9 - target.health  
        return amount

##############################################################################################################

@dataclass(slots=True)
class Coord:
    """Representation of a game cell coordinate (row, col)."""
    row : int = 0
    col : int = 0

    def col_string(self) -> str:
        """Text representation of this Coord's column."""
        coord_char = '?'
        if self.col < 16:
                coord_char = "0123456789abcdef"[self.col]
        return str(coord_char)

    def row_string(self) -> str:
        """Text representation of this Coord's row."""
        coord_char = '?'
        if self.row < 26:
                coord_char = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[self.row]
        return str(coord_char)

    def to_string(self) -> str:
        """Text representation of this Coord."""
        return self.row_string()+self.col_string()
    
    def __str__(self) -> str:
        """Text representation of this Coord."""
        return self.to_string()
    
    def clone(self) -> Coord:
        """Clone a Coord."""
        return copy.copy(self)

    def iter_range(self, dist: int) -> Iterable[Coord]:
        """Iterates over Coords inside a rectangle centered on our Coord."""
        for row in range(self.row-dist,self.row+1+dist):
            for col in range(self.col-dist,self.col+1+dist):
                yield Coord(row,col)

    def iter_adjacent(self) -> Iterable[Coord]:
        """Iterates over adjacent Coords."""
        yield Coord(self.row-1,self.col)
        yield Coord(self.row,self.col-1)
        yield Coord(self.row+1,self.col)
        yield Coord(self.row,self.col+1)

    @classmethod
    def from_string(cls, s : str) -> Coord | None:
        """Create a Coord from a string. ex: D2."""
        s = s.strip()
        for sep in " ,.:;-_":
                s = s.replace(sep, "")
        if (len(s) == 2):
            coord = Coord()
            coord.row = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(s[0:1].upper())
            coord.col = "0123456789abcdef".find(s[1:2].lower())
            return coord
        else:
            return None

##############################################################################################################

@dataclass(slots=True)
class CoordPair:
    """Representation of a game move or a rectangular area via 2 Coords."""
    src : Coord = field(default_factory=Coord)
    dst : Coord = field(default_factory=Coord)

    def to_string(self) -> str:
        """Text representation of a CoordPair."""
        return self.src.to_string()+" "+self.dst.to_string()
    
    def __str__(self) -> str:
        """Text representation of a CoordPair."""
        return self.to_string()

    def clone(self) -> CoordPair:
        """Clones a CoordPair."""
        return copy.copy(self)

    def iter_rectangle(self) -> Iterable[Coord]:
        """Iterates over cells of a rectangular area."""
        for row in range(self.src.row,self.dst.row+1):
            for col in range(self.src.col,self.dst.col+1):
                yield Coord(row,col)

    @classmethod
    def from_quad(cls, row0: int, col0: int, row1: int, col1: int) -> CoordPair:
        """Create a CoordPair from 4 integers."""
        return CoordPair(Coord(row0,col0),Coord(row1,col1))
    
    @classmethod
    def from_dim(cls, dim: int) -> CoordPair:
        """Create a CoordPair based on a dim-sized rectangle."""
        return CoordPair(Coord(0,0),Coord(dim-1,dim-1))
    
    @classmethod
    def from_string(cls, s : str) -> CoordPair | None:
        """Create a CoordPair from a string. ex: A3 B2"""
        s = s.strip()
        for sep in " ,.:;-_":
                s = s.replace(sep, "")
        if (len(s) == 4):
            coords = CoordPair()
            coords.src.row = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(s[0:1].upper())
            coords.src.col = "0123456789abcdef".find(s[1:2].lower())
            coords.dst.row = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(s[2:3].upper())
            coords.dst.col = "0123456789abcdef".find(s[3:4].lower())
            return coords
        else:
            return None

##############################################################################################################

@dataclass(slots=True)
class Options:
    """Representation of the game options."""
    dim: int = 5
    max_depth : int | None = 5
    min_depth : int | None = 0
    max_time : float | None = 5.0
    game_type : GameType = GameType.AttackerVsDefender
    alpha_beta : bool = True
    e : str | None = None
    max_turns : int | None = 100
    randomize_moves : bool = True
    broker : str | None = None

##############################################################################################################

@dataclass(slots=True)
class Stats:
    """Representation of the global game statistics."""
    evaluations_per_depth : dict[int,int] = field(default_factory=dict)
    total_seconds: float = 0.0
    non_leaf : int = 0
    non_root : int = 0
    time_limit : bool = False

##############################################################################################################

@dataclass(slots=True)
class Game:
    """Representation of the game state."""
    board : list[list[Unit | None]] = field(default_factory=list)
    next_player : Player = Player.Attacker
    turns_played : int = 0
    start_time_comp : float = 0.0

    options: Options = field(default_factory=Options)
    stats: Stats = field(default_factory=Stats)
    _attacker_has_ai : bool = True
    _defender_has_ai : bool = True

    def __post_init__(self):
        """Automatically called after class init to set up the default board state."""
        dim = self.options.dim
        self.board = [[None for _ in range(dim)] for _ in range(dim)]
        md = dim-1
        self.set(Coord(0,0),Unit(player=Player.Defender,type=UnitType.AI))
        self.set(Coord(1,0),Unit(player=Player.Defender,type=UnitType.Tech))
        self.set(Coord(0,1),Unit(player=Player.Defender,type=UnitType.Tech))
        self.set(Coord(2,0),Unit(player=Player.Defender,type=UnitType.Firewall))
        self.set(Coord(0,2),Unit(player=Player.Defender,type=UnitType.Firewall))
        self.set(Coord(1,1),Unit(player=Player.Defender,type=UnitType.Program))
        self.set(Coord(md,md),Unit(player=Player.Attacker,type=UnitType.AI))
        self.set(Coord(md-1,md),Unit(player=Player.Attacker,type=UnitType.Virus))
        self.set(Coord(md,md-1),Unit(player=Player.Attacker,type=UnitType.Virus))
        self.set(Coord(md-2,md),Unit(player=Player.Attacker,type=UnitType.Program))
        self.set(Coord(md,md-2),Unit(player=Player.Attacker,type=UnitType.Program))
        self.set(Coord(md-1,md-1),Unit(player=Player.Attacker,type=UnitType.Firewall))

    def clone(self) -> Game:
        """Make a new copy of a game for minimax recursion.

        Shallow copy of everything except the board (options and stats are shared).
        """
        new = copy.copy(self)
        new.board = copy.deepcopy(self.board)
        return new

    def is_empty(self, coord : Coord) -> bool:
        """Check if contents of a board cell of the game at Coord is empty (must be valid coord)."""
        return self.board[coord.row][coord.col] is None

    def get(self, coord : Coord) -> Unit | None:
        """Get contents of a board cell of the game at Coord."""
        if self.is_valid_coord(coord):
            return self.board[coord.row][coord.col]
        else:
            return None

    def set(self, coord : Coord, unit : Unit | None):
        """Set contents of a board cell of the game at Coord."""
        if self.is_valid_coord(coord):
            self.board[coord.row][coord.col] = unit

    def remove_dead(self, coord: Coord):
        """Remove unit at Coord if dead."""
        unit = self.get(coord)
        if unit is not None and not unit.is_alive():
            self.set(coord,None)
            if unit.type == UnitType.AI:
                if unit.player == Player.Attacker:
                    self._attacker_has_ai = False
                else:
                    self._defender_has_ai = False

    def mod_health(self, coord : Coord, health_delta : int):
        """Modify health of unit at Coord (positive or negative delta)."""
        target = self.get(coord)
        if target is not None:
            target.mod_health(health_delta)
            self.remove_dead(coord)

    def is_valid_move(self, coords : CoordPair) -> bool:
        """Validate a move expressed as a CoordPair. TODO: WRITE MISSING CODE!!!"""

        if not self.is_valid_coord(coords.src) or not self.is_valid_coord(coords.dst):
            return False
        
        unitSRC = self.get(coords.src)
        unitDST = self.get(coords.dst)
        
        # if no unit is at current position or if unit at current position belongs to the opponent
        if unitSRC is None or unitSRC.player != self.next_player:
            return False

        # get all adjacent cells to current player
        cellADJ = coords.src.iter_adjacent()
        listADJ = [next(cellADJ), next(cellADJ), next(cellADJ), next(cellADJ)]

        # if unit self-destructs
        if coords.src == coords.dst:
            return True

        # if adjacent cell is occupied by opponent and target is opponent, unit attacks opponent
        if coords.dst in listADJ:
            if self.get(coords.dst) is not None and self.get(coords.dst).player != unitSRC.player:
                return True
        
        # if adjacent cell is occupied by opponent and is not attacked
        # already verified if unit attacked opponent 
        # therefore looking for first instance of a cell occupied by opponent that is not the target of unit
        # if unit is AI, Firewall or Program, unit will NOT move while in combat
        # unit can move in combat IF it is Tech or Virus
        for cell in listADJ:
            if self.get(cell) is not None and self.get(cell).player != unitSRC.player and (unitSRC.type == UnitType.AI or unitSRC.type == UnitType.Firewall or unitSRC.type == UnitType.Program):
                # unit is in combat mode and CANNOT move
                if cell != coords.dst:
                    return False
                
        # AI, Firewall and Program will NOT move if engaged in combat
        if unitSRC.type == UnitType.AI or unitSRC.type == UnitType.Firewall or unitSRC.type == UnitType.Program:
            # Attacker AI, F and P CAN move UP or LEFT
            if unitSRC.player == Player.Attacker:
                # legal moves for AI, Firewall and Program
                attackerMove = [listADJ[0], listADJ[1]] 
                if coords.dst not in attackerMove:
                    return False
            # Defender AI, F and P CAN move BOTTOM or RIGHT
            else:
                # legal moves for AI, Firewall and Program
                defenderMove = [listADJ[2], listADJ[3]]
                if coords.dst not in defenderMove:
                    return False
        # Tech and Virus CAN move in ALL directions at ALL times
        # check if target is adjacent to unit in any direction
        else:
            if coords.dst not in listADJ:
                return False

        # AI can repair Virus or Tech
        # Tech can repair AI, Firewall or Program
        # Repair will fail if unit's health is at maximum (already at 9)
        if unitDST is not None:
            if unitSRC.player == unitDST.player and unitSRC.type == UnitType.AI:
                if (unitDST.type == UnitType.Virus or unitDST.type == UnitType.Tech) and unitDST.health != 9:
                    return True
                else:
                    return False
            if unitSRC.player == unitDST.player and unitSRC.type == UnitType.Tech:
                if (unitDST.type == UnitType.AI or unitDST.type == UnitType.Firewall or unitDST.type == UnitType.Program) and unitDST.health != 9:
                    return True
                else:
                    return False

        # unit moves to empty cell
        else:
            return True

    def perform_move(self, coords : CoordPair) -> Tuple[bool,str]:
        """Validate and perform a move expressed as a CoordPair. TODO: WRITE MISSING CODE!!!"""
        unitSRC = self.get(coords.src)
        unitDST = self.get(coords.dst)

        cellADJ = coords.src.iter_adjacent()
        listADJ = [next(cellADJ), next(cellADJ), next(cellADJ), next(cellADJ)]
       
        if self.is_valid_move(coords):
            # if cell is free, perform move
            if self.get(coords.dst) is None:
                self.set(coords.dst,self.get(coords.src))
                self.set(coords.src,None)
                
                return (True,"move from " + str(coords.src) + " to " + str(coords.dst))

            elif coords.src == coords.dst:
                # if unit self-destructs
                # inflict 2 pts of damage to all units in its surroundings
                # unit is removed from board
                cellCorner = listADJ[0].iter_adjacent()
                listTopCorner = [next(cellCorner), next(cellCorner), next(cellCorner), next(cellCorner)]
                cellCorner = listADJ[2].iter_adjacent()
                listBottomCorner = [next(cellCorner), next(cellCorner), next(cellCorner), next(cellCorner)]

                listADJ.append(listTopCorner[1])
                listADJ.append(listTopCorner[3])
                listADJ.append(listBottomCorner[1])
                listADJ.append(listBottomCorner[3])

                for cell in listADJ:
                    if self.get(cell) is not None:
                        self.mod_health(cell, -2)
                self.mod_health(coords.src, -9)

                return (True,"self-destruct at " + str(coords.src))

            # if unit is AI or Tech, it can repair another unit
            elif self.get(coords.src).player == self.get(coords.dst).player and self.get(coords.src).type == UnitType.AI:
                self.mod_health(coords.dst, unitSRC.repair_amount(unitDST))

                return (True,"repair from " + str(coords.src) + " to " + str(coords.dst))

            elif self.get(coords.src).player == self.get(coords.dst).player and self.get(coords.src).type == UnitType.Tech:
                self.mod_health(coords.dst, unitSRC.repair_amount(unitDST))

                return (True,"repair from " + str(coords.src) + " to " + str(coords.dst))
            
            # if unit attacks
            # unit causes damage to target and vice versa
            else:
                self.mod_health(coords.src, -unitDST.damage_amount(unitSRC))
                self.mod_health(coords.dst, -unitSRC.damage_amount(unitDST))
                
                return (True,"attack from " + str(coords.src) + " to " + str(coords.dst))

        return (False,"invalid move")

    def next_turn(self):
        """Transitions game to the next turn."""
        self.next_player = self.next_player.next()
        self.turns_played += 1

    def to_string(self) -> str:
        """Pretty text representation of the game."""
        dim = self.options.dim
        output = ""
        configuration = ""
        output += f"Next player: {self.next_player.name}\n"
        output += f"Turns played: {self.turns_played}\n"
        if self.turns_played == 0:
            configuration += f"Initial configuration: \n"
        coord = Coord()
        output += "\n   "
        configuration += "   "
        for col in range(dim):
            coord.col = col
            label = coord.col_string()
            output += f"{label:^3} "
            configuration += f"{label:^3} "
        output += "\n"
        configuration += "\n"
        for row in range(dim):
            coord.row = row
            label = coord.row_string()
            output += f"{label}: "
            configuration += f"{label}: "
            for col in range(dim):
                coord.col = col
                unit = self.get(coord)
                if unit is None:
                    output += " .  "
                    configuration += " .  "
                else:
                    output += f"{str(unit):^3} "
                    configuration += f"{str(unit):^3} "
            output += "\n"
            configuration += "\n"
        gameTraceFile = "gameTrace-" + str(self.options.alpha_beta) + "-" + str(self.options.max_time) + "-" + str(self.options.max_turns) + ".txt"
        file = open(gameTraceFile, "a")
        file.writelines(configuration + "\n")
        file.close()
                
        return output

    def __str__(self) -> str:
        """Default string representation of a game."""
        return self.to_string()
    
    def is_valid_coord(self, coord: Coord) -> bool:
        """Check if a Coord is valid within out board dimensions."""
        dim = self.options.dim
        if coord.row < 0 or coord.row >= dim or coord.col < 0 or coord.col >= dim:
            return False
        return True

    def read_move(self) -> CoordPair:
        """Read a move from keyboard and return as a CoordPair."""
        while True:
            s = input(F'Player {self.next_player.name}, enter your move: ')
            coords = CoordPair.from_string(s)
            if coords is not None and self.is_valid_coord(coords.src) and self.is_valid_coord(coords.dst):
                return coords
            else:
                print('Invalid coordinates! Try again.')
    
    def human_turn(self):
        """Human player plays a move (or get via broker)."""
        gameTraceFile = "gameTrace-" + str(self.options.alpha_beta) + "-" + str(self.options.max_time) + "-" + str(self.options.max_turns) + ".txt"

        file = open(gameTraceFile, 'a')

        if self.options.broker is not None:
            print("Getting next move with auto-retry from game broker...")
            while True:
                mv = self.get_move_from_broker()
                if mv is not None:
                    (success,result) = self.perform_move(mv)
                    print(f"Broker {self.next_player.name}: ",end='')
                    print(result)
                    if success:
                        self.next_turn()
                        break
                sleep(0.1)
        else:
            file.writelines("turn # " + str(self.turns_played + 1) + ": " + self.next_player.name + "\n")
            while True:
                mv = self.read_move()
                file.writelines("Player " + self.next_player.name + ", enter your move: "  + str(mv) + "\n")
                (success,result) = self.perform_move(mv)
                if success:
                    print(f"Player {self.next_player.name}: ",end='')
                    print(result)
                    file.writelines(self.next_player.name + ": " + result + "\n")
                    file.close()
                    self.next_turn()
                    break
                else:
                    file.writelines("The move is not valid! Try again.\n")
                    print("The move is not valid! Try again.")

    def computer_turn(self) -> CoordPair | None:
        """Computer plays a move."""
        gameTraceFile = "gameTrace-" + str(self.options.alpha_beta) + "-" + str(self.options.max_time) + "-" + str(self.options.max_turns) + ".txt"
        file = open(gameTraceFile, 'a')

        (move, elapsed_seconds, score, total_evals, evals_depth, evals_percentage, avg_branching) = self.suggest_move()
        if move is not None:
            (success,result) = self.perform_move(move)
            if success:
                file.writelines("turn # " + str(self.turns_played + 1) + ": " + self.next_player.name + "\n")
                print(f"Computer {self.next_player.name}: ",end='')
                print(result)
                print("Elapsed time: " + str(elapsed_seconds))
                print("Heuristic score: " + str(score))
                print("Culmulative evals: " + str(total_evals))
                print("Culmulative evals per depth: " + evals_depth)
                print("Culmulative % evals per depth: " + evals_percentage)
                if self.stats.total_seconds > 0:
                    print(f"Eval perf.: {total_evals/self.stats.total_seconds/1000:0.3f}k/s")
                print("Average branching factor: " + str(avg_branching) + "\n")
                file.writelines("Computer "+ self.next_player.name + ": " + result + "\n")
                file.writelines("Elapsed time: " + str(elapsed_seconds) + "\n")
                file.writelines("Heuristic score: " + str(score) + "\n")
                file.writelines("Culmulative evals: " + str(total_evals) + "\n")
                file.writelines("Culmulative evals per depth: " + evals_depth + "\n")
                file.writelines("Culmulative % evals per depth: " + evals_percentage + "\n")
                if self.stats.total_seconds > 0:
                    file.writelines("Eval perf.: " + str(round((total_evals/self.stats.total_seconds/1000), 3)) + "k/s\n")
                file.writelines("Average branching factor: " + str(avg_branching) + "\n")
                file.close()
                self.next_turn()

                if elapsed_seconds > self.options.max_time:
                    self.stats.time_limit = True
        return move

    def player_units(self, player: Player) -> Iterable[Tuple[Coord,Unit]]:
        """Iterates over all units belonging to a player."""
        for coord in CoordPair.from_dim(self.options.dim).iter_rectangle():
            unit = self.get(coord)
            if unit is not None and unit.player == player:
                yield (coord,unit)

    def is_finished(self) -> bool:
        """Check if the game is over."""
        return self.has_winner() is not None

    def has_winner(self) -> Player | None:
        """Check if the game is over and returns winner"""
        # if max turns is reached, defender wins
        if self.options.max_turns is not None and self.turns_played >= self.options.max_turns:
            return Player.Defender
        # if time limit is surpassed by the ai, ai looses and opponent wins
        if self.stats.time_limit == True:
            return self.next_player
        if self._attacker_has_ai:
            if self._defender_has_ai:
                return None
            else:
                return Player.Attacker    
        return Player.Defender

    def move_candidates(self) -> Iterable[CoordPair]:
        """Generate valid move candidates for the next player."""
        move = CoordPair()
        for (src,_) in self.player_units(self.next_player):
            move.src = src
            for dst in src.iter_adjacent():
                move.dst = dst
                if self.is_valid_move(move) == True:
                    yield move.clone()
            move.dst = src
            yield move.clone()

    def random_move(self) -> Tuple[int, CoordPair | None, float]:
        """Returns a random move."""
        move_candidates = list(self.move_candidates())
        random.shuffle(move_candidates)
        if len(move_candidates) > 0:
            return (0, move_candidates[0], 1)
        else:
            return (0, None, 0)

    def heuristics(self, game: Game, child: CoordPair) -> int:
        nbAttackerV =  nbAttackerT =  nbAttackerF =  nbAttackerP =  nbAttackerAI = 0
        nbDefenderV =  nbDefenderT =  nbDefenderF =  nbDefenderP = nbDefenderAI = 0

        healthAttackerV = healthAttackerT = healthAttackerF = healthAttackerP  =  healthAttackerAI = 0
        healthDefenderV = healthDefenderT = healthDefenderF = healthDefenderP = healthDefenderAI = 0

        if game.next_player == Player.Attacker:
            attacker_units = game.player_units(game.next_player)
            defender_units = game.player_units(game.next_player.next())
        else:
            attacker_units = game.player_units(game.next_player.next())
            defender_units = game.player_units(game.next_player)
        
        for unitA in attacker_units:
            if unitA[1].type == UnitType.Virus:
                healthAttackerV += unitA[1].health
                nbAttackerV += 1
            elif unitA[1].type == UnitType.Tech:
                healthAttackerT += unitA[1].health
                nbAttackerT += 1
            elif unitA[1].type == UnitType.Firewall:
                healthAttackerF += unitA[1].health
                nbAttackerF += 1
            elif unitA[1].type == UnitType.Program:
                healthAttackerP += unitA[1].health
                nbAttackerP += 1
            else:
                healthAttackerAI += unitA[1].health
                nbAttackerAI += 1
                        
        for unitD in defender_units:
            if unitD[1].type == UnitType.Virus:
                healthDefenderV += unitD[1].health
                nbDefenderV += 1
            elif unitD[1].type == UnitType.Tech:
                healthDefenderT += unitD[1].health
                nbDefenderT += 1                
            elif unitD[1].type == UnitType.Firewall:
                healthDefenderF += unitD[1].health
                nbDefenderF += 1
            elif unitD[1].type == UnitType.Program:
                healthDefenderP += unitD[1].health
                nbDefenderP += 1
            else:
                healthDefenderAI += unitD[1].health
                nbDefenderAI += 1
                        
        if game.options.e == "e0" :
            e0 = (3 * (nbAttackerV + nbAttackerT + nbAttackerF + nbAttackerP) + 9999 * nbAttackerAI) - (3 * (nbDefenderV + nbDefenderT + nbDefenderF + nbDefenderP) + 9999 * nbDefenderAI)
            return e0
        elif game.options.e == "e1":
            e1 = ((healthAttackerV * nbAttackerV + healthAttackerT * nbAttackerT + healthAttackerF *nbAttackerF + healthAttackerP * nbAttackerP + 9999 * healthAttackerAI * nbAttackerAI) - (healthDefenderV * nbDefenderV + healthDefenderT * nbDefenderT + healthDefenderF *nbDefenderF + healthDefenderP * nbDefenderP + 9999 * healthDefenderAI * nbDefenderAI) )
            return e1
        elif game.options.e == "e2":
            e2 = (((healthAttackerV + 8 * nbAttackerV) + (healthAttackerT + 10 * nbAttackerT) + (healthAttackerF + 10 * nbAttackerF) + (healthAttackerP + 8 * nbAttackerP) + 9999 * healthAttackerAI * nbAttackerAI) - ((healthDefenderV * nbDefenderV) + (healthDefenderT + 8 * nbDefenderT) + (healthDefenderF+8 * nbDefenderF) + (healthDefenderP +10 * nbDefenderP) + 9999 * healthDefenderAI * nbDefenderAI) ) #/ (nbAttackerV + nbAttackerT + nbAttackerF + nbAttackerP + nbAttackerAI -( nbDefenderV + nbDefenderT + nbDefenderF + nbDefenderP + nbDefenderAI))
            return e2

    def minimax(self, game: Game, node: CoordPair, depth: int, alpha: int, beta: int, maximizing: bool) -> int:
        self.stats.evaluations_per_depth[self.options.max_depth - depth] += 1

        # check time for time limit
        elapsed_seconds = (datetime.now() - self.start_time_comp).total_seconds()
        if depth == 0 or (self.options.max_time - elapsed_seconds) <= (1 / self.options.max_depth) / 10:
            return self.heuristics(game, node)
        
        node_clone = self.clone()
        (success, result) = node_clone.perform_move(node)
        # next move will belong to opponent
        node_clone.next_player = node_clone.next_player.next()
        node_list = []
        if success:
            node_list = list(node_clone.move_candidates())
            # if node produces children it is a non-leaf node
            self.stats.non_leaf += 1
            # all children produced are non-root nodes
            self.stats.non_root += len(node_list)

        if maximizing:
            max_eval = MIN_HEURISTIC_SCORE
            for child_node in node_list:
                v = node_clone.minimax(node_clone, child_node, depth - 1, alpha, beta, False)
                max_eval = max(max_eval, v)
                alpha = max(alpha, v)
                # perform alpha-beta pruning if alpha_beta == True
                if node_clone.options.alpha_beta == True:
                    if beta <= alpha:
                        break
            return max_eval
        else:
            min_eval = MAX_HEURISTIC_SCORE
            for child_node in node_list:
                v = node_clone.minimax(node_clone, child_node, depth - 1, alpha, beta, True)
                min_eval = min(min_eval, v)
                beta = min(beta, v)
                # perform alpha-beta pruning if alpha_beta == True
                if node_clone.options.alpha_beta == True:
                    if beta <= alpha:
                        break 
            return min_eval

    def suggest_move(self) -> CoordPair | None:
        """Suggest the next move using minimax alpha beta. TODO: REPLACE RANDOM_MOVE WITH PROPER GAME LOGIC!!!"""

        # computer starts timer for time limit to return a move
        self.start_time_comp = datetime.now()

        self.stats.non_root = self.stats.non_leaf = 0

        # clone the game for minimax/alpha-beta
        minimax_clone = self.clone()
        minimax_clone_move_candidate = list(minimax_clone.move_candidates())

        move = None
        score = 0
        dict = {}
        value = 0

        max_depth_set = minimax_clone.options.max_depth - 1

        # minimax/alpha-beta maximizes if computer is the attacker
        maximize = True

        # minimax/alpha-beta minimizes if computer is the defender
        if minimax_clone.next_player != Player.Attacker:
            maximize = False

        self.stats.evaluations_per_depth[0] += 1

        # root is a non-leaf node
        self.stats.non_leaf += 1

        # perform minimax on the clone
        for i in range(len(minimax_clone_move_candidate)):
            # check if time is up
            elapsed_seconds = (datetime.now() - self.start_time_comp).total_seconds()
            if (self.options.max_time - elapsed_seconds) <= (1 / self.options.max_depth) / 10:
                break
            child = minimax_clone_move_candidate[i]
            # children of node are non-root nodes
            self.stats.non_root += 1
            value = minimax_clone.minimax(minimax_clone, child, max_depth_set, MIN_HEURISTIC_SCORE, MAX_HEURISTIC_SCORE, maximize)
            dict[value] = child

        # select move based on heuristic score
        # if computer is the attacker, select move with highest heuristic score
        # if computer is the defender, select move with the lowest heuristic score
        if minimax_clone.next_player == Player.Attacker:
            score = max(dict)
            move = dict[score]  
        else:        
            score = min(dict)    
            move = dict[score]

        # produce stats of the game
        elapsed_seconds = (datetime.now() - self.start_time_comp).total_seconds()
        self.stats.total_seconds += elapsed_seconds
        total_evals = sum(self.stats.evaluations_per_depth.values())
        evals_depth = ""
        for k in sorted(self.stats.evaluations_per_depth.keys()):
            evals_depth += (str(k) + "=" + str(self.stats.evaluations_per_depth[k]) + " ")
        evals_percentage = ""
        for k in sorted(self.stats.evaluations_per_depth.keys()):
            evals_percentage += (str(k) + "=" + str(round((self.stats.evaluations_per_depth[k] * 100 / total_evals), 4)) + "% ")
        avg_branching = round((self.stats.non_root/self.stats.non_leaf), 3)

        return (move, elapsed_seconds, score, total_evals, evals_depth, evals_percentage, avg_branching)

    def post_move_to_broker(self, move: CoordPair):
        """Send a move to the game broker."""
        if self.options.broker is None:
            return
        data = {
            "from": {"row": move.src.row, "col": move.src.col},
            "to": {"row": move.dst.row, "col": move.dst.col},
            "turn": self.turns_played
        }
        try:
            r = requests.post(self.options.broker, json=data)
            if r.status_code == 200 and r.json()['success'] and r.json()['data'] == data:
                # print(f"Sent move to broker: {move}")
                pass
            else:
                print(f"Broker error: status code: {r.status_code}, response: {r.json()}")
        except Exception as error:
            print(f"Broker error: {error}")

    def get_move_from_broker(self) -> CoordPair | None:
        """Get a move from the game broker."""
        if self.options.broker is None:
            return None
        headers = {'Accept': 'application/json'}
        try:
            r = requests.get(self.options.broker, headers=headers)
            if r.status_code == 200 and r.json()['success']:
                data = r.json()['data']
                if data is not None:
                    if data['turn'] == self.turns_played+1:
                        move = CoordPair(
                            Coord(data['from']['row'],data['from']['col']),
                            Coord(data['to']['row'],data['to']['col'])
                        )
                        print(f"Got move from broker: {move}")
                        return move
                    else:
                        # print("Got broker data for wrong turn.")
                        # print(f"Wanted {self.turns_played+1}, got {data['turn']}")
                        pass
                else:
                    # print("Got no data from broker")
                    pass
            else:
                print(f"Broker error: status code: {r.status_code}, response: {r.json()}")
        except Exception as error:
            print(f"Broker error: {error}")
        return None

##############################################################################################################

def main():
    # parse command line arguments
    parser = argparse.ArgumentParser(
        prog='ai_wargame',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--max_depth', type=int, help='maximum search depth')
    parser.add_argument('--max_time', type=float, help='maximum search time')
    parser.add_argument('--game_type', type=str, default="manual", help='game type: auto|attacker|defender|manual')
    parser.add_argument('--broker', type=str, help='play via a game broker')
    args = parser.parse_args()

    # parse the game type
    if args.game_type == "attacker":
        game_type = GameType.AttackerVsComp
    elif args.game_type == "defender":
        game_type = GameType.CompVsDefender
    elif args.game_type == "manual":
        game_type = GameType.AttackerVsDefender
    else:
        game_type = GameType.CompVsComp

    # set up game options
    options = Options(game_type=game_type)

    # override class defaults via command line options
    if args.max_depth is not None:
        options.max_depth = args.max_depth
    if args.max_time is not None:
        options.max_time = args.max_time
    if args.broker is not None:
        options.broker = args.broker

    # create a new game
    game = Game(options=options)

    option_gameType = False

    while option_gameType == False:
        input_game_type = input(f"Enter the game type (manual, attacker, defender or comp): ")
        if input_game_type == "manual":
            game.options.game_type =  GameType.AttackerVsDefender
            option_gameType = True
        elif input_game_type == "attacker":
           game.options.game_type = GameType.AttackerVsComp
           option_gameType = True
        elif input_game_type == "defender":
            game.options.game_type = GameType.CompVsDefender
            option_gameType = True
        elif input_game_type == "comp":
            game.options.game_type = GameType.CompVsComp
            option_gameType = True
        else: 
            print("invalid input, please try again")

    option_turns = False

    while option_turns == False:
        input_max_turns = input(f"Enter the max amount of turns or leave empty to keep default max amount of turns at 100: ")
        if input_max_turns.isdigit():
            game.options.max_turns = int(input_max_turns)
            option_turns = True
        elif input_max_turns == "":
            option_turns = True
        else:
            print("Invalid input, please try again.")
    
    if game.options.game_type != GameType.AttackerVsDefender:
        max_time_option = False
        while max_time_option == False:
            input_max_time = input(f"Enter the max amount of time the computer has to return a move or leave empty to keep default max amount of time at 5.0s: ")
            if input_max_time.replace('.', '', 1).isdigit():
                game.options.max_time = float(input_max_time)
                max_time_option = True
            elif input_max_time == "":
                max_time_option = True
            else:
                print("Invalid input, please try again.")

        alpha_option_beta = False
        while alpha_option_beta == False:
            input_alpha_beta = input(f"Enter 'True' to use alpha-beta or 'False' to use minimax: ")
            if input_alpha_beta == "True":
                game.options.alpha_beta = True
                alpha_option_beta = True
            elif input_alpha_beta == "False":
                game.options.alpha_beta = False
                alpha_option_beta = True
            else: 
                print("Invalid input, please try again.")

        options_depth = False
        while options_depth == False:
            input_max_depth = input(f"Enter the max depth for heuritic search or leave empty to keep default max depth at 5: ")
            if input_max_depth.isdigit():
                game.options.max_depth = int(input_max_depth)
                options_depth = True
            elif input_max_depth == "":
                options_depth = True
            else:
                print("Invalid input, please try again.")    

        while game.options.e == None:
            input_e = input(f"Enter the heuristics chosen for the computer (e0, e1 or e2): ")
            if input_e == "e0" or "e1" or "e2":
                game.options.e = input_e
            else:
                print(f"Invalid input please try again.")

    gameTraceFile = "gameTrace-" + str(options.alpha_beta) + "-" + str(options.max_time) + "-" + str(options.max_turns) + ".txt"
    file = open(gameTraceFile, 'w')

    file.writelines("t = " + str(options.max_time) + "\n")
    file.writelines("m = " + str(options.max_turns) + "\n")

    if game.options.game_type != GameType.AttackerVsDefender:
        alpha_beta = ""
        if options.alpha_beta == True:
            alpha_beta = "alpha-beta = ON"
        else:
            alpha_beta = "alpha-beta = OFF"
        file.writelines(alpha_beta + "\n")
        file.writelines("heuristics = " + options.e + "\n")
        for depth in range(game.options.max_depth + 1):
            game.stats.evaluations_per_depth[depth] = 0

    if game.options.game_type == GameType.AttackerVsDefender:
        file.writelines("player 1 = H & player 2 = H" + "\n\n")
    elif game.options.game_type == GameType.AttackerVsComp and game.next_player == Player.Attacker:
        file.writelines("player 1 = H & player 2 = AI" + "\n\n")
    elif game.options.game_type == GameType.CompVsDefender and game.next_player == Player.Defender:
        file.writelines("player 1 = AI & player 2 = H" + "\n\n")
    else:
        file.writelines("player 1 = AI & player 2 = AI" + "\n\n")

    file.close()

    # the main game loop
    while True:
        print()
        print(game)
        winner = game.has_winner()
        if winner is not None:
            print(f"{winner.name} wins!")
            file = open(gameTraceFile, 'a')
            file.writelines(winner.name + " wins in " + str(game.turns_played) + " turns!")
            file.close()  
            break
        if game.options.game_type == GameType.AttackerVsDefender:
            game.human_turn()
        elif game.options.game_type == GameType.AttackerVsComp and game.next_player == Player.Attacker:
            game.human_turn()
        elif game.options.game_type == GameType.CompVsDefender and game.next_player == Player.Defender:
            game.human_turn()
        else:
            player = game.next_player
            move = game.computer_turn()
            if move is not None:
                game.post_move_to_broker(move)
            else:
                print("Computer doesn't know what to do!!!")
                exit(1)

##############################################################################################################

if __name__ == '__main__':
    main()
