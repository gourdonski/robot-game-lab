# Todo: look into retreat-attack strategy some champions were using effectively in the arena.

import rg
import random

class Robot:
    # Default constructor to initialize everything.
    def __init__(self):
        self._act_attack = 'attack'
        self._act_guard = 'guard'
        self._act_move = 'move'
        self._act_suicide = 'suicide'
        self._suicide_hp = 10
        # Can change this.
        self._opp_suicide_hp = 40
        self._opp_suicide_enemy_count = 3
        self._robot_contexts = []
        # Not really using this right now.  Just for ref.
        self._roles = {1: 'grunt', 2: 'ranger'}
        # We can add more probabilities if we end up with more roles. (And find a tidier way to assign them.)
        self._ranger_probability = 0.4
        # Need a better name than this.
        self._ranger_neighborhood_offset = 3
        # Grunts organize themselves into units at specific locations.
        self._grunt_locations = []

        # Let's figure out some random points for our units to gather at.
        # For simplicity sake, we use an inner grid with the same number of rows and columns.
        # Might even be able to use this for point density analysis at some point to mitigate edge effects.
        sub_grid_start = 4
        sub_grid_end = 14
        grunt_location_count = 5

        # What if there is an enemy or group of enemies at the unit location?
        # I guess we can just keep trying to converge on it.
        while grunt_location_count > 0:
            grunt_location = (random.randrange(sub_grid_start, sub_grid_end), 
                random.randrange(sub_grid_start, sub_grid_end))

            if grunt_location not in self._grunt_locations:
                self._grunt_locations.append(grunt_location)

                grunt_location_count -= 1

    def act(self, game):
        # Make sure all the robots know what their role is.  Can probably optimize this to
        # only fire when we've reached a turn that spawns new robots.
        self.__initialize_robots(game)

        adjacent_enemies = self.__get_adjacent_enemies(game, self.location)

        # Enemies, sire!
        if len(adjacent_enemies) > 0:
            # 1. Commit desperate suicide - if we're on our last leg.
            # Todo - check how many turns are left and if suicide will actually 
            # take out any enemy robots.  We don't want to sacrifice one of our
            # dudes near the end of the game if it won't reduce the number of enemies
            # by at least one.
            # Also, right now, we are killing ourselves every time we get in a fight to the death.
            # Is that wise?  What if we are the survivor?  Even with a small amount of HP, isn't it worth staying alive?
            if self.hp <= self._suicide_hp:
                return self.__act(game, self._act_suicide, self.location)

            # 2. Commit opportunistic suicide - if we're surrounded by a bunch of baddies.
            # Not sure how frequently this will occur because if it's 4 bots grinding on you,
            # they can knock off up to 40 HP in a turn and if we're waiting for a certain amount
            # of health, we could be dead before we get a chance to pull the pin.
            if len(adjacent_enemies) >= self._opp_suicide_enemy_count and \
                self.hp <= self._opp_suicide_hp:
                return self.__act(game, self._act_suicide, self.location)
            
            # 3. Retreat!!
            # If we're getting teamed up on, get out of there.
            if len(adjacent_enemies) > 1:
                friendly_adjacent_locations = \
                    self.__get_friendly_adjacent_locations(game, self.location)

                if len(friendly_adjacent_locations) > 0:
                    # Move to first friendly location in array.
                    return self.__act(game, self._act_move, friendly_adjacent_locations[0])
                else:
                    # Get in the fetal position.  Or should we attack and go out gloriously?
                    return self.__act(game, self._act_guard, self.location)

            # 4. Attack!!
            # Sort array on robot HP to attack weakest enemies first.
            # We want to dispatch baddies on their last leg.
            sorted_enemies = sorted(adjacent_enemies.iteritems(), key=lambda x: x[1].hp)

            return self.__act(game, self._act_attack, sorted_enemies[0][0])

        # 5. Move it!
        grunt_contexts = filter(lambda context: context.id == self.robot_id and 
            context.role_id == 1, self._robot_contexts)

        if len(grunt_contexts) > 0:
            next_location = rg.toward(self.location, grunt_contexts[0].target_location)

            return self.__act(game, self._act_move, next_location)
        # Could explicitly check for rangers here, but what if some robots are unaccounted for?
        # Shouldn't happen, but just in case...
        else:
            # Find the weakest enemy in our neighbhoorhood and pursue them.
            target_neighborhood = self.__get_neighborhood(
                self.location, self._ranger_neighborhood_offset)

            weakest_enemy = self.__get_weakest_enemy(game, target_neighborhood)

            # If there aren't any enemies in our neighborhood, check the whole arena.
            if weakest_enemy is None:
                weakest_enemy = self.__get_weakest_enemy(game)

            # Should usually expect there to be some enemies on the board, but just in case.
            if weakest_enemy is not None:
                next_location = rg.toward(self.location, weakest_enemy[0])

                if len(self.__get_adjacent_enemies(game, next_location)) <= 1:
                    return self.__act(game, self._act_move, next_location)

            # If our next move is into a death slot or no enemies, let's just chill for a sec and guard.
            # Don't actually need this here right now since we'll hit the default behavior which is the same.
            return self.__act(game, self._act_guard, self.location)

        # Default behavior.  For now.
        return self.__act(game, self._act_guard, self.location)

    def __initialize_robots(self, game):
        for robot in game['robots'].itervalues():
            # If it's one of ours...
            if robot.player_id == self.player_id:
                robot_contexts = filter(lambda context: context.id == 
                    self.robot_id, self._robot_contexts)

                # Can clean this up to avoid repeated code.
                if len(robot_contexts) == 0:
                    if random.random() <= self._ranger_probability:
                        robot_context = RobotContext(self.robot_id, role_id=2)

                        self._robot_contexts.append(robot_context)
                    else:
                        # Find closest unit and assign robot to it.
                        grunt_location_distances = {}

                        for grunt_location in self._grunt_locations:
                            grunt_location_distances[grunt_location] = \
                                rg.dist(grunt_location, self.location)

                        target_location = min(grunt_location_distances, 
                            key=lambda key: grunt_location_distances[key])

                        robot_context = RobotContext(
                            self.robot_id, role_id=1, target_location=target_location)

                        self._robot_contexts.append(robot_context)
                elif robot_contexts[0].role_id is None:
                    robot_context = robot_contexts[0]

                    if random.random() <= self._ranger_probability:
                        robot_context.role_id = 2
                    else:
                        robot_context.role_id = 1

                        # Find closest unit and assign robot to it.
                        grunt_location_distances = {}

                        for grunt_location in self._grunt_locations:
                            grunt_location_distances[grunt_location] = \
                                rg.dist(grunt_location, self.location)

                        robot_context.target_location = min(grunt_location_distances, 
                            key=lambda key: grunt_location_distances[key])

        # Todo: clean up deceased robots from roles.

    def __act(self, game, action, location):
        if (action == self._act_move):
            return self.__cautious_move(game, location)
        else:
            robot_contexts = filter(
                lambda context: context.id == self.robot_id, self._robot_contexts)

            if len(robot_contexts) == 0:
                robot_context = RobotContext(self.robot_id)
                robot_context.add_action_history(action, location)

                self._robot_contexts.append(robot_context)
            else:
                robot_contexts[0].add_action_history(action, location)

            return [action, location]

    # Is guarding as a default when our attempt at moving has failed a good idea?
    # What other types of behavior are there?
    def __cautious_move(self, game, move_location):
        # Todo: expand on this.
        # First, let's not allow our bots to move back onto a spawn location once they've moved inwards.
        if 'spawn' not in rg.loc_types(self.location) and \
            'spawn' in rg.loc_types(move_location):
            return [self._act_guard, self.location]

        robot_contexts = filter(
            lambda context: context.id == self.robot_id, self._robot_contexts)
        robot_context = None

        if len(robot_contexts) == 0:
            robot_context = RobotContext(self.robot_id)

            self._robot_contexts.append(robot_context)
        else:
            robot_context = robot_contexts[0]

        # Then, check if there is already someone at the location we want to move into.
        for location, robot in game.robots.iteritems():
            if location == move_location:
                robot_context.add_action_history(self._act_guard, self.location)

                return [self._act_guard, self.location]

        # Next, check if the move location is surrounded by at least two enemies.
        if len(self.__get_adjacent_enemies(game, move_location)) > 1:
            robot_context.add_action_history(self._act_guard, self.location)

            return [self._act_guard, self.location]

        # Next, if we tried to move into the same location last time and it didn't
        # work out, could be that we collided.  Let's just relax for a turn and
        # see if that fixes things...  This is to avoid dead-locks.
        last_action = robot_context.get_last_action()

        if last_action is not None:
            if last_action[0] == self._act_move and last_action[1] == move_location:
                robot_context.add_action_history(self._act_guard, self.location)

                return [self._act_guard, self.location]

        # Well, looks like we're moving to the requested location.
        robot_context.add_action_history(self._act_move, move_location)

        return [self._act_move, move_location]

    def __get_adjacent_enemies(self, game, location):
        adjacent_enemies = {}

        for robot_location, robot in game.robots.iteritems():
            if robot.player_id != self.player_id:
                # Should we use rg.settings.attack_range instead of hardcoding a value of 1 here?
                if rg.dist(robot_location, location) <= 1:
                    adjacent_enemies[robot_location] = robot

        return adjacent_enemies

    def __get_friendly_adjacent_locations(self, game, location, max_adjacent_enemy_count = 1):
        friendly_adjacent_locations = []
        valid_adjacent_locations = rg.locs_around(
            location, filter_out=('invalid', 'obstacle', 'spawn'))

        for adjacent_location in valid_adjacent_locations:
            if adjacent_location not in game.robots.iterkeys():
                # Not in love with this implementation.  What about just getting less dangerous locations?
                if len(self.__get_adjacent_enemies(game, adjacent_location)) <= \
                    max_adjacent_enemy_count:
                    friendly_adjacent_locations.append(adjacent_location)

        return friendly_adjacent_locations

    def __get_weakest_enemy(self, game, neighborhood = None):
        if neighborhood is not None:
            neighborhood_enemies = {}
            min_location = neighborhood[0]
            max_location = neighborhood[1]

            for location, robot in game.robots.iteritems():
                if robot.player_id != self.player_id:
                    if location[0] >= min_location[0] and location[0] <= max_location[0] \
                        and location[1] >= min_location[1] and location[1] <= max_location[1]:
                        neighborhood_enemies[location] = robot
            
            if len(neighborhood_enemies) > 0:
                sorted_enemies = sorted(neighborhood_enemies.iteritems(), key=lambda x: x[1].hp)

                return sorted_enemies[0]
        else:
            enemies = {}

            for location, robot in game.robots.iteritems():
                if robot.player_id != self.player_id:
                    enemies[location] = robot

            if len(enemies) > 0:
                sorted_enemies = sorted(enemies.iteritems(), key=lambda x: x[1].hp)

                return sorted_enemies[0]

    # Todo: Get a better name than neighborhood_offset.  Or just make this better in general.
    def __get_neighborhood(self, location, neighborhood_offset):
        location_x = location[0]
        location_y = location[1]
        x_min = location_x - neighborhood_offset
        x_max = location_x + neighborhood_offset
        y_min = location_y - neighborhood_offset
        y_max = location_y + neighborhood_offset

        return ((x_min, y_min), (x_max, y_max))

# Keep track of context info for our robots.  Such as the history of their actions.
# How about adding HP history to this? 
class RobotContext(object):
    def __init__(self, robot_id, role_id = None, target_location = None):
        self.id = robot_id
        self.role_id = role_id
        self.target_location = target_location
        self._action_history = []

    def add_action_history(self, action, location):
        self._action_history.append((action, location))

    def get_last_action(self):
        if len(self._action_history) > 0:
            return self._action_history[-1]

    def get_action_at(self, index):
        int_index = int(index)

        if len(self._action_history) > int_index:
            return self._action_history[int_index]
