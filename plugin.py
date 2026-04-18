"""
Lora Organizer Plugin for Wan2GP
Groups, display names, trigger words, default strength, notes, and URL per lora.
Data is stored per-model in the plugin folder (e.g. ltx2.json, flux.json).
"""

import os
import re
import json
import shutil
import html as html_lib
from contextlib import nullcontext
from urllib.parse import quote
import gradio as gr
from gradio.context import Context
from shared.utils.plugins import WAN2GPPlugin

ALL_GROUP         = "All"
SETTINGS_FILENAME = "Settings.json"

# ---------------------------------------------------------------------------
# CSS  (max-height is injected dynamically via _listbox_height_css)
# ---------------------------------------------------------------------------

_CSS_BASE = """
#lo_style_block,
#lo_icon_style_block,
#lo_group_indent_block,
#lo_metadata_tracker_block,
#lo_orient_style,
#lo_thumbnail_fit_style,
#lo_groups_width_style,
#lo_height_style {
    display: none !important;
}
#lo_accordion > .label-wrap { margin-bottom: 0 !important; }
#lo_grp_radio, #lo_lora_radio, #lo_lora_list {
    border: none !important;
    border-radius: 8px !important;
    overflow-y: auto !important;
    padding: 0 !important;
    gap: 0 !important;
    display: flex !important;
    flex-direction: column !important;
    background: var(--input-background-fill, #1f2937) !important;
}
#lo_grp_radio label, #lo_lora_radio label, #lo_lora_list .lo-lora-item {
    display: flex !important;
    align-items: center !important;
    width: 100% !important;
    box-sizing: border-box !important;
    border-bottom: 1px solid #333 !important;
    margin: 0 !important;
    padding: 0 !important;
    cursor: pointer !important;
}
#lo_grp_radio label:last-child, #lo_lora_radio label:last-child, #lo_lora_list .lo-lora-item:last-child {
    border-bottom: none !important;
}
#lo_grp_radio input[type="radio"], #lo_lora_radio input[type="radio"] {
    display: none !important;
}
#lo_grp_radio label span, #lo_lora_radio label span, #lo_lora_list .lo-lora-item > span {
    display: block !important;
    width: 100% !important;
    padding: 7px 12px !important;
    font-size: 0.9rem !important;
    font-weight: normal !important;
    user-select: none !important;
    cursor: pointer !important;
}
#lo_grp_radio label span {
    white-space: pre !important;
}
#lo_grp_radio input[type="radio"]:checked ~ span,
#lo_lora_radio input[type="radio"]:checked ~ span {
    color: white !important;
    font-weight: normal !important;
}
#lo_lora_radio {
    display: none !important;
}
#lo_lora_list_html,
#lo_lora_list_html .html-container,
#lo_lora_list_html .prose {
    padding: 0 !important;
    margin: 0 !important;
    min-height: 0 !important;
    border: 0 !important;
    background: transparent !important;
}
#lo_lora_list_html .html-container {
    background: var(--input-background-fill, #1f2937) !important;
    border-radius: 8px !important;
}
#lo_lora_list_bind_block,
#lo_lora_list_bind_block .html-container,
#lo_lora_list_bind_block .prose {
    padding: 0 !important;
    margin: 0 !important;
    min-height: 0 !important;
    height: 0 !important;
    border: 0 !important;
    background: transparent !important;
    overflow: hidden !important;
}
#lo_lora_ui_action,
#lo_lora_ui_action .html-container,
#lo_lora_ui_action .prose,
#lo_lora_ui_action textarea,
#lo_lora_ui_action input,
#lo_active_ui_action,
#lo_active_ui_action .html-container,
#lo_active_ui_action .prose,
#lo_active_ui_action textarea,
#lo_active_ui_action input {
    padding: 0 !important;
    margin: 0 !important;
    min-height: 0 !important;
    height: 0 !important;
    border: 0 !important;
    background: transparent !important;
    overflow: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
}
#lo_lora_list {
    width: 100% !important;
    box-sizing: border-box !important;
    margin: 0 !important;
    background: var(--input-background-fill, #1f2937) !important;
    border-radius: 8px !important;
}
#lo_lora_list[data-view-mode="Vertical List View"],
#lo_lora_list.lo-view-vertical {
    display: flex !important;
    flex-direction: column !important;
    gap: 0 !important;
}
#lo_lora_list[data-view-mode="thumbnail"],
#lo_lora_list.lo-view-thumbnail {
    display: grid !important;
    grid-template-columns: repeat(var(--lo-thumb-cols, 3), minmax(0, 1fr)) !important;
    gap: 8px !important;
    padding: 8px !important;
    align-content: start !important;
}
#lo_lora_list .lo-lora-item {
    border-radius: 8px !important;
    background: var(--button-secondary-background-fill, #475569) !important;
    position: relative !important;
}
#lo_lora_list[data-view-mode="Vertical List View"] .lo-lora-item,
#lo_lora_list.lo-view-vertical .lo-lora-item {
    display: flex !important;
    align-items: center !important;
    width: 100% !important;
    border-bottom: 1px solid #333 !important;
}
#lo_lora_list[data-view-mode="thumbnail"] .lo-lora-item,
#lo_lora_list.lo-view-thumbnail .lo-lora-item {
    display: flex !important;
    flex-direction: column !important;
    width: 100% !important;
    min-height: 0 !important;
    aspect-ratio: 1 / 1 !important;
    border: 1px solid rgba(255,255,255,.08) !important;
    justify-content: flex-end !important;
    align-items: stretch !important;
    overflow: hidden !important;
    text-align: center !important;
    position: relative !important;
}
#lo_lora_list[data-view-mode="thumbnail"] .lo-lora-item::before,
#lo_lora_list.lo-view-thumbnail .lo-lora-item::before {
    content: "" !important;
    flex: 1 1 auto !important;
    min-height: 0 !important;
}
#lo_lora_list[data-view-mode="thumbnail"] .lo-lora-thumb,
#lo_lora_list.lo-view-thumbnail .lo-lora-thumb {
    position: absolute !important;
    inset: 0 !important;
    opacity: .9 !important;
}
#lo_lora_list[data-view-mode="thumbnail"] .lo-lora-thumb-img,
#lo_lora_list.lo-view-thumbnail .lo-lora-thumb-img {
    width: 100% !important;
    height: 100% !important;
    object-fit: cover !important;
    object-position: center top !important;
    display: block !important;
}
#lo_lora_list .lo-lora-item > span {
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}
#lo_lora_list[data-view-mode="Vertical List View"] .lo-lora-item > span,
#lo_lora_list.lo-view-vertical .lo-lora-item > span {
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}
#lo_lora_list[data-view-mode="thumbnail"] .lo-lora-item > span,
#lo_lora_list.lo-view-thumbnail .lo-lora-item > span {
    width: 100% !important;
    padding: 10px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    margin-top: auto !important;
    background: linear-gradient(to top, rgba(15,23,42,.72), rgba(15,23,42,.18)) !important;
    min-height: 44px !important;
    max-height: 44px !important;
    position: relative !important;
    z-index: 1 !important;
    text-align: center !important;
}
#lo_lora_list[data-view-mode="thumbnail"] .lo-lora-item > span .lo-lora-label,
#lo_lora_list.lo-view-thumbnail .lo-lora-item > span .lo-lora-label {
    display: -webkit-box !important;
    -webkit-line-clamp: 2 !important;
    -webkit-box-orient: vertical !important;
    overflow: hidden !important;
    white-space: normal !important;
    line-height: 1.2 !important;
    max-height: 2.4em !important;
    text-align: center !important;
    word-break: break-word !important;
}
#lo_lora_list .lo-lora-item.is-selected {
    background: var(--color-accent, #0ea5e9) !important;
}
#lo_lora_list .lo-lora-item.is-selected > span {
    color: white !important;
    font-weight: normal !important;
}
#lo_lora_list .lo-lora-item.is-dragging {
    opacity: .45 !important;
}
#lo_lora_list[data-view-mode="Vertical List View"] .lo-lora-item.drag-target-before::after,
#lo_lora_list[data-view-mode="Vertical List View"] .lo-lora-item.drag-target-after::after,
#lo_lora_list.lo-view-vertical .lo-lora-item.drag-target-before::after,
#lo_lora_list.lo-view-vertical .lo-lora-item.drag-target-after::after {
    content: "" !important;
    position: absolute !important;
    left: 0 !important;
    right: 0 !important;
    height: 3px !important;
    background: var(--color-accent, #0ea5e9) !important;
    z-index: 4 !important;
    pointer-events: none !important;
}
#lo_lora_list[data-view-mode="Vertical List View"] .lo-lora-item.drag-target-before::after,
#lo_lora_list.lo-view-vertical .lo-lora-item.drag-target-before::after {
    top: 0 !important;
}
#lo_lora_list[data-view-mode="Vertical List View"] .lo-lora-item.drag-target-after::after,
#lo_lora_list.lo-view-vertical .lo-lora-item.drag-target-after::after {
    bottom: 0 !important;
}
#lo_lora_list[data-view-mode="Horizontal List View"] .lo-lora-item.drag-target-before::after,
#lo_lora_list[data-view-mode="Horizontal List View"] .lo-lora-item.drag-target-after::after,
#lo_lora_list[data-view-mode="Thumbnail View"] .lo-lora-item.drag-target-before::after,
#lo_lora_list[data-view-mode="Thumbnail View"] .lo-lora-item.drag-target-after::after,
#lo_lora_list.lo-view-list .lo-lora-item.drag-target-before::after,
#lo_lora_list.lo-view-list .lo-lora-item.drag-target-after::after,
#lo_lora_list.lo-view-thumbnail .lo-lora-item.drag-target-before::after,
#lo_lora_list.lo-view-thumbnail .lo-lora-item.drag-target-after::after {
    content: "" !important;
    position: absolute !important;
    top: 0 !important;
    bottom: 0 !important;
    width: 3px !important;
    background: var(--color-accent, #0ea5e9) !important;
    z-index: 4 !important;
    pointer-events: none !important;
}
#lo_lora_list[data-view-mode="Horizontal List View"] .lo-lora-item.drag-target-before::after,
#lo_lora_list[data-view-mode="Thumbnail View"] .lo-lora-item.drag-target-before::after,
#lo_lora_list.lo-view-list .lo-lora-item.drag-target-before::after,
#lo_lora_list.lo-view-thumbnail .lo-lora-item.drag-target-before::after {
    left: 0 !important;
}
#lo_lora_list[data-view-mode="Horizontal List View"] .lo-lora-item.drag-target-after::after,
#lo_lora_list[data-view-mode="Thumbnail View"] .lo-lora-item.drag-target-after::after,
#lo_lora_list.lo-view-list .lo-lora-item.drag-target-after::after,
#lo_lora_list.lo-view-thumbnail .lo-lora-item.drag-target-after::after {
    right: 0 !important;
}
#lo_lora_list .lo-empty {
    padding: 10px 12px !important;
    color: var(--body-text-color-subdued, #94a3b8) !important;
    font-size: 0.9rem !important;
}
#lo_active_list_html,
#lo_active_list_html .html-container,
#lo_active_list_html .prose {
    padding: 0 !important;
    margin: 0 !important;
    min-height: 0 !important;
    border: 0 !important;
    background: transparent !important;
}
#lo_active_list_html .html-container {
    background: var(--input-background-fill, #1f2937) !important;
    border-radius: 8px !important;
}
#lo_active_list {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: wrap !important;
    gap: 8px !important;
    padding: 8px !important;
    align-content: start !important;
    width: 100% !important;
    box-sizing: border-box !important;
    margin: 0 !important;
    background: var(--input-background-fill, #1f2937) !important;
    border-radius: 8px !important;
}
#lo_active_list .lo-active-item {
    flex: 1 1 auto !important;
    min-width: max-content !important;
    max-width: 100% !important;
    width: auto !important;
    border-radius: 8px !important;
    background: var(--button-secondary-background-fill, #475569) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    position: relative !important;
    box-sizing: border-box !important;
    padding: 7px 52px 7px 12px !important;
    font-size: 0.9rem !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    user-select: none !important;
    cursor: pointer !important;
    gap: 10px !important;
}
#lo_active_list .lo-active-main {
    flex: 0 1 auto !important;
    min-width: 0 !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    white-space: nowrap !important;
    text-align: center !important;
}
#lo_active_list .lo-active-actions {
    display: inline-flex !important;
    align-items: center !important;
    gap: 6px !important;
    flex: 0 0 auto !important;
    position: absolute !important;
    right: 12px !important;
    top: 50% !important;
    transform: translateY(-50%) !important;
}
#lo_active_list .lo-active-action {
    appearance: none !important;
    border: none !important;
    background: transparent !important;
    color: inherit !important;
    cursor: pointer !important;
    padding: 0 !important;
    margin: 0 !important;
    font-size: 0.85rem !important;
    line-height: 1 !important;
    opacity: .9 !important;
}
#lo_active_list .lo-active-action:hover {
    opacity: 1 !important;
}
#lo_active_list .lo-active-strength-input {
    width: 5.5em !important;
    max-width: 8em !important;
    border: 1px solid rgba(255,255,255,.25) !important;
    border-radius: 6px !important;
    background: rgba(15,23,42,.35) !important;
    color: inherit !important;
    padding: 2px 6px !important;
    font: inherit !important;
}
#lo_active_list .lo-active-item.is-selected {
    background: var(--button-secondary-background-fill, #475569) !important;
    color: inherit !important;
}
#lo_active_list .lo-active-item.is-dragging {
    opacity: .45 !important;
}
#lo_active_list .lo-active-item.drag-target-before {
    box-shadow: inset 3px 0 0 var(--color-accent, #0ea5e9) !important;
}
#lo_active_list .lo-active-item.drag-target-after {
    box-shadow: inset -3px 0 0 var(--color-accent, #0ea5e9) !important;
}
#lo_active_list .lo-empty {
    padding: 10px 12px !important;
    color: var(--body-text-color-subdued, #94a3b8) !important;
    font-size: 0.9rem !important;
}
/* Uniform button font size */
#lo_btn_use, #lo_btn_use_both,
#lo_btn_clear_all, #lo_btn_reorder_loras,
#lo_btn_add_group, #lo_btn_add_sub_group, #lo_btn_manage_group, #lo_btn_assign,
#lo_btn_rename_group, #lo_btn_delete_group, #lo_btn_move_up, #lo_btn_move_down,
#lo_btn_group_done, #lo_btn_lora_sort, #lo_btn_lora_sort_used, #lo_btn_lora_done,
#lo_btn_save_assign, #lo_btn_cancel_assign,
#lo_btn_save_edit, #lo_btn_cancel_edit,
#lo_btn_confirm, #lo_btn_cancel_grp,
#lo_btn_del_yes, #lo_btn_del_no,
#lo_btn_save_settings,
#lo_btn_preview_add, #lo_btn_preview_left, #lo_btn_preview_right,
#lo_btn_preview_remove, #lo_btn_preview_clear {
    font-size: 0.8rem !important;
    min-height: 2.45rem !important;
}
/* Strip accordion inner padding so all fields fill full width */
#lo_accordion .block.padded,
#lo_accordion .padding {
    padding-top: 0 !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    overflow-x: hidden !important;
    overflow-y: visible !important;
    gap: 6px !important;
}
#lo_accordion .block.padded > .column.gap:first-child,
#lo_accordion .block.padded > .svelte-vt1mxs.gap:first-child,
#lo_accordion .padding > .column.gap:first-child,
#lo_accordion .padding > .svelte-vt1mxs.gap:first-child {
    padding-top: 2px !important;
}
#lo_accordion .block.padded > *:first-child,
#lo_accordion .padding > *:first-child {
    margin-top: 0 !important;
    padding-top: 0 !important;
}
/* Checkboxes have min-width:160px inline — prevent horizontal overflow in Settings */
#lo_settings_accordion .block.padded {
    min-width: 0 !important;
    overflow-y: hidden !important;
}
/* Restore vertical scrollbar on the listbox containers explicitly */
#lo_grp_radio, #lo_lora_radio, #lo_lora_list {
    overflow-y: auto !important;
}
/* Strip inner div padding that was causing misalignment */
#lo_url_row > div > div {
    padding: 0 !important;
}
#lo_disp_name_col {
    margin-right: 3px !important;
}
/* Open URL button: fixed height matching the textbox input area only */
#lo_btn_open_url {
    font-size: 0.9rem !important;
    min-height: 2.23rem !important;
    max-height: 2.23rem !important;
    align-self: flex-end !important;
}
"""

_CSS_HORIZ = """
#lo_lora_radio {
    flex-direction: row !important;
    flex-wrap: wrap !important;
}
#lo_lora_radio label,
#lo_lora_list[data-view-mode="Horizontal List View"],
#lo_lora_list.lo-view-list {
    justify-content: center !important;
}
#lo_lora_radio label,
#lo_lora_list[data-view-mode="Horizontal List View"] .lo-lora-item,
#lo_lora_list.lo-view-list .lo-lora-item {
    width: auto !important;
    border-bottom: none !important;
    border-right: 1px solid #333 !important;
}
#lo_lora_radio label:last-child,
#lo_lora_list[data-view-mode="Horizontal List View"] .lo-lora-item:last-child,
#lo_lora_list.lo-view-list .lo-lora-item:last-child {
    border-right: none !important;
}
#lo_lora_radio label span,
#lo_lora_list[data-view-mode="Horizontal List View"],
#lo_lora_list.lo-view-list {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: wrap !important;
    gap: 8px !important;
    padding: 8px !important;
    align-content: start !important;
}
#lo_lora_list[data-view-mode="Horizontal List View"] .lo-lora-item,
#lo_lora_list.lo-view-list .lo-lora-item {
    flex: 1 1 auto !important;
    min-width: max-content !important;
    max-width: 100% !important;
    width: auto !important;
    border-right: none !important;
    border-bottom: none !important;
}
#lo_lora_list[data-view-mode="Horizontal List View"] .lo-lora-item > span,
#lo_lora_list.lo-view-list .lo-lora-item > span {
    width: 100% !important;
    text-align: center !important;
}
#lo_lora_radio label span {
    width: auto !important;
    white-space: nowrap !important;
}
"""

DEFAULT_LISTBOX_HEIGHT = 390
LORA_VIEW_VERTICAL = "Vertical List View"
LORA_VIEW_HORIZONTAL = "Horizontal List View"
LORA_VIEW_THUMBNAIL = "Thumbnail View"
THUMB_CYCLE_HOVER = "Cycle thumbnail images when hovering"
THUMB_CYCLE_AUTO = "Auto-cycle thumbnail images"
THUMB_CYCLE_NONE = "Do not cycle thumbnail images"
PLACEMENT_MAIN = "Below the prompt in the main tab"
PLACEMENT_LORA_TAB = "In the lora tab"
PLACEMENT_OWN_TAB = "In its own tab"
AUTO_SORT_NONE = "Do not auto-sort"
AUTO_SORT_NAME = "Auto-sort by name (disables manual sorting)"
AUTO_SORT_MOST_USED = "Auto-sort by most used (disables manual sorting)"
TRIGGER_WORDS_PREPEND = "Add trigger words to the beginning of the prompt"
TRIGGER_WORDS_APPEND = "Add trigger words to the end of the prompt"
TRIGGER_WORDS_REPLACE = "Replace the prompt with trigger words of all activated loras"
TRIGGER_WORDS_NONE = "Do not add trigger words"
DEFAULT_TRIGGER_WORDS_MODE = TRIGGER_WORDS_PREPEND


def _normalize_lora_view_mode(value) -> str:
    if value == LORA_VIEW_THUMBNAIL:
        return LORA_VIEW_THUMBNAIL
    if value == LORA_VIEW_HORIZONTAL:
        return LORA_VIEW_HORIZONTAL
    if value == LORA_VIEW_VERTICAL:
        return LORA_VIEW_VERTICAL
    if value == "Thumbnail view":
        return LORA_VIEW_THUMBNAIL
    if value == "List view":
        return LORA_VIEW_VERTICAL
    return LORA_VIEW_VERTICAL


def _listbox_height_css(px: int) -> str:
    return f"<style>#lo_grp_radio, #lo_lora_radio, #lo_lora_list {{ max-height: {px}px !important; }}</style>"


def _thumbnail_fit_css(fit_without_cropping: bool) -> str:
    object_fit = "contain" if fit_without_cropping else "cover"
    object_position = "center center" if fit_without_cropping else "center top"
    return (
        "<style>"
        f"#lo_lora_list[data-view-mode=\"Thumbnail View\"] .lo-lora-thumb-img,"
        f"#lo_lora_list.lo-view-thumbnail .lo-lora-thumb-img{{object-fit:{object_fit} !important;object-position:{object_position} !important;}}"
        "</style>"
    )


def _groups_column_css(max_width_px: int) -> str:
    try:
        px = int(max_width_px)
    except Exception:
        px = 0
    if px <= 0:
        return (
            "<style>"
            "#lo_lists_row{align-items:stretch !important;}"
            "#lo_groups_col,#lo_loras_col{flex:1 1 0 !important;min-width:0 !important;width:100% !important;}"
            "#lo_groups_col > .form, #lo_loras_col > .form, #lo_groups_col .form, #lo_loras_col .form{min-width:0 !important;}"
            "#lo_groups_col #lo_grp_radio{width:100% !important;}"
            "</style>"
        )
    px = max(80, min(600, px))
    return (
        "<style>"
        "#lo_lists_row{align-items:stretch !important;}"
        f"#lo_groups_col{{flex:0 1 {px}px !important;max-width:min({px}px,45%) !important;min-width:0 !important;}}"
        "#lo_loras_col{flex:1 1 0 !important;min-width:0 !important;width:100% !important;}"
        "#lo_groups_col > .form, #lo_loras_col > .form, #lo_groups_col .form, #lo_loras_col .form{min-width:0 !important;}"
        "#lo_groups_col #lo_grp_radio{width:100% !important;}"
        "</style>"
    )


def _skip_updates(count: int):
    return tuple(gr.skip() for _ in range(count))


def _is_horizontal_view_mode(view_mode: str) -> bool:
    return _normalize_lora_view_mode(view_mode) == LORA_VIEW_HORIZONTAL


def _move_labels(horizontal: bool):
    return ("◀ Move Left", "▶ Move Right") if horizontal else ("⬆ Move Up", "⬇ Move Down")


def _move_labels(horizontal: bool):
    return ("🔼 Move Up", "🔽 Move Down")


def _orient_html(horizontal: bool) -> str:
    return f"<style>{_CSS_HORIZ}</style>" if horizontal else ""


def _group_move_labels_explicit() -> tuple[str, str]:
    return ("🔼 Move Up", "🔽 Move Down")


# ---------------------------------------------------------------------------
# High / Low lora pairing helpers
# ---------------------------------------------------------------------------

_HL_SEP = r"[_\-]"
_PAT_HIGH = re.compile(
    r"(?:(?:^|" + _HL_SEP + r")high(?=" + _HL_SEP + r"|\d|$))",
    re.IGNORECASE,
)
_PAT_LOW = re.compile(
    r"(?:(?:^|" + _HL_SEP + r")low(?=" + _HL_SEP + r"|\d|$))",
    re.IGNORECASE,
)


def _is_wan_dir(lora_dir: str) -> bool:
    path = lora_dir.replace("\\", "/").lower()
    return not any(x in path for x in ("hunyuan", "ltxv", "ltx2", "flux", "qwen", "chatterbox"))


def _hl_kind(lora_name: str) -> str:
    base = os.path.splitext(lora_name)[0]
    if _PAT_HIGH.search(base): return "high"
    if _PAT_LOW.search(base):  return "low"
    return ""


def _swap_hl(lora_name: str, kind: str) -> str:
    base, ext = os.path.splitext(lora_name)
    opposite  = "low" if kind == "high" else "high"
    pat       = _PAT_HIGH if kind == "high" else _PAT_LOW
    def replacer(m):
        matched = m.group(0)
        if matched[0].lower() not in ("h", "l"):
            return matched[0] + opposite
        return opposite
    return pat.sub(replacer, base, count=1) + ext


def _find_pair(lora_name: str, all_loras: list, lora_dir: str) -> tuple:
    if not _is_wan_dir(lora_dir):
        return None, None
    kind = _hl_kind(lora_name)
    if not kind:
        return None, None
    candidate = _swap_hl(lora_name, kind)
    if candidate not in set(all_loras):
        return None, None
    return (lora_name, candidate) if kind == "high" else (candidate, lora_name)


def _auto_strength(lora_dir: str, lora_name: str) -> str:
    base = os.path.splitext(lora_name)[0]
    if not _is_wan_dir(lora_dir):
        return "1"
    if _PAT_HIGH.search(base): return "1;0"
    if _PAT_LOW.search(base):  return "0;1"
    return "1"


# ---------------------------------------------------------------------------
# Settings JSON helpers  (Settings.json in plugin folder)
# ---------------------------------------------------------------------------

def _plugin_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# Custom SVG icon helpers  (icons/ subfolder)
# ---------------------------------------------------------------------------
#
# Approach: No special chars in the label text.
# A synchronous <script> (no defer/async) runs as soon as the browser parses
# the gr.HTML block, setting data-lo-icon on each span before the first paint.
# A MutationObserver then keeps icons updated on every Gradio re-render.
# CSS ::before rules display the SVG via background-image data-URI.


# Icon type keys (single char, used in JS data-lo-icon attribute)
_ICO_FOLDER    = "f"
_ICO_COLLAPSED = "c"
_ICO_EXPANDED  = "e"

_ICON_CSS_CACHE: str | None = None
_DEFAULT_THUMBNAIL_CACHE: str | None = None
_SERVED_FILE_URL_CACHE: dict[str, str] = {}
_STATIC_FILE_BLOCK = None


def _icon_css_block() -> str:
    """Pure CSS icons using input[value^="f:"] sibling selector.
    Gradio sets value= on each <input type=radio> equal to the choice value.
    We encode icon type as a prefix in the value ('f:', 'c:', 'e:'),
    then CSS selects the sibling <span> and injects the ::before icon.
    Zero JS needed — works immediately on first paint."""
    global _ICON_CSS_CACHE
    if _ICON_CSS_CACHE is not None:
        return _ICON_CSS_CACHE

    def after_css(symbol):
        return (
            f'content:"{symbol}" !important;'
            'position:absolute !important;'
            'right:10px !important;'
            'top:50% !important;'
            'transform:translateY(-50%) !important;'
            'font-size:1.05em !important;'
            'line-height:1 !important;'
        )

    collapsed_css = after_css("\u25C0")
    expanded_css  = after_css("\u25BC")

    # Gradio Radio DOM structure:
    #   <label>
    #     <input type="radio" value="f:GroupName">
    #     <span>Group Name</span>   ← display text (our label string)
    #   </label>
    #
    # input[value^="f:"] ~ span::before  targets the span that follows
    # an input whose value starts with "f:" — pure CSS, no JS, no flash.
    # ALL_GROUP uses value="All" (no prefix) — we match it with input[value="All"].
    css = (
        "/* === Lora Organizer accordion arrows (value-prefix CSS) === */\n"
        "#lo_grp_radio label span{position:relative !important;padding-right:2.6em !important;}\n"
        "#lo_grp_radio label input[value^=\"c:\"] ~ span::after {"
        + collapsed_css + "}\n"
        "#lo_grp_radio label input[value^=\"e:\"] ~ span::after {"
        + expanded_css + "}\n"
    )

    _ICON_CSS_CACHE = "<style>\n" + css + "\n</style>"
    return _ICON_CSS_CACHE


def _gradio_file_url(path: str) -> str:
    if not path:
        return ""
    abs_native = os.path.abspath(path)
    cached = _SERVED_FILE_URL_CACHE.get(abs_native)
    if cached:
        return cached
    root_block = Context.root_block
    serving_block = root_block or _STATIC_FILE_BLOCK
    if serving_block is not None:
        try:
            served = serving_block.serve_static_file(abs_native)
            url = (served or {}).get("url") or ""
            if url:
                _SERVED_FILE_URL_CACHE[abs_native] = url
                return url
        except Exception:
            pass
    abs_path = abs_native.replace("\\", "/")
    url = "/file=" + quote(abs_path, safe="/")
    _SERVED_FILE_URL_CACHE[abs_native] = url
    return url


def _default_thumbnail_url() -> str:
    global _DEFAULT_THUMBNAIL_CACHE
    if _DEFAULT_THUMBNAIL_CACHE is not None:
        return _DEFAULT_THUMBNAIL_CACHE
    path = os.path.join(_plugin_dir(), "default_thumbnail.png")
    _DEFAULT_THUMBNAIL_CACHE = _gradio_file_url(path) if os.path.isfile(path) else ""
    return _DEFAULT_THUMBNAIL_CACHE


def _group_indent_js() -> str:
    return (
        "<script>\n"
        "(function(){\n"
        "  var observer = null;\n"
        "  function applyIndent(){\n"
        "    var nodes=document.querySelectorAll('#lo_grp_radio label span');\n"
        "    for(var i=0;i<nodes.length;i++){\n"
        "      var s=nodes[i];\n"
        "      var raw=s.textContent || '';\n"
        "      var m=raw.match(/^[\\u00A0 ]+/);\n"
        "      var lead=m ? m[0].length : 0;\n"
        "      var level=Math.floor(lead / 6);\n"
        "      var clean=raw.replace(/^[\\u00A0 ]+/, '');\n"
        "      if(s.textContent !== clean) s.textContent = clean;\n"
        "      s.style.paddingLeft = (12 + level * 18) + 'px';\n"
        "    }\n"
        "  }\n"
        "  function attach(){\n"
        "    var root=document.querySelector('#lo_grp_radio');\n"
        "    if(!root) return false;\n"
        "    applyIndent();\n"
        "    if(observer) observer.disconnect();\n"
        "    observer = new MutationObserver(applyIndent);\n"
        "    observer.observe(root, {subtree:true,childList:true,characterData:true});\n"
        "    return true;\n"
        "  }\n"
        "  if(!attach()){\n"
        "    var tries=0;\n"
        "    var timer=setInterval(function(){\n"
        "      tries += 1;\n"
        "      if(attach() || tries >= 50) clearInterval(timer);\n"
        "    }, 100);\n"
        "  }\n"
        "})();\n"
        "</script>\n"
    )


def _icon_for_group(has_children: bool, expanded: bool) -> str:
    """Return the icon key (f/c/e) for a group."""
    if has_children and expanded:
        return _ICO_EXPANDED
    elif has_children:
        return _ICO_COLLAPSED
    return _ICO_FOLDER


def _data_dir() -> str:
    """Return the data subfolder, creating it if needed."""
    d = os.path.join(_plugin_dir(), "data")
    os.makedirs(d, exist_ok=True)
    return d


def _model_folder_name(lora_dir: str) -> str:
    if not lora_dir:
        return "default"
    return os.path.basename(os.path.normpath(lora_dir)) or "default"


def _preview_images_dir(lora_dir: str) -> str:
    d = os.path.join(_data_dir(), "images", _model_folder_name(lora_dir))
    os.makedirs(d, exist_ok=True)
    return d


def _sanitize_filename_part(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value or "").strip("._-")
    return cleaned or "preview"


def _preview_rel_to_abs(path: str) -> str:
    if not path:
        return ""
    if os.path.isabs(path):
        return path
    return os.path.join(_plugin_dir(), path)


def _preview_abs_to_rel(path: str) -> str:
    if not path:
        return ""
    try:
        return os.path.relpath(path, _plugin_dir())
    except Exception:
        return path


def _preview_images_for_entry(entry: dict) -> list[str]:
    images = []
    for raw in entry.get("preview_images", []) or []:
        abs_path = _preview_rel_to_abs(str(raw))
        if abs_path and os.path.isfile(abs_path):
            images.append(abs_path)
    return images


def _preview_gallery_value(real_name: str, lora_dir: str) -> list[str]:
    if not real_name or not lora_dir:
        return []
    entry = _load_data(lora_dir)["loras"].get(real_name, {})
    return _preview_images_for_entry(entry)


def _preview_image_url(path: str) -> str:
    if not path or not os.path.isfile(path):
        return ""
    return _gradio_file_url(path)


def _first_preview_image_data_uri(entry: dict) -> str:
    images = _preview_images_for_entry(entry)
    if not images:
        return ""
    return _preview_image_url(images[0])


def _preview_image_urls_for_entry(entry: dict) -> list[str]:
    urls = []
    for path in _preview_images_for_entry(entry):
        url = _preview_image_url(path)
        if url:
            urls.append(url)
    return urls


def _copy_preview_uploads(lora_dir: str, real_name: str, uploaded_files) -> list[str]:
    if not lora_dir or not real_name or not uploaded_files:
        return []
    image_dir = _preview_images_dir(lora_dir)
    base_name = _sanitize_filename_part(os.path.splitext(real_name)[0])
    saved_paths = []

    for uploaded in uploaded_files or []:
        if not uploaded:
            continue
        src = getattr(uploaded, "name", uploaded)
        if not isinstance(src, str) or not os.path.isfile(src):
            continue
        ext = os.path.splitext(src)[1].lower() or ".png"
        candidate = os.path.join(image_dir, f"{base_name}{ext}")
        counter = 1
        while os.path.exists(candidate):
            candidate = os.path.join(image_dir, f"{base_name}__{counter}{ext}")
            counter += 1
        try:
            shutil.copy2(src, candidate)
        except Exception:
            continue
        saved_paths.append(candidate)
    return saved_paths


def _empty_settings() -> dict:
    return {
        "trigger_words_mode": DEFAULT_TRIGGER_WORDS_MODE,
        "remove_trigger_words_on_deactivate": False,
        "thumbnail_cycle_mode": THUMB_CYCLE_HOVER,
        "lora_view_mode": LORA_VIEW_VERTICAL,
        "thumbnail_columns": 3,
        "thumbnail_fit_without_cropping": False,
        "lora_auto_sort_mode": AUTO_SORT_NONE,
        "placement_mode": PLACEMENT_LORA_TAB,
        "side_by_side": True,
        "groups_max_width": 0,
        "listbox_height": DEFAULT_LISTBOX_HEIGHT,
        "accordion_open": False,
        "metadata_accordion_open": False,
        "hide_all_group": False,
    }


def _load_settings() -> dict:
    path = os.path.join(_data_dir(), SETTINGS_FILENAME)
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data.setdefault("trigger_words_mode", DEFAULT_TRIGGER_WORDS_MODE)
            data.setdefault("remove_trigger_words_on_deactivate", False)
            data.setdefault("thumbnail_cycle_mode", THUMB_CYCLE_HOVER)
            data["lora_view_mode"] = _normalize_lora_view_mode(data.get("lora_view_mode"))
            data.setdefault("thumbnail_columns", 3)
            data.setdefault("thumbnail_fit_without_cropping", False)
            data.setdefault("lora_auto_sort_mode", AUTO_SORT_NONE)
            data.setdefault("placement_mode", PLACEMENT_LORA_TAB)
            data.setdefault("side_by_side", True)
            data.setdefault("groups_max_width", 0)
            data.setdefault("listbox_height", DEFAULT_LISTBOX_HEIGHT)
            data.setdefault("accordion_open", False)
            data.setdefault("metadata_accordion_open", False)
            data.setdefault("hide_all_group", False)
            return data
        except Exception:
            pass
    return _empty_settings()


def _save_settings(settings: dict) -> None:
    try:
        path = os.path.join(_data_dir(), SETTINGS_FILENAME)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Per-model data JSON helpers  (plugin_dir/data/<model_folder_name>.json)
# ---------------------------------------------------------------------------

def _data_path_for_dir(lora_dir: str) -> str:
    """Return the data-subfolder JSON path for a given lora directory."""
    if not lora_dir:
        return ""
    folder_name = os.path.basename(os.path.normpath(lora_dir))
    return os.path.join(_data_dir(), f"{folder_name}.json")


def _last_used_key(lora_dir: str) -> str:
    """Settings.json key for last-used-lora-per-group, scoped to the model folder."""
    if not lora_dir:
        return ""   # empty string = caller should skip saving/loading
    folder = os.path.basename(os.path.normpath(lora_dir))
    return f"last_used_lora_per_group_{folder}"


def _empty_data() -> dict:
    return {
        "groups": [],
        "loras": {},
        "lora_order": {},
        "last_group": ALL_GROUP,
    }


def _normalize_groups(raw_groups: list) -> list:
    normalized = []
    seen = set()
    for item in (raw_groups or []):
        if isinstance(item, str):
            name = item.strip()
            if not name or name in seen or name == ALL_GROUP:
                continue
            normalized.append({"name": name, "parent": None, "level": 0})
            seen.add(name)
            continue
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name or name in seen or name == ALL_GROUP:
            continue
        parent = item.get("parent")
        if parent is not None:
            parent = str(parent).strip() or None
        normalized.append({
            "name": name,
            "parent": parent,
            "level": int(item.get("level", 0) or 0),
        })
        seen.add(name)

    names = {g["name"] for g in normalized}
    level_cache = {}

    def compute_level(name: str, stack=None) -> int:
        if name in level_cache:
            return level_cache[name]
        if stack is None:
            stack = set()
        if name in stack:
            level_cache[name] = 0
            return 0
        stack.add(name)
        group = next((g for g in normalized if g["name"] == name), None)
        if not group:
            level = 0
        else:
            parent = group.get("parent")
            if not parent or parent not in names or parent == name:
                group["parent"] = None
                level = 0
            else:
                level = compute_level(parent, stack) + 1
        stack.remove(name)
        level_cache[name] = level
        return level

    for group in normalized:
        group["level"] = compute_level(group["name"])
    return normalized


def _group_names(data: dict) -> list:
    return [g["name"] for g in data.get("groups", [])]


def _group_map(data: dict) -> dict:
    return {g["name"]: g for g in data.get("groups", [])}


def _group_children_map(data: dict) -> dict:
    children = {}
    for group in data.get("groups", []):
        children.setdefault(group.get("parent"), []).append(group)
    return children


def _group_has_children(data: dict, group_name: str) -> bool:
    return any(g.get("parent") == group_name for g in data.get("groups", []))


def _group_descendants(data: dict, group_name: str) -> set:
    descendants = set()
    stack = [group_name]
    while stack:
        current = stack.pop()
        for group in data.get("groups", []):
            if group.get("parent") == current and group["name"] not in descendants:
                descendants.add(group["name"])
                stack.append(group["name"])
    return descendants


def _group_ancestor_chain(data: dict, group_name: str) -> list:
    chain = []
    lookup = _group_map(data)
    current = lookup.get(group_name)
    seen = set()
    while current and current["name"] not in seen:
        seen.add(current["name"])
        chain.append(current["name"])
        parent = current.get("parent")
        current = lookup.get(parent)
    chain.reverse()
    return chain


def _visible_group_names(data: dict, selected: str) -> set:
    visible = set()
    children = _group_children_map(data)
    selected_chain = _group_ancestor_chain(data, selected) if selected and selected != ALL_GROUP else []
    expanded = set(selected_chain)
    if selected and selected != ALL_GROUP and _group_has_children(data, selected):
        expanded.add(selected)

    def visit(parent_name=None):
        for group in children.get(parent_name, []):
            name = group["name"]
            visible.add(name)
            if name in expanded:
                visit(name)

    visit(None)
    return visible


def _format_group_choice(group: dict, expanded: bool, has_children: bool) -> str:
    indent = "\u00A0" * (6 * max(0, int(group.get("level", 0))))
    return indent + "📁 " + group["name"]


def _load_data(lora_dir: str) -> dict:
    if not lora_dir:
        return _empty_data()
    path = _data_path_for_dir(lora_dir)
    if path and os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["groups"] = _normalize_groups(data.get("groups", []))
            data.setdefault("loras", {})
            data.setdefault("lora_order", {})
            data.setdefault("last_group", ALL_GROUP)
            return data
        except Exception:
            pass
    return _empty_data()


def _save_data(lora_dir: str, data: dict) -> None:
    path = _data_path_for_dir(lora_dir)
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def _scan_dir(lora_dir: str) -> list:
    lora_exts = {".safetensors", ".pt", ".pth", ".ckpt"}
    if not lora_dir or not os.path.isdir(lora_dir):
        return []
    try:
        return sorted(
            f for f in os.listdir(lora_dir)
            if os.path.splitext(f)[1].lower() in lora_exts
        )
    except Exception:
        return []


def _ensure_lora(data: dict, real_name: str, lora_dir: str = "") -> dict:
    if real_name not in data["loras"]:
        data["loras"][real_name] = {
            "groups": [], "display_name": "", "trigger_words": "",
            "default_strength": _auto_strength(lora_dir, real_name),
            "info": "", "url": "", "usage_count": 0, "preview_images": [],
        }
    else:
        e = data["loras"][real_name]
        e.setdefault("display_name", "")
        e.setdefault("groups", [])
        e.setdefault("info", "")
        e.setdefault("url", "")
        e.setdefault("usage_count", 0)
        e.setdefault("preview_images", [])
        if "default_strength" not in e:
            e["default_strength"] = _auto_strength(lora_dir, real_name)
        elif isinstance(e["default_strength"], (int, float)):
            e["default_strength"] = f"{e['default_strength']:.4g}"
    return data["loras"][real_name]


def _increment_usage_counts(saved_dir: str, real_names: list[str]) -> None:
    if not saved_dir or not real_names:
        return
    try:
        data = _load_data(saved_dir)
        changed = False
        for real_name in real_names:
            if not real_name:
                continue
            entry = _ensure_lora(data, real_name, saved_dir)
            try:
                current = int(entry.get("usage_count", 0) or 0)
            except Exception:
                current = 0
            entry["usage_count"] = current + 1
            changed = True
        if changed:
            _save_data(saved_dir, data)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------

def _loras_for_group(data: dict, group: str, all_loras: list) -> list:
    if group == ALL_GROUP:
        result = list(all_loras)
    elif not group:
        hide_all = _load_settings().get("hide_all_group", False)
        if hide_all and not _group_names(data):
            return []
        result = list(all_loras)
    else:
        result = [l for l in all_loras
                  if group in data["loras"].get(l, {}).get("groups", [])]
    order_key = group or ALL_GROUP
    stored_order = data.get("lora_order", {}).get(order_key, [])
    if not stored_order:
        return result
    rank = {name: idx for idx, name in enumerate(stored_order)}
    return sorted(result, key=lambda name: (rank.get(name, len(rank)), name.lower()))


def _set_lora_order(data: dict, group: str, ordered_loras: list) -> None:
    key = group or ALL_GROUP
    data.setdefault("lora_order", {})[key] = list(ordered_loras)


def _find_choice_val(choices: list, name: str) -> str:
    """Find the encoded Radio value for a group name in a choices list.
    Falls back to the name itself (covers ALL_GROUP which has no prefix)."""
    for label, val in choices:
        if _grp_name(val) == name:
            return val
    return name  # fallback


def _grp_val(icon_key: str, name: str) -> str:
    """Encode icon type into the Radio value: 'f:GroupName'."""
    return icon_key + ":" + name


def _grp_name(value: str) -> str:
    """Strip icon prefix from Radio value to get the real group name."""
    if value and len(value) > 2 and value[1] == ":" and value[0] in (_ICO_FOLDER, _ICO_COLLAPSED, _ICO_EXPANDED):
        return value[2:]
    return value  # ALL_GROUP or legacy value without prefix


def _group_choices(data: dict) -> list:
    """Return Radio choices where each value encodes the icon type: 'f:Name'."""
    hide_all = _load_settings().get("hide_all_group", False)
    visible_names = _visible_group_names(data, data.get("last_group", ALL_GROUP))
    selected_chain = set(_group_ancestor_chain(data, data.get("last_group", ALL_GROUP)))
    if data.get("last_group") and data.get("last_group") != ALL_GROUP and _group_has_children(data, data["last_group"]):
        selected_chain.add(data["last_group"])

    # ALL_GROUP has no prefix — it's a fixed sentinel value
    choices = [] if hide_all else [("📁 " + ALL_GROUP, ALL_GROUP)]
    children = _group_children_map(data)

    def visit(parent_name=None):
        for group in children.get(parent_name, []):
            name = group["name"]
            if name not in visible_names:
                continue
            icon_key = _icon_for_group(
                has_children=_group_has_children(data, name),
                expanded=name in selected_chain,
            )
            label = _format_group_choice(
                group,
                expanded=name in selected_chain,
                has_children=_group_has_children(data, name),
            )
            choices.append((label, _grp_val(icon_key, name)))
            if name in selected_chain:
                visit(name)

    visit(None)
    return choices


def _visible_selected_group(data: dict, preferred: str | None = None, hide_all: bool | None = None) -> str | None:
    if hide_all is None:
        hide_all = _load_settings().get("hide_all_group", False)
    selected = _grp_name(preferred) if preferred else data.get("last_group", ALL_GROUP)
    names = _group_names(data)
    if selected in names:
        return selected
    if selected == ALL_GROUP and not hide_all:
        return ALL_GROUP
    if not hide_all:
        return ALL_GROUP
    return names[0] if names else None


def _is_real_group_selected(group: str | None) -> bool:
    group = _grp_name(group) if group else group
    return bool(group and group != ALL_GROUP)


def _lora_choices_for_radio(data: dict, loras: list) -> list:
    result = []
    for real_name in loras:
        result.append((_lora_display_name(data, real_name), real_name))
    return result


def _lora_display_name(data: dict, real_name: str) -> str:
    entry = data["loras"].get(real_name, {})
    custom = (entry.get("display_name") or "").strip()
    return custom if custom else os.path.splitext(real_name)[0]


def _display_name_for_sort(data: dict, real_name: str) -> str:
    return _lora_display_name(data, real_name).lower()


def _sort_lora_names(data: dict, loras: list[str], mode: str | None) -> list[str]:
    items = list(loras)
    if mode == AUTO_SORT_NAME:
        return sorted(items, key=lambda name: _display_name_for_sort(data, name))
    if mode == AUTO_SORT_MOST_USED:
        return sorted(
            items,
            key=lambda name: (
                -int(data["loras"].get(name, {}).get("usage_count", 0) or 0),
                _display_name_for_sort(data, name),
            ),
        )
    return items


def _apply_lora_auto_sort(data: dict, all_loras: list[str], mode: str | None,
                          target_group: str | None = None, include_all_group: bool = False) -> None:
    if mode not in (AUTO_SORT_NAME, AUTO_SORT_MOST_USED):
        return
    if target_group is not None:
        groups = [target_group]
        if include_all_group and target_group != ALL_GROUP:
            groups.append(ALL_GROUP)
    else:
        groups = [ALL_GROUP] + _group_names(data)
    for group in groups:
        if group == ALL_GROUP:
            members = list(all_loras)
        else:
            members = [l for l in all_loras if group in data["loras"].get(l, {}).get("groups", [])]
        _set_lora_order(data, group, _sort_lora_names(data, members, mode))


def _pick_selected_lora(settings: dict, lora_dir: str, grp: str | None, lo_choices: list) -> str | None:
    if not lo_choices:
        return None
    key = _last_used_key(lora_dir)
    last_used = settings.get(key, {}).get(grp) if key else None
    if last_used and any(choice[1] == last_used for choice in lo_choices):
        return last_used
    return lo_choices[0][1]


def _lora_list_html(data: dict, loras: list, selected: str | None, reveal_selected: bool = False,
                    view_mode: str | None = None, thumbnail_columns: int | None = None) -> str:
    settings = _load_settings()
    view_mode = _normalize_lora_view_mode(
        view_mode if view_mode is not None else settings.get("lora_view_mode")
    )
    if thumbnail_columns is None:
        thumbnail_columns = settings.get("thumbnail_columns", 3)
    try:
        thumbnail_columns = max(1, min(8, int(thumbnail_columns)))
    except Exception:
        thumbnail_columns = 3
    if view_mode not in (LORA_VIEW_VERTICAL, LORA_VIEW_HORIZONTAL, LORA_VIEW_THUMBNAIL):
        view_mode = LORA_VIEW_VERTICAL
    allow_drag_reorder = settings.get("lora_auto_sort_mode", AUTO_SORT_NONE) == AUTO_SORT_NONE
    thumbnail_cycle_mode = settings.get("thumbnail_cycle_mode", THUMB_CYCLE_HOVER)
    view_mode_attr = html_lib.escape(view_mode, quote=True)
    cycle_mode_attr = html_lib.escape(str(thumbnail_cycle_mode), quote=True)
    view_class = (
        "lo-view-thumbnail" if view_mode == LORA_VIEW_THUMBNAIL
        else "lo-view-list" if view_mode == LORA_VIEW_HORIZONTAL
        else "lo-view-vertical"
    )
    view_style = f" style='--lo-thumb-cols:{thumbnail_columns};'" if view_mode == LORA_VIEW_THUMBNAIL else ""
    default_thumb = _default_thumbnail_url() if view_mode == LORA_VIEW_THUMBNAIL else ""
    if not loras:
        return (
            f"<div id='lo_lora_list' class='{view_class}'{view_style} "
            f"data-view-mode='{view_mode_attr}' data-thumb-cycle-mode='{cycle_mode_attr}'>"
            "<div class='lo-empty'>No loras in this group.</div></div>"
        )
    items = []
    for real_name in loras:
        label = html_lib.escape(_lora_display_name(data, real_name))
        safe_name = html_lib.escape(real_name, quote=True)
        selected_cls = " is-selected" if real_name == selected else ""
        thumb_html = ""
        if view_mode == LORA_VIEW_THUMBNAIL:
            preview_urls = _preview_image_urls_for_entry(data["loras"].get(real_name, {}))
            thumb_uri = (preview_urls[0] if preview_urls else "") or default_thumb
        else:
            preview_urls = []
            thumb_uri = ""
        if thumb_uri:
            thumb_url = html_lib.escape(thumb_uri, quote=True)
            preview_urls_attr = html_lib.escape(json.dumps(preview_urls), quote=True) if len(preview_urls) > 1 else ""
            hover_attrs = (
                f" data-preview-images='{preview_urls_attr}'"
                " onmouseenter='window.__loThumbHoverStart && window.__loThumbHoverStart(this)'"
                " onmouseleave='window.__loThumbHoverEnd && window.__loThumbHoverEnd(this)'"
            ) if len(preview_urls) > 1 else ""
            thumb_html = (
                "<div class='lo-lora-thumb'>"
                f"<img class='lo-lora-thumb-img' src='{thumb_url}' data-default-src='{thumb_url}'{hover_attrs} loading='lazy' decoding='async' alt=''>"
                "</div>"
            )
        label_html = (
            f"<span>{label}</span>"
            if view_mode in (LORA_VIEW_VERTICAL, LORA_VIEW_HORIZONTAL)
            else f"<span><span class='lo-lora-label'>{label}</span></span>"
        )
        items.append(
            f"<div class='lo-lora-item{selected_cls}' data-lora='{safe_name}' draggable='{str(allow_drag_reorder).lower()}' "
            "onclick='window.__loSelectLora && window.__loSelectLora(this.dataset.lora)' "
            "ondragstart='window.__loDragStart && window.__loDragStart(event,this)' "
            "ondragover='window.__loDragOver && window.__loDragOver(event,this)' "
            "ondrop='window.__loDrop && window.__loDrop(event,this)' "
            "ondragend='window.__loDragEnd && window.__loDragEnd(event,this)'>"
            f"{thumb_html}"
            f"{label_html}"
            "</div>"
        )
    return (
        f"<div id='lo_lora_list' class='{view_class}'{view_style} "
        + ("data-reveal-selected='1' " if reveal_selected else "")
        + f"data-view-mode='{view_mode_attr}' data-thumb-cycle-mode='{cycle_mode_attr}' "
        + "ondragover='window.__loListDragOver && window.__loListDragOver(event,this)' "
        + "ondrop='window.__loListDrop && window.__loListDrop(event,this)'>"
        + "".join(items) +
        "</div>"
    )


def _lora_list_bind_js() -> str:
    return """
() => {
    if (window.__loLoraBindingsReady) return;
    window.__loLoraBindingsReady = true;

    function root() {
        if (window.gradioApp) return window.gradioApp();
        const app = document.querySelector('gradio-app');
        return app ? (app.shadowRoot || app) : document;
    }

    function updateGradioInput(elemId, value) {
        const r = root();
        const input = r.querySelector(`#${elemId} textarea, #${elemId} input`);
        if (!input) return false;
        input.value = value;
        input.dispatchEvent(new Event('input', { bubbles: true }));
        return true;
    }

    function rememberScroll(list) {
        if (!list) return;
        window.__loLoraScrollTop = list.scrollTop || 0;
    }

    function setScrollMode(mode) {
        window.__loLoraScrollMode = mode || '';
    }

    function getInputValue(elemId) {
        const r = root();
        const input = r.querySelector(`#${elemId} textarea, #${elemId} input`);
        return input ? (input.value || '') : '';
    }

    function suppressEnsureOnce() {
        window.__loLoraSkipEnsureOnce = true;
    }

    function restoreScroll() {
        if (typeof window.__loLoraScrollTop !== 'number') return;
        const targetTop = window.__loLoraScrollTop;
        const apply = () => {
            const list = root().querySelector('#lo_lora_list');
            if (!list) return;
            list.scrollTop = targetTop;
        };
        apply();
        requestAnimationFrame(() => {
            apply();
            requestAnimationFrame(apply);
        });
    }

    function ensureSelectedVisible() {
        const list = root().querySelector('#lo_lora_list');
        if (!list) return false;
        const selected = list.querySelector('.lo-lora-item.is-selected');
        if (!selected) return false;
        const listTop = list.scrollTop;
        const listBottom = listTop + list.clientHeight;
        const itemTop = selected.offsetTop;
        const itemBottom = itemTop + selected.offsetHeight;
        if (itemTop < listTop) {
            list.scrollTop = itemTop;
        } else if (itemBottom > listBottom) {
            list.scrollTop = itemBottom - list.clientHeight;
        }
        return true;
    }

    function scheduleEnsureSelectedVisible(attempts) {
        const remaining = typeof attempts === 'number' ? attempts : 6;
        if (ensureSelectedVisible()) return true;
        if (remaining <= 0) return false;
        requestAnimationFrame(() => scheduleEnsureSelectedVisible(remaining - 1));
        return false;
    }

    function clickButton(elemId) {
        const r = root();
        const btn = r.querySelector(`#${elemId} button, button#${elemId}, #${elemId}`);
        if (!btn) return false;
        btn.click();
        return true;
    }

    function setSelectedClass(value) {
        const list = root().querySelector('#lo_lora_list');
        if (!list) return;
        const target = value || '';
        list.querySelectorAll('.lo-lora-item').forEach((el) => {
            if ((el.dataset.lora || '') === target) el.classList.add('is-selected');
            else el.classList.remove('is-selected');
        });
    }

    function stopThumbCycle(img) {
        if (!img) return;
        if (img.__loThumbTimer) {
            clearInterval(img.__loThumbTimer);
            img.__loThumbTimer = null;
        }
        img.__loThumbIndex = 0;
        const fallback = img.dataset.defaultSrc || img.getAttribute('src') || '';
        if (fallback) {
            img.setAttribute('src', fallback);
        }
    }

    function stopAllThumbCycles() {
        root().querySelectorAll('.lo-lora-thumb-img').forEach((img) => stopThumbCycle(img));
    }

    function thumbCycleMode() {
        const list = root().querySelector('#lo_lora_list');
        return (list && list.dataset.thumbCycleMode) || '';
    }

    function startThumbCycle(img) {
        if (!img) return;
        let images = [];
        try {
            images = JSON.parse(img.dataset.previewImages || '[]');
        } catch (_) {
            images = [];
        }
        if (!Array.isArray(images) || images.length < 2) return;
        if (img.__loThumbTimer) return;
        img.__loThumbIndex = 0;
        img.__loThumbTimer = setInterval(() => {
            img.__loThumbIndex = ((img.__loThumbIndex || 0) + 1) % images.length;
            const nextSrc = images[img.__loThumbIndex];
            if (nextSrc) {
                img.setAttribute('src', nextSrc);
            }
        }, 700);
    }

    function applyThumbCycleMode() {
        const mode = thumbCycleMode();
        root().querySelectorAll('.lo-lora-thumb-img').forEach((img) => {
            stopThumbCycle(img);
            if (mode === 'Auto-cycle thumbnail images') {
                startThumbCycle(img);
            }
        });
    }

    window.__loThumbHoverStart = function(img) {
        if (!img) return;
        if (thumbCycleMode() !== 'Cycle thumbnail images when hovering') return;
        stopThumbCycle(img);
        startThumbCycle(img);
    };

    window.__loThumbHoverEnd = function(img) {
        if (thumbCycleMode() !== 'Cycle thumbnail images when hovering') return;
        stopThumbCycle(img);
    };

    function clearMarks(list) {
        list.querySelectorAll('.drag-target-before,.drag-target-after').forEach((el) => {
            el.classList.remove('drag-target-before');
            el.classList.remove('drag-target-after');
        });
        window.__loDragTarget = null;
        window.__loDragAfter = false;
    }

    function isHorizontalLoraDropMode(list) {
        if (!list) return false;
        const mode = (list.dataset.viewMode || '').trim();
        return mode === 'Horizontal List View' || mode === 'Thumbnail View';
    }

    function closestItem(list, x, y, dragged) {
        const items = [...list.querySelectorAll('.lo-lora-item')].filter((el) => el !== dragged);
        let best = null;
        let bestScore = Number.POSITIVE_INFINITY;
        items.forEach((item) => {
            const rect = item.getBoundingClientRect();
            const dx = x - (rect.left + rect.width / 2);
            const dy = y - (rect.top + rect.height / 2);
            const score = (dx * dx) + (dy * dy);
            if (score < bestScore) {
                bestScore = score;
                best = item;
            }
        });
        return best;
    }

    function horizontalTargetItem(list, x, y, dragged, selector) {
        const items = [...list.querySelectorAll(selector)].filter((el) => el !== dragged);
        if (!items.length) return null;
        let minRowDistance = Number.POSITIVE_INFINITY;
        const withRowDistance = items.map((item) => {
            const rect = item.getBoundingClientRect();
            const rowDistance =
                y < rect.top ? (rect.top - y) :
                y > rect.bottom ? (y - rect.bottom) :
                0;
            if (rowDistance < minRowDistance) minRowDistance = rowDistance;
            return { item, rect, rowDistance };
        });
        const rowCandidates = withRowDistance.filter((entry) => entry.rowDistance <= minRowDistance + 1);
        let best = null;
        let bestXDistance = Number.POSITIVE_INFINITY;
        rowCandidates.forEach((entry) => {
            const centerX = entry.rect.left + entry.rect.width / 2;
            const xDistance = Math.abs(x - centerX);
            if (xDistance < bestXDistance) {
                bestXDistance = xDistance;
                best = entry;
            }
        });
        return best ? best.item : items[0];
    }

    let dragged = null;
    let activeDragged = null;

    window.__loSelectLora = function(value) {
        setSelectedClass(value || '');
        if (!updateGradioInput('lo_lora_radio', value || '')) return false;
        return clickButton('lo_lora_select_dispatch');
    };

    window.__loDragStart = function(e, item) {
        if (!item || !item.closest('#lo_lora_list')) return;
        if (item.getAttribute('draggable') !== 'true') return;
        stopAllThumbCycles();
        dragged = item;
        dragged.classList.add('is-dragging');
        if (e.dataTransfer) {
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/plain', dragged.dataset.lora || '');
            if (!window.__loTransparentDragImage) {
                const pixel = document.createElement('canvas');
                pixel.width = 1;
                pixel.height = 1;
                window.__loTransparentDragImage = pixel;
            }
            e.dataTransfer.setDragImage(window.__loTransparentDragImage, 0, 0);
        }
    };

    window.__loDragEnd = function(_, item) {
        const list = (item && item.closest('#lo_lora_list')) || root().querySelector('#lo_lora_list');
        if (dragged) dragged.classList.remove('is-dragging');
        if (list) clearMarks(list);
        dragged = null;
    };

    window.__loDragOver = function(e, item) {
        const list = item && item.closest('#lo_lora_list');
        if (!list || !dragged || !list.contains(dragged)) return;
        e.preventDefault();
        if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
        clearMarks(list);
        const target = isHorizontalLoraDropMode(list)
            ? horizontalTargetItem(list, e.clientX, e.clientY, dragged, '.lo-lora-item')
            : item;
        if (!target || target === dragged) return;
        const rect = target.getBoundingClientRect();
        const dx = e.clientX - (rect.left + rect.width / 2);
        const dy = e.clientY - (rect.top + rect.height / 2);
        const after = isHorizontalLoraDropMode(list) ? (dx > 0) : (dy > 0);
        target.classList.add(after ? 'drag-target-after' : 'drag-target-before');
        window.__loDragTarget = target;
        window.__loDragAfter = after;
    };

    window.__loListDragOver = function(e, list) {
        if (!list || !dragged || !list.contains(dragged)) return;
        e.preventDefault();
        if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
        const items = [...list.querySelectorAll('.lo-lora-item:not(.is-dragging)')];
        if (!items.length) return;
        if (isHorizontalLoraDropMode(list)) {
            clearMarks(list);
            const target = horizontalTargetItem(list, e.clientX, e.clientY, dragged, '.lo-lora-item') || items[items.length - 1];
            if (!target || target === dragged) return;
            const rect = target.getBoundingClientRect();
            const after = e.clientX > rect.left + rect.width / 2;
            target.classList.add(after ? 'drag-target-after' : 'drag-target-before');
            window.__loDragTarget = target;
            window.__loDragAfter = after;
            return;
        }
        const last = items[items.length - 1];
        const rect = last.getBoundingClientRect();
        if (e.clientY > rect.top + rect.height / 2) {
            clearMarks(list);
            last.classList.add('drag-target-after');
            window.__loDragTarget = last;
            window.__loDragAfter = true;
        }
    };

    window.__loDrop = function(e, item) {
        const list = item && item.closest('#lo_lora_list');
        if (!list || !dragged || !list.contains(dragged)) return;
        e.preventDefault();
        const target = window.__loDragTarget;
        const after = !!window.__loDragAfter;
        if (target && target !== dragged) {
            if (after) list.insertBefore(dragged, target.nextSibling);
            else list.insertBefore(dragged, target);
        }
        clearMarks(list);
        const order = [...list.querySelectorAll('.lo-lora-item')].map((el) => el.dataset.lora || '');
        if (updateGradioInput('lo_lora_ui_action', JSON.stringify({
            action: 'reorder',
            order: order,
            value: dragged.dataset.lora || '',
            nonce: Date.now()
        }))) {
            clickButton('lo_lora_ui_dispatch');
        }
    };

    window.__loListDrop = function(e, list) {
        if (!list || !dragged || !list.contains(dragged)) return;
        e.preventDefault();
        const target = window.__loDragTarget;
        const after = !!window.__loDragAfter;
        if (target && target !== dragged) {
            if (after) list.insertBefore(dragged, target.nextSibling);
            else list.insertBefore(dragged, target);
        }
        clearMarks(list);
        const order = [...list.querySelectorAll('.lo-lora-item')].map((el) => el.dataset.lora || '');
        if (updateGradioInput('lo_lora_ui_action', JSON.stringify({
            action: 'reorder',
            order: order,
            value: dragged.dataset.lora || '',
            nonce: Date.now()
        }))) {
            clickButton('lo_lora_ui_dispatch');
        }
    };

    window.__loPrepareGroupReveal = function() {
        setScrollMode('ensure-selected');
        window.__loPendingRevealPreviousValue = getInputValue('lo_lora_radio');
    };

    function setSelectedActiveClass(value) {
        const list = root().querySelector('#lo_active_list');
        if (!list) return;
        list.querySelectorAll('.lo-active-item').forEach((el) => {
            if ((el.dataset.active || '') === (value || '')) el.classList.add('is-selected');
            else el.classList.remove('is-selected');
        });
    }

    function clearActiveMarks(list) {
        list.querySelectorAll('.drag-target-before,.drag-target-after').forEach((el) => {
            el.classList.remove('drag-target-before');
            el.classList.remove('drag-target-after');
        });
        window.__loActiveDragTarget = null;
        window.__loActiveDragAfter = false;
    }

    function isHorizontalActiveDropMode(list) {
        return !!list;
    }

    window.__loSelectActive = function(value) {
        setSelectedActiveClass(value || '');
        if (!updateGradioInput('lo_active_ui_action', JSON.stringify({
            action: 'select',
            value: value || '',
            nonce: Date.now()
        }))) return false;
        return clickButton('lo_active_ui_dispatch');
    };

    window.__loActiveDragStart = function(e, item) {
        if (!item || !item.closest('#lo_active_list')) return;
        if (item.getAttribute('draggable') !== 'true') return;
        activeDragged = item;
        activeDragged.classList.add('is-dragging');
        if (e.dataTransfer) {
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/plain', activeDragged.dataset.active || '');
        }
    };

    window.__loActiveDragEnd = function(_, item) {
        const list = (item && item.closest('#lo_active_list')) || root().querySelector('#lo_active_list');
        if (activeDragged) activeDragged.classList.remove('is-dragging');
        if (list) clearActiveMarks(list);
        activeDragged = null;
    };

    window.__loActiveDragOver = function(e, item) {
        const list = item && item.closest('#lo_active_list');
        if (!list || !activeDragged || !list.contains(activeDragged)) return;
        e.preventDefault();
        if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
        clearActiveMarks(list);
        const target = isHorizontalActiveDropMode(list)
            ? horizontalTargetItem(list, e.clientX, e.clientY, activeDragged, '.lo-active-item')
            : item;
        if (!target || target === activeDragged) return;
        const rect = target.getBoundingClientRect();
        const dx = e.clientX - (rect.left + rect.width / 2);
        const dy = e.clientY - (rect.top + rect.height / 2);
        const after = isHorizontalActiveDropMode(list) ? (dx > 0) : (dy > 0);
        target.classList.add(after ? 'drag-target-after' : 'drag-target-before');
        window.__loActiveDragTarget = target;
        window.__loActiveDragAfter = after;
    };

    window.__loActiveListDragOver = function(e, list) {
        if (!list || !activeDragged || !list.contains(activeDragged)) return;
        e.preventDefault();
        if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
        const items = [...list.querySelectorAll('.lo-active-item:not(.is-dragging)')];
        if (!items.length) return;
        if (isHorizontalActiveDropMode(list)) {
            clearActiveMarks(list);
            const target = horizontalTargetItem(list, e.clientX, e.clientY, activeDragged, '.lo-active-item') || items[items.length - 1];
            if (!target || target === activeDragged) return;
            const rect = target.getBoundingClientRect();
            const after = e.clientX > rect.left + rect.width / 2;
            target.classList.add(after ? 'drag-target-after' : 'drag-target-before');
            window.__loActiveDragTarget = target;
            window.__loActiveDragAfter = after;
            return;
        }
        const last = items[items.length - 1];
        const rect = last.getBoundingClientRect();
        if (e.clientY > rect.top + rect.height / 2) {
            clearActiveMarks(list);
            last.classList.add('drag-target-after');
            window.__loActiveDragTarget = last;
            window.__loActiveDragAfter = true;
        }
    };

    window.__loActiveDrop = function(e, item) {
        const list = item && item.closest('#lo_active_list');
        if (!list || !activeDragged || !list.contains(activeDragged)) return;
        e.preventDefault();
        const target = window.__loActiveDragTarget;
        const after = !!window.__loActiveDragAfter;
        if (target && target !== activeDragged) {
            if (after) list.insertBefore(activeDragged, target.nextSibling);
            else list.insertBefore(activeDragged, target);
        }
        clearActiveMarks(list);
        const order = [...list.querySelectorAll('.lo-active-item')].map((el) => el.dataset.active || '');
        if (updateGradioInput('lo_active_ui_action', JSON.stringify({
            action: 'reorder',
            order: order,
            value: activeDragged.dataset.active || '',
            nonce: Date.now()
        }))) {
            clickButton('lo_active_ui_dispatch');
        }
    };

    window.__loRemoveActive = function(item) {
        if (!item) return false;
        const payload = {
            action: 'remove',
            index: Number(item.dataset.index || -1),
            value: item.dataset.active || '',
            nonce: Date.now()
        };
        if (!updateGradioInput('lo_active_ui_action', JSON.stringify(payload))) return false;
        return clickButton('lo_active_ui_dispatch');
    };

    window.__loEditActive = function(item) {
        if (!item) return false;
        setSelectedActiveClass(item.dataset.active || '');
        if (item.classList.contains('is-editing')) return false;
        item.classList.add('is-editing');
        const strengthEl = item.querySelector('.lo-active-strength');
        if (!strengthEl) return false;
        const original = strengthEl.dataset.strength || '';
        strengthEl.innerHTML = "<input class='lo-active-strength-input' type='text' spellcheck='false'>";
        const input = strengthEl.querySelector('input');
        if (!input) return false;
        input.value = original;
        input.focus();
        input.select();

        let done = false;
        const restore = (value) => {
            strengthEl.dataset.strength = value;
            strengthEl.textContent = value ? `[${value}]` : '';
            item.classList.remove('is-editing');
        };
        const commit = (cancel) => {
            if (done) return;
            done = true;
            const next = (input.value || '').trim();
            if (cancel) {
                restore(original);
                return;
            }
            const finalValue = next || original;
            restore(finalValue);
            const payload = {
                action: 'set_strength',
                index: Number(item.dataset.index || -1),
                value: item.dataset.active || '',
                strength: finalValue,
                nonce: Date.now()
            };
            if (updateGradioInput('lo_active_ui_action', JSON.stringify(payload))) {
                clickButton('lo_active_ui_dispatch');
            }
        };
        input.addEventListener('keydown', (ev) => {
            if (ev.key === 'Enter') {
                ev.preventDefault();
                commit(false);
            } else if (ev.key === 'Escape') {
                ev.preventDefault();
                commit(true);
            }
        });
        input.addEventListener('blur', () => commit(false));
        return false;
    };

    window.__loActiveListDrop = function(e, list) {
        if (!list || !activeDragged || !list.contains(activeDragged)) return;
        e.preventDefault();
        const target = window.__loActiveDragTarget;
        const after = !!window.__loActiveDragAfter;
        if (target && target !== activeDragged) {
            if (after) list.insertBefore(activeDragged, target.nextSibling);
            else list.insertBefore(activeDragged, target);
        }
        clearActiveMarks(list);
        const order = [...list.querySelectorAll('.lo-active-item')].map((el) => el.dataset.active || '');
        if (updateGradioInput('lo_active_ui_action', JSON.stringify({
            action: 'reorder',
            order: order,
            value: activeDragged.dataset.active || '',
            nonce: Date.now()
        }))) {
            clickButton('lo_active_ui_dispatch');
        }
    };

    root().addEventListener('click', (e) => {
        const toggle = e.target.closest('#lo_accordion > .label-wrap, #lo_accordion .label-wrap');
        if (!toggle) return;
        requestAnimationFrame(() => {
            requestAnimationFrame(() => scheduleEnsureSelectedVisible(12));
        });
    }, true);

    const observer = new MutationObserver(() => {
        applyThumbCycleMode();
        const list = root().querySelector('#lo_lora_list');
        if (list && list.dataset.revealSelected === '1') {
            scheduleEnsureSelectedVisible(12);
            list.dataset.revealSelected = '0';
            window.__loLoraScrollMode = '';
            window.__loPendingRevealPreviousValue = '';
            return;
        }
        const mode = window.__loLoraScrollMode || '';
        if (mode === 'preserve') {
            restoreScroll();
            suppressEnsureOnce();
        } else if (mode === 'ensure-selected') {
            const currentValue = getInputValue('lo_lora_radio');
            if ((window.__loPendingRevealPreviousValue || '') === currentValue) {
                return;
            }
            if (window.__loLoraSkipEnsureOnce) {
                window.__loLoraSkipEnsureOnce = false;
                return;
            }
            scheduleEnsureSelectedVisible(8);
            window.__loLoraScrollMode = '';
            window.__loPendingRevealPreviousValue = '';
            return;
        }
        if (mode) {
            window.__loLoraScrollMode = '';
        }
    });
    observer.observe(root(), { childList: true, subtree: true });
    applyThumbCycleMode();
    function triggerInitialReveal() {
        if (window.__loInitialRevealDone) return;
        const initialList = root().querySelector('#lo_lora_list');
        if (!initialList) return;
        const selected = initialList.querySelector('.lo-lora-item.is-selected');
        if (!selected) return;
        const shouldReveal = initialList.dataset.revealSelected === '1';
        if (!shouldReveal && initialList.scrollHeight <= initialList.clientHeight) {
            return;
        }
        scheduleEnsureSelectedVisible(12);
        initialList.dataset.revealSelected = '0';
    }
    function startInitialRevealWatch() {
        if (window.__loInitialRevealWatchStarted) return;
        window.__loInitialRevealWatchStarted = true;
        const startedAt = Date.now();
        const tick = () => {
            if (window.__loInitialRevealDone) return;
            const list = root().querySelector('#lo_lora_list');
            const selected = list ? list.querySelector('.lo-lora-item.is-selected') : null;
            if (list && selected) {
                const hasOverflow = list.scrollHeight > list.clientHeight;
                if (hasOverflow) {
                    ensureSelectedVisible();
                    const listTop = list.scrollTop;
                    const listBottom = listTop + list.clientHeight;
                    const itemTop = selected.offsetTop;
                    const itemBottom = itemTop + selected.offsetHeight;
                    if (itemTop >= listTop && itemBottom <= listBottom) {
                        window.__loInitialRevealDone = true;
                        return;
                    }
                }
            }
            if (Date.now() - startedAt < 2500) {
                setTimeout(tick, 100);
            }
        };
        tick();
    }
    triggerInitialReveal();
    startInitialRevealWatch();
    setTimeout(triggerInitialReveal, 0);
    setTimeout(triggerInitialReveal, 80);
    setTimeout(triggerInitialReveal, 200);
    setTimeout(triggerInitialReveal, 500);
    setTimeout(restoreScroll, 0);
}
"""


def _assign_choices(all_loras: list) -> list:
    return [(os.path.splitext(f)[0], f) for f in all_loras]


def _is_display_name_unique(data: dict, real_name: str, new_display: str) -> bool:
    if not new_display.strip():
        return True
    new_lower = new_display.strip().lower()
    for other_real, entry in data["loras"].items():
        if other_real == real_name:
            continue
        other_disp = (entry.get("display_name") or "").strip().lower() or other_real.lower()
        if other_disp == new_lower:
            return False
    return True


def _apply_trigger_words(prompt: str, tw: str, mode: str) -> str:
    tw = tw.strip()
    if not tw:
        return prompt
    if mode == TRIGGER_WORDS_NONE:
        return prompt
    if mode == TRIGGER_WORDS_REPLACE:
        return tw
    p = prompt.rstrip()
    if mode == TRIGGER_WORDS_APPEND:
        return tw if not p else p + ("" if p.endswith(",") else ", ") + tw
    return tw if not p else tw + ("" if tw.endswith(",") else ", ") + p


def _append_mult(current: str, strength: str) -> str:
    s = (strength or "1").strip()
    existing = (current or "").strip()
    if not existing:
        return s
    # If the multipliers box ends with "|", append without a space
    sep = "" if existing.endswith("|") else " "
    return existing + sep + s


def _join_trigger_words(parts: list[str]) -> str:
    return ", ".join(p.strip() for p in parts if isinstance(p, str) and p.strip())


def _split_multiplier_values(current: str) -> list[str]:
    text = (current or "").strip()
    if not text:
        return []
    return [part for part in re.split(r"\s+", text) if part]


def _activated_loras_html(lora_dir: str, active_values, multipliers: str = "", known_loras: list | None = None,
                          selected_active: str | None = None) -> str:
    values = list(active_values) if active_values else []
    if not values:
        return "<div id='lo_active_list'><div class='lo-empty'>No activated loras.</div></div>"
    all_loras = known_loras if known_loras is not None else live_loras(lora_dir)
    value_to_real = {real_name: real_name for real_name in all_loras}
    data = _load_data(lora_dir)
    strengths = _split_multiplier_values(multipliers)
    items = []
    for idx, active_value in enumerate(values):
        real_name = value_to_real.get(active_value)
        if not real_name:
            continue
        label = _lora_display_name(data, real_name)
        strength = strengths[idx] if idx < len(strengths) else ""
        label_html = html_lib.escape(label)
        strength_text = f"[{strength}]" if strength else ""
        strength_html = html_lib.escape(strength_text)
        strength_attr = html_lib.escape(str(strength), quote=True)
        safe_value = html_lib.escape(str(active_value), quote=True)
        safe_index = html_lib.escape(str(idx), quote=True)
        selected_cls = " is-selected" if str(active_value) == str(selected_active or "") else ""
        items.append(
            f"<div class='lo-active-item{selected_cls}' data-active='{safe_value}' data-index='{safe_index}' draggable='true' "
            "onclick='window.__loSelectActive && window.__loSelectActive(this.dataset.active)' "
            "ondragstart='window.__loActiveDragStart && window.__loActiveDragStart(event,this)' "
            "ondragover='window.__loActiveDragOver && window.__loActiveDragOver(event,this)' "
            "ondrop='window.__loActiveDrop && window.__loActiveDrop(event,this)' "
            "ondragend='window.__loActiveDragEnd && window.__loActiveDragEnd(event,this)'>"
            f"<span class='lo-active-main'><span class='lo-active-label'>{label_html}</span> "
            f"<span class='lo-active-strength' data-strength='{strength_attr}'>{strength_html}</span></span>"
            "<span class='lo-active-actions'>"
            "<button type='button' class='lo-active-action lo-active-edit' title='Edit strength' "
            "onclick='event.stopPropagation(); window.__loEditActive && window.__loEditActive(this.closest(\".lo-active-item\"))'>✏️</button>"
            "<button type='button' class='lo-active-action lo-active-remove' title='Remove activated lora' "
            "onclick='event.stopPropagation(); window.__loRemoveActive && window.__loRemoveActive(this.closest(\".lo-active-item\"))'>✖</button>"
            "</span></div>"
        )
    if not items:
        return "<div id='lo_active_list'><div class='lo-empty'>No activated loras.</div></div>"
    active_html = "".join(items).replace("βοΈ", "✏️").replace("Γ—", "✖").replace("×", "✖")
    return (
        "<div id='lo_active_list' "
        "ondragover='window.__loActiveListDragOver && window.__loActiveListDragOver(event,this)' "
        "ondrop='window.__loActiveListDrop && window.__loActiveListDrop(event,this)'>"
        + active_html + "</div>"
    )


def _activated_loras_html(lora_dir: str, active_values, multipliers: str = "", known_loras: list | None = None,
                          selected_active: str | None = None) -> str:
    values = list(active_values) if active_values else []
    if not values:
        return "<div id='lo_active_list'><div class='lo-empty'>No activated loras.</div></div>"
    all_loras = known_loras if known_loras is not None else live_loras(lora_dir)
    value_to_real = {real_name: real_name for real_name in all_loras}
    data = _load_data(lora_dir)
    strengths = _split_multiplier_values(multipliers)
    items = []
    for idx, active_value in enumerate(values):
        real_name = value_to_real.get(active_value)
        if not real_name:
            continue
        label = _lora_display_name(data, real_name)
        strength = strengths[idx] if idx < len(strengths) else ""
        label_html = html_lib.escape(label)
        strength_text = f"[{strength}]" if strength else ""
        strength_html = html_lib.escape(strength_text)
        strength_attr = html_lib.escape(str(strength), quote=True)
        safe_value = html_lib.escape(str(active_value), quote=True)
        safe_index = html_lib.escape(str(idx), quote=True)
        selected_cls = " is-selected" if str(active_value) == str(selected_active or "") else ""
        items.append(
            f"<div class='lo-active-item{selected_cls}' data-active='{safe_value}' data-index='{safe_index}' draggable='true' "
            "onclick='window.__loSelectActive && window.__loSelectActive(this.dataset.active)' "
            "ondragstart='window.__loActiveDragStart && window.__loActiveDragStart(event,this)' "
            "ondragover='window.__loActiveDragOver && window.__loActiveDragOver(event,this)' "
            "ondrop='window.__loActiveDrop && window.__loActiveDrop(event,this)' "
            "ondragend='window.__loActiveDragEnd && window.__loActiveDragEnd(event,this)'>"
            f"<span class='lo-active-main'><span class='lo-active-label'>{label_html}</span> "
            f"<span class='lo-active-strength' data-strength='{strength_attr}'>{strength_html}</span></span>"
            "<span class='lo-active-actions'>"
            "<button type='button' class='lo-active-action lo-active-edit' title='Edit strength' "
            "onclick='event.stopPropagation(); window.__loEditActive && window.__loEditActive(this.closest(\".lo-active-item\"))'>✏️</button>"
            "<button type='button' class='lo-active-action lo-active-remove' title='Remove activated lora' "
            "onclick='event.stopPropagation(); window.__loRemoveActive && window.__loRemoveActive(this.closest(\".lo-active-item\"))'>✖</button>"
            "</span></div>"
        )
    if not items:
        return "<div id='lo_active_list'><div class='lo-empty'>No activated loras.</div></div>"
    active_html = "".join(items)
    return (
        "<div id='lo_active_list' "
        "ondragover='window.__loActiveListDragOver && window.__loActiveListDragOver(event,this)' "
        "ondrop='window.__loActiveListDrop && window.__loActiveListDrop(event,this)'>"
        + active_html + "</div>"
    )


def _clear_button_update(active_loras, undo_mode: bool = False):
    has_active = bool(active_loras)
    if undo_mode:
        return gr.update(value="↶ Restore Cleared Loras", interactive=True)
    return gr.update(value="❌ Clear Activated Loras", interactive=has_active)


def _manage_group_button_update(group: str | None):
    return gr.update(interactive=_is_real_group_selected(group))


def _lora_sort_ui_updates(real_name: str | None, group: str | None, data: dict, all_loras: list,
                          auto_sort_mode: str | None):
    group = _grp_name(group) if group else group
    loras = _loras_for_group(data, group, all_loras)
    has_loras = bool(real_name and real_name in loras)
    allow_manual_sort = has_loras and auto_sort_mode == AUTO_SORT_NONE and len(loras) > 0
    return (
        gr.update(interactive=allow_manual_sort),
        gr.update(interactive=allow_manual_sort),
        gr.update(interactive=has_loras),
    )


def _use_both_button_state(real_name: str | None, saved_dir: str, all_loras: list):
    if not real_name:
        return gr.update(visible=False)
    high, low = _find_pair(real_name, all_loras, saved_dir)
    has_pair = (high is not None and low is not None)
    if not has_pair:
        return gr.update(visible=False)
    return gr.update(visible=True)


# ---------------------------------------------------------------------------
# Plugin
# ---------------------------------------------------------------------------

class LoraOrganizerPlugin(WAN2GPPlugin):

    name        = "Lora Organizer"
    version     = "1.01"

    def __init__(self):
        super().__init__()
        self._model_change_pending = False
        self._pending_model_type = None

    def setup_ui(self):
        settings = _load_settings()
        self.request_global("get_lora_dir")
        self.request_global("get_state_model_type")
        self.request_global("loras_names")
        self.request_component("loras")
        self.request_component("loras_choices")
        self.request_component("loras_multipliers")
        self.request_component("prompt")
        self.request_component("main")
        self.request_component("state")
        placement_mode = settings.get("placement_mode", PLACEMENT_LORA_TAB)
        if placement_mode == PLACEMENT_OWN_TAB:
            self.add_tab(
                tab_id="LoraOrganizer",
                label="Lora Organizer",
                component_constructor=self._build_ui,
            )
        else:
            insert_target = "prompt" if placement_mode == PLACEMENT_MAIN else "loras_multipliers"
            self.insert_after(insert_target, self._build_ui)

    def post_ui_setup(self, requested_components=None):
        pass

    def on_model_change(self, state: dict, model_type) -> None:
        self._pending_model_type = model_type
        self._model_change_pending = True

    def _build_ui(self):
        def _component_or_none(value):
            return value if hasattr(value, "_id") else None

        loras_comp  = (
            _component_or_none(getattr(self, "loras", None))
            or _component_or_none(getattr(self, "loras_choices", None))
        )
        mult_comp   = _component_or_none(getattr(self, "loras_multipliers", None))
        prompt_comp = _component_or_none(getattr(self, "prompt", None))
        main_comp   = _component_or_none(getattr(self, "main", None))
        state_comp  = _component_or_none(getattr(self, "state", None))

        # ── Core helpers ──────────────────────────────────────────────

        def resolve_lora_dir(state_val=None) -> str:
            get_ld  = getattr(self, "get_lora_dir",         None)
            get_smt = getattr(self, "get_state_model_type", None)
            if get_ld is not None and get_smt is not None and state_val is not None:
                try:
                    model_type = get_smt(state_val)
                    if model_type:
                        path = get_ld(model_type)
                        if path and os.path.isdir(path):
                            return os.path.abspath(path)
                except Exception:
                    pass
            # Fallback: scan filesystem for lora files
            names = live_loras()
            if names:
                sample = names[0]
                cwd = os.getcwd()
                self_raw = getattr(self, "lora_dir", "") or ""
                if self_raw:
                    abs_d = os.path.abspath(self_raw)
                    if abs_d != cwd and os.path.isfile(os.path.join(abs_d, sample)):
                        return abs_d
                skip = {"__pycache__", "outputs", "models", ".git", ".venv",
                        "venv", "cache", "shared", "web", "static", "plugins"}
                for root, dirs, files in os.walk(cwd):
                    dirs[:] = [d for d in sorted(dirs)
                               if d not in skip and not d.startswith(".")]
                    rel = os.path.relpath(root, cwd)
                    depth = 0 if rel == "." else len(rel.split(os.sep))
                    if depth == 0: continue
                    if depth > 3:
                        dirs.clear()
                        continue
                    if sample in files:
                        return os.path.abspath(root)
            self_raw = getattr(self, "lora_dir", "") or ""
            if self_raw:
                abs_d = os.path.abspath(self_raw)
                cwd   = os.getcwd()
                if abs_d != cwd and os.path.isdir(abs_d):
                    return abs_d
            return ""

        def resolve_lora_dir_always(state_val=None) -> str:
            """Returns the lora dir for the current model, even if empty/nonexistent.
            Trusts get_lora_dir() unconditionally — no filesystem fallback — so that
            switching to a model with no loras does not return another model's directory."""
            get_ld  = getattr(self, "get_lora_dir",         None)
            get_smt = getattr(self, "get_state_model_type", None)
            if get_ld is not None and get_smt is not None and state_val is not None:
                try:
                    model_type = get_smt(state_val)
                    if model_type:
                        path = get_ld(model_type)
                        if path:
                            return os.path.abspath(path)
                except Exception:
                    pass
            # Only fall back to filesystem scan if we have no state info at all
            if state_val is None:
                return resolve_lora_dir(state_val)
            return ""

        def resolve_lora_dir_for_model_type(model_type) -> str:
            get_ld = getattr(self, "get_lora_dir", None)
            if get_ld is not None and model_type:
                try:
                    path = get_ld(model_type)
                    if path:
                        return os.path.abspath(path)
                except Exception:
                    pass
            return ""

        def live_loras(lora_dir: str = "") -> list:
            if lora_dir:
                scanned = _scan_dir(lora_dir)
                return scanned
            if loras_comp is not None:
                try:
                    choices = loras_comp.choices or []
                    if choices:
                        names = [c[0] if isinstance(c, (list, tuple)) else c for c in choices]
                        names = [n for n in names if isinstance(n, str) and n.strip()]
                        if names:
                            return names
                except Exception:
                    pass
            names = getattr(self, "loras_names", None)
            if isinstance(names, list):
                return [n for n in names if isinstance(n, str) and n.strip()]
            return []

        def lora_val(real_name: str) -> str:
            if loras_comp is None:
                return real_name
            try:
                for c in (loras_comp.choices or []):
                    if isinstance(c, (list, tuple)) and c[0] == real_name:
                        return str(c[1])
                    elif c == real_name:
                        return real_name
            except Exception:
                pass
            return real_name

        # ── Bootstrap ─────────────────────────────────────────────────

        init_lora_dir  = resolve_lora_dir_always()
        init_data      = _load_data(init_lora_dir)
        init_settings  = _load_settings()
        init_view_mode = _normalize_lora_view_mode(init_settings.get("lora_view_mode"))
        init_thumbnail_columns = init_settings.get("thumbnail_columns", 3)
        init_thumbnail_fit_without_cropping = init_settings.get("thumbnail_fit_without_cropping", False)
        init_thumbnail_cycle_mode = init_settings.get("thumbnail_cycle_mode", THUMB_CYCLE_HOVER)
        init_auto_sort_mode = init_settings.get("lora_auto_sort_mode", AUTO_SORT_NONE)
        init_placement_mode = init_settings.get("placement_mode", PLACEMENT_LORA_TAB)
        init_remove_trigger_words_on_deactivate = init_settings.get("remove_trigger_words_on_deactivate", False)
        init_horiz     = _is_horizontal_view_mode(init_view_mode)
        init_side      = init_settings.get("side_by_side", True)
        init_groups_max_width = init_settings.get("groups_max_width", 0)
        init_trigger_words_mode = init_settings.get("trigger_words_mode", DEFAULT_TRIGGER_WORDS_MODE)
        init_height    = init_settings.get("listbox_height", DEFAULT_LISTBOX_HEIGHT)
        init_acc_open  = init_settings.get("accordion_open", False)
        init_meta_acc_open = init_settings.get("metadata_accordion_open", False)
        init_hide_all  = init_settings.get("hide_all_group", False)
        init_all_loras = live_loras()
        init_grp       = init_data.get("last_group", ALL_GROUP)
        if init_grp not in [ALL_GROUP] + _group_names(init_data):
            init_grp = ALL_GROUP
            init_data["last_group"] = ALL_GROUP
        init_grp       = _visible_selected_group(init_data, init_grp, init_hide_all)
        init_choices   = _group_choices(init_data)
        init_grp_val   = _find_choice_val(init_choices, init_grp)
        init_lora_list = _loras_for_group(init_data, init_grp, init_all_loras)
        init_lo_radio  = _lora_choices_for_radio(init_data, init_lora_list)
        init_has_group = _is_real_group_selected(init_grp)
        init_has_lora  = bool(init_lo_radio)
        init_sel_lora  = _pick_selected_lora(init_settings, init_lora_dir, init_grp, init_lo_radio)
        init_lora_html = _lora_list_html(
            init_data, init_lora_list, init_sel_lora,
            reveal_selected=True, view_mode=init_view_mode,
            thumbnail_columns=init_thumbnail_columns,
        )
        init_active_loras = []
        if loras_comp is not None:
            try:
                init_active_loras = list(getattr(loras_comp, "value", []) or [])
            except Exception:
                init_active_loras = []
        init_active_mult = ""
        if mult_comp is not None:
            try:
                init_active_mult = str(getattr(mult_comp, "value", "") or "")
            except Exception:
                init_active_mult = ""
        init_active_selected = init_active_loras[0] if init_active_loras else None
        init_active_html = _activated_loras_html(
            init_lora_dir, init_active_loras, init_active_mult, init_all_loras, init_active_selected
        )
        up_lbl, dn_lbl = _group_move_labels_explicit()

        # ── UI ────────────────────────────────────────────────────────

        organizer_wrapper = (
            gr.Accordion("🗂️ Lora Organizer", open=init_acc_open, elem_id="lo_accordion")
            if init_placement_mode != PLACEMENT_OWN_TAB
            else gr.Column(elem_id="lo_accordion")
        )
        with organizer_wrapper:

            gr.HTML(f"<style>{_CSS_BASE}</style>", elem_id="lo_style_block")
            gr.HTML(_icon_css_block(), elem_id="lo_icon_style_block")
            gr.HTML(_group_indent_js(), elem_id="lo_group_indent_block")
            orient_html = gr.HTML(_orient_html(init_horiz), elem_id="lo_orient_style",
                                  visible=False)
            thumbnail_fit_html = gr.HTML(
                _thumbnail_fit_css(init_thumbnail_fit_without_cropping),
                elem_id="lo_thumbnail_fit_style",
                visible=False,
            )
            groups_width_html = gr.HTML(_groups_column_css(init_groups_max_width), elem_id="lo_groups_width_style",
                                        visible=False)
            height_html = gr.HTML(_listbox_height_css(init_height), elem_id="lo_height_style",
                                  visible=False)
            gr.HTML("<div style='height:2px;line-height:0;font-size:0'></div>")
            gr.HTML("<div style='font-size:.8rem;font-weight:600;"
                    "margin:0 0 2px;opacity:.65;letter-spacing:.04em'>"
                    "ACTIVATED LORAS</div>")
            activated_list_html = gr.HTML(init_active_html, elem_id="lo_active_list_html")

            # ── Use / Use Both / Edit buttons ─────────────────────────
            with gr.Row():
                btn_use      = gr.Button("⚡ Activate Lora",  size="sm", min_width=0,
                                         elem_id="lo_btn_use",
                                         interactive=init_has_lora)
                btn_use_both = gr.Button("🔛 Activate High & Low", size="sm", min_width=0,
                                         elem_id="lo_btn_use_both", visible=False)
                btn_clear_all = gr.Button("❌ Clear Activated Loras", size="sm", min_width=0,
                                          elem_id="lo_btn_clear_all",
                                          interactive=bool(init_active_loras))
                btn_reorder_loras = gr.Button("↕️ Sort Loras", size="sm", min_width=0,
                                              elem_id="lo_btn_reorder_loras",
                                              interactive=init_has_lora)

            with gr.Row(visible=False) as lora_manage_row:
                auto_sort_dd = gr.Dropdown(
                    choices=[AUTO_SORT_NONE, AUTO_SORT_NAME, AUTO_SORT_MOST_USED],
                    value=init_auto_sort_mode,
                    label="",
                    show_label=False,
                    interactive=True,
                    scale=2,
                    min_width=0,
                )
                btn_lora_sort = gr.Button("🔤 Sort By Name", size="sm", min_width=0,
                                          interactive=False, elem_id="lo_btn_lora_sort")
                btn_lora_sort_used = gr.Button("🔥 Sort By Most Used", size="sm", min_width=0,
                                               interactive=False, elem_id="lo_btn_lora_sort_used")
                btn_lora_done = gr.Button("✔ Done", size="sm", min_width=0, variant="primary",
                                          elem_id="lo_btn_lora_done")

            # ── Groups + Loras lists ───────────────────────────────────
            if init_side:
                with gr.Row(elem_id="lo_lists_row"):
                    with gr.Column(elem_id="lo_groups_col"):
                        gr.HTML("<div style='font-size:.8rem;font-weight:600;"
                                "margin:4px 0 2px;opacity:.65;letter-spacing:.04em'>"
                                "GROUPS</div>")
                        grp_radio = gr.Radio(choices=init_choices,
                                             value=init_grp_val, label="", show_label=False,
                                             elem_id="lo_grp_radio")
                    with gr.Column(elem_id="lo_loras_col"):
                        gr.HTML("<div style='font-size:.8rem;font-weight:600;"
                                "margin:4px 0 2px;opacity:.65;letter-spacing:.04em'>"
                                "LORAS IN GROUP</div>")
                        lora_list_html = gr.HTML(init_lora_html, elem_id="lo_lora_list_html")
            else:
                gr.HTML("<div style='font-size:.8rem;font-weight:600;"
                        "margin:4px 0 2px;opacity:.65;letter-spacing:.04em'>"
                        "GROUPS</div>")
                grp_radio = gr.Radio(choices=init_choices,
                                     value=init_grp_val, label="", show_label=False,
                                     elem_id="lo_grp_radio")
                gr.HTML("<hr style='margin:6px 0;opacity:.2'>")
                gr.HTML("<div style='font-size:.8rem;font-weight:600;"
                        "margin:4px 0 2px;opacity:.65;letter-spacing:.04em'>"
                        "LORAS IN GROUP</div>")
                lora_list_html = gr.HTML(init_lora_html, elem_id="lo_lora_list_html")

            global _STATIC_FILE_BLOCK
            _STATIC_FILE_BLOCK = lora_list_html

            # ── Group action buttons ───────────────────────────────────
            with gr.Row():
                btn_add    = gr.Button("➕ Add Group", size="sm", min_width=0,
                                       elem_id="lo_btn_add_group")
                btn_add_sub = gr.Button("↳ Add Sub-Group", size="sm", min_width=0,
                                        interactive=init_has_group, elem_id="lo_btn_add_sub_group")
                btn_manage_group = gr.Button("🗂️ Manage Group", size="sm", min_width=0,
                                             interactive=init_has_group, elem_id="lo_btn_manage_group")
                btn_assign = gr.Button("📋 Assign Loras To Group", size="sm", min_width=0,
                                       interactive=init_has_group, elem_id="lo_btn_assign")

            with gr.Row(visible=False) as group_manage_row:
                btn_rename = gr.Button("✏️ Rename Group", size="sm", min_width=0,
                                       interactive=init_has_group, elem_id="lo_btn_rename_group")
                btn_del    = gr.Button("🗑️ Delete Group", size="sm", min_width=0,
                                       interactive=init_has_group, elem_id="lo_btn_delete_group")
                btn_up     = gr.Button(up_lbl, size="sm", min_width=0, interactive=False,
                                       elem_id="lo_btn_move_up")
                btn_down   = gr.Button(dn_lbl, size="sm", min_width=0, interactive=False,
                                       elem_id="lo_btn_move_down")
                btn_group_done = gr.Button("✔ Done", size="sm", min_width=0, variant="primary",
                                           elem_id="lo_btn_group_done")

            with gr.Row(visible=False) as del_confirm_row:
                gr.HTML("<span style='font-size:.9rem;align-self:center;padding-right:8px'>"
                        "Delete this group?</span>")
                btn_del_yes = gr.Button("✔ Yes, Delete", variant="stop", size="sm",
                                        min_width=0, elem_id="lo_btn_del_yes")
                btn_del_no  = gr.Button("✖ Cancel", size="sm", min_width=0,
                                        elem_id="lo_btn_del_no")

            with gr.Column(visible=False) as grp_name_section:
                new_grp_tb = gr.Textbox(label="Group name", placeholder="Enter group name…")
                with gr.Row():
                    btn_confirm    = gr.Button("✔ Confirm", variant="primary",
                                               size="sm", min_width=0, elem_id="lo_btn_confirm")
                    btn_cancel_grp = gr.Button("✖ Cancel", size="sm", min_width=0,
                                               elem_id="lo_btn_cancel_grp")

            assign_dd = gr.Dropdown(
                choices=_assign_choices(init_all_loras), value=None,
                label="Select loras to assign to this group",
                multiselect=True, visible=False, interactive=True,
            )
            with gr.Row(visible=False) as assign_row:
                btn_save_assign   = gr.Button("💾 Save Assignment", variant="primary",
                                              size="sm", elem_id="lo_btn_save_assign")
                btn_cancel_assign = gr.Button("✖ Cancel", size="sm",
                                              elem_id="lo_btn_cancel_assign")

            # ── Lora detail fields ─────────────────────────────────────
            with gr.Accordion("📝 Lora Metadata", open=init_meta_acc_open, elem_id="lo_metadata_accordion") as metadata_accordion:
                with gr.Row(equal_height=True, elem_id="lo_name_row"):
                    with gr.Column(scale=1, min_width=0, elem_id="lo_disp_name_col"):
                        disp_name_tb = gr.Textbox(label="Display Name",
                                                  placeholder="Leave empty to use the real filename",
                                                  interactive=True,
                                                  scale=1, min_width=0)
                    with gr.Column(scale=1, min_width=0):
                        real_name_tb = gr.Textbox(label="Real Name",
                                                  interactive=False,
                                                  elem_id="lo_real_name_tb",
                                                  scale=1, min_width=0)
                tw_tb   = gr.Textbox(label="Trigger Words",
                                     placeholder="e.g. ohwx, cinematic", interactive=True)
                str_tb  = gr.Textbox(label="Default Strength", value="1",
                                     placeholder="e.g. 1  or  1;0  or  0;1", interactive=True)
                info_tb = gr.Textbox(label="Info / Notes", lines=3,
                                 placeholder="Any notes about this lora…", interactive=True)

                with gr.Row(equal_height=True, elem_id="lo_url_row"):
                    url_tb = gr.Textbox(label="Lora URL", placeholder="No URL set for this lora",
                                        interactive=True, elem_id="lo_url_tb",
                                        scale=5, min_width=0)
                    btn_open_url = gr.Button("🔗 Open URL", size="sm", elem_id="lo_btn_open_url",
                                             visible=False, scale=1, min_width=0)
                url_btn_row = btn_open_url
                preview_gallery = gr.Gallery(
                    label="Preview Images",
                    value=_preview_gallery_value(init_sel_lora, init_lora_dir),
                    columns=4,
                    object_fit="cover",
                    height="auto",
                    interactive=False,
                    visible=bool(_preview_gallery_value(init_sel_lora, init_lora_dir)),
                    show_label=True,
                    elem_id="lo_preview_gallery",
                )
                preview_upload = gr.File(
                    label="Add Preview Images",
                    file_count="multiple",
                    file_types=["image"],
                    type="filepath",
                    interactive=True,
                    visible=False,
                    elem_id="lo_preview_upload",
                )
                with gr.Row(visible=bool(init_sel_lora)) as preview_manage_row:
                    btn_preview_add = gr.Button("➕ Add Preview Images", size="sm", min_width=0,
                                                interactive=bool(init_sel_lora), elem_id="lo_btn_preview_add")
                    btn_preview_left = gr.Button("◀", size="sm", min_width=0,
                                                 interactive=False, elem_id="lo_btn_preview_left")
                    btn_preview_right = gr.Button("▶", size="sm", min_width=0,
                                                  interactive=False, elem_id="lo_btn_preview_right")
                    btn_preview_remove = gr.Button("🗑️ Remove", size="sm", min_width=0,
                                                   interactive=False, elem_id="lo_btn_preview_remove")
                    btn_preview_clear = gr.Button("❌ Clear All", size="sm", min_width=0,
                                                  interactive=False, elem_id="lo_btn_preview_clear")

            with gr.Row(visible=False) as edit_row:
                btn_save_edit   = gr.Button("✔ Save Changes",   variant="primary", size="sm",
                                            elem_id="lo_btn_save_edit")
                btn_cancel_edit = gr.Button("✖ Cancel", size="sm", elem_id="lo_btn_cancel_edit")

            # ── Settings ──────────────────────────────────────────────
            with gr.Accordion("⚙️ Settings", open=False, elem_id="lo_settings_accordion"):
                placement_mode_dd = gr.Dropdown(
                    choices=[PLACEMENT_MAIN, PLACEMENT_LORA_TAB, PLACEMENT_OWN_TAB],
                    value=init_placement_mode,
                    label="Lora Organizer placement (requires restart)",
                    interactive=True,
                )
                trigger_words_dd = gr.Dropdown(
                    choices=[
                        TRIGGER_WORDS_PREPEND,
                        TRIGGER_WORDS_APPEND,
                        TRIGGER_WORDS_REPLACE,
                        TRIGGER_WORDS_NONE,
                    ],
                    value=init_trigger_words_mode,
                    label="Trigger words behavior when using a lora",
                    interactive=True,
                )
                remove_tw_on_deactivate_cb = gr.Checkbox(
                    value=init_remove_trigger_words_on_deactivate,
                    label="Remove trigger words from the prompt when deactivating loras",
                )
                view_mode_dd = gr.Dropdown(
                    choices=[LORA_VIEW_VERTICAL, LORA_VIEW_HORIZONTAL, LORA_VIEW_THUMBNAIL],
                    value=init_view_mode,
                    label="Lora list view mode",
                    interactive=True,
                )
                thumbnail_cycle_mode_dd = gr.Dropdown(
                    choices=[THUMB_CYCLE_HOVER, THUMB_CYCLE_AUTO, THUMB_CYCLE_NONE],
                    value=init_thumbnail_cycle_mode,
                    label="Thumbnail image cycling",
                    interactive=True,
                )
                thumbnail_cols_sl = gr.Slider(
                    minimum=1, maximum=8, step=1,
                    value=init_thumbnail_columns,
                    label="Thumbnails per row",
                )
                thumbnail_fit_cb = gr.Checkbox(
                    value=init_thumbnail_fit_without_cropping,
                    label="Fit thumbnail images without cropping",
                )
                groups_max_width_sl = gr.Slider(
                    minimum=0, maximum=600, step=10,
                    value=init_groups_max_width,
                    label="Groups listbox max width in side-by-side view (0 = 50/50 split)",
                )
                height_sl       = gr.Slider(minimum=100, maximum=800, step=10,
                                            value=init_height, label="Listbox max height (px)")
                acc_open_cb     = gr.Checkbox(value=init_acc_open,
                                              label="Start with Lora Organizer expanded")
                meta_acc_open_cb = gr.Checkbox(value=init_meta_acc_open,
                                               label="Start with Lora Metadata expanded")
                hide_all_cb     = gr.Checkbox(value=init_hide_all,
                                              label='Hide "All" group')
                side_cb         = gr.Checkbox(value=init_side,
                                              label="Arrange group and lora listboxes side by side (requires restart)")
                btn_save_settings = gr.Button("💾 Save Settings", size="sm", variant="primary",
                                              elem_id="lo_btn_save_settings")

            with gr.Column(visible=False):
                lora_radio = gr.Textbox(value=init_sel_lora or "", elem_id="lo_lora_radio")
                lora_select_dispatch = gr.Button("dispatch", elem_id="lo_lora_select_dispatch")
                lora_ui_action = gr.Textbox(value="", elem_id="lo_lora_ui_action")
                lora_ui_dispatch = gr.Button("dispatch", elem_id="lo_lora_ui_dispatch")
                active_ui_action = gr.Textbox(value="", elem_id="lo_active_ui_action")
                active_ui_dispatch = gr.Button("dispatch", elem_id="lo_active_ui_dispatch")

            st_dir    = gr.State(init_lora_dir)
            st_action = gr.State("add")
            st_loras  = gr.State(init_all_loras)
            st_sel_lora = gr.State(init_sel_lora)
            st_preview_work = gr.State(_preview_gallery_value(init_sel_lora, init_lora_dir))
            st_preview_index = gr.State(None)
            st_clear_loras = gr.State([])
            st_clear_mult = gr.State("")
            st_clear_prompt = gr.State("")
            st_clear_mode = gr.State(False)
            st_clear_expected = gr.State(None)
            st_active_apply_loras = gr.State(None)
            st_active_apply_mult = gr.State(None)
            st_active_reorder_pending = gr.State(False)
            st_active_selected = gr.State(init_active_selected)


        # ==============================================================
        # Inner helpers
        # ==============================================================

        def _btn_states(grp: str, groups: list):
            grp = _grp_name(grp)
            if not grp or grp == ALL_GROUP:
                return tuple(gr.update(interactive=False) for _ in range(5))
            normalized = [
                g if isinstance(g, dict) else {"name": g, "parent": None, "level": 0}
                for g in groups
            ]
            names  = [g["name"] for g in normalized]
            in_grp = grp in names
            current = next((g for g in normalized if g["name"] == grp), None)
            siblings = [g["name"] for g in normalized
                        if current and g.get("parent") == current.get("parent")]
            idx    = siblings.index(grp) if in_grp and grp in siblings else -1
            n      = len(siblings)
            return (
                gr.update(interactive=in_grp),
                gr.update(interactive=in_grp),
                gr.update(interactive=in_grp and idx > 0),
                gr.update(interactive=in_grp and idx < n - 1),
                gr.update(interactive=in_grp),
            )

        def _preview_manage_updates(real_name: str, lora_dir: str, show_upload: bool = False):
            images = _preview_gallery_value(real_name, lora_dir)
            return _preview_manage_updates_from_images(real_name, images, None, show_upload)

        def _preview_manage_updates_from_images(real_name: str, images: list[str], selected_index: int | None = None,
                                                show_upload: bool = False):
            has_selection = bool(real_name)
            has_images = bool(images)
            valid_idx = selected_index if isinstance(selected_index, int) and 0 <= selected_index < len(images) else None
            return (
                gr.update(value=images, visible=has_images, selected_index=valid_idx),
                gr.update(value=None, visible=show_upload),
                gr.update(visible=has_selection),
                gr.update(visible=has_selection, interactive=has_selection),
                gr.update(visible=has_images, interactive=valid_idx is not None and valid_idx > 0),
                gr.update(visible=has_images, interactive=valid_idx is not None and valid_idx < len(images) - 1),
                gr.update(visible=has_images, interactive=valid_idx is not None),
                gr.update(visible=has_images, interactive=has_images),
            )

        def _metadata_updates(real_name: str, lora_dir: str, show_actions: bool = False):
            e   = _load_data(lora_dir)["loras"].get(real_name, {})
            url = (e.get("url") or "").strip()
            strength = e.get("default_strength")
            if real_name and strength is None:
                strength = _auto_strength(lora_dir, real_name)
            return (
                gr.update(value=e.get("display_name", ""),            interactive=True),
                gr.update(value=os.path.splitext(real_name)[0] if real_name else "", interactive=False),
                gr.update(value=e.get("trigger_words", ""),           interactive=True),
                gr.update(value=str(strength or "1"), interactive=True),
                gr.update(value=e.get("info", ""),                    interactive=True),
                gr.update(value=url, interactive=True, visible=True),
                gr.update(visible=bool(url)),   # btn_open_url
                *_preview_manage_updates(real_name, lora_dir, False),
                gr.update(visible=show_actions), # edit_row
            )

        def _do_refresh(state_val, forced_loras=None, forced_lora_dir=None, active_values=None, active_mult=""):
            lora_dir  = forced_lora_dir if forced_lora_dir is not None else resolve_lora_dir_always(state_val)
            # Use filesystem scan directly; forced_loras is already a scan result
            # from the caller. Never use live_loras() here to avoid stale choices fallback.
            cur_loras = forced_loras if forced_loras is not None else _scan_dir(lora_dir)
            data      = _load_data(lora_dir)
            settings  = _load_settings()
            # Only prune stale entries when we have a confirmed lora list
            if cur_loras:
                cur_set = set(cur_loras)
                removed = [k for k in list(data["loras"].keys()) if k not in cur_set]
                if removed:
                    for k in removed:
                        del data["loras"][k]
                    _save_data(lora_dir, data)
            last_grp = data.get("last_group", ALL_GROUP)
            if last_grp not in [ALL_GROUP] + _group_names(data):
                last_grp = ALL_GROUP
                data["last_group"] = ALL_GROUP
            last_grp   = _visible_selected_group(data, last_grp, settings.get("hide_all_group", False))
            loras_in   = _loras_for_group(data, last_grp, cur_loras)
            lo_choices = _lora_choices_for_radio(data, loras_in)
            bstates    = _btn_states(last_grp, data["groups"])
            has_lora   = bool(lo_choices)
            sel_lora   = _pick_selected_lora(settings, lora_dir, last_grp, lo_choices)
            return (
                gr.update(choices=(_lo_c:=_group_choices(data)), value=_find_choice_val(_lo_c, last_grp)),
                *bstates,
                gr.update(value=sel_lora or ""),
                gr.update(value=_lora_list_html(data, loras_in, sel_lora, reveal_selected=True)),
                gr.update(value=_activated_loras_html(lora_dir, active_values, active_mult, cur_loras)),
                gr.update(choices=_assign_choices(cur_loras), value=None, visible=False),
                *_metadata_updates(sel_lora, lora_dir, False),
                gr.update(value=settings.get("trigger_words_mode", DEFAULT_TRIGGER_WORDS_MODE)),
                gr.update(interactive=has_lora),  # btn_use
                _clear_button_update([], False),
                gr.update(interactive=has_lora),  # btn_reorder_loras
                gr.update(visible=False),         # lora_manage_row
                gr.update(interactive=False),     # btn_lora_sort
                gr.update(interactive=False),     # btn_lora_sort_used
                _manage_group_button_update(last_grp),                # btn_manage_group
                gr.update(visible=False),         # group_manage_row
                gr.update(interactive=_is_real_group_selected(last_grp)),  # btn_add_sub
                lora_dir,
                cur_loras,
                sel_lora,
                _preview_gallery_value(sel_lora, lora_dir),
                None,
                [],
                "",
                "",
                False,
                None,
            )

        _refresh_out = [
            grp_radio,
            btn_rename, btn_del, btn_up, btn_down, btn_assign,
            lora_radio, lora_list_html, activated_list_html, assign_dd,
            disp_name_tb, real_name_tb, tw_tb, str_tb, info_tb, url_tb, url_btn_row,
            preview_gallery, preview_upload, preview_manage_row,
            btn_preview_add, btn_preview_left, btn_preview_right, btn_preview_remove, btn_preview_clear,
            edit_row,
            trigger_words_dd, btn_use, btn_clear_all, btn_reorder_loras,
            lora_manage_row, btn_lora_sort, btn_lora_sort_used,
            btn_manage_group, group_manage_row, btn_add_sub,
            st_dir, st_loras, st_sel_lora, st_preview_work, st_preview_index,
            st_clear_loras, st_clear_mult, st_clear_prompt, st_clear_mode, st_clear_expected,
        ]

        # ==============================================================
        # Callbacks
        # ==============================================================

        _full_refresh_outputs = _refresh_out + [btn_use_both]

        _loras_change_outputs = [
            btn_use,
            activated_list_html,
            btn_clear_all,
            st_clear_loras,
            st_clear_mult,
            st_clear_mode,
            st_clear_expected,
            btn_use_both,
            st_active_apply_loras,
            st_active_apply_mult,
            st_active_reorder_pending,
            st_active_selected,
        ]

        if main_comp is not None and state_comp is not None:
            main_comp.load(fn=None, js=_lora_list_bind_js())
            main_comp.load(fn=lambda sv, act, mult: (*_do_refresh(sv, active_values=act, active_mult=mult), gr.update()),
                           inputs=[
                               state_comp,
                               loras_comp if loras_comp is not None else gr.State([]),
                               mult_comp if mult_comp is not None else gr.State(""),
                           ], outputs=_full_refresh_outputs,
                           js="""
                              (sv, act, mult) => {
                                  window.__loLoraScrollMode = 'ensure-selected';
                                  return [sv, act, mult];
                              }
                           """)

        def on_loras_change(loras_val, curr_mult, saved_dir, state_val, saved_loras, cur_sel_lora,
                            clear_mode, clear_expected, active_reorder_pending,
                            staged_active_loras, staged_active_mult, active_selected):
            pending = getattr(self, "_model_change_pending", False)
            pending_model_type = getattr(self, "_pending_model_type", None)
            if pending and pending_model_type:
                new_dir = resolve_lora_dir_for_model_type(pending_model_type)
            else:
                new_dir = resolve_lora_dir_always(state_val)
            cur_loras = _scan_dir(new_dir) if new_dir else []
            # Model changed — full refresh (btn_use_both handled separately below)
            if new_dir != saved_dir or cur_loras != saved_loras:
                self._model_change_pending = False
                self._pending_model_type = None
                return (
                    gr.update(),
                    gr.update(value=_activated_loras_html(new_dir or saved_dir, loras_val, curr_mult, cur_loras)),
                    _clear_button_update(list(loras_val) if loras_val else [], False),
                    [],
                    "",
                    False,
                    None,
                    gr.update(),
                )
            # Same model — re-evaluate btn_use and btn_use_both for current selection
            if pending:
                self._model_change_pending = False
                self._pending_model_type = None
            already = (cur_sel_lora is not None and
                       _lora_already_active(cur_sel_lora, loras_val))
            btn_use_upd = gr.update(interactive=bool(cur_sel_lora) and not already)
            display_active = list(loras_val) if loras_val else []
            display_mult = curr_mult
            if active_reorder_pending and not display_active and staged_active_loras is not None:
                display_active = list(staged_active_loras) if staged_active_loras else []
                display_mult = str(staged_active_mult or "")
            expected_active = list(clear_expected) if clear_expected else []
            clear_loras_upd = gr.skip()
            clear_mult_upd = gr.skip()
            clear_mode_upd = gr.skip()
            clear_expected_upd = gr.skip()
            active_html_upd = gr.update(value=_activated_loras_html(
                saved_dir, display_active, display_mult, cur_loras if cur_loras else _scan_dir(saved_dir), active_selected
            ))
            current_active = display_active
            active_selected_upd = gr.skip()
            if active_selected and str(active_selected) not in {str(v) for v in current_active}:
                active_selected_upd = current_active[0] if current_active else None
            if clear_mode:
                if current_active == expected_active:
                    btn_clear_upd = _clear_button_update(current_active, True)
                else:
                    btn_clear_upd = _clear_button_update(current_active, False)
                    clear_loras_upd = []
                    clear_mult_upd = ""
                    clear_mode_upd = False
                    clear_expected_upd = None
            else:
                btn_clear_upd = _clear_button_update(current_active, False)
            # btn_use_both: only update if pair exists for current selection
            btn_both_upd = gr.update()  # no-op by default
            if cur_sel_lora:
                all_l = cur_loras if cur_loras else _scan_dir(saved_dir)
                high, low = _find_pair(cur_sel_lora, all_l, saved_dir)
                if high and low:
                    both_disabled = (_lora_already_active(high, loras_val) and
                                     _lora_already_active(low, loras_val))
                    btn_both_upd = gr.update(interactive=not both_disabled)
            staged_loras_upd = gr.skip()
            staged_mult_upd = gr.skip()
            active_pending_upd = gr.skip()
            if active_reorder_pending and staged_active_loras is not None:
                staged_now = list(staged_active_loras) if staged_active_loras else []
                if list(loras_val or []) == staged_now and str(curr_mult or "") == str(staged_active_mult or ""):
                    active_html_upd = gr.skip()
                    staged_loras_upd = None
                    staged_mult_upd = None
                    active_pending_upd = False
            return (
                btn_use_upd,
                active_html_upd,
                btn_clear_upd,
                clear_loras_upd,
                clear_mult_upd,
                clear_mode_upd,
                clear_expected_upd,
                btn_both_upd,
                staged_loras_upd,
                staged_mult_upd,
                active_pending_upd,
                active_selected_upd,
            )

        if loras_comp is not None:
            loras_comp.change(fn=on_loras_change,
                              inputs=[loras_comp, mult_comp if mult_comp is not None else gr.State(""), st_dir,
                                      state_comp if state_comp is not None else gr.State(None),
                                      st_loras, st_sel_lora, st_clear_mode, st_clear_expected,
                                      st_active_reorder_pending, st_active_apply_loras, st_active_apply_mult, st_active_selected],
                              outputs=_loras_change_outputs,
                              show_progress="hidden")

        if mult_comp is not None:
            mult_comp.change(fn=on_loras_change,
                             inputs=[loras_comp if loras_comp is not None else gr.State([]),
                                     mult_comp, st_dir,
                                     state_comp if state_comp is not None else gr.State(None),
                                     st_loras, st_sel_lora, st_clear_mode, st_clear_expected,
                                     st_active_reorder_pending, st_active_apply_loras, st_active_apply_mult, st_active_selected],
                             outputs=_loras_change_outputs,
                             show_progress="hidden")

        if state_comp is not None:
            state_comp.change(fn=lambda act, mult, sv: (*_do_refresh(sv, active_values=act, active_mult=mult), gr.update()),
                              inputs=[loras_comp if loras_comp is not None else gr.State([]),
                                      mult_comp if mult_comp is not None else gr.State(""),
                                      state_comp],
                              outputs=_full_refresh_outputs)

        # ── Group radio change ─────────────────────────────────────────
        def on_grp_change(grp, saved_dir, cur_loras, curr_act):
            grp = _grp_name(grp)
            data = _load_data(saved_dir)
            old_grp_choices = _group_choices(data)
            data["last_group"] = grp
            _save_data(saved_dir, data)
            all_l      = cur_loras if cur_loras else live_loras(saved_dir)
            loras      = _loras_for_group(data, grp, all_l)
            lo_choices = _lora_choices_for_radio(data, loras)
            has_lora   = bool(lo_choices)
            # Restore last used lora for this group (stored safely in Settings.json)
            settings  = _load_settings()
            key       = _last_used_key(saved_dir)
            last_used = settings.get(key, {}).get(grp) if key else None
            if last_used and any(c[1] == last_used for c in lo_choices):
                sel_lora = last_used
            else:
                sel_lora = lo_choices[0][1] if lo_choices else None
            already = sel_lora is not None and _lora_already_active(sel_lora, curr_act)
            # Check btn_use_both state for the restored lora
            has_pair     = False
            both_disabled = True
            if sel_lora:
                high, low = _find_pair(sel_lora, all_l, saved_dir)
                has_pair  = (high is not None and low is not None)
                if has_pair:
                    both_disabled = (_lora_already_active(high, curr_act) and
                                     _lora_already_active(low, curr_act))
            lora_sort_u, lora_sort_used_u, lora_done_u = _lora_sort_ui_updates(
                sel_lora, grp, data, all_l, settings.get("lora_auto_sort_mode", AUTO_SORT_NONE)
            )
            new_grp_choices = _group_choices(data)
            grp_update = (
                gr.skip()
                if old_grp_choices == new_grp_choices
                else gr.update(choices=new_grp_choices, value=_find_choice_val(new_grp_choices, grp))
            )
            return (
                *_btn_states(grp, data["groups"]),
                gr.update(value=sel_lora or ""),
                gr.update(value=_lora_list_html(data, loras, sel_lora, reveal_selected=True)),
                gr.update(interactive=has_lora and not already),          # btn_use
                _clear_button_update(curr_act or [], False),              # btn_clear_all
                gr.update(interactive=has_lora),                          # btn_reorder_loras
                gr.update(visible=False),                                 # edit_row
                gr.update(visible=False),                                 # lora_manage_row
                lora_sort_u,
                lora_sort_used_u,
                lora_done_u,
                gr.update(visible=has_pair, interactive=not both_disabled),# btn_use_both
                grp_update,
                _manage_group_button_update(grp),                         # btn_manage_group
                gr.update(visible=False),                                 # group_manage_row
                gr.update(interactive=_is_real_group_selected(grp)),      # btn_add_sub
                saved_dir,
                sel_lora,
            )

        _curr_act_input = loras_comp if loras_comp is not None else gr.State([])
        grp_radio.change(fn=on_grp_change,
                         inputs=[grp_radio, st_dir, st_loras, _curr_act_input],
                         outputs=[btn_rename, btn_del, btn_up, btn_down, btn_assign,
                                  lora_radio, lora_list_html, btn_use, btn_clear_all, btn_reorder_loras, edit_row,
                                  lora_manage_row, btn_lora_sort, btn_lora_sort_used, btn_lora_done,
                                  btn_use_both, grp_radio, btn_manage_group, group_manage_row,
                                  btn_add_sub, st_dir, st_sel_lora],
                         show_progress="hidden",
                         js="""
                            (grp, savedDir, curLoras, currAct) => {
                                if (window.__loPrepareGroupReveal) {
                                    window.__loPrepareGroupReveal();
                                }
                                return [grp, savedDir, curLoras, currAct];
                            }
                         """)

        def _lora_already_active(real_name: str, curr_act) -> bool:
            val = lora_val(real_name)
            activated = list(curr_act) if curr_act else []
            return val in activated

        # ── Lora radio change ──────────────────────────────────────────
        def on_lora_change(real_name, saved_dir, cur_loras, curr_act):
            settings = _load_settings()
            if not real_name:
                return (
                    gr.update(value=""),
                    *_metadata_updates("", saved_dir, False),
                    gr.update(visible=False, interactive=False),  # btn_use_both
                    gr.update(interactive=False),  # btn_use
                    _clear_button_update(curr_act or [], False),  # btn_clear_all
                    gr.update(interactive=False),  # btn_reorder_loras
                    gr.update(interactive=False),  # btn_lora_sort
                    gr.update(interactive=False),  # btn_lora_sort_used
                    gr.update(interactive=False),  # btn_lora_done
                    saved_dir,
                    None,
                    [],
                    None,
                )
            data     = _load_data(saved_dir)
            e        = data["loras"].get(real_name, {})
            strength = e.get("default_strength")
            if strength is None:
                strength = _auto_strength(saved_dir, real_name)
            url = (e.get("url") or "").strip()
            all_l = cur_loras if cur_loras else live_loras(saved_dir)
            high, low = _find_pair(real_name, all_l, saved_dir)
            has_pair  = (high is not None and low is not None)
            already   = _lora_already_active(real_name, curr_act)
            # btn_use_both: shown only if pair exists; disabled if BOTH already active
            both_disabled = (has_pair and
                             _lora_already_active(high, curr_act) and
                             _lora_already_active(low, curr_act))
            sort_u, sort_used_u, done_u = _lora_sort_ui_updates(
                real_name, _load_data(saved_dir).get("last_group", ALL_GROUP), data, all_l,
                settings.get("lora_auto_sort_mode", AUTO_SORT_NONE)
            )
            return (
                gr.update(value=real_name),
                *_metadata_updates(real_name, saved_dir, False),
                gr.update(visible=has_pair, interactive=not both_disabled),  # btn_use_both
                gr.update(interactive=not already),                            # btn_use
                _clear_button_update(curr_act or [], False),                   # btn_clear_all
                gr.update(interactive=True),                                   # btn_reorder_loras
                sort_u, sort_used_u, done_u,
                saved_dir, real_name,
                _preview_gallery_value(real_name, saved_dir),
                None,
            )

        _curr_act_input = loras_comp if loras_comp is not None else gr.State([])
        lora_select_dispatch.click(fn=on_lora_change,
                                   inputs=[lora_radio, st_dir, st_loras, _curr_act_input],
                                   outputs=[lora_radio, disp_name_tb, real_name_tb, tw_tb, str_tb, info_tb,
                                            url_tb, url_btn_row, preview_gallery, preview_upload, preview_manage_row,
                                            btn_preview_add, btn_preview_left, btn_preview_right, btn_preview_remove, btn_preview_clear,
                                            edit_row, btn_use_both,
                                            btn_use, btn_clear_all, btn_reorder_loras,
                                            btn_lora_sort, btn_lora_sort_used, btn_lora_done,
                                            st_dir, st_sel_lora, st_preview_work, st_preview_index],
                                   show_progress="hidden")

        def on_lora_ui_action(payload, saved_dir, cur_loras, curr_act, grp, curr_selected):
            try:
                action = json.loads(payload or "{}")
            except Exception:
                return (gr.update(),) * 26
            kind = action.get("action")
            real_name = action.get("value")
            data = _load_data(saved_dir)
            settings = _load_settings()
            grp = _grp_name(grp)
            all_l = cur_loras if cur_loras else live_loras(saved_dir)
            loras = _loras_for_group(data, grp, all_l)
            if kind == "reorder" and settings.get("lora_auto_sort_mode", AUTO_SORT_NONE) == AUTO_SORT_NONE:
                new_order = [name for name in action.get("order", []) if name in loras]
                if set(new_order) == set(loras) and new_order:
                    _set_lora_order(data, grp, new_order)
                    _save_data(saved_dir, data)
                    loras = new_order
                real_name = curr_selected
            if real_name not in loras:
                real_name = loras[0] if loras else None
            if not real_name:
                return (
                    gr.update(value=""),
                    *_metadata_updates("", saved_dir, False),
                    gr.update(visible=False, interactive=False),
                    gr.update(interactive=False),
                    _clear_button_update(curr_act or [], False),
                    gr.update(interactive=False),
                    gr.update(interactive=False),
                    gr.update(interactive=False),
                    gr.update(interactive=False),
                    saved_dir,
                    None,
                    [],
                    None,
                )
            e = data["loras"].get(real_name, {})
            strength = e.get("default_strength")
            if strength is None:
                strength = _auto_strength(saved_dir, real_name)
            url = (e.get("url") or "").strip()
            high, low = _find_pair(real_name, all_l, saved_dir)
            has_pair = (high is not None and low is not None)
            already = _lora_already_active(real_name, curr_act)
            both_disabled = (has_pair and
                             _lora_already_active(high, curr_act) and
                             _lora_already_active(low, curr_act))
            sort_u, sort_used_u, done_u = _lora_sort_ui_updates(
                real_name, grp, data, all_l, settings.get("lora_auto_sort_mode", AUTO_SORT_NONE)
            )
            return (
                gr.update(value=real_name),
                *_metadata_updates(real_name, saved_dir, False),
                gr.update(visible=has_pair, interactive=not both_disabled),
                gr.update(interactive=not already),
                _clear_button_update(curr_act or [], False),
                gr.update(interactive=True),
                sort_u,
                sort_used_u,
                done_u,
                saved_dir,
                real_name,
                _preview_gallery_value(real_name, saved_dir),
                None,
            )

        lora_ui_dispatch.click(
            fn=on_lora_ui_action,
            inputs=[lora_ui_action, st_dir, st_loras, _curr_act_input, grp_radio, lora_radio],
            outputs=[lora_radio, disp_name_tb, real_name_tb, tw_tb, str_tb, info_tb,
                     url_tb, url_btn_row, preview_gallery, preview_upload, preview_manage_row,
                     btn_preview_add, btn_preview_left, btn_preview_right, btn_preview_remove, btn_preview_clear,
                     edit_row, btn_use_both,
                     btn_use, btn_clear_all, btn_reorder_loras,
                     btn_lora_sort, btn_lora_sort_used, btn_lora_done,
                     st_dir, st_sel_lora, st_preview_work, st_preview_index],
            show_progress="hidden"
        )

        # ── Add / Rename Group ─────────────────────────────────────────
        def on_active_ui_action(payload, curr_act, curr_mult, curr_prompt, saved_dir, cur_loras, current_selected):
            try:
                action = json.loads(payload or "{}")
            except Exception:
                return gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip()

            values = list(curr_act) if curr_act else []
            strengths = _split_multiplier_values(curr_mult)
            while len(strengths) < len(values):
                strengths.append("")
            prompt_text = curr_prompt or ""

            kind = action.get("action")
            try:
                idx = int(action.get("index", -1))
            except Exception:
                idx = -1
            value = action.get("value")
            selected = current_selected

            if kind == "select":
                return gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), value

            if kind == "reorder":
                order = action.get("order") or []
                value_keys = {str(x) for x in values}
                order_keys = [str(v) for v in order if str(v) in value_keys]
                if not order_keys:
                    return gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip()
                used = set()
                reordered_values = []
                reordered_strengths = []
                value_pairs = list(zip(values, strengths[:len(values)]))
                for key in order_keys:
                    for pair_idx, (val, strength) in enumerate(value_pairs):
                        if pair_idx in used:
                            continue
                        if str(val) == key:
                            used.add(pair_idx)
                            reordered_values.append(val)
                            reordered_strengths.append(strength)
                            break
                for pair_idx, (val, strength) in enumerate(value_pairs):
                    if pair_idx in used:
                        continue
                    reordered_values.append(val)
                    reordered_strengths.append(strength)
                values = reordered_values
                strengths = reordered_strengths
                selected = current_selected
            else:
                if idx < 0 or idx >= len(values):
                    return gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip()

                if value and str(values[idx]) != str(value):
                    try:
                        idx = next(i for i, v in enumerate(values) if str(v) == str(value))
                    except StopIteration:
                        return gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip()

            if kind == "remove":
                removed_real_names = _active_values_to_real_names([values[idx]], saved_dir, cur_loras)
                del values[idx]
                if idx < len(strengths):
                    del strengths[idx]
                prompt_text = _remove_trigger_words_from_prompt(prompt_text, removed_real_names, saved_dir, cur_loras)
                if selected and str(selected) == str(value):
                    selected = values[idx] if idx < len(values) else (values[-1] if values else None)
            elif kind == "set_strength":
                new_strength = str(action.get("strength", "") or "").strip()
                if idx < len(strengths):
                    strengths[idx] = new_strength
                else:
                    while len(strengths) < idx:
                        strengths.append("")
                    strengths.append(new_strength)
            elif kind == "reorder":
                final_mult = " ".join(strengths[:len(values)])
                return gr.skip(), gr.skip(), gr.skip(), values, final_mult, True, selected
            else:
                return gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip()

            return values, " ".join(strengths[:len(values)]), prompt_text, gr.skip(), gr.skip(), False, selected

        def apply_active_reorder(staged_values, staged_mult):
            if staged_values is None:
                return gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip()
            values = list(staged_values) if staged_values else []
            mult = str(staged_mult or "")
            # Clear staged state and pending flag after applying so on_loras_change
            # does not stay in reorder-pending mode for subsequent loras changes.
            return values, mult, None, None, False

        if loras_comp is not None and mult_comp is not None:
            _active_ui_inputs = [active_ui_action, loras_comp, mult_comp]
            _active_ui_outputs = [loras_comp, mult_comp]
            if prompt_comp is not None:
                def _active_ui_wrapped(payload, curr_act, curr_mult, curr_prompt, saved_dir, cur_loras, current_selected):
                    return on_active_ui_action(payload, curr_act, curr_mult, curr_prompt, saved_dir, cur_loras, current_selected)

                _active_ui_fn = _active_ui_wrapped
                _active_ui_inputs.append(prompt_comp)
                _active_ui_outputs.append(prompt_comp)
            else:
                def _active_ui_wrapped(payload, curr_act, curr_mult, saved_dir, cur_loras, current_selected):
                    act, mult, _prompt, staged_loras, staged_mult, pending, selected = on_active_ui_action(
                        payload, curr_act, curr_mult, "", saved_dir, cur_loras, current_selected
                    )
                    return act, mult, staged_loras, staged_mult, pending, selected

                _active_ui_fn = _active_ui_wrapped
            _active_ui_inputs.extend([st_dir, st_loras, st_active_selected])
            _active_ui_outputs.extend([st_active_apply_loras, st_active_apply_mult, st_active_reorder_pending, st_active_selected])
            active_ui_dispatch.click(
                fn=_active_ui_fn,
                inputs=_active_ui_inputs,
                outputs=_active_ui_outputs,
                show_progress="hidden"
            ).then(
                fn=apply_active_reorder,
                inputs=[st_active_apply_loras, st_active_apply_mult],
                outputs=[loras_comp, mult_comp, st_active_apply_loras, st_active_apply_mult, st_active_reorder_pending],
                show_progress="hidden"
            )

        btn_add.click(fn=lambda: (gr.update(value=""), gr.update(visible=True), "add",
                                   gr.update(interactive=False),
                                   gr.update(interactive=False),
                                   gr.update(interactive=False),
                                   gr.update(interactive=False)),
                      outputs=[new_grp_tb, grp_name_section, st_action,
                               btn_add, btn_add_sub, btn_rename, btn_del])

        btn_manage_group.click(
            fn=lambda grp: gr.update(visible=_is_real_group_selected(grp)),
            inputs=[grp_radio], outputs=[group_manage_row]
        )
        btn_group_done.click(fn=lambda: gr.update(visible=False), outputs=[group_manage_row])

        btn_reorder_loras.click(
            fn=lambda real_name, grp, saved_dir, cur_loras: (
                (lambda updates: (gr.update(visible=True), updates[0], updates[1], updates[2]))(
                    _lora_sort_ui_updates(
                        real_name,
                        grp,
                        _load_data(saved_dir),
                        cur_loras if cur_loras else live_loras(saved_dir),
                        _load_settings().get("lora_auto_sort_mode", AUTO_SORT_NONE),
                    )
                )
            ),
            inputs=[lora_radio, grp_radio, st_dir, st_loras],
            outputs=[lora_manage_row, btn_lora_sort, btn_lora_sort_used, btn_lora_done]
        )

        auto_sort_dd.change(
            fn=lambda auto_sort_mode, real_name, grp, saved_dir, cur_loras: _lora_sort_ui_updates(
                real_name,
                grp,
                _load_data(saved_dir),
                cur_loras if cur_loras else live_loras(saved_dir),
                auto_sort_mode,
            ),
            inputs=[auto_sort_dd, lora_radio, grp_radio, st_dir, st_loras],
            outputs=[btn_lora_sort, btn_lora_sort_used, btn_lora_done]
        )

        def save_lora_sort_mode(auto_sort_mode, real_name, grp, saved_dir, cur_loras):
            settings = _load_settings()
            settings["lora_auto_sort_mode"] = auto_sort_mode
            _save_settings(settings)
            data = _load_data(saved_dir)
            all_l = cur_loras if cur_loras else live_loras(saved_dir)
            _apply_lora_auto_sort(data, all_l, auto_sort_mode)
            if auto_sort_mode in (AUTO_SORT_NAME, AUTO_SORT_MOST_USED):
                _save_data(saved_dir, data)
            grp = _grp_name(grp)
            loras = _loras_for_group(data, grp, all_l)
            selected = real_name if real_name in loras else (loras[0] if loras else None)
            sort_u, sort_used_u, done_u = _lora_sort_ui_updates(selected, grp, data, all_l, auto_sort_mode)
            return (
                gr.update(visible=False),
                gr.update(value=selected or ""),
                gr.update(value=_lora_list_html(data, loras, selected)),
                sort_u,
                sort_used_u,
                done_u,
                saved_dir,
                selected,
            )

        btn_lora_done.click(
            fn=save_lora_sort_mode,
            inputs=[auto_sort_dd, lora_radio, grp_radio, st_dir, st_loras],
            outputs=[lora_manage_row, lora_radio, lora_list_html, btn_lora_sort, btn_lora_sort_used, btn_lora_done, st_dir, st_sel_lora]
        )

        btn_add_sub.click(fn=lambda grp: (
                              gr.update(value=""),
                              gr.update(visible=bool(grp and grp != ALL_GROUP)),
                              "add_sub",
                              gr.update(interactive=False),
                              gr.update(interactive=False),
                              gr.update(interactive=False),
                              gr.update(interactive=False)),
                          inputs=[grp_radio],
                          outputs=[new_grp_tb, grp_name_section, st_action,
                                   btn_add, btn_add_sub, btn_rename, btn_del])

        def click_rename(grp):
            grp = _grp_name(grp)
            if not grp or grp == ALL_GROUP:
                return (gr.update(), gr.update(visible=False), "add",
                        gr.update(), gr.update(), gr.update(), gr.update())
            return (gr.update(value=grp), gr.update(visible=True), "rename",
                    gr.update(interactive=False),
                    gr.update(interactive=False),
                    gr.update(interactive=False),
                    gr.update(interactive=False))

        btn_rename.click(fn=click_rename, inputs=[grp_radio],
                         outputs=[new_grp_tb, grp_name_section, st_action,
                                  btn_add, btn_add_sub, btn_rename, btn_del])

        btn_cancel_grp.click(fn=lambda: (gr.update(visible=False),
                                          gr.update(interactive=True),
                                          gr.update(interactive=True),
                                          gr.update(interactive=True),
                                          gr.update(interactive=True)),
                             outputs=[grp_name_section, btn_add, btn_add_sub, btn_rename, btn_del])

        def confirm_group(cur_grp, new_name, action, saved_dir):
            cur_grp = _grp_name(cur_grp)
            new_name = (new_name or "").strip()
            if not new_name:
                return (gr.update(), gr.update(), gr.update(visible=False), "add",
                        gr.update(interactive=True), gr.update(interactive=True),
                        gr.update(interactive=True), gr.update(interactive=True),
                        saved_dir)
            data   = _load_data(saved_dir)
            groups = data["groups"]
            # Reject duplicate names (case-insensitive), also reject ALL_GROUP
            name_lower = new_name.lower()
            existing_lower = [g["name"].lower() for g in groups]
            is_duplicate = (
                new_name == ALL_GROUP or
                (action == "add" and name_lower in existing_lower) or
                (action == "add_sub" and name_lower in existing_lower) or
                (action == "rename" and name_lower in existing_lower
                 and new_name.lower() != cur_grp.lower())
            )
            if is_duplicate:
                gr.Warning(f"A group named '{new_name}' already exists.")
                return (gr.update(), gr.update(), gr.update(visible=True), action,
                        gr.update(interactive=False), gr.update(interactive=False),
                        gr.update(interactive=False), gr.update(interactive=False),
                        saved_dir)
            if action == "add":
                groups.append({"name": new_name, "parent": None, "level": 0})
                data["groups"] = _normalize_groups(groups)
                selected = new_name
            elif action == "add_sub" and cur_grp and cur_grp != ALL_GROUP:
                parent_group = _group_map(data).get(cur_grp)
                parent_level = parent_group.get("level", 0) if parent_group else 0
                groups.append({"name": new_name, "parent": cur_grp, "level": parent_level + 1})
                data["groups"] = _normalize_groups(groups)
                selected = new_name
            else:
                names = _group_names(data)
                if cur_grp in names and cur_grp != ALL_GROUP:
                    idx = names.index(cur_grp)
                    for entry in data["loras"].values():
                        g = entry.get("groups", [])
                        if cur_grp in g:
                            g.remove(cur_grp)
                            if new_name not in g:
                                g.append(new_name)
                    for group in groups:
                        if group.get("parent") == cur_grp:
                            group["parent"] = new_name
                    groups[idx]["name"] = new_name
                    data["groups"] = _normalize_groups(groups)
                    selected = new_name
                else:
                    selected = cur_grp
            data["last_group"] = selected
            _save_data(saved_dir, data)
            cur_loras  = _scan_dir(saved_dir)
            loras      = _loras_for_group(data, selected, cur_loras)
            lo_choices = _lora_choices_for_radio(data, loras)
            is_all     = (selected == ALL_GROUP)
            return (
                gr.update(choices=(_lo_c:=_group_choices(data)), value=_find_choice_val(_lo_c, selected)),
                gr.update(value=lo_choices[0][1] if lo_choices else ""),
                gr.update(value=_lora_list_html(data, loras, lo_choices[0][1] if lo_choices else None, reveal_selected=True)),
                gr.update(visible=False),
                "add",
                gr.update(interactive=True),
                gr.update(interactive=not is_all),
                gr.update(interactive=not is_all),
                gr.update(interactive=not is_all),
                saved_dir,
                lo_choices[0][1] if lo_choices else None,
            )

        btn_confirm.click(fn=confirm_group,
                          inputs=[grp_radio, new_grp_tb, st_action, st_dir],
                          outputs=[grp_radio, lora_radio, lora_list_html, grp_name_section, st_action,
                                   btn_add, btn_add_sub, btn_rename, btn_del, st_dir, st_sel_lora])

        # ── Delete Group ───────────────────────────────────────────────
        btn_del.click(
            fn=lambda grp: (gr.update(visible=True) if (grp and grp != ALL_GROUP)
                            else gr.update(visible=False)),
            inputs=[grp_radio], outputs=[del_confirm_row])

        btn_del_no.click(fn=lambda: gr.update(visible=False), outputs=[del_confirm_row])

        def do_delete_group(grp, saved_dir):
            grp = _grp_name(grp)
            if not grp or grp == ALL_GROUP:
                return (gr.update(), gr.update(), *_btn_states(ALL_GROUP, []),
                        gr.update(interactive=False),
                        gr.update(visible=False), saved_dir, None)
            data = _load_data(saved_dir)
            deleted_group = _group_map(data).get(grp)
            preferred_next = deleted_group.get("parent") if deleted_group else ALL_GROUP
            descendants = _group_descendants(data, grp)
            to_remove = {grp} | descendants
            if grp in _group_names(data):
                data["groups"] = [g for g in data["groups"] if g["name"] not in to_remove]
                for e in data["loras"].values():
                    e["groups"] = [name for name in e.get("groups", []) if name not in to_remove]
            settings = _load_settings()
            next_grp = _visible_selected_group(data, preferred_next, settings.get("hide_all_group", False))
            data["last_group"] = next_grp if next_grp is not None else ALL_GROUP
            _save_data(saved_dir, data)
            cur_loras  = _scan_dir(saved_dir)
            loras      = _loras_for_group(data, next_grp, cur_loras)
            lo_choices = _lora_choices_for_radio(data, loras)
            return (
                gr.update(choices=(_lo_c:=_group_choices(data)), value=_find_choice_val(_lo_c, next_grp)),
                gr.update(value=lo_choices[0][1] if lo_choices else ""),
                gr.update(value=_lora_list_html(data, loras, lo_choices[0][1] if lo_choices else None, reveal_selected=True)),
                *_btn_states(next_grp, data["groups"]),
                gr.update(interactive=False),
                gr.update(visible=False),
                saved_dir,
                lo_choices[0][1] if lo_choices else None,
            )

        btn_del_yes.click(fn=do_delete_group, inputs=[grp_radio, st_dir],
                          outputs=[grp_radio, lora_radio, lora_list_html,
                                   btn_rename, btn_del, btn_up, btn_down, btn_assign,
                                   btn_add_sub, del_confirm_row, st_dir, st_sel_lora])

        # ── Move Group ─────────────────────────────────────────────────
        def move_group(grp, saved_dir, direction):
            grp = _grp_name(grp)
            if not grp or grp == ALL_GROUP:
                return (gr.update(), gr.update(interactive=False),
                        gr.update(interactive=False), saved_dir)
            data   = _load_data(saved_dir)
            groups = data["groups"]
            names = _group_names(data)
            if grp not in names:
                return gr.update(), gr.update(), gr.update(), saved_dir
            current = _group_map(data).get(grp)
            siblings = [g["name"] for g in groups if g.get("parent") == current.get("parent")]
            idx = siblings.index(grp)
            ni  = idx + direction
            if 0 <= ni < len(siblings):
                target = siblings[ni]
                idx_a = names.index(grp)
                idx_b = names.index(target)
                groups[idx_a], groups[idx_b] = groups[idx_b], groups[idx_a]
                _save_data(saved_dir, data)
            _, _, up_u, dn_u, _ = _btn_states(grp, data["groups"])
            return gr.update(choices=(_lo_c:=_group_choices(data)), value=_find_choice_val(_lo_c, grp)), up_u, dn_u, saved_dir

        btn_up.click(fn=lambda g, d: move_group(g, d, -1), inputs=[grp_radio, st_dir],
                     outputs=[grp_radio, btn_up, btn_down, st_dir])
        btn_down.click(fn=lambda g, d: move_group(g, d, +1), inputs=[grp_radio, st_dir],
                       outputs=[grp_radio, btn_up, btn_down, st_dir])

        def sort_loras_by_name(real_name, grp, saved_dir, cur_loras):
            grp = _grp_name(grp)
            data = _load_data(saved_dir)
            all_l = cur_loras if cur_loras else live_loras(saved_dir)
            ordered = _loras_for_group(data, grp, all_l)
            ordered = _sort_lora_names(data, ordered, AUTO_SORT_NAME)
            _set_lora_order(data, grp, ordered)
            _save_data(saved_dir, data)
            selected = real_name if real_name in ordered else (ordered[0] if ordered else None)
            settings = _load_settings()
            sort_u, sort_used_u, done_u = _lora_sort_ui_updates(
                selected, grp, data, all_l, settings.get("lora_auto_sort_mode", AUTO_SORT_NONE)
            )
            return (
                gr.update(value=selected or ""),
                gr.update(value=_lora_list_html(data, ordered, selected)),
                sort_u,
                sort_used_u,
                done_u,
                saved_dir,
                selected,
            )

        btn_lora_sort.click(fn=sort_loras_by_name,
                            inputs=[lora_radio, grp_radio, st_dir, st_loras],
                            outputs=[lora_radio, lora_list_html, btn_lora_sort, btn_lora_sort_used, btn_lora_done, st_dir, st_sel_lora])

        def sort_loras_by_most_used(real_name, grp, saved_dir, cur_loras):
            grp = _grp_name(grp)
            data = _load_data(saved_dir)
            all_l = cur_loras if cur_loras else live_loras(saved_dir)
            ordered = _loras_for_group(data, grp, all_l)
            ordered = _sort_lora_names(data, ordered, AUTO_SORT_MOST_USED)
            _set_lora_order(data, grp, ordered)
            _save_data(saved_dir, data)
            selected = real_name if real_name in ordered else (ordered[0] if ordered else None)
            settings = _load_settings()
            sort_u, sort_used_u, done_u = _lora_sort_ui_updates(
                selected, grp, data, all_l, settings.get("lora_auto_sort_mode", AUTO_SORT_NONE)
            )
            return (
                gr.update(value=selected or ""),
                gr.update(value=_lora_list_html(data, ordered, selected)),
                sort_u,
                sort_used_u,
                done_u,
                saved_dir,
                selected,
            )

        btn_lora_sort_used.click(
            fn=sort_loras_by_most_used,
            inputs=[lora_radio, grp_radio, st_dir, st_loras],
            outputs=[lora_radio, lora_list_html, btn_lora_sort, btn_lora_sort_used, btn_lora_done, st_dir, st_sel_lora]
        )

        # ── Assign Loras ───────────────────────────────────────────────
        def click_assign(grp, saved_dir, cur_loras):
            grp = _grp_name(grp)
            if not grp or grp == ALL_GROUP:
                return gr.update(visible=False), gr.update(visible=False), saved_dir
            data    = _load_data(saved_dir)
            all_l   = cur_loras if cur_loras else live_loras(saved_dir)
            already = [l for l in all_l
                       if grp in data["loras"].get(l, {}).get("groups", [])]
            return (gr.update(choices=_assign_choices(all_l), value=already, visible=True),
                    gr.update(visible=True), saved_dir)

        btn_assign.click(fn=click_assign, inputs=[grp_radio, st_dir, st_loras],
                         outputs=[assign_dd, assign_row, st_dir])

        def save_assign(grp, selected, saved_dir, cur_loras):
            grp = _grp_name(grp)
            if not grp or grp == ALL_GROUP:
                return gr.update(visible=False), gr.update(visible=False), gr.update(), saved_dir, None
            data  = _load_data(saved_dir)
            settings = _load_settings()
            all_l = cur_loras if cur_loras else live_loras(saved_dir)
            for l in all_l:
                e = _ensure_lora(data, l, saved_dir)
                if grp in e["groups"]:
                    e["groups"].remove(grp)
            for l in (selected or []):
                e = _ensure_lora(data, l, saved_dir)
                if grp not in e["groups"]:
                    e["groups"].append(grp)
            _apply_lora_auto_sort(data, all_l, settings.get("lora_auto_sort_mode", AUTO_SORT_NONE), grp)
            _save_data(saved_dir, data)
            loras      = _loras_for_group(data, grp, all_l)
            lo_choices = _lora_choices_for_radio(data, loras)
            return (gr.update(visible=False), gr.update(visible=False),
                    gr.update(value=lo_choices[0][1] if lo_choices else ""),
                    gr.update(value=_lora_list_html(data, loras, lo_choices[0][1] if lo_choices else None)),
                    saved_dir,
                    lo_choices[0][1] if lo_choices else None)

        btn_save_assign.click(fn=save_assign,
                              inputs=[grp_radio, assign_dd, st_dir, st_loras],
                              outputs=[assign_dd, assign_row, lora_radio, lora_list_html, st_dir, st_sel_lora])
        btn_cancel_assign.click(fn=lambda: (gr.update(visible=False), gr.update(visible=False)),
                                outputs=[assign_dd, assign_row])

        # ── Use Lora ───────────────────────────────────────────────────
        def _activate_single(real_name, curr_act, curr_mult, curr_prompt,
                             trigger_words_mode, saved_dir):
            val       = lora_val(real_name)
            activated = list(curr_act) if curr_act else []
            already   = val in activated
            if not already:
                activated.append(val)
            entry    = _load_data(saved_dir)["loras"].get(real_name, {})
            strength = str(entry.get("default_strength", "1")).strip() or "1"
            new_mult = curr_mult or ""
            if not already:
                new_mult = _append_mult(new_mult, strength)
            new_prompt = curr_prompt or ""
            tw = entry.get("trigger_words", "")
            new_prompt = _apply_trigger_words(new_prompt, tw, trigger_words_mode)
            return activated, new_mult, new_prompt

        def _build_replace_prompt(active_values, saved_dir, known_loras=None):
            if not active_values:
                return ""
            all_loras = known_loras if known_loras is not None else live_loras(saved_dir)
            value_to_real = {lora_val(real_name): real_name for real_name in all_loras}
            data = _load_data(saved_dir)
            trigger_words = []
            for active_value in active_values:
                real_name = value_to_real.get(active_value)
                if not real_name:
                    continue
                entry = data["loras"].get(real_name, {})
                tw = (entry.get("trigger_words") or "").strip()
                if tw:
                    trigger_words.append(tw)
            return _join_trigger_words(trigger_words)

        def _active_values_to_real_names(active_values, saved_dir, known_loras=None):
            all_loras = known_loras if known_loras is not None else live_loras(saved_dir)
            value_to_real = {lora_val(real_name): real_name for real_name in all_loras}
            real_names = []
            for active_value in list(active_values or []):
                real_name = value_to_real.get(active_value)
                if real_name:
                    real_names.append(real_name)
            return real_names

        def _remove_trigger_words_from_prompt(prompt, real_names, saved_dir, known_loras=None):
            settings = _load_settings()
            text = prompt or ""
            if not settings.get("remove_trigger_words_on_deactivate", False):
                return text
            if not real_names:
                return text
            trigger_words_mode = settings.get("trigger_words_mode", DEFAULT_TRIGGER_WORDS_MODE)
            data = _load_data(saved_dir)
            for real_name in real_names:
                entry = data["loras"].get(real_name, {})
                trigger_words = str(entry.get("trigger_words", "") or "")
                tw = trigger_words.strip()
                if not tw:
                    continue
                if trigger_words_mode == TRIGGER_WORDS_PREPEND:
                    text = text.replace(f"{tw}, ", "")
                elif trigger_words_mode == TRIGGER_WORDS_APPEND:
                    text = text.replace(f", {tw}", "")
                elif trigger_words_mode == TRIGGER_WORDS_REPLACE:
                    text = text.replace(tw, "")
            return text

        def use_lora(real_name, curr_act, curr_mult, curr_prompt, trigger_words_mode, saved_dir, cur_grp, cur_loras):
            if not real_name:
                return gr.update(), gr.update(), gr.update(), gr.update(interactive=False), saved_dir, gr.update(), None, gr.update()
            val       = lora_val(real_name)
            activated = list(curr_act) if curr_act else []
            already   = val in activated
            activated, new_mult, new_prompt = _activate_single(
                real_name, curr_act, curr_mult, curr_prompt, trigger_words_mode, saved_dir)
            _increment_usage_counts(saved_dir, [real_name])
            sort_html_update = gr.update()
            selected_after = real_name
            cur_grp = _grp_name(cur_grp)
            if trigger_words_mode == TRIGGER_WORDS_REPLACE:
                new_prompt = _build_replace_prompt(activated, saved_dir)
            settings = _load_settings()
            if settings.get("lora_auto_sort_mode") == AUTO_SORT_MOST_USED:
                data = _load_data(saved_dir)
                all_l = cur_loras if cur_loras else live_loras(saved_dir)
                _apply_lora_auto_sort(data, all_l, AUTO_SORT_MOST_USED, cur_grp, include_all_group=True)
                _save_data(saved_dir, data)
                group_loras = _loras_for_group(data, cur_grp or ALL_GROUP, all_l)
                if selected_after not in group_loras:
                    selected_after = group_loras[0] if group_loras else None
                sort_html_update = gr.update(value=_lora_list_html(data, group_loras, selected_after))
            # Save last used lora for this group in Settings.json (safe — no lora data)
            if not already:
                data    = _load_data(saved_dir)
                cur_grp = data.get("last_group", ALL_GROUP)
                key = _last_used_key(saved_dir)
                if key:
                    settings.setdefault(key, {})[cur_grp] = real_name
                    _save_settings(settings)
            return (gr.update(value=activated), gr.update(value=new_mult),
                    gr.update(value=new_prompt), gr.update(interactive=False), saved_dir,
                    sort_html_update, selected_after,
                    gr.update(value=_activated_loras_html(saved_dir, activated, new_mult, cur_loras if cur_loras else live_loras(saved_dir))))

        def use_both(real_name, curr_act, curr_mult, curr_prompt,
                     trigger_words_mode, saved_dir, cur_loras, cur_grp):
            if not real_name:
                return gr.update(), gr.update(), gr.update(), gr.update(interactive=False), saved_dir, gr.update(), None, gr.update()
            all_l     = cur_loras if cur_loras else live_loras(saved_dir)
            high, low = _find_pair(real_name, all_l, saved_dir)
            if high is None or low is None:
                return gr.update(), gr.update(), gr.update(), gr.update(interactive=False), saved_dir, gr.update(), None, gr.update()
            _increment_usage_counts(saved_dir, [high, low])
            activated = list(curr_act) if curr_act else []
            new_mult  = curr_mult or ""
            new_prompt = curr_prompt or ""
            sort_html_update = gr.update()
            selected_after = real_name
            cur_grp = _grp_name(cur_grp)
            # Add only the loras not already active
            high_val = lora_val(high)
            low_val  = lora_val(low)
            if high_val not in activated:
                activated, new_mult, new_prompt = _activate_single(
                    high, activated, new_mult, new_prompt, trigger_words_mode, saved_dir)
            if low_val not in activated:
                activated, new_mult, new_prompt = _activate_single(
                    low, activated, new_mult, new_prompt, trigger_words_mode, saved_dir)
            if trigger_words_mode == TRIGGER_WORDS_REPLACE:
                new_prompt = _build_replace_prompt(activated, saved_dir, all_l)
            settings = _load_settings()
            if settings.get("lora_auto_sort_mode") == AUTO_SORT_MOST_USED:
                data = _load_data(saved_dir)
                _apply_lora_auto_sort(data, all_l, AUTO_SORT_MOST_USED, cur_grp, include_all_group=True)
                _save_data(saved_dir, data)
                group_loras = _loras_for_group(data, cur_grp or ALL_GROUP, all_l)
                if selected_after not in group_loras:
                    selected_after = group_loras[0] if group_loras else None
                sort_html_update = gr.update(value=_lora_list_html(data, group_loras, selected_after))
            # Save last used lora (the one selected in the listbox)
            data    = _load_data(saved_dir)
            cur_grp = data.get("last_group", ALL_GROUP)
            key = _last_used_key(saved_dir)
            if key:
                settings.setdefault(key, {})[cur_grp] = real_name
                _save_settings(settings)
            return (gr.update(value=activated), gr.update(value=new_mult),
                    gr.update(value=new_prompt), gr.update(interactive=False), saved_dir,
                    sort_html_update, selected_after,
                    gr.update(value=_activated_loras_html(saved_dir, activated, new_mult, all_l)))

        _use_in_base = [
            loras_comp  if loras_comp  is not None else gr.State([]),
            mult_comp   if mult_comp   is not None else gr.State(""),
            prompt_comp if prompt_comp is not None else gr.State(""),
            trigger_words_dd, st_dir, grp_radio, st_loras,
        ]
        _use_out = []
        if loras_comp  is not None: _use_out.append(loras_comp)
        if mult_comp   is not None: _use_out.append(mult_comp)
        if prompt_comp is not None: _use_out.append(prompt_comp)

        if _use_out:
            def _use_wrapped(rn, ca, cm, cp, atw, sd, grp, cur_l):
                act, mult, prompt, btn_upd, ld, html_upd, sel_upd, active_html_upd = use_lora(rn, ca, cm, cp, atw, sd, grp, cur_l)
                out = []
                if loras_comp  is not None: out.append(act)
                if mult_comp   is not None: out.append(mult)
                if prompt_comp is not None: out.append(prompt)
                out.append(btn_upd)  # btn_use update
                out.append(ld)
                out.append(html_upd)
                out.append(sel_upd)
                out.append(active_html_upd)
                return tuple(out)

            def _use_both_wrapped(rn, ca, cm, cp, atw, sd, grp, cur_l):
                act, mult, prompt, btn_upd, ld, html_upd, sel_upd, active_html_upd = use_both(rn, ca, cm, cp, atw, sd, cur_l, grp)
                out = []
                if loras_comp  is not None: out.append(act)
                if mult_comp   is not None: out.append(mult)
                if prompt_comp is not None: out.append(prompt)
                out.append(btn_upd)  # btn_use_both update
                out.append(ld)
                out.append(html_upd)
                out.append(sel_upd)
                out.append(active_html_upd)
                return tuple(out)

            btn_use.click(fn=_use_wrapped, inputs=[lora_radio] + _use_in_base,
                          outputs=_use_out + [btn_use, st_dir, lora_list_html, st_sel_lora, activated_list_html])
            btn_use_both.click(fn=_use_both_wrapped,
                               inputs=[lora_radio] + _use_in_base,
                               outputs=_use_out + [btn_use_both, st_dir, lora_list_html, st_sel_lora, activated_list_html])

        def clear_all_activated(curr_act, curr_mult, curr_prompt, undo_mode, saved_loras, saved_mult, saved_prompt, saved_dir, cur_loras):
            current_active = list(curr_act) if curr_act else []
            current_mult = curr_mult or ""
            current_prompt = curr_prompt or ""
            if undo_mode:
                restored_active = list(saved_loras) if saved_loras else []
                restored_mult = saved_mult or ""
                restored_prompt = saved_prompt or ""
                return (
                    gr.update(value=restored_active),
                    gr.update(value=restored_mult),
                    gr.update(value=restored_prompt),
                    _clear_button_update(restored_active, False),
                    [],
                    "",
                    "",
                    False,
                    None,
                    gr.update(value=_activated_loras_html(saved_dir, restored_active, restored_mult, cur_loras if cur_loras else live_loras(saved_dir))),
                )
            removed_real_names = _active_values_to_real_names(current_active, saved_dir, cur_loras)
            cleared_prompt = _remove_trigger_words_from_prompt(current_prompt, removed_real_names, saved_dir, cur_loras)
            return (
                gr.update(value=[]),
                gr.update(value=""),
                gr.update(value=cleared_prompt),
                _clear_button_update([], True),
                current_active,
                current_mult,
                current_prompt,
                True,
                [],
                gr.update(value=_activated_loras_html(saved_dir, [], "", cur_loras if cur_loras else live_loras(saved_dir))),
            )

        if loras_comp is not None and mult_comp is not None:
            _clear_inputs = [loras_comp, mult_comp]
            _clear_outputs = [loras_comp, mult_comp]
            if prompt_comp is not None:
                def _clear_all_wrapped(curr_act, curr_mult, curr_prompt, undo_mode, saved_loras, saved_mult, saved_prompt, saved_dir, cur_loras):
                    return clear_all_activated(curr_act, curr_mult, curr_prompt, undo_mode, saved_loras, saved_mult, saved_prompt, saved_dir, cur_loras)

                _clear_fn = _clear_all_wrapped
                _clear_inputs.append(prompt_comp)
                _clear_outputs.append(prompt_comp)
            else:
                def _clear_all_wrapped(curr_act, curr_mult, undo_mode, saved_loras, saved_mult, saved_prompt, saved_dir, cur_loras):
                    act, mult, _prompt, btn_u, clr_loras, clr_mult, clr_prompt, clr_mode, clr_expected, active_html = clear_all_activated(
                        curr_act, curr_mult, "", undo_mode, saved_loras, saved_mult, saved_prompt, saved_dir, cur_loras
                    )
                    return act, mult, btn_u, clr_loras, clr_mult, clr_prompt, clr_mode, clr_expected, active_html

                _clear_fn = _clear_all_wrapped
            _clear_inputs.extend([st_clear_mode, st_clear_loras, st_clear_mult, st_clear_prompt, st_dir, st_loras])
            _clear_outputs.extend([btn_clear_all, st_clear_loras, st_clear_mult, st_clear_prompt, st_clear_mode, st_clear_expected, activated_list_html])
            btn_clear_all.click(
                fn=_clear_fn,
                inputs=_clear_inputs,
                outputs=_clear_outputs,
            )

        # ── Edit Lora ──────────────────────────────────────────────────
        def _show_metadata_actions(real_name):
            return gr.update(visible=bool(real_name))

        for tb in (disp_name_tb, tw_tb, str_tb, info_tb, url_tb):
            tb.input(fn=_show_metadata_actions, inputs=[lora_radio], outputs=[edit_row])
        preview_upload.change(
            fn=lambda files: gr.update(visible=bool(files)),
            inputs=[preview_upload],
            outputs=[edit_row],
        )
        btn_preview_add.click(
            fn=lambda real_name: (gr.update(visible=True), gr.update(visible=bool(real_name))),
            inputs=[lora_radio],
            outputs=[preview_upload, edit_row],
        )

        def on_preview_select(real_name, preview_work, evt: gr.SelectData):
            idx = evt.index if evt else None
            try:
                idx = int(idx) if idx is not None else None
            except Exception:
                idx = None
            return (*_preview_manage_updates_from_images(real_name, list(preview_work or []), idx, False), idx)

        preview_gallery.select(
            fn=on_preview_select,
            inputs=[lora_radio, st_preview_work],
            outputs=[preview_gallery, preview_upload, preview_manage_row,
                     btn_preview_add, btn_preview_left, btn_preview_right, btn_preview_remove, btn_preview_clear,
                     st_preview_index],
        )

        def move_preview(real_name, preview_work, preview_index, delta):
            images = list(preview_work or [])
            if not real_name or preview_index is None:
                return (*_preview_manage_updates_from_images(real_name, images, None, False), images, None, gr.update())
            try:
                idx = int(preview_index)
            except Exception:
                idx = None
            if idx is None or idx < 0 or idx >= len(images):
                return (*_preview_manage_updates_from_images(real_name, images, None, False), images, None, gr.update())
            new_idx = idx + delta
            if new_idx < 0 or new_idx >= len(images):
                return (*_preview_manage_updates_from_images(real_name, images, idx, False), images, idx, gr.update())
            item = images.pop(idx)
            images.insert(new_idx, item)
            return (*_preview_manage_updates_from_images(real_name, images, new_idx, False), images, new_idx, gr.update(visible=True))

        btn_preview_left.click(
            fn=lambda rn, pw, pi: move_preview(rn, pw, pi, -1),
            inputs=[lora_radio, st_preview_work, st_preview_index],
            outputs=[preview_gallery, preview_upload, preview_manage_row,
                     btn_preview_add, btn_preview_left, btn_preview_right, btn_preview_remove, btn_preview_clear,
                     st_preview_work, st_preview_index, edit_row],
        )
        btn_preview_right.click(
            fn=lambda rn, pw, pi: move_preview(rn, pw, pi, 1),
            inputs=[lora_radio, st_preview_work, st_preview_index],
            outputs=[preview_gallery, preview_upload, preview_manage_row,
                     btn_preview_add, btn_preview_left, btn_preview_right, btn_preview_remove, btn_preview_clear,
                     st_preview_work, st_preview_index, edit_row],
        )

        def remove_preview(real_name, preview_work, preview_index):
            images = list(preview_work or [])
            if not real_name or preview_index is None:
                return (*_preview_manage_updates_from_images(real_name, images, None, False), images, None, gr.update())
            try:
                idx = int(preview_index)
            except Exception:
                idx = None
            if idx is None or idx < 0 or idx >= len(images):
                return (*_preview_manage_updates_from_images(real_name, images, None, False), images, None, gr.update())
            del images[idx]
            next_idx = min(idx, len(images) - 1) if images else None
            return (*_preview_manage_updates_from_images(real_name, images, next_idx, False), images, next_idx, gr.update(visible=True))

        btn_preview_remove.click(
            fn=remove_preview,
            inputs=[lora_radio, st_preview_work, st_preview_index],
            outputs=[preview_gallery, preview_upload, preview_manage_row,
                     btn_preview_add, btn_preview_left, btn_preview_right, btn_preview_remove, btn_preview_clear,
                     st_preview_work, st_preview_index, edit_row],
        )

        def clear_preview(real_name):
            return (*_preview_manage_updates_from_images(real_name, [], None, False), [], None, gr.update(visible=bool(real_name)))

        btn_preview_clear.click(
            fn=clear_preview,
            inputs=[lora_radio],
            outputs=[preview_gallery, preview_upload, preview_manage_row,
                     btn_preview_add, btn_preview_left, btn_preview_right, btn_preview_remove, btn_preview_clear,
                     st_preview_work, st_preview_index, edit_row],
        )

        def save_edit(real_name, disp_name, tw, strength, info_text, url, preview_files, preview_work, cur_grp, saved_dir, cur_loras):
            cur_grp = _grp_name(cur_grp)
            if real_name and saved_dir:
                clean_disp = (disp_name or "").strip()
                data = _load_data(saved_dir)
                previous_display_name = (data["loras"].get(real_name, {}).get("display_name") or "").strip()
                if clean_disp != previous_display_name and clean_disp and not _is_display_name_unique(data, real_name, clean_disp):
                    gr.Warning(f"The display name '{clean_disp}' is already used.")
                    return (gr.update(),) * 23
                e = _ensure_lora(data, real_name, saved_dir)
                e["display_name"]     = clean_disp
                e["trigger_words"]    = (tw or "").strip()
                e["default_strength"] = (strength or "1").strip() or "1"
                e["info"]             = (info_text or "").strip()
                e["url"]              = (url or "").strip()
                settings = _load_settings()
                if settings.get("lora_auto_sort_mode") == AUTO_SORT_NAME and clean_disp != previous_display_name:
                    all_l = cur_loras if cur_loras else live_loras(saved_dir)
                    _apply_lora_auto_sort(data, all_l, AUTO_SORT_NAME, cur_grp, include_all_group=True)
                entry = _ensure_lora(data, real_name, saved_dir)
                current_images = _preview_images_for_entry(entry)
                kept_images = [p for p in (preview_work or []) if p in current_images and os.path.isfile(p)]
                removed_images = [p for p in current_images if p not in kept_images]
                new_images = _copy_preview_uploads(saved_dir, real_name, preview_files)
                entry["preview_images"] = [_preview_abs_to_rel(p) for p in (kept_images + new_images)]
                _save_data(saved_dir, data)
                for path in removed_images:
                    try:
                        if os.path.isfile(path):
                            os.remove(path)
                    except Exception:
                        pass
            data       = _load_data(saved_dir)
            all_l      = live_loras(saved_dir)
            loras      = _loras_for_group(data, cur_grp or ALL_GROUP, all_l)
            lo_choices = _lora_choices_for_radio(data, loras)
            safe_val   = (real_name if any(c[1] == real_name for c in lo_choices)
                          else (lo_choices[0][1] if lo_choices else None))
            pair_btn_u = _use_both_button_state(safe_val, saved_dir, all_l)
            return (
                *_metadata_updates(real_name or "", saved_dir, False),
                pair_btn_u,
                gr.update(value=safe_val or ""),
                gr.update(value=_lora_list_html(data, loras, safe_val)),
                saved_dir,
                safe_val,
                _preview_gallery_value(safe_val, saved_dir),
                None,
            )

        btn_save_edit.click(fn=save_edit,
                            inputs=[lora_radio, disp_name_tb, tw_tb, str_tb,
                                    info_tb, url_tb, preview_upload, st_preview_work, grp_radio, st_dir, st_loras],
                            outputs=[disp_name_tb, real_name_tb, tw_tb, str_tb, info_tb,
                                     url_tb, url_btn_row, preview_gallery, preview_upload, preview_manage_row,
                                     btn_preview_add, btn_preview_left, btn_preview_right, btn_preview_remove, btn_preview_clear,
                                     edit_row,
                                     btn_use_both, lora_radio, lora_list_html, st_dir, st_sel_lora, st_preview_work, st_preview_index])

        def cancel_edit(real_name, saved_dir, cur_loras):
            pair_btn_u = _use_both_button_state(real_name, saved_dir, cur_loras if cur_loras else live_loras(saved_dir))
            data = _load_data(saved_dir)
            loras = _loras_for_group(data, data.get("last_group", ALL_GROUP), cur_loras if cur_loras else live_loras(saved_dir))
            return (*_metadata_updates(real_name or "", saved_dir, False),
                    pair_btn_u,
                    gr.update(value=real_name),
                    gr.update(value=_lora_list_html(data, loras, real_name)),
                    saved_dir,
                    _preview_gallery_value(real_name, saved_dir),
                    None)

        btn_cancel_edit.click(fn=cancel_edit, inputs=[lora_radio, st_dir, st_loras],
                              outputs=[disp_name_tb, real_name_tb, tw_tb, str_tb, info_tb,
                                       url_tb, url_btn_row, preview_gallery, preview_upload, preview_manage_row,
                                       btn_preview_add, btn_preview_left, btn_preview_right, btn_preview_remove, btn_preview_clear,
                                       edit_row,
                                       btn_use_both, lora_radio, lora_list_html, st_dir, st_preview_work, st_preview_index])

        # ── Open URL ───────────────────────────────────────────────────
        btn_open_url.click(
            fn=lambda url: url,
            inputs=[url_tb], outputs=[url_tb],
            js="(url) => { if(url && url.trim()) window.open(url.trim(), '_blank', 'noopener,noreferrer'); return url; }",
        )

        # ── Settings: Save button ──────────────────────────────────────
        def save_settings_cb(view_mode, auto_sort_mode, thumbnail_columns, thumbnail_fit_without_cropping, thumbnail_cycle_mode, placement_mode, trigger_words_mode, remove_trigger_words_on_deactivate, acc_open, meta_acc_open, hide_all, side, groups_max_width, height, saved_dir, cur_loras):
            settings = _load_settings()
            view_mode = _normalize_lora_view_mode(view_mode)
            horiz = _is_horizontal_view_mode(view_mode)
            settings["lora_view_mode"]        = view_mode
            settings["lora_auto_sort_mode"]   = auto_sort_mode
            settings["thumbnail_columns"]     = int(thumbnail_columns)
            settings["thumbnail_fit_without_cropping"] = bool(thumbnail_fit_without_cropping)
            settings["thumbnail_cycle_mode"]  = thumbnail_cycle_mode
            settings["placement_mode"]        = placement_mode
            settings["trigger_words_mode"]    = trigger_words_mode
            settings["remove_trigger_words_on_deactivate"] = bool(remove_trigger_words_on_deactivate)
            settings["accordion_open"]        = acc_open
            settings["metadata_accordion_open"] = meta_acc_open
            settings["hide_all_group"]        = hide_all
            settings["side_by_side"]          = side
            settings["groups_max_width"]      = int(groups_max_width)
            settings["listbox_height"]        = int(height)
            _save_settings(settings)
            data = _load_data(saved_dir)
            selected_grp = _visible_selected_group(data, data.get("last_group", ALL_GROUP), hide_all)
            stored_grp = selected_grp if selected_grp is not None else ALL_GROUP
            if data.get("last_group") != stored_grp:
                data["last_group"] = stored_grp
                _save_data(saved_dir, data)
            loras = _loras_for_group(data, selected_grp, cur_loras or _scan_dir(saved_dir))
            lo_choices = _lora_choices_for_radio(data, loras)
            sel_lora = _pick_selected_lora(settings, saved_dir, selected_grp, lo_choices)
            btn_rename_u, btn_del_u, btn_up_u, btn_down_u, btn_assign_u = _btn_states(selected_grp, data["groups"])
            btn_up_interactive = btn_up_u.get("interactive", False) if isinstance(btn_up_u, dict) else False
            btn_down_interactive = btn_down_u.get("interactive", False) if isinstance(btn_down_u, dict) else False
            group_up_lbl, group_down_lbl = _group_move_labels_explicit()
            sort_u, sort_used_u, _ = _lora_sort_ui_updates(sel_lora, selected_grp, data, cur_loras or _scan_dir(saved_dir), auto_sort_mode)
            has_lora = bool(lo_choices)
            return (
                gr.update(value=_orient_html(horiz)),       # orient_html
                gr.update(value=_thumbnail_fit_css(bool(thumbnail_fit_without_cropping))),  # thumbnail_fit_html
                gr.update(value=_groups_column_css(int(groups_max_width))),       # groups_width_html
                gr.update(value=group_up_lbl, interactive=btn_up_interactive),    # btn_up
                gr.update(value=group_down_lbl, interactive=btn_down_interactive),# btn_down
                gr.update(value=_listbox_height_css(int(height))),  # height_html
                gr.update(open=meta_acc_open),                                         # metadata_accordion
                gr.update(choices=(_grp_choices:=_group_choices(data)),
                          value=_find_choice_val(_grp_choices, selected_grp)),    # grp_radio
                gr.update(value=sel_lora or ""),                                  # lora_radio
                gr.update(value=_lora_list_html(data, loras, sel_lora, reveal_selected=True, view_mode=view_mode, thumbnail_columns=thumbnail_columns)),          # lora_list_html
                sort_u,                                                          # btn_lora_sort
                sort_used_u,                                                     # btn_lora_sort_used
                btn_rename_u,                                                   # btn_rename
                btn_del_u,                                                      # btn_del
                btn_assign_u,                                                   # btn_assign
                _manage_group_button_update(selected_grp),                      # btn_manage_group
                gr.update(interactive=bool(selected_grp and selected_grp != ALL_GROUP)),  # btn_add_sub
                gr.update(interactive=has_lora),                                 # btn_use
                saved_dir,
                sel_lora,
            )

        btn_save_settings.click(
            fn=save_settings_cb,
            inputs=[view_mode_dd, auto_sort_dd, thumbnail_cols_sl, thumbnail_fit_cb, thumbnail_cycle_mode_dd, placement_mode_dd, trigger_words_dd, remove_tw_on_deactivate_cb, acc_open_cb, meta_acc_open_cb, hide_all_cb, side_cb, groups_max_width_sl, height_sl, st_dir, st_loras],
            outputs=[orient_html, thumbnail_fit_html, groups_width_html, btn_up, btn_down, height_html, metadata_accordion,
                     grp_radio, lora_radio, lora_list_html, btn_lora_sort, btn_lora_sort_used,
                     btn_rename, btn_del, btn_assign, btn_manage_group, btn_add_sub,
                     btn_use,
                     st_dir, st_sel_lora],
            js=(
                "(...args) => {"
                "  var btn = document.getElementById('lo_btn_save_settings');"
                "  if(btn) {"
                "    btn.disabled = true;"
                "    var orig = btn.textContent;"
                "    btn.textContent = orig + ' ✔';"
                "    setTimeout(function() {"
                "      btn.disabled = false;"
                "      btn.textContent = orig;"
                "    }, 2000);"
                "  }"
                "  return args;"
                "}"
            ),
        )

        return grp_radio


# ---------------------------------------------------------------------------
plugin = LoraOrganizerPlugin()
