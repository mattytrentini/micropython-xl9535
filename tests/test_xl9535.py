import unittest

from xl9535 import XL9535


class RegisterModel:
    """Model register pairs, direction-controlled pins, and external levels."""

    def __init__(self, address=0x20):
        self.address = address
        self.registers = bytearray((0, 0, 0xFF, 0xFF, 0, 0, 0xFF, 0xFF))
        self.external = 0xFFFF
        self.forced_low = 0
        self.transactions = []

    def word(self, register):
        return self.registers[register] | (self.registers[register + 1] << 8)

    def seed(self, register, value):
        self.registers[register] = value & 0xFF
        self.registers[register + 1] = value >> 8

    def readfrom_mem_into(self, address, register, buffer):
        if address != self.address:
            raise OSError("no device at address")
        self.transactions.append(("read", register))
        config = self.word(6)
        levels = ((self.external & config) | (self.word(2) & ~config))
        levels &= ~self.forced_low
        levels ^= self.word(4)
        for offset in range(len(buffer)):
            current = register ^ (offset & 1)
            if current < 2:
                buffer[offset] = (levels >> (8 * current)) & 0xFF
            else:
                buffer[offset] = self.registers[current]

    def writeto_mem(self, address, register, buffer):
        if address != self.address:
            raise OSError("no device at address")
        self.transactions.append(("write", register, bytes(buffer)))
        for offset, value in enumerate(buffer):
            current = register ^ (offset & 1)
            if current >= 2:
                self.registers[current] = value


class XL9535Tests(unittest.TestCase):
    def test_constructor_preserves_all_registers_without_bus_access(self):
        bus = RegisterModel(0x24)
        bus.seed(2, 0xA55A)
        bus.seed(4, 0x1256)
        bus.seed(6, 0xF00F)
        before = bytes(bus.registers)
        chip = XL9535(bus, address=0x24)
        self.assertEqual(bus.transactions, [])
        self.assertEqual(bytes(bus.registers), before)
        self.assertEqual(chip.config, 0xF00F)
        self.assertEqual(chip.output, 0xA55A)
        self.assertEqual(chip.polarity, 0x1256)

    def test_input_reads_actual_pins_not_output_latches(self):
        bus = RegisterModel()
        chip = XL9535(bus)
        chip.config = 0xFFFE
        chip.output = 0xFFFF
        bus.external = 0x1234
        bus.forced_low = 1  # Simulate an externally clamped output pin.
        self.assertEqual(chip.input, 0x1234)
        self.assertEqual(chip.output, 0xFFFF)
        self.assertEqual(chip.pin(0), 0)
        bus.external = 0x9234
        self.assertEqual(chip.pin(15), 1)
        self.assertEqual(chip.output, 0xFFFF)
        with self.assertRaises(AttributeError):
            chip.input = 0

    def test_pin_write_preserves_other_latches_and_directions(self):
        bus = RegisterModel()
        chip = XL9535(bus)
        chip.config = 0xF0F0
        chip.output = 0xA55A
        bus.external = 0
        bus.forced_low = 0xFFFF
        chip.pin(8, 0)
        self.assertEqual(chip.output, 0xA45A)
        chip.pin(15, 0)
        self.assertEqual(chip.output, 0x245A)
        chip.pin(9, 1)
        self.assertEqual(chip.output, 0x265A)
        chip.pin(0, True)
        self.assertEqual(chip.output, 0x265B)
        self.assertEqual(chip.config, 0xF0F0)

    def test_register_words_are_low_byte_first_and_independent(self):
        bus = RegisterModel()
        chip = XL9535(bus)
        for name, register, value in (
            ("output", 2, 0x1234),
            ("polarity", 4, 0xABCD),
            ("config", 6, 0x5678),
        ):
            setattr(chip, name, value)
            self.assertEqual(bus.word(register), value)
            self.assertEqual(getattr(chip, name), value)
        self.assertEqual(chip.output, 0x1234)
        self.assertEqual(chip.polarity, 0xABCD)
        self.assertEqual(chip.config, 0x5678)

    def test_input_polarity_and_second_bank_mapping(self):
        bus = RegisterModel()
        chip = XL9535(bus)
        bus.external = 0x8101
        self.assertEqual(chip.input, 0x8101)
        self.assertEqual(chip.pin(0), 1)
        self.assertEqual(chip.pin(7), 0)
        self.assertEqual(chip.pin(8), 1)
        self.assertEqual(chip.pin(15), 1)
        chip.polarity = 0x8001
        self.assertEqual(chip.input, 0x0100)
        self.assertEqual(chip.pin(0), 0)
        self.assertEqual(chip.pin(8), 1)
        self.assertEqual(chip.pin(15), 0)

    def test_invalid_values_do_not_access_bus_or_change_outputs(self):
        bus = RegisterModel()
        chip = XL9535(bus)
        chip.output = 0x5AA5
        chip.config = 0xA5A5
        before = bytes(bus.registers)
        bus.transactions.clear()
        for name in ("output", "config", "polarity"):
            for value in (-1, 0x10000, 1.5, "0", None):
                with self.subTest(name=name, value=value):
                    with self.assertRaises(ValueError):
                        setattr(chip, name, value)
        for index in (-1, 16, 1.5, "0", None):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    chip.pin(index)
                with self.assertRaises(ValueError):
                    chip.pin(index, 1)
        for value in (-1, 2, 0x10000, 1.0, "1"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    chip.pin(8, value)
        self.assertEqual(bus.transactions, [])
        self.assertEqual(bytes(bus.registers), before)

    def test_address_bounds_and_full_word_bounds(self):
        for address in (0x20, 0x27):
            bus = RegisterModel(address)
            chip = XL9535(bus, address)
            for value in (0, 0xFFFF):
                chip.output = value
                self.assertEqual(chip.output, value)
                chip.config = value
                self.assertEqual(chip.config, value)
                chip.polarity = value
                self.assertEqual(chip.polarity, value)
        bus = RegisterModel()
        for address in (0x1F, 0x28, -1, 0x20 + 0.5, "32", None):
            with self.subTest(address=address):
                with self.assertRaises(ValueError):
                    XL9535(bus, address)
        self.assertEqual(bus.transactions, [])


if __name__ == "__main__":
    unittest.main()
