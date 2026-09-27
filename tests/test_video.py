"""
tests for video.py - converting video frames to ASCII

i don't test on real video files, but on
frames built manually with numpy, having known colors
the expected result can be computed by hand for comparison
"""
import numpy as np
from src.video import frame_to_ascii
from src.image import CHAR_SET

def make_solid_frame(height, width, bgr_color):
    """
    builds a uniform BGR frame
    """
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:, :] = bgr_color
    return frame

def test_frame_to_ascii_output_dimensions():
    # square frame 40x40, new_width=10 - the line width must be 10
    # and the height computed from the same aspect ratio as in resize()
    frame = make_solid_frame(40, 40, (128, 128, 128))
    text, rgb_matrix = frame_to_ascii(frame, new_width=10)
    lines = text.split("\n")

    expected_height = int(10 * (40 / 40) * 0.6)
    assert len(lines) == expected_height
    assert all(len(line) == 10 for line in lines)
    assert len(rgb_matrix) == expected_height
    assert all(len(row) == 10 for row in rgb_matrix)

def test_frame_to_ascii_solid_color_gives_uniform_output():
    # on a single-color frame there are no edges, so all
    # characters in the text should be identical
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
    # frame is BGR so (10, 20, 200)
    # must become (200, 20, 10) in RGB in rgb_matrix
    frame = make_solid_frame(10, 10, (10, 20, 200))
    _, rgb_matrix = frame_to_ascii(frame, new_width=5)
    assert rgb_matrix[0][0] == (200, 20, 10)

def test_frame_to_ascii_detects_edge_between_halves():
    # half black, half white - there must be at least one character
    # marked as an edge (the densest one in CHAR_SET, per combine())
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    frame[:, :5] = (0, 0, 0)
    frame[:, 5:] = (255, 255, 255)
    text, _ = frame_to_ascii(frame, new_width=10)
    assert CHAR_SET[0] in text.replace("\n", "")

def test_frame_to_ascii_invert_changes_output():
    # uniform frame - gray_contrast doesn't change anything (div by zero guard)
    # so any difference between the variants comes strictly from invert()
    frame = make_solid_frame(10, 10, (90, 90, 90))
    text_normal, _ = frame_to_ascii(frame, new_width=4, do_invert=False)
    text_inverted, _ = frame_to_ascii(frame, new_width=4, do_invert=True)
    assert text_normal != text_inverted

def test_frame_to_ascii_new_height_never_zero():
    # for a very wide and short frame, the computed new_height could
    # round to 0 - the function has an explicit guard for this case
    frame = make_solid_frame(2, 200, (128, 128, 128))
    text, rgb_matrix = frame_to_ascii(frame, new_width=20)
    lines = text.split("\n")
    assert len(lines) >= 1
    assert len(rgb_matrix) >= 1