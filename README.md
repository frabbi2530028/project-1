# Space Shooter: Neon Drift

A fast-paced 2D arcade space shooter built with Python and the `arcade` library. You control a neon ship, survive enemy waves, collect power-ups, and fight bosses as the game gets harder over time.

## Overview

This project is a top-down shooter game with:

- smooth player movement
- mouse-based shooting
- multiple enemy types
- boss fights
- collectible and stored power-ups
- score and combo system
- particle effects and HUD
- fullscreen toggle

## Features

- **Player movement:** move freely with `W`, `A`, `S`, `D`
- **Combat:** aim with the mouse and shoot with left click
- **Enemy types:**
  - basic enemy that chases the player
  - shooting enemy that attacks from range
  - boss enemy with special bullet spread attacks
- **Power-ups:**
  - health
  - shield
  - autofire
  - speed
  - triple shot
- **Inventory system:** stored power-ups can be activated using number keys
- **Difficulty scaling:** enemies become more dangerous as survival time increases
- **Visual effects:** starfield background, glow effects, particles, crosshair, and damage flash

## Requirements

- Python 3.x
- `arcade`
- `Pillow`

Install dependencies with:

```bash
pip install arcade pillow
