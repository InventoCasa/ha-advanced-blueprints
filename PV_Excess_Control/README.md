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

## Usage
TODO

## Blueprint configuration parameters