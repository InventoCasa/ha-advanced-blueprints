# INFO --------------------------------------------
# This is intended to be called once manually or on startup. See blueprint.
# Automations can be deactivated correctly from the UI!
# -------------------------------------------------
from typing import Union

class_instances = {}



def _get_state(entity_str: str) -> Union[str, None]:
    """
    Get the state of an entity in Home Assistant
    :param entity_str:  Name of the entity
    :return:            State if entity name is valid, else None
    """
    try:
        return state.get(entity_str)
    except Exception as e:
        log.error(f'Could not get state from entity {entity_str}: {e}')
        return None


def _get_num_state(entity_str: str) -> Union[float, None]:
    return _validate_number(_get_state(entity_str))


def _validate_number(num: Union[float, str]) -> Union[float, None]:
    """
    Validate, if the passed variable is a number between 0 and 1000000.
    :param num:     Number
    :return:        Number if valid, else None
    """
    try:
        if 0 <= float(num) <= 1000000:
            return float(num)
    except Exception as e:
        log.error(f'{num=} is not a valid number between 0 and 1000000: {e}')
        return None


@service
def pv_excess_control(automation_id, appliance_priority, export_power, pv_power, load_power, home_battery_level,
                      min_home_battery_level, dynamic_current_appliance, three_phase_appliance, min_current,
                      max_current, appliance_switch, appliance_switch_interval, appliance_current_set_entity,
                      actual_power, defined_current, appliance_on_only):

    automation_id = f"automation.{automation_id.strip().replace(' ', '_').lower()}"

    class_instances[automation_id] = PvExcessControl(automation_id, appliance_priority, export_power, pv_power,
                                                     load_power, home_battery_level, min_home_battery_level,
                                                     dynamic_current_appliance, three_phase_appliance, min_current,
                                                     max_current, appliance_switch, appliance_switch_interval,
                                                     appliance_current_set_entity, actual_power, defined_current, appliance_on_only)



class PvExcessControl:
    # TODO:
    #  - What about other domains than switches? Enable use of other domains (e.g. light, ...)
    #  - Format blueprint config entry description
    instances = {}
    trigger = None
    export_power = None
    pv_power = None
    load_power = None
    home_battery_level = None
    # Exported Power history
    export_history = [0]*60
    # PV Excess history (PV power minus load power)
    pv_history = [0]*60
    # Minimum excess power in watts. If the average min_excess_power at the specified appliance switch interval is greater than the actual
    # excess power, the appliance with the lowest priority will be shut off. WARNING: Setting this too low (e.g. to zero) could have the
    # consequence that your last running appliance will not be switched off.
    # TODO: Make this configurable via blueprint.
    min_excess_power = 10


    def __init__(self, automation_id, appliance_priority, export_power, pv_power, load_power, home_battery_level,
                 min_home_battery_level, dynamic_current_appliance, three_phase_appliance, min_current,
                 max_current, appliance_switch, appliance_switch_interval, appliance_current_set_entity,
                 actual_power, defined_current, appliance_on_only):
        self.automation_id = automation_id
        self.appliance_priority = int(appliance_priority)
        PvExcessControl.export_power = export_power
        PvExcessControl.pv_power = pv_power
        PvExcessControl.load_power = load_power
        PvExcessControl.home_battery_level = home_battery_level
        self.min_home_battery_level = float(min_home_battery_level)
        self.dynamic_current_appliance = bool(dynamic_current_appliance)
        self.min_current = float(min_current)
        self.max_current = float(max_current)
        self.appliance_switch = appliance_switch
        self.appliance_switch_interval = int(appliance_switch_interval)
        self.appliance_current_set_entity = appliance_current_set_entity
        self.actual_power = actual_power
        self.defined_current = float(defined_current)
        self.appliance_on_only = bool(appliance_on_only)

        if bool(three_phase_appliance):
            self.phases = 3
        else:
            self.phases = 1

        self.switch_interval_counter = 0

        # Make sure trigger method is only registered once
        if PvExcessControl.trigger is None:
            PvExcessControl.trigger = self.trigger_factory()
        # Add self to class dict and sort by priority (highest to lowest)
        PvExcessControl.instances[self.automation_id] = {'instance': self, 'priority': self.appliance_priority}
        PvExcessControl.instances = dict(sorted(PvExcessControl.instances.items(), key=lambda item: item[1]['priority'], reverse=True))
        log.debug(f'[{self.appliance_switch} (Prio {self.appliance_priority})] Registered appliance.')


    def trigger_factory(self):
        # trigger every minute between 06:00 and 23:00
        @time_trigger('cron(* 6-23 * * *)')
        def on_time():
            log.debug('Trigger method triggered')
            # ----------------------------------- get the current export / pv excess -----------------------------------
            if len(PvExcessControl.export_history) >= 60:
                PvExcessControl.export_history.pop(0)
            if len(PvExcessControl.pv_history) >= 60:
                PvExcessControl.pv_history.pop(0)
            try:
                PvExcessControl.export_history.append(_get_num_state(PvExcessControl.export_power))
                PvExcessControl.pv_history.append(_get_num_state(PvExcessControl.pv_power) - _get_num_state(PvExcessControl.load_power))
            except Exception as e:
                log.error(f'Could not update Export/PV history!: {e}')
            log.debug(f'PV Excess (PV Power - Load Power) History: {PvExcessControl.pv_history}')
            log.debug(f'Export History: {PvExcessControl.export_history}')

            # ----------------------------------- go through each appliance (highest prio to lowest) ---------------------------------------
            # this is for determining which devices can be switched on
            instances = []
            for e in PvExcessControl.instances.values():
                inst = e['instance']
                inst.switch_interval_counter += 1
                log_prefix = f'[{inst.appliance_switch} (Prio {inst.appliance_priority})]'
                # Check if automation is activated
                if not _get_state(inst.automation_id) == 'on':
                    log.debug(f'{log_prefix} Doing nothing, because automation is not activated.')
                    continue

                # check min bat lvl and decide whether to regard export power or solar power minus load power
                if _get_num_state(inst.home_battery_level) >= inst.min_home_battery_level:
                    # home battery charge is high enough to direct solar power to appliances, if solar power is higher than load power
                    # calc avg based on pv excess (solar power - load power) according to specified window
                    avg_excess_power = int(sum(PvExcessControl.pv_history[-inst.appliance_switch_interval:]) / inst.appliance_switch_interval)
                    log.debug(f'{log_prefix} Home battery charge is sufficient ({_get_num_state(inst.home_battery_level)}/{inst.min_home_battery_level} %). '
                              f'Calculated average excess power based on >> solar power - load power <<: {avg_excess_power} W')

                else:
                    # home battery charge is not yet high enough. Only use excess power (which would otherwise be
                    # exported to the grid) for appliance
                    # calc avg based on export power history according to specified window
                    avg_excess_power = int(sum(PvExcessControl.export_history[-inst.appliance_switch_interval:]) / inst.appliance_switch_interval)
                    log.debug(f'{log_prefix} Home battery charge is not sufficient ({_get_num_state(inst.home_battery_level)}/{inst.min_home_battery_level} %). '
                              f'Calculated average excess power based on >> export power <<: {avg_excess_power} W')

                # add instance including calculated excess power to inverted list (priority from low to high)
                instances.insert(0, {'instance': inst, 'avg_excess_power': avg_excess_power})

                # check if appliance can be switched on
                defined_power = inst.defined_current*230*inst.phases
                if _get_state(inst.appliance_switch) == 'on':
                    log.debug(f'{log_prefix} Appliance is already switched on.')
                elif avg_excess_power < defined_power:
                    log.debug(f'{log_prefix} Average Excess power not high enough to switch on appliance.')
                else:
                    log.debug(f'{log_prefix} Average Excess power is high enough to switch on appliance.')
                    # turn on appliance
                    if _get_state(inst.appliance_switch) == 'off':
                        if inst.switch_interval_counter >= inst.appliance_switch_interval:
                            switch.turn_on(entity_id=inst.appliance_switch)
                            inst.switch_interval_counter = 0
                            log.debug(f'{log_prefix} Switched on appliance.')
                            # "restart" history by subtracting defined power from each history value within the specified time frame
                            self._adjust_pwr_history(inst, -defined_power)
                            task.sleep(1)
                        else:
                            log.debug(f'{log_prefix} Cannot switch on appliance, because appliance switch interval is not reached '
                                      f'({inst.switch_interval_counter}/{inst.appliance_switch_interval}).')

                    # Dynamic current appliances
                    if inst.dynamic_current_appliance:
                        excess_amps = round(avg_excess_power / (230*inst.phases), 1)
                        amps = max(inst.min_current, min(excess_amps, inst.max_current))
                        number.set_value(entity_id=inst.appliance_current_set_entity, value=amps)
                        log.debug(f'{log_prefix} Setting dynamic current appliance to {amps} A per phase.')
                        defined_power = amps*230*inst.phases
                        # "restart" history by subtracting defined power from each history value within the specified time frame
                        self._adjust_pwr_history(inst, -defined_power)


            # ----------------------------------- go through each appliance (lowest prio to highest prio) ----------------------------------
            # this is for determining which devices need to be switched off again
            prev_consumption_sum = 0
            for dic in instances:
                inst = dic['instance']
                avg_excess_power = dic['avg_excess_power'] + prev_consumption_sum
                log_prefix = f'[{inst.appliance_switch} (Prio {inst.appliance_priority})]'

                if _get_state(inst.appliance_switch) == 'off':
                    log.debug(f'{log_prefix} Appliance is already switched off.')
                elif avg_excess_power > PvExcessControl.min_excess_power:
                    log.debug(f'{log_prefix} Average Excess Power ({avg_excess_power} W) is still greater than minimum excess power '
                              f'({PvExcessControl.min_excess_power} W) - Doing nothing.')
                else:
                    log.debug(f'{log_prefix} Average Excess Power ({avg_excess_power} W) is less than minimum excess power '
                              f'({PvExcessControl.min_excess_power} W).')

                    # if switch-on-only appliance, continue
                    if inst.appliance_on_only:
                        log.debug(f'{log_prefix} "Only-On-Appliance" detected - Not switching off.')
                        continue

                    elif inst.dynamic_current_appliance:
                        # check if current of appliance can be reduced
                        if inst.actual_power is None:
                            actual_current = round((inst.defined_current*230*inst.phases) / (230 * inst.phases), 1)
                        else:
                            actual_current = round(_get_num_state(inst.actual_power) / (230*inst.phases), 1)
                        diff_current = round(avg_excess_power / (230*inst.phases), 1)
                        target_current = max(inst.min_current, actual_current+diff_current)
                        log.debug(f'{log_prefix} {actual_current=}A | {diff_current=}A | {target_current=}A')
                        if inst.min_current <= target_current < actual_current:
                            log.debug(f'{log_prefix} Reducing dynamic current appliance from {actual_current} A to {target_current} A.')
                            number.set_value(entity_id=inst.appliance_current_set_entity, value=target_current)
                            # add released power consumption to next appliances in list
                            diff_power = (actual_current - target_current)*230*inst.phases
                            prev_consumption_sum += diff_power
                            log.debug(f'{log_prefix} Added {diff_power=} W to prev_consumption_sum, '
                                      f'which is now {prev_consumption_sum} W.')
                            # "restart" history by adding defined power to each history value within the specified time frame
                            self._adjust_pwr_history(inst, diff_power)
                            continue

                        else:
                            log.debug(f'{log_prefix} Current of appliance could not be reduced.')

                    # if switch interval not reached, continue
                    if inst.switch_interval_counter < inst.appliance_switch_interval:
                        log.debug(f'{log_prefix} Cannot switch off appliance, because appliance switch interval is not reached '
                                  f'({inst.switch_interval_counter}/{inst.appliance_switch_interval}).')
                        continue

                    else:
                        # get last power consumption
                        if inst.actual_power is None:
                            power_consumption = inst.defined_current*230*inst.phases
                        else:
                            power_consumption = _get_num_state(inst.actual_power)
                        log.debug(f'{log_prefix} Current power consumption: {power_consumption} W')
                        # switch off appliance
                        switch.turn_off(entity_id=inst.appliance_switch)
                        log.debug(f'{log_prefix} Switched off appliance.')
                        task.sleep(1)
                        inst.switch_interval_counter = 0
                        # add released power consumption to next appliances in list
                        prev_consumption_sum += power_consumption
                        log.debug(f'{log_prefix} Added {power_consumption=} W to prev_consumption_sum, '
                                  f'which is now {prev_consumption_sum} W.')
                        # "restart" history by adding defined power to each history value within the specified time frame
                        self._adjust_pwr_history(inst, power_consumption)

        return on_time


    def _adjust_pwr_history(self, inst, value):
        log.debug(f'Export history: {PvExcessControl.export_history}')
        PvExcessControl.export_history[-inst.appliance_switch_interval:] = [max(0, x + value) for x in
                                                                            PvExcessControl.export_history[
                                                                            -inst.appliance_switch_interval:]]
        log.debug(f'Adjusted export history: {PvExcessControl.export_history}')
        log.debug(f'PV Excess (solar power - load power) history: {PvExcessControl.pv_history}')
        PvExcessControl.pv_history[-inst.appliance_switch_interval:] = [max(0, x + value) for x in
                                                                        PvExcessControl.pv_history[
                                                                        -inst.appliance_switch_interval:]]
        log.debug(f'Adjusted PV Excess (solar power - load power) history: {PvExcessControl.pv_history}')
