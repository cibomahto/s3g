import unittest
import sys
import io
import s3g

class CRCTests(unittest.TestCase):
  def test_cases(self):
    cases = [
      [b'input', b'\xFF'],
      [b'input2', b'\xFF'],
    ]
    for case in cases:
      assert s3g.CalculateCRC(case[0]) == case[1]


class EncodeTests(unittest.TestCase):
  def test_encode_int32(self):
    cases = [
      [0,            '\x00\x00\x00\x00'],
      [-2147483648,  '\x00\x00\x00\x80'],
      [2147483647,   '\xFF\xFF\xFF\x7F'],
    ]
    for case in cases:
      assert s3g.EncodeInt32(case[0]) == case[1]
    
  def test_encode_uint32(self):
    cases = [
      [0,            '\x00\x00\x00\x00'],
      [2147483647,   '\xFF\xFF\xFF\x7F'],
      [4294967295,   '\xFF\xFF\xFF\xFF'],
    ]
    for case in cases:
      assert s3g.EncodeUint32(case[0]) == case[1]


class PacketEncodeTests(unittest.TestCase):
  def test_reject_oversize_payload(self):
    payload = bytearray()
    for i in range (0, s3g.maximum_payload_length + 1):
      payload.append(i)
    self.assertRaises(s3g.PacketLengthError,s3g.EncodePacket,payload)

  def test_packet_length(self):
    payload = 'abcd'
    packet = s3g.EncodePacket(payload)
    assert len(packet) == len(payload) + 3

  def test_packet_header(self):
    payload = 'abcd'
    packet = s3g.EncodePacket(payload)

    assert packet[0] == s3g.header

  def test_packet_length_field(self):
    payload = 'abcd'
    packet = s3g.EncodePacket(payload)
    assert packet[1] == len(payload)

  def test_packet_crc(self):
    payload = 'abcd'
    packet = s3g.EncodePacket(payload)
    assert packet[6] == s3g.CalculateCRC(payload);


class PacketDecodeTests(unittest.TestCase):
  def test_undersize_packet(self):
    packet = bytearray('abc')
    self.assertRaises(s3g.PacketLengthError,s3g.DecodePacket,packet)
    
  def test_wrong_header(self):
    packet = bytearray('abcd')
    self.assertRaises(s3g.PacketHeaderError,s3g.DecodePacket,packet)

  def test_bad_packet_length_field(self):
    packet = bytearray()
    packet.append(s3g.header)
    packet.append(5)
    packet.extend('ab')
    self.assertRaises(s3g.PacketLengthFieldError,s3g.DecodePacket,packet)

  def test_bad_crc(self):
    packet = bytearray()
    packet.append(s3g.header)
    packet.append(1)
    packet.extend('a')
    packet.append(s3g.CalculateCRC('a')+1)
    self.assertRaises(s3g.PacketCRCError,s3g.DecodePacket,packet)

  def test_got_payload(self):
    expected_payload = bytearray('abcde')

    packet = bytearray()
    packet.append(s3g.header)
    packet.append(len(expected_payload))
    packet.extend(expected_payload)
    packet.append(s3g.CalculateCRC(expected_payload))

    payload = s3g.DecodePacket(packet)
    assert payload == expected_payload


class PacketStreamDecoderTests(unittest.TestCase):
  def setUp(self):
    self.s = s3g.PacketStreamDecoder()

  def tearDown(self):
    self.s = None

  def test_starts_in_ready_mode(self):
    assert(self.s.state == "READY")
    assert(len(self.s.payload) == 0)
    assert(self.s.expected_length == 0)

  def test_reject_bad_header(self):
    self.assertRaises(s3g.PacketHeaderError,self.s.ReceiveByte,0x00)
    assert(self.s.state == "READY")

  def test_accept_header(self):
    self.s.ReceiveByte(s3g.header)
    assert(self.s.state == "WAIT_FOR_LENGTH")

  def test_reject_bad_size(self):
    self.s.ReceiveByte(s3g.header)
    self.assertRaises(s3g.PacketLengthFieldError,self.s.ReceiveByte,s3g.maximum_payload_length+1)

  def test_accept_size(self):
    self.s.ReceiveByte(s3g.header)
    self.s.ReceiveByte(s3g.maximum_payload_length)
    assert(self.s.state == "WAIT_FOR_DATA")
    assert(self.s.expected_length == s3g.maximum_payload_length)

  def test_accepts_data(self):
    self.s.ReceiveByte(s3g.header)
    self.s.ReceiveByte(s3g.maximum_payload_length)
    for i in range (0, s3g.maximum_payload_length):
      self.s.ReceiveByte(i)

    assert(self.s.expected_length == s3g.maximum_payload_length)
    for i in range (0, s3g.maximum_payload_length):
      assert(self.s.payload[i] == i)

  def test_reject_bad_crc(self):
    payload = 'abcde'
    self.s.ReceiveByte(s3g.header)
    self.s.ReceiveByte(len(payload))
    for i in range (0, len(payload)):
      self.s.ReceiveByte(payload[i])
    self.assertRaises(s3g.PacketCRCError,self.s.ReceiveByte,s3g.CalculateCRC(payload)+1)

  def test_returns_payload(self):
    payload = 'abcde'
    self.s.ReceiveByte(s3g.header)
    self.s.ReceiveByte(len(payload))
    for i in range (0, len(payload)):
      self.s.ReceiveByte(payload[i])
    assert(self.s.ReceiveByte(s3g.CalculateCRC(payload)) == payload)


class ReplicatorTests(unittest.TestCase):
  def setUp(self):
    self.r = s3g.Replicator()
    self.stream = io.BytesIO()
    self.r.stream = self.stream

  def tearDown(self):
    self.r = None
    self.stream = None

  def test_queue_extended_point(self):
    expected_target = [1,2,3,4,5]
    expected_velocity = 6
    self.r.Move(expected_target, expected_velocity)

    packet = bytearray(self.stream.getvalue())

    payload = s3g.DecodePacket(packet)
    assert payload[0] == s3g.command_map['QUEUE_EXTENDED_POINT']
    for i in range(0, 5):
      assert s3g.EncodeInt32(expected_target[i]) == payload[(i*4+1):(i*4+5)]


if __name__ == "__main__":
  unittest.main()
    
