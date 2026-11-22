#!/usr/bin/env python3
"""Generate a 50-second 1080p cartoon turtle animation with music and ocean sounds.

Requirements:
  pip install pillow numpy
  ffmpeg installed on PATH

Output:
  turtle_video.mp4
"""

from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

WIDTH = 1920
HEIGHT = 1080
FPS = 30
DURATION = 50
FRAMES = FPS * DURATION
OUTPUT = Path("turtle_video.mp4")


def ellipse(draw: ImageDraw.ImageDraw, box, fill):
    draw.ellipse(box, fill=fill)


def draw_turtle(frame: np.ndarray, t: float) -> np.ndarray:
    """Draw a cheerful, side-view cartoon turtle using a PIL overlay."""
    img = Image.fromarray(frame)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    # Underwater background rays
    for i in range(7):
        x = 120 + i * 310
        d.polygon([(x, 0), (x + 150, 0), (x + 360, 900), (x + 180, 900)],
                  fill=(220, 248, 255, 18))

    # Bubbles
    for i in range(24):
        seed = i * 97
        bx = (seed * 13 % WIDTH)
        phase = (t * (18 + i % 5) + i * 61) % (HEIGHT + 180)
        by = HEIGHT - phase
        r = 4 + (i % 5)
        d.ellipse((bx-r, by-r, bx+r, by+r), outline=(210, 245, 255, 150), width=3)

    # Seaweed along the bottom
    for i in range(9):
        sx = i * 250 - 70
        for j in range(3):
            wx = sx + j * 38
            top = 900 + j * 25
            sway = int(math.sin(t * 1.8 + i + j) * 26)
            d.ellipse((wx+sway-32, top-100, wx+sway+32, top+70), fill=(30, 145, 100, 230))

    # Turtle swims left-right with a gentle bob
    x = int(WIDTH * 0.5 + math.sin(t * 0.38) * 520)
    y = int(535 + math.sin(t * 1.15) * 42)
    direction = 1 if math.cos(t * 0.38) >= 0 else -1

    # Shadow
    d.ellipse((x-260, y+210, x+260, y+260), fill=(5, 75, 105, 75))

    # Shell
    d.ellipse((x-210, y-150, x+210, y+180), fill=(73, 126, 62, 255), outline=(43, 82, 48, 255), width=14)
    d.polygon([(x-150,y-130),(x,y-175),(x+150,y-130),(x+190,y),(x+125,y+145),
               (x-125,y+145),(x-190,y),(x-150,y-130)], fill=(104, 171, 83, 255))
    # Shell plates
    d.line((x,y-155,x,y+145), fill=(44,102,54,255), width=9)
    d.line((x-150,y-90,x+150,y-90), fill=(44,102,54,255), width=9)
    d.line((x-145,y+75,x+145,y+75), fill=(44,102,54,255), width=9)

    # Flippers
    flap = int(math.sin(t * 2.3) * 25)
    d.ellipse((x-180, y-65+flap, x-40, y+130+flap), fill=(77, 166, 121, 255), outline=(39,112,82,255), width=9)
    d.ellipse((x+40, y-65-flap, x+180, y+130-flap), fill=(77, 166, 121, 255), outline=(39,112,82,255), width=9)

    # Head and neck
    head_x = x + direction * 230
    d.ellipse((head_x-95,y-75,head_x+95,y+115), fill=(103,186,139,255), outline=(49,119,88,255), width=9)
    d.ellipse((head_x-55,y-15,head_x-25,y+15), fill=(24,58,48,255))
    d.ellipse((head_x+25,y-15,head_x+55,y+15), fill=(24,58,48,255))

    # Smile
    d.arc((head_x-42,y+18,head_x+42,y+82),0,180,fill=(25,72,58,255),width=7)

    # Head direction makes the face readable if the turtle turns around
    if direction < 0:
        d.ellipse((head_x+25,y-15,head_x+55,y+15), fill=(24,58,48,255))

    # Tiny title card for the first 4 seconds
    if t < 4:
        alpha = min(255, int(t * 180), int((4-t) * 180))
        d.rounded_rectangle((650,115,1270,230),radius=28,fill=(255,255,255,alpha))
        d.text((735,145), "Turtle Adventures", fill=(28,82,96,alpha), font=None)

    img = Image.alpha_composite(img.convert("RGBA"), layer)
    return np.asarray(img.convert("RGB"))


def make_audio(path: Path) -> None:
    """Synthesizes upbeat chords, ocean ambience, and short sound effects."""
    sr = 48000
    n = DURATION * sr
    rng = np.random.default_rng(1234)
    t = np.arange(n, dtype=np.float64) / sr

    # Pink-ish noise for ocean ambience
    white = rng.normal(0, 1, n)
    pink = np.zeros(n)
    b0 = b1 = b2 = b3 = b4 = b5 = b6 = 0.0
    for i in range(n):
        w = white[i]
        b0 = 0.99886*b0 + w*0.0555179
        b1 = 0.99332*b1 + w*0.0750759
        b2 = 0.96900*b2 + w*0.1538520
        b3 = 0.86650*b3 + w*0.3104856
        b4 = 0.55000*b4 + w*0.5329522
        b5 = -0.7616*b5 - w*0.0168980
        pink[i] = b0+b1+b2+b3+b4+b5+b6+w*0.5362
        b6 = w*0.115926
    pink *= 0.018

    # Gentle underwater bed and warm piano-like arpeggio
    bass = np.sin(2*np.pi*55*t) * 0.035
    melody_notes = [261.63,329.63,392.00,523.25,392.00,329.63,293.66,349.23]
    music = np.zeros(n)
    beat = 0.5
    for i in range(int(DURATION/beat)):
        note = melody_notes[i % len(melody_notes)]
        start = i * int(sr*beat)
        length = int(sr*0.42)
        local = np.arange(length)/sr
        env = np.exp(-5*local) * (1-np.exp(-40*local))
        music[start:start+length] += env * (0.16*np.sin(2*np.pi*note*local) + 0.06*np.sin(2*np.pi*note*2*local))

    # Bubble and splash effects
    effects = np.zeros(n)
    for i in range(25):
        start = int(rng.uniform(1,48)*sr)
        length = int(rng.uniform(.08,.22)*sr)
        if start+length > n:
            continue
        freq = rng.uniform(550,1600)
        local = np.arange(length)/sr
        bubble = np.sin(2*np.pi*(freq*local + 350*local*local)) * np.exp(-10*local)
        effects[start:start+length] += bubble * rng.uniform(.025,.07)

    mix = bass + music + pink + effects
    mix *= 0.86 / max(1.0, np.max(np.abs(mix)))
    pcm = np.clip(mix * 32767, -32768, 32767).astype(np.int16)

    import wave
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def main() -> None:
    if shutil.which("ffmpeg") is None:
        raise SystemExit("FFmpeg is required. Install it and ensure 'ffmpeg' is on PATH.")

    audio = Path("turtle_audio.wav")
    make_audio(audio)

    with tempfile.TemporaryDirectory() as td:
        raw_video = Path(td) / "video.mp4"
        temp = Path(td) / "frames"
        temp.mkdir()

        # Create a background once per frame, with a subtle animated ocean gradient.
        for frame_num in range(FRAMES):
            t = frame_num / FPS
            yy = np.linspace(0, 1, HEIGHT)[:, None, None]
            top = np.array([18, 155, 205])
            bottom = np.array([10, 92, 145])
            bg = top*(1-yy) + bottom*yy
            shimmer = (np.sin(np.linspace(0, 28, WIDTH)[None,:] + t*1.4)[:,:,None] * 5).astype(np.float32)
            bg = np.clip(bg + np.broadcast_to(shimmer,(HEIGHT,WIDTH,1)),0,255).astype(np.uint8)
            # Add bottom sand
            bg[850:] = (194, 171, 112)
            image = draw_turtle(bg, t)
            Image.fromarray(image).save(temp / f"{frame_num:05d}.jpg", quality=92)

        cmd = [
            "ffmpeg", "-y", "-framerate", str(FPS), "-i", str(temp / "%05d.jpg"),
            "-i", str(audio), "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
            "-t", str(DURATION), "-movflags", "+faststart", str(OUTPUT)
        ]
        subprocess.run(cmd, check=True)

    audio.unlink(missing_ok=True)
    print(f"Created {OUTPUT.resolve()} ({WIDTH}x{HEIGHT}, {DURATION}s, {FPS} FPS)")


if __name__ == "__main__":
    main()
