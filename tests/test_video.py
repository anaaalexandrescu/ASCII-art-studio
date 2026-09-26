"""
teste pt video.py - conversia frame urilor video in ASCII

nu testez pe fisiere video reale, ci pe
frame uri construite manual cu numpy, avand culori stiute
se poate calcula rezultatul asteptat de mana pentru comparatie
"""
import numpy as np
from src.video import frame_to_ascii
from src.image import CHAR_SET

def make_solid_frame(height, width, bgr_color):
    """
    construieste un frame BGR uniform
    """
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:, :] = bgr_color
    return frame

def test_frame_to_ascii_output_dimensions():
    # frame patrat 40x40, new_width=10 - latimea liniilor trebuie sa fie 10
    # si inaltimea calculata din acelasi aspect ratio ca in resize()
    frame = make_solid_frame(40, 40, (128, 128, 128))
    text, rgb_matrix = frame_to_ascii(frame, new_width=10)
    lines = text.split("\n")

    expected_height = int(10 * (40 / 40) * 0.6)
    assert len(lines) == expected_height
    assert all(len(line) == 10 for line in lines)
    assert len(rgb_matrix) == expected_height
    assert all(len(row) == 10 for row in rgb_matrix)

def test_frame_to_ascii_solid_color_gives_uniform_output():
    # pe un frame de o singura culoare nu exista margini, deci toate
    # caracterele din text ar trebui sa fie identice
    frame = make_solid_frame(20, 20, (100, 100, 100))
    text, _ = frame_to_ascii(frame, new_width=8)
    chars = set(text.replace("\n", ""))
    assert len(chars) == 1

def test_frame_to_ascii_black_frame_gives_densest_char():
    frame = make_solid_frame(10, 10, (0, 0, 0))
    text, _ = frame_to_ascii(frame, new_width=5)
    assert text.replace("\n", "")[0] == CHAR_SET[0]

def test_frame_to_ascii_white_frame_gives_sparsest_char():
    frame = make_solid_frame(10, 10, (255, 255, 255))
    text, _ = frame_to_ascii(frame, new_width=5)
    assert text.replace("\n", "")[0] == CHAR_SET[-1]

def test_frame_to_ascii_rgb_matrix_preserves_color():
    # frame e BGR deci (10, 20, 200)
    # trebuie sa ajunga (200, 20, 10) in RGB in rgb_matrix
    frame = make_solid_frame(10, 10, (10, 20, 200))
    _, rgb_matrix = frame_to_ascii(frame, new_width=5)
    assert rgb_matrix[0][0] == (200, 20, 10)

def test_frame_to_ascii_detects_edge_between_halves():
    # jumatate neagra, jumatate alba - trebuie sa existe macar un caracter
    # marcat ca margine (cel mai dens din CHAR_SET, cf. combine())
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    frame[:, :5] = (0, 0, 0)
    frame[:, 5:] = (255, 255, 255)
    text, _ = frame_to_ascii(frame, new_width=10)
    assert CHAR_SET[0] in text.replace("\n", "")

def test_frame_to_ascii_invert_changes_output():
    # frame uniform - gray_contrast nu modifica nimic (guard div by zero)
    # deci orice diferenta intre variante vine strict din invert()
    frame = make_solid_frame(10, 10, (90, 90, 90))
    text_normal, _ = frame_to_ascii(frame, new_width=4, do_invert=False)
    text_inverted, _ = frame_to_ascii(frame, new_width=4, do_invert=True)
    assert text_normal != text_inverted

def test_frame_to_ascii_new_height_never_zero():
    # pt un frame foarte lat si scund, new_height calculat ar putea
    # rotunji la 0 - functia are un guard explicit pt cazul asta
    frame = make_solid_frame(2, 200, (128, 128, 128))
    text, rgb_matrix = frame_to_ascii(frame, new_width=20)
    lines = text.split("\n")
    assert len(lines) >= 1
    assert len(rgb_matrix) >= 1