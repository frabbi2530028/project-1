import arcade
import math
from pymunk.examples.spiderweb import window

SCREEN_WIDTH = 900
SCREEN_HEIGHT = 600
SCREEN_TITLE = "Project Game"

PLAYER_SCALE = 0.3


class GameWindow(arcade.Window):
    def __init__(self):
        super(). __init__(SCREEN_WIDTH, SCREEN_HEIGHT,SCREEN_TITLE)
        arcade.set_background_color(arcade.color.BLACK)

        self.player_x = SCREEN_WIDTH / 2
        self.player_y = SCREEN_HEIGHT / 2
        self.player_angle = 0
        self.player_redius = 150 * PLAYER_SCALE

    def on_draw(self):
        arcade.start_render()

        arcade.draw_triangle_filled(
            self.player_x +math.cos(math.radians(self.player_angle)) * self.player_redius * 1.5,
            self.player_y +math.sin(math.radians(self.player_angle)) * self.player_redius * 1.5,
            self.player_x+ math.cos(math.radians(self.player_angle + 150)) * self.player_redius,
            self.player_y+ math.sin(math.radians(self.player_angle + 150)) * self.player_redius,
            self.player_x+ math.cos(math.radians(self.player_angle - 150)) * self.player_redius,
            self.player_y+ math.sin(math.radians(self.player_angle - 150)) * self.player_redius,
            arcade.color.WHITE
            )

    def main():
        window = GameWindow()
        arcade.run()

    if __name__ == '__main__':
        main()