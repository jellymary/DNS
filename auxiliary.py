class Auxiliary:
    @staticmethod
    def bytes_to_bits(bytes: bytes) -> str:
        return Auxiliary.int_to_bits(int.from_bytes(bytes, 'big'), len(bytes) * 8)

    @staticmethod
    def flags_to_bits(*flags: bool) -> str:
        return ''.join(str(int(flag)) for flag in flags)

    @staticmethod
    def int_to_bits(decimal: int, length: int) -> str:
        return bin(decimal)[2:].zfill(length)
