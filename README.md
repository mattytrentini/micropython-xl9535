# MicroPython XL9535 / XL9555

A dependency-free, pure-Python driver for the XL9535 and XL9555 16-bit I2C GPIO
expanders. Both chips use the same register map and the `XL9535` class.

## Install

On a network-connected MicroPython device:

```python
import mip
mip.install("github:mattytrentini/micropython-xl9535")
```

Or install from a host with mpremote:

```sh
mpremote mip install github:mattytrentini/micropython-xl9535
```

Only `xl9535.py` is installed; there are no runtime dependencies.

## API

```python
from xl9535 import XL9535
expander = XL9535(i2c, address=0x20)
```

Supply an existing `machine.I2C` or compatible object supporting
`readfrom_mem_into` and `writeto_mem`. Addresses must be integers in
`0x20`–`0x27`; the default is `0x20`. The caller owns bus setup and lifetime.
Construction performs **no I2C transactions** and does not change directions,
output latches, or polarity.

| Member | Meaning |
| --- | --- |
| `input` | Read-only 16-bit actual input register, not the output latch. Hardware polarity inversion applies. |
| `output` | Read/write 16-bit output latch; reading it does not measure the pins. |
| `config` | Read/write 16-bit directions: `1` = input, `0` = output. |
| `polarity` | Read/write 16-bit input inversion: `1` inverts that input register bit, `0` leaves it unchanged. It does not invert the output latch. |
| `pin(index)` | Read an actual input register bit as `0` or `1`. |
| `pin(index, value)` | Set one output latch bit to `0` or `1`, preserving all other latch bits and all direction bits. Returns `None`. |

Indices are contiguous `0`–`15`: bits 0–7 map to P00–P07, and bits 8–15 map
to P10–P17. Port 0 is the low byte and is transferred first. Register setters
accept integers `0`–`0xffff`; pin setters accept `0`/`1` (including booleans).
Invalid addresses, indices, or values raise `ValueError` before hardware
writes. I2C errors propagate to the caller.

A pin write does **not** enable output mode. Set a safe output latch before
changing a pin's direction to output, to avoid driving an unintended level:

```python
expander.pin(8, 0)                 # Prepare P10's latch, preserve other outputs.
expander.config = expander.config & ~(1 << 8)
```

Each operation reuses a two-byte buffer. The driver is not thread-safe or
reentrant, and `pin(index, value)` is a non-atomic read-modify-write of the
output latch. The caller must serialize all access, including access through
other driver instances to the same chip. Two-bank reads/writes are sequential
hardware transfers, not simultaneous sampling or switching.

## KinCony CO16 safe input example

The CO16's XL9555 digital input expander is at `0x24`, separate from the relay
expander at `0x22`. Configure all 16 pins as inputs before reading:

```python
from machine import I2C, Pin
from xl9535 import XL9535

i2c = I2C(0, sda=Pin(8), scl=Pin(18), freq=100_000)
inputs = XL9535(i2c, address=0x24)
inputs.config = 0xffff
raw = inputs.input
print("Input register: 0x%04x" % raw)
```

The CO16 inputs are active-low. The driver does not change polarity or assume
an application channel mapping: interpret raw levels in the caller. If the
hardware polarity register is zero, for example, `(~raw) & 0xffff` represents
active bits. Construction preserves any existing polarity setting; explicitly
set `inputs.polarity = 0` if your application needs uninverted raw levels.

The XL9555 has weak internal pull-ups (approximately 100 kOhm); the XL9535
does not. Neither chip has software-configurable pull-ups. Provide suitable
external biasing for floating XL9535 inputs and check the board circuitry and
electrical requirements for either variant.

## Register map and source

| Register pair | Function |
| --- | --- |
| `0x00`, `0x01` | Input ports 0, 1 |
| `0x02`, `0x03` | Output latches 0, 1 |
| `0x04`, `0x05` | Polarity inversion 0, 1 |
| `0x06`, `0x07` | Configuration 0, 1 |

Implemented from the [Xinluda XL9535/XL9555 datasheet, revision 2.2](https://file.elecfans.com/web2/M00/42/C2/pYYBAGJ6MciAaGQmAAj-0j0UacY043.pdf),
particularly sections 9.2–9.6. Input reads measure pin levels even for output
pins; output reads return stored latch bits instead.

## Regression tests

The CPython tests use a stateful two-port register model with independent
external levels and output latches:

```sh
python -m unittest discover -s tests
```

The mip-installed driver was also exercised on a CO16 XL9555 at `0x24`:
construction preserved configuration, output and polarity registers, and
all-input configuration plus both-bank input reads succeeded. Output-latch
behavior is covered by the register-model tests; the hardware smoke did not
drive the CO16 input terminals or operate its separate relay expander.

## License

MIT; copyright 2026 Matt Trentini. See `LICENSE`.
