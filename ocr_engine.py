import os
import re
import shutil
from datetime import datetime

import pytesseract
from PIL import Image, ImageFilter, ImageEnhance

# Default Tesseract path on Windows
TESSERACT_DEFAULT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Regex pattern for J&T Express resi: JD, JP, JX, JZ, JO, JJ + 10-15 digits
RESI_PATTERN = re.compile(r'(J[DPXZOJ]\d{10,15})', re.IGNORECASE)

# Looser pattern: J + any letter + digits (catches OCR misreads like "JD" → "JB" etc.)
RESI_PATTERN_LOOSE = re.compile(r'(J\s*[A-Z]\s*\d[\d\s]{9,17})', re.IGNORECASE)

# Supported image extensions
SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}

# Common OCR character substitutions
OCR_CHAR_MAP = {
    'l': '1', 'I': '1', '|': '1', 'i': '1',
    'O': '0', 'o': '0', 'Q': '0',
    'S': '5', 's': '5',
    'B': '8', 'b': '6',
    'Z': '2', 'z': '2',
    'G': '6', 'g': '9',
    'T': '7', 't': '7',
    'A': '4',
}


def setup_tesseract(custom_path=None):
    """Configure Tesseract executable path."""
    if custom_path and os.path.isfile(custom_path):
        pytesseract.pytesseract.tesseract_cmd = custom_path
        return True
    elif os.path.isfile(TESSERACT_DEFAULT_PATH):
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_DEFAULT_PATH
        return True
    return False


def scale_up(img, min_width=1500):
    """Scale image up if too small."""
    width, height = img.size
    if width < min_width:
        scale = min_width / width
        img = img.resize((int(width * scale), int(height * scale)), Image.LANCZOS)
    return img


def preprocess_variants(image_path):
    """Generate 3 key preprocessed variants for OCR (balanced speed vs accuracy)."""
    img_original = Image.open(image_path)
    variants = []

    # Variant 1: Grayscale + High Contrast + Sharpen (best for clear text)
    img = img_original.convert('L')
    img = scale_up(img)
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.5)
    img = img.filter(ImageFilter.SHARPEN)
    variants.append(("grayscale_contrast", img))

    # Variant 2: Binary threshold (best for high-contrast documents)
    img = img_original.convert('L')
    img = scale_up(img)
    img = img.point(lambda x: 0 if x < 128 else 255, '1')
    variants.append(("binary", img))

    # Variant 3: Original scaled (fallback, preserves color info)
    img = img_original.convert('RGB')
    img = scale_up(img)
    variants.append(("original", img))

    return variants


# PSM modes: 6 (uniform block) and 3 (auto) cover most cases
PSM_MODES = [6, 3]


def extract_text_multi(image_path):
    """Extract text using multiple preprocessing variants and PSM modes.
    Returns all extracted text concatenated, plus individual results for debugging.
    """
    variants = preprocess_variants(image_path)
    all_texts = []
    debug_info = []

    for variant_name, img in variants:
        for psm in PSM_MODES:
            try:
                config = f'--oem 3 --psm {psm}'
                text = pytesseract.image_to_string(img, config=config)
                if text.strip():
                    all_texts.append(text)
                    debug_info.append(f"[{variant_name}/psm{psm}] {len(text)} chars")
            except Exception:
                continue

    return all_texts, debug_info


def fix_ocr_resi(candidate):
    """Fix common OCR misreads in resi number.
    The first 2 chars should be letters (e.g. JD), rest should be digits.
    """
    # Remove spaces
    candidate = candidate.replace(' ', '')

    if len(candidate) < 12:
        return None

    prefix = candidate[:2].upper()
    digits_part = candidate[2:]

    # Fix prefix: first char must be J
    if prefix[0] != 'J':
        return None

    # Fix second char to valid J&T prefix
    valid_second = {'D', 'P', 'X', 'Z', 'O', 'J'}
    if prefix[1] not in valid_second:
        return None

    # Fix digit part: replace common OCR letter→digit errors
    fixed_digits = []
    for ch in digits_part:
        if ch.isdigit():
            fixed_digits.append(ch)
        elif ch in OCR_CHAR_MAP:
            fixed_digits.append(OCR_CHAR_MAP[ch])
        else:
            # Skip non-digit, non-fixable chars
            continue

    fixed = prefix + ''.join(fixed_digits)

    # Validate length: J&T resi is typically 12-17 chars
    if 12 <= len(fixed) <= 17:
        return fixed

    return None


def count_resi_candidates(texts):
    """Collect all resi candidates with frequency counts across OCR runs.
    Returns dict: {resi: count}
    """
    candidates = {}

    for text in texts:
        found_in_this_text = set()
        cleaned = text.replace(' ', '').replace('\n', ' ').replace('\r', '')

        # Strategy 1: Strict regex on cleaned text
        for match in RESI_PATTERN.finditer(cleaned):
            found_in_this_text.add(match.group(1).upper())

        # Strategy 2: Strict regex line by line
        for line in text.split('\n'):
            for match in RESI_PATTERN.finditer(line):
                found_in_this_text.add(match.group(1).upper())

        # Count each unique resi once per OCR text
        for resi in found_in_this_text:
            candidates[resi] = candidates.get(resi, 0) + 1

    return candidates


def cluster_similar_resi(candidates, threshold=2):
    """Group similar resi numbers (OCR variants of the same real resi).
    Two resi are considered similar if they differ by <= threshold characters
    and have the same prefix (first 2 chars) and same length.
    Returns list of best resi per cluster.
    """
    items = sorted(candidates.items(), key=lambda x: -x[1])
    clusters = []

    for resi, count in items:
        merged = False
        for cluster in clusters:
            if (resi[:2] == cluster['resi'][:2] and len(resi) == len(cluster['resi'])):
                diff = sum(1 for a, b in zip(resi, cluster['resi']) if a != b)
                if diff <= threshold:
                    cluster['members'].append(resi)
                    cluster['count'] += count
                    merged = True
                    break
        if not merged:
            clusters.append({'resi': resi, 'count': count, 'members': [resi]})

    clusters.sort(key=lambda x: -x['count'])
    return [c['resi'] for c in clusters]


def find_resi(texts):
    """Find J&T Express resi numbers using consensus voting.
    Only keeps resi that appear in >= 2 OCR runs (consensus).
    Falls back to loose pattern if nothing found.
    """
    total_runs = len(texts)

    # Phase 1: Strict regex with consensus voting
    candidates = count_resi_candidates(texts)

    # Consensus threshold: at least 2 runs, or 1 if few runs
    min_consensus = 2 if total_runs >= 3 else 1

    confident = {r: c for r, c in candidates.items() if c >= min_consensus}

    if confident:
        return cluster_similar_resi(confident)

    # Phase 2: Fallback — loose pattern + OCR fix (only if strict found nothing)
    loose_candidates = {}
    for text in texts:
        found_in_this_text = set()
        cleaned = text.replace(' ', '').replace('\n', ' ').replace('\r', '')

        for match in RESI_PATTERN_LOOSE.finditer(text):
            fixed = fix_ocr_resi(match.group(1))
            if fixed:
                found_in_this_text.add(fixed)
        for match in RESI_PATTERN_LOOSE.finditer(cleaned):
            fixed = fix_ocr_resi(match.group(1))
            if fixed:
                found_in_this_text.add(fixed)

        for resi in found_in_this_text:
            loose_candidates[resi] = loose_candidates.get(resi, 0) + 1

    if loose_candidates:
        min_loose = max(1, min_consensus - 1)
        confident_loose = {r: c for r, c in loose_candidates.items() if c >= min_loose}
        if confident_loose:
            return cluster_similar_resi(confident_loose)

    return []


def get_image_files(folder_path):
    """Get list of image files in a folder."""
    files = []
    for filename in os.listdir(folder_path):
        ext = os.path.splitext(filename)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            files.append(os.path.join(folder_path, filename))
    return sorted(files)


def create_output_folder(source_folder):
    """Create output folder with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_name = f"Output_{timestamp}"
    output_path = os.path.join(source_folder, output_name)
    os.makedirs(output_path, exist_ok=True)
    return output_path


def process_single_image(image_path, output_folder):
    """
    Process a single image:
    - Extract text via OCR
    - Find all resi numbers
    - Copy image once per resi found to output folder

    Returns: (success: bool, resi_list: list[str], messages: list[str])
    """
    filename = os.path.basename(image_path)

    try:
        # Extract text with multiple strategies
        all_texts, debug_info = extract_text_multi(image_path)

        if not all_texts:
            return False, [], [f"Tidak bisa membaca teks dari '{filename}'"]

        # Find all resi numbers
        resi_list = find_resi(all_texts)

        if not resi_list:
            # Save debug OCR output for troubleshooting
            debug_path = os.path.join(output_folder, f"_debug_{os.path.splitext(filename)[0]}.txt")
            with open(debug_path, 'w', encoding='utf-8') as f:
                f.write(f"=== OCR Debug untuk: {filename} ===\n")
                f.write(f"Strategies tried: {len(debug_info)}\n\n")
                for i, text in enumerate(all_texts):
                    f.write(f"--- Attempt {i+1}: {debug_info[i] if i < len(debug_info) else 'unknown'} ---\n")
                    f.write(text + "\n\n")
            return False, [], [
                f"Tidak ditemukan nomor resi pada '{filename}' ({len(all_texts)} OCR attempts)",
                f"Debug OCR saved: _debug_{os.path.splitext(filename)[0]}.txt"
            ]

        messages = []
        ext = os.path.splitext(filename)[1]

        for resi in resi_list:
            output_filename = f"{resi}{ext}"
            output_path = os.path.join(output_folder, output_filename)

            # Handle duplicate resi names
            counter = 1
            while os.path.exists(output_path):
                output_filename = f"{resi}_{counter}{ext}"
                output_path = os.path.join(output_folder, output_filename)
                counter += 1

            # Copy file
            shutil.copy2(image_path, output_path)
            messages.append(f"Resi: {resi} → {output_filename}")

        return True, resi_list, messages

    except Exception as e:
        return False, [], [f"Error memproses '{filename}': {str(e)}"]


def write_rekap(output_folder, resi_list):
    """Write all resi numbers to a rekap text file."""
    rekap_path = os.path.join(output_folder, "rekap_resi.txt")
    with open(rekap_path, 'w', encoding='utf-8') as f:
        for resi in resi_list:
            f.write(resi + '\n')
    return rekap_path
