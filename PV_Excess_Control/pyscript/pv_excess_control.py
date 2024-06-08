# INFO --------------------------------------------
# This is intended to be called once manually or on startup. See blueprint.
# Automations can be deactivated correctly from the UI!
# -------------------------------------------------
from typing import Union
import datetime


def _get_state(entity_id: str) -> Union[str, None]:
    """
    Get the state of an entity in Home Assistant
    :param entity_id:  Name of the entity
    :return:            State if entity name is valid, else None
    """
    # get entity domain
    domain = entity_id.split('.')[0]
    try:
        entity_state = state.get(entity_id)
    except Exception as e:
        log.error(f'Could not get state from entity {entity_id}: {e}')
        return None

    if domain == 'climate':
        if entity_state.lower() in ['heat', 'cool', 'boost', 'on']:
            return 'on'
        elif entity_state == 'off':
            return entity_state
        else:
            log.error(f'Entity state not supported: {entity_state}')
            return None

    else:
        return entity_state


def _turn_off(entity_id: str) -> bool:
    """
    Switches an entity off
    :param entity_id: ID of the entity
    """
    # get entity domain
    domain = entity_id.split('.')[0]
    # check if service exists:
    if not service.has_service(domain, 'turn_off'):
        log.error(f'Cannot switch off appliance: Service "{domain}.turn_off" does not exist.')
        return False

    try:
        service.call(domain, 'turn_off', entity_id=entity_id)
    except Exception as e:
        log.error(f'Cannot switch off appliance: {e}')
        return False
    else:
        return True


def _turn_on(entity_id: str) -> bool:
    """
    Switches an entity on
    :param entity_id: ID of the entity
    """
    # get entity domain
    domain = entity_id.split('.')[0]
    # check if service exists:
    if not service.has_service(domain, 'turn_on'):
        log.error(f'Cannot switch on appliance: Service "{domain}.turn_on" does not exist.')
        return False

    try:
        service.call(domain, 'turn_on', entity_id=entity_id)
    except Exception as e:
        log.error(f'Cannot switch on appliance: {e}')
        return False
    else:
        return True


def _set_value(entity_id: str, value: Union[int, float, str]) -> bool:
    """
    Sets a number entity to a specific value
    :param entity_id: ID of the entity
    :param value: Numerical value
    :return:
    """
    # get entity domain
    domain = entity_id.split('.')[0]
    # check if service exists:
    if not service.has_service(domain, 'set_value'):
        log.error(f'Cannot set value "{value}": Service "{domain}.set_value" does not exist.')
        return False

    try:
        service.call(domain, 'set_value', entity_id=entity_id, value=value)
    except Exception as e:
        log.error(f'Cannot set value "{value}": {e}')
        return False
    else:
        return True


def _get_num_state(entity_id: str, return_on_error: Union[float, None] = None) -> Union[float, None]:
    return _validate_number(_get_state(entity_id), return_on_error)


def _validate_number(num: Union[float, str], return_on_error: Union[float, None] = None) -> Union[float, None]:
    """
    Validate, if the passed variable is a number between 0 and 1000000.
    :param num:             Number
    :param return_on_error: Value to return in case of error
    :return:                Number if valid, else None
    """
    if num is None or num == 'unavailable':
        return return_on_error

    min_v = -1000000
    max_v = 1000000
    try:
        if min_v <= float(num) <= max_v:
            return float(num)
        else:
            raise Exception(f'{float(num)} not in range: [{min_v}, {max_v}]')
    except Exception as e:
        log.error(f'{num=} is not a valid number between 0 and 1000000: {e}')
        return return_on_error


def _replace_vowels(input: str) -> str:
    """
    Function to replace lowercase vowels in a string
    :param input:   Input string
    :return:        String with replaced vowels
    """
    vowel_replacement = {'ä': 'a', 'ö': 'o', 'ü': 'u'}
    res = [vowel_replacement[v] if v in vowel_replacement else v for v in input]
    return ''.join(res)


@time_trigger("cron(0 0 * * *)")
def reset_midnight():
    log.info("Resetting 'switched_on_today' instance variables.")
    for e in PvExcessControl.instances.copy().values():
        inst = e['instance']
        inst.switched_on_today = False
        inst.daily_run_time = 0


@service
def pv_excess_control(automation_id, appliance_priority, export_power, pv_power, load_power, home_battery_level,
                      min_home_battery_level, dynamic_current_appliance, appliance_phases, min_current,
                      max_current, appliance_switch, appliance_switch_interval, appliance_current_set_entity,
                      actual_power, defined_current, appliance_on_only, grid_voltage, import_export_power,
                      home_battery_capacity, solar_production_forecast, appliance_once_only):

    automation_id = automation_id[11:] if automation_id[:11] == 'automation.' else automation_id
    automation_id = _replace_vowels(f"automation.{automation_id.strip().replace(' ', '_').lower()}")


    PvExcessControl(automation_id, appliance_priority, export_power, pv_power,
                    load_power, home_battery_level, min_home_battery_level,
                    dynamic_current_appliance, appliance_phases, min_current,
                    max_current, appliance_switch, appliance_switch_interval,
                    appliance_current_set_entity, actual_power, defined_current, appliance_on_only,
                    grid_voltage, import_export_power, home_battery_capacity, solar_production_forecast,
                    appliance_once_only)



class PvExcessControl:
    # TODO:
    #  - What about other domains than switches? Enable use of other domains (e.g. light, ...)
    #  - Make min_excess_power configurable via blueprint
    #  - Implement updating of pv sensors history more often. E.g. every 10secs, and averaging + adding to history every minute.
    instances = {}
    export_power = None
    pv_power = None
    load_power = None
    home_battery_level = None
    grid_voltage = None
    import_export_power = None
    home_battery_capacity = None
    solar_production_forecast = None
    min_home_battery_level = None
    # Exported Power history
    export_history = [0]*60
    export_history_buffer = []
    # PV Excess history (PV power minus load power)
    pv_history = [0]*60
    pv_history_buffer = []
    # Minimum excess power in watts. If the average min_excess_power at the specified appliance switch interval is greater than the actual
    #  excess power, the appliance with the lowest priority will be shut off.
    #  NOTE: Should be slightly negative, to compensate for inaccurate power corrections
    #  WARNING: Do net set this to more than 0, otherwise some devices with dynamic current control will abruptly get switched off in some
    #  situations.
    min_excess_power = -10
    on_time_counter = 0


    def __init__(self, automation_id, appliance_priority, export_power, pv_power, load_power, home_battery_level,
                 min_home_battery_level, dynamic_current_appliance, appliance_phases, min_current,
                 max_current, appliance_switch, appliance_switch_interval, appliance_current_set_entity,
                 actual_power, defined_current, appliance_on_only, grid_voltage, import_export_power,
                 home_battery_capacity, solar_production_forecast, appliance_once_only):
        if automation_id not in PvExcessControl.instances:
            inst = self
        else:
            inst = PvExcessControl.instances[automation_id]['instance']
        inst.automation_id = automation_id
        inst.appliance_priority = int(appliance_priority)
        PvExcessControl.export_power = export_power
        PvExcessControl.pv_power = pv_power
        PvExcessControl.load_power = load_power
        PvExcessControl.home_battery_level = home_battery_level
        PvExcessControl.grid_voltage = grid_voltage
        PvExcessControl.import_export_power = import_export_power
        PvExcessControl.home_battery_capacity = home_battery_capacity
        PvExcessControl.solar_production_forecast = solar_production_forecast
        PvExcessControl.min_home_battery_level = float(min_home_battery_level)

        inst.dynamic_current_appliance = bool(dynamic_current_appliance)
        inst.min_current = float(min_current)
        inst.max_current = float(max_current)
        inst.appliance_switch = appliance_switch
        inst.appliance_switch_interval = int(appliance_switch_interval)
        inst.appliance_current_set_entity = appliance_current_set_entity
        inst.actual_power = actual_power
        inst.defined_current = float(defined_current)
        inst.appliance_on_only = bool(appliance_on_only)
        inst.appliance_once_only = appliance_once_only

        inst.phases = appliance_phases

        inst.log_prefix = f'[{inst.appliance_switch} {inst.automation_id} (Prio {inst.appliance_priority})]'
        inst.domain = inst.appliance_switch.split('.')[0]


        # start if needed
        if inst.automation_id not in PvExcessControl.instances:
            inst.switched_on_today = False
            inst.switch_interval_counter = 0
            inst.switched_on_time = datetime.datetime.now()
            inst.daily_run_time = 0
            inst.trigger_factory()
            PvExcessControl.instances[inst.automation_id] = {'instance': inst, 'priority': inst.appliance_priority}
            log.info(f'{self.log_prefix} Trigger Method started.')
        PvExcessControl.instances = dict(sorted(PvExcessControl.instances.items(), key=lambda item: item[1]['priority'], reverse=True))
        log.info(f'{inst.log_prefix} Registered appliance.')

    def trigger_factory(self):
        # trigger every 10s
        @time_trigger('period(now, 10s)')
        def on_time():
            # Sanity check
            if (not PvExcessControl.instances) or (not self.sanity_check()):
                return on_time
                
            # execute only if this the first instance of the dictionary (avoid two automations acting)
            #log.info(f'{self.log_prefix} I am around.')
            first_item = next(iter(PvExcessControl.instances.values()))
            if first_item["instance"] != self:
                return on_time                

            PvExcessControl.on_time_counter += 1
            PvExcessControl._update_pv_history()
            # ensure that control algo only runs every minute (= every 6th on_time trigger)
            if PvExcessControl.on_time_counter % 6 != 0:
                return on_time
            PvExcessControl.on_time_counter = 0

            # ----------------------------------- go through each appliance (highest prio to lowest) ---------------------------------------
            # this is for determining which devices can be switched on
            instances = []
            switched_off_appliance_to_switch_on_higher_prioritized_one = False
            for a_id, e in PvExcessControl.instances.copy().items():
                inst = e['instance']
                inst.switch_interval_counter += 1
                log_prefix = inst.log_prefix

                # Check if automation is activated for specific instance
                if not self.automation_activated(inst.automation_id):
                    continue

                # check min bat lvl and decide whether to regard export power or solar power minus load power
                if PvExcessControl.home_battery_level is None:
                    home_battery_level = 100
                else:
                    home_battery_level = _get_num_state(PvExcessControl.home_battery_level)
                if home_battery_level >= PvExcessControl.min_home_battery_level or not self._force_charge_battery():
                    # home battery charge is high enough to direct solar power to appliances, if solar power is higher than load power
                    # calc avg based on pv excess (solar power - load power) according to specified window
                    avg_excess_power = int(sum(PvExcessControl.pv_history[-max(inst.appliance_switch_interval,1):]) / max([1,inst.appliance_switch_interval]))
                    log.debug(f'{log_prefix} Home battery charge is sufficient ({home_battery_level}/{PvExcessControl.min_home_battery_level} %)'
                              f' OR remaining solar forecast is higher than remaining capacity of home battery. '
                              f'Calculated average excess power based on >> solar power - load power <<: {avg_excess_power} W')

                else:
                    # home battery charge is not yet high enough OR battery force charge is necessary.
                    # Only use excess power (which would otherwise be exported to the grid) for appliance
                    # calc avg based on export power history according to specified window
                    avg_excess_power = int(sum(PvExcessControl.export_history[-max(1,inst.appliance_switch_interval):]) / max([1,inst.appliance_switch_interval]))
                    log.debug(f'{log_prefix} Home battery charge is not sufficient ({home_battery_level}/{PvExcessControl.min_home_battery_level} %), '
                              f'OR remaining solar forecast is lower than remaining capacity of home battery. '
                              f'Calculated average excess power based on >> export power <<: {avg_excess_power} W')

                # add instance including calculated excess power to inverted list (priority from low to high)
                instances.insert(0, {'instance': inst, 'avg_excess_power': avg_excess_power})


                # -------------------------------------------------------------------
                # Determine if appliance can be turned on or current can be increased
                if _get_state(inst.appliance_switch) == 'on':
                    # check if current of appliance can be increased
                    log.debug(f'{log_prefix} Appliance is already switched on.')
                    run_time = inst.daily_run_time + (datetime.datetime.now() - inst.switched_on_time).total_seconds()
                    log.info(f'{inst.log_prefix} Application has run for {(run_time / 60):.1f} minutes')
                    if avg_excess_power >= PvExcessControl.min_excess_power and inst.dynamic_current_appliance:
                        # try to increase dynamic current, because excess solar power is available
                        prev_amps = _get_num_state(inst.appliance_current_set_entity, return_on_error=inst.min_current)
                        excess_amps = round(avg_excess_power / (PvExcessControl.grid_voltage * inst.phases), 1) + prev_amps
                        amps = max(inst.min_current, min(excess_amps, inst.max_current))
                        if amps > (prev_amps+0.09):
                            _set_value(inst.appliance_current_set_entity, amps)
                            log.info(f'{log_prefix} Setting dynamic current appliance from {prev_amps} to {amps} A per phase.')
                            diff_power = (amps-prev_amps) * PvExcessControl.grid_voltage * inst.phases
                            # "restart" history by subtracting power difference from each history value within the specified time frame
                            self._adjust_pwr_history(inst, -diff_power)

                elif not (inst.appliance_once_only and inst.switched_on_today):
                    # check if appliance can be switched on
                    if _get_state(inst.appliance_switch) != 'off':
                        log.warning(f'{log_prefix} Appliance state (={_get_state(inst.appliance_switch)}) is neither ON nor OFF. '
                                    f'Assuming OFF state.')
                    defined_power = inst.defined_current * PvExcessControl.grid_voltage * inst.phases

                    if avg_excess_power >= defined_power or (inst.appliance_priority > 1000 and avg_excess_power > 0):
                        log.debug(f'{log_prefix} Average Excess power is high enough to switch on appliance.')
                        if inst.switch_interval_counter >= inst.appliance_switch_interval:
                            self.switch_on(inst)
                            inst.switch_interval_counter = 0
                            log.info(f'{log_prefix} Switched on appliance.')
                            # "restart" history by subtracting defined power from each history value within the specified time frame
                            self._adjust_pwr_history(inst, -defined_power)
                            task.sleep(1)
                            if inst.dynamic_current_appliance:
                                _set_value(inst.appliance_current_set_entity, inst.min_current)
                        else:
                            log.debug(f'{log_prefix} Cannot switch on appliance, because appliance switch interval is not reached '
                                      f'({inst.switch_interval_counter}/{inst.appliance_switch_interval}).')
                    elif (not switched_off_aplliance_to_switch_on_higher_prioritized_one) and (self.calculate_pwr_reducible(inst.appliance_priority) + avg_excess_power) >= (defined_power if inst.appliance_priority <= 500 else 0):
                        # excess power is sufficent by switching off lower prioritized appliance(s)
                        if inst.switch_interval_counter >= inst.appliance_switch_interval:
                            self.switch_on(inst)
                            inst.switch_interval_counter = 0
                            switched_off_aplliance_to_switch_on_higher_prioritized_one = True
                            log.info(f'{log_prefix} Average Excess power will be high enough by switching off lower prioritized appliance(s). Switched on appliance.')
                            # "restart" history by subtracting defined power from each history value within the specified time frame
                            self._adjust_pwr_history(inst, -defined_power)
                            task.sleep(1)
                            if inst.dynamic_current_appliance:
                                _set_value(inst.appliance_current_set_entity, inst.min_current)
                    else:
                        log.debug(f'{log_prefix} Average Excess power not high enough to switch on appliance.')
                # -------------------------------------------------------------------


            # ----------------------------------- go through each appliance (lowest prio to highest prio) ----------------------------------
            # this is for determining which devices need to be switched off or decreased in current
            prev_consumption_sum = 0
            for dic in instances:
                inst = dic['instance']
                avg_excess_power = dic['avg_excess_power'] + prev_consumption_sum
                log_prefix = f'[{inst.appliance_switch} (Prio {inst.appliance_priority})]'

                # -------------------------------------------------------------------
                if _get_state(inst.appliance_switch) == 'on':
                    # check if inst.appliance_priority > 1000 and switching of will cause excess. In that case keep it on
                    if inst.appliance_priority > 1000:
                        if inst.actual_power is None:
                            allowed_excess_power_consumption = inst.defined_current * PvExcessControl.grid_voltage * inst.phases
                        else:
                            allowed_excess_power_consumption = _get_num_state(inst.actual_power)
                    else:
                        allowed_excess_power_consumption = 0
                    if avg_excess_power < PvExcessControl.min_excess_power - allowed_excess_power_consumption:
                        log.debug(f'{log_prefix} Average Excess Power ({avg_excess_power} W) is less than minimum excess power '
                                  f'({PvExcessControl.min_excess_power} W).')

                        # check if current of dyn. curr. appliance can be reduced
                        if inst.dynamic_current_appliance:
                            if inst.actual_power is None:
                                actual_current = round((inst.defined_current * PvExcessControl.grid_voltage * inst.phases) / (
                                        PvExcessControl.grid_voltage * inst.phases), 1)
                            else:
                                actual_current = round(_get_num_state(inst.actual_power) / (PvExcessControl.grid_voltage * inst.phases), 1)
                            diff_current = round(avg_excess_power / (PvExcessControl.grid_voltage * inst.phases), 1)
                            target_current = max(inst.min_current, actual_current + diff_current)
                            log.debug(f'{log_prefix} {actual_current=}A | {diff_current=}A | {target_current=}A')
                            if inst.min_current < target_current < actual_current:
                                # current can be reduced
                                log.info(f'{log_prefix} Reducing dynamic current appliance from {actual_current} A to {target_current} A.')
                                _set_value(inst.appliance_current_set_entity, target_current)
                                # add released power consumption to next appliances in list
                                diff_power = (actual_current - target_current) * PvExcessControl.grid_voltage * inst.phases
                                prev_consumption_sum += diff_power
                                log.debug(f'{log_prefix} Added {diff_power=} W to prev_consumption_sum, '
                                          f'which is now {prev_consumption_sum} W.')
                                # "restart" history by adding defined power to each history value within the specified time frame
                                self._adjust_pwr_history(inst, diff_power)
                            else:
                                # current cannot be reduced
                                # turn off appliance
                                power_consumption = self.switch_off(inst)
                                if power_consumption != 0:
                                    prev_consumption_sum += power_consumption
                                    log.debug(f'{log_prefix} Added {power_consumption=} W to prev_consumption_sum, '
                                              f'which is now {prev_consumption_sum} W.')

                        else:
                            # Try to switch off appliance
                            power_consumption = self.switch_off(inst)
                            if power_consumption != 0:
                                prev_consumption_sum += power_consumption
                                log.debug(f'{log_prefix} Added {power_consumption=} W to prev_consumption_sum, '
                                          f'which is now {prev_consumption_sum} W.')
                    else:
                        log.debug(f'{log_prefix} Average Excess Power ({avg_excess_power} W) is still greater than minimum excess power '
                                  f'({PvExcessControl.min_excess_power} W) - Doing nothing.')


                else:
                    if _get_state(inst.appliance_switch) != 'off':
                        log.warning(f'{log_prefix} Appliance state (={_get_state(inst.appliance_switch)}) is neither ON nor OFF. '
                                    f'Assuming OFF state.')
                    # Note: This can misfire right after an appliance has been switched on. Generally no problem.
                    log.debug(f'{log_prefix} Appliance is already switched off.')
                # -------------------------------------------------------------------

        return on_time

    @staticmethod
    def _update_pv_history():
        """
        Update Export and PV history
        """
        try:
            if PvExcessControl.import_export_power:
                # Calc values based on combined import/export power sensor
                import_export_state = _get_num_state(PvExcessControl.import_export_power)
                if import_export_state is None:
                    raise Exception(f'Could not update Export/PV history: {PvExcessControl.import_export_power} is None.')
                import_export = int(import_export_state)
                # load_pwr = pv_pwr + import_export
                export_pwr = abs(min(0, import_export))
                excess_pwr = -import_export
            else:
                # Calc values based on separate sensors
                export_pwr_state = _get_num_state(PvExcessControl.export_power)
                pv_power_state = _get_num_state(PvExcessControl.pv_power)
                load_power_state = _get_num_state(PvExcessControl.load_power)
                if export_pwr_state is None or pv_power_state is None or load_power_state is None:
                    raise Exception(f'Could not update Export/PV history {PvExcessControl.export_power=} | {PvExcessControl.pv_power=} | '
                                    f'{PvExcessControl.load_power=} = {export_pwr_state=} | {pv_power_state=} | {load_power_state=}')
                export_pwr = int(export_pwr_state)
                excess_pwr = int(pv_power_state - load_power_state)
        except Exception as e:
            log.error(f'Could not update Export/PV history!: {e}')
            return
        else:
            PvExcessControl.export_history_buffer.append(export_pwr)
            PvExcessControl.pv_history_buffer.append(excess_pwr)

        # log.debug(f'Export History Buffer: {PvExcessControl.export_history_buffer}')
        # log.debug(f'PV Excess (PV Power - Load Power) History Buffer: {PvExcessControl.pv_history_buffer}')

        if PvExcessControl.on_time_counter % 6 == 0:
            # enforce max. 60 minute length of history
            if len(PvExcessControl.export_history) >= 60:
                PvExcessControl.export_history.pop(0)
            if len(PvExcessControl.pv_history) >= 60:
                PvExcessControl.pv_history.pop(0)
            # calc avg of buffer
            export_avg = round(sum(PvExcessControl.export_history_buffer) / len(PvExcessControl.export_history_buffer))
            excess_avg = round(sum(PvExcessControl.pv_history_buffer) / len(PvExcessControl.pv_history_buffer))
            # add avg to history
            PvExcessControl.export_history.append(export_avg)
            PvExcessControl.pv_history.append(excess_avg)
            log.debug(f'Export History: {PvExcessControl.export_history}')
            log.debug(f'PV Excess (PV Power - Load Power) History: {PvExcessControl.pv_history}')
            # clear buffer
            PvExcessControl.export_history_buffer = []
            PvExcessControl.pv_history_buffer = []


    def sanity_check(self) -> bool:
        if PvExcessControl.import_export_power is not None and PvExcessControl.home_battery_level is not None:
            log.warning('"Import/Export power" has been defined together with "Home Battery". This is not intended and will lead to always '
                        'giving the home battery priority over appliances, regardless of the specified min. battery level.')
            return True
        if PvExcessControl.import_export_power is not None and (PvExcessControl.export_power is not None or
                                                                PvExcessControl.load_power is not None):
            log.error('"Import/Export power" has been defined together with either "Export power" or "Load power". This is not '
                      'allowed. Please specify either "Import/Export power" or both "Load power" & "Export Power".')
            return False
        if not (PvExcessControl.import_export_power is not None or (PvExcessControl.export_power is not None and
                                                                    PvExcessControl.load_power is not None)):
            log.error('Either "Export power" or "Load power" have not been defined. This is not '
                      'allowed. Please specify either "Import/Export power" or both "Load power" & "Export Power".')
            return False
        return True

    def switch_on(self, inst):
        """
        Switches an appliance on, if possible.
        :param inst:        PVExcesscontrol Class instance
        """
        if inst.appliance_once_only and inst.switched_on_today:
            log.debug(f'{inst.log_prefix} "Only-Run-Once-Appliance" detected - Appliance was already switched on today - '
                      f'Not switching on again.')
        elif _turn_on(inst.appliance_switch):
            inst.switched_on_today = True
            inst.switched_on_time = datetime.datetime.now()

    def switch_off(self, inst) -> float:
        """
        Switches an appliance off, if possible.
        :param inst:        PVExcesscontrol Class instance
        :return:            Power consumption relief achieved through switching the appliance off (will be 0 if appliance could
                             not be switched off)
        """
        # Check if automation is activated for specific instance
        if not self.automation_activated(inst.automation_id):
            return 0
        # Do not turn off only-on-appliances
        if inst.appliance_on_only:
            log.debug(f'{inst.log_prefix} "Only-On-Appliance" detected - Not switching off.')
            return 0
        # Do not turn off if switch interval not reached
        elif inst.switch_interval_counter < inst.appliance_switch_interval:
            log.debug(f'{inst.log_prefix} Cannot switch off appliance, because appliance switch interval is not reached '
                      f'({inst.switch_interval_counter}/{inst.appliance_switch_interval}).')
            return 0
        else:
            # switch off
            # get last power consumption
            if inst.actual_power is None:
                power_consumption = inst.defined_current * PvExcessControl.grid_voltage * inst.phases
            else:
                power_consumption = _get_num_state(inst.actual_power)
            log.debug(f'{inst.log_prefix} Current power consumption: {power_consumption} W')
            # switch off appliance
            _turn_off(inst.appliance_switch)
            inst.daily_run_time += (datetime.datetime.now() - inst.switched_on_time).total_seconds()
            log.info(f'{inst.log_prefix} Switched off appliance.')
            log.info(f'{inst.log_prefix} Application has run for {(inst.daily_run_time / 60):.1f} minutes')
            task.sleep(1)
            inst.switch_interval_counter = 0
            # "restart" history by adding defined power to each history value within the specified time frame
            self._adjust_pwr_history(inst, power_consumption)
            return power_consumption


    def automation_activated(self, a_id):
        """
        Checks if the automation for a specific appliance is activated or not.
        :param a_id:    Automation ID in Home Assistant
        :return:        True if automation is activated, False otherwise
        """
        automation_state = _get_state(a_id)
        if automation_state == 'off':
            log.debug(f'Doing nothing, because automation is not activated: State is {automation_state}.')
            return False
        elif automation_state is None:
            log.info(f'Automation "{a_id}" was deleted. Removing related class instance.')
            del PvExcessControl.instances[a_id]
            return False
        return True


    def _adjust_pwr_history(self, inst, value):
        log.debug(f'Adjusting power history by {value}.')
        log.debug(f'Export history: {PvExcessControl.export_history}')
        PvExcessControl.export_history[-inst.appliance_switch_interval:] = [max(0, x + value) for x in
                                                                            PvExcessControl.export_history[-inst.appliance_switch_interval:]]
        log.debug(f'Adjusted export history: {PvExcessControl.export_history}')
        log.debug(f'PV Excess (solar power - load power) history: {PvExcessControl.pv_history}')
        PvExcessControl.pv_history[-inst.appliance_switch_interval:] = [x + value for x in
                                                                        PvExcessControl.pv_history[-inst.appliance_switch_interval:]]
        log.debug(f'Adjusted PV Excess (solar power - load power) history: {PvExcessControl.pv_history}')


    def _force_charge_battery(self, kwh_offset: float = 1):
        """
        Calculates if the remaining solar power forecast is enough to ensure the specified min. home battery level is reached at the end
        of the day.
        :param kwh_offset:  Offset in kWh, which will be added to the calculated remaining battery capacity to ensure an earlier
                             triggering of a force charge
        :return:            True if force charge is necessary, False otherwise
        """
        if PvExcessControl.home_battery_level is None:
            return False

        capacity = PvExcessControl.home_battery_capacity
        remaining_capacity = capacity - (0.01 * capacity * _get_num_state(PvExcessControl.home_battery_level, return_on_error=0))
        remaining_forecast = _get_num_state(PvExcessControl.solar_production_forecast, return_on_error=0)
        if remaining_forecast <= remaining_capacity + kwh_offset:
            log.debug(f'Force battery charge necessary: {capacity=} kWh|{remaining_capacity=} kWh|{remaining_forecast=} kWh| '
                      f'{kwh_offset=} kWh')
            # go through appliances lowest to highest priority, and try switching them off individually
            for a_id, e in dict(sorted(PvExcessControl.instances.items(), key=lambda item: item[1]['priority'])).items():
                inst = e['instance']
                self.switch_off(inst)
            return True
        return False


    def calculate_pwr_reducible(self, max_priority):
        """
        Calculates the reduicible power by switching off all aplicances, which van be switched off and have a priority below max_priority
        :param  max_priority: see description
        :return:              reducible power
        """
        pwr_reducible = 0
        for a_id, e in PvExcessControl.instances.copy().items():
            inst = e['instance']
            if not self.automation_activated(inst.automation_id):
                continue
            # Do not turn off only-on-appliances
            if inst.appliance_on_only:
                continue
            # Do not turn off if switch interval not reached
            if inst.switch_interval_counter < inst.appliance_switch_interval:
                continue
            if inst.appliance_priority >= max_priority:
                continue
            if _get_state(inst.appliance_switch) != 'on':
                continue
            if inst.actual_power is None:
                pwr_reducible += inst.defined_current * PvExcessControl.grid_voltage * inst.phases
            else:
                pwr_reducible += _get_num_state(inst.actual_power)
        
        return pwr_reducible
