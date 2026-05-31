from __future__ import annotations
from enum import Enum
from typing import Self
from dataclasses import dataclass, replace
import random
from typing import Generator

@dataclass(frozen=True, eq=True)
class Location:
    row: int
    col: int

    def __lt__(self, other: Self) -> bool:
        if self.row < other.row:
            return True
        elif self.row == other.row:
            return self.col < other.col
        else:
            return False


@dataclass(frozen=True, eq=True)
class MapTile:
    pass


@dataclass(frozen=True, eq=True)
class EmptyTile(MapTile):
    def __str__(self):
        return " "


@dataclass(frozen=True, eq=True)
class Wall(MapTile):
    def __str__(self):
        return "#"

@dataclass(frozen=True, eq=True)
class Portal(MapTile):
    def __str__(self):
        return "P"

@dataclass(frozen=True, eq=True)
class Lava(MapTile):
    def __str__(self):
        return "L"


@dataclass(frozen=True, eq=True)
class Crystal(MapTile):
    def __str__(self):
        return "C"

@dataclass(frozen=True, eq=True)
class Entity:
    id: int = 0

    def __lt__(self, other) -> bool:
        return self.id < other.id


@dataclass(frozen=True, eq=True)
class EmptyEntity(Entity):
    def __str__(self):
        return " "


@dataclass(frozen=True, eq=True)
class Wizard(Entity):
    def __str__(self):
        return "W"

class WizardMoves(Enum):
    UP = (-1, 0)
    DOWN = (1, 0)
    RIGHT = (0, 1)
    LEFT = (0, -1)
    STAY = (0, 0)


    def __str__(self):
        return f"Wizard {self.name}"



@dataclass(frozen=True, eq=True)
class Observation:
    approximatePortalDist: int



GameAction = WizardMoves


@dataclass(frozen=True, eq=True)
class GameState:
    grid_size: tuple[int, int]
    tile_grid: tuple[tuple[MapTile, ...], ...]
    entity_grid: tuple[tuple[Entity, ...], ...]
    active_entity_location: Location
    turn: int = 0
    score: int =0
    victory:bool = False
    defeat:bool = False

    def win(self) -> Self:
        return replace(self, victory=True)

    def lose(self) -> Self:
        return replace(self, defeat=True)

    def advance_turn(self) -> Self:
        return replace(self, turn=self.turn + 1)

    def replace_score(self, new_score: int) -> Self:
        return replace(self, score=new_score)


    def replace_active_entity_location(self, loc: Location) -> Self:
        prev = self.active_entity_location
        entity = self.entity_grid[prev.row][prev.col]
        new_state = self.replace_entity(prev.row,prev.col,EmptyEntity()).replace_entity(loc.row,loc.col,entity)
        return replace(new_state, active_entity_location=loc)

    def replace_entity(self, row: int, col: int, new_entity: Entity) -> Self:
        list_grid = list([list(row) for row in self.entity_grid])
        list_grid[row][col] = new_entity
        return replace(self, entity_grid=tuple((tuple(row) for row in list_grid)))

    def replace_tile(self, row: int, col: int, new_tile: MapTile) -> Self:
        list_grid = list([list(row) for row in self.tile_grid])
        list_grid[row][col] = new_tile
        return replace(self, tile_grid=tuple((tuple(row) for row in list_grid)))

    def get_all_tile_locations(self, type) -> list[Location]:
        locs: list[Location] = []
        for r, row in enumerate(self.tile_grid):
            for c, tile in enumerate(row):
                if isinstance(tile, type):
                    locs.append(Location(row=r, col=c))
        return locs

    def get_all_entity_locations(self, type) -> list[Location]:
        locs: list[Location] = []
        for r, row in enumerate(self.entity_grid):
            for c, entity in enumerate(row):
                if isinstance(entity, type):
                    locs.append(Location(row=r, col=c))
        return locs

    def get_active_entity(self) -> Entity:
        return self.entity_grid[self.active_entity_location.row][
            self.active_entity_location.col
        ]



    def observe(self) -> Observation:
        wizard_loc = self.active_entity_location
        portal_loc = self.get_all_tile_locations(Portal)

        def dist(a:Location,b:Location)-> int:
            return abs(a.row-b.row) + abs(a.col-b.col)

        portal_dist = dist(wizard_loc,portal_loc[0])
        portal_noise = random.randint(-1,1)

        obs_portal_dist = portal_dist + portal_noise
        return Observation(obs_portal_dist)


    def __lt__(self, other: Self) -> bool:
        my_hash = hash(self)
        other_hash = hash(other)
        return my_hash < other_hash

    def __str__(self):
        lines = []
        lines.append("GameState:")
        lines.append(f"Grid Size: {self.grid_size}")
        lines.append(
            f"Active Entity: {repr(self.get_active_entity())} @ {self.active_entity_location}"
        )

        lines.append("\n")

        lines.append(f"Tile Grid: {self.grid_size}")
        tile_grid_lines = []
        tile_grid_lines.append("".join(["-"] * (2 * self.grid_size[1] + 3)))
        for grid_line in self.tile_grid:
            tile_grid_lines.append(
                " ".join(["|"] + [str(tile) for tile in grid_line] + ["|"])
            )
        tile_grid_lines.append("".join(["-"] * (2 * self.grid_size[1] + 3)))

        lines.append("\n".join(tile_grid_lines))
        lines.append("\n")

        lines.append(f"Entity Grid: {self.grid_size}")
        entity_grid_lines = []
        entity_grid_lines.append("".join(["-"] * (2 * self.grid_size[1] + 3)))
        for entity_line in self.entity_grid:
            entity_grid_lines.append(
                " ".join(["|"] + [str(entity) for entity in entity_line] + ["|"])
            )
        entity_grid_lines.append("".join(["-"] * (2 * self.grid_size[1] + 3)))

        lines.append("\n".join(entity_grid_lines))

        entity_grid_lines.append("".join(["-"] * (2 * self.grid_size[1] + 3)))

        lines.append("\n")

        return "\n".join(lines)


class GameTransitions:
    def get_successors(source: GameState) -> tuple[tuple[GameAction, GameState], ...]:
        if source.victory or source.defeat:
            return ()

        wizard = source.get_active_entity()
        wizard_loc = source.active_entity_location

        if not isinstance(wizard, Wizard):
            raise ValueError(
                f"Tried to calculate wizard action successors for Game State : {source},  with active entity : {wizard}"
            )

        transitions: list[tuple[GameAction, GameState]] = []


        for action in WizardMoves:
            dir_row, dir_col = action.value
            target = Location(wizard_loc.row + dir_row, wizard_loc.col + dir_col)
            in_bounds = (0 <= target.row < source.grid_size[0]) and (
                0 <= target.col < source.grid_size[1]
            )
            if in_bounds:
                target_tile = source.tile_grid[target.row][target.col]
                target_entity = source.entity_grid[target.row][target.col]
                if action == WizardMoves.STAY:
                    successor = source.advance_turn()
                    transitions.append(
                        (
                            action,
                            successor,
                        )
                    )

                if isinstance(target_tile, EmptyTile):
                    if isinstance(target_entity, EmptyEntity):
                        successor = (
                            (
                                source
                                .replace_active_entity_location(target)
                            )
                            .advance_turn()
                        )
                        transitions.append(
                            (
                                action,
                                successor,
                            )
                        )
                elif isinstance(target_tile, Crystal):
                    if isinstance(target_entity, EmptyEntity):
                        successor = (
                            (
                                source.replace_tile(target.row, target.col, EmptyTile())
                                .replace_entity(target.row, target.col, wizard)
                                .replace_active_entity_location(target)
                                .replace_score(source.score +1)
                            )
                            .advance_turn()
                        )
                        transitions.append(
                            (
                                action,
                                successor,
                            )
                        )
                elif isinstance(target_tile, Lava):
                    successor = (
                        (
                            source.replace_entity(
                                wizard_loc.row, wizard_loc.col, EmptyEntity()
                            ).replace_active_entity_location(target)
                            .replace_score(0)
                            .lose()
                        )
                        .advance_turn()
                    )
                    transitions.append(
                        (
                            action,
                            successor,
                        )
                    )
                elif isinstance(target_tile, Portal):
                    successor = (
                        (
                            source.replace_entity(
                                wizard_loc.row, wizard_loc.col, EmptyEntity()
                            )
                            .replace_active_entity_location(target)
                            .win()
                        )
                        .advance_turn()
                    )
                    transitions.append(
                        (
                            action,
                            successor,
                        )
                    )
        return tuple(transitions)


    def transition(game_state:GameState, action: GameAction) -> GameState:
        successors = GameTransitions.get_successors(game_state)
        actions = [a for a, _ in successors]
        successor_states = [state for _, state in successors]

        if action not in actions:
            action = WizardMoves.STAY

        # Do a random action half of the time
        random_action = random.randint(0,1)
        if random_action:
            random_successor = random.randint(0,len(successor_states)-1)
            return successor_states[random_successor]
        else:
            return [successor_state for a,successor_state in successors if a == action][0]


class LocationCounts:
    def __init__(self,grid_size:tuple[int,int]):
        self.counts_grid = [[0.0 for _ in range(grid_size[1])] for _ in range(grid_size[0])]

    def add_count(self,loc:Location):
        self.counts_grid[loc.row][loc.col] += 1

    def count(self,loc:Location):
        return self.counts_grid[loc.row][loc.col]

    def normalize(self) -> LocationDistribution:
        """
        Given a grid of counts at locations, normalize to a probability distribution over the same locations
        """

        #given distribution shaped data, normalize to a valid probability distribution
        total = 0
        for row in self.counts_grid:
            for count in row:
                total += count

        prob_grid = [[0.0 for _ in range(len(self.counts_grid[0]))] for _ in range(len(self.counts_grid))]

        for i, row in enumerate(self.counts_grid):
            for j, count in enumerate(row):
                prob_grid[i][j] = self.counts_grid[i][j] / total


        return LocationDistribution(prob_grid)

class LocationDistribution:
    def __init__(self,prob_grid: list[list[float]]):
        self.prob_grid = prob_grid

    def from_location(loc:Location, grid_size:tuple[int,int])->LocationDistribution:
        prob_grid = [[0.0 for _ in range(grid_size[1])] for _ in range(grid_size[0])]
        prob_grid[loc.row][loc.col] = 1.0
        return LocationDistribution(prob_grid)

    def from_game_state(game_state:GameState)->LocationDistribution:
        grid_size = game_state.grid_size
        loc = game_state.active_entity_location
        prob_grid = [[0.0 for _ in range(grid_size[1])] for _ in range(grid_size[0])]
        prob_grid[loc.row][loc.col] = 1.0
        return LocationDistribution(prob_grid)

    def from_game_state_uniform(game_state:GameState)->LocationDistribution:
        """
        Initialize a uniformly random distribution over all empty tiles
        """
        empty_grid = LocationCounts(game_state.grid_size)
        for i in range(game_state.grid_size[0]):
            for j in range(game_state.grid_size[1]):
                if isinstance(game_state.tile_grid[i][j], EmptyTile):
                    empty_grid.add_count(Location(i,j))
        return empty_grid.normalize()


    def probability(self, loc:Location) -> float:
        return self.prob_grid[loc.row][loc.col]

    def renormalize(self):
        cumulative_prob = 0.0
        for loc in self.locations():
            cumulative_prob += self.probability(loc)

        for loc in self.locations():
            self.prob_grid[loc.row][loc.col] /= cumulative_prob

    def update_probability(self, loc:Location, p: float):
        self.prob_grid[loc.row][loc.col] = p

    def locations(self) -> Generator[Location]:
        for i, row in enumerate(self.prob_grid):
            for j,_ in enumerate(row):
                if self.prob_grid[i][j]>0:
                    yield Location(i,j)

    def sample(self) -> Location:
        """
        Sample a random location based off of the distribution.
        """

        sample_prob = random.random()
        cumulative_prob = 0.0
        for loc in self.locations():
            cumulative_prob += self.probability(loc)
            if sample_prob < cumulative_prob:
                return loc

        raise ValueError(f'Error in sampling. This should never happen! Distribution {self} ')

    def __repr__(self):
        r = ""
        for row in self.prob_grid:
            for v in row:
                r += f"|{v:0.02f}|"
            r+="\n"
        return r
