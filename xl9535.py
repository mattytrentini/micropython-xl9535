# MIT License
# Copyright (c) 2026 Matt Trentini


class XL9535:
    """XL9535/XL9555 16-bit I2C GPIO expander with caller-owned I2C."""

    def __init__(self, i2c, address=0x20):
        if not isinstance(address, int) or not 0x20 <= address <= 0x27:
            raise ValueError("address must be an integer from 0x20 to 0x27")
        self._i2c = i2c
        self._address = address
        self._buffer = bytearray(2)

    def _read16(self, register):
        self._i2c.readfrom_mem_into(self._address, register, self._buffer)
        return self._buffer[0] | (self._buffer[1] << 8)

    def _write16(self, register, value):
        if not isinstance(value, int) or not 0 <= value <= 0xFFFF:
            raise ValueError("value must be an integer from 0 to 0xffff")
        self._buffer[0] = value & 0xFF
        self._buffer[1] = value >> 8
        self._i2c.writeto_mem(self._address, register, self._buffer)

    @property
    def input(self):
        """Actual input register, including the hardware polarity inversion."""
        return self._read16(0x00)

    @property
    def output(self):
        """Output latch; does not report the actual pin levels."""
        return self._read16(0x02)

    @output.setter
    def output(self, value):
        self._write16(0x02, value)

    @property
    def config(self):
        """Direction bits: 1 selects input, 0 selects output."""
        return self._read16(0x06)

    @config.setter
    def config(self, value):
        self._write16(0x06, value)

    @property
    def polarity(self):
        """Input polarity bits: 1 inverts the corresponding input reading."""
        return self._read16(0x04)

    @polarity.setter
    def polarity(self, value):
        self._write16(0x04, value)

    def pin(self, index, value=None):
        """Read actual pin level, or update one output latch bit with 0/1."""
        if not isinstance(index, int) or not 0 <= index <= 15:
            raise ValueError("index must be an integer from 0 to 15")
        if value is None:
            return (self.input >> index) & 1
        if not isinstance(value, int) or value not in (0, 1):
            raise ValueError("pin value must be 0 or 1")
        mask = 1 << index
        latch = self.output
        if value:
            latch |= mask
        else:
            latch &= ~mask
        self.output = latch
