"""
Lora Organizer Plugin for Wan2GP
Groups, display names, trigger words, default strength, notes, and URL per lora.
Data is stored per-model in the plugin folder (e.g. ltx2.json, flux.json).
"""

import os
import re
import json
import gradio as gr
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
#lo_height_style {
    display: none !important;
}
#lo_accordion > .label-wrap { margin-bottom: 0 !important; }
#lo_grp_radio, #lo_lora_radio {
    border: none !important;
    border-radius: 8px !important;
    overflow-y: auto !important;
    padding: 0 !important;
    gap: 0 !important;
    display: flex !important;
    flex-direction: column !important;
    background: var(--input-background-fill, #1f2937) !important;
}
#lo_grp_radio label, #lo_lora_radio label {
    display: flex !important;
    align-items: center !important;
    width: 100% !important;
    box-sizing: border-box !important;
    border-bottom: 1px solid #333 !important;
    margin: 0 !important;
    padding: 0 !important;
    cursor: pointer !important;
}
#lo_grp_radio label:last-child, #lo_lora_radio label:last-child {
    border-bottom: none !important;
}
#lo_grp_radio input[type="radio"], #lo_lora_radio input[type="radio"] {
    display: none !important;
}
#lo_grp_radio label span, #lo_lora_radio label span {
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
/* Uniform button font size */
#lo_btn_use, #lo_btn_use_both,
#lo_btn_clear_all, #lo_btn_reorder_loras,
#lo_btn_add_group, #lo_btn_add_sub_group, #lo_btn_manage_group, #lo_btn_assign,
#lo_btn_rename_group, #lo_btn_delete_group, #lo_btn_move_up, #lo_btn_move_down,
#lo_btn_group_done, #lo_btn_lora_up, #lo_btn_lora_down, #lo_btn_lora_sort, #lo_btn_lora_done,
#lo_btn_save_assign, #lo_btn_cancel_assign,
#lo_btn_save_edit, #lo_btn_cancel_edit,
#lo_btn_confirm, #lo_btn_cancel_grp,
#lo_btn_del_yes, #lo_btn_del_no,
#lo_btn_save_settings {
    font-size: 0.8rem !important;
    min-height: 2.45rem !important;
}
/* Strip accordion inner padding so all fields fill full width */
#lo_accordion .block.padded {
    padding-top: 0 !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    overflow-x: hidden !important;
    overflow-y: visible !important;
    gap: 6px !important;
}
#lo_accordion .block.padded > .column.gap:first-child,
#lo_accordion .block.padded > .svelte-vt1mxs.gap:first-child {
    padding-top: 12px !important;
}
#lo_accordion .block.padded > *:first-child {
    margin-top: 0 !important;
    padding-top: 0 !important;
}
/* Checkboxes have min-width:160px inline — prevent horizontal overflow in Settings */
#lo_settings_accordion .block.padded {
    min-width: 0 !important;
    overflow-y: hidden !important;
}
/* Restore vertical scrollbar on the listbox containers explicitly */
#lo_grp_radio, #lo_lora_radio {
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
#lo_lora_radio label {
    width: auto !important;
    border-bottom: none !important;
    border-right: 1px solid #333 !important;
}
#lo_lora_radio label:last-child {
    border-right: none !important;
}
#lo_lora_radio label span {
    width: auto !important;
    white-space: nowrap !important;
}
"""

DEFAULT_LISTBOX_HEIGHT = 390
TRIGGER_WORDS_PREPEND = "Add trigger words to the beginning of the prompt"
TRIGGER_WORDS_APPEND = "Add trigger words to the end of the prompt"
TRIGGER_WORDS_REPLACE = "Replace the prompt with trigger words of all activated loras"
TRIGGER_WORDS_NONE = "Do not add trigger words"
DEFAULT_TRIGGER_WORDS_MODE = TRIGGER_WORDS_PREPEND


def _listbox_height_css(px: int) -> str:
    return f"<style>#lo_grp_radio, #lo_lora_radio {{ max-height: {px}px !important; }}</style>"


def _move_labels(horizontal: bool):
    return ("◀ Move Left", "▶ Move Right") if horizontal else ("⬆ Move Up", "⬇ Move Down")


def _move_labels(horizontal: bool):
    return ("🔼 Move Up", "🔽 Move Down")


def _orient_html(horizontal: bool) -> str:
    return f"<style>{_CSS_HORIZ}</style>" if horizontal else ""


def _group_move_labels_explicit() -> tuple[str, str]:
    return ("🔼 Move Up", "🔽 Move Down")


def _lora_move_labels_explicit(horizontal: bool) -> tuple[str, str]:
    return ("◀ Move Left", "▶ Move Right") if horizontal else ("🔼 Move Up", "🔽 Move Down")


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


def _empty_settings() -> dict:
    return {
        "trigger_words_mode": DEFAULT_TRIGGER_WORDS_MODE,
        "horizontal_layout": False,
        "side_by_side": True,
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
            data.setdefault("horizontal_layout", False)
            data.setdefault("side_by_side", True)
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
            "info": "", "url": "",
        }
    else:
        e = data["loras"][real_name]
        e.setdefault("display_name", "")
        e.setdefault("groups", [])
        e.setdefault("info", "")
        e.setdefault("url", "")
        if "default_strength" not in e:
            e["default_strength"] = _auto_strength(lora_dir, real_name)
        elif isinstance(e["default_strength"], (int, float)):
            e["default_strength"] = f"{e['default_strength']:.4g}"
    return data["loras"][real_name]


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
        entry = data["loras"].get(real_name, {})
        custom = (entry.get("display_name") or "").strip()
        disp = custom if custom else os.path.splitext(real_name)[0]
        result.append((disp, real_name))
    return result


def _display_name_for_sort(data: dict, real_name: str) -> str:
    entry = data["loras"].get(real_name, {})
    custom = (entry.get("display_name") or "").strip()
    disp = custom if custom else os.path.splitext(real_name)[0]
    return disp.lower()


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


def _clear_button_update(active_loras, undo_mode: bool = False):
    has_active = bool(active_loras)
    if undo_mode:
        return gr.update(value="↶ Restore Cleared Loras", interactive=True)
    return gr.update(value="❌ Clear Activated Loras", interactive=has_active)


def _manage_group_button_update(group: str | None):
    return gr.update(interactive=_is_real_group_selected(group))


def _lora_move_states(real_name: str | None, group: str | None, data: dict, all_loras: list):
    group = _grp_name(group) if group else group
    loras = _loras_for_group(data, group, all_loras)
    if not real_name or real_name not in loras:
        return (
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False),
        )
    idx = loras.index(real_name)
    n = len(loras)
    return (
        gr.update(interactive=n > 1 and idx > 0),
        gr.update(interactive=n > 1 and idx < n - 1),
        gr.update(interactive=n > 1),
        gr.update(interactive=True),
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
    version     = "1.0"

    def setup_ui(self):
        self.request_global("get_lora_dir")
        self.request_global("get_state_model_type")
        self.request_global("loras_names")
        self.request_component("loras_choices")
        self.request_component("loras_multipliers")
        self.request_component("prompt")
        self.request_component("main")
        self.request_component("state")
        self.insert_after("loras_multipliers", self._build_ui)

    def post_ui_setup(self, requested_components=None):
        pass

    def _build_ui(self):
        loras_comp  = getattr(self, "loras_choices",     None)
        mult_comp   = getattr(self, "loras_multipliers", None)
        prompt_comp = getattr(self, "prompt",            None)
        main_comp   = getattr(self, "main",              None)
        state_comp  = getattr(self, "state",             None)

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
        init_horiz     = init_settings.get("horizontal_layout", False)
        init_side      = init_settings.get("side_by_side", True)
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
        init_sel_lora  = init_lo_radio[0][1] if init_lo_radio else None
        init_active_loras = []
        if loras_comp is not None:
            try:
                init_active_loras = list(getattr(loras_comp, "value", []) or [])
            except Exception:
                init_active_loras = []
        up_lbl, dn_lbl = _group_move_labels_explicit()
        lora_up_lbl, lora_dn_lbl = _lora_move_labels_explicit(init_horiz)

        # ── UI ────────────────────────────────────────────────────────

        with gr.Accordion("🗂️ Lora Organizer", open=init_acc_open, elem_id="lo_accordion"):

            gr.HTML(f"<style>{_CSS_BASE}</style>", elem_id="lo_style_block")
            gr.HTML(_icon_css_block(), elem_id="lo_icon_style_block")
            gr.HTML(_group_indent_js(), elem_id="lo_group_indent_block")
            orient_html = gr.HTML(_orient_html(init_horiz), elem_id="lo_orient_style",
                                  visible=False)
            height_html = gr.HTML(_listbox_height_css(init_height), elem_id="lo_height_style",
                                  visible=False)
            gr.HTML("<div style='height:8px;line-height:0;font-size:0'></div>")

            # ── Use / Use Both / Edit buttons ─────────────────────────
            with gr.Row():
                btn_use      = gr.Button("⚡ Use Lora",  size="sm", min_width=0,
                                         elem_id="lo_btn_use",
                                         interactive=init_has_lora)
                btn_use_both = gr.Button("🔛 Use High & Low", size="sm", min_width=0,
                                         elem_id="lo_btn_use_both", visible=False)
                btn_clear_all = gr.Button("❌ Clear Activated Loras", size="sm", min_width=0,
                                          elem_id="lo_btn_clear_all",
                                          interactive=bool(init_active_loras))
                btn_reorder_loras = gr.Button("↕️ Reorder Loras", size="sm", min_width=0,
                                              elem_id="lo_btn_reorder_loras",
                                              interactive=init_has_lora)

            with gr.Row(visible=False) as lora_manage_row:
                btn_lora_up   = gr.Button(lora_up_lbl, size="sm", min_width=0, interactive=False,
                                          elem_id="lo_btn_lora_up")
                btn_lora_down = gr.Button(lora_dn_lbl, size="sm", min_width=0, interactive=False,
                                          elem_id="lo_btn_lora_down")
                btn_lora_sort = gr.Button("🔤 Sort By Name", size="sm", min_width=0,
                                          interactive=False, elem_id="lo_btn_lora_sort")
                btn_lora_done = gr.Button("✔ Done", size="sm", min_width=0, variant="primary",
                                          elem_id="lo_btn_lora_done")

            # ── Groups + Loras lists ───────────────────────────────────
            if init_side:
                with gr.Row():
                    with gr.Column():
                        gr.HTML("<div style='font-size:.8rem;font-weight:600;"
                                "margin:4px 0 2px;opacity:.65;letter-spacing:.04em'>"
                                "GROUPS</div>")
                        grp_radio = gr.Radio(choices=init_choices,
                                             value=init_grp_val, label="", show_label=False,
                                             elem_id="lo_grp_radio")
                    with gr.Column():
                        gr.HTML("<div style='font-size:.8rem;font-weight:600;"
                                "margin:4px 0 2px;opacity:.65;letter-spacing:.04em'>"
                                "LORAS IN GROUP</div>")
                        lora_radio = gr.Radio(
                            choices=init_lo_radio,
                            value=init_sel_lora,
                            label="", show_label=False, elem_id="lo_lora_radio")
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
                lora_radio = gr.Radio(
                    choices=init_lo_radio,
                    value=init_sel_lora,
                    label="", show_label=False, elem_id="lo_lora_radio")

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

            with gr.Row(visible=False) as edit_row:
                btn_save_edit   = gr.Button("✔ Save Changes",   variant="primary", size="sm",
                                            elem_id="lo_btn_save_edit")
                btn_cancel_edit = gr.Button("✖ Cancel", size="sm", elem_id="lo_btn_cancel_edit")

            # ── Settings ──────────────────────────────────────────────
            with gr.Accordion("⚙️ Settings", open=False, elem_id="lo_settings_accordion"):
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
                acc_open_cb     = gr.Checkbox(value=init_acc_open,
                                              label="Start with Lora Organizer expanded")
                meta_acc_open_cb = gr.Checkbox(value=init_meta_acc_open,
                                               label="Start with Lora Metadata expanded")
                hide_all_cb     = gr.Checkbox(value=init_hide_all,
                                              label='Hide "All" group')
                horiz_cb        = gr.Checkbox(value=init_horiz,
                                              label="Arrange lora items horizontally")
                side_cb         = gr.Checkbox(value=init_side,
                                              label="Arrange group and lora listboxes side by side (requires restart)")
                height_sl       = gr.Slider(minimum=100, maximum=800, step=10,
                                            value=init_height, label="Listbox max height (px)")
                btn_save_settings = gr.Button("💾 Save Settings", size="sm", variant="primary",
                                              elem_id="lo_btn_save_settings")

            st_dir    = gr.State(init_lora_dir)
            st_action = gr.State("add")
            st_loras  = gr.State(init_all_loras)
            st_sel_lora = gr.State(init_sel_lora)
            st_clear_loras = gr.State([])
            st_clear_mult = gr.State("")
            st_clear_mode = gr.State(False)
            st_clear_expected = gr.State(None)


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
                gr.update(visible=show_actions), # edit_row
            )

        def _do_refresh(state_val, forced_loras=None):
            lora_dir  = resolve_lora_dir_always(state_val)
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
            # Always reset lora_radio value to None first to avoid stale-value validation
            # error when switching models (old value not in new choices list)
            sel_lora   = lo_choices[0][1] if lo_choices else None
            return (
                gr.update(choices=(_lo_c:=_group_choices(data)), value=_find_choice_val(_lo_c, last_grp)),
                *bstates,
                gr.update(choices=lo_choices, value=sel_lora),
                gr.update(choices=_assign_choices(cur_loras), value=None, visible=False),
                *_metadata_updates(sel_lora, lora_dir, False),
                gr.update(value=settings.get("trigger_words_mode", DEFAULT_TRIGGER_WORDS_MODE)),
                gr.update(interactive=has_lora),  # btn_use
                _clear_button_update([], False),
                gr.update(interactive=has_lora),  # btn_reorder_loras
                gr.update(visible=False),         # lora_manage_row
                gr.update(value=_lora_move_labels_explicit(settings.get("horizontal_layout", False))[0], interactive=False),  # btn_lora_up
                gr.update(value=_lora_move_labels_explicit(settings.get("horizontal_layout", False))[1], interactive=False),  # btn_lora_down
                gr.update(interactive=False),     # btn_lora_sort
                _manage_group_button_update(last_grp),                # btn_manage_group
                gr.update(visible=False),         # group_manage_row
                gr.update(interactive=_is_real_group_selected(last_grp)),  # btn_add_sub
                lora_dir,
                cur_loras,
                sel_lora,
                [],
                "",
                False,
                None,
            )

        _refresh_out = [
            grp_radio,
            btn_rename, btn_del, btn_up, btn_down, btn_assign,
            lora_radio, assign_dd,
            disp_name_tb, real_name_tb, tw_tb, str_tb, info_tb, url_tb, url_btn_row, edit_row,
            trigger_words_dd, btn_use, btn_clear_all, btn_reorder_loras,
            lora_manage_row, btn_lora_up, btn_lora_down, btn_lora_sort,
            btn_manage_group, group_manage_row, btn_add_sub,
            st_dir, st_loras, st_sel_lora, st_clear_loras, st_clear_mult, st_clear_mode, st_clear_expected,
        ]

        # ==============================================================
        # Callbacks
        # ==============================================================

        _loras_change_outputs = _refresh_out + [btn_use_both]

        if main_comp is not None and state_comp is not None:
            main_comp.load(fn=lambda sv: (*_do_refresh(sv), gr.update()),
                           inputs=[state_comp], outputs=_loras_change_outputs)

        def on_loras_change(loras_val, saved_dir, state_val, saved_loras, cur_sel_lora,
                            clear_mode, clear_expected):
            new_dir   = resolve_lora_dir_always(state_val)
            cur_loras = _scan_dir(new_dir) if new_dir else []
            # Model changed — full refresh (btn_use_both handled separately below)
            if new_dir != saved_dir or cur_loras != saved_loras:
                return (*_do_refresh(state_val, cur_loras), gr.update())
            # Same model — re-evaluate btn_use and btn_use_both for current selection
            already = (cur_sel_lora is not None and
                       _lora_already_active(cur_sel_lora, loras_val))
            result = [gr.update()] * len(_refresh_out)
            btn_use_idx = _refresh_out.index(btn_use)
            btn_clear_idx = _refresh_out.index(btn_clear_all)
            st_clear_loras_idx = _refresh_out.index(st_clear_loras)
            st_clear_mult_idx = _refresh_out.index(st_clear_mult)
            st_clear_mode_idx = _refresh_out.index(st_clear_mode)
            st_clear_expected_idx = _refresh_out.index(st_clear_expected)
            result[btn_use_idx] = gr.update(interactive=bool(cur_sel_lora) and not already)
            current_active = list(loras_val) if loras_val else []
            expected_active = list(clear_expected) if clear_expected else []
            if clear_mode:
                if current_active == expected_active:
                    result[btn_clear_idx] = _clear_button_update(current_active, True)
                else:
                    result[btn_clear_idx] = _clear_button_update(current_active, False)
                    result[st_clear_loras_idx] = []
                    result[st_clear_mult_idx] = ""
                    result[st_clear_mode_idx] = False
                    result[st_clear_expected_idx] = None
            else:
                result[btn_clear_idx] = _clear_button_update(current_active, False)
            # btn_use_both: only update if pair exists for current selection
            btn_both_upd = gr.update()  # no-op by default
            if cur_sel_lora:
                all_l = cur_loras if cur_loras else _scan_dir(saved_dir)
                high, low = _find_pair(cur_sel_lora, all_l, saved_dir)
                if high and low:
                    both_disabled = (_lora_already_active(high, loras_val) and
                                     _lora_already_active(low, loras_val))
                    btn_both_upd = gr.update(interactive=not both_disabled)
            return (*result, btn_both_upd)

        if loras_comp is not None:
            loras_comp.change(fn=on_loras_change,
                              inputs=[loras_comp, st_dir,
                                      state_comp if state_comp is not None else gr.State(None),
                                      st_loras, st_sel_lora, st_clear_mode, st_clear_expected],
                              outputs=_loras_change_outputs)

        if state_comp is not None:
            state_comp.change(fn=on_loras_change,
                              inputs=[loras_comp if loras_comp is not None else gr.State([]),
                                      st_dir, state_comp, st_loras, st_sel_lora, st_clear_mode, st_clear_expected],
                              outputs=_loras_change_outputs)

        try:
            timer = gr.Timer(value=2)
            def on_timer(saved_dir, saved_loras, state_val):
                new_dir   = resolve_lora_dir_always(state_val)
                if not new_dir:
                    return (gr.update(),) * len(_loras_change_outputs)
                cur_loras = _scan_dir(new_dir)
                if new_dir == saved_dir and cur_loras == saved_loras:
                    return (gr.update(),) * len(_loras_change_outputs)
                return (*_do_refresh(state_val, cur_loras), gr.update())
            timer.tick(fn=on_timer,
                       inputs=[st_dir, st_loras,
                               state_comp if state_comp is not None else gr.State(None)],
                       outputs=_loras_change_outputs)
        except Exception:
            pass

        # ── Group radio change ─────────────────────────────────────────
        def on_grp_change(grp, saved_dir, cur_loras, curr_act):
            grp = _grp_name(grp)
            data = _load_data(saved_dir)
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
            lora_up_u, lora_down_u, lora_sort_u, lora_done_u = _lora_move_states(sel_lora, grp, data, all_l)
            lora_up_lbl, lora_down_lbl = _lora_move_labels_explicit(settings.get("horizontal_layout", False))
            return (
                *_btn_states(grp, data["groups"]),
                gr.update(choices=lo_choices, value=sel_lora),
                gr.update(interactive=has_lora and not already),          # btn_use
                _clear_button_update(curr_act or [], False),              # btn_clear_all
                gr.update(interactive=has_lora),                          # btn_reorder_loras
                gr.update(visible=False),                                 # edit_row
                gr.update(visible=False),                                 # lora_manage_row
                gr.update(value=lora_up_lbl, interactive=lora_up_u.get("interactive", False)),
                gr.update(value=lora_down_lbl, interactive=lora_down_u.get("interactive", False)),
                lora_sort_u,
                lora_done_u,
                gr.update(visible=has_pair, interactive=not both_disabled),# btn_use_both
                gr.update(choices=(_lo_c:=_group_choices(data)), value=_find_choice_val(_lo_c, grp)),
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
                                  lora_radio, btn_use, btn_clear_all, btn_reorder_loras, edit_row,
                                  lora_manage_row, btn_lora_up, btn_lora_down, btn_lora_sort, btn_lora_done,
                                  btn_use_both, grp_radio, btn_manage_group, group_manage_row,
                                  btn_add_sub, st_dir, st_sel_lora])

        def _lora_already_active(real_name: str, curr_act) -> bool:
            val = lora_val(real_name)
            activated = list(curr_act) if curr_act else []
            return val in activated

        # ── Lora radio change ──────────────────────────────────────────
        def on_lora_change(real_name, saved_dir, cur_loras, curr_act):
            settings = _load_settings()
            lora_up_lbl, lora_down_lbl = _lora_move_labels_explicit(settings.get("horizontal_layout", False))
            if not real_name:
                return (gr.update(value=""), gr.update(value=""), gr.update(value=""), gr.update(value="1"),
                        gr.update(value=""),
                        gr.update(value="", interactive=True, visible=True),
                        gr.update(visible=False),
                        gr.update(visible=False),
                        gr.update(interactive=False),  # btn_use
                        _clear_button_update(curr_act or [], False),  # btn_clear_all
                        gr.update(interactive=False),  # btn_reorder_loras
                        gr.update(visible=False),  # edit_row
                        gr.update(value=lora_up_lbl, interactive=False),  # btn_lora_up
                        gr.update(value=lora_down_lbl, interactive=False),  # btn_lora_down
                        gr.update(interactive=False),  # btn_lora_sort
                        gr.update(interactive=False),  # btn_lora_done
                        saved_dir, None)
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
            up_u, down_u, sort_u, done_u = _lora_move_states(real_name, _load_data(saved_dir).get("last_group", ALL_GROUP), data, all_l)
            return (
                gr.update(value=e.get("display_name", "")),
                gr.update(value=os.path.splitext(real_name)[0]),
                gr.update(value=e.get("trigger_words", "")),
                gr.update(value=str(strength)),
                gr.update(value=e.get("info", "")),
                gr.update(value=url, interactive=True, visible=True),
                gr.update(visible=bool(url)),
                gr.update(visible=has_pair, interactive=not both_disabled),  # btn_use_both
                gr.update(interactive=not already),                            # btn_use
                _clear_button_update(curr_act or [], False),                   # btn_clear_all
                gr.update(interactive=True),                                   # btn_reorder_loras
                gr.update(visible=False),                                      # edit_row
                gr.update(value=lora_up_lbl, interactive=up_u.get("interactive", False)),
                gr.update(value=lora_down_lbl, interactive=down_u.get("interactive", False)),
                sort_u, done_u,
                saved_dir, real_name,
            )

        _curr_act_input = loras_comp if loras_comp is not None else gr.State([])
        lora_radio.change(fn=on_lora_change,
                          inputs=[lora_radio, st_dir, st_loras, _curr_act_input],
                          outputs=[disp_name_tb, real_name_tb, tw_tb, str_tb, info_tb,
                                   url_tb, url_btn_row, btn_use_both,
                                   btn_use, btn_clear_all, btn_reorder_loras, edit_row,
                                   btn_lora_up, btn_lora_down, btn_lora_sort, btn_lora_done,
                                   st_dir, st_sel_lora])

        # ── Add / Rename Group ─────────────────────────────────────────
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
                gr.update(visible=True),
                gr.update(value=_lora_move_labels_explicit(_load_settings().get("horizontal_layout", False))[0],
                          interactive=_lora_move_states(real_name, grp, _load_data(saved_dir), cur_loras if cur_loras else live_loras(saved_dir))[0].get("interactive", False)),
                gr.update(value=_lora_move_labels_explicit(_load_settings().get("horizontal_layout", False))[1],
                          interactive=_lora_move_states(real_name, grp, _load_data(saved_dir), cur_loras if cur_loras else live_loras(saved_dir))[1].get("interactive", False)),
                _lora_move_states(real_name, grp, _load_data(saved_dir), cur_loras if cur_loras else live_loras(saved_dir))[2],
                _lora_move_states(real_name, grp, _load_data(saved_dir), cur_loras if cur_loras else live_loras(saved_dir))[3]
            ),
            inputs=[lora_radio, grp_radio, st_dir, st_loras],
            outputs=[lora_manage_row, btn_lora_up, btn_lora_down, btn_lora_sort, btn_lora_done]
        )
        btn_lora_done.click(fn=lambda: gr.update(visible=False), outputs=[lora_manage_row])

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
                gr.update(choices=lo_choices, value=lo_choices[0][1] if lo_choices else None),
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
                          outputs=[grp_radio, lora_radio, grp_name_section, st_action,
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
                gr.update(choices=lo_choices, value=lo_choices[0][1] if lo_choices else None),
                *_btn_states(next_grp, data["groups"]),
                gr.update(interactive=False),
                gr.update(visible=False),
                saved_dir,
                lo_choices[0][1] if lo_choices else None,
            )

        btn_del_yes.click(fn=do_delete_group, inputs=[grp_radio, st_dir],
                          outputs=[grp_radio, lora_radio,
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

        def move_lora(real_name, grp, saved_dir, cur_loras, direction):
            grp = _grp_name(grp)
            if not real_name:
                return gr.update(), gr.update(), gr.update(), gr.update(), saved_dir
            data = _load_data(saved_dir)
            all_l = cur_loras if cur_loras else live_loras(saved_dir)
            ordered = _loras_for_group(data, grp, all_l)
            if real_name not in ordered:
                return gr.update(), gr.update(), gr.update(), gr.update(), saved_dir
            idx = ordered.index(real_name)
            ni = idx + direction
            if 0 <= ni < len(ordered):
                ordered[idx], ordered[ni] = ordered[ni], ordered[idx]
                _set_lora_order(data, grp, ordered)
                _save_data(saved_dir, data)
            lo_choices = _lora_choices_for_radio(data, ordered)
            up_u, down_u, sort_u, done_u = _lora_move_states(real_name, grp, data, all_l)
            return (
                gr.update(choices=lo_choices, value=real_name),
                up_u,
                down_u,
                sort_u,
                done_u,
                saved_dir,
            )

        btn_lora_up.click(fn=lambda l, g, d, ls: move_lora(l, g, d, ls, -1),
                          inputs=[lora_radio, grp_radio, st_dir, st_loras],
                          outputs=[lora_radio, btn_lora_up, btn_lora_down, btn_lora_sort, btn_lora_done, st_dir])
        btn_lora_down.click(fn=lambda l, g, d, ls: move_lora(l, g, d, ls, +1),
                            inputs=[lora_radio, grp_radio, st_dir, st_loras],
                            outputs=[lora_radio, btn_lora_up, btn_lora_down, btn_lora_sort, btn_lora_done, st_dir])

        def sort_loras_by_name(real_name, grp, saved_dir, cur_loras):
            grp = _grp_name(grp)
            data = _load_data(saved_dir)
            all_l = cur_loras if cur_loras else live_loras(saved_dir)
            ordered = _loras_for_group(data, grp, all_l)
            ordered = sorted(ordered, key=lambda name: _display_name_for_sort(data, name))
            _set_lora_order(data, grp, ordered)
            _save_data(saved_dir, data)
            selected = real_name if real_name in ordered else (ordered[0] if ordered else None)
            lo_choices = _lora_choices_for_radio(data, ordered)
            up_u, down_u, sort_u, done_u = _lora_move_states(selected, grp, data, all_l)
            return (
                gr.update(choices=lo_choices, value=selected),
                up_u,
                down_u,
                sort_u,
                done_u,
                saved_dir,
                selected,
            )

        btn_lora_sort.click(fn=sort_loras_by_name,
                            inputs=[lora_radio, grp_radio, st_dir, st_loras],
                            outputs=[lora_radio, btn_lora_up, btn_lora_down, btn_lora_sort, btn_lora_done, st_dir, st_sel_lora])

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
            all_l = cur_loras if cur_loras else live_loras(saved_dir)
            for l in all_l:
                e = _ensure_lora(data, l, saved_dir)
                if grp in e["groups"]:
                    e["groups"].remove(grp)
            for l in (selected or []):
                e = _ensure_lora(data, l, saved_dir)
                if grp not in e["groups"]:
                    e["groups"].append(grp)
            _save_data(saved_dir, data)
            loras      = _loras_for_group(data, grp, all_l)
            lo_choices = _lora_choices_for_radio(data, loras)
            return (gr.update(visible=False), gr.update(visible=False),
                    gr.update(choices=lo_choices,
                              value=lo_choices[0][1] if lo_choices else None),
                    saved_dir,
                    lo_choices[0][1] if lo_choices else None)

        btn_save_assign.click(fn=save_assign,
                              inputs=[grp_radio, assign_dd, st_dir, st_loras],
                              outputs=[assign_dd, assign_row, lora_radio, st_dir, st_sel_lora])
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

        def use_lora(real_name, curr_act, curr_mult, curr_prompt, trigger_words_mode, saved_dir):
            if not real_name:
                return gr.update(), gr.update(), gr.update(), gr.update(interactive=False), saved_dir
            val       = lora_val(real_name)
            activated = list(curr_act) if curr_act else []
            already   = val in activated
            activated, new_mult, new_prompt = _activate_single(
                real_name, curr_act, curr_mult, curr_prompt, trigger_words_mode, saved_dir)
            if trigger_words_mode == TRIGGER_WORDS_REPLACE:
                new_prompt = _build_replace_prompt(activated, saved_dir)
            # Save last used lora for this group in Settings.json (safe — no lora data)
            if not already:
                data    = _load_data(saved_dir)
                cur_grp = data.get("last_group", ALL_GROUP)
                settings = _load_settings()
                key = _last_used_key(saved_dir)
                if key:
                    settings.setdefault(key, {})[cur_grp] = real_name
                    _save_settings(settings)
            return (gr.update(value=activated), gr.update(value=new_mult),
                    gr.update(value=new_prompt), gr.update(interactive=False), saved_dir)

        def use_both(real_name, curr_act, curr_mult, curr_prompt,
                     trigger_words_mode, saved_dir, cur_loras):
            if not real_name:
                return gr.update(), gr.update(), gr.update(), gr.update(interactive=False), saved_dir
            all_l     = cur_loras if cur_loras else live_loras(saved_dir)
            high, low = _find_pair(real_name, all_l, saved_dir)
            if high is None or low is None:
                return gr.update(), gr.update(), gr.update(), gr.update(interactive=False), saved_dir
            activated = list(curr_act) if curr_act else []
            new_mult  = curr_mult or ""
            new_prompt = curr_prompt or ""
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
            # Save last used lora (the one selected in the listbox)
            data    = _load_data(saved_dir)
            cur_grp = data.get("last_group", ALL_GROUP)
            settings = _load_settings()
            key = _last_used_key(saved_dir)
            if key:
                settings.setdefault(key, {})[cur_grp] = real_name
                _save_settings(settings)
            return (gr.update(value=activated), gr.update(value=new_mult),
                    gr.update(value=new_prompt), gr.update(interactive=False), saved_dir)

        _use_in_base = [
            loras_comp  if loras_comp  is not None else gr.State([]),
            mult_comp   if mult_comp   is not None else gr.State(""),
            prompt_comp if prompt_comp is not None else gr.State(""),
            trigger_words_dd, st_dir,
        ]
        _use_out = []
        if loras_comp  is not None: _use_out.append(loras_comp)
        if mult_comp   is not None: _use_out.append(mult_comp)
        if prompt_comp is not None: _use_out.append(prompt_comp)

        if _use_out:
            def _use_wrapped(rn, ca, cm, cp, atw, sd):
                act, mult, prompt, btn_upd, ld = use_lora(rn, ca, cm, cp, atw, sd)
                out = []
                if loras_comp  is not None: out.append(act)
                if mult_comp   is not None: out.append(mult)
                if prompt_comp is not None: out.append(prompt)
                out.append(btn_upd)  # btn_use update
                out.append(ld)
                return tuple(out)

            def _use_both_wrapped(rn, ca, cm, cp, atw, sd, cur_l):
                act, mult, prompt, btn_upd, ld = use_both(rn, ca, cm, cp, atw, sd, cur_l)
                out = []
                if loras_comp  is not None: out.append(act)
                if mult_comp   is not None: out.append(mult)
                if prompt_comp is not None: out.append(prompt)
                out.append(btn_upd)  # btn_use_both update
                out.append(ld)
                return tuple(out)

            btn_use.click(fn=_use_wrapped, inputs=[lora_radio] + _use_in_base,
                          outputs=_use_out + [btn_use, st_dir])
            btn_use_both.click(fn=_use_both_wrapped,
                               inputs=[lora_radio] + _use_in_base + [st_loras],
                               outputs=_use_out + [btn_use_both, st_dir])

        def clear_all_activated(curr_act, curr_mult, undo_mode, saved_loras, saved_mult):
            current_active = list(curr_act) if curr_act else []
            current_mult = curr_mult or ""
            if undo_mode:
                restored_active = list(saved_loras) if saved_loras else []
                restored_mult = saved_mult or ""
                return (
                    gr.update(value=restored_active),
                    gr.update(value=restored_mult),
                    _clear_button_update(restored_active, False),
                    [],
                    "",
                    False,
                    None,
                )
            return (
                gr.update(value=[]),
                gr.update(value=""),
                _clear_button_update([], True),
                current_active,
                current_mult,
                True,
                [],
            )

        if loras_comp is not None and mult_comp is not None:
            btn_clear_all.click(
                fn=clear_all_activated,
                inputs=[loras_comp, mult_comp, st_clear_mode, st_clear_loras, st_clear_mult],
                outputs=[loras_comp, mult_comp, btn_clear_all, st_clear_loras, st_clear_mult, st_clear_mode, st_clear_expected],
            )

        # ── Edit Lora ──────────────────────────────────────────────────
        def _show_metadata_actions(real_name):
            return gr.update(visible=bool(real_name))

        for tb in (disp_name_tb, tw_tb, str_tb, info_tb, url_tb):
            tb.input(fn=_show_metadata_actions, inputs=[lora_radio], outputs=[edit_row])

        def save_edit(real_name, disp_name, tw, strength, info_text, url, cur_grp, saved_dir, cur_loras):
            cur_grp = _grp_name(cur_grp)
            if real_name and saved_dir:
                clean_disp = (disp_name or "").strip()
                data = _load_data(saved_dir)
                if clean_disp and not _is_display_name_unique(data, real_name, clean_disp):
                    gr.Warning(f"The display name '{clean_disp}' is already used.")
                    return (gr.update(),) * 12
                e = _ensure_lora(data, real_name, saved_dir)
                e["display_name"]     = clean_disp
                e["trigger_words"]    = (tw or "").strip()
                e["default_strength"] = (strength or "1").strip() or "1"
                e["info"]             = (info_text or "").strip()
                e["url"]              = (url or "").strip()
                _save_data(saved_dir, data)
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
                gr.update(choices=lo_choices, value=safe_val),
                saved_dir,
                safe_val,
            )

        btn_save_edit.click(fn=save_edit,
                            inputs=[lora_radio, disp_name_tb, tw_tb, str_tb,
                                    info_tb, url_tb, grp_radio, st_dir, st_loras],
                            outputs=[disp_name_tb, real_name_tb, tw_tb, str_tb, info_tb,
                                     url_tb, url_btn_row, edit_row,
                                     btn_use_both, lora_radio, st_dir, st_sel_lora])

        def cancel_edit(real_name, saved_dir, cur_loras):
            pair_btn_u = _use_both_button_state(real_name, saved_dir, cur_loras if cur_loras else live_loras(saved_dir))
            return (*_metadata_updates(real_name or "", saved_dir, False),
                    pair_btn_u,
                    gr.update(value=real_name),
                    saved_dir)

        btn_cancel_edit.click(fn=cancel_edit, inputs=[lora_radio, st_dir, st_loras],
                              outputs=[disp_name_tb, real_name_tb, tw_tb, str_tb, info_tb,
                                       url_tb, url_btn_row, edit_row,
                                       btn_use_both, lora_radio, st_dir])

        # ── Open URL ───────────────────────────────────────────────────
        btn_open_url.click(
            fn=lambda url: url,
            inputs=[url_tb], outputs=[url_tb],
            js="(url) => { if(url && url.trim()) window.open(url.trim(), '_blank', 'noopener,noreferrer'); return url; }",
        )

        # ── Settings: Save button ──────────────────────────────────────
        def save_settings_cb(trigger_words_mode, acc_open, meta_acc_open, hide_all, horiz, side, height, saved_dir, cur_loras):
            settings = _load_settings()
            settings["trigger_words_mode"]    = trigger_words_mode
            settings["accordion_open"]        = acc_open
            settings["metadata_accordion_open"] = meta_acc_open
            settings["hide_all_group"]        = hide_all
            settings["horizontal_layout"]     = horiz
            settings["side_by_side"]          = side
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
            sel_lora = lo_choices[0][1] if lo_choices else None
            btn_rename_u, btn_del_u, btn_up_u, btn_down_u, btn_assign_u = _btn_states(selected_grp, data["groups"])
            btn_up_interactive = btn_up_u.get("interactive", False) if isinstance(btn_up_u, dict) else False
            btn_down_interactive = btn_down_u.get("interactive", False) if isinstance(btn_down_u, dict) else False
            group_up_lbl, group_down_lbl = _group_move_labels_explicit()
            lora_up_lbl, lora_down_lbl = _lora_move_labels_explicit(horiz)
            has_lora = bool(lo_choices)
            return (
                gr.update(value=_orient_html(horiz)),       # orient_html
                gr.update(value=group_up_lbl, interactive=btn_up_interactive),    # btn_up
                gr.update(value=group_down_lbl, interactive=btn_down_interactive),# btn_down
                gr.update(value=_listbox_height_css(int(height))),  # height_html
                gr.update(open=meta_acc_open),                                         # metadata_accordion
                gr.update(choices=(_grp_choices:=_group_choices(data)),
                          value=_find_choice_val(_grp_choices, selected_grp)),    # grp_radio
                gr.update(choices=lo_choices, value=sel_lora),                    # lora_radio
                gr.update(value=lora_up_lbl),                                     # btn_lora_up
                gr.update(value=lora_down_lbl),                                   # btn_lora_down
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
            inputs=[trigger_words_dd, acc_open_cb, meta_acc_open_cb, hide_all_cb, horiz_cb, side_cb, height_sl, st_dir, st_loras],
            outputs=[orient_html, btn_up, btn_down, height_html, metadata_accordion,
                     grp_radio, lora_radio, btn_lora_up, btn_lora_down,
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
                "    }, 3000);"
                "  }"
                "  return args;"
                "}"
            ),
        )

        return grp_radio


# ---------------------------------------------------------------------------
plugin = LoraOrganizerPlugin()
