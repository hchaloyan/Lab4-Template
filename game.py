from lab4 import MDPAgent
import sys
import time
from enum import Enum
import pyglet
from model import (
    Entity,
    EmptyEntity,
    Wizard,
    GameState,
    WizardMoves,
    GameAction,
    Location,
    MapTile,
    Wall,
    EmptyTile,
    GameTransitions, Lava, Portal, Crystal, LocationDistribution,
)
from agents import (
    EntityAgent,
    UncertainAgent,
)


class GameStatus(Enum):
    PLAYING = 1
    SUCCESS = 2
    FAILURE = 3


class MDPGame:
    status: GameStatus = GameStatus.PLAYING
    tile_size = 64
    game_tick_interval = 0.2
    debug = False

    entity_agent_map: dict[int, EntityAgent] = {}
    no_render = False

    def __init__(
        self,
        path: str,
        game_tick_interval: float,
        no_render: bool,
        debug: bool,
        timeout: int,
    ):
        self.start_time = time.time()
        self.game_tick_interval = game_tick_interval
        self.no_render = no_render
        self.debug = debug
        self.timeout = timeout
        self.status = GameStatus.PLAYING

        with open(path) as f:
            file_rows = f.readlines()
        file_rows = [line.rstrip("\n") for line in file_rows]

        grid_size = (len(file_rows), max(len(row) for row in file_rows))
        tile_grid: list[list[MapTile]] = [
            [EmptyTile() for _ in range(grid_size[1])] for _ in range(grid_size[0])
        ]
        entity_grid: list[list[Entity]] = [
            [EmptyEntity() for _ in range(grid_size[1])] for _ in range(grid_size[0])
        ]

        id_counter = 1
        wizard_loc = None
        for r in range(grid_size[0]):
            for c in range(grid_size[1]):
                code = file_rows[r][c].strip()
                match code:
                    case "W":  # w for wizard
                        entity_grid[r][c] = Wizard(id=id_counter)
                        tile_grid[r][c] = EmptyTile()
                        id_counter += 1
                        wizard_loc = Location(r, c)

                    case "L":  # L for Lava
                        entity_grid[r][c] = EmptyEntity()
                        tile_grid[r][c] = Lava()

                    case "P":  # P for Portal
                        entity_grid[r][c] = EmptyEntity()
                        tile_grid[r][c] = Portal()

                    case "C":  # C for Crystal
                        entity_grid[r][c] = EmptyEntity()
                        tile_grid[r][c] = Crystal()

                    case "#":  # Wall
                        entity_grid[r][c] = EmptyEntity()
                        tile_grid[r][c] = Wall()

                    case " ":  # Empty
                        entity_grid[r][c] = EmptyEntity()
                        tile_grid[r][c] = EmptyTile()

        if id_counter == 1:
            raise ValueError("Map has no entities!")
        if not wizard_loc:
            raise ValueError("Map has no wizard!")
        self.state = GameState(
            grid_size=grid_size,
            tile_grid=tuple((tuple(row) for row in tile_grid)),
            entity_grid=tuple((tuple(row) for row in entity_grid)),
            active_entity_location=wizard_loc,
        )
        self.path_locs = [wizard_loc]

        if not self.no_render:
            self.wall_img = pyglet.image.load("assets/wall.png")
            self.wizard_img = pyglet.image.load("assets/robo_wizard.png")
            self.lava_img = pyglet.image.load("assets/lava.png")
            self.portal_img = pyglet.image.load("assets/portal.png")
            self.crystal_img = pyglet.image.load("assets/crystal.png")

            self.ground_img = pyglet.image.load("assets/ground.png")

            self.batch = pyglet.graphics.Batch()

            self.background = pyglet.graphics.Group(order=0)
            self.foreground = pyglet.graphics.Group(order=1)
            self.effects = pyglet.graphics.Group(order=2)

            self.bg_sprites: dict[Location, pyglet.sprite.Sprite] = {}
            self.grid_sprites: dict[Location, pyglet.sprite.Sprite] = {}
            self.entity_sprites: dict[Location, pyglet.sprite.Sprite] = {}
            self.search_sprites: dict[Location, pyglet.sprite.Sprite] = {}

            self.window = pyglet.window.Window(
                width=(self.state.grid_size[1] * self.tile_size),
                height=(self.state.grid_size[0] * self.tile_size),
                caption="Lab 3: Fog of War",
                resizable=True,
            )
            self.window.set_icon(self.wizard_img.get_image_data())

            self.window.event

            @self.window.event
            def on_draw() -> None:
                self.window.clear()
                self.batch.draw()

            @self.window.event
            def on_resize(width: int, height: int) -> None:
                grid_rows, grid_cols = self.state.grid_size
                fit_tile_height = height // grid_rows
                fit_tile_width = width // grid_cols
                new_tile_size = min(fit_tile_height, fit_tile_width)
                self.tile_size = new_tile_size

                self.render()

    def register_entity_agent(self, agent: EntityAgent, id: int) -> None:
        self.entity_agent_map[id] = agent

    def run(self):
        if self.no_render:
            while True:
                self.update(0)
        else:
            pyglet.clock.schedule_interval(self.update, self.game_tick_interval)

    def update(self, dt: float):
        tick_time = time.time()
        if tick_time - self.start_time > self.timeout:
            self.status = GameStatus.FAILURE
            print(f"Timeout after {int(tick_time - self.start_time)} seconds!")
        match self.status:
            case GameStatus.PLAYING:
                self.game_tick()
            case GameStatus.SUCCESS:
                print(
                    f"Victory! at turn:\t{self.state.turn}\n\tScore:\t{self.state.score}\n\tTime Taken (s):\t{tick_time - self.start_time: .02f}"
                )
                if self.no_render:
                    sys.exit()
                else:
                    self.window.close()
                    pyglet.app.exit()

            case GameStatus.FAILURE:
                print(
                    f"Defeat! at turn {self.state.turn}\n\tTime Taken (s):\t{tick_time - self.start_time: 0.02f}"
                )
                if self.no_render:
                    sys.exit()
                else:
                    self.window.close()
                    pyglet.app.exit()


    def game_tick(self) -> None:

        active_entity = self.state.get_active_entity()

        if active_entity.id in self.entity_agent_map:
            active_agent = self.entity_agent_map[active_entity.id]

            if isinstance(active_agent, MDPAgent):
                action = active_agent.react(self.state.observe())
                self.state = GameTransitions.transition(self.state,action)

        if self.state.victory:
            self.status = GameStatus.SUCCESS
        elif self.state.defeat:
            self.status = GameStatus.FAILURE



        # render game every tick
        self.entity_sprites = {}  # maybe this could be made more efficient, for now assume all entities need to be rerendered each tick
        self.grid_sprites = {}
        self.render()

    def render(self) -> None:
        if self.no_render:
            return

        match self.status:
            case GameStatus.PLAYING:
                self.window.set_caption("Lab 3: Fog of War: PLAYING")
            case GameStatus.SUCCESS:
                self.window.set_caption("Lab 3: Fog of War: VICTORY")
            case GameStatus.FAILURE:
                self.window.set_caption("Lab 3: Fog of War: DEFEAT")

        if not self.bg_sprites:
            for r, row in enumerate(self.state.tile_grid):
                for c, tile in enumerate(row):
                    x, y = self.grid_to_pix(r, c)

                    sprite = pyglet.sprite.Sprite(
                        img=self.ground_img,
                        x=x,
                        y=y,
                        batch=self.batch,
                        group=self.background,
                    )
                    sprite.height = self.tile_size
                    sprite.width = self.tile_size
                    self.bg_sprites[Location(r, c)] = sprite

        if not self.grid_sprites:
            for r, row in enumerate(self.state.tile_grid):
                for c, tile in enumerate(row):
                    x, y = self.grid_to_pix(r, c)

                    if isinstance(tile, Wall):
                        sprite = pyglet.sprite.Sprite(
                            img=self.wall_img,
                            x=x,
                            y=y,
                            batch=self.batch,
                            group=self.foreground,
                        )
                        sprite.height = self.tile_size
                        sprite.width = self.tile_size
                        self.grid_sprites[Location(r, c)] = sprite
                    elif isinstance(tile, Lava):
                        sprite = pyglet.sprite.Sprite(
                            img=self.lava_img,
                            x=x,
                            y=y,
                            batch=self.batch,
                            group=self.foreground,
                        )
                        sprite.height = self.tile_size
                        sprite.width = self.tile_size
                        self.grid_sprites[Location(r, c)] = sprite
                    elif isinstance(tile, Portal):
                        sprite = pyglet.sprite.Sprite(
                            img=self.portal_img,
                            x=x,
                            y=y,
                            batch=self.batch,
                            group=self.foreground,
                        )
                        sprite.height = self.tile_size
                        sprite.width = self.tile_size
                        self.grid_sprites[Location(r, c)] = sprite
                    elif isinstance(tile, Crystal):
                        sprite = pyglet.sprite.Sprite(
                            img=self.crystal_img,
                            x=x,
                            y=y,
                            batch=self.batch,
                            group=self.foreground,
                        )
                        sprite.height = self.tile_size
                        sprite.width = self.tile_size
                        self.grid_sprites[Location(r, c)] = sprite





        if not self.entity_sprites:
            for r, row in enumerate(self.state.entity_grid):
                for c, entity in enumerate(row):
                    if isinstance(entity, Wizard):
                        x, y = self.grid_to_pix(r, c)
                        sprite = pyglet.sprite.Sprite(
                            img=self.wizard_img,
                            x=x,
                            y=y,
                            batch=self.batch,
                            group=self.foreground,
                        )
                        sprite.height = self.tile_size
                        sprite.width = self.tile_size
                        self.entity_sprites[Location(r, c)] = sprite


    def grid_to_pix(self, row: int, col: int) -> tuple[int, int]:
        return col * self.tile_size, (
            self.state.grid_size[0] - 1 - row
        ) * self.tile_size
