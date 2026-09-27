from PIL import Image, ImageFont, ImageDraw

# CHAR_SET = " .:-=+*#%@$B&8W"
CHAR_SET = "W8&B$@%#*+=-:. "

def load(path):
    """
    loads an image from disk and returns the pixel access object plus the dimensions.
    converts to RGB for a consistent 3-channel format for everything
    that follows, regardless of the original mode of the image.

    args:
        path: path to the image file

    returns:
        tuple (pixels, width, height) - pixels is a PixelAccess object
        indexed as pixels[x, y], width/height are the dimensions
    """
    image = Image.open(path)
    image = image.convert("RGB")
    width, height = image.size
    pixels = image.load()
    return pixels, width, height

def grayscale(pixels, height, width):
    """
    converts a matrix of rgb pixels to grayscale using weights.

    i used the standard formula 0.299R + 0.587G + 0.114B: it puts more
    weight on green because the human eye is more sensitive to it. it gives much
    better results than a simple average between the 3 channels.

    args:
        pixels: PixelAccess object
        height: image height
        width: image width

    returns:
        matrix of grayscale float values
    """
    final = []
    for j in range(height):
        row = []
        for i in range(width):
            r, g, b = pixels[i, j]
            gray = 0.299 * r + 0.587 * g + 0.114 * b
            row.append(gray)
        final.append(row)
    return final

def gray_contrast(mat):
    """
    stretches the contrast to cover the whole 0-255 range

    finds min and max in the matrix and linearly rescales each value, so
    that the darkest pixel becomes 0 and the lightest becomes 255. visually
    improves the ASCII output, especially on images that don't already use the whole spectrum

    args:
        mat: matrix with grayscale values

    returns:
        a new list with the stretched-contrast values, or the original matrix
        unchanged if all pixels have the same value (guard for div by zero)
    """
    vals = [val for row in mat for val in row]
    min_val = min(vals)
    max_val = max(vals)

    if max_val == min_val:
        return mat
    
    final = []
    for row in mat:
        new = []
        for val in row:
            stretched = (val - min_val) / (max_val - min_val) * 255
            new.append(stretched)
        final.append(new)
    return final

def sobel(mat, height, width):
    """
    applies the sobel operator for edge detection on a grayscale matrix

    performs convolution with 2 3x3 kernels (gx for horizontal gradient, gy for vertical)
    to estimate the intensity gradient at each pixel. the final
    magnitude is the euclidean norm of gx and gy. at the edges - clamping
    (min/max) instead of zero padding

    args:
        mat: matrix with grayscale values
        height: matrix height
        width: matrix width

    returns:
        matrix with the same shape + the edge magnitude values
    """
    gx_kernel = [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]]
    gy_kernel = [[-1, -2, -1], [0, 0, 0], [1, 2, 1]]

    edges = []
    for i in range(height):
        row = []
        for j in range(width):
            gx, gy = 0, 0
            for m in range(-1, 2):
                for n in range(-1, 2):
                    y = min(max(i + m, 0), height - 1) 
                    x = min(max(j + n, 0), width - 1)
                    pixel = mat[y][x]
                    gx += pixel * gx_kernel[m + 1][n + 1]
                    gy += pixel * gy_kernel[m + 1][n + 1]

            magnitude = (gx ** 2 + gy ** 2) ** 0.5
            row.append(magnitude)
        edges.append(row)
    return edges

def combine(mat, edges, height, width, threshold=100):
    """
    combines the grayscale matrix with the edge map, forcing strong edges to be black

    wherever the edge magnitude exceeds the threshold, the pixel becomes 0
    (pure black) to make the contours stand out. otherwise it keeps the original
    grayscale value

    args:
        mat: matrix with grayscale values
        edges: 2D list with edge magnitudes
        height: matrix height
        width: matrix width
        threshold: minimum magnitude to be considered an edge, default 100

    returns:
        a matrix combining the grayscale with edge info.
    """
    final = []
    for i in range(height):
        row = []
        for j in range(width):
            if edges[i][j] > threshold:
                row.append(0)  
            else:
                row.append(mat[i][j])
        final.append(row)
    return final

def resize(gray_m, width, height, new_width=100, char=0.6):
    """
    shrinks a grayscale matrix to new_width, using nearest-neighbor

    the new height is computed from the original aspect ratio, corrected with
    the char factor to compensate for the fact that a monospace character is taller
    than it is wide

    args:
        gray_m: matrix
        width: original width
        height: original height
        new_width: target width in characters, default 100
        char: correction factor, default 0.6

    returns:
        tuple (final, new_width, new_height)
    """
    ratio = height / width
    new_height = int(new_width * ratio * char)

    final = []
    for i in range(new_height):
        y = int(i * height / new_height)
        row = []
        for j in range(new_width):
            x = int(j * width / new_width)
            row.append(gray_m[y][x])
        final.append(row)
    return final, new_width, new_height

def map_set(gray, set = CHAR_SET):
    """
    maps a single grayscale value to a character from the given set

    scales the grayscale value to an index into the length of the character
    set, so dark/light pixels end up at opposite ends of the
    set, depending on how CHAR_SET is ordered

    args:
        gray: grayscale value in [0, 255].
        set: string of characters ordered dense to sparse

    returns:
        a character representing the given grayscale value
    """
    idx = int((gray / 255) * (len(set) - 1))
    return set[idx]

def convert(mat, set = CHAR_SET):
    """
    converts a grayscale matrix into a multi-line ASCII string

    applies map_set() to each value in the matrix, row by row, and joins
    the resulting characters into lines separated by newline

    args:
        mat: matrix with grayscale values
        set: character set used for mapping

    returns:
        string with the ASCII art
    """
    final = []
    for row in mat:
        line = ""
        for i in row:
            line += map_set(i, set)
        final.append(line)
    return "\n".join(final)

def size(font):
    """
    computes the width and height in pixels of a single monospace character

    renders the character "A" on an image to measure the bounding box

    args:
        font: ImageFont object loaded from PIL

    returns:
        tuple (width, height) in pixels for a single character
    """
    img = Image.new("RGB", (10, 10))
    draw = ImageDraw.Draw(img)
    width = draw.textlength("A", font=font) 
    corners = draw.textbbox((0, 0), "A", font=font)
    height = corners[3] - corners[1]
    return int(width), height

def image(text, font_size=10, bg_color=(255, 255, 255), text_color=(0, 0, 0)):
    """
    renders an ASCII string into a simple PIL image

    each character is drawn individually at a grid position computed from
    the monospace character's dimensions, so the final image exactly
    reproduces the text layout.

    args:
        text: multi-line ASCII art string
        font_size: font size in points
        bg_color: image background color
        text_color: color used for all characters

    returns:
        PIL Image object with the rendered ASCII art
    """
    lines = text.split("\n")

    font = ImageFont.truetype("DejaVuSansMono.ttf", font_size)

    width, _ = size(font)
    height = int(width * 1.8) 
    max_line = max(len(line) for line in lines)
    img_width = width * max_line
    img_height = height * len(lines)

    image = Image.new("RGB", (img_width, img_height), color=bg_color)
    draw = ImageDraw.Draw(image)

    for row_index, line in enumerate(lines):
        y_pos = row_index * height
        for col_index, char in enumerate(line):
            x_pos = col_index * width
            draw.text((x_pos, y_pos), char, fill=text_color, font=font)
    return image

def resize_rgb(pixels, width, height, new_width=100, char=0.6):
    """
    shrinks the original RGB data to fit the ASCII grid

    uses the same nearest-neighbor sampling logic and aspect ratio
    correction as resize(), but works directly on RGB tuples instead of
    grayscale values.

    args:
        pixels: PixelAccess object
        width: original image width
        height: original image height
        new_width: target width in characters, default 100
        char: character aspect ratio correction factor, default 0.6

    returns:
        tuple (final, new_width, new_height)
    """
    ratio = height / width
    new_height = int(new_width * ratio * char)

    final = []
    for i in range(new_height):
        y = int(i * height / new_height)
        row = []
        for j in range(new_width):
            x = int(j * width / new_width)
            row.append(pixels[x, y])
        final.append(row)
    return final, new_width, new_height

def invert(mat):
    """
    inverts every value in a grayscale matrix

    useful for output viewed on a dark background vs a light one

    args:
        mat: matrix with grayscale values

    returns:
        matrix with every value inverted
    """
    final = []
    for row in mat:
        line = []
        for val in row:
            line.append(255 - val)
        final.append(line)
    return final

def image_colored(text, rgb_matrix, font_size=10, bg_black=True):
    """
    renders colored ASCII art into a PIL image, using per-character colors

    similar to image(), but instead of a single fixed text_color, each
    character is drawn with its own color from rgb_matrix

    args:
        text: ASCII string
        rgb_matrix: 2D list of (r, g, b) tuples
        font_size: font size in points
        bg_black: if True uses a black background

    returns:
        PIL Image object with the rendered colored ASCII art
    """
    lines = text.split("\n")
    font = ImageFont.truetype("DejaVuSansMono.ttf", font_size)

    width, _ = size(font)
    height = int(width * 1.8)
    max_line = max(len(line) for line in lines)
    img_width = width * max_line
    img_height = height * len(lines)

    bg_color = (0, 0, 0) if bg_black else (255, 255, 255)
    img = Image.new("RGB", (img_width, img_height), color=bg_color)
    draw = ImageDraw.Draw(img)

    for i in range(len(lines)):
        line = lines[i]
        y_pos = i * height
        for j in range(len(line)):
            char = line[j]
            x_pos = j * width
            color = rgb_matrix[i][j]
            draw.text((x_pos, y_pos), char, fill=color, font=font)
    return img

def ascii(path, new_width=100, set=CHAR_SET, do_invert=False):
    """
    runs the whole pipeline: loads an image and converts it to ASCII art

    args:
        path: path to the source image
        new_width: target ASCII output width in characters
        set: character set
        do_invert: if True, inverts the grayscale values before processing, default False

    returns:
        tuple (ascii_text, rgb_mat), ascii_text is the resulting ASCII art
        string and rgb_mat the shrunk RGB matrix aligned to the same character grid
    """
    pixels, width, height = load(path)
    rgb_mat, _, _ = resize_rgb(pixels, width, height, new_width)

    gray = grayscale(pixels, height, width)
    gray, new_w, new_h = resize(gray, width, height, new_width)

    if do_invert:
        gray = invert(gray)

    gray = gray_contrast(gray)
    edges = sobel(gray, new_h, new_w)
    gray = combine(gray, edges, new_h, new_w, threshold=400)
    return convert(gray, set), rgb_mat