"""
tests for image.py - the image-to-ASCII conversion functions

general idea: i don't test on real photos from assets/, but on matrices
built manually, with known values, so i can compute the expected result
by hand and compare
"""
import pytest

from src.image import (
    grayscale,
    gray_contrast,
    sobel,
    combine,
    resize,
    resize_rgb,
    map_set,
    convert,
    invert,
    CHAR_SET,
)

# grayscale

class FakePixels:
    """
    so there's no need for a real
    image just to test the grayscale formula.
    indexed the same way as PIL: pixels[x, y].
    """
    def __init__(self, data):
        self._data = data

    def __getitem__(self, coords):
        x, y = coords
        return self._data[y][x]

def test_grayscale_pure_white():
    pixels = FakePixels([[(255, 255, 255)]])
    result = grayscale(pixels, height=1, width=1)
    assert result[0][0] == pytest.approx(255.0)

def test_grayscale_pure_black():
    pixels = FakePixels([[(0, 0, 0)]])
    result = grayscale(pixels, height=1, width=1)
    assert result[0][0] == pytest.approx(0.0)

def test_grayscale_formula():
    # check that the formula 0.299R + 0.587G + 0.114B is applied correctly
    pixels = FakePixels([[(100, 150, 200)]])
    result = grayscale(pixels, height=1, width=1)
    expected = 0.299 * 100 + 0.587 * 150 + 0.114 * 200
    assert result[0][0] == pytest.approx(expected)

def test_grayscale_shape():
    # 2x3 - check that the output matrix dimensions are correct
    pixels = FakePixels([
        [(0, 0, 0), (255, 255, 255), (128, 128, 128)],
        [(10, 20, 30), (40, 50, 60), (70, 80, 90)],
    ])
    result = grayscale(pixels, height=2, width=3)
    assert len(result) == 2
    assert all(len(row) == 3 for row in result)

def test_grayscale_multiple_pixels_independent():
    # check that each pixel on the same row is computed separately, values
    # aren't mixed between them
    pixels = FakePixels([
        [(255, 0, 0), (0, 255, 0)],
    ])
    result = grayscale(pixels, height=1, width=2)
    expected_red = 0.299 * 255
    expected_green = 0.587 * 255
    assert result[0][0] == pytest.approx(expected_red)
    assert result[0][1] == pytest.approx(expected_green)

# contrast

def test_contrast_stretch_full_range():
    mat = [[50, 100], [150, 200]]
    result = gray_contrast(mat)
    assert result[0][0] == pytest.approx(0.0)
    assert result[1][1] == pytest.approx(255.0)

def test_contrast_uniform_matrix_unchanged():
    # if all pixels are identical, stretching the contrast makes no sense
    # it would cause a div by zero, must return the matrix unchanged
    mat = [[100, 100], [100, 100]]
    result = gray_contrast(mat)
    assert result == mat

# sobel

def test_sobel_uniform_image_no_edges():
    # on a completely uniform image there are no edges, so the magnitude
    # should be ~0 everywhere
    mat = [[100, 100, 100],
           [100, 100, 100],
           [100, 100, 100]]
    result = sobel(mat, height=3, width=3)
    for row in result:
        for val in row:
            assert val == pytest.approx(0.0)

def test_sobel_detects_vertical_edge():
    # half black, half white - clear edge on the vertical
    mat = [[0, 0, 255, 255],
           [0, 0, 255, 255],
           [0, 0, 255, 255]]
    result = sobel(mat, height=3, width=4)
    middle_col_vals = [row[1] for row in result] + [row[2] for row in result]
    assert max(middle_col_vals) > 100
    assert result[1][0] < 50

def test_sobel_detects_horizontal_edge():
    # same test as the vertical one, but on the horizontal, to make sure
    # sobel isn't biased toward a single direction
    mat = [[0, 0, 0],
           [0, 0, 0],
           [255, 255, 255]]
    result = sobel(mat, height=3, width=3)
    # the top row is far from the edge, and is clamped, so it should be 0
    assert result[0][0] == pytest.approx(0.0)
    # somewhere near the edge we should have a large magnitude
    assert max(max(row) for row in result) > 100

# combine

def test_combine_forces_black_above_threshold():
    mat = [[100, 100]]
    edges = [[50, 200]]  # the second pixel exceeds the threshold
    result = combine(mat, edges, height=1, width=2, threshold=100)
    assert result[0][0] == 100 # below threshold, stays the original
    assert result[0][1] == 0 # above threshold, becomes black

def test_combine_equal_to_threshold_not_forced_black():
    # combine uses strict ">" not ">=", so a value equal to the
    # threshold must not be considered an edge
    mat = [[77]]
    edges = [[100]]
    result = combine(mat, edges, height=1, width=1, threshold=100)
    assert result[0][0] == 77

# resize

def test_resize_output_width():
    mat = [[i for i in range(10)] for _ in range(10)]
    result, new_w, new_h = resize(mat, width=10, height=10, new_width=5, char=1.0)
    assert new_w == 5
    assert all(len(row) == 5 for row in result)

def test_resize_aspect_ratio_correction():
    # square image, char=0.5 the resulting height must be halved
    mat = [[0] * 10 for _ in range(10)]
    result, new_w, new_h = resize(mat, width=10, height=10, new_width=10, char=0.5)
    assert new_h == 5

def test_resize_rgb_shape_and_sampling():
    # same nearest-neighbor logic as resize(), but on RGB tuples
    pixels = FakePixels([
        [(10, 10, 10), (20, 20, 20), (30, 30, 30), (40, 40, 40)],
        [(50, 50, 50), (60, 60, 60), (70, 70, 70), (80, 80, 80)],
    ])
    result, new_w, new_h = resize_rgb(pixels, width=4, height=2, new_width=2, char=1.0)
    assert new_w == 2
    assert len(result) == new_h
    assert all(len(row) == 2 for row in result)
    # the first sampled pixel must be the original top-left corner
    assert result[0][0] == (10, 10, 10)

# map

def test_map_black_gives_last_char():
    # gray = 0 first character in the set
    assert map_set(0) == CHAR_SET[0]

def test_map_white_gives_first_char():
    # gray = 255 last character in the set
    assert map_set(255) == CHAR_SET[-1]

def test_map_set_mid_value():
    # a value from the middle of the range must map to the corresponding
    # character in the middle of the set, using the same formula as the implementation
    idx_expected = int((128 / 255) * (len(CHAR_SET) - 1))
    assert map_set(128) == CHAR_SET[idx_expected]

def test_convert_produces_correct_line_count():
    mat = [[0, 255], [128, 64]]
    result = convert(mat)
    lines = result.split("\n")
    assert len(lines) == 2
    assert all(len(line) == 2 for line in lines)

def test_convert_with_custom_charset():
    # check that the set parameter is actually used, not just the default CHAR_SET
    mat = [[0, 255]]
    result = convert(mat, set=".#")
    assert result == ".#"

def test_invert_flips_values():
    mat = [[0, 100], [255, 50]]
    result = invert(mat)
    assert result == [[255, 155], [0, 205]]

def test_invert_double_invert_returns_original():
    mat = [[10, 200], [50, 128]]
    assert invert(invert(mat)) == mat