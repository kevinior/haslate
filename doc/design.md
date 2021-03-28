# HAslate Application design

Briefly:

* pygame for the UI
* Interface to Home Assistant using the [websocket API]
* Configuration from file in USB-accessed partition

## Configuration

* USB mass-storage gadget mode
* When disconnected we mount the partition and check for config changes
* Things that can be configured:
  * Wifi settings
  * Hostname
  * Timezone
  * Home Assistant API URL and token
  * UI

## Main UI

* Configurable layout of entities:
  * Home Assistant entities
  * Local:
    * Battery status
    * Time
    * Date
    * etc.
* At the top level everything is a button
* Entities can be displayed in different formats (text, graph,
  gauge, etc.) (most formats not implemented)
* Clicking on a button can pop up a dialog for complex entities (not implemented)

### UI layout config

* Grid, configure how many cells in each direction
* Each button is configured in terms of top-left, width, height
* If screen is 1448x1072, roughly 300 dpi (118 px/cm), minimum button
  size 1 cm => ~120 px minimum button size?
* That gives us about 12 x 8 button grid

[websocket API]: https://developers.home-assistant.io/docs/api/websocket/
