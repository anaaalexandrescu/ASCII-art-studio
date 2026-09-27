import cv2
import src.image as image

def frame_to_ascii(frame, new_width=150, do_invert=False):
    """
    converts a video frame numpy array BGR into an ASCII frame

    recreates the same pipeline as image.ascii() adapted for video: uses
    cv2.resize with interpolation instead of manual nearest-neighbor
    (faster), and does not load anything from disk
    the frame already comes in memory from the camera or from a video file

    pixels is transposed from (height, width, 3) to (width, height, 3)
    to respect pixels[x, y] used by image.grayscale()

    args:
        frame: a BGR frame as returned by cv2
        new_width: target width of the ASCII output in characters, default 150
        do_invert: if True, inverts the grayscale values before processing

    returns:
        tuple (text, rgb_matrix) - text is the resulting ASCII string, rgb_matrix
        is a matrix of tuples (r, g, b) aligned to the same grid as the text
    """
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    height, width, _ = rgb_frame.shape
    ratio = height / width
    char_ratio = 0.6

    new_height = int(new_width * ratio * char_ratio)
    if new_height < 1:
        new_height = 1
    rgb_resized = cv2.resize(rgb_frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

    # image.grayscale() uses pixels[x, y]
    # while numpy uses [y, x]
    # transpose the first 2 axes
    pixels = rgb_resized.transpose(1, 0, 2)
    gray = image.grayscale(pixels, new_height, new_width)
    gray = image.gray_contrast(gray)

    if do_invert:
        gray = image.invert(gray)

    edges = image.sobel(gray, new_height, new_width)
    gray = image.combine(gray, edges, new_height, new_width, threshold=400)
    text = image.convert(gray, image.CHAR_SET)

    rgb_matrix = []
    for i in range(new_height):
        row = []
        for j in range(new_width):
            r, g, b = rgb_resized[i, j]
            row.append((int(r), int(g), int(b)))
        rgb_matrix.append(row)
    return text, rgb_matrix