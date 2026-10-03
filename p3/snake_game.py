"""A polished Snake game built with Tkinter.

Run with:  python snake_game.py
Controls:  Arrow keys or WASD to move, R to restart after game over.
"""

import math
import random
import tkinter as tk

# ---- Grid / gameplay (preserved exactly) ------------------------------------
GRID_WIDTH = 30               # columns in the play field
GRID_HEIGHT = 20              # rows in the play field
CELL_SIZE = 20                # pixels per cell
BOARD_WIDTH = GRID_WIDTH * CELL_SIZE     # 600 px play field width
BOARD_HEIGHT = GRID_HEIGHT * CELL_SIZE   # 400 px play field height
TICK_MS = 100                 # milliseconds between each snake move (game speed)

# ---- Window layout ---------------------------------------------------------
WINDOW_WIDTH = 640            # total window width (board + side padding)
WINDOW_HEIGHT = 520           # total window height (HUD + board + bottom padding)
BOARD_X = 20                  # left offset of the board (centers 600 in 640)
BOARD_Y = 100                 # top offset of the board (HUD sits above)

# ---- Colors (modern dark, green-accented theme) ----------------------------
BG_TOP = "#101A14"            # gradient top (deep dark green)
BG_BOTTOM = "#0A110D"         # gradient bottom (darker)
BOARD_BG = "#142019"          # board fill
BOARD_GRID = "#1C2A22"        # subtle grid lines
BOARD_BORDER = "#2E4334"      # board border
SNAKE_BODY = "#3DDC84"        # vibrant green body
SNAKE_HEAD = "#7BED9F"        # brighter green head
SNAKE_SHADOW = "#1E6B43"      # dark green outline (shadow effect)
SNAKE_HIGHLIGHT = "#C6F8DE"   # light highlight on the head
FOOD = "#FF6B6B"              # coral red food
FOOD_HIGHLIGHT = "#FFD0D0"    # shine on the food
TEXT = "#E8F0EA"              # off-white text
TEXT_MUTED = "#7A8C80"        # muted text
ACCENT = "#A3E635"            # lime accent (title / score)
CARD_BG = "#1A2922"           # card background
CARD_BORDER = "#2E4334"       # card border
OVERLAY_BG = "#1B2A22"        # game-over card background


def lerp_color(c1, c2, t):
    """Blend linearly between two hex colors by t (0..1)."""
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02X}{g:02X}{b:02X}"


def random_food(snake):
    """Return a random cell that is not occupied by the snake."""
    while True:
        food = (random.randint(0, GRID_WIDTH - 1),
                random.randint(0, GRID_HEIGHT - 1))
        if food not in snake:        # make sure food does not spawn on the snake
            return food


def reset_game():
    """Reset the snake, direction, food, and score to their starting state."""
    start = (GRID_WIDTH // 2, GRID_HEIGHT // 2)   # snake starts in the middle
    snake = [start, (start[0] - 1, start[1]), (start[0] - 2, start[1])]
    direction = (1, 0)            # moving right initially
    food = random_food(snake)
    score = 0
    return snake, direction, food, score


class SnakeGame:
    """Main game class: sets up the window, handles input, and runs the loop."""

    def __init__(self, root):
        self.root = root
        self.root.title("Snake Game")
        self.root.resizable(False, False)

        # Canvas is where everything is drawn
        self.canvas = tk.Canvas(root, width=WINDOW_WIDTH, height=WINDOW_HEIGHT,
                                bg=BG_BOTTOM, highlightthickness=0)
        self.canvas.pack()

        # Center the window on screen for a balanced layout
        self.root.update_idletasks()
        sx = (self.root.winfo_screenwidth() - WINDOW_WIDTH) // 2
        sy = (self.root.winfo_screenheight() - WINDOW_HEIGHT) // 2
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{sx}+{sy}")

        # Bind keyboard events to the root window
        self.root.bind("<KeyPress>", self.on_key)

        # Initialize game state
        self.snake, self.direction, self.food, self.score = reset_game()
        self.game_over = False
        self.frame = 0            # animation counter (drives subtle pulses)

        self.draw()                       # draw the first frame
        self.root.after(TICK_MS, self.tick)  # start the game loop

    # ---- Input / game logic (behavior unchanged) ---------------------------
    def on_key(self, event):
        """Handle keyboard input for movement and restart."""
        key = event.keysym

        # Restart the game when R is pressed after game over
        if self.game_over and key in ("r", "R"):
            self.snake, self.direction, self.food, self.score = reset_game()
            self.game_over = False
            self.draw()
            return

        if self.game_over:
            return

        # Change direction with arrow keys or WASD.
        # Ignore the reverse direction so the snake cannot fold into itself.
        if key in ("Up", "w", "W") and self.direction != (0, 1):
            self.direction = (0, -1)
        elif key in ("Down", "s", "S") and self.direction != (0, -1):
            self.direction = (0, 1)
        elif key in ("Left", "a", "A") and self.direction != (1, 0):
            self.direction = (-1, 0)
        elif key in ("Right", "d", "D") and self.direction != (-1, 0):
            self.direction = (1, 0)

    def tick(self):
        """Advance the game by one step, then schedule the next tick."""
        if not self.game_over:
            self.move_snake()
        self.draw()               # always redraw so animations keep running

        # Schedule the next tick to keep the game running at a steady speed
        self.root.after(TICK_MS, self.tick)

    def move_snake(self):
        """Move the snake forward one cell and check for collisions / food."""
        head_x, head_y = self.snake[0]
        new_head = (head_x + self.direction[0], head_y + self.direction[1])

        # Game over if the snake hits a wall
        if (new_head[0] < 0 or new_head[0] >= GRID_WIDTH or
                new_head[1] < 0 or new_head[1] >= GRID_HEIGHT):
            self.game_over = True
            return

        # Game over if the snake hits its own body
        if new_head in self.snake:
            self.game_over = True
            return

        self.snake.insert(0, new_head)        # move the head forward

        if new_head == self.food:
            self.score += 1                    # eat food: grow and score
            self.food = random_food(self.snake)  # spawn new food
        else:
            self.snake.pop()                   # did not eat: remove the tail

    # ---- Drawing helpers ----------------------------------------------------
    def round_rect(self, x1, y1, x2, y2, r, **kwargs):
        """Rounded rectangle via a smooth polygon (Tkinter has no native one)."""
        r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
        points = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        ]
        return self.canvas.create_polygon(points, smooth=True, splinesteps=18, **kwargs)

    def draw_background(self):
        """Subtle vertical gradient filling the whole window."""
        band = 6
        for y in range(0, WINDOW_HEIGHT, band):
            color = lerp_color(BG_TOP, BG_BOTTOM, y / WINDOW_HEIGHT)
            self.canvas.create_rectangle(0, y, WINDOW_WIDTH, y + band,
                                         fill=color, outline="")

    def draw_hud(self):
        """Title and score card above the board."""
        # Title
        self.canvas.create_text(BOARD_X, 42, anchor="w", text="SNAKE",
                                fill=ACCENT, font=("Arial", 30, "bold"))
        self.canvas.create_text(BOARD_X, 64, anchor="w", text="ARCADE",
                                fill=TEXT_MUTED, font=("Arial", 10, "bold"))
        # Score card
        cx, cy, cw, ch = 458, 14, 162, 68
        self.round_rect(cx, cy, cx + cw, cy + ch, 12,
                        fill=CARD_BG, outline=CARD_BORDER)
        self.canvas.create_text(cx + 14, cy + 14, anchor="w", text="SCORE",
                                fill=TEXT_MUTED, font=("Arial", 10, "bold"))
        self.canvas.create_text(cx + 14, cy + 44, anchor="w", text=str(self.score),
                                fill=ACCENT, font=("Arial", 26, "bold"))

    def draw_board(self):
        """Board background, rounded border, and subtle grid lines."""
        self.round_rect(BOARD_X, BOARD_Y,
                        BOARD_X + BOARD_WIDTH, BOARD_Y + BOARD_HEIGHT,
                        14, fill=BOARD_BG, outline=BOARD_BORDER, width=2)
        for col in range(1, GRID_WIDTH):
            x = BOARD_X + col * CELL_SIZE
            self.canvas.create_line(x, BOARD_Y, x, BOARD_Y + BOARD_HEIGHT,
                                    fill=BOARD_GRID)
        for row in range(1, GRID_HEIGHT):
            y = BOARD_Y + row * CELL_SIZE
            self.canvas.create_line(BOARD_X, y, BOARD_X + BOARD_WIDTH, y,
                                    fill=BOARD_GRID)

    def draw_snake(self):
        """Rounded segments with a brighter head, highlight, and shadow outline."""
        for index, (sx, sy) in enumerate(self.snake):
            x1 = BOARD_X + sx * CELL_SIZE
            y1 = BOARD_Y + sy * CELL_SIZE
            x2 = x1 + CELL_SIZE
            y2 = y1 + CELL_SIZE
            if index == 0:
                # Head: slightly larger, brighter, with a small highlight dot
                self.round_rect(x1 + 1, y1 + 1, x2 - 1, y2 - 1, 7,
                                fill=SNAKE_HEAD, outline=SNAKE_SHADOW)
                self.canvas.create_oval(x1 + 4, y1 + 4, x1 + 9, y1 + 9,
                                        fill=SNAKE_HIGHLIGHT, outline="")
            else:
                # Body: rounded tile with a 2px gap for a clean segmented look
                self.round_rect(x1 + 2, y1 + 2, x2 - 2, y2 - 2, 6,
                                fill=SNAKE_BODY, outline=SNAKE_SHADOW)

    def draw_food(self):
        """Pulsing food with a soft glow and a shine highlight."""
        fx, fy = self.food
        cx = BOARD_X + fx * CELL_SIZE + CELL_SIZE / 2
        cy = BOARD_Y + fy * CELL_SIZE + CELL_SIZE / 2
        pulse = 1 + 0.10 * math.sin(self.frame * 0.25)   # gentle size pulse
        r = (CELL_SIZE / 2 - 3) * pulse
        # Glow (semi-transparent aura via stipple)
        self.canvas.create_oval(cx - r - 4, cy - r - 4, cx + r + 4, cy + r + 4,
                                fill=FOOD, outline="", stipple="gray25")
        # Main food
        self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                fill=FOOD, outline="")
        # Shine
        self.canvas.create_oval(cx - r * 0.45, cy - r * 0.45,
                                cx - r * 0.1, cy - r * 0.1,
                                fill=FOOD_HIGHLIGHT, outline="")

    def draw_overlay(self):
        """Dimmed, centered game-over card with final score and restart hint."""
        # Dim the board area behind the overlay (semi-transparent via stipple)
        self.canvas.create_rectangle(BOARD_X, BOARD_Y,
                                     BOARD_X + BOARD_WIDTH, BOARD_Y + BOARD_HEIGHT,
                                     fill="#000000", outline="", stipple="gray50")
        # Centered card
        cx = BOARD_X + BOARD_WIDTH / 2
        cy = BOARD_Y + BOARD_HEIGHT / 2
        cw, ch = 280, 170
        self.round_rect(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2,
                        16, fill=OVERLAY_BG, outline=ACCENT, width=2)
        self.canvas.create_text(cx, cy - 48, text="GAME OVER",
                                fill=FOOD, font=("Arial", 30, "bold"))
        self.canvas.create_text(cx, cy - 8, text=f"Score   {self.score}",
                                fill=TEXT, font=("Arial", 18, "bold"))
        # Restart hint with a subtle color pulse
        pulse = 0.5 + 0.5 * math.sin(self.frame * 0.18)
        hint_color = lerp_color(TEXT_MUTED, ACCENT, pulse)
        self.canvas.create_text(cx, cy + 36, text="PRESS R TO RESTART",
                                fill=hint_color, font=("Arial", 13, "bold"))

    def draw(self):
        """Redraw the entire UI on the canvas."""
        self.canvas.delete("all")             # clear the previous frame
        self.frame += 1
        self.draw_background()
        self.draw_board()
        self.draw_food()
        self.draw_snake()
        self.draw_hud()
        if self.game_over:
            self.draw_overlay()


def main():
    root = tk.Tk()
    SnakeGame(root)        # create and start the game
    root.mainloop()        # run the Tkinter event loop


if __name__ == "__main__":
    main()
