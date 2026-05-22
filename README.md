# Lab 3: Fog of War

Your wizard has descended into the deepest chamber of the dungeon dimension, and something has gone terribly wrong. A dark enchantment hangs in the air, a *Fog of War* that has robbed your wizard robot of its sight. It can no longer see the walls, the lava, or the glittering portal home. Worse still, the dungeon's magical currents are unpredictable, even when your wizard tries to move in a chosen direction, the currents may carry it somewhere else entirely.

All that remains is a faint magical sense, a feeling in the air. Your wizard is able to divine a rough feeling of how far away the portal is. However, this sense is imperfect, it can sometimes be off by a step in either direction.

Your task is to give your wizard the tools to navigate blind. First, it must learn the dungeon by reasoning about which positions are valuable before it ever sets foot inside. Then, as it wanders the fog, it must track its own location using Bayesian beliefs and use those beliefs to act wisely under uncertainty.

## Setting up your environment
To get started make sure to install pyglet using the given `pyproject.toml` in order to run renders of the game.

## Files You Will Edit

> `lab3.py`: All of your implementation goes here.

## Files You Might Want to Read
While these files are pretty similar to your previous assignments, there are some minor differences and it may be worth refreshing your understandings.

> `model.py`:  This contains the dungeon data models(ie `GameState`, `Location`, `LocationDistribution`, `LocationCounts`, `Observation`, tile types, and transitions). Understanding the new classes of `LocationDistribution`, `LocationCounts`, `Observation` will be very important. Be mindful about the difference between _distributions_ and individual _samples_ and how or why you might try and work between them. In particular for some parts of the lab instead of acting directly on distributions you may want to sample from a distribution, do some things to those samples, and count them back and normalize to a distribution.

> `agents.py`: This is the abstract agent classes your `MDPAgent` inherits from.

> `run.py`: This is the entry point for running your wizard locally.

## Running Your Wizard

```bash
python run.py --map open
python run.py --map cliff
python run.py --map open --no_render
python run.py --map cliff --living_reward -1 --discount 0.95 --value_iteration_steps 200
```

Important CLI options(there others in model.py but these are the important new ones):
- `--map`: which map to load (`open` or `cliff`)
- `--value_iteration_steps`: how many rounds of value iteration to run before the game starts
- `--escape_reward`:reward (or penalty) the wizard receives when it can escape from the portal
- `--living_reward`:reward (or penalty) the wizard receives each turn it survives
- `--death_reward`: reward (or penalty) given when the wizard steps into lava
- `--discount`: future discount factor γ
---

# Part 1: Learning the Dungeon (Value Iteration)

Before your wizard steps into the fog, it must study ancient maps of the dungeon and reason about the value of each position(You should think about the value of long term rewards that can be derived from each tile, given optimal play). You might from lecture (See the MDP/Bellman Lecture Notes) that this process is called _value iteration_(the process of repeatedly refining estimates of state value until they converge).

The dungeon's magical currents make every action uncertain. When the wizard attempts a move, there is a 50% chance it is carried somewhere random instead. The `MDP` class encodes this as a _transition model_. Once again you'll recall that for any location and action, `transition_model` returns a probability distribution over resulting locations.

## `value_iteration_update`

Implement one round of value iteration in `LocationValues.value_iteration_update`. This method should compute an entirely new value grid from the current one. For each non terminal location, compute the _Bellman update_:

$$V_{k+1}(s) = \max_a \sum_{s'} T(s, a, s') \left[ R(s, a, s') + \gamma V_k(s') \right]$$

where:
- $T(s, a, s')$ is the transition probability from state $s$ to $s'$ under action $a$, given by `transition_model`
- $R(s, a, s')$ is the reward for that transition, given by `mdp.reward`
- $\gamma$ is the discount factor `mdp.discount`
- $V_k(s')$ is the value of the successor location in the current value grid

Some things to consider:
- Terminal states (lava, portal) have their reward baked in and do not need further look a head.
- Use `GameTransitions.get_successors` to find valid actions from any location. You can construct a `GameState` with a wizard at a given location using `game_state.replace_active_entity_location(loc)`.
- The `transition_model` method handles the magical(stochastic) currents for you. You can call it with a location and action to get the resulting `LocationDistribution`.


After implementing this, run value iteration and observe what values the wizard assigns to different tiles. Lava adjacent squares should have lower value and positions near the portal should be higher.

---

# Part 2: Navigating the Fog

With value estimates in hand, the wizard enters the dungeon. But it cannot see where it is. All it receives each turn is an `Observation`, or a a noisy integer representing its approximate Manhattan distance to the portal. The noise can be -1, 0, or +1 from the true distance, each equally likely.

The wizard must maintain its belief about where it probably is, a probability distribution over all possible locations, and update it each turn using its observation and the motion it just took.

## `transition_distribution`

Implement `MDP.transition_distribution`. Given a distribution over current locations (`source: LocationDistribution`) and an action, compute the resulting distribution of locations after taking that action.

The dungeon's stochastic currents make it impossible to compute this analytically across a full distribution, so use sampling. You'll need to draw many sample locations from the source distribution, apply the transition model at each sampled location, draw a result location, and accumulate counts to form the new distribution.

For the most part the scaffolds for this are already there so now you need complete the implementation.

## `update_belief`

Implement `MDPAgent.update_belief`. Each turn, before acting, the wizard receives an observation and must update its belief using Bayes' rule:

$$P(\text{Loc} \mid \text{Obs}) \propto P(\text{Obs} \mid \text{Loc}) \cdot P(\text{Loc})$$

where:
- $P(\text{Loc})$ is the current belief `self.current_position_estimate`
- $P(\text{Obs} \mid \text{Loc})$ is the observation likelihood from `observation_likelihood`

The main structure is provided, so your job is to fill in what the new probability of each location should be, and make sure the result is a valid distribution.

## `react`

Implement `MDPAgent.react`. The belief update and prior update calls are already wired in. So you will need to choose the best action given that the wizard does not know exactly where it is.

Remember, you have a value map built for a known location, but you only have a _distribution_ over possible locations. How do you use the value of known outcomes to choose wisely under that uncertainty? 

---

# Part 3: Tuning Rationality

Finally, we want to understand how the different parameters of our MDP affect what choices the wizard makes. Look at the map `cliff` and see there are three kinds of route to the portal. The shortest path "risks the cliff" by being near lava for many steps in a row. Another route risks part of the cliff but diverts away for a slightly longer but safer path. And finally some paths take the path straight away from the cliff which is the safest and longest route. Experiment with different values of `escape_reward`, `living_reward`, `death_reward`, and `discount`. How many different configurations of variables can you find to take the three different paths? Are there any configurations that do something odd or different? Why? (I will be asking you about this in the lab review).



--- 
## Getting Help

You are not alone in the fog! *Office hours, lab, and the **EdStem** forum* exist for your support! We don't want you all to suffer as your wizards have, don't just feel around in the dark, reach out for help! Hopefully this assignment will be an interesting exploration of probability and planning, not a stumble in the dark.
