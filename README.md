# trying to fix a multiplicity of issues of the original code here
1. Original  code has problems to roubstly have a time_triggered instance of on_time() running. Often there was no instance.
2. Works now with hybrid systems like Fenecon Home. System has a battery and a combined power sensor for import/export. Original code rejected working with this.
3. Original code did not work with car chargers/wallboxes that do not report power
4. Power on dynamic appliances like car chargers works now also if appliance does not immediately change power
5. Car Chargers afaik only work with whole numbers for the current value
6. Added a toggle on margin of 200W to avoid on/off sequences#
   
# ha-advanced-blueprints
Advanced Home Assistant Blueprints combined with pyscript for extra useful automations

If you like my work, you can support me here:\
[<img src="https://user-images.githubusercontent.com/1286821/181085373-12eee197-187a-4438-90fe-571ac6d68900.png" alt="Buy me a coffee" width="200" />](https://buymeacoffee.com/henrikIC)

## Prerequisites
- A working installation of [pyscript](https://github.com/custom-components/pyscript) (can be installed via [HACS](https://hacs.xyz/))
- Home Assistant v2023.1 or greater

## Documentation
See seperate README within sub-folders
