"""A polished Snake game built with Tkinter.

Run with:  python snake_game.py
Controls:  Arrow keys or WASD to move, Escape to pause.
"""

import json
import math
import os
import random
import sys
import tkinter as tk
from tkinter import messagebox


def resource_path(relative):
    """Resolve a file path that works both normally and when frozen by PyInstaller."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


GRID_WIDTH = 30
GRID_HEIGHT = 20
CELL_SIZE = 20
BOARD_WIDTH = GRID_WIDTH * CELL_SIZE
BOARD_HEIGHT = GRID_HEIGHT * CELL_SIZE
TICK_MS = 100
WINDOW_WIDTH = 640
WINDOW_HEIGHT = 520
BOARD_X = 20
BOARD_Y = 100

BG_TOP = "#101A14"
BG_BOTTOM = "#0A110D"
BOARD_BG = "#142019"
BOARD_GRID = "#1C2A22"
BOARD_BORDER = "#2E4334"
SNAKE_BODY = "#3DDC84"
SNAKE_HEAD = "#7BED9F"
SNAKE_SHADOW = "#1E6B43"
SNAKE_HIGHLIGHT = "#C6F8DE"
FOOD = "#FF6B6B"
FOOD_HIGHLIGHT = "#FFD0D0"
TEXT = "#E8F0EA"
TEXT_MUTED = "#7A8C80"
ACCENT = "#A3E635"
CARD_BG = "#1A2922"
CARD_BORDER = "#2E4334"
OVERLAY_BG = "#1B2A22"

LEVEL_TITLES = (
    "Beginner", "Fast Food", "Speed Challenge", "Snake Master", "Expert",
    "Rapid Runner", "Neon Serpent", "Quick Reflexes", "Turbo Trail",
    "Elite Eater", "Velocity Viper", "Lightning Coil", "Hyper Snake",
    "Primal Speed", "Apex Serpent", "Blitz Master", "Supersonic",
    "Ultimate Coil", "Legendary Snake", "Grandmaster",
)
MAX_LEVEL = len(LEVEL_TITLES)
LEVEL_TARGET = 10
MIN_TICK_MS = 45
LEVEL_SPEED_STEP_MS = 3
SAVE_VERSION = 1


def lerp_color(c1, c2, t):
    """Blend linearly between two hex colors by t (0..1)."""
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02X}{g:02X}{b:02X}"


WALL_SEGMENTS = (
    ((4, 5), (9, 5)),
    ((20, 14), (25, 14)),
    ((5, 11), (5, 14)),
    ((24, 5), (24, 8)),
    ((11, 3), (14, 3)),
    ((15, 16), (18, 16)),
    ((12, 12), (12, 15)),
    ((18, 4), (18, 7)),
    ((3, 16), (7, 16)),
    ((22, 3), (26, 3)),
    ((9, 7), (9, 10)),
    ((20, 10), (20, 13)),
)


def level_walls(level):
    """Return the obstacle cells for a level; later levels add more barriers."""
    segment_count = min(len(WALL_SEGMENTS),
                        (level * len(WALL_SEGMENTS) + MAX_LEVEL - 1) // MAX_LEVEL)
    walls = set()
    for (x1, y1), (x2, y2) in WALL_SEGMENTS[:segment_count]:
        step_x = 1 if x2 >= x1 else -1
        step_y = 1 if y2 >= y1 else -1
        x, y = x1, y1
        while True:
            walls.add((x, y))
            if (x, y) == (x2, y2):
                break
            x += step_x if x != x2 else 0
            y += step_y if y != y2 else 0
    return walls


def random_food(snake, walls=()):
    """Return a random cell that is not occupied by the snake."""
    available = [
        (x, y)
        for x in range(GRID_WIDTH)
        for y in range(GRID_HEIGHT)
        if (x, y) not in snake and (x, y) not in walls
    ]
    if not available:
        raise ValueError("No free cells remain for food.")
    return random.choice(available)


def reset_game(level=1):
    """Reset the snake, direction, and food to their starting state."""
    start = (GRID_WIDTH // 2, GRID_HEIGHT // 2)
    snake = [start, (start[0] - 1, start[1]), (start[0] - 2, start[1])]
    direction = (1, 0)
    walls = level_walls(level)
    return snake, direction, random_food(snake, walls)


def level_speed(level):
    """Return the movement interval for a level, in milliseconds."""
    return max(MIN_TICK_MS, TICK_MS - (level - 1) * LEVEL_SPEED_STEP_MS)


def save_file_path():
    """Use a writable per-user location in frozen builds, beside source otherwise."""
    if not getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "save_data.json")
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        folder = os.path.join(base, "SnakeGame")
    elif sys.platform == "darwin":
        folder = os.path.join(os.path.expanduser("~"), "Library", "Application Support",
                              "SnakeGame")
    else:
        folder = os.path.join(os.path.expanduser("~"), ".local", "share", "SnakeGame")
    return os.path.join(folder, "save_data.json")


class SaveManager:
    """Validate, load, and atomically write the local game progress."""

    def __init__(self, path=None):
        self.path = path or save_file_path()
        self.last_error = None

    def load(self):
        self.last_error = None
        try:
            with open(self.path, "r", encoding="utf-8") as save_file:
                data = json.load(save_file)
        except FileNotFoundError:
            return None
        except (OSError, json.JSONDecodeError) as error:
            self.last_error = f"Could not load save data: {error}"
            return None
        if not self._is_valid(data):
            self.last_error = "The save file is invalid or from an unsupported version."
            return None
        return data

    @staticmethod
    def _is_valid(data):
        if not isinstance(data, dict) or data.get("version") != SAVE_VERSION:
            return False
        integer_fields = ("current_level", "unlocked_level", "score", "level_score")
        if any(type(data.get(key)) is not int for key in integer_fields):
            return False
        level = data["current_level"]
        unlocked = data["unlocked_level"]
        if not (1 <= level <= unlocked <= MAX_LEVEL):
            return False
        if data["score"] < 0 or not (0 <= data["level_score"] <= LEVEL_TARGET):
            return False
        snake = data.get("snake")
        if (not isinstance(snake, list) or len(snake) < 2 or
                any(not isinstance(cell, list) or len(cell) != 2 or
                    any(type(coord) is not int for coord in cell) or
                    not (0 <= cell[0] < GRID_WIDTH and 0 <= cell[1] < GRID_HEIGHT)
                    for cell in snake)):
            return False
        if len({tuple(cell) for cell in snake}) != len(snake):
            return False
        direction = data.get("direction")
        if direction not in ([1, 0], [-1, 0], [0, 1], [0, -1]):
            return False
        food = data.get("food")
        if (not isinstance(food, list) or len(food) != 2 or
                any(type(coord) is not int for coord in food) or
                not (0 <= food[0] < GRID_WIDTH and 0 <= food[1] < GRID_HEIGHT) or
                food in snake):
            return False
        if type(data.get("level_complete")) is not bool:
            return False
        return not data["level_complete"] or data["level_score"] == LEVEL_TARGET

    def save(self, data):
        folder = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(folder, exist_ok=True)
        temporary_path = self.path + ".tmp"
        try:
            with open(temporary_path, "w", encoding="utf-8") as save_file:
                json.dump(data, save_file, indent=2)
                save_file.flush()
                os.fsync(save_file.fileno())
            os.replace(temporary_path, self.path)
        except OSError:
            try:
                if os.path.exists(temporary_path):
                    os.remove(temporary_path)
            except OSError:
                pass
            raise
        self.last_error = None


class SnakeGame:
    """Main game class: renders screens, handles input, and runs the game loop."""

    def __init__(self, root):
        self.root = root
        self.root.title("Snake Game")
        self.root.resizable(False, False)
        self.canvas = tk.Canvas(root, width=WINDOW_WIDTH, height=WINDOW_HEIGHT,
                                bg=BG_BOTTOM, highlightthickness=0)
        self.canvas.pack()
        self.root.update_idletasks()
        sx = (self.root.winfo_screenwidth() - WINDOW_WIDTH) // 2
        sy = (self.root.winfo_screenheight() - WINDOW_HEIGHT) // 2
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{sx}+{sy}")

        try:
            self.icon_image = tk.PhotoImage(file=resource_path(os.path.join("assets", "icon.png")))
            self.root.iconphoto(False, self.icon_image)
        except (tk.TclError, OSError):
            self.icon_image = None

        self.save_manager = SaveManager()
        self.save_data = self.save_manager.load()
        self.save_error = self.save_manager.last_error
        self.has_active_progress = self.save_data is not None
        self.root.bind("<KeyPress>", self.on_key)
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Motion>", self.on_motion)
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)

        self.score = 0
        self.current_level = 1
        self.unlocked_level = 1
        self.walls = level_walls(self.current_level)
        self.snake, self.direction, self.food = reset_game(self.current_level)
        self.level_score = 0
        self.level_complete = False
        self.screen = "menu"
        self.frame = 0
        self.hovered_button = None
        self.buttons = []
        self.draw()
        self.root.after(TICK_MS, self.tick)

    def new_run(self, level=1, preserve_score=False):
        if not preserve_score:
            self.score = 0
        self.current_level = level
        self.unlocked_level = max(self.unlocked_level, level)
        self.walls = level_walls(level)
        self.snake, self.direction, self.food = reset_game(level)
        self.level_score = 0
        self.level_complete = False
        self.screen = "playing"
        self.has_active_progress = True
        self.save_progress()
        self.draw()

    def progress_data(self):
        return {
            "version": SAVE_VERSION,
            "current_level": self.current_level,
            "unlocked_level": self.unlocked_level,
            "score": self.score,
            "level_score": self.level_score,
            "snake": [list(cell) for cell in self.snake],
            "direction": list(self.direction),
            "food": list(self.food),
            "level_complete": self.level_complete,
        }

    def save_progress(self):
        if self.screen == "game_over" or not self.has_active_progress:
            return False
        try:
            self.save_manager.save(self.progress_data())
        except OSError as error:
            self.save_error = f"Could not save progress: {error}"
            return False
        self.save_error = None
        self.save_data = self.progress_data()
        return True

    def continue_game(self):
        data = self.save_manager.load()
        if data is None:
            self.save_data = None
            self.save_error = self.save_manager.last_error
            self.screen = "menu"
            self.draw()
            return
        self.save_data = data
        self.has_active_progress = True
        self.current_level = data["current_level"]
        self.unlocked_level = data["unlocked_level"]
        self.score = data["score"]
        self.level_score = data["level_score"]
        self.walls = level_walls(self.current_level)
        self.snake = [tuple(cell) for cell in data["snake"]]
        self.direction = tuple(data["direction"])
        self.food = tuple(data["food"])
        if self.food in self.walls:
            self.food = random_food(self.snake, self.walls)
        self.level_complete = data["level_complete"]
        self.screen = "level_complete" if self.level_complete else "playing"
        self.save_error = None
        self.draw()

    def start_new_game(self):
        if self.save_data is not None:
            confirmed = messagebox.askyesno(
                "Start a new game?",
                "Starting a new game will replace your saved progress. Continue?",
                parent=self.root,
            )
            if not confirmed:
                return
        self.unlocked_level = 1
        self.score = 0
        self.new_run(level=1)

    def start_selected_level(self, level):
        if not (1 <= level <= self.unlocked_level):
            return
        self.new_run(level=level, preserve_score=True)

    def tick(self):
        if self.screen == "playing":
            self.move_snake()
        self.draw()
        delay = level_speed(self.current_level) if self.screen == "playing" else TICK_MS
        self.root.after(delay, self.tick)

    def move_snake(self):
        head_x, head_y = self.snake[0]
        new_head = (head_x + self.direction[0], head_y + self.direction[1])
        new_head = (new_head[0] % GRID_WIDTH, new_head[1] % GRID_HEIGHT)

        if new_head in self.snake or new_head in self.walls:
            self.screen = "game_over"
            return

        self.snake.insert(0, new_head)
        if new_head == self.food:
            self.score += 1
            self.level_score += 1
            self.food = random_food(self.snake, self.walls)
            if self.level_score >= LEVEL_TARGET:
                self.level_complete = True
                if self.current_level < MAX_LEVEL:
                    self.unlocked_level = max(self.unlocked_level, self.current_level + 1)
                self.screen = "level_complete"
            self.save_progress()
        else:
            self.snake.pop()

    def on_key(self, event):
        key = event.keysym
        if key == "Escape":
            if self.screen == "playing":
                self.screen = "paused"
                self.save_progress()
            elif self.screen == "paused":
                self.screen = "playing"
            self.draw()
            return

        if self.screen == "game_over" and key.lower() == "r":
            self.new_run(level=self.current_level, preserve_score=True)
            return
        if self.screen != "playing":
            return

        if key in ("Up", "w", "W") and self.direction != (0, 1):
            self.direction = (0, -1)
        elif key in ("Down", "s", "S") and self.direction != (0, -1):
            self.direction = (0, 1)
        elif key in ("Left", "a", "A") and self.direction != (1, 0):
            self.direction = (-1, 0)
        elif key in ("Right", "d", "D") and self.direction != (-1, 0):
            self.direction = (1, 0)

    def on_click(self, event):
        for button in reversed(self.buttons):
            x1, y1, x2, y2 = button["bounds"]
            if x1 <= event.x <= x2 and y1 <= event.y <= y2 and not button["disabled"]:
                button["action"]()
                return

    def on_motion(self, event):
        hovered = None
        for button in self.buttons:
            x1, y1, x2, y2 = button["bounds"]
            if x1 <= event.x <= x2 and y1 <= event.y <= y2 and not button["disabled"]:
                hovered = button["id"]
                break
        if hovered != self.hovered_button:
            self.hovered_button = hovered
            self.draw()

    def on_exit(self):
        self.save_progress()
        self.root.destroy()

    def show_menu(self):
        self.screen = "menu"
        self.draw()

    def quit_game(self):
        self.on_exit()

    # ---- Drawing helpers ----------------------------------------------------
    def round_rect(self, x1, y1, x2, y2, r, **kwargs):
        r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
        points = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        ]
        return self.canvas.create_polygon(points, smooth=True, splinesteps=18, **kwargs)

    def draw_background(self):
        band = 6
        for y in range(0, WINDOW_HEIGHT, band):
            color = lerp_color(BG_TOP, BG_BOTTOM, y / WINDOW_HEIGHT)
            self.canvas.create_rectangle(0, y, WINDOW_WIDTH, y + band,
                                         fill=color, outline="")

    def draw_button(self, label, center_x, center_y, width, height, action,
                    button_id, disabled=False, small=False):
        bounds = (center_x - width / 2, center_y - height / 2,
                  center_x + width / 2, center_y + height / 2)
        hovered = self.hovered_button == button_id and not disabled
        fill = "#263A2D" if hovered else CARD_BG
        outline = ACCENT if hovered else CARD_BORDER
        text_color = TEXT_MUTED if disabled else (ACCENT if hovered else TEXT)
        self.round_rect(*bounds, 10, fill=fill, outline=outline, width=2 if hovered else 1)
        self.canvas.create_text(center_x, center_y, text=label, fill=text_color,
                                font=("Arial", 11 if small else 13, "bold"))
        self.buttons.append({"id": button_id, "bounds": bounds, "action": action,
                             "disabled": disabled})

    def draw_title(self, subtitle=None):
        self.canvas.create_text(WINDOW_WIDTH / 2, 58, text="SNAKE",
                                fill=ACCENT, font=("Arial", 34, "bold"))
        self.canvas.create_text(WINDOW_WIDTH / 2, 88, text=subtitle or "ARCADE",
                                fill=TEXT_MUTED, font=("Arial", 11, "bold"))

    def draw_menu(self):
        self.draw_title("ARCADE")
        self.round_rect(170, 118, 470, 490, 18, fill=CARD_BG, outline=CARD_BORDER)
        self.draw_button("NEW GAME", 320, 190, 210, 48, self.start_new_game, "new")
        self.draw_button("CONTINUE", 320, 250, 210, 48, self.continue_game, "continue",
                         disabled=self.save_data is None)
        self.draw_button("LEVELS", 320, 310, 210, 48,
                         lambda: self.set_screen("levels"), "levels")
        self.draw_button("QUIT", 320, 370, 210, 48, self.quit_game, "quit")
        if self.save_data:
            status = (f"Saved: Level {self.save_data['current_level']}  ·  "
                      f"Score {self.save_data['score']}")
            self.canvas.create_text(320, 435, text=status, fill=TEXT_MUTED,
                                    font=("Arial", 10))
        self.draw_save_error()

    def set_screen(self, screen):
        self.screen = screen
        self.draw()

    def draw_levels(self):
        self.draw_title("SELECT A LEVEL")
        self.canvas.create_text(320, 119,
                                text=f"Current: Level {self.current_level}    "
                                     f"Highest unlocked: Level {self.unlocked_level}",
                                fill=TEXT, font=("Arial", 12, "bold"))
        columns = 5
        button_width, button_height = 102, 48
        gap_x, gap_y = 10, 10
        total_width = columns * button_width + (columns - 1) * gap_x
        left = (WINDOW_WIDTH - total_width) / 2
        top = 158
        for level in range(1, MAX_LEVEL + 1):
            index = level - 1
            row, column = divmod(index, columns)
            cx = left + column * (button_width + gap_x) + button_width / 2
            cy = top + row * (button_height + gap_y) + button_height / 2
            unlocked = level <= self.unlocked_level
            label = f"{level:02d}  {LEVEL_TITLES[index]}" if unlocked else f"{level:02d}  LOCKED"
            self.draw_button(
                label, cx, cy, button_width, button_height,
                lambda selected=level: self.start_selected_level(selected),
                f"level-{level}", disabled=not unlocked, small=True,
            )
        self.draw_button("BACK", 320, 445, 150, 42, self.show_menu, "levels-back")

    def draw_board(self):
        self.round_rect(BOARD_X, BOARD_Y, BOARD_X + BOARD_WIDTH, BOARD_Y + BOARD_HEIGHT,
                        14, fill=BOARD_BG, outline=BOARD_BORDER, width=2)
        for col in range(1, GRID_WIDTH):
            x = BOARD_X + col * CELL_SIZE
            self.canvas.create_line(x, BOARD_Y, x, BOARD_Y + BOARD_HEIGHT, fill=BOARD_GRID)
        for row in range(1, GRID_HEIGHT):
            y = BOARD_Y + row * CELL_SIZE
            self.canvas.create_line(BOARD_X, y, BOARD_X + BOARD_WIDTH, y, fill=BOARD_GRID)

    def draw_walls(self):
        """Draw level obstacles as solid tiles inside the wraparound board."""
        for wx, wy in self.walls:
            x1 = BOARD_X + wx * CELL_SIZE
            y1 = BOARD_Y + wy * CELL_SIZE
            x2, y2 = x1 + CELL_SIZE, y1 + CELL_SIZE
            self.round_rect(x1 + 1, y1 + 1, x2 - 1, y2 - 1, 4,
                            fill="#566357", outline="#82907E", width=1)
            self.canvas.create_line(x1 + 5, y1 + 5, x2 - 5, y1 + 5,
                                    fill="#A0AC9D", width=1)

    def draw_hud(self):
        self.canvas.create_text(BOARD_X, 42, anchor="w", text="SNAKE",
                                fill=ACCENT, font=("Arial", 30, "bold"))
        self.canvas.create_text(BOARD_X, 64, anchor="w", text="ARCADE",
                                fill=TEXT_MUTED, font=("Arial", 10, "bold"))
        cx, cy, cw, ch = 392, 12, 228, 74
        self.round_rect(cx, cy, cx + cw, cy + ch, 12,
                        fill=CARD_BG, outline=CARD_BORDER)
        self.canvas.create_text(cx + 13, cy + 17, anchor="w",
                                text=f"LEVEL {self.current_level} · "
                                     f"{LEVEL_TITLES[self.current_level - 1].upper()}",
                                fill=ACCENT, font=("Arial", 11, "bold"))
        self.canvas.create_text(cx + 13, cy + 48, anchor="w",
                                text=f"SCORE  {self.score}     "
                                     f"TARGET  {self.level_score}/{LEVEL_TARGET}",
                                fill=TEXT, font=("Arial", 12, "bold"))

    def draw_snake(self):
        for index, (sx, sy) in enumerate(self.snake):
            x1 = BOARD_X + sx * CELL_SIZE
            y1 = BOARD_Y + sy * CELL_SIZE
            x2, y2 = x1 + CELL_SIZE, y1 + CELL_SIZE
            if index == 0:
                self.round_rect(x1 + 1, y1 + 1, x2 - 1, y2 - 1, 7,
                                fill=SNAKE_HEAD, outline=SNAKE_SHADOW)
                self.canvas.create_oval(x1 + 4, y1 + 4, x1 + 9, y1 + 9,
                                        fill=SNAKE_HIGHLIGHT, outline="")
            else:
                self.round_rect(x1 + 2, y1 + 2, x2 - 2, y2 - 2, 6,
                                fill=SNAKE_BODY, outline=SNAKE_SHADOW)

    def draw_food(self):
        fx, fy = self.food
        cx = BOARD_X + fx * CELL_SIZE + CELL_SIZE / 2
        cy = BOARD_Y + fy * CELL_SIZE + CELL_SIZE / 2
        pulse = 1 + 0.10 * math.sin(self.frame * 0.25)
        radius = (CELL_SIZE / 2 - 3) * pulse
        self.canvas.create_oval(cx - radius - 4, cy - radius - 4,
                                cx + radius + 4, cy + radius + 4,
                                fill=FOOD, outline="", stipple="gray25")
        self.canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius,
                                fill=FOOD, outline="")
        self.canvas.create_oval(cx - radius * 0.45, cy - radius * 0.45,
                                cx - radius * 0.1, cy - radius * 0.1,
                                fill=FOOD_HIGHLIGHT, outline="")

    def draw_game_screen(self):
        self.draw_board()
        self.draw_walls()
        self.draw_food()
        self.draw_snake()
        self.draw_hud()
        self.canvas.create_text(620, 92, anchor="e", text="ESC  PAUSE",
                                fill=TEXT_MUTED, font=("Arial", 9, "bold"))
        if self.screen == "paused":
            self.draw_overlay("PAUSED", [
                ("RESUME", lambda: self.set_screen("playing")),
                ("NEW GAME", self.start_new_game),
                ("MAIN MENU", self.show_menu),
                ("QUIT", self.quit_game),
            ], "pause")
        elif self.screen == "level_complete":
            is_final = self.current_level == MAX_LEVEL
            title = "ALL LEVELS COMPLETE" if is_final else "LEVEL COMPLETED"
            action = self.show_menu if is_final else self.advance_level
            label = "MAIN MENU" if is_final else "NEXT LEVEL"
            self.draw_overlay(title, [(label, action)], "completed",
                              detail=f"Level {self.current_level}  ·  Score {self.score}")
        elif self.screen == "game_over":
            self.draw_overlay("GAME OVER", [
                ("RETRY", lambda: self.new_run(self.current_level, preserve_score=True)),
                ("NEW GAME", self.start_new_game),
                ("MAIN MENU", self.show_menu),
                ("CONTINUE", self.continue_game),
            ], "game-over",
                detail=f"Final score  {self.score}    ·    Level {self.current_level}")

    def draw_overlay(self, title, actions, prefix, detail=None):
        self.canvas.create_rectangle(BOARD_X, BOARD_Y, BOARD_X + BOARD_WIDTH,
                                     BOARD_Y + BOARD_HEIGHT, fill="#000000",
                                     outline="", stipple="gray50")
        cx, cy = BOARD_X + BOARD_WIDTH / 2, BOARD_Y + BOARD_HEIGHT / 2
        card_height = 316 if len(actions) == 4 else 206
        self.round_rect(cx - 190, cy - card_height / 2, cx + 190, cy + card_height / 2,
                        16, fill=OVERLAY_BG, outline=ACCENT, width=2)
        self.canvas.create_text(cx, cy - card_height / 2 + 35, text=title,
                                fill=FOOD if prefix == "game-over" else ACCENT,
                                font=("Arial", 22 if len(title) > 18 else 26, "bold"))
        if detail:
            self.canvas.create_text(cx, cy - card_height / 2 + 67, text=detail,
                                    fill=TEXT, font=("Arial", 11, "bold"))
        first_y = cy - (10 if detail else 3)
        for index, (label, action) in enumerate(actions):
            self.draw_button(label, cx, first_y + index * 47, 190, 38, action,
                             f"{prefix}-{index}")

    def advance_level(self):
        if self.current_level >= MAX_LEVEL:
            self.show_menu()
            return
        self.current_level += 1
        self.level_score = 0
        self.level_complete = False
        self.walls = level_walls(self.current_level)
        self.snake, self.direction, self.food = reset_game(self.current_level)
        self.screen = "playing"
        self.save_progress()
        self.draw()

    def draw_save_error(self):
        if self.save_error:
            self.canvas.create_text(WINDOW_WIDTH / 2, WINDOW_HEIGHT - 12,
                                    text=self.save_error[:90], fill=FOOD,
                                    font=("Arial", 9))

    def draw(self):
        self.canvas.delete("all")
        self.frame += 1
        self.buttons = []
        self.draw_background()
        if self.screen == "menu":
            self.draw_menu()
        elif self.screen == "levels":
            self.draw_levels()
        else:
            self.draw_game_screen()
        if self.screen != "menu":
            self.draw_save_error()


def main():
    root = tk.Tk()
    SnakeGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()
