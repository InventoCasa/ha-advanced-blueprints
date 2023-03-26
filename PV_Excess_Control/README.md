# PV Excess Control
Automatically control your appliances (wallbox, heatpump, washing machine, ...) based on excess solar power.

If you like my work, you can support me here:\
[<img src="https://user-images.githubusercontent.com/1286821/181085373-12eee197-187a-4438-90fe-571ac6d68900.png" alt="Buy me a coffee" width="200" />](https://buymeacoffee.com/henrikIC)

## Features
:white_check_mark: Configurable priority handling between multiple appliances\
:white_check_mark: Define a *minimum home battery level* before directing PV excess to your specific appliance\
:white_check_mark: Define an *On/Off switch interval* / solar power averaging interval\
:white_check_mark: Supports dynamic current control (e.g. for wallboxes)\
:white_check_mark: Define min. and max. current for appliances supporting dynamic current control\
:white_check_mark: Supports one- and three-phase appliances\
:white_check_mark: Supports *Only-Switch-On* devices like washing machines or dishwashers


## Prerequisites
- A working installation of [pyscript](https://github.com/custom-components/pyscript) (can be installed via [HACS](https://hacs.xyz/))
- Home Assistant v2023.1 or greater
- Access to the following values from your (hybrid) PV inverter:
  - Export power
  - PV Power
  - Load Power
  - (Home battery level)
- Pyscript must be configured to allow all imports. This can be done 
  - either via UI: 
    - Configuration -> Integrations page -> “+” -> Pyscript Python scripting
    - After that, you can change the settings anytime by selecting Options under Pyscript in the Configuration page
  - or via *`configuration.yaml`*:
    ```
    pyscript:
      allow_all_imports: true
    ```

## Installation
- Download (or clone) this GitHub repository
- Copy both folders (*blueprints* and *pyscript*) to your HA config directory, or manually place the automation blueprint **`pv_excess_control.yaml`** and the python module **`pv_excess_control.py`** into their respective folders.
- Configure the desired logging level in your *`configuration.yaml`*:
  ```
  logger:
    logs:
      custom_components.pyscript.file.pv_excess_control: debug
  ```

## Configuration &  Usage
### Initial Configuration
- For each appliance which should be controlled, create a new automation based on the *PV Excess Control* blueprint
- After creating the automation, manually execute it once. This will send the chosen configuration parameters and sensors to the python module and start the optimizer in the background
- The python module stays active in background, even if HA or the complete system is restarted

### Update
- To update the configuration, simply update the chosen parameters and values in your automation, which was created based on the blueprint.
- After that, manually execute the automation once to send the changes to the python module

### Deactivation
- To deactivate the auto-control of a single appliance, simply deactivate the related automation.

### Deletion
- To remove the auto-control of a single appliance, simply delete the related automation.