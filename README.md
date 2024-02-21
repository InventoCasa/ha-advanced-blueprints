# trying to extend & fix a multiplicity of issues of the original code
1. Original  code has problems to roubstly have a time_triggered instance of on_time() running. Often there was no instance.
2. Works now with hybrid systems like Fenecon Home. System has a battery and a combined power sensor for import/export. Original code rejected working with this.
3. Original code did not work with car chargers/wallboxes that do not report power
4. Power on dynamic appliances like car chargers works now also if appliance does not immediately change power
5. Car Chargers afaik only work with whole numbers for the current value
6. Added a toggle on margin setting to avoid on/off sequences
7. Added a setting to for inverter limited PV systems
   
# Find the original repository here
https://github.com/InventoCasa/ha-advanced-blueprints/
