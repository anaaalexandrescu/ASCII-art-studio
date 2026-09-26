import cv2
import src.image as image

def frame_to_ascii(frame, new_width=150, do_invert=False):
    """
    converteste un frame video numpy array BGR intr un frame ASCII
 
    reface acelasi pipeline ca image.ascii() adaptat pt video: foloseste
    cv2.resize cu interpolare in loc de nearest-neighbor manual
    (mai rapid), si nu incarca nimic de pe disk
    frame ul vine deja in memorie de la camera sau de la un fisier video
 
    pixels e transpus din (height, width, 3) in (width, height, 3)
    ca sa respecte pixels[x, y] folosit de image.grayscale()
 
    args:
        frame: un frame BGR asa cum il returneaza cv2 
        new_width: latimea tinta a output ului ASCII in charactere, default 150
        do_invert: daca True, inverseaza valorile grayscale inainte de procesare
 
    returns:
        tuplu (text, rgb_matrix) - text e string ul ASCII rezultat, rgb_matrix
        e matrice de tupluri (r, g, b) aliniata la acelasi grid ca text ul
    """
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    height, width, _ = rgb_frame.shape
    ratio = height / width
    char_ratio = 0.6

    new_height = int(new_width * ratio * char_ratio)
    if new_height < 1:
        new_height = 1
    rgb_resized = cv2.resize(rgb_frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

    # image.grayscale() foloseste pixels[x, y]
    # în timp ce numpy foloseste [y, x]
    # transpune primele 2 axe
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