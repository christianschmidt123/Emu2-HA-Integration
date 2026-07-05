# Emu2-HA-Integration

Home Assistant HACS-Integration für den EMU Professional II (Modbus TCP) mit UI-Setup.

## Installation (HACS)

1. Dieses Repository in HACS als benutzerdefiniertes Repository hinzufügen.
2. Integration **EMU2 Modbus** installieren.
3. Home Assistant neu starten.
4. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** nach **EMU2 Modbus** suchen.
5. Host, Port, Timeout und Slave-ID eintragen.

## UI-Konfiguration

Beim UI-Setup werden folgende Verbindungsdaten abgefragt:

- `name`
- `host`
- `port` (Standard: `502`)
- `timeout` (Standard: `5`)
- `slave` (Standard: `1`)

Die Sensoren aus deiner ursprünglichen YAML sind fest in der Integration hinterlegt und werden nach erfolgreicher Einrichtung automatisch angelegt.

## Enthaltene Sensoren

- EMU Wirkenergie Import
- EMU Wirkenergie Export
- EMU Wirkleistung Gesamt
- EMU Wirkleistung L1
- EMU Wirkleistung L2
- EMU Wirkleistung L3
- EMU Blindleistung Gesamt
- EMU Strom L1
- EMU Strom L2
- EMU Strom L3
- EMU Spannung L1-N
- EMU Spannung L2-N
- EMU Spannung L3-N
- EMU Leistungsfaktor L1
- EMU Leistungsfaktor L2
- EMU Leistungsfaktor L3
- EMU Netzfrequenz

## Verwendete Registerdefinitionen

Die Integration nutzt intern diese aus deiner YAML abgeleiteten Werte:

- Adressen sind protokollnahe Register-Adressen, 0-basiert, ohne automatischen Offset.
- Unterstützte Registerarten: `holding`
- Unterstützte Datentypen: `float32`, `uint64`
- Unterstütztes Byte-/Word-Swapping: `swap: word`
- Skalierung und Präzision entsprechen der gelieferten YAML-Konfiguration.
