import os
import re
import time
from collections.abc import Iterable
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from astrbot.core.utils.astrbot_path import get_astrbot_data_path

from .constants import DEFAULT_CATEGORY

IMAGE_FORMAT_SUFFIXES = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "GIF": ".gif",
    "WEBP": ".webp",
    "BMP": ".bmp",
}


def normalize_category_name(category: str | None) -> str:
    text = (category or "").strip().lower()
    if not text:
        return DEFAULT_CATEGORY
    text = re.sub(r"[\s\-]+", "_", text)
    text = re.sub(r"[^a-z0-9_\u4e00-\u9fff]", "", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or DEFAULT_CATEGORY


def safe_filename(
    name: str | None,
    suffix: str,
    *,
    force_suffix: bool = False,
    force_extension: bool | None = None,
) -> str:
    normalized_suffix = suffix.lower().strip()
    if normalized_suffix and not normalized_suffix.startswith("."):
        normalized_suffix = f".{normalized_suffix}"
    if not normalized_suffix:
        normalized_suffix = ".jpg"

    force_suffix = force_suffix or bool(force_extension)
    base = (name or "").strip()
    if base:
        base = Path(base).name
        base = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", base)
        stem = Path(base).stem.strip() or f"meme_{int(time.time())}"
        ext = (
            normalized_suffix
            if force_suffix
            else (Path(base).suffix or normalized_suffix)
        )
        return f"{stem}{ext.lower()}"
    return f"meme_{int(time.time())}{normalized_suffix}"


def _is_png(buf: bytes) -> bool:
    return len(buf) > 3 and buf[:4] == b"\x89PNG"


def _is_jpg(buf: bytes) -> bool:
    return len(buf) > 2 and buf[0] == 0xFF and buf[1] == 0xD8 and buf[2] == 0xFF


def _is_gif(buf: bytes) -> bool:
    return len(buf) > 2 and buf[:3] == b"GIF"


def _is_webp(buf: bytes) -> bool:
    return len(buf) > 13 and buf[:4] == b"RIFF" and buf[8:12] == b"WEBP"


def _is_bmp(buf: bytes) -> bool:
    return len(buf) > 1 and buf[:2] == b"BM"


def _is_tiff(buf: bytes) -> bool:
    return len(buf) > 3 and (buf[:2] == b"II" or buf[:2] == b"MM")


def _is_ico(buf: bytes) -> bool:
    return len(buf) > 3 and buf[:4] == b"\x00\x00\x01\x00"


def _is_heic(buf: bytes) -> bool:
    if len(buf) < 16 or buf[4:8] != b"ftyp":
        return False
    major_brand = buf[8:12].decode(errors="ignore")
    return major_brand == "heic" or major_brand in ("mif1", "msf1")


def _is_avif(buf: bytes) -> bool:
    if len(buf) < 16 or buf[4:8] != b"ftyp":
        return False
    major_brand = buf[8:12].decode(errors="ignore")
    return major_brand == "avif"


_IMAGE_CHECKERS = [
    (_is_png, "png"),
    (_is_jpg, "jpg"),
    (_is_gif, "gif"),
    (_is_webp, "webp"),
    (_is_bmp, "bmp"),
    (_is_tiff, "tiff"),
    (_is_ico, "ico"),
    (_is_heic, "heic"),
    (_is_avif, "avif"),
]


def detect_image_format(data: bytes) -> str | None:
    if not data:
        return None
    for checker, ext in _IMAGE_CHECKERS:
        if checker(data):
            return ext
    return None


def get_image_extension(data: bytes, default: str = "jpg") -> str:
    ext = detect_image_format(data)
    return ext if ext else default


def detect_image_suffix(path: Path) -> str:
    try:
        with path.open("rb") as file:
            header = file.read(32)
    except OSError as exc:
        raise ValueError(f"Invalid image file: {path}") from exc

    try:
        with Image.open(path) as image:
            image_format = (image.format or "").upper()
    except (FileNotFoundError, OSError, UnidentifiedImageError):
        image_format = ""
    else:
        detected_suffix = IMAGE_FORMAT_SUFFIXES.get(image_format)
        if detected_suffix:
            return detected_suffix

    detected_extension = get_image_extension(header, default="")
    if detected_extension:
        return f".{detected_extension.lower()}"

    raise ValueError(f"Unsupported image format: {path}")


def resolve_user_path(raw_path: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(raw_path))).resolve()


def get_allowed_image_roots(
    extra_roots: Iterable[Path] | None = None,
) -> tuple[Path, ...]:
    roots = {
        Path(get_astrbot_data_path()).resolve(),
        Path.cwd().resolve(),
    }
    if extra_roots:
        roots.update(path.resolve() for path in extra_roots)
    return tuple(sorted(roots))


def is_path_within_roots(target_path: Path, roots: Iterable[Path]) -> bool:
    resolved_target = target_path.resolve()
    for root in roots:
        resolved_root = root.resolve()
        if resolved_target == resolved_root or resolved_root in resolved_target.parents:
            return True
    return False
