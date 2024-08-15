from datetime import datetime, timezone
import struct

from colmi_r02_client.packet import make_packet

CMD_READ_HEART_RATE = 21  # 0x15


def read_heart_rate_packet(target: datetime | None = None) -> bytearray:
    if target is None:
        target = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
    data = bytearray(struct.pack("<L", int(target.timestamp())))

    return make_packet(CMD_READ_HEART_RATE, data)


class DailyHeartRateParser:
    def __init__(self):
        self.reset()

    def reset(self):
        self.heart_rate_array = []
        self.m_utc_time = None
        self.size = 0
        self.index = 0
        self.end = False
        self.range = 5

    def is_today(self) -> bool:
        d = self.m_utc_time
        if d is None:
            return False
        now = datetime.now()  # use local time
        return d.year == now.year and d.month == now.month and d.day == now.day

    def parse(self, packet: bytearray) -> None:
        r"""
        first byte of packet should always be CMD_READ_HEART_RATE (21)
        second byte is the sub_type

        sub_type 0 contains the lengths of things
        byte 2 is the number of expected packets after this.

        example: bytearray(b'\x15\x00\x18\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x002'),


        """

        sub_type = packet[1]
        if sub_type == 255 or (self.is_today() and sub_type == 23):
            # reset?
            return
        if sub_type == 0:
            self.end = False
            self.size = packet[2]  # number of expected readings or packets?
            self.range = packet[3]
            self.heart_rate_array = [-1] * (
                self.size * 13
            )  # don't really need this but...
        elif sub_type == 1:
            # next 4 bytes are a timestamp
            ts = struct.unpack_from("<l", packet, offset=2)[0]
            self.m_utc_time = datetime.fromtimestamp(ts, timezone.utc)
            # TODO timezone?

            # remaining 16 - type - subtype - 4 - crc = 9
            self.heart_rate_array[0:9] = list(packet[6:-1])  # I think this is the rest?
            self.index += 9
        else:
            b = len(self.heart_rate_array)
            print("packet", list(packet[2:15]))
            print("slice", self.heart_rate_array[self.index : self.index + 13])
            print(
                [
                    x
                    for x in self.heart_rate_array[self.index : self.index + 13]
                    if x != -1
                ]
            )
            assert not [
                x
                for x in self.heart_rate_array[self.index : self.index + 13]
                if x != -1
            ]
            self.heart_rate_array[self.index : self.index + 13] = list(packet[2:15])
            assert b == len(self.heart_rate_array)
            self.index += 13
            if sub_type == self.size - 1:
                self.end = True
                # probaby do a reset
        self.end = True
        # possibly do a reset
        print("post self", self)