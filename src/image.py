from PIL import Image, ImageFont, ImageDraw

# CHAR_SET = " .:-=+*#%@$B&8W"
CHAR_SET = "W8&B$@%#*+=-:. "

def load(path):
    """
    incarca o imagine de pe disk si returneaza pixel access object ul plus dimensiunile.
    convertesc la RGB pt format consistent pe 3 canale pt tot ce
    urmeaza, indiferent de modul original al pozei.

    args:
        path: calea catre fisierul imagine

    returns:
        tuplu (pixels, width, height) - pixels e un obiect PixelAccess
        indexat ca pixels[x, y], width/height sunt dimensiunile
    """
    image = Image.open(path)
    image = image.convert("RGB")
    width, height = image.size
    pixels = image.load()
    return pixels, width, height

def grayscale(pixels, height, width):
    """
    transf o matrice de pixeli rgb in grayscale folosind ponderi.

    am folosit formula standard 0.299R + 0.587G + 0.114B: pune mai mult 
    accent pe verde pt ca ochiul uman e mai sensibil la acesta. da rezultate mult
    mai bune decat o medie simpla intre cele 3 canale.

    args:
        pixels: PixelAccess object
        height: inaltimea imaginii
        width: latimea imaginii

    returns:
        matrice de valori grayscale float
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
    intinde contrastul ca sa acopere tot range-ul 0 255

    gasesc min si max in matrice si re scalez liniar fiecare valoare, astfel
    ca pixelul cel mai inchis devine 0 si cel mai deschis devine 255. imbunatateste
    vizual output ul ASCII, mai ales pe poze care nu folosesc deja tot spectrul

    args:
        mat: matrice cu valori grayscale

    returns:
        o noua lista cu valorile cu contrast intins, sau matricea originala
        neschimbata daca toti pixelii au aceeasi valoare (guard pt div by zero)
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
    aplica operatorul sobel pt edge detection pe o matrice grayscale

    fac convolutie cu 2 kernele 3x3 (gx pt gradient orizontal, gy pt vertical)
    ca sa estimez gradientul de intensitate in fiecare pixel. magnitudinea 
    finala e norma euclidiana din gx si gy. la margini - clamping 
    (min/max) in loc de padding cu zero

    args:
        mat: matrice cu valori grayscale
        height: inaltimea matricei
        width: latimea matricei

    returns:
        matrice cu aceeasi forma + valorile de magnitudine ale marginilor
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
    combina matricea grayscale cu edge map_set ul, fortand marginile puternice sa fie negre

    acolo unde magnitudinea marginii depaseste threshold ul, pixelul devine 0
    (negru pur) ca sa scoata in evidenta contururile. altfel ramane valoarea
    grayscale originala

    args:
        mat: matrice cu valori grayscale
        edges: lista 2D cu magnitudinile marginilor
        height: inaltimea matricei
        width: latimea matricei
        threshold: magnitudinea minima ca sa fie considerat margine, default 100

    returns:
        o matrice combinand grayscale ul cu info de margini.
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
    micsoreaza o matrice grayscale la new_width, folosind nearest-neighbor

    noua inaltime se calculeaza din aspect ratio ul original, corectat cu 
    factorul char ca sa compensez faptul ca un caracter monospace e mai inalt
    decat lat 

    args:
        gray_m: matrice
        width: latimea originala
        height: inaltimea originala
        new_width: latimea tinta in caractere, default 100
        char: factor de corectie,d efault 0.6

    returns:
        tuplu (final, new_width, new_height)
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
    seteaza o singura valoare grayscale la un caracter din setul dat

    scaleaza valoarea grayscale intr un index din lungimea setului de 
    caractere, deci pixelii inchisi/ deschisi ajung la capete opuse ale 
    set ului, in functie de cum e ordonat CHAR_SET 

    args:
        gray: valoare grayscale in [0, 255].
        set: string de caractere ordonate dens sparse

    returns:
        un caracter care reprezinta valoarea grayscale data
    """
    idx = int((gray / 255) * (len(set) - 1))
    return set[idx]

def convert(mat, set = CHAR_SET):
    """
    converteste o matrice grayscale intr-un string ASCII pe mai multe linii

    aplic map_set() pe fiecare valoare din matrice, rand cu rand, si unesc 
    caracterele rezultate in linii separate prin newline

    args:
        mat: matrice cu valori grayscale
        set: set ul de caractere folosit la map_setare

    returns:
        string cu ASCII art
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
    calculeaza latimea si inaltimea in pixeli a unui singur caracter monospace

    randez caracterul "A" pe o imagine pt a masura bounding box-ul

    args:
        font: obiect ImageFont incarcat din PIL

    returns:
        tuplu (width, height) in pixeli pt un singur caracter
    """
    img = Image.new("RGB", (10, 10))
    draw = ImageDraw.Draw(img)
    width = draw.textlength("A", font=font) 
    corners = draw.textbbox((0, 0), "A", font=font)
    height = corners[3] - corners[1]
    return int(width), height

def image(text, font_size=10, bg_color=(255, 255, 255), text_color=(0, 0, 0)):
    """
    randeaza un string ASCII intr o imagine PIL simpla

    fiecare caracter e desenat individual la o pozitie de grid calculata din
    dimensiunile caracterului monospace, ca imaginea finala sa reproduca 
    exact layout ul textului.

    args:
        text: string ASCII art pe mai multe linii
        font_size: marimea fontului in puncte
        bg_color: culoarea de fundal a imaginii
        text_color: culoarea folosita pt toate caracterele

    returns:
        obiect PIL Image cu ASCII art ul randat
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
    micsoreaza datele RGB originale ca sa se potriveasca cu grid ul ASCII

    foloseste aceeasi logica de nearest-neighbor sampling si corectie de
    aspect ratio ca resize(), dar lucreaza direct pe tuple uri RGB in loc de
    valori grayscale.

    args:
        pixels: PixelAccess object
        width: latimea imaginii originale
        height: inaltimea imaginii originale
        new_width: latimea tinta in caractere, default 100
        char: factor de corectie a aspect ratio-ului caracterelor default 0.6

    returns:
        tuplu (final, new_width, new_height)
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
    inverseaza fiecare valoare dintr-o matrice grayscale 

    util pt output vazut pe fundal inchis vs deschis

    args:
        mat: matrice cu valori grayscale

    returns:
        matrice cu fiecare valoare inversata
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
    randeaza ASCII art colorat intr o imagine PIL, folosind culori per caracter

    similar cu image(), dar in loc de un singur text_color fix, fiecare
    caracter e desenat cu culoarea lui din rgb_matrix

    args:
        text: string ASCII
        rgb_matrix: lista 2D de tupluri (r, g, b)
        font_size: marimea fontului in puncte
        bg_black: daca True foloseste fundal negru

    returns:
        obiect PIL Image cu ASCII art ul colorat randat
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
    ruleaza tot pipeline ul: incarca o imagine si o converteste in ASCII art

    args:
        path: calea catre imaginea sursa
        new_width: latimea tinta a output ului ASCII in caractere
        set: setul de caractere 
        do_invert: daca True, inverseaza valorile grayscale inainte de procesare, default False

    returns:
        tuplu (ascii_text, rgb_mat), ascii_text este stringul ASCII art rezultat
        si rgb_mat matricea RGB micsorata aliniata la acelasi grid de caractere
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