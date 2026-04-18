# Lora Organizer

Lora Organizer is a plugin for [Wan2GP](https://github.com/deepbeepmeep/Wan2GP).

It adds a UI that lets you organize loras into groups and subgroups, store metadata, and activate loras with their trigger words and strength in one click.

## Features

- Create, rename, delete, and reorder groups.
- Create nested subgroups.
- Expand and collapse group branches in the groups list.
- Assign loras to groups.
- Reorder loras inside a group with drag and drop.
- Sort loras in the current group by name.
- Sort loras in the current group by most used.
- Auto-sort loras by name or most used.
- Change the display name of a lora so long filenames can be shown with shorter, cleaner names without changing the original file.
- Store per-lora metadata:
  - trigger words
  - default strength
  - notes
  - URL
  - preview images
- Activate a lora with one click using its saved default strength, and apply its trigger words based on the selected trigger-word behavior.
- Activate matched Wan 2.2 high/low lora pairs with one click when available.
- Automatically detect Wan 2.2 high/low loras and assign `1;0` as the default strength for high loras and `0;1` for low loras.
- Clear all activated loras and restore them if needed.
- Optionally remove trigger words from the prompt when deactivating loras.
- Display loras in:
  - vertical list view
  - horizontal list view
  - thumbnail view
- Use preview images as lora thumbnails in thumbnail view.
- Cycle thumbnail preview images when hovering, auto-cycle them, or keep them static.
- Use a custom activated-loras control that shows activated loras and strengths in one place.
- Edit activated-lora strengths inline.
- Reorder activated loras.
- Remove activated loras directly from the custom activated-loras control.
- Place Lora Organizer:
  - in the lora tab
  - below the prompt in the main tab
  - in its own tab
- Adjust groups listbox width in side-by-side view.
- Choose how trigger words are applied:
  - add to the beginning of the prompt
  - add to the end of the prompt
  - replace the prompt with trigger words from all activated loras
  - do not add trigger words

## Installation

1. Open the `Plugins` tab in Wan2GP.
2. Paste this repository URL into the `GitHub URL` textbox:

   `https://github.com/ppc2017/wan2gp-lora-organizer`

3. Click `Download and Install from URL`.
4. Restart Wan2GP if needed.

## How It Works

The plugin can be shown:

- in the lora tab
- below the prompt in the main tab
- in its own tab

Inside it you can:

- browse groups and subgroups
- browse loras in the selected group
- manage group structure
- manage lora metadata
- activate loras directly from the organizer
- manage activated loras from the custom activated-loras list

## Metadata

Each lora can store:

- Display Name
- Trigger Words
- Default Strength
- Info / Notes
- Lora URL
- Preview Images

Metadata fields are always editable. When you change a field, `Save Changes` and `Cancel` appear.

Preview images are stored in the plugin data folder under `data/images/<model>/...`.
The first preview image is used as the lora thumbnail in thumbnail view.

## Settings

The plugin includes settings for:

- lora organizer placement
- trigger words behavior
- remove trigger words from the prompt when deactivating loras
- lora list view mode
- thumbnail image cycling
- thumbnails per row
- fit thumbnail images without cropping
- groups listbox max width in side-by-side view
- start with Lora Organizer expanded
- start with Lora Metadata expanded
- hide the `All` group
- arrange group and lora listboxes side by side
- listbox max height

## Data Storage

The plugin stores its data in JSON files in the plugin folder for the active lora folder/model context.

This includes:

- groups and subgroups
- group order
- lora order
- metadata
- preview image order
- usage counts
- plugin settings

The lora files themselves are not modified.

## Notes

- Group/subgroup structure is saved and restored from JSON.
- The `All` group can be hidden from settings.
- Group data is effectively tied to the active lora directory, so different model contexts can have different organizer data.

## Status

Current plugin version: `1.1`
