import arcade
import random
import math

# --- Constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "Hero Aircraft Shooter"

# Constants used to scale our sprites from their original size
ENEMY_SCALING = 0.5
BULLET_SCALING = 0.3  # Reduced size to make it look like a small missile/bolt
ENEMY_BULLET_SCALING = 0.4

# Aircraft movement speed
PLAYER_MOVEMENT_SPEED = 5
ENEMY_SPEED = 2
BULLET_SPEED = 10
ENEMY_BULLET_SPEED = 6

# Firing rate (seconds between shots)
SHOOT_INTERVAL = 0.15

# How long the health bar is displayed after taking damage (in seconds)
HEALTH_BAR_DISPLAY_TIME = 1.5


def draw_custom_rect(center_x, center_y, width, height, color):
    """ Draw a rectangle using two triangles to avoid version issues with newer arcade libraries """
    hw = width / 2
    hh = height / 2

    # Triangle 1 (Top-Left, Top-Right, Bottom-Left)
    arcade.draw_triangle_filled(
        center_x - hw, center_y + hh,
        center_x + hw, center_y + hh,
        center_x - hw, center_y - hh,
        color
    )
    # Triangle 2 (Top-Right, Bottom-Right, Bottom-Left)
    arcade.draw_triangle_filled(
        center_x + hw, center_y + hh,
        center_x + hw, center_y - hh,
        center_x - hw, center_y - hh,
        color
    )


class Enemy(arcade.Sprite):
    """ Custom Enemy class to handle health bars """

    def __init__(self, image, scale):
        super().__init__(image, scale)
        self.max_health = 3
        self.health = 3
        self.show_health_timer = 0.0

    def draw_health_bar(self):
        """ Draw a health bar above the enemy """
        if self.show_health_timer <= 0:
            return

        bar_width = 40
        bar_height = 5

        # Draw the red background
        draw_custom_rect(self.center_x, self.top + 10, bar_width, bar_height, arcade.color.RED)

        # Calculate the green foreground width based on health
        health_ratio = max(self.health / self.max_health, 0)
        green_width = bar_width * health_ratio

        if green_width > 0:
            # Shift the green bar so it aligns to the left side
            green_x = self.center_x - (bar_width / 2) + (green_width / 2)
            draw_custom_rect(green_x, self.top + 10, green_width, bar_height, arcade.color.GREEN)


class ShootingEnemy(Enemy):
    """ A new enemy type that shoots bullets in random directions """

    def __init__(self, image, scale):
        super().__init__(image, scale)
        self.max_health = 5  # Slightly tougher than regular enemies
        self.health = 5
        self.time_since_last_shot = 0.0
        self.shoot_interval = random.uniform(0.5, 2.0)


class MyGame(arcade.Window):
    """
    Main application class for the game.
    """

    def __init__(self):
        # Call the parent class and set up the window
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

        # Sprite lists
        self.enemy_list = None
        self.bullet_list = None
        self.enemy_bullet_list = None

        # Player variables based on your math measurements
        self.player_x = 0
        self.player_y = 0
        self.player_angle = 90
        self.player_redius = 20

        # Player Health
        self.player_max_health = 100
        self.player_health = 100
        self.player_show_health_timer = 0.0

        # Mouse tracking for rotation
        self.mouse_x = SCREEN_WIDTH / 2
        self.mouse_y = SCREEN_HEIGHT / 2

        # Keep track of key presses for smooth movement
        self.up_pressed = False
        self.down_pressed = False
        self.left_pressed = False
        self.right_pressed = False

        # Continuous shooting tracking
        self.is_shooting = False
        self.time_since_last_shot = 0.0

        # Keep track of the score
        self.score = 0
        self.score_text = None

        # Set the background color
        arcade.set_background_color(arcade.color.AMAZON)

    def setup(self):
        """ Set up the game and initialize the variables. """

        # Create the sprite lists
        self.enemy_list = arcade.SpriteList()
        self.bullet_list = arcade.SpriteList()
        self.enemy_bullet_list = arcade.SpriteList()

        # Score
        self.score = 0
        self.score_text = arcade.Text(f"Score: {self.score}", 10, 10, arcade.color.WHITE, 14, bold=True)

        # Set up the player initial state
        self.player_x = SCREEN_WIDTH / 2
        self.player_y = 50
        self.player_angle = 90  # 90 degrees points straight up
        self.player_health = self.player_max_health
        self.player_show_health_timer = 0.0

        # Reset shooting variables
        self.is_shooting = False
        self.time_since_last_shot = SHOOT_INTERVAL  # Allows firing immediately on first click

        # Spawn a few initial enemies
        for i in range(5):
            self.spawn_enemy()

    def spawn_enemy(self):
        """ Create a new enemy aircraft and add it to the game. """
        # 30% chance to spawn the new shooting enemy
        if random.random() < 0.3:
            enemy = ShootingEnemy(":resources:images/space_shooter/playerShip1_green.png", ENEMY_SCALING)
        else:
            enemy = Enemy(":resources:images/space_shooter/playerShip3_orange.png", ENEMY_SCALING)

        # Pick a random spawn side: top (front), left, or right
        side = random.choice(["top", "left", "right"])

        if side == "top":
            enemy.center_x = random.randrange(50, SCREEN_WIDTH - 50)
            enemy.center_y = random.randrange(SCREEN_HEIGHT + 20, SCREEN_HEIGHT + 150)
        elif side == "left":
            enemy.center_x = random.randrange(-150, -20)
            enemy.center_y = random.randrange(50, SCREEN_HEIGHT - 50)
        elif side == "right":
            enemy.center_x = random.randrange(SCREEN_WIDTH + 20, SCREEN_WIDTH + 150)
            enemy.center_y = random.randrange(50, SCREEN_HEIGHT - 50)

        self.enemy_list.append(enemy)

    def enemy_shoot(self, enemy):
        """ Handles shooting logic for the new ShootingEnemy """
        bullet = arcade.Sprite(":resources:images/space_shooter/laserRed01.png", ENEMY_BULLET_SCALING)
        bullet.center_x = enemy.center_x
        bullet.center_y = enemy.center_y

        # Shoot directly at the player
        dy = self.player_y - enemy.center_y
        dx = self.player_x - enemy.center_x
        angle = math.atan2(dy, dx)

        bullet.change_x = math.cos(angle) * ENEMY_BULLET_SPEED
        bullet.change_y = math.sin(angle) * ENEMY_BULLET_SPEED
        bullet.angle = math.degrees(angle) - 90  # Visually rotate the bullet

        self.enemy_bullet_list.append(bullet)

    def shoot_bullet(self):
        """ Handles the creation and trajectory of a single bullet """
        bullet = arcade.Sprite(":resources:images/space_shooter/laserBlue01.png", BULLET_SCALING)

        # Position the bullet at the tip of the player's triangle
        bullet.center_x = self.player_x + math.cos(math.radians(self.player_angle)) * self.player_redius * 1.5
        bullet.center_y = self.player_y + math.sin(math.radians(self.player_angle)) * self.player_redius * 1.5

        # Send the bullet exactly in the direction the triangle is pointing
        bullet.change_x = math.cos(math.radians(self.player_angle)) * BULLET_SPEED
        bullet.change_y = math.sin(math.radians(self.player_angle)) * BULLET_SPEED

        # Visually rotate the bullet sprite to match trajectory (-90 because standard sprite points up)
        bullet.angle = self.player_angle - 90

        self.bullet_list.append(bullet)

    def on_draw(self):
        """ Render the screen. """

        # self.clear() replaces arcade.start_render() in modern versions
        self.clear()

        # Draw the Player using your triangle measurements!
        arcade.draw_triangle_filled(
            self.player_x + math.cos(math.radians(self.player_angle)) * self.player_redius * 1.5,
            self.player_y + math.sin(math.radians(self.player_angle)) * self.player_redius * 1.5,
            self.player_x + math.cos(math.radians(self.player_angle + 150)) * self.player_redius,
            self.player_y + math.sin(math.radians(self.player_angle + 150)) * self.player_redius,
            self.player_x + math.cos(math.radians(self.player_angle - 150)) * self.player_redius,
            self.player_y + math.sin(math.radians(self.player_angle - 150)) * self.player_redius,
            arcade.color.WHITE
        )

        # Draw Player Health Bar under the player ONLY if timer > 0
        if self.player_show_health_timer > 0:
            p_bar_width = 50
            p_bar_height = 8
            draw_custom_rect(self.player_x, self.player_y - 30, p_bar_width, p_bar_height, arcade.color.RED)

            health_ratio = max(self.player_health / self.player_max_health, 0)
            p_green_width = p_bar_width * health_ratio
            if p_green_width > 0:
                p_green_x = self.player_x - (p_bar_width / 2) + (p_green_width / 2)
                draw_custom_rect(p_green_x, self.player_y - 30, p_green_width, p_bar_height, arcade.color.GREEN)

        # Draw all the sprites
        self.enemy_list.draw()
        self.bullet_list.draw()
        self.enemy_bullet_list.draw()

        # Draw enemy health bars
        for enemy in self.enemy_list:
            enemy.draw_health_bar()

        # Draw our score on the screen
        self.score_text.draw()

    def on_update(self, delta_time):
        """ Movement and game logic """

        self.bullet_list.update()
        self.enemy_list.update()
        self.enemy_bullet_list.update()

        # Decrease player health display timer
        if self.player_show_health_timer > 0:
            self.player_show_health_timer -= delta_time

        # --- Continuous Shooting Logic ---
        self.time_since_last_shot += delta_time
        if self.is_shooting and self.time_since_last_shot >= SHOOT_INTERVAL:
            self.shoot_bullet()
            self.time_since_last_shot = 0.0

        # --- Player Rotation Logic (Aim at Mouse) ---
        dx = self.mouse_x - self.player_x
        dy = self.mouse_y - self.player_y
        self.player_angle = math.degrees(math.atan2(dy, dx))

        # --- Player Movement Logic (WASD/B Navigation) ---
        if self.up_pressed:
            self.player_y += PLAYER_MOVEMENT_SPEED
        if self.down_pressed:
            self.player_y -= PLAYER_MOVEMENT_SPEED
        if self.left_pressed:
            self.player_x -= PLAYER_MOVEMENT_SPEED
        if self.right_pressed:
            self.player_x += PLAYER_MOVEMENT_SPEED

        # --- Manage Boundaries for the Player ---
        if self.player_x < 0:
            self.player_x = 0
        elif self.player_x > SCREEN_WIDTH - 1:
            self.player_x = SCREEN_WIDTH - 1

        if self.player_y < 0:
            self.player_y = 0
        elif self.player_y > SCREEN_HEIGHT - 1:
            self.player_y = SCREEN_HEIGHT - 1

        # --- Enemy Logic (Movement & Shooting) ---

        # hi
        for enemy in self.enemy_list:
            # Decrease enemy health display timer
            if enemy.show_health_timer > 0:
                enemy.show_health_timer -= delta_time

            # 1. Constantly aim and move towards the player
            dy = self.player_y - enemy.center_y
            dx = self.player_x - enemy.center_x
            angle = math.atan2(dy, dx)

            speed = ENEMY_SPEED - 0.5 if isinstance(enemy, ShootingEnemy) else ENEMY_SPEED
            enemy.change_x = math.cos(angle) * speed
            enemy.change_y = math.sin(angle) * speed
            enemy.angle = math.degrees(angle) - 90

            # 2. Shooting Logic for ShootingEnemy
            if isinstance(enemy, ShootingEnemy):
                enemy.time_since_last_shot += delta_time
                if enemy.time_since_last_shot >= enemy.shoot_interval:
                    self.enemy_shoot(enemy)
                    enemy.time_since_last_shot = 0.0
                    enemy.shoot_interval = random.uniform(0.5, 2.0)  # Reset interval

            # 3. Cleanup if they somehow get way out of bounds (anti-bug)
            if enemy.center_x < -300 or enemy.center_x > SCREEN_WIDTH + 300 or \
                    enemy.center_y < -300 or enemy.center_y > SCREEN_HEIGHT + 300:
                enemy.remove_from_sprite_lists()
                self.spawn_enemy()

        # --- Collision Logic ---

        # 1. Player getting hit by Enemies
        for enemy in self.enemy_list:
            # Calculate distance between player center and enemy center
            distance = math.hypot(self.player_x - enemy.center_x, self.player_y - enemy.center_y)
            # If distance is less than their combined radius, it's a hit!
            if distance < self.player_redius + (enemy.width / 2):
                enemy.remove_from_sprite_lists()
                self.player_health -= 20  # Player takes damage
                self.player_show_health_timer = HEALTH_BAR_DISPLAY_TIME  # Show health bar briefly
                self.spawn_enemy()

                # Simple game over check
                if self.player_health <= 0:
                    print("Game Over! Restarting...")
                    self.setup()  # Restart the game automatically

        # 2. Bullets hitting Enemies
        for bullet in self.bullet_list:
            hit_list = arcade.check_for_collision_with_list(bullet, self.enemy_list)

            # If bullet hit something, destroy bullet
            if len(hit_list) > 0:
                bullet.remove_from_sprite_lists()

            for enemy in hit_list:
                enemy.health -= 1  # Reduce enemy health
                enemy.show_health_timer = HEALTH_BAR_DISPLAY_TIME  # Show health bar briefly

                # If enemy runs out of health, destroy it
                if enemy.health <= 0:
                    enemy.remove_from_sprite_lists()
                    self.score += 1
                    self.score_text.text = f"Score: {self.score}"
                    self.spawn_enemy()

            # Remove bullets flying off screen
            if bullet.bottom > SCREEN_HEIGHT or bullet.top < 0 or bullet.left < 0 or bullet.right > SCREEN_WIDTH:
                bullet.remove_from_sprite_lists()

        # 3. Enemy Bullets hitting Player
        for bullet in self.enemy_bullet_list:
            # Calculate distance between player and enemy bullet
            distance = math.hypot(self.player_x - bullet.center_x, self.player_y - bullet.center_y)

            # Check collision (using player radius)
            if distance < self.player_redius + (bullet.width / 2):
                bullet.remove_from_sprite_lists()
                self.player_health -= 10  # Player takes 10 damage
                self.player_show_health_timer = HEALTH_BAR_DISPLAY_TIME

                if self.player_health <= 0:
                    print("Game Over! Restarting...")
                    self.setup()

            # Remove bullets flying off screen
            elif bullet.bottom > SCREEN_HEIGHT or bullet.top < 0 or bullet.left < 0 or bullet.right > SCREEN_WIDTH:
                bullet.remove_from_sprite_lists()

    def on_mouse_motion(self, x, y, dx, dy):
        """ Called whenever the mouse moves. """
        self.mouse_x = x
        self.mouse_y = y

    def on_key_press(self, key, modifiers):
        """ Called whenever a key is pressed. """
        if key == arcade.key.W:
            self.up_pressed = True
        elif key == arcade.key.S:
            self.down_pressed = True
        elif key == arcade.key.A:
            self.left_pressed = True
        elif key == arcade.key.D or key == arcade.key.B:
            self.right_pressed = True

    def on_key_release(self, key, modifiers):
        """ Called when the user releases a key. """
        if key == arcade.key.W:
            self.up_pressed = False
        elif key == arcade.key.S:
            self.down_pressed = False
        elif key == arcade.key.A:
            self.left_pressed = False
        elif key == arcade.key.D or key == arcade.key.B:
            self.right_pressed = False

    def on_mouse_press(self, x, y, button, modifiers):
        """ Called whenever the mouse button is clicked. """
        if button == arcade.MOUSE_BUTTON_LEFT:
            self.is_shooting = True

    def on_mouse_release(self, x, y, button, modifiers):
        """ Called whenever the mouse button is released. """
        if button == arcade.MOUSE_BUTTON_LEFT:
            self.is_shooting = False


def main():
    """ Main function to run the game """
    window = MyGame()
    window.setup()
    arcade.run()


if __name__ == "__main__":
    main()