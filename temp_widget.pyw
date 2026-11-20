"""Tiny always-on-top temperature widget.

Reads values HWiNFO publishes to HKCU\\Software\\HWiNFO64\\VSB
(enable "Report value in Gadget" on the sensors you want).
Falls back to nvidia-smi for GPU temp if HWiNFO isn't reporting it.

Drag with left mouse. Right-click for menu. Mouse wheel = resize text.
"""
import json
import os
import subprocess
import tkinter as tk
import winreg

HERE = os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.path.join(HERE, "config.json")

DEFAULT_CFG = {
    "x": 40, "y": 40,
    "font_size": 22,
    "cpu_hot": 95, "gpu_hot": 85,   # red at or above
    "warn_margin": 10,              # orange within this many degrees of hot
    "interval_ms": 1500,
    "opacity": 0.88,
    "units": "F",                   # "F" or "C" (thresholds above stay in °C)
}

COLORS = {"ok": "#7CFC8A", "warn": "#FFB020", "hot": "#FF3B30", "dim": "#9AA0A6"}
BG = "#111111"
NO_WINDOW = 0x08000000


def load_cfg():
    cfg = dict(DEFAULT_CFG)
    try:
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def save_cfg(cfg):
    try:
        with open(CFG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


def read_hwinfo():
    """Return list of (label, value_float) from HWiNFO's gadget registry key."""
    out = []
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\HWiNFO64\VSB")
    except OSError:
        return out
    with key:
        i = 0
        while True:
            try:
                label = winreg.QueryValueEx(key, f"Label{i}")[0]
                raw = winreg.QueryValueEx(key, f"ValueRaw{i}")[0]
            except OSError:
                break
            try:
                shown = str(winreg.QueryValueEx(key, f"Value{i}")[0])
            except OSError:
                shown = ""
            i += 1
            # keep temperatures only (skip power, clocks, usage, etc.)
            if shown and "°" not in shown and not shown.strip().endswith(("C", "F")):
                continue
            try:
                v = float(str(raw).replace(",", "."))
            except ValueError:
                continue
            if "°F" in shown:
                v = (v - 32) * 5 / 9  # HWiNFO set to Fahrenheit: normalise to °C
            out.append((str(label), v))
    return out


def read_nvidia_gpu():
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3, creationflags=NO_WINDOW)
        return float(r.stdout.strip().splitlines()[0])
    except Exception:
        return None


def pick_temps():
    """Return dict with the HIGHEST reported 'CPU' and 'GPU' temps (or None).

    Every temperature you tick "Report value in Gadget" on counts: GPU-labelled
    ones (incl. hot spot) go to GPU, everything else (package, cores, core max,
    CPU) goes to CPU. The widget shows the hottest of each group.
    """
    cpu_vals, gpu_vals = [], []
    for label, v in read_hwinfo():
        (gpu_vals if "gpu" in label.lower() else cpu_vals).append(v)
    nv = read_nvidia_gpu()
    if nv is not None:
        gpu_vals.append(nv)
    return {"CPU": max(cpu_vals) if cpu_vals else None,
            "GPU": max(gpu_vals) if gpu_vals else None}


class Widget:
    def __init__(self):
        self.cfg = load_cfg()
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        try:
            self.root.attributes("-alpha", self.cfg["opacity"])
        except tk.TclError:
            pass
        self.root.configure(bg=BG)
        self.root.geometry(f"+{self.cfg['x']}+{self.cfg['y']}")

        self.frame = tk.Frame(self.root, bg=BG, padx=10, pady=4)
        self.frame.pack()
        self.labels = {}
        for col, name in enumerate(("CPU", "GPU")):
            lbl = tk.Label(self.frame, text=f"{name} --°", bg=BG, fg=COLORS["dim"])
            lbl.grid(row=0, column=col, padx=(0 if col == 0 else 14, 0))
            self.labels[name] = lbl
        self.apply_font()

        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label="Bigger text", command=lambda: self.resize(+2))
        self.menu.add_command(label="Smaller text", command=lambda: self.resize(-2))
        self.menu.add_separator()
        self.menu.add_command(label="Close", command=self.quit)

        for w in [self.root, self.frame, *self.labels.values()]:
            w.bind("<ButtonPress-1>", self.start_drag)
            w.bind("<B1-Motion>", self.drag)
            w.bind("<ButtonRelease-1>", self.end_drag)
            w.bind("<Button-3>", self.show_menu)
            w.bind("<MouseWheel>", lambda e: self.resize(+1 if e.delta > 0 else -1))

        self.tick()

    def apply_font(self):
        for lbl in self.labels.values():
            lbl.configure(font=("Segoe UI Semibold", self.cfg["font_size"]))

    def resize(self, step):
        self.cfg["font_size"] = max(8, min(72, self.cfg["font_size"] + step))
        self.apply_font()
        save_cfg(self.cfg)

    def start_drag(self, e):
        self._dx, self._dy = e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y()

    def drag(self, e):
        self.root.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    def end_drag(self, _e):
        self.cfg["x"], self.cfg["y"] = self.root.winfo_x(), self.root.winfo_y()
        save_cfg(self.cfg)

    def show_menu(self, e):
        self.menu.tk_popup(e.x_root, e.y_root)

    def color_for(self, name, v):
        if v is None:
            return COLORS["dim"]
        hot = self.cfg["cpu_hot"] if name == "CPU" else self.cfg["gpu_hot"]
        if v >= hot:
            return COLORS["hot"]
        if v >= hot - self.cfg["warn_margin"]:
            return COLORS["warn"]
        return COLORS["ok"]

    def tick(self):
        temps = pick_temps()
        for name, v in temps.items():
            if v is None:
                txt = f"{name} --°"
            elif str(self.cfg.get("units", "F")).upper() == "F":
                txt = f"{name} {v * 9 / 5 + 32:.0f}°F"
            else:
                txt = f"{name} {v:.0f}°C"
            self.labels[name].configure(text=txt, fg=self.color_for(name, v))
        hot = any(
            v is not None and v >= (self.cfg["cpu_hot"] if n == "CPU" else self.cfg["gpu_hot"])
            for n, v in temps.items())
        self.frame.configure(bg="#3A0000" if hot else BG)
        for lbl in self.labels.values():
            lbl.configure(bg="#3A0000" if hot else BG)
        self.root.attributes("-topmost", True)
        self.root.after(self.cfg["interval_ms"], self.tick)

    def quit(self):
        save_cfg(self.cfg)
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    Widget().run()
