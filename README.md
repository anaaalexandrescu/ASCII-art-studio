# ASCII Art Studio

Convert digital images and videos into ASCII art through a custom image-processing pipeline, with a PyQt6 desktop interface.

Instead of displaying an image using its original pixels and colors, the image is rendered as a grid of text characters. The character chosen for each position is based on local brightness, refined with edge detection so that shapes and contours are preserved rather than just average tone.

## Features

- **Image to ASCII** conversion with adjustable output width
- **Video to ASCII** conversion, frame by frame, with playback controls (play, pause, stop)
- **Color mode (RGB)** — characters keep the original pixel color while shape is still determined by brightness
- **Invert colors** option
- **Save output** as an image

## How it works

The conversion pipeline combines two sources of information: brightness and edge structure.

1. **Grayscale conversion** — each RGB pixel is reduced to a single luminance value using a perceptually weighted formula (`Y = 0.299R + 0.587G + 0.114B`), since the human eye is more sensitive to green than to blue.
2. **Contrast stretching** — pixel values are normalized to use the full `[0, 255]` range, so dark and bright regions are more clearly separated before mapping to characters.
3. **Resizing** — the image is downscaled to the character width chosen by the user; height is calculated automatically from the original aspect ratio and a correction factor for the non-square shape of monospace characters.
4. **Edge detection (Sobel operator)** — horizontal and vertical gradients are computed for each pixel and combined into a gradient magnitude, highlighting object contours.
5. **Character mapping** — each brightness value is mapped to a character from a density-ordered set (`W8&B$@%#*+=-:.`), so darker areas get visually denser characters and lighter areas get sparser ones.
6. **Color mode** — in RGB mode, the character shown is still chosen from brightness, but it's drawn using the original pixel's color instead of a single fixed color.

For video, each frame is extracted with OpenCV, resized with `cv2.resize` for speed, and passed through the same pipeline used for static images. Processing runs on a dedicated `QThread` worker so the UI stays responsive while frames are being converted.

## Tech stack

- **Python**
- **Pillow** — loading and pixel-level access for static images
- **OpenCV** — video frame extraction and resizing
- **PyQt6** — desktop GUI
- **pytest** — automated test suite

## Project structure

```
ascii/
├── src/
│   ├── image.py          # image loading, grayscale, contrast, resizing, edge detection, ASCII mapping
│   ├── video.py           # frame-by-frame video processing
│   ├── gui.py              # main window
│   └── gui_widgets.py      # reusable GUI components
├── tests/
│   ├── test_image.py
│   └── test_video.py
├── assets/                 # sample images used for testing/screenshots
└── main.py                 # entry point
```

## Getting started

```bash
git clone https://github.com/anaaalexandrescu/ASCII-art-studio.git
cd ASCII-art-studio
pip install -r requirements.txt
python main.py
```

## Usage

1. Open an image or video file from the interface.
2. Set the desired ASCII output width — smaller values give a more compact, less detailed result; larger values preserve more detail but produce a bigger output.
3. Optionally enable **Color Mode (RGB)** or **Invert Colors**.
4. Press **Convert** to process an image, or use the playback controls for video.
5. Save the result as an image if needed.

## Testing

The processing functions are covered by an automated `pytest` suite. Rather than relying only on real images — where the exact expected output is hard to verify by hand — tests use small, manually constructed matrices with known values, so operations like grayscale conversion, resizing, inversion, and character mapping can be checked directly.

Pixel access is tested using a `FakePixels` mock that mirrors Pillow's indexing (`pixels[x, y]`), and video processing is tested using synthetic frames built with NumPy, avoiding any dependency on external video files.

## Notes

This was developed as an academic project (Digital Multimedia course, POLITEHNICA Bucharest). The full technical report (in Romanian) covers the theoretical background — RGB representation, the Sobel operator, contrast normalization — in more depth.
