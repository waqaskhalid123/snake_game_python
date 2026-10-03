# Snake Game

A desktop Snake game written in Python with Tkinter. The play field is a 30 by 20 grid, the snake starts in the center moving right, and the score goes up by one each time it eats.

The game lives in the `p3` folder.

## Run from source

Python 3 is enough. Tkinter ships with the standard install on macOS and Windows.

```bash
cd p3
python3 snake_game.py
```

## Controls

| Key | Action |
| --- | --- |
| Arrow keys or WASD | Move |
| R | Restart after game over |

The snake cannot reverse into itself. Hitting a wall or its own body ends the game.

## macOS app

A PyInstaller build for Intel macOS is already in the folder:

- `p3/dist/SnakeGame.app` — double-click to play
- `p3/SnakeGame-macOS-Intel.zip` — the same app, zipped

To rebuild it:

```bash
cd p3
pip install pyinstaller
pyinstaller SnakeGame.spec
```

The new app is written to `p3/dist/SnakeGame.app`.
