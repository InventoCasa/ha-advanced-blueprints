# PV Excess Control

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
- Copy both folders to your HA config directory, or manually place the automation blueprint **`pv_excess_control.yaml`** and the python module **`pv_excess_control.py`** into their respective folders.
- Configure the desired logging level in your *`configuration.yaml`*:
  ```
  logger:
    logs:
        custom_components.pyscript.file.pv_excess_control: debug
  ```

## Configuration &  Usage
### Initial Configuration
- For each appliance which should be controlled, create a new automation based on the *PV Excess Optimizer* blueprint
- After creating the automation, manually execute it once. This will send the chosen configuration parameters and sensors to the python module and start the optimizer in the background
- The python module stays active in background, even if HA or the complete system is restarted

### Update
- To update the configuration, simply update the chosen parameters and values in your automation, which was created based on the blueprint.
- After that, manually execute the automation once to send the changes to the python module

### Deactivation
- To deactivate the auto-control of a single appliance, simply deactivate the related automation.

### Deletion
- To remove the auto-control of a single appliance, simply delete the related automation.

## Blueprint configuration parameters
TODO