# Bubble Card Tools

**Bubble Card Tools** is the companion backend for **Bubble Card**. It adds a safe, local API that installs, edits, and removes Bubble Card modules as separated YAML files. It powers the **Module Store** and is **required** to manage modules from the UI.
It is designed to grow with new features.

## Requirements

* [Home Assistant](https://www.home-assistant.io/) (recent stable)
* [Bubble Card](https://github.com/Clooos/Bubble-Card) (v3.1.0 or later) installed

## Install

* **HACS (recommended):**
  * Add repository → Install → Restart Home Assistant
      
    <img width="301" height="475" alt="image" src="https://github.com/user-attachments/assets/0608c0fb-7f76-4007-a130-43d3244bc2e7" />

* **Manual:** Copy `custom_components/bubble_card_tools/` into `/config/custom_components/` → Restart Home Assistant

## Configure in Home Assistant

<a href="https://my.home-assistant.io/redirect/config_flow_start?domain=bubble_card_tools" class="my badge" target="_blank"><img src="https://my.home-assistant.io/badges/config_flow_start.svg"></a>

1. Go to **Settings → Devices & Services → Add Integration**
2. Search **Bubble Card Tools** and add it
3. The integration creates the base path:

   * Base: `/config/bubble_card`
   * Modules: `/config/bubble_card/modules`

## How it works

* Modules are stored as separate YAML files (e.g. `modules/my_module.yaml`)
* Fast, local WebSocket API used by the editor and the **Module Store**
* Strict validation, safe filenames, size limits, and update events

## Typical actions (handled by the UI)

* List modules, open and edit, create new, delete
* Import from the Module Store
* Receive live update events when files change

## Migration (if you used the old method)

* If legacy modules exist (sensor or `bubble-modules.yaml`), the editor will guide you to **migrate** them into files
* Migration keeps legacy data untouched for safe rollback
* After migration, files become the single source of truth

## Security and privacy

* Local-only, no external services
* No secrets needed; keep sensitive data outside public paths
* Enforces safe names and size limits for YAML files

## Troubleshooting

* After install, **restart Home Assistant** and add the integration
* If the UI says “Unknown command,” the integration is not loaded; check logs and folder paths
* For support, include HA version, logs, and steps to reproduce

## Built for growth

* Event-driven updates for responsive UIs
* File layout ready for future module types and tooling
* Clean separation between frontend editor and backend storage

---


