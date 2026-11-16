# Copyright (c) 2026 Rickard Längkvist
"""Small, UI-independent gallery filtering and layout helpers."""
EXTENSIONS = {
    'JPEG': {'.jpg', '.jpeg'}, 'PNG': {'.png'}, 'GIF': {'.gif'},
    'WebP': {'.webp'}, 'Andra': {'.bmp', '.tiff', '.tif', '.heic', '.heif'},
}


def filter_images(images, term='', kind='Alla'):
    term = term.strip().casefold()
    extensions = EXTENSIONS.get(kind)
    return [path for path in images if term in path.name.casefold()
            and (extensions is None or path.suffix.lower() in extensions)]


def column_count(width, thumbnail_size):
    # thumbnail + inner padding + border + grid spacing
    return max(1, int(width) // (int(thumbnail_size) + 30))
