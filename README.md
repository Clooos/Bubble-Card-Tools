# Bubble Card Tools

**Bubble Card Tools** is a custom integration for Home Assistant that handles the **Bubble Card** backend. It adds a safe, local API that installs, edits, and removes Bubble Card modules as separated YAML files. It powers the **Module Store** and is **required** to manage modules from the UI.
It is designed to grow with new features.

[![Stars](https://img.shields.io/github/stars/clooos/Bubble-Card-Tools)](#) [![Last commit](https://img.shields.io/github/last-commit/clooos/Bubble-Card-Tools)](#) [![YouTube](https://img.shields.io/badge/YouTube-My%20channel-red?logo=youtube)](https://www.youtube.com/@cloooos) [![Reddit Page](https://img.shields.io/badge/Reddit-r/BubbleCard-orange?logo=reddit)](https://www.reddit.com/r/BubbleCard/) [![Reddit Profile](https://img.shields.io/badge/Reddit-My%20stuff-orange?logo=reddit)](https://www.reddit.com/user/Clooooos/submitted/) [![Home Assistant Community Forum](https://img.shields.io/badge/Home%20Assistant-Community%20Forum-blue?logo=home-assistant)](https://community.home-assistant.io/t/bubble-card-a-minimalist-card-collection-for-home-assistant-with-a-nice-pop-up-touch/609678) [![Buy me a beer](https://img.shields.io/badge/Donate-Buy%20me%20a%20beer-yellow?logo=buy-me-a-coffee)](https://www.buymeacoffee.com/clooos) [![PayPal](https://img.shields.io/badge/Donate-PayPal-blue?logo=paypal)](https://www.paypal.com/donate/?business=MRVBV9PLT9ZPL&no_recurring=0&item_name=Hi%2C+I%27m+Clooos+the+creator+of+Bubble+Card.+Thank+you+for+supporting+me+and+my+passion.+You+are+awesome%21+%F0%9F%8D%BB&currency_code=EUR) [![Patreon Clooos](https://img.shields.io/badge/Patreon-Clooos-orange?logo=patreon)](https://www.patreon.com/Clooos)

<br>

## Installation

#### Requirements

* [Home Assistant](https://www.home-assistant.io/) (recent stable)
* [Bubble Card](https://github.com/Clooos/Bubble-Card) (v3.1.0 and up) installed

<br>

<details>

<summary>Without HACS</summary>

<br>

1. Copy the `bubble_card_tools` folder from `custom_components/bubble_card_tools/` into `/config/custom_components/`
2. Restart Home Assistant

<br>

</details>

<details>

<summary>With HACS (Recommended)</summary>

<br>

This method allows you to get updates directly on the HACS main page

1. In HACS, go to the menu in the top right corner, then go to "Custom repositories" (it will soon be added natively in HACS).
    
   <img width="301" height="475" alt="image" src="https://github.com/user-attachments/assets/0608c0fb-7f76-4007-a130-43d3244bc2e7" /><br><br>

2. Then add `https://github.com/Clooos/Bubble-Card-Tools` as the repository and select "Integration". After that, click on "Add".
  
   <img width="583" height="249" alt="image" src="https://github.com/user-attachments/assets/8bc9c242-363d-4bfb-893a-449232a806a1" /><br><br>

3. Once it is added, click on "Cancel" next to the "Add" button.

   <img width="598" height="78" alt="image" src="https://github.com/user-attachments/assets/c2ae8724-af22-4db1-acd0-a78ebf6dc744" /><br><br>

4. Now search for "Bubble Card Tools" and click on it. Then finally, click on the "Download" button in the bottom right corner to install it.

   <img width="489" height="313" alt="image" src="https://github.com/user-attachments/assets/f2b71cdf-b5f0-4777-8390-40f6ae783e83" /><br><br>

5. Restart Home Assistant.<br><br>

</details>

<br>

<a href="https://my.home-assistant.io/redirect/config_flow_start?domain=bubble_card_tools" class="my badge" target="_blank"><img src="https://my.home-assistant.io/badges/config_flow_start.svg"></a>

<br>

## Configure in Home Assistant

1. Go to **Settings → Devices & services → Add Integration**
2. Search **Bubble Card Tools** and add it
3. The integration creates the base path:

   * Base: `/config/bubble_card`
   * Modules: `/config/bubble_card/modules`

4. You are all set! Just check in the editor (in Modules) if the warning has been removed.
  
<br>

## Migration (if you used the old method)

* If legacy modules exist (sensor or `bubble-modules.yaml`), the migration will be made automatically
* Migration keeps legacy data untouched for safe rollback
* After migration, files become the single source

<br>

## Troubleshooting

* After install, **restart Home Assistant** and add the integration
* If the UI says “Unknown command,” the integration is not loaded, check logs and folder paths
* For support, include HA version, logs, and steps to reproduce


