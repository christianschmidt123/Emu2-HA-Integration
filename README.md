# Emu2-HA-Integration

Home Assistant HACS-Integration für den EMU Professional II (Modbus TCP).

## Installation (HACS)

1. Dieses Repository in HACS als benutzerdefiniertes Repository hinzufügen.
2. Integration **EMU2 Modbus** installieren.
3. Home Assistant neu starten.

## Konfiguration (`configuration.yaml`)

```yaml
sensor:
  - platform: emu2_modbus
    name: emu_professional_ii
    host: 192.168.0.76
    port: 502
    timeout: 5
    slave: 1

    sensors:
      - name: "EMU Wirkenergie Import"
        unique_id: emu_energy_import
        address: 5999
        input_type: holding
        data_type: uint64
        scan_interval: 30
        unit_of_measurement: kWh
        device_class: energy
        state_class: total_increasing
        scale: 0.001
        precision: 3

      - name: "EMU Wirkenergie Export"
        unique_id: emu_energy_export
        address: 6019
        input_type: holding
        data_type: uint64
        scan_interval: 30
        unit_of_measurement: kWh
        device_class: energy
        state_class: total_increasing
        scale: 0.001
        precision: 3

      - name: "EMU Wirkleistung Gesamt"
        unique_id: emu_power_total
        address: 8999
        input_type: holding
        data_type: float32
        scan_interval: 5
        unit_of_measurement: kW
        device_class: power
        state_class: measurement
        scale: 0.001
        precision: 3

      - name: "EMU Wirkleistung L1"
        unique_id: emu_power_l1
        address: 9001
        input_type: holding
        data_type: float32
        scan_interval: 5
        unit_of_measurement: kW
        device_class: power
        state_class: measurement
        scale: 0.001
        precision: 3

      - name: "EMU Wirkleistung L2"
        unique_id: emu_power_l2
        address: 9003
        input_type: holding
        data_type: float32
        scan_interval: 5
        unit_of_measurement: kW
        device_class: power
        state_class: measurement
        scale: 0.001
        precision: 3

      - name: "EMU Wirkleistung L3"
        unique_id: emu_power_l3
        address: 9005
        input_type: holding
        data_type: float32
        scan_interval: 5
        unit_of_measurement: kW
        device_class: power
        state_class: measurement
        scale: 0.001
        precision: 3

      - name: "EMU Blindleistung Gesamt"
        unique_id: emu_reactive_power_total
        address: 9009
        input_type: holding
        data_type: float32
        scan_interval: 10
        unit_of_measurement: kvar
        state_class: measurement
        scale: 0.001
        precision: 3

      - name: "EMU Strom L1"
        unique_id: emu_current_l1
        address: 9100
        input_type: holding
        data_type: float32
        swap: word
        scan_interval: 5
        unit_of_measurement: A
        device_class: current
        state_class: measurement
        precision: 3

      - name: "EMU Strom L2"
        unique_id: emu_current_l2
        address: 9102
        input_type: holding
        data_type: float32
        swap: word
        scan_interval: 5
        unit_of_measurement: A
        device_class: current
        state_class: measurement
        precision: 3

      - name: "EMU Strom L3"
        unique_id: emu_current_l3
        address: 9104
        input_type: holding
        data_type: float32
        swap: word
        scan_interval: 5
        unit_of_measurement: A
        device_class: current
        state_class: measurement
        precision: 3

      - name: "EMU Spannung L1-N"
        unique_id: emu_voltage_l1
        address: 9198
        input_type: holding
        data_type: float32
        swap: word
        scan_interval: 10
        unit_of_measurement: V
        device_class: voltage
        state_class: measurement
        precision: 1

      - name: "EMU Spannung L2-N"
        unique_id: emu_voltage_l2
        address: 9200
        input_type: holding
        data_type: float32
        swap: word
        scan_interval: 10
        unit_of_measurement: V
        device_class: voltage
        state_class: measurement
        precision: 1

      - name: "EMU Spannung L3-N"
        unique_id: emu_voltage_l3
        address: 9202
        input_type: holding
        data_type: float32
        swap: word
        scan_interval: 10
        unit_of_measurement: V
        device_class: voltage
        state_class: measurement
        precision: 1

      - name: "EMU Leistungsfaktor L1"
        unique_id: emu_pf_l1
        address: 9298
        input_type: holding
        data_type: float32
        swap: word
        scan_interval: 10
        unit_of_measurement: ""
        state_class: measurement
        precision: 3

      - name: "EMU Leistungsfaktor L2"
        unique_id: emu_pf_l2
        address: 9300
        input_type: holding
        data_type: float32
        swap: word
        scan_interval: 10
        unit_of_measurement: ""
        state_class: measurement
        precision: 3

      - name: "EMU Leistungsfaktor L3"
        unique_id: emu_pf_l3
        address: 9302
        input_type: holding
        data_type: float32
        swap: word
        scan_interval: 10
        unit_of_measurement: ""
        state_class: measurement
        precision: 3

      - name: "EMU Netzfrequenz"
        unique_id: emu_frequency
        address: 9308
        input_type: holding
        data_type: float32
        swap: word
        scan_interval: 30
        unit_of_measurement: Hz
        device_class: frequency
        state_class: measurement
        precision: 3
```

## Unterstützte Sensor-Optionen

- `name` (Pflicht)
- `address` (Pflicht, protokollnahe Register-Adresse 0-basiert; kein automatischer Offset)
- `input_type`: `holding` oder `input` (Standard: `holding`)
- `data_type`: `float32` oder `uint64` (Standard: `float32`)
- `swap`: `none` oder `word` (Standard: `none`)
- `slave` (Standard vom Plattformwert `slave`)
- `scan_interval` in Sekunden
- `unit_of_measurement`, `device_class`, `state_class`
- `scale` (Standard: `1.0`)
- `precision`
