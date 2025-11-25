# Bubble Card Tools (WIP)

**Bubble Card Tools** is the companion backend for **Bubble Card**. It adds a safe, local API that installs, edits, and removes Bubble Card modules as separated YAML files. It powers the **Module Store** and is **required** to manage modules from the UI.
It is designed to grow with new features.

## Requirements

* [Home Assistant](https://www.home-assistant.io/) (recent stable)
* [Bubble Card](https://github.com/Clooos/Bubble-Card) (v3.1.0 or later) installed

## Install

* **HACS (recommended):**
  * In HACS, go to the menu in the top right corner, then go to "Custom repositories" (it will soon be added natively in HACS).
      
    <img width="301" height="475" alt="image" src="https://github.com/user-attachments/assets/0608c0fb-7f76-4007-a130-43d3244bc2e7" />  

  * Then add `https://github.com/Clooos/Bubble-Card-Tools` as the repository and select "Integration". After that, click on "Add".
    
    <img width="583" height="249" alt="image" src="https://github.com/user-attachments/assets/8bc9c242-363d-4bfb-893a-449232a806a1" />


* **Manual:** Copy `custom_components/bubble_card_tools/` into `/config/custom_components/` → Restart Home Assistant

## Configure in Home Assistant

<a href="https://my.home-assistant.io/redirect/config_flow_start?domain=bubble_card_tools" class="my badge" target="_blank"><img src="https://my.home-assistant.io/badges/config_flow_start.svg"></a>

1. Go to **Settings → Devices & Services → Add Integration**
2. Search **Bubble Card Tools** and add it
3. The integration creates the base path:

   * Base: `/config/bubble_card`
   * Modules: `/config/bubble_card/modules`

## Migration (if you used the old method)

* If legacy modules exist (sensor or `bubble-modules.yaml`), the migration will be made automatically
* Migration keeps legacy data untouched for safe rollback
* After migration, files become the single source of truth

## Security and privacy

* Local-only, no external services
* No secrets needed; keep sensitive data outside public paths
* Enforces safe names and size limits for YAML files

## Troubleshooting

* After install, **restart Home Assistant** and add the integration
* If the UI says “Unknown command,” the integration is not loaded, check logs and folder paths
* For support, include HA version, logs, and steps to reproduce


