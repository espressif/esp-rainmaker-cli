# ESP RainMaker Schedule Management Guide

This guide explains how to use the ESP RainMaker CLI to manage schedules for your devices.

## Command Overview

### Get Schedules
To retrieve all schedules for a node:
```
esp-rainmaker-cli getschedules <nodeid>
```

### Manage Schedules
The `setschedule` command is used to add, edit, remove, enable, or disable schedules:
```
esp-rainmaker-cli setschedule <nodeid> --operation <operation> [options]
```

## Schedule Operations

### Add a Schedule

To add a new schedule, you need to provide:
- Node ID
- Schedule name
- Trigger configuration (in JSON format)
- Action configuration (in JSON format)

```
esp-rainmaker-cli setschedule <nodeid> --operation add --name "Evening Light" --trigger '{"m": 1110, "d": 31}' --action '{"Light": {"Power": true}}'
```

This example creates a schedule named "Evening Light" that turns on the light at 6:30 PM (1110 minutes since midnight) on all weekdays (d=31, which is the bitmap for Monday through Friday).

### Edit a Schedule

To edit an existing schedule, you must provide:
- Node ID
- Schedule ID
- Any fields you want to change

```
esp-rainmaker-cli setschedule <nodeid> --operation edit --id "8D36" --name "Updated Evening Light" --trigger '{"m": 1140, "d": 31}'
```

This example updates the schedule with ID "8D36" to have a new name and to trigger at 7:00 PM (1140 minutes since midnight).

### Remove a Schedule

To remove a schedule:
```
esp-rainmaker-cli setschedule <nodeid> --operation remove --id "8D36"
```

### Enable/Disable a Schedule

To enable a schedule:
```
esp-rainmaker-cli setschedule <nodeid> --operation enable --id "8D36"
```

To disable a schedule:
```
esp-rainmaker-cli setschedule <nodeid> --operation disable --id "8D36"
```

## Trigger Configuration Examples

### Daily Schedule at a Specific Time
```json
{"m": 480, "d": 127}
```
This triggers at 8:00 AM (480 minutes since midnight) every day of the week (d=127, which is the bitmap for all days).

### Weekday Schedule
```json
{"m": 1020, "d": 31}
```
This triggers at 5:00 PM (1020 minutes since midnight) on weekdays (Monday through Friday).

### Weekend Schedule
```json
{"m": 600, "d": 96}
```
This triggers at 10:00 AM (600 minutes since midnight) on weekends (Saturday and Sunday).

### One-time Schedule
```json
{"m": 1140, "d": 0}
```
This triggers at 7:00 PM (1140 minutes since midnight) just once.

### Monthly Schedule on a Specific Date
```json
{"m": 720, "dd": 15, "mm": 4095}
```
This triggers at 12:00 PM (720 minutes since midnight) on the 15th day of every month (mm=4095, which is the bitmap for all months).

### Relative Time Schedule (Trigger After X Seconds)
```json
{"rsec": 3600}
```
This triggers 1 hour (3600 seconds) from the time the schedule is created. When you use the CLI, the current timestamp will be automatically added to the trigger.

### Using Timestamp for Exact Trigger Time
```json
{"ts": 1748866626}
```
This schedule will trigger exactly at the specified timestamp (1748866626), which converts to a specific date and time in your local timezone. The timestamp is in Unix time (seconds since January 1, 1970).

When both `ts` and other trigger fields like `rsec`, `m`, or `d` are present, the `ts` field takes precedence and indicates the exact time when the schedule will be triggered.

## Action Configuration Examples

### Turn on a Light
```json
{"Light": {"Power": true}}
```

### Set Light Brightness
```json
{"Light": {"Power": true, "Brightness": 80}}
```

### Control Multiple Parameters
```json
{"Thermostat": {"Power": true, "Temperature": 22}}
```

## Advanced Usage

### Schedule with Additional Information
```
esp-rainmaker-cli setschedule <nodeid> --operation add --name "Morning Routine" --trigger '{"m": 420, "d": 31}' --action '{"Light": {"Power": true, "Brightness": 70}}' --info "Weekday morning schedule"
```

### Schedule with Flags
```
esp-rainmaker-cli setschedule <nodeid> --operation add --name "Special Schedule" --trigger '{"m": 1080, "d": 127}' --action '{"Light": {"Power": true}}' --flags "1"