import stat
import dataclasses
from agents import EntityAgent, UncertainAgent
from model import Location,GameState, GameAction, WizardMoves, Location, Crystal, Portal, Lava, GameTransitions, Observation, EmptyTile, LocationCounts, LocationDistribution
import random


class MDP:
    def __init__(self,initial_state: GameState, escape_reward:float,living_reward: float,death_reward:float, discount: float):
        self.game_state = initial_state
        self.living_reward = living_reward
        self.death_reward = death_reward
        self.escape_reward = escape_reward
        self.discount = discount

    def reward(self,source:GameState,target:GameState, action: GameAction) -> float:
        loc = target.active_entity_location
        if isinstance(target.tile_grid[loc.row][loc.col],Lava):
            return self.death_reward
        elif target.victory:
            return self.escape_reward
        else:
            return self.living_reward


    def transition_model(self,location: Location, action: GameAction) -> LocationDistribution:
        """
        Transition model of the MDP, gives conditional probability distribution of result location given starting location and action choice.
        """
        source_state = self.game_state.replace_active_entity_location(location)
        successors = GameTransitions.get_successors(source_state)
        actions = [a for a, _ in successors]
        successor_states = [state for _, state in successors]

        if action not in actions:
            return self.transition_model(location,WizardMoves.STAY)

        # Outcomes are either the desired outcome of the action, or a random other action each with 50% prob.
        possible_results = LocationCounts(self.game_state.grid_size)
        for i in range(len(actions)):
            if actions[i] == action:
                for _ in range(len(actions)+1):
                    possible_results.add_count(successor_states[i].active_entity_location)
            else:
                possible_results.add_count(successor_states[i].active_entity_location)

        return possible_results.normalize()

    def transition_distribution(self, source: LocationDistribution, action: GameAction) -> LocationDistribution:
        """
        Given a location distribution, calculate the new distribution that is a result of taking the given action.
        The easiest way to do this will involve sampling.
        """

        # Sample Size Constant
        SAMPLE_SIZE = 1000

        # Count result locations
        counts = LocationCounts(self.game_state.grid_size)

        # Iterate through all samples
        for _ in range(SAMPLE_SIZE):

            # Use Sample function to sample 
            sample = source.sample()

            # Apply transition model to the sample
            result = self.transition_model(sample, action).sample()

            counts.add_count(result)

        # Normalize counts to get probabilities
        return counts.normalize()


class LocationValues:
    def __init__(self, mdp: MDP):
        self.mdp = mdp
        self.value_grid = [[0.0 for _ in range(mdp.game_state.grid_size[1])] for _ in range(mdp.game_state.grid_size[1])]

    def value_iteration(self,k):
        for _ in range(k):
            self.value_iteration_update()

    def value_iteration_update(self):
        """
        Perform one update of value iteration based off of the provided MDP.
        """

        rows, cols = self.mdp.game_state.grid_size
        next_value_grid = [[0.0 for _ in range(cols)] for _ in range(rows)]

        for row in range(rows):
            for col in range(cols):

                curr_location = Location(row, col)


                # Set entity's state to current location 
                state_at_location = self.mdp.game_state.replace_active_entity_location(curr_location)


                # If the current location is lava or portal, skip
                if isinstance(self.mdp.game_state.tile_grid[row][col], (Lava, Portal)):
                    continue


                # Get potential successors and actions at each ---------------------

                successors = GameTransitions.get_successors(state_at_location)

                actions = [a for a, _ in successors]

                # ------------------------------------------------------------------


                q_vals = []

                # Iterate through all possible actions & compute Q-val using Bellman equation
                for action in actions:

                    distance = self.mdp.transition_model(curr_location, action)

                    gamma = self.mdp.discount
                    q_val = 0.0

                    # Iterate through all possible S'
                    for s_prime in distance.locations():

                        value_s_prime = self.value_grid[s_prime.row][s_prime.col]
                        reward = self.mdp.reward(
                            state_at_location,
                            self.mdp.game_state.replace_active_entity_location(s_prime), 
                            action
                        )

                        q_val += distance.probability(s_prime) * (reward + gamma * value_s_prime)

                    q_vals.append(q_val)

                # Only take max if q_vals isn't empty (walkable tile)
                if q_vals:
                    next_value_grid[row][col] = max(q_vals)

        
        self.value_grid = next_value_grid

        return next_value_grid


class MDPAgent(UncertainAgent):
    values: LocationValues
    current_position_estimate: LocationDistribution
    current_score_estimate: int
    mdp: MDP

    def __init__(self, mdp: MDP, value_iteration_steps=100):
        self.mdp = mdp
        self.values = LocationValues(mdp)
        self.values.value_iteration(value_iteration_steps)
        self.current_position_estimate = LocationDistribution.from_game_state_uniform(mdp.game_state)


    def observation_likelihood(self, observation: Observation, loc: Location)-> float:
        portal_loc = self.mdp.game_state.get_all_tile_locations(Portal)[0]
        portal_dist = abs(loc.row-portal_loc.row) + abs(loc.col - portal_loc.col)

        if abs(portal_dist - observation.approximatePortalDist) > 1:
            return 0
        else:
            return 1.0/3.0

    def update_prior(self,action: GameAction):
        self.current_position_estimate = self.mdp.transition_distribution(self.current_position_estimate,action)


    def update_belief(self, observation: Observation):
        """
        Use Bayes rule to update your beliefs about the wizard location by updating self.current_position_estimate.
        You have prior belief of your current estimate P(Loc), and the observation likelihood model (P(Obs | Loc)).
        Use these to calculate the new belief.
        """

        #We need to update our belief for all possible locations. So lets start by creating a new distribution
        new_estimate = LocationDistribution.from_game_state_uniform(self.mdp.game_state)

        #The new distribution should be set for each location
        for loc in new_estimate.locations():

            # Update posterior based on new data
            posterior = self.observation_likelihood(observation, loc) * self.current_position_estimate.probability(loc)

            # Update estimate based on posterior
            new_estimate.update_probability(
                loc, 
                posterior
            )


        new_estimate.renormalize()
        self.current_position_estimate = new_estimate

    def react(self, observation: Observation) -> GameAction:
        """
        Our uncertain agent only has noisy observations to guess where in the dungeon it is. Use the previously implemented parts to generate an estimate for the distribution of possible locations the wizard might be at, updating every turn with a new observation, and choose the action based off of your value iteration policy based on your estimate.
        """

        # Use Bayes Rule to update your beliefs about where you think the wizard is based off of the observation
        self.update_belief(observation)


        # Part 2: Choose the best action
        # use your calculated value iteration map of location values alongside your estimated location to choose the best action given your uncertain state.
        # There are multiple ways to do this, but some things to consider:
            # 1. You want to select the action which will have the highest expected value, given the probability distribution of the resultant states.
            # 2. The expected value of some quantity is just the weighted average value of that quantity in an outcome weighted by the probability of that outcome over all outcomes (and can be estimated by the average of a sufficiently big sample of outcomes sampled from the distribution)
            # 3. You can sample locations from any distribution, and can form distributions of locations from samples
            # 4. You can find the distribution of the results of an action for a given specific location
            # 5. You can calculate the reward of a specific transition as a result of a specific action with a specific result
            # 6. You have an estimate of the value of each result location
        
        # Initialize best action and best expected val
        best_action = None
        best_value = float('-inf')

        # Go through all possible WizardMoves
        for action in WizardMoves:


            distance = self.mdp.transition_distribution(self.current_position_estimate, action)

            expected_value = 0.0

            # Calculate expected values for each possible location
            for loc in distance.locations():

                expected_value += distance.probability(loc) * self.values.value_grid[loc.row][loc.col]

            
            # Update best expected value if newly found is better
            if expected_value > best_value:
                best_value = expected_value
                best_action = action

        action = best_action

            
        # When choosing an action, we must update our prior to account for the new distribution as a result of the action being taken
        self.update_prior(action)
        return action
