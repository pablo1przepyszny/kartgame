import streamlit as st
import subprocess
import json
import sys
import os
python game.py game_config.json


st.set_page_config(page_title="Hungaroring Kart Launcher", layout="centered")

st.title("🏎️ Hungaroring Kart – Game Launcher")

st.markdown(
    "Configure your race below and launch the game. "
    "The game will open in a separate window on your computer."
)

# -----------------------------
# UI Controls
# -----------------------------

st.header("Game Settings")

col1, col2 = st.columns(2)

with col1:
    width = st.number_input("Screen width", min_value=640, max_value=3840, value=1280)
    laps = st.number_input("Number of laps", min_value=1, max_value=50, value=3)
    difficulty = st.selectbox("AI Difficulty", ["easy", "medium", "hard"])

with col2:
    height = st.number_input("Screen height", min_value=480, max_value=2160, value=720)
    enable_p2 = st.checkbox("Enable Player 2", value=False)

st.header("Kart Colors")

p1_color = st.color_picker("Player 1 Color", "#ff0000")
p2_color = st.color_picker("Player 2 Color", "#0000ff") if enable_p2 else None

# Convert hex → RGB tuple
def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

p1_rgb = hex_to_rgb(p1_color)
p2_rgb = hex_to_rgb(p2_color) if p2_color else None

# -----------------------------
# Launch Button
# -----------------------------

if st.button("🚀 Launch Game"):
    st.success("Launching game window...")

    # Prepare config to pass to game.py
    config = {
        "width": width,
        "height": height,
        "laps": laps,
        "difficulty": difficulty,
        "player1_color": p1_rgb,
        "player2_enabled": enable_p2,
        "player2_color": p2_rgb,
    }

    # Save config to a temporary JSON file
    with open("game_config.json", "w") as f:
        json.dump(config, f)

    # Run game.py with config file
    # (game.py must be modified to read this JSON instead of asking questions)
    subprocess.Popen([sys.executable, "game.py", "game_config.json"])

    st.info("Game started. Check your desktop for the game window.")
