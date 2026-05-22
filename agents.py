import random
from model import (
    GameState,
    GameAction,
    WizardMoves,
    GameTransitions,
    Wizard,
    EmptyEntity, Observation,
)
import sys


class EntityAgent:
    id: int

class UncertainAgent(EntityAgent):
    def __init__(self, initial_state: GameState):
        pass

    def react(self, observation: Observation) -> GameAction:
        # given observation, update any internal state and return next move
        return WizardMoves.STAY
