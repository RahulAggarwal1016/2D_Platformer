import arcade
# import random

# Note 0 for y is at the bottom
# Larger x is to the right of the screen
SCREEN_WIDTH = 1700
SCREEN_HEIGHT = 1000
SCREEN_TITLE = "Personal Game"

# Constant to scale sprite from original size
character_scaling = 0.5
tile_scaling = 0.5
coin_scaling = 0.5
sprite_pixel_size = 128
grid_pixel_size = (sprite_pixel_size*tile_scaling)

# coin_count = 10 (Number of Coins used for coin animation)

# Movement speed of player, in pixels per frame
player_movement_speed = 7
gravity = 3 # How fast character will accelerate downwards
player_jump_speed = 40 # How high the character will jump
updates_per_frame = 7

left_viewpoint_margin = 400
right_viewpoint_margin = 400
bottom_viewpoint_margin = 180
top_viewpoint_margin = 300

player_start_x = 64
player_start_y = 500

# Constants used to check if player is facing right or left
right_facing = 0
left_facing = 1

def load_texture_pair(filename):
    """
    Load a texture pair, with the second being a mirror image.
    """
    return [
        arcade.load_texture(filename, scale=character_scaling),
        arcade.load_texture(filename, scale=character_scaling, mirrored=True)
    ]

class PlayerCharacter(arcade.Sprite):
    "Main Player Class"

    def __init__(self):

        # Set up parent class
        super().__init__()

        # Default to face-right
        self.character_face_direction = right_facing

        # Used for flipping between image sequences
        self.cur_texture = 0

        # Track our state
        self.jumping = False
        self.climbing = False
        self.is_on_ladder = False

        # Adjust the collision box. Default includes too much empty space
        # side-to-side. Box is centered at sprite center, (0, 0)
        self.points = [[-22, -64], [22, -64], [22, 28], [-22, 28]]

        # --- Load Textures ---

        # Images from Kenney.nl's Asset Pack 3
        main_path = "maleAdventurer/character_maleAdventurer"

        # Load textures for idle standing
        self.idle_texture_pair = load_texture_pair(f"{main_path}_idle.png")
        self.jump_texture_pair = load_texture_pair(f"{main_path}_jump.png")
        self.fall_texture_pair = load_texture_pair(f"{main_path}_fall.png")

        # Load textures for walking
        self.walk_textures = []
        for i in range(8):
            texture = load_texture_pair(f"{main_path}_walk{i}.png")
            self.walk_textures.append(texture)

        # Load textures for climbing
        self.climbing_textures = []
        texture = arcade.load_texture(f"{main_path}_climb0.png", scale=character_scaling)
        self.climbing_textures.append(texture)
        texture = arcade.load_texture(f"{main_path}_climb1.png", scale=character_scaling)
        self.climbing_textures.append(texture)

    def update_animation(self, delta_time:float = 1/60):

        # Figure out if we need to flip face left or right
        if self.change_x < 0 and self.character_face_direction == right_facing:
            self.character_face_direction = left_facing
        elif self.change_x > 0 and self.character_face_direction == left_facing:
            self.character_face_direction = right_facing

        # Climbing animation
        if self.is_on_ladder:
            self.climbing = True
        if not self.is_on_ladder and self.climbing:
            self.climbing = False
        if self.climbing and abs(self.change_y) > 1:
            self.cur_texture += 1
            if self.cur_texture > 7:
                self.cur_texture = 0
        if self.climbing:
            self.texture = self.climbing_textures[self.cur_texture//4]
            return

        # Jumping animation
        if self.jumping and not self.is_on_ladder:
            if self.change_y >= 0:
                self.texture = self.jump_texture_pair[self.character_face_direction]
            else:
                self.texture = self.fall_texture_pair[self.character_face_direction]
            return

        # Idle animation
        if self.change_x == 0:
            self.texture = self.idle_texture_pair[self.character_face_direction]
            return

        # Walking animation
        self.cur_texture += 1
        if self.cur_texture > 7*updates_per_frame:
            self.cur_texture = 0
        self.texture = self.walk_textures[self.cur_texture//updates_per_frame][self.character_face_direction]

class MyGame(arcade.Window):
    """
    Main application class.
    """

    def __init__(self):

        # Call the parent class and set up the window
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False
        self.jump_needs_reset = False

        # These are lists that are going to keep track of our sprites. Each sprite should go into a list
        self.coin_list = None
        self.wall_list = None
        self.background_list = None
        self.dont_touch_list = None
        self.ladder_list = None
        self.player_list = None
        self.foreground_list = None

        # Seperate variable that will hold the player sprite
        self.player_sprite = None

        # Our physics engine
        self.physics_engine = None

        # Used to keep track of our scrolling (0,0) is bottom left of our world
        self.view_bottom = 0
        self.view_left = 0

        # Where is the right end of the map?
        self.end_of_map = 0

        # Keep track of score
        self.score = 0

        # Level
        self.level = 1

        # Load Sounds
        self.collect_coin_sound = arcade.load_sound("sounds/coin3.wav")
        self.jump_sound = arcade.load_sound("sounds/jump1.wav")
        self.game_over = arcade.load_sound("sounds/gameover2.wav")

        arcade.set_background_color(arcade.csscolor.DEEP_SKY_BLUE) # Set background colour

    def setup(self, level):
        """ Set up the game here. Call this function to restart the game. """

        # Used to keep track of scrolling
        self.view_bottom = 0
        self.view_left = 0

        # Keep track of the score
        self.score = 0

        # Create the sprite lists
        self.player_list = arcade.SpriteList()
        self.wall_list = arcade.SpriteList()
        self.coin_list = arcade.SpriteList()
        self.foreground_list = arcade.SpriteList()
        self.background_list = arcade.SpriteList()

        # Set up the player, specifically placing it at these coordinates
        self.player_sprite = PlayerCharacter() # Create Sprite
        self.player_sprite.center_x = player_start_x # Set x
        self.player_sprite.center_y = player_start_y # Set y
        self.player_sprite.update_animation(0)
        self.player_list.append(self.player_sprite) # Append to sprite list

        "---------Load Map from Tile Editor------------"

        # Name of the layer in the file that has our platforms/walls
        platforms_layer_name = 'Platforms'
        moving_platforms_layer_name = "Moving Platforms"
        # Name of the layer that has items for pick-up
        coins_layer_name = "Coins"
        # Name of the layer that has items for foreground
        foreground_layer_name = "Foreground"
        # Name of the layer that has items for background
        background_layer_name = "Background"
        # Name of the layer that has items we shouldn't touch
        dont_touch_layer_name = "Don't Touch"

        # Map Name
        map_name = f"the_map_level_{level}.tmx" # Initialization is set to 1

        # Read in the tiled map
        my_map = arcade.tilemap.read_tmx(map_name)

        # Calculate the right edge of my_map in pixels
        # self.end_of_map = my_map.map_size.width*grid_pixel_size

        self.end_of_map = my_map.map_size.width * grid_pixel_size

        # -- Background
        # -- Things that we can pass in front of
        self.background_list = arcade.tilemap.process_layer(my_map, background_layer_name, tile_scaling)

        # -- Ladder
        self.ladder_list = arcade.tilemap.process_layer(my_map, "Ladders", tile_scaling)

        # -- Foreground
        # -- Things that we can pass behind of
        self.foreground_list = arcade.tilemap.process_layer(my_map, foreground_layer_name, tile_scaling)

        # -- Platforms
        # -- Things that we can't move through
        self.wall_list = arcade.tilemap.process_layer(my_map, platforms_layer_name, tile_scaling)

        # -- Moving Platforms
        moving_platforms_list = arcade.tilemap.process_layer(my_map, moving_platforms_layer_name, tile_scaling)
        for sprite in moving_platforms_list:
            self.wall_list.append(sprite)

        # -- Coins
        # -- Things that we can grab
        self.coin_list = arcade.tilemap.process_layer(my_map, coins_layer_name, coin_scaling)

        # -- Don't Touch Layer
        # -- Things that will reset us
        self.dont_touch_list = arcade.tilemap.process_layer(my_map, dont_touch_layer_name, tile_scaling)

        self.end_of_map = my_map.map_size.width * grid_pixel_size

        # --- Other stuff
        # Set the background color
        if my_map.background_color:
            arcade.set_background_color(my_map.background_color)

        # Create the "physics engine" (prevent character from being able to move through walls)
        # Takes two primary parameters (1. item that is moving, 2. ist of things that you can't move through)
        self.physics_engine = arcade.PhysicsEnginePlatformer(self.player_sprite, self.wall_list, gravity_constant =gravity, ladders=self.ladder_list)


    def on_draw(self):
        """ Render the screen. """

        # Clear the screen to the background colour
        arcade.start_render()

        # Draw our sprites (Order Matters, last one drawn will appear on top of everything else)
        self.wall_list.draw()
        self.background_list.draw()
        self.wall_list.draw()
        self.ladder_list.draw()
        self.coin_list.draw()
        self.dont_touch_list.draw()
        self.player_list.draw()
        self.foreground_list.draw()


        # Draw our score on the screen, scrolling it with viewpoint
        score_text = f"Score: {self.score}"
        arcade.draw_text(score_text, 10 + self.view_left, 10 + self.view_bottom, arcade.csscolor.BLACK, 18)

    def process_keychange(self):
        """
        Called when we change a key up/down or we move on/off a ladder.
        """
        # Process up/down
        if self.up_pressed and not self.down_pressed:
            if self.physics_engine.is_on_ladder():
                self.player_sprite.change_y = player_movement_speed
            elif self.physics_engine.can_jump() and not self.jump_needs_reset:
                self.player_sprite.change_y = player_jump_speed
                self.player_sprite.jumping = True # I Added This
                self.jump_needs_reset = True
                arcade.play_sound(self.jump_sound)
        elif self.down_pressed and not self.up_pressed:
            if self.physics_engine.is_on_ladder():
                self.player_sprite.change_y = -player_movement_speed

        # Process up/down when on a ladder and no movement
        if self.physics_engine.is_on_ladder():
            if not self.up_pressed and not self.down_pressed:
                self.player_sprite.change_y = 0
            elif self.up_pressed and self.down_pressed:
                self.player_sprite.change_y = 0

        # Process left/right
        if self.right_pressed and not self.left_pressed:
            self.player_sprite.change_x = player_movement_speed
        elif self.left_pressed and not self.right_pressed:
            self.player_sprite.change_x = -player_movement_speed
        else:
            self.player_sprite.change_x = 0

    def on_key_press(self, key, modifiers):
        """Called whenever a key is pressed. """

        if key == arcade.key.UP or key == arcade.key.W:
            self.up_pressed = True
        elif key == arcade.key.DOWN or key == arcade.key.S:
            self.down_pressed = True
        elif key == arcade.key.LEFT or key == arcade.key.A:
            self.left_pressed = True
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.right_pressed = True

        self.process_keychange()

    def on_key_release(self, key, modifiers):
        """Called when the user releases a key. """

        if key == arcade.key.UP or key == arcade.key.W:
            self.up_pressed = False
            self.jump_needs_reset = False
        elif key == arcade.key.DOWN or key == arcade.key.S:
            self.down_pressed = False
        elif key == arcade.key.LEFT or key == arcade.key.A:
            self.left_pressed = False
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.right_pressed = False

        self.process_keychange()

    def update(self, delta_time):
        """ Movement and game logic """

        # Move the player with the physics engine
        self.physics_engine.update()

        # Update animations
        if self.physics_engine.can_jump():
            self.player_sprite.jumping = False
            self.player_sprite.can_jump = False
        else:
            self.player_sprite.can_jump = True

        if self.physics_engine.is_on_ladder() and not self.physics_engine.can_jump():
            self.player_sprite.is_on_ladder = True
            self.process_keychange()
        else:
            self.player_sprite.is_on_ladder = False
            self.process_keychange()

        self.player_list.update_animation(delta_time)

        self.coin_list.update_animation(delta_time)
        self.background_list.update_animation(delta_time)

        # Update walls, used with moving platforms
        self.wall_list.update()

        self.coin_list.update_animation(delta_time)
        self.background_list.update_animation(delta_time)

        # Update walls, used with moving platforms
        self.wall_list.update()

        # See if the wall hit a boundary and needs to reverse direction.
        for wall in self.wall_list:
            if wall.boundary_right and wall.right > wall.boundary_right and wall.change_x > 0:
                wall.change_x *= -1
            if wall.boundary_left and wall.left < wall.boundary_left and wall.change_x < 0:
                wall.change_x *= -1
            if wall.boundary_top and wall.top > wall.boundary_top and wall.change_y > 0:
                wall.change_y *= -1
            if wall.boundary_bottom and wall.bottom < wall.boundary_bottom and wall.change_y < 0:
                wall.change_y *= -1

        # See if we hit any coins
        coin_hit_list = arcade.check_for_collision_with_list(self.player_sprite, self.coin_list)

        # Loop through each coin we hit (if any) and remove it
        for coin in coin_hit_list:
            # Remove the Coin
            coin.remove_from_sprite_lists()
            # Play a Sound
            arcade.play_sound(self.collect_coin_sound)
            # Add One to the Score
            self.score += 1

        "Manage Scrolling"

        # Track if we need to change viewpoint
        changed = False # Set to false to indicate that we don't need to scroll

        # Did the player fall off the map?
        if self.player_sprite.center_y < -100:
            self.player_sprite.center_x = player_start_x
            self.player_sprite.center_y = player_start_y

            # Set the camera to the start
            self.view_left = 0
            self.view_bottom = 0
            changed = True
            arcade.play_sound(self.game_over)

        # Did the player touch something they should not?
        if arcade.check_for_collision_with_list(self.player_sprite, self.dont_touch_list):
            self.player_sprite.change_x = 0
            self.player_sprite.change_y = 0
            self.player_sprite.center_x = player_start_x
            self.player_sprite.center_y = player_start_y

            # Set the camera to the start
            self.view_left = 0
            self.view_bottom = 0
            changed = True
            arcade.play_sound(self.game_over)

        # See if the user got to the end of the level
        if self.player_sprite.center_x >= self.end_of_map:
            # Advance to the next level
            self.level += 1

            # Load the next level
            self.setup(self.level)

            # Set the camera to the start
            self.view_left = 0
            self.view_bottom = 0
            changed = True

        # Scroll Left
        left_boundary = self.view_left + left_viewpoint_margin
        if self.player_sprite.left < left_boundary:
            self.view_left -= left_boundary - self.player_sprite.left
            changed = True

        # Scroll Right
        right_boundary = self.view_left + SCREEN_WIDTH - right_viewpoint_margin
        if self.player_sprite.right > right_boundary:
            self.view_left += self.player_sprite.right - right_boundary
            changed = True

        # Scroll Up
        top_boundary = self.view_bottom + SCREEN_HEIGHT - top_viewpoint_margin
        if self.player_sprite.top > top_boundary:
            self.view_bottom += self.player_sprite.top - top_boundary
            changed = True

        # Scroll Down
        bottom_boundary = self.view_bottom + bottom_viewpoint_margin
        if self.player_sprite.bottom < bottom_boundary:
            self.view_bottom -= bottom_boundary - self.player_sprite.bottom
            changed = True

        if changed:
            # Only scroll to integers, or else pixels don't line up with screen
            self.view_bottom = int(self.view_bottom)
            self.view_left = int(self.view_left)

            # Actually do the scrolling
            arcade.set_viewport(self.view_left, SCREEN_WIDTH + self.view_left, self.view_bottom, self.view_bottom + SCREEN_HEIGHT)

def main():
    """ Main method """
    window = MyGame()
    window.setup(window.level)
    arcade.run()

if __name__ == "__main__":
    main()