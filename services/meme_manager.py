from asyncio import Lock
from pathlib import Path

from astrbot.api import logger
from astrbot.core.utils.io import download_image_by_url

from ..constants import SUPPORTED_IMAGE_SUFFIXES
from ..models import MemeToolResult
from ..utils import (
    detect_image_suffix,
    get_allowed_image_roots,
    is_path_within_roots,
    normalize_category_name,
    resolve_user_path,
)
from .dedup import DHashDedupService


class MemeManager:
    def __init__(self, storage):
        self.storage = storage
        self.write_lock = Lock()
        self.dedup = DHashDedupService(storage=self.storage)
        self.allowed_image_roots = get_allowed_image_roots(
            extra_roots=(self.storage.paths.plugin_dir, self.storage.paths.data_dir)
        )

    def initialize(self) -> None:
        self.dedup.initialize()

    async def _resolve_image_ref(self, image_ref: str) -> tuple[Path | None, bool]:
        """Resolve an image reference into a local file path.

        Returns:
            tuple[Optional[Path], bool]: (resolved_path, downloaded_from_url)
        """
        text = (image_ref or "").strip()
        if not text:
            return None, False

        if text.startswith("http://") or text.startswith("https://"):
            try:
                downloaded = await download_image_by_url(text)
                return resolve_user_path(downloaded), True
            except Exception as exc:  # noqa: BLE001
                logger.warning("AngelSmile: failed to download image %s: %s", text, exc)
                return None, True

        if text.startswith("file:///"):
            local_path = text[8:]
            if len(local_path) > 2 and local_path[0] == "/" and local_path[2] == ":":
                local_path = local_path[1:]
            return resolve_user_path(local_path), False

        return resolve_user_path(text), False

    async def steal_meme(
        self,
        image_path: str,
        category: str,
        description: str | None = None,
        save_name: str | None = None,
    ) -> str:
        raw_path, from_url = await self._resolve_image_ref(image_path)
        if raw_path is None:
            return f"Unable to resolve image reference: {image_path}"

        if not raw_path.exists() or not raw_path.is_file():
            return f"Image file does not exist: {raw_path}"

        if not is_path_within_roots(raw_path, self.allowed_image_roots):
            return "Image path is outside the allowed directories."

        try:
            suffix = detect_image_suffix(raw_path)
        except ValueError:
            return f"Unsupported or invalid image file: {raw_path}"

        if suffix not in SUPPORTED_IMAGE_SUFFIXES:
            return f"Unsupported image format: {suffix or 'unknown'}"

        if not category.strip():
            return "Missing category for meme import."

        final_category = normalize_category_name(category)
        final_description = str(
            description
            or self.storage.get_catalog_description(final_category)
            or "Imported by manual category selection"
        ).strip()
        reason = "Manual category selection"
        overwrite_description = bool(description)

        async with self.write_lock:
            duplicate = self.dedup.find_similar_duplicate(raw_path)
            if duplicate is not None:
                return MemeToolResult(
                    ok=True,
                    saved=False,
                    category=final_category,
                    description=final_description,
                    message="Duplicate meme detected",
                    reason="Duplicate meme detected",
                    duplicate=True,
                    duplicate_type="similar",
                    matched_file=str(duplicate.matched_file),
                    distance=duplicate.distance,
                ).to_message()

            result = self.storage.save_meme(
                source_file=Path(raw_path),
                category=final_category,
                description=final_description,
                reason=reason,
                save_name=save_name,
                overwrite_description=overwrite_description,
            )
            self.dedup.register_file(result.saved_file)

        if from_url:
            logger.info("AngelSmile: saved meme imported from URL %s", image_path)

        return result.to_tool_result().to_message()
