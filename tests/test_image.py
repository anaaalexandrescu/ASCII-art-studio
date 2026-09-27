"""
teste pt image.py - functiile de conversie imagine - ASCII

idee generala: nu testez pe poze reale din assets/, ci pe matrici
construite manual, cu valori stiute, ca sa pot calcula rezultatul asteptat
de mana si sa compar 
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
    sa nu fie nevoie de o imagine
    reala doar ca sa testez formula de grayscale.
    indexat la fel ca PIL: pixels[x, y].
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
    # vf ca formula 0.299R + 0.587G + 0.114B e aplicata corect
    pixels = FakePixels([[(100, 150, 200)]])
    result = grayscale(pixels, height=1, width=1)
    expected = 0.299 * 100 + 0.587 * 150 + 0.114 * 200
    assert result[0][0] == pytest.approx(expected)

def test_grayscale_shape():
    # 2x3 - vf ca dimensiunile matricei de output sunt corecte
    pixels = FakePixels([
        [(0, 0, 0), (255, 255, 255), (128, 128, 128)],
        [(10, 20, 30), (40, 50, 60), (70, 80, 90)],
    ])
    result = grayscale(pixels, height=2, width=3)
    assert len(result) == 2
    assert all(len(row) == 3 for row in result)

def test_grayscale_multiple_pixels_independent():
    # vf ca fiecare pixel de pe acelasi rand e calculat separat, nu se
    # amesteca valorile intre ei
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
    # daca toti pixelii sunt identici, nu are sens sa intinzi contrastul
    # ar da div by zero trebuie sa returneze matricea neschimbata
    mat = [[100, 100], [100, 100]]
    result = gray_contrast(mat)
    assert result == mat

# sobel

def test_sobel_uniform_image_no_edges():
    # pe o imagine complet uniforma nu exista margini, deci magnitudinea
    # trebuie sa fie ~0 peste tot
    mat = [[100, 100, 100],
           [100, 100, 100],
           [100, 100, 100]]
    result = sobel(mat, height=3, width=3)
    for row in result:
        for val in row:
            assert val == pytest.approx(0.0)

def test_sobel_detects_vertical_edge():
    # jumatate neagra, jumatate alba margine clara pe verticala
    mat = [[0, 0, 255, 255],
           [0, 0, 255, 255],
           [0, 0, 255, 255]]
    result = sobel(mat, height=3, width=4)
    middle_col_vals = [row[1] for row in result] + [row[2] for row in result]
    assert max(middle_col_vals) > 100
    assert result[1][0] < 50

def test_sobel_detects_horizontal_edge():
    # acelasi test ca cel vertical, dar pe orizontala, sa fiu sigur
    # ca sobel ul nu e biasat spre o singura directie
    mat = [[0, 0, 0],
           [0, 0, 0],
           [255, 255, 255]]
    result = sobel(mat, height=3, width=3)
    # randul de sus e departe de margine, si e clamped, deci ar trebui sa fie 0
    assert result[0][0] == pytest.approx(0.0)
    # undeva langa margine ar trebui sa avem o magnitudine mare
    assert max(max(row) for row in result) > 100

# combine

def test_combine_forces_black_above_threshold():
    mat = [[100, 100]]
    edges = [[50, 200]]  # al doilea pixel depaseste threshold-ul
    result = combine(mat, edges, height=1, width=2, threshold=100)
    assert result[0][0] == 100 # sub threshold, ramane originala
    assert result[0][1] == 0 # peste threshold, devine negru

def test_combine_equal_to_threshold_not_forced_black():
    # combine foloseste strict ">" nu ">=", deci o valoare egala cu
    # threshold ul nu trebuie considerata margine
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
    # imagine patrata, char=0.5 inaltimea rezultata trebuie injumatatita
    mat = [[0] * 10 for _ in range(10)]
    result, new_w, new_h = resize(mat, width=10, height=10, new_width=10, char=0.5)
    assert new_h == 5

def test_resize_rgb_shape_and_sampling():
    # aceeasi logica de nearest-neighbor ca resize(), dar pe tupluri RGB
    pixels = FakePixels([
        [(10, 10, 10), (20, 20, 20), (30, 30, 30), (40, 40, 40)],
        [(50, 50, 50), (60, 60, 60), (70, 70, 70), (80, 80, 80)],
    ])
    result, new_w, new_h = resize_rgb(pixels, width=4, height=2, new_width=2, char=1.0)
    assert new_w == 2
    assert len(result) == new_h
    assert all(len(row) == 2 for row in result)
    # primul pixel esantionat trebuie sa fie coltul din stanga sus original
    assert result[0][0] == (10, 10, 10)

# map

def test_map_black_gives_last_char():
    # gray = 0 primul caracter din set
    assert map_set(0) == CHAR_SET[0]

def test_map_white_gives_first_char():
    # gray = 255 ultimul caracter din set
    assert map_set(255) == CHAR_SET[-1]

def test_map_set_mid_value():
    # o valoare din mijlocul range ului trebuie sa mapeze la caracterul
    # corespunzator din mijlocul setului, cu aceeasi formula ca in implementare
    idx_expected = int((128 / 255) * (len(CHAR_SET) - 1))
    assert map_set(128) == CHAR_SET[idx_expected]

def test_convert_produces_correct_line_count():
    mat = [[0, 255], [128, 64]]
    result = convert(mat)
    lines = result.split("\n")
    assert len(lines) == 2
    assert all(len(line) == 2 for line in lines)

def test_convert_with_custom_charset():
    # vf ca parametrul set e folosit efectiv, nu doar CHAR_SET-ul default
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