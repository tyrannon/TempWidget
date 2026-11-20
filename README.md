# TempWidget

A tiny, always-on-top Windows widget that shows your **CPU and GPU temperature** in big, readable text — because the 16×16 tray icons are useless.

```
CPU 172°F   GPU 136°F
```

- Green = fine, orange = getting warm, **red + dark-red background = too hot**
- Drag it anywhere (position is remembered)
- Mouse wheel over it = bigger / smaller text
- Right-click = menu (resize, close)
- Fahrenheit or Celsius
- Pure Python + tkinter, no dependencies, near-zero CPU

## How it reads temperatures

| Sensor | Source |
|---|---|
| CPU | [HWiNFO](https://www.hwinfo.com/) "Report value in Gadget" (registry `HKCU\Software\HWiNFO64\VSB`) |
| GPU | HWiNFO if reported, otherwise `nvidia-smi` |

Reading CPU temperature on Windows needs a kernel driver. Rather than shipping one, TempWidget lets HWiNFO (which has a signed driver) do the sensor work and just displays the numbers.

## Setup

1. Install Python 3 (with tkinter — the default python.org installer includes it).
2. Run HWiNFO in *Sensors-only* mode. In its settings → **HWiNFO Gadget** tab, tick **Enable reporting to Gadget**, then tick **Report value in Gadget** on **CPU Package** and **Core Max** (and optionally GPU Hot Spot). The widget shows the **hottest** reported CPU and GPU value, and ignores non-temperature values. HWiNFO set to °F is handled automatically.
3. Run the widget without a console window:
   ```powershell
   pythonw temp_widget.pyw
   ```
4. Optional — start with Windows: put a shortcut to `pythonw.exe "path\to\temp_widget.pyw"` in `shell:startup`.

## Configuration

`config.json` is created next to the script the first time you move or resize the widget:

| Key | Default | Meaning |
|---|---|---|
| `units` | `"F"` | `"F"` or `"C"` |
| `cpu_hot` | `95` | CPU red threshold, °C |
| `gpu_hot` | `85` | GPU red threshold, °C |
| `warn_margin` | `10` | Orange when within this many °C of hot |
| `font_size` | `22` | Text size |
| `interval_ms` | `1500` | Refresh rate |
| `opacity` | `0.88` | Window transparency |

Thresholds are always in °C (that's what the sensors report); only the display changes with `units`.

## License

MIT
